import sys
import os
import pytest
from PyQt6.QtWidgets import QApplication

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.core.version import APP_VERSION

@pytest.fixture(scope="session")
def qapp():
    # Only create QApplication once per session
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

def test_imports(qapp):
    """Test that main modules can be imported."""
    try:
        from src.gui.main_window import MainWindow
        assert MainWindow is not None
    except ImportError as e:
        pytest.fail(f"Could not import MainWindow: {e}")

def test_mainwindow_title(qapp):
    """Test that MainWindow has correct title."""
    try:
        from src.gui.main_window import MainWindow
        window = MainWindow()
        assert window.windowTitle() == f"FlowScroll v{APP_VERSION}"
        window.close()
    except ImportError as e:
        pytest.fail(f"Could not import MainWindow: {e}")

if __name__ == "__main__":
    pytest.main([__file__])
