import time
import random
from PyQt6.QtCore import QThread, pyqtSignal
from pynput.mouse import Button, Controller

class Clicker(QThread):
    """
    High-performance clicker engine using QThread and pynput.
    """
    stats_updated = pyqtSignal(int)
    state_changed = pyqtSignal(str)

    def __init__(self, button='left', click_type='single', cps=10.0, jitter=0.0, 
                 start_delay=0.0, smart_pause=False, smart_pause_delay=1.0,
                 mode='fixed', min_interval=1.0, max_interval=5.0,
                 stop_mode='none', stop_value=0.0):
        super().__init__()
        self.mouse = Controller()
        self.running = False
        self.button = button
        self.click_type = click_type
        self.cps = max(0.1, cps)
        self.jitter = jitter
        self.start_delay = start_delay
        self.smart_pause = smart_pause
        self.smart_pause_delay = smart_pause_delay
        self.mode = mode
        self.min_interval = min_interval
        self.max_interval = max_interval
        
        # Stop conditions
        self.stop_mode = stop_mode  # 'none', 'count', 'time'
        self.stop_value = stop_value
        
        self.click_count = 0
        self.finish_reason = 'idle'
        self._last_state = None
        
        self.button_map = {
            'left': Button.left,
            'right': Button.right,
            'middle': Button.middle,
            'side1': Button.x1,
            'side2': Button.x2
        }

    def update_settings(self, button, click_type, cps, jitter, 
                        start_delay=0.0, smart_pause=False, smart_pause_delay=1.0,
                        mode='fixed', min_interval=1.0, max_interval=5.0,
                        stop_mode='none', stop_value=0.0):
        self.button = button
        self.click_type = click_type
        self.cps = max(0.1, cps)
        self.jitter = jitter
        self.start_delay = start_delay
        self.smart_pause = smart_pause
        self.smart_pause_delay = smart_pause_delay
        self.mode = mode
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.stop_mode = stop_mode
        self.stop_value = stop_value

    def stop(self):
        self.finish_reason = 'idle'
        self.running = False
        if QThread.currentThread() != self:
            self.wait()

    def _emit_state(self, state):
        if self._last_state != state:
            self._last_state = state
            self.state_changed.emit(state)

    def run(self):
        self.finish_reason = 'finished'
        self.running = True
        self._emit_state('running')
        
        # Start Delay
        if self.start_delay > 0:
            end_delay_time = time.time() + self.start_delay
            while time.time() < end_delay_time:
                if not self.running:
                    self._emit_state(self.finish_reason)
                    return
                # Short sleep to remain responsive
                time.sleep(0.05)

        run_start_time = time.time()
        self.click_count = 0
        
        btn = self.button_map.get(self.button, Button.left)
        next_click_time = time.perf_counter()
        last_stats_time = time.perf_counter()
        
        # Smart Pause state
        last_mouse_pos = self.mouse.position
        last_move_time = time.time()
        is_paused = False

        while self.running:
            # Check Stop Condition: Time
            if self.stop_mode == 'time':
                if (time.time() - run_start_time) >= self.stop_value:
                    self.running = False
                    break

            # Smart Pause Logic
            if self.smart_pause:
                current_pos = self.mouse.position
                if current_pos != last_mouse_pos:
                    last_mouse_pos = current_pos
                    last_move_time = time.time()
                    if not is_paused:
                        is_paused = True
                        self._emit_state('paused')
                
                if is_paused:
                    if time.time() - last_move_time > self.smart_pause_delay:
                        is_paused = False
                        # Reset next_click_time to avoid burst after resume
                        next_click_time = time.perf_counter()
                        self._emit_state('running')
                    else:
                        # Paused, so we loop continue. 
                        # Sleep briefly to not spin CPU while paused
                        time.sleep(0.05)
                        continue

            current_time = time.perf_counter()
            
            if current_time >= next_click_time:
                # Perform the action
                if self.click_type == 'single':
                    self.mouse.click(btn, 1)
                elif self.click_type == 'double':
                    self.mouse.click(btn, 2)
                elif self.click_type == 'hold':
                     self.mouse.press(btn)
                     time.sleep(0.05) 
                     self.mouse.release(btn)
                
                self.click_count += 1
                
                # Check Stop Condition: Count
                if self.stop_mode == 'count':
                    if self.click_count >= self.stop_value:
                        self.running = False
                        break

                if self.mode == 'random':
                    interval = random.uniform(self.min_interval, self.max_interval)
                    next_click_time = current_time + interval
                else:
                    # Calculate next interval with jitter
                    base_interval = 1.0 / self.cps
                    interval = base_interval
                    if self.jitter > 0:
                        calc_jitter = base_interval * self.jitter
                        interval = base_interval + random.uniform(-calc_jitter, calc_jitter)
                    
                    next_click_time = max(next_click_time + interval, current_time + 0.001)

                # Emit stats
                if current_time - last_stats_time >= 0.1:
                    self.stats_updated.emit(self.click_count)
                    last_stats_time = current_time

            # High-precision sleep with responsiveness
            while self.running:
                # Re-check time stop condition during sleep
                if self.stop_mode == 'time':
                    if (time.time() - run_start_time) >= self.stop_value:
                        self.running = False
                        break

                now = time.perf_counter()
                if now >= next_click_time - 0.002:
                    break
                
                sleep_time = next_click_time - now - 0.001
                if sleep_time > 0.05:
                    time.sleep(0.01)
                else:
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    break
        
        self.stats_updated.emit(self.click_count)
        self._emit_state(self.finish_reason)
