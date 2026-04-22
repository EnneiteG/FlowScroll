from copy import deepcopy
import json
import logging
import os
import shutil
import sys

APP_DIR_NAME = "FlowScroll"
SETTINGS_FILE_NAME = "flowscroll_settings.json"
PROFILES_FILE_NAME = "profiles.json"

DEFAULT_SETTINGS = {
    "start_delay": 3.0,
    "smart_pause": False,
    "smart_pause_delay": 1.0,
    "click_mode": "fixed",
    "click_min_interval": 1.0,
    "click_max_interval": 5.0,
    "click_rate": 10.0,
    "click_type": "single",
    "mouse_button": "left",
    "clicker_start_delay": 3.0,
    "clicker_smart_pause": False,
    "clicker_resume_delay": 1.0,
    "theme": "dark",
    "enable_overlay": False,
    "update_frequency": "On Launch",
    "hotkeys": {
        "toggle_scroll": "F9",
        "toggle_click": "F10",
    },
    "click_stop_mode": "none",
    "click_stop_value": 1000.0,
    "scroll_speed": 10.0,
    "scroll_direction": "down",
    "scroller_start_delay": 3.0,
    "scroller_smart_pause": False,
    "scroller_resume_delay": 1.0,
    "scroll_stop_mode": "none",
    "scroll_stop_value": 1000.0,
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
        self._migrate_legacy_files()
        self.load_config()
        self.load_profiles()
        self._initialized = True

    @classmethod
    def get_app_data_dir(cls):
        """Return the writable directory used for settings, profiles, and logs."""
        override = os.environ.get("FLOWSCROLL_APPDATA_DIR")
        if override:
            app_dir = override
        elif sys.platform == "win32":
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                app_dir = os.path.join(local_appdata, APP_DIR_NAME)
            else:
                app_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", APP_DIR_NAME)
        else:
            app_dir = os.path.join(os.path.expanduser("~"), ".local", "share", APP_DIR_NAME)

        os.makedirs(app_dir, exist_ok=True)
        return app_dir

    @classmethod
    def get_logs_dir(cls):
        logs_dir = os.path.join(cls.get_app_data_dir(), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        return logs_dir

    def _get_base_path(self):
        return self.get_app_data_dir()

    def _iter_legacy_base_paths(self):
        candidates = []

        override = os.environ.get("FLOWSCROLL_LEGACY_DIR")
        if override:
            candidates.append(override)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
        candidates.append(project_root)

        if getattr(sys, 'frozen', False):
            candidates.append(os.path.dirname(sys.executable))
            bundle_dir = getattr(sys, '_MEIPASS', '')
            if bundle_dir:
                candidates.append(bundle_dir)

        target_base = os.path.abspath(self._get_base_path())
        unique_candidates = []
        seen = set()
        for candidate in candidates:
            normalized = os.path.abspath(candidate)
            if normalized == target_base or normalized in seen:
                continue
            seen.add(normalized)
            unique_candidates.append(normalized)

        return unique_candidates

    def _migrate_legacy_file(self, file_name):
        destination = os.path.join(self._get_base_path(), file_name)
        if os.path.exists(destination):
            return

        for legacy_base in self._iter_legacy_base_paths():
            source = os.path.join(legacy_base, file_name)
            if not os.path.exists(source):
                continue

            try:
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                shutil.copy2(source, destination)
                logging.info("Migrated %s to %s", source, destination)
                return
            except OSError as exc:
                logging.warning("Failed to migrate %s to %s: %s", source, destination, exc)

    def _migrate_legacy_files(self):
        self._migrate_legacy_file(SETTINGS_FILE_NAME)
        self._migrate_legacy_file(PROFILES_FILE_NAME)

    def _get_settings_path(self):
        return os.path.join(self._get_base_path(), SETTINGS_FILE_NAME)

    def _get_profiles_path(self):
        return os.path.join(self._get_base_path(), PROFILES_FILE_NAME)

    def load_config(self):
        """Load settings from flowscroll_settings.json."""
        path = self._get_settings_path()
        self.settings = deepcopy(DEFAULT_SETTINGS)
        
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
            os.makedirs(os.path.dirname(path), exist_ok=True)
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
            os.makedirs(os.path.dirname(path), exist_ok=True)
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
