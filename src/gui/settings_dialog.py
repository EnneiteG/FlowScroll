from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout, 
    QComboBox, QCheckBox, QGroupBox, QDialogButtonBox, QLabel, 
    QKeySequenceEdit, QHBoxLayout
)
from PyQt6.QtGui import QKeySequence

class SettingsDialog(QDialog):
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(400, 300)
        self.settings = settings or {}
        
        # Temporary storage for changes
        self.temp_settings = self.settings.copy()
        if "hotkeys" in self.settings:
             self.temp_settings["hotkeys"] = self.settings["hotkeys"].copy()
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Tab 1: General
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        
        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "Auto"])
        current_theme = self.temp_settings.get("theme", "dark").capitalize()
        self.theme_combo.setCurrentText(current_theme)
        general_layout.addRow("Theme:", self.theme_combo)
        
        # Overlay
        self.overlay_check = QCheckBox()
        self.overlay_check.setChecked(self.temp_settings.get("enable_overlay", False))
        general_layout.addRow("Show Overlay (HUD):", self.overlay_check)
        
        # Update Frequency
        self.update_freq_combo = QComboBox()
        self.update_freq_combo.addItems(["On Launch", "Daily", "Monthly", "Never"])
        self.update_freq_combo.setCurrentText(self.temp_settings.get("update_frequency", "On Launch"))
        general_layout.addRow("Check Updates:", self.update_freq_combo)
        
        tabs.addTab(general_tab, "General")

        # Tab 2: Hotkeys
        hotkey_tab = QWidget()
        hotkey_layout = QFormLayout(hotkey_tab)
        
        self.hotkey_clicker_edit = QKeySequenceEdit()
        click_key = self.temp_settings.get("hotkeys", {}).get("toggle_click", "F10")
        self.hotkey_clicker_edit.setKeySequence(QKeySequence(click_key))
        
        self.hotkey_scroller_edit = QKeySequenceEdit()
        scroll_key = self.temp_settings.get("hotkeys", {}).get("toggle_scroll", "F9")
        self.hotkey_scroller_edit.setKeySequence(QKeySequence(scroll_key))
        
        hotkey_layout.addRow("Toggle Clicker:", self.hotkey_clicker_edit)
        hotkey_layout.addRow("Toggle Scroller:", self.hotkey_scroller_edit)
        
        tabs.addTab(hotkey_tab, "Hotkeys")
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_settings(self):
        # Collect values from UI
        self.temp_settings["theme"] = self.theme_combo.currentText().lower()
        self.temp_settings["enable_overlay"] = self.overlay_check.isChecked()
        self.temp_settings["update_frequency"] = self.update_freq_combo.currentText()
        
        if "hotkeys" not in self.temp_settings:
            self.temp_settings["hotkeys"] = {}
        
        self.temp_settings["hotkeys"]["toggle_click"] = self.hotkey_clicker_edit.keySequence().toString()
        self.temp_settings["hotkeys"]["toggle_scroll"] = self.hotkey_scroller_edit.keySequence().toString()
        
        return self.temp_settings
