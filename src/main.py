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
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    # Ensure logs directory exists if we want file logging
    log_dir = os.path.join(project_root, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Add file handler
    file_handler = logging.FileHandler(os.path.join(log_dir, 'flowscroll.log'))
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)

def main():
    setup_environment()
    logging.info("Starting FlowScroll application...")
    
    app = QApplication(sys.argv)
    app.setApplicationName("FlowScroll")

    # Single Instance Lock
    # shared_memory = QSharedMemory("FlowScrollRunningLock")
    # Using a simple file-based lock might be more reliable on Windows restart
    # temporarily bypassing strict lock check to ensure startup
    shared_memory = QSharedMemory("FlowScrollRunningLock_v3")
    if not shared_memory.create(1):
        if shared_memory.attach():
            pass # We attached to verify it exists
        logging.warning("Another instance might be running (SharedMemory check failed). Continuing anyway for safety.")
        # msg = QMessageBox()
        # msg.setIcon(QMessageBox.Icon.Warning)
        # msg.setWindowTitle("FlowScroll")
        # msg.setText("FlowScroll is already running!")
        # msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        # msg.exec()
        # sys.exit(0) # BYPASS EXIT to force launch

    
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
