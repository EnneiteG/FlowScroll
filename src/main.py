import sys
import os
import logging
import qdarktheme
import darkdetect
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QSharedMemory

# Adjust path to include project root so 'src' module can be found
# Assuming this file is at src/main.py
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now we can import from src
try:
    from src.gui.main_window import MainWindow
    from src.core.config_manager import ConfigManager
except ImportError as e:
    logging.error(f"Failed to import modules: {e}")
    sys.exit(1)

def setup_environment():
    """Setup logging and other environment checks."""
    log_dir = ConfigManager.get_logs_dir()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join(log_dir, 'flowscroll.log'), encoding='utf-8')
        ]
    )


def enforce_single_instance(shared_memory, parent=None):
    if shared_memory.create(1):
        return True

    logging.warning("Another FlowScroll instance is already running.")
    QMessageBox.warning(parent, "FlowScroll", "FlowScroll is already running.")
    return False

def main():
    setup_environment()
    logging.info("Starting FlowScroll application...")
    
    app = QApplication(sys.argv)
    app.setApplicationName("FlowScroll")

    shared_memory = QSharedMemory("FlowScrollRunningLock_v4")
    if not enforce_single_instance(shared_memory):
        sys.exit(0)

    
    # Load Config to get Theme
    config_manager = ConfigManager()
    theme_mode = config_manager.settings.get("theme", "dark")

    # Determine and apply theme
    try:
        actual_theme = theme_mode.lower()
        if actual_theme == "auto":
            stylesheet = qdarktheme.load_stylesheet("dark" if darkdetect.isDark() else "light")
        else:
            stylesheet = qdarktheme.load_stylesheet(actual_theme)
        
        app.setStyleSheet(stylesheet)
    except Exception as e:
        logging.warning(f"Failed to apply qdarktheme: {e}")
        # Fallback
        try:
            app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
        except Exception:
            pass

    try:
        window = MainWindow()
        window.show()
        
        exit_code = app.exec()
        
        logging.info("Application exiting with code: %d", exit_code)
        sys.exit(exit_code)
        
    except Exception as e:
        logging.critical(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
