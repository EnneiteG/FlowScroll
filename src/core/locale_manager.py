import os
import sys
import json
import logging

class LocaleManager:
    """
    Singleton class to manage application localization.
    Handles loading of 'locales.json' and retrieval of translated strings.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LocaleManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, lang='fr'):
        if hasattr(self, '_initialized') and self._initialized:
            # If lang provided is different and we want to allow switching via re-init
            # we could handle it, but typically set_language is used.
            return

        self.lang = lang
        self.translations = {}
        self._load_translations()
        self._initialized = True

    def _get_locale_path(self):
        """Get the path for the locales.json file."""
        try:
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
                return os.path.join(bundle_dir, 'locales.json')
            else:
                # Running as normal Python script
                # We are in src/core/locale_manager.py, so we go up 2 levels
                current_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
                return os.path.join(root_dir, 'locales.json')
        except Exception as e:
            logging.error(f"Error determining locale path: {e}")
            return 'locales.json'

    def _load_translations(self):
        """Load translations from JSON file."""
        path = self._get_locale_path()
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
            else:
                # Create default file if missing (only in non-frozen mode)
                if not getattr(sys, 'frozen', False):
                    self._create_default_translations(path)
        except (json.JSONDecodeError, IOError, OSError) as e:
            logging.error(f"Error loading translations: {e}")

    def _create_default_translations(self, path):
        """Create default translations file."""
        default = {
            "fr": {"app_title": "FlowScroll v{version}"},
            "en": {"app_title": "FlowScroll v{version}"}
        }
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(default, f, indent=2, ensure_ascii=False)
            self.translations = default
        except (IOError, OSError) as e:
            logging.error(f"Error creating default translations: {e}")

    def get(self, key, **kwargs):
        """Get translated text with optional formatting."""
        try:
            # Try specific language, then key as fallback
            text = self.translations.get(self.lang, {}).get(key, key)
            
            # If text is explicit None (missing in json but key exists), fallback to key
            if text is None:
                text = key
            
            return text.format(**kwargs) if kwargs else text
        except Exception as e:
            logging.warning(f"Error formatting translation for key '{key}': {e}")
            return key

    def set_language(self, lang):
        """Change the current language."""
        if lang in self.translations:
            self.lang = lang
            return True
        return False
