import sys
import os
import logging
import ctypes # Access to Windows DWM API
try:
    import qdarktheme
except ImportError:
    qdarktheme = None
try:
    import darkdetect
except ImportError:
    darkdetect = None
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QDoubleSpinBox, QComboBox, QPushButton, QFormLayout, 
    QKeySequenceEdit, QGroupBox, QMessageBox, QCheckBox, QInputDialog, QToolButton,
    QStyle, QSystemTrayIcon, QMenu, QDialog
)
from PyQt6.QtCore import pyqtSignal, pyqtSlot, Qt, QSize, QEvent, QUrl, QTimer
from PyQt6.QtGui import QKeySequence, QIcon, QCloseEvent, QAction, QDesktopServices, QFont
from pynput import keyboard

from src.core.version import APP_VERSION, GITHUB_REPO

# Adjust path so we can import from src
try:
    from src.engine.clicker import Clicker
    from src.engine.scroller import Scroller
    from src.core.config_manager import ConfigManager
    from src.gui.overlay_window import OverlayWindow
    from src.core.updater import UpdateChecker
    from src.gui.settings_dialog import SettingsDialog
except ImportError:
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    from src.engine.clicker import Clicker
    from src.engine.scroller import Scroller
    from src.core.config_manager import ConfigManager
    from src.gui.overlay_window import OverlayWindow
    from src.core.updater import UpdateChecker
    from src.gui.settings_dialog import SettingsDialog

class AboutDialog(QDialog):
    def __init__(self, parent=None, updater=None):
        super().__init__(parent)
        self.setWindowTitle("About FlowScroll")
        self.updater = updater
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(300, 300)
        layout = QVBoxLayout(self)
        
        # Title
        label_title = QLabel(f"FlowScroll v{APP_VERSION}")
        label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = label_title.font()
        font.setPointSize(14)
        font.setBold(True)
        label_title.setFont(font)
        layout.addWidget(label_title)

        # Description
        label_desc = QLabel("Auto-Clicker & Auto-Scroller")
        label_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label_desc)
        
        layout.addSpacing(10)

        # Check Update Button
        self.btn_check_update = QPushButton("Check for Updates")
        self.btn_check_update.clicked.connect(self.check_update)
        layout.addWidget(self.btn_check_update)
        
        # Status Label
        self.label_status = QLabel("")
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_status.setStyleSheet("color: #888;")
        layout.addWidget(self.label_status)

        layout.addStretch()

        # GitHub Link
        label_link = QLabel(f"<a href='https://github.com/{GITHUB_REPO}'>GitHub Repository</a>")
        label_link.setOpenExternalLinks(True)
        label_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label_link)
        
        # Close Button
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def check_update(self):
        if not self.updater:
            self.label_status.setText("Updater not initialized.")
            return

        self.label_status.setText("Checking...")
        self.btn_check_update.setEnabled(False)
        
        # Connect signal first
        self.updater.check_finished.connect(self.on_check_finished)
        
        if not self.updater.isRunning():
            self.updater.start()

    def on_check_finished(self, found, version, url):
        self.btn_check_update.setEnabled(True)
        if self.updater:
            try:
                 self.updater.check_finished.disconnect(self.on_check_finished)
            except TypeError: pass

        if found:
            self.label_status.setText(f"Update available: {version}")
            reply = QMessageBox.question(
                self, "Update Available",
                f"Version {version} is available. Download now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl(url))
        else:
            if version: # version string exists means check succeeded but no update
                self.label_status.setText("You are up to date.")
            else:
                 self.label_status.setText("Check failed (No internet?)")

class MainWindow(QMainWindow):
    # Signals to handle hotkey events from non-GUI thread
    toggle_clicker_signal = pyqtSignal()
    toggle_scroller_signal = pyqtSignal()
    MAX_DELAY_SECONDS = 999999.0

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"FlowScroll v{APP_VERSION}")
        self.resize(400, 500)

        # Set Window Icon
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        else:
            # Running from source
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        
        icon_path = os.path.join(base_path, 'assets', 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            logging.warning(f"Icon not found at {icon_path}")

        # Initialize ConfigManager
        self.config_manager = ConfigManager()
        self.settings = self.config_manager.settings
        self.profiles = self.config_manager.profiles

        # Apply Theme and Title Bar Color
        current_theme = self.settings.get("theme", "dark")
        self.change_theme(current_theme)

        # Engine instances
        self.clicker = Clicker()
        self.scroller = Scroller()
        self.clicker_state = "idle"
        self.scroller_state = "idle"
        self.clicker_count = 0
        self.scroller_count = 0
        
        # Overlay
        self.overlay = OverlayWindow()
        # Ensure overlay state matches settings (default hidden)
        if self.settings.get("enable_overlay", False):
            self.overlay.show()
        else:
            self.overlay.hide()
        
        # Connect engine signals
        self.clicker.stats_updated.connect(self.on_clicker_stats)
        self.scroller.stats_updated.connect(self.on_scroller_stats)
        self.clicker.state_changed.connect(self.on_clicker_state_changed)
        self.scroller.state_changed.connect(self.on_scroller_state_changed)
        self.clicker.finished.connect(self.on_clicker_finished)
        self.scroller.finished.connect(self.on_scroller_finished)

        # UI Setup
        self.init_ui()
        
        # Load Settings to UI
        self.load_settings_to_ui()
        self.refresh_clicker_status()
        self.refresh_scroller_status()

        # Update engines with initial settings
        self.update_clicker_settings()
        self.update_scroller_settings()

        # Hotkeys
        self.hotkey_listener = None
        self.setup_hotkeys()
        self.toggle_clicker_signal.connect(self.trigger_clicker_toggle)
        self.toggle_scroller_signal.connect(self.trigger_scroller_toggle)

        # System Tray
        self.setup_tray_icon()

        # Auto-Updater
        self.start_updater()

    def start_updater(self):
        # Initial check logic
        self.updater = UpdateChecker()
        self.updater.check_finished.connect(self.on_auto_check_finished)

        freq = self.settings.get("update_frequency", "On Launch")
        last_check = float(self.settings.get("last_update_check", 0))
        
        import time
        now = time.time()
        
        should_check = False
        if freq == "On Launch":
            should_check = True
        elif freq == "Daily":
            if now - last_check > 86400: # 24h
                should_check = True
        elif freq == "Monthly":
            if now - last_check > 2592000: # 30 days
                should_check = True
        elif freq == "Never":
            should_check = False
            
        if should_check:
            self.updater.start()

    def on_auto_check_finished(self, found, version, url):
        # Update last check time if successful (version string returned)
        if version:
            import time
            self.settings["last_update_check"] = time.time()
            self.config_manager.save_config()

        if found:
            # Only popup if update is actually found during auto-check
            self.show_about_dialog(auto_trigger=True, version=version, url=url)

    def show_about_dialog(self, auto_trigger=False, version="", url=""):
        dlg = AboutDialog(self, self.updater)
        if auto_trigger:
            dlg.on_check_finished(True, version, url)
        dlg.exec()

    def on_update_available(self, version, url):
        # Legacy method kept just in case, redirected
        self.show_about_dialog(True, version, url)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Top Bar (Profile | Settings | About)
        top_bar_layout = QHBoxLayout()
        
        # Profile Selection (Moved to top left for better UX or kept here?)
        # Let's keep Profile logic here but maybe move it to top left eventually. 
        # For now, just Settings button.
        
        top_bar_layout.addStretch()
        
        # Settings Button
        self.btn_settings = QToolButton()
        self.btn_settings.setText("⚙") # Gear icon
        self.btn_settings.setToolTip("Settings (Theme, Hotkeys, General)")
        self.btn_settings.clicked.connect(self.open_settings)
        top_bar_layout.addWidget(self.btn_settings)
        
        # Help/About Button
        self.btn_about = QToolButton()
        self.btn_about.setText("?")
        self.btn_about.setToolTip("About & Updates")
        self.btn_about.clicked.connect(lambda: self.show_about_dialog(False))
        top_bar_layout.addWidget(self.btn_about)
        
        layout.addLayout(top_bar_layout)

        # Profile Selection Group
        profile_group = QGroupBox("Profile")
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel("Select Profile:"))
        profile_group = QGroupBox("Profile")
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel("Select Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(list(self.profiles.keys()) if self.profiles else ["Default"])
        self.profile_combo.setEditable(False)
        self.profile_combo.currentTextChanged.connect(self.load_profile_state)
        profile_layout.addWidget(self.profile_combo)

        # Profile Actions
        self.btn_new_profile = QToolButton()
        self.btn_new_profile.setText("+")
        self.btn_new_profile.setToolTip("New Profile")
        self.btn_new_profile.clicked.connect(self.on_new_profile)
        profile_layout.addWidget(self.btn_new_profile)

        self.btn_rename_profile = QToolButton()
        self.btn_rename_profile.setText("Ren") # Text
        self.btn_rename_profile.setToolTip("Rename Profile")
        self.btn_rename_profile.clicked.connect(self.on_rename_profile)
        profile_layout.addWidget(self.btn_rename_profile)

        self.btn_delete_profile = QToolButton()
        self.btn_delete_profile.setText("Del") # Bin
        self.btn_delete_profile.setToolTip("Delete Profile")
        self.btn_delete_profile.clicked.connect(self.on_delete_profile)
        profile_layout.addWidget(self.btn_delete_profile)

        self.btn_save_profile = QToolButton()
        self.btn_save_profile.setText("Save") # Disk
        self.btn_save_profile.setToolTip("Save Profile (Update current)")
        self.btn_save_profile.clicked.connect(self.on_save_profile)
        profile_layout.addWidget(self.btn_save_profile)

        profile_group.setLayout(profile_layout)
        # Move profile group under tabs? No, tabs under profile.
        layout.addWidget(profile_group)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Auto-Clicker Tab
        self.clicker_tab = QWidget()
        self.setup_clicker_tab()
        self.tabs.addTab(self.clicker_tab, "Auto-Clicker")

        # Auto-Scroller Tab
        self.scroller_tab = QWidget()
        self.setup_scroller_tab()
        self.tabs.addTab(self.scroller_tab, "Auto-Scroller")

        # Status Bar / Message area
        status_layout = QHBoxLayout()
        self.clicker_status_label = QLabel("Clicker: Idle")
        self.scroller_status_label = QLabel("Scroller: Idle")
        status_layout.addWidget(self.clicker_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.scroller_status_label)
        layout.addLayout(status_layout)

    def open_settings(self):
        dlg = SettingsDialog(self, self.settings)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_settings = dlg.get_settings()
            self.settings.update(new_settings)
            self.config_manager.save_config()
            
            # Apply changes
            self.apply_settings()

    def apply_settings(self):
        # Theme
        theme = self.settings.get("theme", "dark")
        self.change_theme(theme)
        
        # Overlay
        enabled = self.settings.get("enable_overlay", False)
        if enabled:
            self.overlay.show()
            self.refresh_overlay_status()
        else:
            self.overlay.hide()
            
        # Hotkeys
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.setup_hotkeys()

    def change_theme(self, text):
        """Change the application theme."""
        theme_value = text.lower()
        if theme_value == "auto":
            is_dark = True
            if darkdetect:
                try:
                    is_dark = darkdetect.isDark()
                except Exception:
                    pass
            actual_theme = "dark" if is_dark else "light"
        else:
            actual_theme = theme_value

        try:
            if qdarktheme:
                app = QApplication.instance()
                if isinstance(app, QApplication):
                    app.setStyleSheet(qdarktheme.load_stylesheet(actual_theme))
                logging.info(f"Theme changed to {actual_theme}")
            
            # Apply Windows Title Bar Theme
            self.update_title_bar_theme(actual_theme == "dark")
            
        except Exception as e:
            logging.error(f"Failed to change theme: {e}")
            
    def update_title_bar_theme(self, is_dark):
        """
        Update the Windows DWM title bar color to match the theme.
        Uses native Windows API calls via ctypes.
        """
        if sys.platform != "win32":
            return
            
        try:
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            # Works on Windows 10 build 1809+ and Windows 11
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_dark = ctypes.c_int(1 if is_dark else 0)
            hwnd = int(self.winId())
            
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 
                DWMWA_USE_IMMERSIVE_DARK_MODE, 
                ctypes.byref(set_dark), 
                ctypes.sizeof(set_dark)
            )
            
            # Force a repaint if needed (usually handled by OS, but can redraw non-client area)
            # win32gui.RedrawWindow(hwnd, None, None, win32con.RDW_INVALIDATE | win32con.RDW_FRAME)
            # For pure ctypes without pywin32, usually just resizing or moving helps, but on Win11 it's instant.
            
        except Exception as e:
            logging.warning(f"Failed to set Windows title bar theme: {e}")
            
    def setup_clicker_tab(self):
        layout = QVBoxLayout(self.clicker_tab)
        
        # Click Mode Selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Click Mode:"))
        self.click_mode_combo = QComboBox()
        self.click_mode_combo.addItems(["Fixed Rate", "Random Interval"])
        self.click_mode_combo.currentTextChanged.connect(self.on_click_mode_changed)
        self.click_mode_combo.currentTextChanged.connect(self.update_clicker_settings)
        mode_layout.addWidget(self.click_mode_combo)
        layout.addLayout(mode_layout)

        # Container for Fixed Rate (CPS)
        self.fixed_rate_widget = QWidget()
        fixed_layout = QFormLayout(self.fixed_rate_widget)
        fixed_layout.setContentsMargins(0, 0, 0, 0)
        
        self.cps_spin = QDoubleSpinBox()
        self.cps_spin.setRange(0.1, 500.0)
        self.cps_spin.setSingleStep(0.1)
        self.cps_spin.setValue(10.0)
        self.cps_spin.valueChanged.connect(self.update_clicker_settings)
        fixed_layout.addRow("CPS (Clicks/sec):", self.cps_spin)
        
        layout.addWidget(self.fixed_rate_widget)

        # Container for Random Interval
        self.random_interval_widget = QWidget()
        random_layout = QFormLayout(self.random_interval_widget)
        random_layout.setContentsMargins(0, 0, 0, 0)

        self.min_interval_spin = QDoubleSpinBox()
        self.min_interval_spin.setRange(0.01, 300.0)
        self.min_interval_spin.setSingleStep(0.1)
        self.min_interval_spin.setValue(1.0)
        self.min_interval_spin.valueChanged.connect(self.update_clicker_settings)
        random_layout.addRow("Min Interval (s):", self.min_interval_spin)

        self.max_interval_spin = QDoubleSpinBox()
        self.max_interval_spin.setRange(0.01, 300.0)
        self.max_interval_spin.setSingleStep(0.1)
        self.max_interval_spin.setValue(5.0)
        self.max_interval_spin.valueChanged.connect(self.update_clicker_settings)
        random_layout.addRow("Max Interval (s):", self.max_interval_spin)
        
        layout.addWidget(self.random_interval_widget)
        
        # Initially hide random
        self.random_interval_widget.hide()

        # Common Settings
        form_layout = QFormLayout()
        
        self.click_type_combo = QComboBox()
        self.click_type_combo.addItems(["single", "double"])
        self.click_type_combo.currentTextChanged.connect(self.update_clicker_settings)
        form_layout.addRow("Click Type:", self.click_type_combo)
        
        self.mouse_btn_combo = QComboBox()
        self.mouse_btn_combo.addItems(["left", "right", "middle"])
        self.mouse_btn_combo.currentTextChanged.connect(self.update_clicker_settings)
        form_layout.addRow("Mouse Button:", self.mouse_btn_combo)

        layout.addLayout(form_layout)

        # Advanced Settings
        clicker_adv_group = QGroupBox("Advanced Settings")
        adv_layout = QFormLayout()

        self.clicker_start_delay = QDoubleSpinBox()
        self.clicker_start_delay.setRange(0.0, self.MAX_DELAY_SECONDS)
        self.clicker_start_delay.setSingleStep(0.1)
        self.clicker_start_delay.setValue(3.0)
        self.clicker_start_delay.valueChanged.connect(self.update_clicker_settings)
        adv_layout.addRow("Start Delay (s):", self.clicker_start_delay)

        self.clicker_smart_pause = QCheckBox("Enable Smart Pause")
        self.clicker_smart_pause.toggled.connect(self.update_clicker_settings)
        
        self.clicker_resume_delay = QDoubleSpinBox()
        self.clicker_resume_delay.setRange(0.0, self.MAX_DELAY_SECONDS)
        self.clicker_resume_delay.setSingleStep(0.5)
        self.clicker_resume_delay.setValue(1.0)
        self.clicker_resume_delay.setEnabled(False)
        self.clicker_resume_delay.valueChanged.connect(self.update_clicker_settings)
        
        self.clicker_smart_pause.toggled.connect(self.clicker_resume_delay.setEnabled)
        
        adv_layout.addRow(self.clicker_smart_pause)
        adv_layout.addRow("Resume Delay (s):", self.clicker_resume_delay)
        
        clicker_adv_group.setLayout(adv_layout)
        layout.addWidget(clicker_adv_group)

        # Stop Condition Group
        stop_group = QGroupBox("Stop Condition")
        stop_layout = QFormLayout()
        
        self.click_stop_mode_combo = QComboBox()
        self.click_stop_mode_combo.addItems(["None", "Count", "Time (s)"])
        self.click_stop_mode_combo.currentTextChanged.connect(self.on_click_stop_mode_changed)
        self.click_stop_mode_combo.currentTextChanged.connect(self.update_clicker_settings)
        stop_layout.addRow("Stop Mode:", self.click_stop_mode_combo)
        
        self.click_stop_value_spin = QDoubleSpinBox()
        self.click_stop_value_spin.setRange(0, 999999)
        self.click_stop_value_spin.setSingleStep(1)
        self.click_stop_value_spin.setEnabled(False) # Initially disabled for "None"
        self.click_stop_value_spin.valueChanged.connect(self.update_clicker_settings)
        stop_layout.addRow("Stop Value:", self.click_stop_value_spin)
        
        stop_group.setLayout(stop_layout)
        layout.addWidget(stop_group)

        self.start_clicker_btn = QPushButton("Start Auto-Clicker")
        self.start_clicker_btn.setCheckable(True)
        self.start_clicker_btn.clicked.connect(self.toggle_clicker_state)
        self.start_clicker_btn.setMinimumHeight(40)
        layout.addWidget(self.start_clicker_btn)
        
        layout.addStretch()

    def setup_scroller_tab(self):
        layout = QVBoxLayout(self.scroller_tab)
        
        form_layout = QFormLayout()
        
        self.scroll_speed_spin = QDoubleSpinBox()
        self.scroll_speed_spin.setRange(0.1, 500.0)
        self.scroll_speed_spin.setSingleStep(1.0)
        self.scroll_speed_spin.setValue(10.0)
        self.scroll_speed_spin.valueChanged.connect(self.update_scroller_settings)
        form_layout.addRow("Scroll Speed (Lines/sec):", self.scroll_speed_spin)
        
        self.scroll_dir_combo = QComboBox()
        self.scroll_dir_combo.addItems(["down", "up", "left", "right", "up-left", "up-right", "down-left", "down-right"])
        self.scroll_dir_combo.currentTextChanged.connect(self.update_scroller_settings)
        form_layout.addRow("Direction:", self.scroll_dir_combo)

        layout.addLayout(form_layout)

        # Advanced Settings
        scroller_adv_group = QGroupBox("Advanced Settings")
        adv_layout = QFormLayout()

        self.scroller_start_delay = QDoubleSpinBox()
        self.scroller_start_delay.setRange(0.0, self.MAX_DELAY_SECONDS)
        self.scroller_start_delay.setSingleStep(0.1)
        self.scroller_start_delay.setValue(3.0)
        self.scroller_start_delay.valueChanged.connect(self.update_scroller_settings)
        adv_layout.addRow("Start Delay (s):", self.scroller_start_delay)

        self.scroller_smart_pause = QCheckBox("Enable Smart Pause")
        self.scroller_smart_pause.toggled.connect(self.update_scroller_settings)
        
        self.scroller_resume_delay = QDoubleSpinBox()
        self.scroller_resume_delay.setRange(0.0, self.MAX_DELAY_SECONDS)
        self.scroller_resume_delay.setSingleStep(0.5)
        self.scroller_resume_delay.setValue(1.0)
        self.scroller_resume_delay.setEnabled(False)
        self.scroller_resume_delay.valueChanged.connect(self.update_scroller_settings)
        
        self.scroller_smart_pause.toggled.connect(self.scroller_resume_delay.setEnabled)
        
        adv_layout.addRow(self.scroller_smart_pause)
        adv_layout.addRow("Resume Delay (s):", self.scroller_resume_delay)
        
        scroller_adv_group.setLayout(adv_layout)
        layout.addWidget(scroller_adv_group)

        # Stop Condition Group
        stop_group = QGroupBox("Stop Condition")
        stop_layout = QFormLayout()
        
        self.scroll_stop_mode_combo = QComboBox()
        self.scroll_stop_mode_combo.addItems(["None", "Count (Lines)", "Time (s)"])
        self.scroll_stop_mode_combo.currentTextChanged.connect(self.on_scroll_stop_mode_changed)
        self.scroll_stop_mode_combo.currentTextChanged.connect(self.update_scroller_settings)
        stop_layout.addRow("Stop Mode:", self.scroll_stop_mode_combo)
        
        self.scroll_stop_value_spin = QDoubleSpinBox()
        self.scroll_stop_value_spin.setRange(0, 999999)
        self.scroll_stop_value_spin.setSingleStep(1)
        self.scroll_stop_value_spin.setEnabled(False) # Initially disabled for "None"
        self.scroll_stop_value_spin.valueChanged.connect(self.update_scroller_settings)
        stop_layout.addRow("Stop Value:", self.scroll_stop_value_spin)
        
        stop_group.setLayout(stop_layout)
        layout.addWidget(stop_group)

        self.start_scroller_btn = QPushButton("Start Auto-Scroller")
        self.start_scroller_btn.setCheckable(True)
        self.start_scroller_btn.clicked.connect(self.toggle_scroller_state)
        self.start_scroller_btn.setMinimumHeight(40)
        layout.addWidget(self.start_scroller_btn)
        
        layout.addStretch()

    def on_click_mode_changed(self, mode):
        if mode == "Fixed Rate":
            self.fixed_rate_widget.show()
            self.random_interval_widget.hide()
        else:
            self.fixed_rate_widget.hide()
            self.random_interval_widget.show()

    def on_click_stop_mode_changed(self, text):
        if text == "None":
            self.click_stop_value_spin.setEnabled(False)
        else:
            self.click_stop_value_spin.setEnabled(True)
            if text == "Count":
                self.click_stop_value_spin.setDecimals(0)
                self.click_stop_value_spin.setSingleStep(1)
            else: # Time (s)
                self.click_stop_value_spin.setDecimals(1)
                self.click_stop_value_spin.setSingleStep(0.1)
                
    def on_scroll_stop_mode_changed(self, text):
        if text == "None":
            self.scroll_stop_value_spin.setEnabled(False)
        else:
            self.scroll_stop_value_spin.setEnabled(True)
            if "Count" in text:
                self.scroll_stop_value_spin.setDecimals(0)
                self.scroll_stop_value_spin.setSingleStep(1)
            else: # Time (s)
                self.scroll_stop_value_spin.setDecimals(1)
                self.scroll_stop_value_spin.setSingleStep(0.1)

    def load_settings_to_ui(self):
        # Load from self.settings
        # Clicker
        mode = self.settings.get("click_mode", "fixed")
        self.click_mode_combo.setCurrentText("Fixed Rate" if mode == "fixed" else "Random Interval")
        self.cps_spin.setValue(self.settings.get("click_rate", 10.0))
        self.min_interval_spin.setValue(self.settings.get("click_min_interval", 1.0))
        self.max_interval_spin.setValue(self.settings.get("click_max_interval", 5.0))
        self.click_type_combo.setCurrentText(self.settings.get("click_type", "single"))
        self.mouse_btn_combo.setCurrentText(self.settings.get("mouse_button", "left"))
        
        self.clicker_start_delay.setValue(self.settings.get("clicker_start_delay", 3.0))
        self.clicker_smart_pause.setChecked(self.settings.get("clicker_smart_pause", False))
        self.clicker_resume_delay.setValue(self.settings.get("clicker_resume_delay", 1.0))
        self.clicker_resume_delay.setEnabled(self.clicker_smart_pause.isChecked())

        # Clicker Stop Mode
        click_stop = self.settings.get("click_stop_mode", "none")
        if click_stop == "count":
            self.click_stop_mode_combo.setCurrentText("Count")
        elif click_stop == "time":
            self.click_stop_mode_combo.setCurrentText("Time (s)")
        else:
            self.click_stop_mode_combo.setCurrentText("None")
        self.click_stop_value_spin.setValue(self.settings.get("click_stop_value", 0))

        # Scroller
        self.scroll_speed_spin.setValue(self.settings.get("scroll_speed", 0) if self.settings.get("scroll_speed", 0) > 0 else 10.0)
        self.scroll_dir_combo.setCurrentText(self.settings.get("scroll_direction", "down"))

        self.scroller_start_delay.setValue(self.settings.get("scroller_start_delay", 3.0))
        self.scroller_smart_pause.setChecked(self.settings.get("scroller_smart_pause", False))
        self.scroller_resume_delay.setValue(self.settings.get("scroller_resume_delay", 1.0))
        self.scroller_resume_delay.setEnabled(self.scroller_smart_pause.isChecked())
        
        # Scroller Stop Mode
        scroll_stop = self.settings.get("scroll_stop_mode", "none")
        if scroll_stop == "count":
            self.scroll_stop_mode_combo.setCurrentText("Count (Lines)")
        elif scroll_stop == "time":
            self.scroll_stop_mode_combo.setCurrentText("Time (s)")
        else:
            self.scroll_stop_mode_combo.setCurrentText("None")
        self.scroll_stop_value_spin.setValue(self.settings.get("scroll_stop_value", 0))
        
        # Trigger visibility
        self.on_click_mode_changed(self.click_mode_combo.currentText())
        self.on_click_stop_mode_changed(self.click_stop_mode_combo.currentText())
        self.on_scroll_stop_mode_changed(self.scroll_stop_mode_combo.currentText())

    def update_clicker_settings(self):
        if hasattr(self, 'clicker'):
            mode = "fixed" if self.click_mode_combo.currentText() == "Fixed Rate" else "random"
            
            stop_text = self.click_stop_mode_combo.currentText()
            stop_mode = "none"
            if stop_text == "Count":
                stop_mode = "count"
            elif stop_text == "Time (s)":
                stop_mode = "time"

            self.clicker.update_settings(
                button=self.mouse_btn_combo.currentText(),
                click_type=self.click_type_combo.currentText(),
                cps=self.cps_spin.value(),
                start_delay=self.clicker_start_delay.value(),
                smart_pause=self.clicker_smart_pause.isChecked(),
                smart_pause_delay=self.clicker_resume_delay.value(),
                jitter=0.0, # Default/Hidden setting
                mode=mode,
                min_interval=self.min_interval_spin.value(),
                max_interval=self.max_interval_spin.value(),
                stop_mode=stop_mode,
                stop_value=self.click_stop_value_spin.value()
            )

    def update_scroller_settings(self):
        if hasattr(self, 'scroller'):
            stop_text = self.scroll_stop_mode_combo.currentText()
            stop_mode = "none"
            if "Count" in stop_text:
                stop_mode = "count"
            elif "Time" in stop_text:
                stop_mode = "time"
            
            self.scroller.update_settings(
                direction=self.scroll_dir_combo.currentText(),
                scroll_speed=self.scroll_speed_spin.value(),
                start_delay=self.scroller_start_delay.value(),
                smart_pause=self.scroller_smart_pause.isChecked(),
                smart_pause_delay=self.scroller_resume_delay.value(),
                jitter=0.0, # Default/Hidden setting
                stop_mode=stop_mode,
                stop_value=self.scroll_stop_value_spin.value()
            )

    def toggle_clicker_state(self, checked):
        if checked:
            if not self.clicker.isRunning():
                self.update_clicker_settings()
                self.clicker.start()
                self.start_clicker_btn.setText("Stop Auto-Clicker")
                self.start_clicker_btn.setChecked(True)
        else:
            if self.clicker.isRunning():
                self.clicker.stop()
                self.clicker.wait()
                self.start_clicker_btn.setText("Start Auto-Clicker")
                self.start_clicker_btn.setChecked(False)

    def toggle_scroller_state(self, checked):
        if checked:
            if not self.scroller.isRunning():
                self.update_scroller_settings()
                self.scroller.start()
                self.start_scroller_btn.setText("Stop Auto-Scroller")
                self.start_scroller_btn.setChecked(True)
        else:
            if self.scroller.isRunning():
                self.scroller.stop()
                self.scroller.wait()
                self.start_scroller_btn.setText("Start Auto-Scroller")
                self.start_scroller_btn.setChecked(False)

    # Slots for pynput signals
    @pyqtSlot()
    def trigger_clicker_toggle(self):
        # Toggle based on current state
        is_running = self.clicker.isRunning()
        self.toggle_clicker_state(not is_running)

    @pyqtSlot()
    def trigger_scroller_toggle(self):
        is_running = self.scroller.isRunning()
        self.toggle_scroller_state(not is_running)

    def on_clicker_stats(self, count):
        self.clicker_count = count
        self.refresh_clicker_status()

    def on_scroller_stats(self, count):
        self.scroller_count = count
        self.refresh_scroller_status()

    @pyqtSlot(str)
    def on_clicker_state_changed(self, state):
        previous_state = self.clicker_state
        self.clicker_state = state
        if state == "running" and previous_state in {"idle", "finished"}:
            self.clicker_count = 0
        self.refresh_clicker_status()

    @pyqtSlot(str)
    def on_scroller_state_changed(self, state):
        previous_state = self.scroller_state
        self.scroller_state = state
        if state == "running" and previous_state in {"idle", "finished"}:
            self.scroller_count = 0
        self.refresh_scroller_status()

    def format_status_label(self, prefix, state, count, unit):
        if state == "running":
            return f"{prefix}: Running - {count} {unit}"
        if state == "paused":
            return f"{prefix}: Paused - {count} {unit}"
        if state == "finished":
            return f"{prefix}: Finished - {count} {unit}"
        return f"{prefix}: Idle"

    def refresh_clicker_status(self):
        self.clicker_status_label.setText(
            self.format_status_label("Clicker", self.clicker_state, self.clicker_count, "clicks")
        )
        self.refresh_overlay_status()

    def refresh_scroller_status(self):
        self.scroller_status_label.setText(
            self.format_status_label("Scroller", self.scroller_state, self.scroller_count, "scrolls")
        )
        self.refresh_overlay_status()

    def refresh_overlay_status(self):
        if not self.overlay.isVisible():
            return

        parts = []
        if self.clicker_state != "idle":
            parts.append(self.format_status_label("Clicker", self.clicker_state, self.clicker_count, "clicks"))
        if self.scroller_state != "idle":
            parts.append(self.format_status_label("Scroller", self.scroller_state, self.scroller_count, "scrolls"))

        self.overlay.update_text(" | ".join(parts) if parts else "FlowScroll: Ready")

    def setup_hotkeys(self):
        # Read from settings or default
        hotkeys = self.settings.get("hotkeys", {})
        click_key = hotkeys.get("toggle_click", "F10")
        scroll_key = hotkeys.get("toggle_scroll", "F9")

        # Map to pynput format (basic mapping)
        def map_key(k):
            k = k.lower()
            if k.startswith('f') and len(k) > 1 and k[1:].isdigit():
                return f'<{k}>'
            return k

        key_map = {
            map_key(click_key): self.toggle_clicker_signal.emit,
            map_key(scroll_key): self.toggle_scroller_signal.emit
        }

        try:
            self.hotkey_listener = keyboard.GlobalHotKeys(key_map)
            self.hotkey_listener.start()
        except Exception as e:
            logging.error(f"Failed to setup hotkeys: {e}")
            QMessageBox.warning(self, "Hotkey Error", f"Could not register hotkeys: {e}")

    def load_profile_state(self, name):
        if not name:
            return
            
        profile_data = self.config_manager.get_profile(name)
        if not profile_data:
            return

        # Block signals to prevent triggering engine updates for every single change
        self.block_signals(True)
        try:
            # Clicker Settings
            mode = profile_data.get("click_mode", "fixed")
            self.click_mode_combo.setCurrentText("Fixed Rate" if mode == "fixed" else "Random Interval")
            
            self.cps_spin.setValue(float(profile_data.get("cps", 10.0)))
            self.min_interval_spin.setValue(float(profile_data.get("click_min_interval", 1.0)))
            self.max_interval_spin.setValue(float(profile_data.get("click_max_interval", 5.0)))
            
            self.click_type_combo.setCurrentText(profile_data.get("click_type", "single"))
            self.mouse_btn_combo.setCurrentText(profile_data.get("mouse_button", "left"))
            self.clicker_start_delay.setValue(float(profile_data.get("clicker_start_delay", 3.0)))
            self.clicker_smart_pause.setChecked(profile_data.get("clicker_smart_pause", False))
            self.clicker_resume_delay.setValue(float(profile_data.get("clicker_resume_delay", 1.0)))
            self.clicker_resume_delay.setEnabled(self.clicker_smart_pause.isChecked())

            # Clicker Stop Mode
            click_stop = profile_data.get("click_stop_mode", "none")
            if click_stop == "count":
                self.click_stop_mode_combo.setCurrentText("Count")
            elif click_stop == "time":
                self.click_stop_mode_combo.setCurrentText("Time (s)")
            else:
                self.click_stop_mode_combo.setCurrentText("None")
            self.click_stop_value_spin.setValue(profile_data.get("click_stop_value", 0))

            # Scroller Settings
            self.scroll_speed_spin.setValue(float(profile_data.get("scroll_speed", 10.0)))
            self.scroll_dir_combo.setCurrentText(profile_data.get("scroll_direction", "down"))
            self.scroller_start_delay.setValue(float(profile_data.get("scroller_start_delay", 3.0)))
            self.scroller_smart_pause.setChecked(profile_data.get("scroller_smart_pause", False))
            self.scroller_resume_delay.setValue(float(profile_data.get("scroller_resume_delay", 1.0)))
            self.scroller_resume_delay.setEnabled(self.scroller_smart_pause.isChecked())
            
            # Scroller Stop Mode
            scroll_stop = profile_data.get("scroll_stop_mode", "none")
            if scroll_stop == "count":
                self.scroll_stop_mode_combo.setCurrentText("Count (Lines)")
            elif scroll_stop == "time":
                self.scroll_stop_mode_combo.setCurrentText("Time (s)")
            else:
                self.scroll_stop_mode_combo.setCurrentText("None")
            self.scroll_stop_value_spin.setValue(profile_data.get("scroll_stop_value", 0))

            # Trigger visibility
            self.on_click_stop_mode_changed(self.click_stop_mode_combo.currentText())
            self.on_scroll_stop_mode_changed(self.scroll_stop_mode_combo.currentText())
            
        finally:
            self.block_signals(False)
            
        # Update engines once
        self.update_clicker_settings()
        self.update_scroller_settings()

    def gather_current_settings(self):
        # Clicker stop mode
        c_mode_text = self.click_stop_mode_combo.currentText()
        c_stop_mode = "none"
        if c_mode_text == "Count":
            c_stop_mode = "count"
        elif c_mode_text == "Time (s)":
            c_stop_mode = "time"

        # Scroller stop mode
        s_mode_text = self.scroll_stop_mode_combo.currentText()
        s_stop_mode = "none"
        if "Count" in s_mode_text:
            s_stop_mode = "count"
        elif "Time" in s_mode_text:
            s_stop_mode = "time"

        return {
            "click_mode": "fixed" if self.click_mode_combo.currentText() == "Fixed Rate" else "random",
            "cps": self.cps_spin.value(),
            "click_min_interval": self.min_interval_spin.value(),
            "click_max_interval": self.max_interval_spin.value(),
            "click_type": self.click_type_combo.currentText(),
            "mouse_button": self.mouse_btn_combo.currentText(),
            "clicker_start_delay": self.clicker_start_delay.value(),
            "clicker_smart_pause": self.clicker_smart_pause.isChecked(),
            "clicker_resume_delay": self.clicker_resume_delay.value(),
            "click_stop_mode": c_stop_mode,
            "click_stop_value": self.click_stop_value_spin.value(),
            
            "scroll_speed": self.scroll_speed_spin.value(),
            "scroll_direction": self.scroll_dir_combo.currentText(),
            "scroller_start_delay": self.scroller_start_delay.value(),
            "scroller_smart_pause": self.scroller_smart_pause.isChecked(),
            "scroller_resume_delay": self.scroller_resume_delay.value(),
            "scroll_stop_mode": s_stop_mode,
            "scroll_stop_value": self.scroll_stop_value_spin.value()
        }

    def on_new_profile(self):
        name, ok = QInputDialog.getText(self, "New Profile", "Enter profile name:")
        if ok and name:
            name = name.strip()
            if not name:
                QMessageBox.warning(self, "Error", "Profile name cannot be empty.")
                return
            if name in self.config_manager.get_all_profiles():
                QMessageBox.warning(self, "Error", "Profile already exists.")
                return
                
            settings = self.gather_current_settings()
            self.config_manager.set_profile(name, settings)
            
            self.profile_combo.addItem(name)
            self.profile_combo.setCurrentText(name)

    def on_rename_profile(self):
        current_name = self.profile_combo.currentText()
        if not current_name:
            return
            
        new_name, ok = QInputDialog.getText(self, "Rename Profile", f"Rename '{current_name}' to:")
        if ok and new_name:
            new_name = new_name.strip()
            if not new_name:
                QMessageBox.warning(self, "Error", "Profile name cannot be empty.")
                return
            if new_name == current_name:
                return
            if new_name in self.config_manager.get_all_profiles():
                QMessageBox.warning(self, "Error", "Profile name already exists.")
                return
                
            if self.config_manager.rename_profile(current_name, new_name):
                idx = self.profile_combo.findText(current_name)
                if idx >= 0:
                    self.profile_combo.setItemText(idx, new_name)
                    self.profile_combo.setCurrentText(new_name)

    def on_delete_profile(self):
        current_name = self.profile_combo.currentText()
        if not current_name:
            return
            
        reply = QMessageBox.question(self, "Delete Profile", 
                                     f"Are you sure you want to delete profile '{current_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                     
        if reply == QMessageBox.StandardButton.Yes:
            if self.config_manager.delete_profile(current_name):
                idx = self.profile_combo.findText(current_name)
                if idx >= 0:
                    self.profile_combo.removeItem(idx)
                    
                if self.profile_combo.count() == 0:
                     # Create default if empty
                    self.profile_combo.addItem("Default")
                    self.config_manager.set_profile("Default", self.gather_current_settings())
                
                # Select first item
                if self.profile_combo.count() > 0:
                    self.profile_combo.setCurrentIndex(0)

    def on_save_profile(self):
        current_name = self.profile_combo.currentText()
        if not current_name:
            return
            
        settings = self.gather_current_settings()
        self.config_manager.set_profile(current_name, settings)

    def block_signals(self, block):
        # Helper to block/unblock signals for all input widgets
        widgets = [
            self.click_mode_combo, self.cps_spin, self.min_interval_spin, self.max_interval_spin,
            self.click_type_combo, self.mouse_btn_combo,
            self.clicker_start_delay, self.clicker_smart_pause, self.clicker_resume_delay,
            self.click_stop_mode_combo, self.click_stop_value_spin,
            self.scroll_speed_spin, self.scroll_dir_combo,
            self.scroller_start_delay, self.scroller_smart_pause, self.scroller_resume_delay,
            self.scroll_stop_mode_combo, self.scroll_stop_value_spin
        ]
        for w in widgets:
            w.blockSignals(block)



    def on_clicker_finished(self):
        if self.start_clicker_btn.isChecked():
            self.start_clicker_btn.setChecked(False)
        self.start_clicker_btn.setText("Start Auto-Clicker")
        self.refresh_clicker_status()

    def on_scroller_finished(self):
        if self.start_scroller_btn.isChecked():
            self.start_scroller_btn.setChecked(False)
        self.start_scroller_btn.setText("Start Auto-Scroller")
        self.refresh_scroller_status()

    def perform_cleanup(self):
        # Save settings on close
        self.settings["click_mode"] = "fixed" if self.click_mode_combo.currentText() == "Fixed Rate" else "random"
        self.settings["click_min_interval"] = self.min_interval_spin.value()
        self.settings["click_max_interval"] = self.max_interval_spin.value()
        self.settings["click_rate"] = self.cps_spin.value()
        self.settings["click_type"] = self.click_type_combo.currentText()
        self.settings["mouse_button"] = self.mouse_btn_combo.currentText()
        self.settings["clicker_start_delay"] = self.clicker_start_delay.value()
        self.settings["clicker_smart_pause"] = self.clicker_smart_pause.isChecked()
        self.settings["clicker_resume_delay"] = self.clicker_resume_delay.value()
        
        c_mode_text = self.click_stop_mode_combo.currentText()
        if c_mode_text == "Count":
            self.settings["click_stop_mode"] = "count"
        elif c_mode_text == "Time (s)":
            self.settings["click_stop_mode"] = "time"
        else:
             self.settings["click_stop_mode"] = "none"
        self.settings["click_stop_value"] = self.click_stop_value_spin.value()

        self.settings["scroll_speed"] = self.scroll_speed_spin.value()
        self.settings["scroll_direction"] = self.scroll_dir_combo.currentText()
        self.settings["scroller_start_delay"] = self.scroller_start_delay.value()
        self.settings["scroller_smart_pause"] = self.scroller_smart_pause.isChecked()
        self.settings["scroller_resume_delay"] = self.scroller_resume_delay.value()

        s_mode_text = self.scroll_stop_mode_combo.currentText()
        if "Count" in s_mode_text:
            self.settings["scroll_stop_mode"] = "count"
        elif "Time" in s_mode_text:
            self.settings["scroll_stop_mode"] = "time"
        else:
             self.settings["scroll_stop_mode"] = "none"
        self.settings["scroll_stop_value"] = self.scroll_stop_value_spin.value()
        
        # Save config
        self.config_manager.save_config()

        # Stop workers
        if self.clicker.isRunning():
            self.clicker.stop()
        if self.scroller.isRunning():
            self.scroller.stop()
        
        # Stop listener
        if self.hotkey_listener:
            self.hotkey_listener.stop()

    def setup_tray_icon(self):
        """Setup the system tray icon."""
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = self.windowIcon()
        if not icon_path or icon_path.isNull():
            # Fallback if no window icon set
            icon_path = QIcon(os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'icon.ico'))
        self.tray_icon.setIcon(icon_path)
        
        # Tray Menu
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)
        
        quit_action = QAction("Exit", self)
        app = QApplication.instance()
        if app:
            quit_action.triggered.connect(app.quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                if self.isMinimized():
                    self.show_window()
                else:
                    self.hide()
            else:
                self.show_window()

    def show_window(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.activateWindow()

    def changeEvent(self, a0):
        if a0 and hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            if a0.type() == QEvent.Type.WindowStateChange:
                if self.windowState() & Qt.WindowState.WindowMinimized:
                    # Minimize to tray
                    a0.ignore()
                    self.hide()
                    return
        super().changeEvent(a0)

    def showEvent(self, a0):
        super().showEvent(a0)
        # Apply theme again to ensure title bar color is correct after show
        # This fixes startup issues where DWM color isn't applied immediately
        QTimer.singleShot(100, lambda: self.change_theme(self.settings.get("theme", "dark")))

    def closeEvent(self, a0):
        self.perform_cleanup()
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.hide()
        
        if a0:
            a0.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
