from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel("FlowScroll: Ready")
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 30, 30, 180);
                color: #00FF00;
                padding: 6px;
                border-radius: 4px;
                font-family: Consolas, monospace;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.layout.addWidget(self.label)
        
        self.adjustSize()
        self.move(20, 20)  # Default top-left

    def update_text(self, text):
        self.label.setText(text)
        self.adjustSize()
