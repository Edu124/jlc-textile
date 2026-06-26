from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


class PlaceholderScreen(QWidget):
    def __init__(self, key: str, error: str = "", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(f"Screen: {key}")
        lbl.setStyleSheet("font-size: 20px; color: #8E8E93;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)
        if error:
            err = QLabel(f"Error: {error}")
            err.setStyleSheet("font-size: 12px; color: #D9685F;")
            err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(err)
