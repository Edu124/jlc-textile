import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from core import pendrive


class DriveSelectorScreen(QWidget):
    drive_selected = pyqtSignal(str, str)  # app_dir, drive_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._refresh_drives()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_drives)
        self._timer.start(3000)

    def _build_ui(self):
        self.setStyleSheet("background-color: #161618;")
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        center = QFrame()
        center.setFixedWidth(520)
        center.setStyleSheet(
            "QFrame { background-color: #2C2C2E; border: 1px solid #38383A;"
            "border-radius: 12px; }"
        )
        cl = QVBoxLayout(center)
        cl.setContentsMargins(40, 36, 40, 36)
        cl.setSpacing(24)

        # Header
        hdr = QVBoxLayout()
        hdr.setSpacing(6)
        title = QLabel("JLC TEXTILE MANAGER")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "font-size: 22px; font-weight: 800; color: #F5F5F7;"
            "letter-spacing: 2px; background: transparent; border: none;"
        )
        sub = QLabel("Select the pendrive where your data will be stored")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(
            "font-size: 13px; color: #8E8E93; background: transparent; border: none;"
        )
        hdr.addWidget(title)
        hdr.addWidget(sub)
        cl.addLayout(hdr)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #38383A; border: none; max-height: 1px;")
        cl.addWidget(sep)

        # Drive list
        list_lbl = QLabel("AVAILABLE DRIVES")
        list_lbl.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: #8E8E93;"
            "letter-spacing: 1px; background: transparent; border: none;"
        )
        cl.addWidget(list_lbl)

        self._list = QListWidget()
        self._list.setFixedHeight(200)
        self._list.setStyleSheet("""
            QListWidget {
                background-color: #1C1C1E;
                border: 1px solid #38383A;
                border-radius: 12px;
                outline: none;
            }
            QListWidget::item {
                color: #C7C7CC;
                padding: 14px 16px;
                border-bottom: 1px solid #2C2C2E;
            }
            QListWidget::item:selected {
                background-color: #1E3A5F;
                color: #F5F5F7;
                border-left: 3px solid #5E7E9B;
            }
            QListWidget::item:hover {
                background-color: #2C2C2E;
            }
        """)
        self._list.itemDoubleClicked.connect(self._on_select)
        cl.addWidget(self._list)

        # Status
        self._status_lbl = QLabel("")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setStyleSheet(
            "font-size: 12px; color: #5FB07C; background: transparent; border: none;"
        )
        self._status_lbl.hide()
        cl.addWidget(self._status_lbl)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.setFixedHeight(38)
        self._refresh_btn.setStyleSheet(
            "background-color: #2C2C2E; border: 1px solid #48484A; color: #AEAEB2;"
            "border-radius: 12px; font-size: 13px;"
        )
        self._refresh_btn.clicked.connect(self._refresh_drives)

        self._select_btn = QPushButton("Use Selected Drive")
        self._select_btn.setObjectName("btn_primary")
        self._select_btn.setFixedHeight(38)
        self._select_btn.setStyleSheet(
            "QPushButton { background-color: #5E7E9B; border: 1px solid #6E8FAC;"
            "color: #FFFFFF; border-radius: 12px; font-size: 13px; font-weight: 600; }"
            "QPushButton:hover { background-color: #6E8FAC; color: #ffffff; }"
        )
        self._select_btn.clicked.connect(self._on_select)

        btn_row.addWidget(self._refresh_btn)
        btn_row.addWidget(self._select_btn, 1)
        cl.addLayout(btn_row)

        # No pendrive hint
        hint = QLabel("Insert your pendrive and click Refresh, or double-click a drive above.")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "font-size: 11px; color: #8E8E93; background: transparent; border: none;"
        )
        cl.addWidget(hint)

        root.addStretch()
        root.addWidget(center, 0, Qt.AlignmentFlag.AlignCenter)
        root.addStretch()

        self._drives = []

    def _refresh_drives(self):
        self._drives = pendrive.get_removable_drives()
        self._list.clear()

        if not self._drives:
            item = QListWidgetItem("  No removable drives detected")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setForeground(Qt.GlobalColor.darkGray)
            self._list.addItem(item)
            return

        for d in self._drives:
            text = f"  {d['letter']}:\\   {d['label']}   —   {d['free_gb']} GB free"
            self._list.addItem(text)

    def _on_select(self):
        idx = self._list.currentRow()
        if idx < 0 or idx >= len(self._drives):
            QMessageBox.warning(self, "No Drive Selected", "Please select a drive from the list.")
            return
        drive = self._drives[idx]
        app_dir = pendrive.setup_drive_folder(drive["path"])
        pendrive.save_config(drive["path"], drive["serial"])
        self._timer.stop()
        self.drive_selected.emit(app_dir, drive["path"])
