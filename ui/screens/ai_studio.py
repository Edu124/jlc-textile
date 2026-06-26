import os
import requests
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QFileDialog, QScrollArea, QFrame,
    QComboBox, QMessageBox, QProgressBar, QSizePolicy, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QPixmap
import core.database as db
from ui.widgets.components import SectionHeader, HSep


class _GenerateWorker(QObject):
    finished = pyqtSignal(bytes, str)  # image_bytes, error
    progress = pyqtSignal(str)

    def __init__(self, prompt: str, mode: str, source_path: str, api_key: str):
        super().__init__()
        self._prompt = prompt
        self._mode = mode
        self._source_path = source_path
        self._api_key = api_key

    def run(self):
        try:
            if self._mode == "text_to_image":
                data = self._text_to_image()
            else:
                data = self._image_to_image()
            self.finished.emit(data, "")
        except Exception as e:
            self.finished.emit(b"", str(e))

    def _text_to_image(self) -> bytes:
        self.progress.emit("Generating image from text...")
        encoded = requests.utils.quote(self._prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            "?width=512&height=512&nologo=true&model=flux"
        )
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return resp.content

    def _image_to_image(self) -> bytes:
        if not self._api_key:
            raise ValueError(
                "Stability AI API key required for image-to-image.\n"
                "Add your key in Settings → AI API Key."
            )
        self.progress.emit("Sending image for transformation...")
        with open(self._source_path, "rb") as f:
            img_data = f.read()

        resp = requests.post(
            "https://api.stability.ai/v1/generation/stable-diffusion-v1-6/image-to-image",
            headers={"Authorization": f"Bearer {self._api_key}"},
            files={"init_image": img_data},
            data={
                "text_prompts[0][text]": self._prompt,
                "text_prompts[0][weight]": 1,
                "image_strength": 0.35,
                "steps": 30,
            },
            timeout=90
        )
        resp.raise_for_status()
        import base64
        artifacts = resp.json().get("artifacts", [])
        if not artifacts:
            raise ValueError("No image returned from API.")
        return base64.b64decode(artifacts[0]["base64"])


class AIStudioScreen(QWidget):
    def __init__(self, app_dir: str, parent=None):
        super().__init__(parent)
        self._app_dir = app_dir
        self._source_path = ""
        self._result_bytes = b""
        self._thread = None
        self._worker = None
        self._build_ui()
        self._load_gallery()

    def _build_ui(self):
        main = QHBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # Left panel — generation controls
        left = QWidget()
        left.setFixedWidth(360)
        left.setStyleSheet("background-color: #1C1C1E; border-right: 1px solid #2C2C2E;")
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(20, 20, 20, 20)
        left_lay.setSpacing(14)

        title = QLabel("AI DESIGN STUDIO")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #C7C7CC; letter-spacing: 1px;")
        left_lay.addWidget(title)
        left_lay.addWidget(HSep())

        # Mode
        mode_lbl = QLabel("Generation Mode")
        mode_lbl.setStyleSheet("font-size: 11px; color: #AEAEB2; font-weight: 700;")
        left_lay.addWidget(mode_lbl)

        self._mode = QComboBox()
        self._mode.setFixedHeight(36)
        self._mode.addItems(["Text → Image", "Image → Image"])
        self._mode.currentIndexChanged.connect(self._on_mode_change)
        left_lay.addWidget(self._mode)

        # Prompt
        prompt_lbl = QLabel("Describe the design *")
        prompt_lbl.setStyleSheet("font-size: 11px; color: #AEAEB2; font-weight: 700;")
        left_lay.addWidget(prompt_lbl)

        self._prompt = QTextEdit()
        self._prompt.setFixedHeight(100)
        self._prompt.setPlaceholderText(
            "e.g. blue floral pattern on white cotton fabric, "
            "traditional Indian motif, high resolution..."
        )
        left_lay.addWidget(self._prompt)

        # Presets
        preset_lbl = QLabel("Quick Styles")
        preset_lbl.setStyleSheet("font-size: 11px; color: #AEAEB2; font-weight: 700;")
        left_lay.addWidget(preset_lbl)

        preset_grid = QGridLayout()
        preset_grid.setSpacing(6)
        presets = [
            ("Floral", "floral pattern"),
            ("Geometric", "geometric pattern"),
            ("Paisley", "paisley motif"),
            ("Stripes", "striped fabric"),
            ("Checks", "checkered pattern"),
            ("Abstract", "abstract art print"),
        ]
        for i, (label, text) in enumerate(presets):
            btn = QPushButton(label)
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                "QPushButton { background:#2C2C2E; border:1px solid #48484A; "
                "color:#AEAEB2; border-radius:10px; font-size: 11px; }"
                "QPushButton:hover { background:#48484A; color:#F5F5F7; }"
            )
            btn.clicked.connect(lambda _, t=text: self._append_preset(t))
            preset_grid.addWidget(btn, i // 3, i % 3)
        left_lay.addLayout(preset_grid)

        # Source image (for img2img)
        self._source_frame = QFrame()
        src_lay = QVBoxLayout(self._source_frame)
        src_lay.setContentsMargins(0, 0, 0, 0)
        src_lay.setSpacing(6)
        src_lbl = QLabel("Source Image *")
        src_lbl.setStyleSheet("font-size: 11px; color: #AEAEB2; font-weight: 700;")
        src_lay.addWidget(src_lbl)

        src_row = QHBoxLayout()
        self._src_preview = QLabel("No image selected")
        self._src_preview.setFixedSize(80, 80)
        self._src_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._src_preview.setStyleSheet(
            "background:#2C2C2E; border:1px solid #48484A; border-radius:10px; color:#8E8E93; font-size:11px;"
        )
        src_row.addWidget(self._src_preview)
        browse_btn = QPushButton("Browse Image")
        browse_btn.setFixedHeight(34)
        browse_btn.clicked.connect(self._browse_source)
        src_row.addWidget(browse_btn)
        src_row.addStretch()
        src_lay.addLayout(src_row)
        self._source_frame.hide()
        left_lay.addWidget(self._source_frame)

        # Name
        name_lbl = QLabel("Design Name")
        name_lbl.setStyleSheet("font-size: 11px; color: #AEAEB2; font-weight: 700;")
        left_lay.addWidget(name_lbl)
        self._name = QLineEdit()
        self._name.setFixedHeight(34)
        self._name.setPlaceholderText("Give this design a name (optional)")
        left_lay.addWidget(self._name)

        left_lay.addStretch()

        # Progress
        self._progress_lbl = QLabel("")
        self._progress_lbl.setStyleSheet("font-size: 11px; color: #5E7E9B;")
        self._progress_lbl.hide()
        left_lay.addWidget(self._progress_lbl)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        self._progress_bar.hide()
        left_lay.addWidget(self._progress_bar)

        # Generate button
        self._gen_btn = QPushButton("✦  Generate Design")
        self._gen_btn.setObjectName("btn_primary")
        self._gen_btn.setFixedHeight(42)
        self._gen_btn.setStyleSheet(
            "QPushButton { background-color: #5E7E9B; border: 1px solid #6E8FAC;"
            "color: #FFFFFF; font-size: 14px; font-weight: 700; border-radius: 12px; }"
            "QPushButton:hover { background-color: #6E8FAC; color: #fff; }"
        )
        self._gen_btn.clicked.connect(self._generate)
        left_lay.addWidget(self._gen_btn)

        hint = QLabel("Text→Image uses free Pollinations.ai API (no key needed).\nImage→Image requires Stability AI key (set in Settings).")
        hint.setStyleSheet("font-size: 10px; color: #8E8E93;")
        hint.setWordWrap(True)
        left_lay.addWidget(hint)

        main.addWidget(left)

        # Right panel — result + gallery
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(20, 20, 20, 20)
        right_lay.setSpacing(14)

        # Result area
        result_lbl = QLabel("GENERATED DESIGN")
        result_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #8E8E93; letter-spacing: 1px;")
        right_lay.addWidget(result_lbl)

        result_frame = QFrame()
        result_frame.setObjectName("card")
        result_frame.setFixedHeight(300)
        result_fl = QVBoxLayout(result_frame)
        result_fl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._result_img = QLabel("Generate a design to see it here")
        self._result_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_img.setStyleSheet("color: #8E8E93; font-size: 13px;")
        self._result_img.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        result_fl.addWidget(self._result_img)
        right_lay.addWidget(result_frame)

        # Save button
        save_row = QHBoxLayout()
        save_row.addStretch()
        self._save_btn = QPushButton("Save to Gallery")
        self._save_btn.setObjectName("btn_success")
        self._save_btn.setFixedHeight(34)
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_design)
        save_row.addWidget(self._save_btn)
        right_lay.addLayout(save_row)

        right_lay.addWidget(HSep())

        gallery_lbl = QLabel("DESIGN GALLERY")
        gallery_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #8E8E93; letter-spacing: 1px;")
        right_lay.addWidget(gallery_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._gallery_w = QWidget()
        self._gallery_lay = QHBoxLayout(self._gallery_w)
        self._gallery_lay.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._gallery_lay.setSpacing(10)
        scroll.setWidget(self._gallery_w)
        right_lay.addWidget(scroll, 1)

        main.addWidget(right, 1)

    def _on_mode_change(self, idx):
        self._source_frame.setVisible(idx == 1)

    def _append_preset(self, text: str):
        cur = self._prompt.toPlainText().strip()
        if cur:
            self._prompt.setText(cur + ", " + text)
        else:
            self._prompt.setText(text)

    def _browse_source(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Source Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if path:
            self._source_path = path
            px = QPixmap(path).scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation)
            self._src_preview.setPixmap(px)

    def _generate(self):
        prompt = self._prompt.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Required", "Please enter a design description.")
            return

        mode = "text_to_image" if self._mode.currentIndex() == 0 else "image_to_image"

        if mode == "image_to_image" and not self._source_path:
            QMessageBox.warning(self, "Required", "Please select a source image for Image→Image mode.")
            return

        api_key = db.get_setting("ai_api_key", "")

        self._gen_btn.setEnabled(False)
        self._progress_lbl.setText("Connecting to AI service...")
        self._progress_lbl.show()
        self._progress_bar.show()

        self._thread = QThread()
        self._worker = _GenerateWorker(prompt, mode, self._source_path, api_key)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_generated)
        self._worker.progress.connect(lambda msg: self._progress_lbl.setText(msg))
        self._thread.start()

    def _on_generated(self, data: bytes, error: str):
        self._thread.quit()
        self._gen_btn.setEnabled(True)
        self._progress_bar.hide()
        self._progress_lbl.hide()

        if error:
            QMessageBox.critical(self, "Generation Failed", error)
            return

        self._result_bytes = data
        px = QPixmap()
        px.loadFromData(data)
        scaled = px.scaled(
            self._result_img.width() - 20, 260,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._result_img.setPixmap(scaled)
        self._save_btn.setEnabled(True)

    def _save_design(self):
        if not self._result_bytes:
            return
        dest_dir = os.path.join(self._app_dir, "images", "ai_designs")
        os.makedirs(dest_dir, exist_ok=True)
        import time
        fname = f"design_{int(time.time())}.png"
        path = os.path.join(dest_dir, fname)
        with open(path, "wb") as f:
            f.write(self._result_bytes)

        name = self._name.text().strip() or fname
        mode = "text_to_image" if self._mode.currentIndex() == 0 else "image_to_image"
        prompt = self._prompt.toPlainText().strip()
        db.execute(
            """INSERT INTO ai_designs (name, prompt, style, source_image_path, result_image_path)
               VALUES (?,?,?,?,?)""",
            (name, prompt, mode, self._source_path or None, path)
        )
        QMessageBox.information(self, "Saved", f"Design saved to gallery!\n{path}")
        self._load_gallery()

    def _load_gallery(self):
        # Clear
        while self._gallery_lay.count():
            child = self._gallery_lay.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        designs = db.fetchall(
            "SELECT id, name, result_image_path, created_at FROM ai_designs ORDER BY id DESC LIMIT 20"
        )
        if not designs:
            empty = QLabel("No designs generated yet")
            empty.setStyleSheet("color: #8E8E93; font-size: 12px;")
            self._gallery_lay.addWidget(empty)
            return

        for d in designs:
            card = QWidget()
            card.setFixedWidth(120)
            card.setStyleSheet(
                "QWidget { background: #2C2C2E; border: 1px solid #38383A; border-radius: 12px; }"
            )
            cl = QVBoxLayout(card)
            cl.setContentsMargins(6, 6, 6, 6)
            cl.setSpacing(4)

            img_lbl = QLabel()
            img_lbl.setFixedSize(108, 90)
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if d["result_image_path"] and os.path.exists(d["result_image_path"]):
                px = QPixmap(d["result_image_path"]).scaled(
                    108, 90, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                img_lbl.setPixmap(px)
            else:
                img_lbl.setStyleSheet("background:#111; border-radius:10px; color:#444;")
                img_lbl.setText("No image")

            name_lbl = QLabel(d["name"] or "")
            name_lbl.setStyleSheet("font-size: 10px; color: #AEAEB2; border: none;")
            name_lbl.setWordWrap(True)
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            cl.addWidget(img_lbl)
            cl.addWidget(name_lbl)
            self._gallery_lay.addWidget(card)

        self._gallery_lay.addStretch()

    def refresh(self):
        self._load_gallery()
