import os
import sys
import json
import logging

DEFAULT_SETTINGS = {
    "start_delay": 3.0,
    "smart_pause": False,
    "smart_pause_delay": 1.0,
    "click_mode": "fixed",
    "click_min_interval": 1.0,
    "click_max_interval": 5.0,
    "theme": "dark",
    "click_stop_mode": "none",
    "click_stop_value": 1000.0,
    "scroll_stop_mode": "none",
    "scroll_stop_value": 1000.0
}

class ConfigManager:
    """
    Singleton class to manage application configuration and profiles.
    Handles loading and saving of 'flowscroll_settings.json' and 'profiles.json'.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Prevent re-initialization if already initialized
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.settings = {}
        self.profiles = {}
        self.load_config()
        self.load_profiles()
        self._initialized = True

    def _get_base_path(self):
        """Get the base path for configuration files."""
        try:
            if getattr(sys, 'frozen', False):
                # When frozen with PyInstaller, use the executable's directory
                return os.path.dirname(sys.executable)
            else:
                # When running as script, use the project root directory
                # We are in src/core/config_manager.py, so we go up 2 levels
                current_dir = os.path.dirname(os.path.abspath(__file__))
                return os.path.abspath(os.path.join(current_dir, '..', '..'))
        except Exception as e:
            logging.error(f"Error determining base path: {e}")
            return os.getcwd()

    def _get_settings_path(self):
        return os.path.join(self._get_base_path(), 'flowscroll_settings.json')

    def _get_profiles_path(self):
        return os.path.join(self._get_base_path(), 'profiles.json')

    def load_config(self):
        """Load settings from flowscroll_settings.json."""
        path = self._get_settings_path()
        self.settings = DEFAULT_SETTINGS.copy()
        
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
        except (json.JSONDecodeError, IOError, OSError) as e:
            logging.error(f"Error loading settings from {path}: {e}")
            # Keep defaults
        return self.settings

    def save_config(self):
        """Save current settings to flowscroll_settings.json."""
        path = self._get_settings_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
        except (IOError, OSError, TypeError) as e:
            logging.error(f"Error saving settings to {path}: {e}")

    def load_profiles(self):
        """Load profiles from profiles.json."""
        path = self._get_profiles_path()
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self.profiles = json.load(f)
            else:
                self.profiles = {}
        except (json.JSONDecodeError, IOError, OSError) as e:
            logging.error(f"Error loading profiles from {path}: {e}")
            self.profiles = {}
        return self.profiles

    def save_profiles(self):
        """Save current profiles to profiles.json."""
        path = self._get_profiles_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, indent=2)
        except (IOError, OSError, TypeError) as e:
            logging.error(f"Error saving profiles to {path}: {e}")

    def get_setting(self, key, default=None):
        """Safe access to a setting value."""
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        """Set a setting value and save configuration."""
        self.settings[key] = value
        self.save_config()

    def get_profile(self, name):
        """Get a specific profile by name."""
        return self.profiles.get(name)

    def set_profile(self, name, profile_data):
        """Set/Update a profile and save profiles."""
        self.profiles[name] = profile_data
        self.save_profiles()

    def delete_profile(self, name):
        """Delete a profile by name."""
        if name in self.profiles:
            del self.profiles[name]
            self.save_profiles()
            return True
        return False

    def rename_profile(self, old_name, new_name):
        """Rename an existing profile."""
        if old_name in self.profiles and new_name not in self.profiles:
            self.profiles[new_name] = self.profiles.pop(old_name)
            self.save_profiles()
            return True
        return False

    def get_all_profiles(self):
        """Return all profile names."""
        return list(self.profiles.keys())
