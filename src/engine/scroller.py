import time
import random
from PyQt6.QtCore import QThread, pyqtSignal
from pynput.mouse import Controller

class Scroller(QThread):
    """
    High-performance scroller engine using QThread and pynput.
    """
    stats_updated = pyqtSignal(int)

    # Direction vectors for scrolling
    # Using 0.7071 (approx 1/sqrt(2)) for diagonals to maintain consistent speed
    DIRECTION_MAP = {
        'up': (0.0, 1.0),
        'down': (0.0, -1.0),
        'left': (-1.0, 0.0),
        'right': (1.0, 0.0),
        'up-left': (-0.7071, 0.7071),
        'up-right': (0.7071, 0.7071),
        'down-left': (-0.7071, -0.7071),
        'down-right': (0.7071, -0.7071)
    }

    def __init__(self, direction='down', scroll_speed=10.0, jitter=0.0,
                 start_delay=0.0, smart_pause=False, smart_pause_delay=1.0,
                 stop_mode='none', stop_value=0.0):
        super().__init__()
        self.mouse = Controller()
        self.running = False
        self.direction = direction
        self.scroll_speed = max(0.1, scroll_speed)
        self.jitter = jitter
        self.start_delay = start_delay
        self.smart_pause = smart_pause
        self.smart_pause_delay = smart_pause_delay
        self.stop_mode = stop_mode
        self.stop_value = stop_value
        self.scroll_count = 0

    def update_settings(self, direction, scroll_speed, jitter,
                        start_delay=0.0, smart_pause=False, smart_pause_delay=1.0,
                        stop_mode='none', stop_value=0.0):
        self.direction = direction
        self.scroll_speed = max(0.1, scroll_speed)
        self.jitter = jitter
        self.start_delay = start_delay
        self.smart_pause = smart_pause
        self.smart_pause_delay = smart_pause_delay
        self.stop_mode = stop_mode
        self.stop_value = stop_value

    def stop(self):
        self.running = False
        # Prevent deadlock if stop() is called from within the running thread
        if QThread.currentThread() != self:
            self.wait()

    def run(self):
        self.running = True
        
        # Start Delay
        if self.start_delay > 0:
            end_delay_time = time.time() + self.start_delay
            while time.time() < end_delay_time:
                if not self.running:
                    return
                # Short sleep to remain responsive
                time.sleep(0.05)

        self.scroll_count = 0
        run_start_time = time.time()
        
        # 100Hz Fixed Loop + Accumulator
        TARGET_FPS = 100
        time_step = 1.0 / TARGET_FPS
        
        # Accumulators for sub-pixel scrolling
        acc_x = 0.0
        acc_y = 0.0
        
        # Statistics accumulator
        accumulated_lines = 0.0
        
        # Smart Pause state
        last_mouse_pos = self.mouse.position
        last_move_time = time.time()
        is_paused = False

        # Initialize loop timing
        next_frame_time = time.perf_counter()
        last_stats_time = time.perf_counter()

        while self.running:
            current_loop_start = time.perf_counter()

            # --- CHECK STOP LIMITS ---
            if self.stop_mode == 'time' and (time.time() - run_start_time) >= self.stop_value:
                self.stop()
                break

            if self.stop_mode == 'count' and self.scroll_count >= self.stop_value:
                self.stop()
                break

            # --- SMART PAUSE LOGIC ---
            if self.smart_pause:
                current_pos = self.mouse.position
                if current_pos != last_mouse_pos:
                    last_mouse_pos = current_pos
                    last_move_time = time.time()
                    is_paused = True
                
                if is_paused:
                    if time.time() - last_move_time > self.smart_pause_delay:
                        is_paused = False
                        # Reset loop timing to avoid "catch-up" burst
                        next_frame_time = time.perf_counter()
                    else:
                        # While paused, sleep a bit and skip processing
                        time.sleep(0.05)
                        next_frame_time = time.perf_counter()
                        continue

            # --- SCROLL LOGIC ---
            
            # Base step calculation: lines per frame = lines/sec * sec/frame
            base_step = self.scroll_speed * time_step
            
            # Apply Jitter
            if self.jitter > 0:
                # Jitter as percentage variance (e.g., 0.1 = +/- 10%)
                variance = random.uniform(-self.jitter, self.jitter)
                step_amount = base_step * (1.0 + variance)
            else:
                step_amount = base_step
            
            # Get direction vector
            # Default to (0, -1) [down] if direction is invalid
            dir_x, dir_y = self.DIRECTION_MAP.get(self.direction, (0.0, -1.0))

            # Add to accumulators
            acc_x += step_amount * dir_x
            acc_y += step_amount * dir_y
            
            # Threshold for sending scroll event (1/120th of a logical line unit)
            # pynput/Windows generally use 120 units per notch. 
            threshold = 1.0 / 120.0
            
            send_x = 0.0
            send_y = 0.0
            
            # Quantize X Logic
            if abs(acc_x) >= threshold:
                # Calculate integer steps for pynput
                # e.g. acc_x = 0.1 --> steps_x = 12 --> send_x = 0.1
                # e.g. acc_x = 0.0084 (approx 1/120) --> steps_x = 1 --> send_x = 0.00833
                steps_x = int(acc_x * 120.0)
                if steps_x != 0:
                    send_x = steps_x / 120.0
                    acc_x -= send_x
            
            # Quantize Y Logic
            if abs(acc_y) >= threshold:
                steps_y = int(acc_y * 120.0)
                if steps_y != 0:
                    send_y = steps_y / 120.0
                    acc_y -= send_y

            # Send scroll command if valid steps were generated
            if send_x != 0.0 or send_y != 0.0:
                self.mouse.scroll(send_x, send_y)
                
                # Update statistics (approximate based on sent lines)
                lines_passed = max(abs(send_x), abs(send_y))
                accumulated_lines += lines_passed
                
                if accumulated_lines >= 1.0:
                    lines_int = int(accumulated_lines)
                    self.scroll_count += lines_int
                    accumulated_lines -= lines_int

            # --- STATS EMISSION ---
            if current_loop_start - last_stats_time >= 0.1:
                self.stats_updated.emit(self.scroll_count)
                last_stats_time = current_loop_start

            # --- LOOP TIMING ---
            next_frame_time += time_step
            now = time.perf_counter()
            sleep_needed = next_frame_time - now
            
            if sleep_needed > 0:
                time.sleep(sleep_needed)
            else:
                # If we are falling behind, don't sleep, but prevent spiral
                if now - next_frame_time > 0.1:
                    next_frame_time = now
