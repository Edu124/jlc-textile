import os
import shutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFormLayout, QGroupBox, QMessageBox, QTextEdit, QFileDialog,
    QCheckBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
import core.database as db
from ui.styles import C
from utils.image_tools import process_logo


class SettingsScreen(QWidget):
    def __init__(self, app_dir: str = "", parent=None):
        super().__init__(parent)
        self._app_dir = app_dir
        self._logo_path = db.get_setting("logo_path", "")
        self._build_ui()

    def _build_ui(self):
        # Scrollable so the long settings page never crams its rows together.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        outer.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet(f"background-color: {C.BG};")
        scroll.setWidget(content)

        lay = QVBoxLayout(content)
        lay.setContentsMargins(32, 24, 32, 28)
        lay.setSpacing(20)

        title = QLabel("Settings")
        title.setObjectName("section_title")
        lay.addWidget(title)

        # ── Company Info ──
        company_box = QGroupBox("Company Information (printed on bills)")
        company_lay = QFormLayout(company_box)
        company_lay.setSpacing(10)
        company_lay.setContentsMargins(16, 20, 16, 16)
        company_lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._company_name = self._field("Company name", db.get_setting("company_name", "Jai Laxmi Creation"))
        self._tagline = self._field("e.g. MFG. OF EXCLUSIVE SALWAR KAMEEZ", db.get_setting("company_tagline", ""))
        self._gst_number = self._field("GST Registration Number", db.get_setting("gst_number", ""))
        self._phone = self._field("Mobile / contact number", db.get_setting("phone", ""))
        self._email = self._field("Email address", db.get_setting("email", ""))
        self._instagram = self._field("Instagram handle", db.get_setting("instagram", ""))

        self._address = QTextEdit()
        self._address.setFixedHeight(60)
        self._address.setPlaceholderText("Shop address")
        self._address.setText(db.get_setting("address", ""))

        company_lay.addRow("Company Name *", self._company_name)
        company_lay.addRow("Tagline", self._tagline)
        company_lay.addRow("GST Number", self._gst_number)
        company_lay.addRow("Mobile", self._phone)
        company_lay.addRow("Email", self._email)
        company_lay.addRow("Instagram", self._instagram)
        company_lay.addRow("Address", self._address)
        lay.addWidget(company_box)

        # ── Logo ──
        logo_box = QGroupBox("Company Logo (top-left of order form)")
        logo_lay = QHBoxLayout(logo_box)
        logo_lay.setContentsMargins(16, 20, 16, 16)
        logo_lay.setSpacing(16)

        self._logo_preview = QLabel()
        self._logo_preview.setFixedSize(90, 90)
        self._logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._logo_preview.setStyleSheet(
            "background:#2C2C2E; border:1px solid #48484A; border-radius:10px; color:#8E8E93;"
        )
        self._refresh_logo_preview()

        logo_btn_col = QVBoxLayout()
        logo_btn_col.setSpacing(8)
        browse = QPushButton("Browse Logo Image…")
        browse.setFixedHeight(34)
        browse.clicked.connect(self._pick_logo)
        clear = QPushButton("Remove Logo")
        clear.setObjectName("btn_danger")
        clear.setFixedHeight(34)
        clear.clicked.connect(self._clear_logo)

        self._remove_bg = QCheckBox("Auto-remove logo background")
        self._remove_bg.setChecked(True)
        self._remove_bg.toggled.connect(self._reprocess_logo)

        hint = QLabel("Tip: a photo/scan of a logo has a coloured background. "
                      "Keep this ticked to drop the background so the logo sits "
                      "cleanly on the form. Untick if your logo is already a clean PNG.")
        hint.setStyleSheet("color:#8E8E93; font-size:11px;")
        hint.setWordWrap(True)
        logo_btn_col.addWidget(browse)
        logo_btn_col.addWidget(clear)
        logo_btn_col.addWidget(self._remove_bg)
        logo_btn_col.addWidget(hint)
        logo_btn_col.addStretch()

        logo_lay.addWidget(self._logo_preview)
        logo_lay.addLayout(logo_btn_col, 1)
        lay.addWidget(logo_box)

        # ── AI Settings ──
        ai_box = QGroupBox("AI Settings")
        ai_lay = QFormLayout(ai_box)
        ai_lay.setSpacing(10)
        ai_lay.setContentsMargins(16, 20, 16, 16)
        ai_lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._api_key = QLineEdit()
        self._api_key.setFixedHeight(34)
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText("Stability AI API Key (for image-to-image)")
        self._api_key.setText(db.get_setting("ai_api_key", ""))

        ai_hint = QLabel(
            "Text→Image uses Pollinations.ai (free, no key needed).\n"
            "Image→Image requires a Stability AI API key from stability.ai"
        )
        ai_hint.setStyleSheet("color: #8E8E93; font-size: 11px;")
        ai_hint.setWordWrap(True)

        ai_lay.addRow("Stability AI Key", self._api_key)
        ai_lay.addRow("", ai_hint)
        lay.addWidget(ai_box)

        # ── Save ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("btn_primary")
        save_btn.setFixedHeight(38)
        save_btn.setFixedWidth(160)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)
        lay.addStretch()

    def _field(self, placeholder: str, value: str) -> QLineEdit:
        f = QLineEdit()
        f.setFixedHeight(34)
        f.setPlaceholderText(placeholder)
        f.setText(value)
        return f

    def _refresh_logo_preview(self):
        if self._logo_path and os.path.exists(self._logo_path):
            px = QPixmap(self._logo_path).scaled(
                86, 86, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self._logo_preview.setPixmap(px)
        else:
            self._logo_preview.setText("No logo")

    def _pick_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Logo Image", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return
        try:
            dest_dir = os.path.join(self._app_dir, "images")
            os.makedirs(dest_dir, exist_ok=True)
            # Keep an untouched copy so the background toggle can re-run.
            ext = os.path.splitext(path)[1].lower()
            original = os.path.join(dest_dir, f"company_logo_original{ext}")
            shutil.copy2(path, original)
            self._logo_original = original
            self._apply_logo()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load logo:\n{e}")

    def _apply_logo(self):
        """Produce the final logo PNG from the stored original, honouring
        the 'remove background' toggle."""
        if not getattr(self, "_logo_original", "") or not os.path.exists(self._logo_original):
            return
        dest = os.path.join(self._app_dir, "images", "company_logo.png")
        try:
            process_logo(self._logo_original, dest,
                         remove_bg=self._remove_bg.isChecked())
            self._logo_path = dest
            self._refresh_logo_preview()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not process logo:\n{e}")

    def _reprocess_logo(self):
        # Re-run processing when the user toggles the background option.
        if getattr(self, "_logo_original", ""):
            self._apply_logo()

    def _clear_logo(self):
        self._logo_path = ""
        self._logo_original = ""
        self._refresh_logo_preview()

    def _save(self):
        db.set_setting("company_name", self._company_name.text().strip())
        db.set_setting("company_tagline", self._tagline.text().strip())
        db.set_setting("gst_number", self._gst_number.text().strip().upper())
        db.set_setting("phone", self._phone.text().strip())
        db.set_setting("email", self._email.text().strip())
        db.set_setting("instagram", self._instagram.text().strip())
        db.set_setting("address", self._address.toPlainText().strip())
        db.set_setting("ai_api_key", self._api_key.text().strip())
        db.set_setting("logo_path", self._logo_path)
        # Uploading an image switches to image mode; otherwise keep the drawn
        # vector logo.
        db.set_setting("logo_mode", "image" if self._logo_path else "vector")
        QMessageBox.information(self, "Saved", "Settings saved successfully.")

    def refresh(self):
        self._company_name.setText(db.get_setting("company_name", "Jai Laxmi Creation"))
        self._tagline.setText(db.get_setting("company_tagline", ""))
        self._gst_number.setText(db.get_setting("gst_number", ""))
        self._phone.setText(db.get_setting("phone", ""))
        self._email.setText(db.get_setting("email", ""))
        self._instagram.setText(db.get_setting("instagram", ""))
        self._address.setText(db.get_setting("address", ""))
        self._api_key.setText(db.get_setting("ai_api_key", ""))
        self._logo_path = db.get_setting("logo_path", "")
        self._refresh_logo_preview()
