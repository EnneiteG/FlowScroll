import tkinter as tk
import tkinter.ttk as ttk
# Optional theming with ttkbootstrap. Keep the ttkbootstrap Style class separate
# so we never call its constructor when it's not available.
try:
    from ttkbootstrap import Style as _TBStyle
    _HAS_TTBOOT = True
except Exception:
    _TBStyle = None
    _HAS_TTBOOT = False

# pyautogui is optional for environments where automation isn't available.
try:
    import pyautogui
    _HAS_PYAUTOGUI = True
except Exception:
    pyautogui = None
    _HAS_PYAUTOGUI = False

def _ensure_pyautogui():
    """Check if pyautogui is available."""
    return _HAS_PYAUTOGUI

import time
import os
import sys
import json
import traceback
import tkinter.messagebox as messagebox
import random
import concurrent.futures
import multiprocessing
import workers_legacy as workers

# Keyboard support for global hotkeys
# Lazy loading - imported only when listeners are started
_HAS_KEYBOARD = None
_pynput_keyboard = None

def _ensure_pynput_keyboard():
    """Lazy load pynput keyboard only when needed."""
    global _pynput_keyboard, _HAS_KEYBOARD
    if _HAS_KEYBOARD is None:
        try:
            from pynput import keyboard as _kb
            _pynput_keyboard = _kb
            _HAS_KEYBOARD = True
        except Exception:
            _pynput_keyboard = None
            _HAS_KEYBOARD = False
    return _HAS_KEYBOARD

# Mouse support - lazy loading
_pynput_mouse = None

def _ensure_pynput_mouse():
    """Lazy load pynput mouse only when needed."""
    global _pynput_mouse
    if _pynput_mouse is None:
        try:
            from pynput import mouse as _pm
            _pynput_mouse = _pm
        except Exception:
            _pynput_mouse = None
    return _pynput_mouse

APP_VERSION = "2.2.0"


class Localization:
    """Localization system for multi-language support."""
    def __init__(self, lang='fr'):
        self.lang = lang
        self.translations = {}
        self._load_translations()
    
    def _load_translations(self):
        """Load translations from JSON file."""
        try:
            # Check if running as PyInstaller bundle
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
                locale_path = os.path.join(bundle_dir, 'locales.json')
            else:
                # Running as normal Python script
                locale_path = os.path.join(os.path.dirname(_settings_path()), 'locales.json')
            
            if os.path.exists(locale_path):
                with open(locale_path, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
            else:
                # Create default file if missing (only in non-frozen mode)
                if not getattr(sys, 'frozen', False):
                    self._create_default_translations(locale_path)
        except Exception as e:
            print(f"Error loading translations: {e}")
    
    def _create_default_translations(self, path):
        """Create default translations file."""
        default = {
            "fr": {"app_title": "Autoscroller v{version}"},
            "en": {"app_title": "Autoscroller v{version}"}
        }
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(default, f, indent=2, ensure_ascii=False)
            self.translations = default
        except Exception:
            pass
    
    def get(self, key, **kwargs):
        """Get translated text with optional formatting."""
        try:
            text = self.translations.get(self.lang, {}).get(key, key)
            if text is None:
                text = key
            return text.format(**kwargs) if kwargs else text
        except Exception:
            return key
    
    def set_language(self, lang):
        """Change language."""
        if lang in self.translations:
            self.lang = lang


def scroll_mouse_wheel(clicks, direction='down'):
    """Simulate a mouse-wheel scroll using pyautogui.

    clicks: positive integer number of wheel 'clicks'.
    direction: 'up' or 'down'.
    """
    if not _ensure_pyautogui() or pyautogui is None:
        return
    try:
        scroll_fn = getattr(pyautogui, 'scroll', None)
        if not callable(scroll_fn):
            return
        if direction == 'up':
            scroll_fn(clicks)
        elif direction == 'down':
            scroll_fn(-clicks)
    except Exception:
        pass


def _settings_path():
    """Get the settings file path that works with both script and PyInstaller executable."""
    try:
        # When frozen with PyInstaller, use the executable's directory
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
        else:
            # When running as script, use the script's directory
            base = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        base = os.getcwd()
    return os.path.join(base, 'autoscroller_settings.json')


def load_settings():
    path = _settings_path()
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_settings(settings: dict):
    path = _settings_path()
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


class ToolTip:
    """Simple tooltip class for hover help."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                        background="#ffffe0", relief='solid', borderwidth=1,
                        font=("tahoma", 8, "normal"))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class AutoScroller:
    def __init__(self, root, style=None):
        self.root = root
        self.style = style
        
        # Load settings
        self.settings = load_settings()
        
        # Track current theme
        self.current_theme = self.settings.get('theme', 'flatly')
        
        # Initialize localization
        self.locale = Localization(self.settings.get('language', 'fr'))
        
        try:
            self.root.title(self.locale.get('app_title', version=APP_VERSION))
        except Exception:
            pass
        
        # Scrolling state (vertical and horizontal)
        self.scrolling = False
        self.h_scrolling = False
        self.speed = self.settings.get('scroll_speed', 0)
        self.h_speed = self.settings.get('h_scroll_speed', 0)
        
        # Preset direction (positive or negative)
        self.scroll_preset_reverse = self.settings.get('scroll_preset_reverse', False)
        self.h_scroll_preset_reverse = self.settings.get('h_scroll_preset_reverse', False)
        
        # Scheduler tick (ms) and mapping to clicks/second
        self._tick_ms = 50  # Augmenté de 10 à 50ms pour réduire la charge CPU
        self._max_cps = 800.0
        self._accumulator = 0.0
        self._h_accumulator = 0.0
        self._last_time = None
        self._scroll_job = None
        self._h_scroll_job = None
        
        # Auto clicker state
        self.clicking = False
        self._click_job = None
        self._click_accumulator = 0.0
        self._last_click_time = None
        self._click_tick_ms = 50
        
        # Click configuration
        self.click_button = self.settings.get('click_button', 'left')  # left, right, middle
        self.click_type = self.settings.get('click_type', 'single')  # single, double, triple
        self.click_position_mode = self.settings.get('click_position_mode', 'current')  # current, fixed
        self.click_fixed_x = self.settings.get('click_fixed_x', 0)
        self.click_fixed_y = self.settings.get('click_fixed_y', 0)
        self.click_repeat_mode = self.settings.get('click_repeat_mode', 'infinite')  # infinite, count
        self.click_repeat_count = self.settings.get('click_repeat_count', 100)
        self._clicks_performed = 0
        
        # Phase 2 features
        self.hold_click_enabled = self.settings.get('hold_click_enabled', False)
        self.hold_duration = self.settings.get('hold_duration', 1.0)  # seconds
        self.click_area_randomization = self.settings.get('click_area_randomization', 0)  # pixels radius
        self._holding = False
        
        # Profile management
        self.current_profile = self.settings.get('current_profile', 'Défaut')
        
        # Counters
        self.click_count = 0
        
        # Batching optimization for pyautogui calls
        self._scroll_batch = 0
        self._h_scroll_batch = 0
        
        # Auto-timeout state
        self.auto_timeout_enabled = self.settings.get('auto_timeout_enabled', False)
        self.auto_timeout_minutes = self.settings.get('auto_timeout_minutes', 1)
        self._timeout_job = None
        self._timeout_start_time = None
        
        # Smart Pause state
        self.smart_pause_enabled = self.settings.get('smart_pause_enabled', False)
        self.smart_pause_seconds = self.settings.get('smart_pause_seconds', 3)
        self._smart_pause_active = False
        self._last_mouse_pos = None
        self._mouse_inactive_start = None
        self._smart_pause_check_job = None
        
        # UI state
        self.always_on_top = self.settings.get('always_on_top', False)
        
        # Logging state
        self.logging_enabled = self.settings.get('logging_enabled', False)
        self._log_file = None
        
        # Hotkeys with defaults
        default_hotkeys = {
            'toggle_scroll': 'F9',
            'toggle_click': 'F10',
            'toggle_h_scroll': 'F11',
            'emergency_stop': 'space'
        }
        self.hotkeys = self.settings.get('hotkeys', {})
        # Merge defaults for missing keys
        for key, value in default_hotkeys.items():
            if key not in self.hotkeys:
                self.hotkeys[key] = value
        
        self.create_widgets()
        self.create_menu()
        
        # Load saved values
        self.load_ui_state()
        
        # Apply saved UI preferences
        try:
            self.root.attributes('-topmost', self.always_on_top)
        except Exception:
            pass
        
        # Initialize logging if enabled
        if self.logging_enabled:
            self._init_logging()
        
        # Global listeners
        self._global_listener = None
        self._keyboard_listener = None

        # Executors for background work: thread executor for I/O / GUI-safe background tasks,
        # process executor left lazy (create when needed for CPU‑bound jobs).
        try:
            cpu_count = os.cpu_count() or 2
        except Exception:
            cpu_count = 2
        # Thread pool sized to allow background I/O and OS calls without blocking the mainloop
        self._thread_executor = concurrent.futures.ThreadPoolExecutor(max_workers=max(2, cpu_count * 2))
        self._process_executor = None

    def _get_process_executor(self):
        """Lazy-create a ProcessPoolExecutor for CPU-bound tasks.
        Keep it lazy so we don't spawn processes unless needed.
        """
        if self._process_executor is None:
            try:
                cpu_count = os.cpu_count() or 2
            except Exception:
                cpu_count = 2
            # Use number of CPUs (or at most cpu_count) processes
            self._process_executor = concurrent.futures.ProcessPoolExecutor(max_workers=cpu_count)
        return self._process_executor

    def submit_cpu_task(self, func_name, *args, callback=None):
        """Submit a CPU-bound worker function (from `workers` module) to process pool.
        - `func_name` : str, name of function in `workers` module
        - `callback` : callable to be invoked on main thread with `future` as arg
        """
        try:
            func = getattr(workers, func_name)
        except Exception:
            raise ValueError(f"Unknown worker function: {func_name}")

        proc_exec = self._get_process_executor()
        try:
            future = proc_exec.submit(func, *args)
            if callback is not None:
                # ensure callback runs on main thread using root.after
                def _cb(fut, cb=callback):
                    try:
                        self.root.after(0, lambda: cb(fut))
                    except Exception:
                        # best-effort: call synchronously
                        try:
                            cb(fut)
                        except Exception:
                            pass
                future.add_done_callback(_cb)
            return future
        except Exception as e:
            raise
        
        # Defer listener startup for faster initial launch (Option 3)
        try:
            self.root.after(100, self._start_global_listeners)
        except Exception:
            pass
        
        try:
            self.root.protocol('WM_DELETE_WINDOW', self._on_close)
        except Exception:
            pass

    def load_ui_state(self):
        """Load UI values from settings."""
        try:
            self.click_min_var.set(self.settings.get('click_min', 1))
            self.click_max_var.set(self.settings.get('click_max', 20))
            self.click_rate_var.set(self.settings.get('click_rate', 1))
            self.click_mode_var.set(self.settings.get('click_mode_cps', False))
            self._speed_var.set(self.speed)
            self._h_speed_var.set(self.h_speed)
            self.auto_timeout_var.set(self.auto_timeout_enabled)
            self.auto_timeout_minutes_var.set(self.auto_timeout_minutes)
            self.smart_pause_var.set(self.smart_pause_enabled)
            self.smart_pause_seconds_var.set(self.smart_pause_seconds)
            self.click_button_var.set(self.click_button)
            self.click_type_var.set(self.click_type)
            self.click_position_var.set(self.click_position_mode)
            self.click_fixed_x_var.set(self.click_fixed_x)
            self.click_fixed_y_var.set(self.click_fixed_y)
            self.click_repeat_var.set(self.click_repeat_mode)
            self.click_repeat_count_var.set(self.click_repeat_count)
            self.hold_click_var.set(self.hold_click_enabled)
            self.hold_duration_var.set(self.hold_duration)
            self.click_area_var.set(self.click_area_randomization)
            self._on_click_mode_changed()
            self._on_click_position_changed()
            self._on_click_repeat_changed()
            self._on_hold_click_changed()
        except Exception:
            pass

    def save_ui_state(self):
        """Save current UI values to settings."""
        try:
            self.settings['scroll_speed'] = self.speed
            self.settings['h_scroll_speed'] = self.h_speed
            self.settings['click_min'] = self.click_min_var.get()
            self.settings['click_max'] = self.click_max_var.get()
            self.settings['click_rate'] = self.click_rate_var.get()
            self.settings['click_mode_cps'] = self.click_mode_var.get()
            self.settings['click_button'] = self.click_button_var.get()
            self.settings['click_type'] = self.click_type_var.get()
            self.settings['click_position_mode'] = self.click_position_var.get()
            self.settings['click_fixed_x'] = self.click_fixed_x_var.get()
            self.settings['click_fixed_y'] = self.click_fixed_y_var.get()
            self.settings['click_repeat_mode'] = self.click_repeat_var.get()
            self.settings['click_repeat_count'] = self.click_repeat_count_var.get()
            self.settings['hold_click_enabled'] = self.hold_click_var.get()
            self.settings['hold_duration'] = self.hold_duration_var.get()
            self.settings['click_area_randomization'] = self.click_area_var.get()
            self.settings['current_profile'] = self.current_profile
            self.settings['auto_timeout_enabled'] = self.auto_timeout_var.get()
            self.settings['auto_timeout_minutes'] = self.auto_timeout_minutes_var.get()
            self.settings['smart_pause_enabled'] = self.smart_pause_var.get()
            self.settings['smart_pause_seconds'] = self.smart_pause_seconds_var.get()
            self.settings['always_on_top'] = self.always_on_top
            self.settings['logging_enabled'] = self.logging_enabled
            self.settings['hotkeys'] = self.hotkeys
            self.settings['language'] = self.locale.lang
            self.settings['scroll_preset_reverse'] = self.scroll_preset_reverse_var.get()
            self.settings['h_scroll_preset_reverse'] = self.h_scroll_preset_reverse_var.get()
            # Ensure theme is preserved if not explicitly set in this session
            if 'theme' not in self.settings and hasattr(self, 'current_theme'):
                self.settings['theme'] = self.current_theme
            save_settings(self.settings)
        except Exception:
            pass

    def create_menu(self):
        menubar = tk.Menu(self.root)
        
        # Theme menu
        theme_menu = tk.Menu(menubar, tearoff=0)
        
        # Light themes submenu
        light_menu = tk.Menu(theme_menu, tearoff=0)
        light_menu.add_command(label='Flatly', command=lambda: self.set_theme('flatly'))
        light_menu.add_command(label='Morph', command=lambda: self.set_theme('morph'))
        light_menu.add_command(label='Simplex', command=lambda: self.set_theme('simplex'))
        theme_menu.add_cascade(label=self.locale.get('menu_theme_light'), menu=light_menu)
        
        # Dark themes submenu
        dark_menu = tk.Menu(theme_menu, tearoff=0)
        dark_menu.add_command(label='Darkly', command=lambda: self.set_theme('darkly'))
        dark_menu.add_command(label='Solar', command=lambda: self.set_theme('solar'))
        dark_menu.add_command(label='Vapor', command=lambda: self.set_theme('vapor'))
        theme_menu.add_cascade(label=self.locale.get('menu_theme_dark'), menu=dark_menu)
        
        menubar.add_cascade(label=self.locale.get('menu_theme'), menu=theme_menu)
        
        # Profiles menu
        profiles_menu = tk.Menu(menubar, tearoff=0)
        profiles_menu.add_command(label=self.locale.get('menu_profiles_save'), command=self.save_profile_as)
        profiles_menu.add_command(label=self.locale.get('menu_profiles_load'), command=self.load_profile)
        profiles_menu.add_separator()
        profiles_menu.add_command(label=self.locale.get('menu_profiles_manage'), command=self.manage_profiles)
        menubar.add_cascade(label=self.locale.get('menu_profiles'), menu=profiles_menu)
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label=self.locale.get('menu_settings_hotkeys'), command=self.show_hotkey_dialog)
        settings_menu.add_separator()
        
        # Language submenu
        language_menu = tk.Menu(settings_menu, tearoff=0)
        language_menu.add_command(label='Français', command=lambda: self.set_language('fr'))
        language_menu.add_command(label='English', command=lambda: self.set_language('en'))
        settings_menu.add_cascade(label=self.locale.get('menu_settings_language'), menu=language_menu)
        settings_menu.add_separator()
        
        # Create BooleanVars for menu checkbuttons
        self.always_on_top_var = tk.BooleanVar(value=self.always_on_top)
        self.logging_var = tk.BooleanVar(value=self.logging_enabled)
        
        settings_menu.add_checkbutton(label=self.locale.get('menu_settings_always_on_top'), variable=self.always_on_top_var, command=self.toggle_always_on_top)
        settings_menu.add_separator()
        settings_menu.add_checkbutton(label=self.locale.get('menu_settings_enable_logs'), variable=self.logging_var, command=self.toggle_logging)
        settings_menu.add_command(label=self.locale.get('menu_settings_open_logs'), command=self.open_logs_folder)
        menubar.add_cascade(label=self.locale.get('menu_settings'), menu=settings_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label=self.locale.get('menu_help_about'), command=self.show_about)
        menubar.add_cascade(label=self.locale.get('menu_help'), menu=help_menu)
        
        try:
            self.root.config(menu=menubar)
        except Exception:
            pass

    def _position_dialog(self, dialog, width, height):
        """Position dialog window next to the main window (right or left if no space)."""
        try:
            # Update to get actual sizes
            self.root.update_idletasks()
            dialog.update_idletasks()
            
            # Get main window position and size
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            main_width = self.root.winfo_width()
            main_height = self.root.winfo_height()
            
            # Get screen size
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Calculate dialog size
            dialog_width = width
            dialog_height = height
            
            # Try to position on the right first
            dialog_x = main_x + main_width + 10
            dialog_y = main_y
            
            # Check if there's enough space on the right
            if dialog_x + dialog_width > screen_width:
                # Not enough space on right, try left
                dialog_x = main_x - dialog_width - 10
                
                # If still not enough space on left, center it
                if dialog_x < 0:
                    dialog_x = (screen_width - dialog_width) // 2
                    dialog_y = (screen_height - dialog_height) // 2
            
            # Ensure dialog stays within screen bounds
            dialog_x = max(0, min(dialog_x, screen_width - dialog_width))
            dialog_y = max(0, min(dialog_y, screen_height - dialog_height))
            
            dialog.geometry(f"{dialog_width}x{dialog_height}+{dialog_x}+{dialog_y}")
        except Exception:
            # Fallback to default geometry
            dialog.geometry(f"{width}x{height}")
    
    def show_hotkey_dialog(self):
        """Show dialog to configure hotkeys."""
        dialog = tk.Toplevel(self.root)
        dialog.title(self.locale.get('dialog_hotkeys_title'))
        dialog.transient(self.root)
        dialog.grab_set()
        self._position_dialog(dialog, 450, 280)
        
        tk.Label(dialog, text=self.locale.get('dialog_hotkeys_label'), font=('Arial', 10, 'bold')).pack(pady=10)
        
        frame = tk.Frame(dialog)
        frame.pack(pady=10, padx=20, fill='both', expand=True)
        
        tk.Label(frame, text=self.locale.get('dialog_hotkeys_scroll')).grid(row=0, column=0, sticky='w', pady=5)
        scroll_entry = tk.Entry(frame, width=15)
        scroll_entry.insert(0, self.hotkeys.get('toggle_scroll', 'F9'))
        scroll_entry.grid(row=0, column=1, padx=10, pady=5)
        
        tk.Label(frame, text=self.locale.get('dialog_hotkeys_click')).grid(row=1, column=0, sticky='w', pady=5)
        click_entry = tk.Entry(frame, width=15)
        click_entry.insert(0, self.hotkeys.get('toggle_click', 'F10'))
        click_entry.grid(row=1, column=1, padx=10, pady=5)
        
        tk.Label(frame, text=self.locale.get('dialog_hotkeys_h_scroll')).grid(row=2, column=0, sticky='w', pady=5)
        h_scroll_entry = tk.Entry(frame, width=15)
        h_scroll_entry.insert(0, self.hotkeys.get('toggle_h_scroll', 'F11'))
        h_scroll_entry.grid(row=2, column=1, padx=10, pady=5)
        
        def save_hotkeys():
            self.hotkeys['toggle_scroll'] = scroll_entry.get()
            self.hotkeys['toggle_click'] = click_entry.get()
            self.hotkeys['toggle_h_scroll'] = h_scroll_entry.get()
            self.save_ui_state()
            try:
                self._stop_keyboard_listener()
                self._start_keyboard_listener()
            except Exception:
                pass
            dialog.destroy()
        
        tk.Button(dialog, text=self.locale.get('button_save'), command=save_hotkeys).pack(pady=10)

    def show_about(self):
        """Show about dialog."""
        about_text = self.locale.get('dialog_about_text', version=APP_VERSION)
        messagebox.showinfo(self.locale.get('dialog_about_title'), about_text)
    
    def set_language(self, lang):
        """Change application language and reload UI in real-time."""
        self.locale.set_language(lang)
        self.settings['language'] = lang
        save_settings(self.settings)
        
        # Update all UI elements in real-time
        self._update_ui_texts()
    
    def _update_ui_texts(self):
        """Update all UI texts with current language."""
        try:
            # Update window title
            self.root.title(self.locale.get('app_title', version=APP_VERSION))
            
            # Update button texts (preserve state)
            if hasattr(self, 'clicker_button'):
                if self.clicking:
                    self.clicker_button.config(text=self.locale.get('button_stop_click'))
                else:
                    self.clicker_button.config(text=self.locale.get('button_start_click'))
            
            if hasattr(self, 'start_stop_button'):
                if self.scrolling:
                    self.start_stop_button.config(text=self.locale.get('button_stop_scroll'))
                else:
                    self.start_stop_button.config(text=self.locale.get('button_start_scroll'))
            
            if hasattr(self, 'h_start_stop_button'):
                if self.h_scrolling:
                    self.h_start_stop_button.config(text=self.locale.get('button_stop_h_scroll'))
                else:
                    self.h_start_stop_button.config(text=self.locale.get('button_start_h_scroll'))
            
            if hasattr(self, 'pick_position_btn'):
                self.pick_position_btn.config(text=self.locale.get('button_pick_position'))
            
            # Update preset buttons
            if hasattr(self, 'scroll_preset_slow_btn'):
                self.scroll_preset_slow_btn.config(text=self.locale.get('button_preset_slow'))
            if hasattr(self, 'scroll_preset_normal_btn'):
                self.scroll_preset_normal_btn.config(text=self.locale.get('button_preset_normal'))
            if hasattr(self, 'scroll_preset_fast_btn'):
                self.scroll_preset_fast_btn.config(text=self.locale.get('button_preset_fast'))
            if hasattr(self, 'scroll_preset_ultra_btn'):
                self.scroll_preset_ultra_btn.config(text=self.locale.get('button_preset_ultra'))
            if hasattr(self, 'scroll_preset_reset_btn'):
                self.scroll_preset_reset_btn.config(text=self.locale.get('button_preset_reset'))
            
            if hasattr(self, 'h_scroll_preset_slow_btn'):
                self.h_scroll_preset_slow_btn.config(text=self.locale.get('button_preset_slow'))
            if hasattr(self, 'h_scroll_preset_normal_btn'):
                self.h_scroll_preset_normal_btn.config(text=self.locale.get('button_preset_normal'))
            if hasattr(self, 'h_scroll_preset_fast_btn'):
                self.h_scroll_preset_fast_btn.config(text=self.locale.get('button_preset_fast'))
            if hasattr(self, 'h_scroll_preset_ultra_btn'):
                self.h_scroll_preset_ultra_btn.config(text=self.locale.get('button_preset_ultra'))
            if hasattr(self, 'h_scroll_preset_reset_btn'):
                self.h_scroll_preset_reset_btn.config(text=self.locale.get('button_preset_reset'))
            
            # Update preset reverse checkboxes
            if hasattr(self, 'scroll_preset_reverse_cb'):
                self.scroll_preset_reverse_cb.config(text=self.locale.get('checkbox_preset_reverse'))
            if hasattr(self, 'h_scroll_preset_reverse_cb'):
                self.h_scroll_preset_reverse_cb.config(text=self.locale.get('checkbox_preset_reverse'))
            
            # Update click counter
            if hasattr(self, 'click_counter_label'):
                self.click_counter_label.config(text=self.locale.get('label_clicks', count=self.click_count))
            
            # Update checkbutton texts
            if hasattr(self, 'click_mode_cb'):
                self.click_mode_cb.config(text=self.locale.get('checkbox_use_cps'))
            if hasattr(self, 'hold_click_cb'):
                self.hold_click_cb.config(text=self.locale.get('checkbox_hold_click'))
            if hasattr(self, 'auto_timeout_cb'):
                self.auto_timeout_cb.config(text=self.locale.get('checkbox_timeout'))
            if hasattr(self, 'smart_pause_cb'):
                self.smart_pause_cb.config(text=self.locale.get('checkbox_smart_pause'))
            
            # Update radiobutton texts
            for widget in self.root.winfo_children():
                self._update_widget_texts_recursive(widget)
            
            # Recreate menu bar with new language
            self.create_menu()
            
        except Exception as e:
            print(f"Error updating UI texts: {e}")
    
    def _update_widget_texts_recursive(self, widget):
        """Recursively update texts for all child widgets."""
        try:
            # Update radiobuttons based on their value
            if isinstance(widget, tk.Radiobutton):
                var = widget.cget('variable')
                val = widget.cget('value')
                
                # Position radiobuttons
                if val == 'current':
                    widget.config(text=self.locale.get('label_position_current'))
                elif val == 'fixed':
                    widget.config(text=self.locale.get('label_position_fixed'))
                # Repeat radiobuttons
                elif val == 'infinite':
                    widget.config(text=self.locale.get('label_repeat_infinite'))
                elif val == 'count':
                    widget.config(text=self.locale.get('label_repeat_count'))
            
            # Recursively process children
            for child in widget.winfo_children():
                self._update_widget_texts_recursive(child)
        except Exception:
            pass

    def set_theme(self, theme_name: str):
        """Switch ttkbootstrap theme at runtime."""
        try:
            if _HAS_TTBOOT and _TBStyle is not None:
                if self.style is not None:
                    try:
                        self.style.theme_use(theme_name)
                    except Exception:
                        try:
                            self.style = _TBStyle(theme=theme_name)
                        except Exception:
                            pass
                else:
                    try:
                        self.style = _TBStyle(theme=theme_name)
                    except Exception:
                        pass
            else:
                try:
                    if self.style is None:
                        self.style = ttk.Style()
                        try:
                            setattr(self.style, 'master', self.root)
                        except Exception:
                            pass
                    try:
                        self.style.theme_use(theme_name)
                    except Exception:
                        pass
                except Exception:
                    pass
            
            try:
                self.current_theme = theme_name
                self.settings['theme'] = theme_name
                save_settings(self.settings)
            except Exception:
                pass
        except Exception:
            pass

    def create_widgets(self):
        # Create canvas with scrollbar directly in root (no padding container)
        canvas = tk.Canvas(self.root, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient='vertical', command=canvas.yview)
        
        # Pack scrollbar first to ensure it's always visible
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        
        # Create scrollable frame with padding inside canvas
        scrollable_frame = tk.Frame(canvas)
        scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        
        # Create window centered with no offset, add padding to frame instead
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add padding to canvas window when canvas is resized
        def _on_canvas_configure(event):
            # Center the scrollable frame if it's narrower than canvas
            canvas_width = event.width
            frame_width = scrollable_frame.winfo_reqwidth()
            if frame_width < canvas_width:
                x_offset = (canvas_width - frame_width) // 2
                canvas.itemconfig(canvas_window, width=canvas_width)
        
        canvas.bind('<Configure>', _on_canvas_configure)
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        canvas.bind_all('<MouseWheel>', _on_mousewheel)
        
        # Add padding frame inside scrollable_frame
        padded_frame = tk.Frame(scrollable_frame)
        padded_frame.pack(fill='both', expand=True, padx=12, pady=12)
        
        # Use padded_frame for all widgets
        middle_frame = padded_frame

        # === CLICKER SECTION ===
        self.clicker_button = ttk.Button(middle_frame, text=self.locale.get('button_start_click'), command=self.toggle_clicker, width=20)
        self.clicker_button.pack(fill='x', pady=(0, 6), ipady=6)
        ToolTip(self.clicker_button, self.locale.get('tooltip_clicker', hotkey='F10'))

        # Clicker interval controls
        interval_frame = tk.Frame(middle_frame)
        interval_frame.pack(fill='x', pady=(0, 12))
        
        tk.Label(interval_frame, text=self.locale.get('label_interval_min')).pack(side='left')
        self.click_min_var = tk.IntVar(value=1)
        self.click_min_spin = tk.Spinbox(interval_frame, from_=1, to=3600, textvariable=self.click_min_var, width=6)
        self.click_min_spin.pack(side='left', padx=(6, 12))
        ToolTip(self.click_min_spin, self.locale.get('tooltip_interval_min'))
        
        tk.Label(interval_frame, text=self.locale.get('label_interval_max')).pack(side='left')
        self.click_max_var = tk.IntVar(value=20)
        self.click_max_spin = tk.Spinbox(interval_frame, from_=1, to=3600, textvariable=self.click_max_var, width=6)
        self.click_max_spin.pack(side='left', padx=(6, 6))
        ToolTip(self.click_max_spin, self.locale.get('tooltip_interval_max'))

        self.click_mode_var = tk.BooleanVar(value=False)
        self.click_mode_cb = tk.Checkbutton(interval_frame, text=self.locale.get('checkbox_use_cps'), 
                                            variable=self.click_mode_var, command=self._on_click_mode_changed)
        self.click_mode_cb.pack(side='left', padx=(12, 6))
        ToolTip(self.click_mode_cb, self.locale.get('tooltip_use_cps'))

        tk.Label(interval_frame, text=self.locale.get('label_cps')).pack(side='left')
        self.click_rate_var = tk.IntVar(value=1)
        self.click_rate_spin = tk.Spinbox(interval_frame, from_=1, to=1000, textvariable=self.click_rate_var, width=6)
        self.click_rate_spin.pack(side='left', padx=(6, 0))
        ToolTip(self.click_rate_spin, self.locale.get('tooltip_cps_rate'))
        
        # Click counter
        self.click_counter_label = tk.Label(middle_frame, text=self.locale.get('label_clicks', count=0), font=('Arial', 9))
        self.click_counter_label.pack(pady=(0, 6))
        
        # Click button type
        button_frame = tk.Frame(middle_frame)
        button_frame.pack(fill='x', pady=(0, 6))
        tk.Label(button_frame, text=self.locale.get('label_button')).pack(side='left')
        self.click_button_var = tk.StringVar(value=self.click_button)
        button_combo = ttk.Combobox(button_frame, textvariable=self.click_button_var, 
                                     values=['left', 'right', 'middle'], state='readonly', width=10)
        button_combo.pack(side='left', padx=(6, 12))
        button_combo.bind('<<ComboboxSelected>>', lambda e: button_combo.selection_clear())
        ToolTip(button_combo, self.locale.get('tooltip_button'))
        
        # Click type
        tk.Label(button_frame, text=self.locale.get('label_type')).pack(side='left')
        self.click_type_var = tk.StringVar(value=self.click_type)
        type_combo = ttk.Combobox(button_frame, textvariable=self.click_type_var,
                                  values=['single', 'double', 'triple'], state='readonly', width=10)
        type_combo.pack(side='left', padx=(6, 0))
        type_combo.bind('<<ComboboxSelected>>', lambda e: type_combo.selection_clear())
        ToolTip(type_combo, self.locale.get('tooltip_click_type'))
        
        # Click position mode
        position_frame = tk.Frame(middle_frame)
        position_frame.pack(fill='x', pady=(0, 6))
        tk.Label(position_frame, text=self.locale.get('label_position')).pack(side='left')
        self.click_position_var = tk.StringVar(value=self.click_position_mode)
        position_rb1 = tk.Radiobutton(position_frame, text=self.locale.get('label_position_current'), 
                                       variable=self.click_position_var, value='current',
                                       command=self._on_click_position_changed)
        position_rb1.pack(side='left', padx=(6, 6))
        ToolTip(position_rb1, self.locale.get('tooltip_position_current'))
        
        position_rb2 = tk.Radiobutton(position_frame, text=self.locale.get('label_position_fixed'), 
                                       variable=self.click_position_var, value='fixed',
                                       command=self._on_click_position_changed)
        position_rb2.pack(side='left', padx=(0, 6))
        ToolTip(position_rb2, self.locale.get('tooltip_position_fixed'))
        
        # Fixed position inputs
        fixed_pos_frame = tk.Frame(middle_frame)
        fixed_pos_frame.pack(fill='x', pady=(0, 6))
        tk.Label(fixed_pos_frame, text='X:').pack(side='left')
        self.click_fixed_x_var = tk.IntVar(value=self.click_fixed_x)
        self.fixed_x_spin = tk.Spinbox(fixed_pos_frame, from_=0, to=9999, 
                                        textvariable=self.click_fixed_x_var, width=6)
        self.fixed_x_spin.pack(side='left', padx=(6, 12))
        
        tk.Label(fixed_pos_frame, text='Y:').pack(side='left')
        self.click_fixed_y_var = tk.IntVar(value=self.click_fixed_y)
        self.fixed_y_spin = tk.Spinbox(fixed_pos_frame, from_=0, to=9999,
                                        textvariable=self.click_fixed_y_var, width=6)
        self.fixed_y_spin.pack(side='left', padx=(6, 12))
        
        self.pick_position_btn = ttk.Button(fixed_pos_frame, text=self.locale.get('button_pick_position'),
                                            command=self._pick_position)
        self.pick_position_btn.pack(side='left', padx=(6, 0))
        ToolTip(self.pick_position_btn, self.locale.get('tooltip_pick_position'))
        
        # Repeat mode
        repeat_frame = tk.Frame(middle_frame)
        repeat_frame.pack(fill='x', pady=(0, 12))
        tk.Label(repeat_frame, text=self.locale.get('label_repeat')).pack(side='left')
        self.click_repeat_var = tk.StringVar(value=self.click_repeat_mode)
        repeat_rb1 = tk.Radiobutton(repeat_frame, text=self.locale.get('label_repeat_infinite'), 
                                     variable=self.click_repeat_var, value='infinite',
                                     command=self._on_click_repeat_changed)
        repeat_rb1.pack(side='left', padx=(6, 6))
        ToolTip(repeat_rb1, self.locale.get('tooltip_repeat_infinite'))
        
        repeat_rb2 = tk.Radiobutton(repeat_frame, text=self.locale.get('label_repeat_count'), 
                                     variable=self.click_repeat_var, value='count',
                                     command=self._on_click_repeat_changed)
        repeat_rb2.pack(side='left', padx=(0, 6))
        ToolTip(repeat_rb2, self.locale.get('tooltip_repeat_count'))
        
        self.click_repeat_count_var = tk.IntVar(value=self.click_repeat_count)
        self.repeat_count_spin = tk.Spinbox(repeat_frame, from_=1, to=999999,
                                             textvariable=self.click_repeat_count_var, width=8)
        self.repeat_count_spin.pack(side='left', padx=(0, 0))
        ToolTip(self.repeat_count_spin, self.locale.get('tooltip_repeat_count_value'))
        
        # Phase 2: Hold Click Mode
        hold_frame = tk.Frame(middle_frame)
        hold_frame.pack(fill='x', pady=(0, 6))
        self.hold_click_var = tk.BooleanVar(value=self.hold_click_enabled)
        self.hold_click_cb = tk.Checkbutton(hold_frame, text=self.locale.get('checkbox_hold_click'), 
                                             variable=self.hold_click_var, command=self._on_hold_click_changed)
        self.hold_click_cb.pack(side='left')
        ToolTip(self.hold_click_cb, self.locale.get('tooltip_hold_click'))
        
        tk.Label(hold_frame, text=self.locale.get('label_hold_duration')).pack(side='left', padx=(12, 6))
        self.hold_duration_var = tk.DoubleVar(value=self.hold_duration)
        self.hold_duration_spin = tk.Spinbox(hold_frame, from_=0.1, to=60, increment=0.5,
                                              textvariable=self.hold_duration_var, width=6)
        self.hold_duration_spin.pack(side='left')
        ToolTip(self.hold_duration_spin, self.locale.get('tooltip_hold_duration'))
        
        # Phase 2: Random Click Area
        random_frame = tk.Frame(middle_frame)
        random_frame.pack(fill='x', pady=(0, 12))
        tk.Label(random_frame, text=self.locale.get('label_random_area')).pack(side='left')
        self.click_area_var = tk.IntVar(value=self.click_area_randomization)
        self.click_area_spin = tk.Spinbox(random_frame, from_=0, to=100,
                                          textvariable=self.click_area_var, width=6)
        self.click_area_spin.pack(side='left', padx=(6, 6))
        tk.Label(random_frame, text=self.locale.get('label_pixels')).pack(side='left')
        ToolTip(self.click_area_spin, self.locale.get('tooltip_random_area'))

        # === VERTICAL SCROLL SECTION ===
        self.start_stop_button = ttk.Button(middle_frame, text=self.locale.get('button_start_scroll'), command=self.toggle_scroll, width=20)
        self.start_stop_button.pack(fill='x', pady=(0, 6), ipady=6)
        ToolTip(self.start_stop_button, self.locale.get('tooltip_scroll', hotkey='F9'))

        self._speed_var = tk.DoubleVar(value=self.speed)
        try:
            self.speed_slider = ttk.Scale(middle_frame, from_=-100, to=100, orient='horizontal',
                                         variable=self._speed_var, command=self.update_speed)
            self.speed_slider.pack(fill='x')
        except Exception:
            self.speed_slider = tk.Scale(middle_frame, from_=-100, to=100, orient='horizontal',
                                        resolution=1, showvalue=False, command=self.update_speed)
            self.speed_slider.set(self.speed)
            self.speed_slider.pack(fill='x')
        ToolTip(self.speed_slider, self.locale.get('tooltip_scroll_speed'))

        label_frame = tk.Frame(middle_frame)
        label_frame.pack(fill='x', pady=(0, 6))
        tk.Label(label_frame, text='↓ -100').pack(side='left')
        tk.Label(label_frame, text='0').pack(side='left', expand=True)
        tk.Label(label_frame, text='100 ↑').pack(side='right')
        
        # Speed presets
        preset_frame = tk.Frame(middle_frame)
        preset_frame.pack(fill='x', pady=(0, 3))
        self.scroll_preset_slow_btn = ttk.Button(preset_frame, text=self.locale.get('button_preset_slow'), 
                   command=lambda: self._set_scroll_preset(25), width=9)
        self.scroll_preset_slow_btn.pack(side='left', padx=(0, 2))
        self.scroll_preset_normal_btn = ttk.Button(preset_frame, text=self.locale.get('button_preset_normal'), 
                   command=lambda: self._set_scroll_preset(50), width=9)
        self.scroll_preset_normal_btn.pack(side='left', padx=(2, 2))
        self.scroll_preset_fast_btn = ttk.Button(preset_frame, text=self.locale.get('button_preset_fast'), 
                   command=lambda: self._set_scroll_preset(75), width=9)
        self.scroll_preset_fast_btn.pack(side='left', padx=(2, 2))
        self.scroll_preset_ultra_btn = ttk.Button(preset_frame, text=self.locale.get('button_preset_ultra'), 
                   command=lambda: self._set_scroll_preset(100), width=9)
        self.scroll_preset_ultra_btn.pack(side='left', padx=(2, 2))
        self.scroll_preset_reset_btn = ttk.Button(preset_frame, text=self.locale.get('button_preset_reset'), 
                   command=lambda: self._set_scroll_preset(0), width=9)
        self.scroll_preset_reset_btn.pack(side='left', padx=(2, 0))
        
        # Preset direction checkbox
        preset_opt_frame = tk.Frame(middle_frame)
        preset_opt_frame.pack(fill='x', pady=(0, 6))
        self.scroll_preset_reverse_var = tk.BooleanVar(value=self.scroll_preset_reverse)
        self.scroll_preset_reverse_cb = tk.Checkbutton(preset_opt_frame, text=self.locale.get('checkbox_preset_reverse'), 
                       variable=self.scroll_preset_reverse_var)
        self.scroll_preset_reverse_cb.pack(side='left')

        # === HORIZONTAL SCROLL SECTION ===
        self.h_start_stop_button = ttk.Button(middle_frame, text=self.locale.get('button_start_h_scroll'), 
                                              command=self.toggle_h_scroll, width=20)
        self.h_start_stop_button.pack(fill='x', pady=(0, 6), ipady=6)
        ToolTip(self.h_start_stop_button, self.locale.get('tooltip_h_scroll', hotkey='F11'))

        self._h_speed_var = tk.DoubleVar(value=self.h_speed)
        try:
            self.h_speed_slider = ttk.Scale(middle_frame, from_=-100, to=100, orient='horizontal',
                                           variable=self._h_speed_var, command=self.update_h_speed)
            self.h_speed_slider.pack(fill='x')
        except Exception:
            self.h_speed_slider = tk.Scale(middle_frame, from_=-100, to=100, orient='horizontal',
                                          resolution=1, showvalue=False, command=self.update_h_speed)
            self.h_speed_slider.set(self.h_speed)
            self.h_speed_slider.pack(fill='x')
        ToolTip(self.h_speed_slider, self.locale.get('tooltip_h_scroll_speed'))

        h_label_frame = tk.Frame(middle_frame)
        h_label_frame.pack(fill='x', pady=(0, 6))
        tk.Label(h_label_frame, text='← -100').pack(side='left')
        tk.Label(h_label_frame, text='0').pack(side='left', expand=True)
        tk.Label(h_label_frame, text='100 →').pack(side='right')
        
        # Horizontal speed presets
        h_preset_frame = tk.Frame(middle_frame)
        h_preset_frame.pack(fill='x', pady=(0, 3))
        self.h_scroll_preset_slow_btn = ttk.Button(h_preset_frame, text=self.locale.get('button_preset_slow'), 
                   command=lambda: self._set_h_scroll_preset(25), width=9)
        self.h_scroll_preset_slow_btn.pack(side='left', padx=(0, 2))
        self.h_scroll_preset_normal_btn = ttk.Button(h_preset_frame, text=self.locale.get('button_preset_normal'), 
                   command=lambda: self._set_h_scroll_preset(50), width=9)
        self.h_scroll_preset_normal_btn.pack(side='left', padx=(2, 2))
        self.h_scroll_preset_fast_btn = ttk.Button(h_preset_frame, text=self.locale.get('button_preset_fast'), 
                   command=lambda: self._set_h_scroll_preset(75), width=9)
        self.h_scroll_preset_fast_btn.pack(side='left', padx=(2, 2))
        self.h_scroll_preset_ultra_btn = ttk.Button(h_preset_frame, text=self.locale.get('button_preset_ultra'), 
                   command=lambda: self._set_h_scroll_preset(100), width=9)
        self.h_scroll_preset_ultra_btn.pack(side='left', padx=(2, 2))
        self.h_scroll_preset_reset_btn = ttk.Button(h_preset_frame, text=self.locale.get('button_preset_reset'), 
                   command=lambda: self._set_h_scroll_preset(0), width=9)
        self.h_scroll_preset_reset_btn.pack(side='left', padx=(2, 0))
        
        # Horizontal preset direction checkbox
        h_preset_opt_frame = tk.Frame(middle_frame)
        h_preset_opt_frame.pack(fill='x', pady=(0, 6))
        self.h_scroll_preset_reverse_var = tk.BooleanVar(value=self.h_scroll_preset_reverse)
        self.h_scroll_preset_reverse_cb = tk.Checkbutton(h_preset_opt_frame, text=self.locale.get('checkbox_preset_reverse'), 
                       variable=self.h_scroll_preset_reverse_var)
        self.h_scroll_preset_reverse_cb.pack(side='left')

        # === AUTO TIMEOUT SECTION ===
        timeout_frame = tk.Frame(middle_frame)
        timeout_frame.pack(fill='x', pady=(12, 0))
        
        self.auto_timeout_var = tk.BooleanVar(value=self.auto_timeout_enabled)
        self.auto_timeout_cb = tk.Checkbutton(timeout_frame, text=self.locale.get('checkbox_timeout'), 
                                               variable=self.auto_timeout_var)
        self.auto_timeout_cb.pack(side='left')
        ToolTip(self.auto_timeout_cb, self.locale.get('tooltip_timeout'))
        
        tk.Label(timeout_frame, text=self.locale.get('label_timeout_delay')).pack(side='left', padx=(12, 6))
        self.auto_timeout_minutes_var = tk.IntVar(value=self.auto_timeout_minutes)
        self.auto_timeout_spin = tk.Spinbox(timeout_frame, from_=1, to=120, 
                                            textvariable=self.auto_timeout_minutes_var, width=6)
        self.auto_timeout_spin.pack(side='left')
        ToolTip(self.auto_timeout_spin, self.locale.get('tooltip_timeout_delay'))
        
        # Timeout status label
        self.timeout_status_label = tk.Label(middle_frame, text="", font=('Arial', 9), fg='blue')
        self.timeout_status_label.pack(pady=(6, 0))
        
        # === SMART PAUSE SECTION ===
        smart_pause_frame = tk.Frame(middle_frame)
        smart_pause_frame.pack(fill='x', pady=(12, 0))
        
        self.smart_pause_var = tk.BooleanVar(value=self.smart_pause_enabled)
        self.smart_pause_cb = tk.Checkbutton(smart_pause_frame, text=self.locale.get('checkbox_smart_pause'), 
                                              variable=self.smart_pause_var)
        self.smart_pause_cb.pack(side='left')
        ToolTip(self.smart_pause_cb, self.locale.get('tooltip_smart_pause'))
        
        tk.Label(smart_pause_frame, text=self.locale.get('label_smart_pause_resume')).pack(side='left', padx=(12, 6))
        self.smart_pause_seconds_var = tk.IntVar(value=self.smart_pause_seconds)
        self.smart_pause_spin = tk.Spinbox(smart_pause_frame, from_=1, to=60, 
                                           textvariable=self.smart_pause_seconds_var, width=6)
        self.smart_pause_spin.pack(side='left')
        ToolTip(self.smart_pause_spin, self.locale.get('tooltip_smart_pause_resume'))
        
        # Smart pause status label
        self.smart_pause_status_label = tk.Label(middle_frame, text="", font=('Arial', 9), fg='orange')
        self.smart_pause_status_label.pack(pady=(6, 12))  # Add bottom padding to ensure visibility

    def update_button_colors(self):
        """Update button colors based on active state."""
        try:
            # Clicker button
            if self.clicking:
                self.clicker_button.config(style='success.TButton' if _HAS_TTBOOT else '')
            else:
                self.clicker_button.config(style='TButton')
            
            # Vertical scroll button
            if self.scrolling:
                self.start_stop_button.config(style='success.TButton' if _HAS_TTBOOT else '')
            else:
                self.start_stop_button.config(style='TButton')
            
            # Horizontal scroll button
            if self.h_scrolling:
                self.h_start_stop_button.config(style='success.TButton' if _HAS_TTBOOT else '')
            else:
                self.h_start_stop_button.config(style='TButton')
        except Exception:
            pass

    # === CLICKER METHODS ===
    def toggle_clicker(self):
        if not self.clicking:
            self.start_clicker()
        else:
            self.stop_clicker()

    def start_clicker(self):
        self.clicking = True
        button_type = self.click_button_var.get()
        click_type = self.click_type_var.get()
        position_mode = self.click_position_var.get()
        interval_mode = self.locale.get('mode_cps') if self.click_mode_var.get() else self.locale.get('mode_interval')
        self._log(self.locale.get('log_clicker_started', button=button_type, type=click_type, mode=position_mode, interval_mode=interval_mode))
        try:
            self.clicker_button.config(text=self.locale.get('button_stop_click'))
        except Exception:
            pass
        self.update_button_colors()
        self.click_count = 0
        self._clicks_performed = 0
        self.update_click_counter()
        self._click_accumulator = 0.0
        try:
            self._last_click_time = time.monotonic()
        except Exception:
            self._last_click_time = None
        self._schedule_next_click()
        # Start auxiliary monitors when clicker starts
        try:
            self._start_timeout_if_needed()
        except Exception:
            pass
        try:
            self._start_smart_pause_monitoring()
        except Exception:
            pass

    def _perform_click(self, x, y, button, clicks):
        """Worker: perform the actual pyautogui click(s). Runs in background thread."""
        if not _HAS_PYAUTOGUI or pyautogui is None:
            return Exception('pyautogui unavailable')
        try:
            if button == 'middle':
                pyautogui.click(x=x, y=y, clicks=clicks, button='middle')
            else:
                pyautogui.click(x=x, y=y, clicks=clicks, button=button)
            return None
        except Exception as e:
            return e

    def _on_click_performed(self, future, clicks):
        """Callback run when click worker finishes. Schedules UI update on main thread."""
        exc = None
        try:
            res = future.result()
            if isinstance(res, Exception):
                exc = res
        except Exception as e:
            exc = e

        def _ui_update():
            if exc is None:
                try:
                    self.click_count += 1
                    self._clicks_performed += 1
                    self.update_click_counter()
                except Exception:
                    pass
            else:
                try:
                    self._log(self.locale.get('log_error_click', error=str(exc)))
                except Exception:
                    pass

        try:
            self.root.after(0, _ui_update)
        except Exception:
            _ui_update()

    def _perform_hold_click(self, x, y, button, duration):
        """Worker: perform a hold click sequence (move, mousedown, sleep, mouseup)."""
        if not _HAS_PYAUTOGUI or pyautogui is None:
            return Exception('pyautogui unavailable')
        try:
            try:
                pyautogui.moveTo(x, y)
            except Exception:
                pass
            if button == 'middle':
                pyautogui.mouseDown(x=x, y=y, button='middle')
            else:
                pyautogui.mouseDown(x=x, y=y, button=button)
            if duration and duration > 0:
                time.sleep(duration)
            if button == 'middle':
                pyautogui.mouseUp(x=x, y=y, button='middle')
            else:
                pyautogui.mouseUp(x=x, y=y, button=button)
            return None
        except Exception as e:
            return e

    def _on_hold_performed(self, future, duration):
        """Callback when hold worker finishes. Schedule UI updates and logging."""
        exc = None
        try:
            res = future.result()
            if isinstance(res, Exception):
                exc = res
        except Exception as e:
            exc = e

        def _ui_update():
            try:
                self._holding = False
                self._log(self.locale.get('log_hold_released'))
            except Exception:
                pass
            if exc is not None:
                try:
                    self._log(self.locale.get('log_error_hold_click', error=str(exc)))
                except Exception:
                    pass
            # After a hold with finite duration, schedule the next click interval
            try:
                if duration and duration > 0:
                    # Check repeat limit
                    if self.click_repeat_var.get() == 'count':
                        if self._clicks_performed >= self.click_repeat_count_var.get():
                            self._log(self.locale.get('log_click_limit', count=self._clicks_performed))
                            self.stop_clicker()
                            return
                    # Generate next interval
                    try:
                        minv = float(self.click_min_var.get())
                    except Exception:
                        minv = 1.0
                    try:
                        maxv = float(self.click_max_var.get())
                    except Exception:
                        maxv = 20.0
                    if minv <= 0:
                        minv = 1.0
                    if maxv < minv:
                        minv, maxv = maxv, minv
                    interval_s = random.uniform(minv, maxv)
                    try:
                        self._click_job = self.root.after(int(interval_s * 1000), self._do_click)
                    except Exception:
                        self._click_job = None
            except Exception:
                pass

        try:
            self.root.after(0, _ui_update)
        except Exception:
            _ui_update()
        self._start_timeout_if_needed()
        self._start_smart_pause_monitoring()

    def stop_clicker(self):
        self.clicking = False
        
        # Release held button if holding
        if self._holding and _HAS_PYAUTOGUI and pyautogui is not None:
            try:
                button = self.click_button_var.get()
                if button == 'middle':
                    pyautogui.mouseUp(button='middle')
                else:
                    pyautogui.mouseUp(button=button)
                self._log(self.locale.get('log_hold_released_stop'))
            except Exception:
                pass
            self._holding = False
        
        self._log(self.locale.get('log_clicker_stopped', count=self.click_count))
        try:
            self.clicker_button.config(text=self.locale.get('button_start_click'))
        except Exception:
            pass
        self.update_button_colors()
        if self._click_job is not None:
            try:
                self.root.after_cancel(self._click_job)
            except Exception:
                pass
            self._click_job = None
        self._check_and_stop_timeout()
        if not self.scrolling and not self.h_scrolling:
            self._stop_smart_pause_monitoring()

    def _schedule_next_click(self):
        if not self.clicking:
            return
        
        try:
            if self.click_mode_var.get():
                if self._last_click_time is None:
                    self._last_click_time = time.monotonic()
                try:
                    self._click_job = self.root.after(self._click_tick_ms, self._click_tick)
                except Exception:
                    self._click_job = None
                return
        except Exception:
            pass

        try:
            minv = float(self.click_min_var.get())
        except Exception:
            minv = 1.0
        try:
            maxv = float(self.click_max_var.get())
        except Exception:
            maxv = 20.0
        if minv <= 0:
            minv = 1.0
        if maxv < minv:
            minv, maxv = maxv, minv
        
        interval_s = random.uniform(minv, maxv)
        try:
            self._click_job = self.root.after(int(interval_s * 1000), self._do_click)
        except Exception:
            self._click_job = None

    def _click_tick(self):
        if not self.clicking:
            return
        
        # Skip tick if smart pause is active
        if self._smart_pause_active:
            try:
                self._click_job = self.root.after(self._click_tick_ms, self._click_tick)
            except Exception:
                self._click_job = None
            return
        
        try:
            now = time.monotonic()
        except Exception:
            now = None
        
        if self._last_click_time is None or now is None:
            elapsed = float(self._click_tick_ms) / 1000.0
            try:
                self._last_click_time = time.monotonic()
            except Exception:
                self._last_click_time = None
        else:
            elapsed = now - self._last_click_time
            self._last_click_time = now

        try:
            cps = float(self.click_rate_var.get())
        except Exception:
            cps = 1.0

        self._click_accumulator += cps * elapsed
        if abs(self._click_accumulator) >= 1.0:
            n = int(self._click_accumulator)
            try:
                if _ensure_pyautogui() and pyautogui is not None:
                    # Get click parameters
                    button = self.click_button_var.get()
                    click_type = self.click_type_var.get()
                    position_mode = self.click_position_var.get()
                    
                    # Determine position once for all clicks
                    if position_mode == 'fixed':
                        x = self.click_fixed_x_var.get()
                        y = self.click_fixed_y_var.get()
                    else:
                        pos = pyautogui.position()
                        x, y = pos[0], pos[1]
                    
                    # Determine clicks per action
                    clicks_per_action = 1
                    if click_type == 'double':
                        clicks_per_action = 2
                    elif click_type == 'triple':
                        clicks_per_action = 3
                    
                    for _ in range(n):
                        # Check click limit
                        if self.click_repeat_var.get() == 'count':
                            if self._clicks_performed >= self.click_repeat_count_var.get():
                                self._log(self.locale.get('log_click_limit', count=self._clicks_performed))
                                self.stop_clicker()
                                return
                        
                        try:
                            # Apply randomization to position
                            rand_x, rand_y = self._randomize_position(x, y)
                            
                            # Middle button requires special handling
                            if button == 'middle':
                                pyautogui.click(x=rand_x, y=rand_y, clicks=clicks_per_action, button='middle')
                            else:
                                pyautogui.click(x=rand_x, y=rand_y, clicks=clicks_per_action, button=button)
                            self.click_count += 1
                            self._clicks_performed += 1
                            self.update_click_counter()
                        except Exception:
                            pass
            except Exception:
                pass
            self._click_accumulator -= n

        try:
            self._click_job = self.root.after(self._click_tick_ms, self._click_tick)
        except Exception:
            self._click_job = None

    def _on_click_position_changed(self):
        """Enable/disable fixed position inputs based on mode."""
        try:
            is_fixed = self.click_position_var.get() == 'fixed'
            state = 'normal' if is_fixed else 'disabled'
            self.fixed_x_spin.configure(state=state)
            self.fixed_y_spin.configure(state=state)
            self.pick_position_btn.configure(state=state)
        except Exception:
            pass
    
    def _on_click_repeat_changed(self):
        """Enable/disable repeat count input based on mode."""
        try:
            is_count = self.click_repeat_var.get() == 'count'
            state = 'normal' if is_count else 'disabled'
            self.repeat_count_spin.configure(state=state)
        except Exception:
            pass
    
    def _pick_position(self):
        """Allow user to pick a screen position by clicking."""
        def pick_thread():
            try:
                messagebox.showinfo(self.locale.get('dialog_pick_position_title'), 
                                    self.locale.get('dialog_pick_position_text'))
                time.sleep(5)
                if _ensure_pyautogui() and pyautogui is not None:
                    pos = pyautogui.position()
                    self.click_fixed_x_var.set(pos[0])
                    self.click_fixed_y_var.set(pos[1])
                    self._log(self.locale.get('log_position_set', x=pos[0], y=pos[1]))
            except Exception as e:
                self._log(self.locale.get('log_error_pick_position', error=str(e)))
        
        import threading
        threading.Thread(target=pick_thread, daemon=True).start()
    
    def _on_click_mode_changed(self):
        try:
            if self.click_mode_var.get():
                try:
                    self.click_min_spin.configure(state='disabled')
                except Exception:
                    pass
                try:
                    self.click_max_spin.configure(state='disabled')
                except Exception:
                    pass
                try:
                    self.click_rate_spin.configure(state='normal')
                except Exception:
                    pass
            else:
                try:
                    self.click_min_spin.configure(state='normal')
                except Exception:
                    pass
                try:
                    self.click_max_spin.configure(state='normal')
                except Exception:
                    pass
                try:
                    self.click_rate_spin.configure(state='disabled')
                except Exception:
                    pass
        except Exception:
            pass
    
    def _on_hold_click_changed(self):
        """Enable/disable options when hold click mode is toggled."""
        try:
            hold_enabled = self.hold_click_var.get()
            # When hold click is enabled, disable incompatible options
            state_disabled = 'disabled' if hold_enabled else 'normal'
            
            # Disable click type (single/double/triple don't apply to hold)
            try:
                # Can't disable combobox directly, but we can make it readonly
                pass
            except Exception:
                pass
            
            # Disable CPS mode (hold doesn't use CPS)
            try:
                if hold_enabled:
                    self.click_mode_var.set(False)
                    self._on_click_mode_changed()
                    self.click_mode_cb.configure(state='disabled')
                else:
                    self.click_mode_cb.configure(state='normal')
            except Exception:
                pass
            
            # Enable/disable hold duration
            try:
                state_hold = 'normal' if hold_enabled else 'disabled'
                self.hold_duration_spin.configure(state=state_hold)
            except Exception:
                pass
        except Exception:
            pass
    
    def _randomize_position(self, x, y):
        """Add random offset to click position based on area size."""
        try:
            area = self.click_area_var.get()
            if area > 0:
                import random
                offset_x = random.randint(-area, area)
                offset_y = random.randint(-area, area)
                return x + offset_x, y + offset_y
        except Exception:
            pass
        return x, y
    
    def _do_hold_click(self):
        """Perform hold click - press and hold button for specified duration."""
        if not _HAS_PYAUTOGUI or pyautogui is None:
            self.stop_clicker()
            return
        
        try:
            # Get click parameters
            button = self.click_button_var.get()
            position_mode = self.click_position_var.get()
            duration = self.hold_duration_var.get()
            
            # Determine position
            if position_mode == 'fixed':
                x = self.click_fixed_x_var.get()
                y = self.click_fixed_y_var.get()
            else:
                pos = pyautogui.position()
                x, y = pos[0], pos[1]
            
            # Apply randomization
            x, y = self._randomize_position(x, y)
            
            # Move to position first
            # Offload move/mousedown/sleep/mouseup to background thread so UI remains responsive
            try:
                self._holding = True
                self.click_count += 1
                self._clicks_performed += 1
                self.update_click_counter()
                self._log(self.locale.get('log_hold_started', duration=duration))
                # Submit worker
                fut = self._thread_executor.submit(self._perform_hold_click, x, y, button, duration)
                fut.add_done_callback(lambda f, d=duration: self._on_hold_performed(f, d))
                # If duration == 0 => infinite hold; worker will block until externally stopped
            except Exception as e:
                # Fallback to synchronous behavior
                try:
                    try:
                        pyautogui.moveTo(x, y)
                    except Exception:
                        pass
                    if button == 'middle':
                        pyautogui.mouseDown(x=x, y=y, button='middle')
                    else:
                        pyautogui.mouseDown(x=x, y=y, button=button)
                    if duration and duration > 0:
                        time.sleep(duration)
                        if button == 'middle':
                            pyautogui.mouseUp(x=x, y=y, button='middle')
                        else:
                            pyautogui.mouseUp(x=x, y=y, button=button)
                except Exception:
                    pass
        
        except Exception as e:
            self._log(self.locale.get('log_error_hold_click', error=str(e)))
            self._holding = False
            self.stop_clicker()

    def _do_click(self):
        if not _HAS_PYAUTOGUI or pyautogui is None:
            self._schedule_next_click()
            return
        
        try:
            # Check hold click mode
            if self.hold_click_var.get():
                self._do_hold_click()
                return
            
            # Check if we've reached the click limit
            if self.click_repeat_var.get() == 'count':
                if self._clicks_performed >= self.click_repeat_count_var.get():
                    self._log(self.locale.get('log_click_limit', count=self._clicks_performed))
                    self.stop_clicker()
                    return
            
            # Get click parameters
            button = self.click_button_var.get()
            click_type = self.click_type_var.get()
            position_mode = self.click_position_var.get()
            
            # Determine position
            if position_mode == 'fixed':
                x = self.click_fixed_x_var.get()
                y = self.click_fixed_y_var.get()
            else:
                pos = pyautogui.position()
                x, y = pos[0], pos[1]
            
            # Apply randomization
            x, y = self._randomize_position(x, y)
            
            # Perform click(s) asynchronously to avoid blocking the tkinter mainloop
            clicks = 1
            if click_type == 'double':
                clicks = 2
            elif click_type == 'triple':
                clicks = 3

            try:
                # Submit the actual OS click to the thread pool; result/exception handled in callback
                future = self._thread_executor.submit(self._perform_click, x, y, button, clicks)
                future.add_done_callback(lambda f, c=clicks: self._on_click_performed(f, c))
            except Exception as e:
                # Fallback to synchronous click if executor fails
                try:
                    if button == 'middle':
                        pyautogui.click(x=x, y=y, clicks=clicks, button='middle')
                    else:
                        pyautogui.click(x=x, y=y, clicks=clicks, button=button)
                    self.click_count += 1
                    self._clicks_performed += 1
                    self.update_click_counter()
                except Exception as e2:
                    self._log(self.locale.get('log_error_click', error=str(e2)))
            
        except Exception as e:
            self._log(self.locale.get('log_error_click', error=str(e)))
        
        self._schedule_next_click()

    def update_click_counter(self):
        """Update click counter display."""
        try:
            self.click_counter_label.config(text=self.locale.get('label_clicks', count=self.click_count))
        except Exception:
            pass

    # === VERTICAL SCROLL METHODS ===
    def toggle_scroll(self):
        if not self.scrolling:
            self.start_scroll()
        else:
            self.stop_scroll()

    def start_scroll(self):
        # Arrêter le scroll horizontal si actif
        if self.h_scrolling:
            self.stop_h_scroll()
        
        self.scrolling = True
        self._log(self.locale.get('log_scroll_started', speed=self.speed))
        self.start_stop_button.config(text=self.locale.get('button_stop_scroll'))
        self.update_button_colors()
        self._accumulator = 0.0
        try:
            self._last_time = time.monotonic()
        except Exception:
            self._last_time = None
        self._schedule_next_scroll()
        self._start_timeout_if_needed()
        self._start_smart_pause_monitoring()

    def stop_scroll(self):
        self.scrolling = False
        self._log(self.locale.get('log_scroll_stopped'))
        self.start_stop_button.config(text=self.locale.get('button_start_scroll'))
        self.update_button_colors()
        if self._scroll_job is not None:
            try:
                self.root.after_cancel(self._scroll_job)
            except Exception:
                pass
            self._scroll_job = None
        # Exécuter le batch restant
        if self._scroll_batch != 0:
            if self._scroll_batch > 0:
                scroll_mouse_wheel(self._scroll_batch, 'up')
            else:
                scroll_mouse_wheel(abs(self._scroll_batch), 'down')
            self._scroll_batch = 0
        self._check_and_stop_timeout()
        if not self.clicking and not self.h_scrolling:
            self._stop_smart_pause_monitoring()

    def update_speed(self, value):
        try:
            new_speed = int(float(value))
        except Exception:
            return
        self.speed = new_speed
        if not self.scrolling:
            return
        if self.speed == 0:
            if self._scroll_job is not None:
                try:
                    self.root.after_cancel(self._scroll_job)
                except Exception:
                    pass
                self._scroll_job = None
            return
        if self._scroll_job is not None:
            try:
                self.root.after_cancel(self._scroll_job)
            except Exception:
                pass
            self._scroll_job = None
        self._schedule_next_scroll()
    
    def _set_scroll_preset(self, speed):
        """Set scroll speed to a preset value."""
        if self.scroll_preset_reverse_var.get():
            speed = -speed
        self._speed_var.set(speed)
        self.update_speed(speed)

    def _schedule_next_scroll(self):
        if not self.scrolling:
            return
        if self.speed == 0:
            return
        self._do_scroll()
        try:
            self._scroll_job = self.root.after(self._tick_ms, self._schedule_next_scroll)
        except Exception:
            self._scroll_job = None

    def _do_scroll(self):
        if self.speed == 0:
            return
        
        # Skip scroll if smart pause is active
        if self._smart_pause_active:
            return

        cps = (float(self.speed) / 100.0) * self._max_cps

        try:
            now = time.monotonic()
        except Exception:
            now = None

        if self._last_time is None or now is None:
            elapsed = float(self._tick_ms) / 1000.0
            try:
                self._last_time = time.monotonic()
            except Exception:
                self._last_time = None
        else:
            elapsed = now - self._last_time
            self._last_time = now

        delta = cps * elapsed
        self._accumulator += delta

        if abs(self._accumulator) >= 1.0:
            n = int(self._accumulator)
            self._scroll_batch += n
            self._accumulator -= n
            
            # Exécuter le batch tous les 10 scrolls pour réduire les appels pyautogui
            if abs(self._scroll_batch) >= 10:
                if self._scroll_batch > 0:
                    scroll_mouse_wheel(self._scroll_batch, 'up')
                elif self._scroll_batch < 0:
                    scroll_mouse_wheel(abs(self._scroll_batch), 'down')
                self._scroll_batch = 0

    # === HORIZONTAL SCROLL METHODS ===
    def toggle_h_scroll(self):
        if not self.h_scrolling:
            self.start_h_scroll()
        else:
            self.stop_h_scroll()

    def start_h_scroll(self):
        # Arrêter le scroll vertical si actif
        if self.scrolling:
            self.stop_scroll()
        
        self.h_scrolling = True
        self._log(self.locale.get('log_h_scroll_started', speed=self.h_speed))
        self.h_start_stop_button.config(text=self.locale.get('button_stop_h_scroll'))
        self.update_button_colors()
        self._h_accumulator = 0.0
        try:
            self._h_last_time = time.monotonic()
        except Exception:
            self._h_last_time = None
        self._schedule_next_h_scroll()
        self._start_timeout_if_needed()
        self._start_smart_pause_monitoring()

    def stop_h_scroll(self):
        self.h_scrolling = False
        self._log(self.locale.get('log_h_scroll_stopped'))
        self.h_start_stop_button.config(text=self.locale.get('button_start_h_scroll'))
        self.update_button_colors()
        if self._h_scroll_job is not None:
            try:
                self.root.after_cancel(self._h_scroll_job)
            except Exception:
                pass
            self._h_scroll_job = None
        # Exécuter le batch restant
        if self._h_scroll_batch != 0:
            if _ensure_pyautogui() and pyautogui is not None:
                try:
                    pyautogui.keyDown('shift')
                    pyautogui.scroll(self._h_scroll_batch)
                    pyautogui.keyUp('shift')
                except Exception:
                    pass
            self._h_scroll_batch = 0
        self._check_and_stop_timeout()
        if not self.clicking and not self.scrolling:
            self._stop_smart_pause_monitoring()

    def update_h_speed(self, value):
        try:
            new_speed = int(float(value))
        except Exception:
            return
        self.h_speed = new_speed
        if not self.h_scrolling:
            return
        if self.h_speed == 0:
            if self._h_scroll_job is not None:
                try:
                    self.root.after_cancel(self._h_scroll_job)
                except Exception:
                    pass
                self._h_scroll_job = None
            return
        if self._h_scroll_job is not None:
            try:
                self.root.after_cancel(self._h_scroll_job)
            except Exception:
                pass
            self._h_scroll_job = None
        self._schedule_next_h_scroll()
    
    def _set_h_scroll_preset(self, speed):
        """Set horizontal scroll speed to a preset value."""
        if self.h_scroll_preset_reverse_var.get():
            speed = -speed
        self._h_speed_var.set(speed)
        self.update_h_speed(speed)

    def _schedule_next_h_scroll(self):
        if not self.h_scrolling:
            return
        if self.h_speed == 0:
            return
        self._do_h_scroll()
        try:
            self._h_scroll_job = self.root.after(self._tick_ms, self._schedule_next_h_scroll)
        except Exception:
            self._h_scroll_job = None

    def _do_h_scroll(self):
        if self.h_speed == 0:
            return
        
        # Skip scroll if smart pause is active
        if self._smart_pause_active:
            return

        cps = (float(self.h_speed) / 100.0) * self._max_cps

        try:
            now = time.monotonic()
        except Exception:
            now = None

        if not hasattr(self, '_h_last_time') or self._h_last_time is None or now is None:
            elapsed = float(self._tick_ms) / 1000.0
            try:
                self._h_last_time = time.monotonic()
            except Exception:
                self._h_last_time = None
        else:
            elapsed = now - self._h_last_time
            self._h_last_time = now

        delta = cps * elapsed
        self._h_accumulator += delta

        if abs(self._h_accumulator) >= 1.0:
            n = int(self._h_accumulator)
            self._h_scroll_batch += n
            self._h_accumulator -= n
            
            # Exécuter le batch tous les 10 scrolls pour réduire drastiquement les appels keyDown/keyUp
            if abs(self._h_scroll_batch) >= 10:
                if _HAS_PYAUTOGUI and pyautogui is not None:
                    try:
                        # Un seul appel keyDown/keyUp pour tout le batch
                        pyautogui.keyDown('shift')
                        pyautogui.scroll(self._h_scroll_batch)
                        pyautogui.keyUp('shift')
                    except Exception:
                        pass
                
                self._h_scroll_batch = 0

    # === UI PREFERENCES METHODS ===
    def toggle_always_on_top(self):
        """Toggle always on top window attribute."""
        self.always_on_top = self.always_on_top_var.get()
        self.save_ui_state()
        
        try:
            self.root.attributes('-topmost', self.always_on_top)
            status = self.locale.get('status_enabled') if self.always_on_top else self.locale.get('status_disabled')
            self._log(self.locale.get('log_always_on_top', status=status))
        except Exception as e:
            self._log(self.locale.get('log_error_always_on_top', error=str(e)))
    
    def toggle_logging(self):
        """Toggle logging on/off."""
        self.logging_enabled = self.logging_var.get()
        self.save_ui_state()
        
        if self.logging_enabled:
            self._init_logging()
            self._log("=" * 50)
            self._log(self.locale.get('log_logging_enabled'))
            self._log(f"Version: {APP_VERSION}")
            self._log("=" * 50)
        else:
            self._log(self.locale.get('log_logging_disabled'))
            self._close_logging()
    
    def _init_logging(self):
        """Initialize logging to file."""
        try:
            import datetime
            import glob
            logs_dir = os.path.join(os.path.dirname(_settings_path()), 'logs')
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir)
            
            # Clean up old log files (keep only 3 most recent)
            log_files = sorted(glob.glob(os.path.join(logs_dir, 'autoscroller_*.log')))
            while len(log_files) >= 3:
                oldest_file = log_files.pop(0)
                try:
                    os.remove(oldest_file)
                except Exception:
                    pass
            
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            log_filename = f'autoscroller_{timestamp}.log'
            log_path = os.path.join(logs_dir, log_filename)
            
            self._log_file = open(log_path, 'w', encoding='utf-8')
            self._log_path = log_path
        except Exception as e:
            print(self.locale.get('log_error_init_logging', error=str(e)))
            self._log_file = None
    
    def _close_logging(self):
        """Close logging file."""
        if self._log_file is not None:
            try:
                self._log_file.close()
            except Exception:
                pass
            self._log_file = None
    
    def _log(self, message):
        """Write message to log file if logging is enabled."""
        if not self.logging_enabled or self._log_file is None:
            return
        
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            log_line = f"[{timestamp}] {message}\n"
            self._log_file.write(log_line)
            self._log_file.flush()
        except Exception as e:
            print(self.locale.get('log_error_write_log', error=str(e)))
    
    def open_logs_folder(self):
        """Open the logs folder in file explorer."""
        try:
            logs_dir = os.path.join(os.path.dirname(_settings_path()), 'logs')
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir)
            
            # Open folder based on OS
            import subprocess
            import platform
            
            if platform.system() == 'Windows':
                os.startfile(logs_dir)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.Popen(['open', logs_dir])
            else:  # Linux
                subprocess.Popen(['xdg-open', logs_dir])
            
            self._log(self.locale.get('log_logs_opened', path=logs_dir))
        except Exception as e:
            self._log(self.locale.get('log_error_open_logs', error=str(e)))
            messagebox.showerror(self.locale.get('dialog_error'), self.locale.get('log_error_open_logs', error=str(e)))
    
    # === PROFILE MANAGEMENT METHODS ===
    def _profiles_path(self):
        """Get path to profiles file."""
        return os.path.join(os.path.dirname(_settings_path()), 'profiles.json')
    
    def _load_profiles(self):
        """Load all saved profiles."""
        try:
            if os.path.exists(self._profiles_path()):
                with open(self._profiles_path(), 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self._log(self.locale.get('log_error_load_profiles', error=str(e)))
        return {}
    
    def _save_profiles(self, profiles):
        """Save all profiles to file."""
        try:
            with open(self._profiles_path(), 'w', encoding='utf-8') as f:
                json.dump(profiles, f, indent=2)
        except Exception as e:
            self._log(self.locale.get('log_error_save_profiles', error=str(e)))
    
    def _get_current_config(self):
        """Get current configuration as a profile."""
        return {
            'click_min': self.click_min_var.get(),
            'click_max': self.click_max_var.get(),
            'click_rate': self.click_rate_var.get(),
            'click_mode_cps': self.click_mode_var.get(),
            'click_button': self.click_button_var.get(),
            'click_type': self.click_type_var.get(),
            'click_position_mode': self.click_position_var.get(),
            'click_fixed_x': self.click_fixed_x_var.get(),
            'click_fixed_y': self.click_fixed_y_var.get(),
            'click_repeat_mode': self.click_repeat_var.get(),
            'click_repeat_count': self.click_repeat_count_var.get(),
            'hold_click_enabled': self.hold_click_var.get() if hasattr(self, 'hold_click_var') else False,
            'hold_duration': self.hold_duration_var.get() if hasattr(self, 'hold_duration_var') else 1.0,
            'click_area_randomization': self.click_area_var.get() if hasattr(self, 'click_area_var') else 0,
            'scroll_speed': self.speed,
            'h_scroll_speed': self.h_speed,
            'auto_timeout_enabled': self.auto_timeout_var.get(),
            'auto_timeout_minutes': self.auto_timeout_minutes_var.get(),
            'smart_pause_enabled': self.smart_pause_var.get(),
            'smart_pause_seconds': self.smart_pause_seconds_var.get(),
        }
    
    def _apply_config(self, config):
        """Apply a configuration profile."""
        try:
            if 'click_min' in config:
                self.click_min_var.set(config['click_min'])
            if 'click_max' in config:
                self.click_max_var.set(config['click_max'])
            if 'click_rate' in config:
                self.click_rate_var.set(config['click_rate'])
            if 'click_mode_cps' in config:
                self.click_mode_var.set(config['click_mode_cps'])
            if 'click_button' in config:
                self.click_button_var.set(config['click_button'])
            if 'click_type' in config:
                self.click_type_var.set(config['click_type'])
            if 'click_position_mode' in config:
                self.click_position_var.set(config['click_position_mode'])
            if 'click_fixed_x' in config:
                self.click_fixed_x_var.set(config['click_fixed_x'])
            if 'click_fixed_y' in config:
                self.click_fixed_y_var.set(config['click_fixed_y'])
            if 'click_repeat_mode' in config:
                self.click_repeat_var.set(config['click_repeat_mode'])
            if 'click_repeat_count' in config:
                self.click_repeat_count_var.set(config['click_repeat_count'])
            if 'hold_click_enabled' in config and hasattr(self, 'hold_click_var'):
                self.hold_click_var.set(config['hold_click_enabled'])
            if 'hold_duration' in config and hasattr(self, 'hold_duration_var'):
                self.hold_duration_var.set(config['hold_duration'])
            if 'click_area_randomization' in config and hasattr(self, 'click_area_var'):
                self.click_area_var.set(config['click_area_randomization'])
            if 'scroll_speed' in config:
                self.speed = config['scroll_speed']
                self._speed_var.set(self.speed)
            if 'h_scroll_speed' in config:
                self.h_speed = config['h_scroll_speed']
                self._h_speed_var.set(self.h_speed)
            if 'auto_timeout_enabled' in config:
                self.auto_timeout_var.set(config['auto_timeout_enabled'])
            if 'auto_timeout_minutes' in config:
                self.auto_timeout_minutes_var.set(config['auto_timeout_minutes'])
            if 'smart_pause_enabled' in config:
                self.smart_pause_var.set(config['smart_pause_enabled'])
            if 'smart_pause_seconds' in config:
                self.smart_pause_seconds_var.set(config['smart_pause_seconds'])
            
            # Update UI states
            self._on_click_mode_changed()
            self._on_click_position_changed()
            self._on_click_repeat_changed()
            if hasattr(self, '_on_hold_click_changed'):
                self._on_hold_click_changed()
        except Exception as e:
            self._log(self.locale.get('log_error_apply_config', error=str(e)))
    
    def save_profile_as(self):
        """Save current configuration as a named profile."""
        dialog = tk.Toplevel(self.root)
        dialog.title(self.locale.get('dialog_profile_save_title'))
        dialog.transient(self.root)
        dialog.grab_set()
        self._position_dialog(dialog, 450, 180)
        
        tk.Label(dialog, text=self.locale.get('dialog_profile_save_label'), font=('Arial', 10)).pack(pady=10)
        
        name_entry = tk.Entry(dialog, width=30)
        name_entry.pack(pady=5)
        name_entry.focus()
        
        def do_save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning(self.locale.get('dialog_warning'), self.locale.get('dialog_profile_save_warning'))
                return
            
            profiles = self._load_profiles()
            profiles[name] = self._get_current_config()
            self._save_profiles(profiles)
            
            self.current_profile = name
            self._log(self.locale.get('log_profile_saved', name=name))
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text=self.locale.get('button_save'), command=do_save).pack(side='left', padx=5)
        tk.Button(btn_frame, text=self.locale.get('button_cancel'), command=dialog.destroy).pack(side='left', padx=5)
        
        name_entry.bind('<Return>', lambda e: do_save())
    
    def load_profile(self):
        """Load a saved profile."""
        profiles = self._load_profiles()
        
        if not profiles:
            messagebox.showinfo(self.locale.get('dialog_info'), self.locale.get('dialog_profile_load_none'))
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title(self.locale.get('dialog_profile_load_title'))
        dialog.transient(self.root)
        dialog.grab_set()
        self._position_dialog(dialog, 450, 350)
        
        tk.Label(dialog, text=self.locale.get('dialog_profile_load_label'), font=('Arial', 10, 'bold')).pack(pady=10)
        
        listbox = tk.Listbox(dialog, height=8)
        listbox.pack(fill='both', expand=True, padx=20, pady=5)
        
        for name in sorted(profiles.keys()):
            listbox.insert(tk.END, name)
        
        def do_load():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning(self.locale.get('dialog_warning'), self.locale.get('dialog_profile_load_warning'))
                return
            
            name = listbox.get(selection[0])
            self._apply_config(profiles[name])
            self.current_profile = name
            self._log(self.locale.get('log_profile_loaded', name=name))
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text=self.locale.get('button_load'), command=do_load).pack(side='left', padx=5)
        tk.Button(btn_frame, text=self.locale.get('button_cancel'), command=dialog.destroy).pack(side='left', padx=5)
        
        listbox.bind('<Double-Button-1>', lambda e: do_load())
    
    def manage_profiles(self):
        """Manage saved profiles (delete, rename, etc)."""
        profiles = self._load_profiles()
        
        if not profiles:
            messagebox.showinfo(self.locale.get('dialog_info'), self.locale.get('dialog_profile_load_none'))
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title(self.locale.get('dialog_profile_manage_title'))
        dialog.transient(self.root)
        dialog.grab_set()
        self._position_dialog(dialog, 500, 400)
        
        tk.Label(dialog, text=self.locale.get('dialog_profile_manage_label'), font=('Arial', 10, 'bold')).pack(pady=10)
        
        listbox = tk.Listbox(dialog, height=10)
        listbox.pack(fill='both', expand=True, padx=20, pady=5)
        
        def refresh_list():
            listbox.delete(0, tk.END)
            for name in sorted(profiles.keys()):
                listbox.insert(tk.END, name)
        
        refresh_list()
        
        def delete_profile():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning(self.locale.get('dialog_warning'), self.locale.get('dialog_profile_load_warning'))
                return
            
            name = listbox.get(selection[0])
            if messagebox.askyesno(self.locale.get('dialog_confirm'), self.locale.get('dialog_profile_manage_confirm', name=name)):
                del profiles[name]
                self._save_profiles(profiles)
                refresh_list()
                self._log(self.locale.get('log_profile_deleted', name=name))
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text=self.locale.get('button_delete'), command=delete_profile).pack(side='left', padx=5)
        tk.Button(btn_frame, text=self.locale.get('button_close'), command=dialog.destroy).pack(side='left', padx=5)
    
    # === SMART PAUSE METHODS ===
    def _start_smart_pause_monitoring(self):
        """Start monitoring mouse movement for smart pause."""
        try:
            if not self.smart_pause_var.get():
                return
            
            # Only monitor if something is active
            if not self.clicking and not self.scrolling and not self.h_scrolling:
                return
            
            # Get current mouse position
            try:
                if not _ensure_pyautogui() or pyautogui is None:
                    return
                current_pos = pyautogui.position()
            except Exception:
                return
            
            # Check if mouse moved
            if self._last_mouse_pos is not None:
                if current_pos != self._last_mouse_pos:
                    # Mouse moved - activate pause if not already active
                    if not self._smart_pause_active:
                        self._activate_smart_pause()
                    self._mouse_inactive_start = None
                else:
                    # Mouse didn't move
                    if self._smart_pause_active:
                        # Start counting inactivity if not started
                        if self._mouse_inactive_start is None:
                            self._mouse_inactive_start = time.monotonic()
                        else:
                            # Check if enough time has passed
                            elapsed = time.monotonic() - self._mouse_inactive_start
                            if elapsed >= self.smart_pause_seconds_var.get():
                                self._deactivate_smart_pause()
            
            self._last_mouse_pos = current_pos
            
            # Continue monitoring
            try:
                self._smart_pause_check_job = self.root.after(100, self._start_smart_pause_monitoring)
            except Exception:
                self._smart_pause_check_job = None
        except Exception:
            pass
    
    def _activate_smart_pause(self):
        """Pause all activities due to mouse movement."""
        self._smart_pause_active = True
        self._paused_clicking = self.clicking
        self._paused_scrolling = self.scrolling
        self._paused_h_scrolling = self.h_scrolling
        
        if self.clicking:
            self._pause_clicker()
        if self.scrolling:
            self._pause_scroll()
        if self.h_scrolling:
            self._pause_h_scroll()
        
        # Réinitialiser les timers pour éviter l'accumulation de temps
        self._last_time = None
        self._h_last_time = None
        self._last_click_time = None
        
        self._log(self.locale.get('log_smart_pause_activated'))
        try:
            self.smart_pause_status_label.config(text=self.locale.get('status_smart_pause_active'))
        except Exception:
            pass
    
    def _deactivate_smart_pause(self):
        """Resume activities after mouse inactivity."""
        self._smart_pause_active = False
        self._mouse_inactive_start = None
        
        # Réinitialiser les timers avant la reprise
        try:
            self._last_time = time.monotonic()
        except Exception:
            self._last_time = None
        try:
            self._h_last_time = time.monotonic()
        except Exception:
            self._h_last_time = None
        try:
            self._last_click_time = time.monotonic()
        except Exception:
            self._last_click_time = None
        
        if hasattr(self, '_paused_clicking') and self._paused_clicking:
            self._resume_clicker()
        if hasattr(self, '_paused_scrolling') and self._paused_scrolling:
            self._resume_scroll()
        if hasattr(self, '_paused_h_scrolling') and self._paused_h_scrolling:
            self._resume_h_scroll()
        
        self._log(self.locale.get('log_smart_pause_deactivated'))
        try:
            self.smart_pause_status_label.config(text="")
        except Exception:
            pass
    
    def _stop_smart_pause_monitoring(self):
        """Stop smart pause monitoring."""
        if self._smart_pause_check_job is not None:
            try:
                self.root.after_cancel(self._smart_pause_check_job)
            except Exception:
                pass
            self._smart_pause_check_job = None
        
        self._last_mouse_pos = None
        self._mouse_inactive_start = None
        
        if self._smart_pause_active:
            self._deactivate_smart_pause()

    # (smart pause toggle handler removed to restore previous behavior)
    
    def _pause_clicker(self):
        """Pause clicker without changing clicking state."""
        if self._click_job is not None:
            try:
                self.root.after_cancel(self._click_job)
            except Exception:
                pass
            self._click_job = None
    
    def _resume_clicker(self):
        """Resume clicker."""
        if self.clicking:
            self._schedule_next_click()
    
    def _pause_scroll(self):
        """Pause scroll without changing scrolling state."""
        if self._scroll_job is not None:
            try:
                self.root.after_cancel(self._scroll_job)
            except Exception:
                pass
            self._scroll_job = None
    
    def _resume_scroll(self):
        """Resume scroll."""
        if self.scrolling:
            self._schedule_next_scroll()
    
    def _pause_h_scroll(self):
        """Pause horizontal scroll without changing h_scrolling state."""
        if self._h_scroll_job is not None:
            try:
                self.root.after_cancel(self._h_scroll_job)
            except Exception:
                pass
            self._h_scroll_job = None
    
    def _resume_h_scroll(self):
        """Resume horizontal scroll."""
        if self.h_scrolling:
            self._schedule_next_h_scroll()
    
    # === AUTO TIMEOUT METHODS ===
    def _start_timeout_if_needed(self):
        """Start timeout timer if enabled and not already running."""
        try:
            if not self.auto_timeout_var.get():
                return
            
            # Si aucune activité n'est en cours, ne pas démarrer le timeout
            if not self.clicking and not self.scrolling and not self.h_scrolling:
                return
            
            # Si le timeout est déjà actif, ne pas le redémarrer
            if self._timeout_job is not None:
                return
            
            # Démarrer le timeout
            try:
                self._timeout_start_time = time.monotonic()
            except Exception:
                self._timeout_start_time = None
            
            self._check_timeout()
        except Exception:
            pass

    def _check_timeout(self):
        """Check if timeout has expired and stop all activities."""
        try:
            if self._timeout_start_time is None:
                return
            
            # Si plus rien n'est actif, arrêter le timeout
            if not self.clicking and not self.scrolling and not self.h_scrolling:
                self._stop_timeout()
                return
            
            try:
                elapsed = time.monotonic() - self._timeout_start_time
            except Exception:
                elapsed = 0
            
            timeout_seconds = self.auto_timeout_minutes_var.get() * 60
            remaining = timeout_seconds - elapsed
            
            if remaining <= 0:
                # Timeout expiré, arrêter tout
                self._on_timeout_expired()
                return
            
            # Afficher le temps restant
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            try:
                self.timeout_status_label.config(text=self.locale.get('status_timeout_remaining', mins=mins, secs=secs))
            except Exception:
                pass
            
            # Vérifier à nouveau dans 2 secondes (réduit la charge)
            try:
                self._timeout_job = self.root.after(2000, self._check_timeout)
            except Exception:
                self._timeout_job = None
        except Exception:
            pass

    def _on_timeout_expired(self):
        """Called when timeout expires - stop all activities."""
        try:
            if self.clicking:
                self.stop_clicker()
        except Exception:
            pass
        try:
            if self.scrolling:
                self.stop_scroll()
        except Exception:
            pass
        try:
            if self.h_scrolling:
                self.stop_h_scroll()
        except Exception:
            pass
        
        try:
            self.timeout_status_label.config(text=self.locale.get('status_timeout_expired'))
        except Exception:
            pass
        
        self._stop_timeout()

    def _stop_timeout(self):
        """Stop the timeout timer."""
        if self._timeout_job is not None:
            try:
                self.root.after_cancel(self._timeout_job)
            except Exception:
                pass
            self._timeout_job = None
        
        self._timeout_start_time = None
        
        try:
            self.timeout_status_label.config(text="")
        except Exception:
            pass

    def _check_and_stop_timeout(self):
        """Check if all activities are stopped and stop timeout if so."""
        try:
            if not self.clicking and not self.scrolling and not self.h_scrolling:
                self._stop_timeout()
        except Exception:
            pass

    # === GLOBAL LISTENERS ===
    def _start_global_listeners(self):
        """Start both mouse and keyboard global listeners."""
        if _ensure_pynput_mouse() is not None:
            try:
                self._start_global_mouse_listener()
            except Exception:
                pass
        
        if _ensure_pynput_keyboard() and _pynput_keyboard is not None:
            try:
                self._start_keyboard_listener()
            except Exception:
                pass

    def _start_global_mouse_listener(self):
        """Mouse listener no longer used - emergency stop now uses space key."""
        # Kept for potential future use
        pass

    def _start_keyboard_listener(self):
        """Start global keyboard listener for hotkeys."""
        if not _ensure_pynput_keyboard() or _pynput_keyboard is None:
            return
        
        def on_press(key):
            try:
                # Check for emergency stop (space bar)
                key_str = None
                try:
                    if hasattr(key, 'char') and key.char is not None:
                        key_str = key.char.lower()
                    elif hasattr(key, 'name'):
                        key_str = key.name.lower()
                except Exception:
                    pass
                
                if key_str == 'space' or key_str == ' ':
                    try:
                        self.root.after(0, self._on_safety_right_click)
                    except Exception:
                        pass
                    return
                
                # Check other hotkeys
                key_str = None
                if hasattr(key, 'name'):
                    key_str = key.name
                elif hasattr(key, 'char'):
                    key_str = key.char
                else:
                    key_str = str(key)
                
                # Normalize and compare keys exactly
                if key_str:
                    key_str = key_str.lower().replace('key.', '').replace('<', '').replace('>', '')
                    scroll_key = self.hotkeys.get('toggle_scroll', '').lower()
                    click_key = self.hotkeys.get('toggle_click', '').lower()
                    h_scroll_key = self.hotkeys.get('toggle_h_scroll', '').lower()
                    
                    # Exact match comparison
                    if scroll_key and key_str == scroll_key:
                        self.toggle_scroll()
                    elif click_key and key_str == click_key:
                        self.toggle_clicker()
                    elif h_scroll_key and key_str == h_scroll_key:
                        self.toggle_h_scroll()
            except Exception:
                pass
        
        try:
            self._keyboard_listener = _pynput_keyboard.Listener(on_press=on_press)
            self._keyboard_listener.start()
        except Exception:
            self._keyboard_listener = None

    def _stop_global_listener(self):
        try:
            if self._global_listener is not None:
                try:
                    stop_fn = getattr(self._global_listener, 'stop', None)
                    if callable(stop_fn):
                        stop_fn()
                except Exception:
                    pass
                self._global_listener = None
        except Exception:
            pass

    def _stop_keyboard_listener(self):
        try:
            if self._keyboard_listener is not None:
                try:
                    stop_fn = getattr(self._keyboard_listener, 'stop', None)
                    if callable(stop_fn):
                        stop_fn()
                except Exception:
                    pass
                self._keyboard_listener = None
        except Exception:
            pass

    def _on_safety_right_click(self, event=None):
        """Safety handler: stop everything when right-click detected."""
        try:
            if self.clicking:
                self.stop_clicker()
        except Exception:
            pass
        try:
            if self.scrolling:
                self.stop_scroll()
        except Exception:
            pass
        try:
            if self.h_scrolling:
                self.stop_h_scroll()
        except Exception:
            pass

    def _on_close(self):
        """Cleanup and save state on window close."""
        try:
            self.stop_clicker()
        except Exception:
            pass
        try:
            self.stop_scroll()
        except Exception:
            pass
        try:
            self.stop_h_scroll()
        except Exception:
            pass
        try:
            self._stop_global_listener()
        except Exception:
            pass
        try:
            self._stop_keyboard_listener()
        except Exception:
            pass
        try:
            self._stop_smart_pause_monitoring()
        except Exception:
            pass
        try:
            self._log(self.locale.get('log_app_closing'))
            self._close_logging()
        except Exception:
            pass
        try:
            self.save_ui_state()
        except Exception:
            pass
        try:
            # Shutdown executors gracefully
            try:
                if hasattr(self, '_thread_executor') and self._thread_executor is not None:
                    self._thread_executor.shutdown(wait=False)
            except Exception:
                pass
            try:
                if hasattr(self, '_process_executor') and self._process_executor is not None:
                    self._process_executor.shutdown(wait=False)
            except Exception:
                pass
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    # Required for multiprocessing on Windows when frozen with PyInstaller
    try:
        multiprocessing.freeze_support()
    except Exception:
        pass
    settings = load_settings()
    theme = settings.get('theme', 'flatly')
    style = None
    root = None
    
    # Try ttkbootstrap first if available
    if _HAS_TTBOOT and _TBStyle is not None:
        try:
            style = _TBStyle(theme=theme)
            root = getattr(style, 'master', None)
        except Exception:
            pass
    
    # Fallback to standard tkinter
    if root is None:
        root = tk.Tk()
    
    # Set application icon
    try:
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            icon_path = os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))), 'icon.ico')
        else:
            # Running as script
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass
    
    # Center the window on screen
    window_width = 900
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Set a fixed height that's sufficient for all content (increased from 1000)
    window_height = min(1050, int(screen_height * 0.85))
    
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f'{window_width}x{window_height}+{x}+{y}')
    
    # Allow window resizing
    root.resizable(True, True)
    
    # Set minimum size to prevent too small windows
    root.minsize(400, 300)
    
    try:
        app = AutoScroller(root, style)
        root.mainloop()
    except Exception:
        tb = traceback.format_exc()
        try:
            messagebox.showerror('Autoscroller Error', f'An error occurred:\n\n{tb}')
        except Exception:
            print(tb)
