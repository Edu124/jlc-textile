from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QFrame, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSortFilterProxyModel
from PyQt6.QtGui import QColor, QFont
from ui.styles import STATUS_COLORS, C


def _hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except (ValueError, IndexError):
        return 10, 132, 255


# ── Stat Card ────────────────────────────────────────────────────────────────

class StatCard(QWidget):
    def __init__(self, label: str, value: str, icon: str, accent_color: str = C.BLUE, parent=None):
        super().__init__(parent)
        self.setObjectName("stat_card")
        self.setMinimumHeight(110)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(16)

        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("stat_icon")
        icon_lbl.setFixedSize(48, 48)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _r, _g, _b = _hex_to_rgb(accent_color)
        icon_lbl.setStyleSheet(
            f"font-size: 24px; color: {accent_color};"
            f"background-color: rgba({_r},{_g},{_b},0.16);"
            "border-radius: 14px; border: none;"
        )

        text_lay = QVBoxLayout()
        text_lay.setSpacing(4)

        self._value_lbl = QLabel(value)
        self._value_lbl.setObjectName("stat_value")

        lbl = QLabel(label.upper())
        lbl.setObjectName("stat_label")

        text_lay.addWidget(self._value_lbl)
        text_lay.addWidget(lbl)

        lay.addWidget(icon_lbl)
        lay.addLayout(text_lay)
        lay.addStretch()

    def set_value(self, val: str):
        self._value_lbl.setText(val)


# ── Section Header ───────────────────────────────────────────────────────────

class SectionHeader(QWidget):
    def __init__(self, title: str, btn_label: str = "", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        t = QLabel(title)
        t.setObjectName("section_title")
        lay.addWidget(t)
        lay.addStretch()

        self.btn = None
        if btn_label:
            self.btn = QPushButton(btn_label)
            self.btn.setObjectName("btn_primary")
            self.btn.setFixedHeight(34)
            lay.addWidget(self.btn)


# ── Searchable ComboBox ───────────────────────────────────────────────────────

class SearchableCombo(QWidget):
    selection_changed = pyqtSignal(object)  # emits (id, text) tuple

    def __init__(self, placeholder="Search or select...", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._search = QLineEdit()
        self._search.setPlaceholderText(placeholder)
        self._search.textChanged.connect(self._filter)

        self._combo = QComboBox()
        self._combo.setMaxVisibleItems(12)
        self._combo.currentIndexChanged.connect(self._on_select)
        self._combo.setFixedWidth(0)
        self._combo.hide()

        self._data = []  # list of (id, label)
        self._filtered = []

        lay.addWidget(self._search)

        self._drop = QComboBox()
        self._drop.setMaxVisibleItems(14)
        self._drop.setEditable(False)
        self._drop.currentIndexChanged.connect(self._on_drop_select)
        lay.addWidget(self._drop)

        self._search.hide()
        lay.removeWidget(self._search)

        self._lay = lay

    def load(self, data: list):
        self._data = [("", "— Select —")] + list(data)
        self._drop.blockSignals(True)
        self._drop.clear()
        for _, label in self._data:
            self._drop.addItem(label)
        self._drop.blockSignals(False)

    def _filter(self, text):
        pass

    def _on_drop_select(self, idx):
        if idx <= 0:
            self.selection_changed.emit((None, ""))
        else:
            item = self._data[idx]
            self.selection_changed.emit(item)

    def _on_select(self, idx):
        pass

    def current_id(self):
        idx = self._drop.currentIndex()
        if idx <= 0:
            return None
        return self._data[idx][0]

    def current_text(self):
        return self._drop.currentText()

    def set_by_id(self, item_id):
        for i, (iid, _) in enumerate(self._data):
            if iid == item_id:
                self._drop.setCurrentIndex(i)
                return

    def clear_selection(self):
        self._drop.setCurrentIndex(0)


# ── DataTable ────────────────────────────────────────────────────────────────

class DataTable(QTableWidget):
    def __init__(self, headers: list, parent=None):
        super().__init__(parent)
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setShowGrid(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Uniform, comfortable row height so status badges and action
        # buttons always fit without clipping.
        vh = self.verticalHeader()
        vh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        vh.setDefaultSectionSize(52)
        self.setSortingEnabled(True)

        # Friendly empty-state overlay (does not add table rows, so screens'
        # row loops stay safe).
        self._empty_text = "Nothing here yet."
        self._empty_label = QLabel(self._empty_text, self.viewport())
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {C.TEXT_MUTED}; font-size: 14px; background: transparent;"
        )
        self._empty_label.hide()

    def set_empty_text(self, text: str):
        self._empty_text = text

    def load_rows(self, rows: list):
        self.setSortingEnabled(False)
        self.setRowCount(0)
        for row_data in rows:
            r = self.rowCount()
            self.insertRow(r)
            for c, val in enumerate(row_data):
                item = QTableWidgetItem(str(val) if val is not None else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.setItem(r, c, item)
        self.setSortingEnabled(True)
        self._update_empty()

    def _update_empty(self):
        if self.rowCount() == 0:
            self._empty_label.setText(self._empty_text)
            self._empty_label.resize(self.viewport().size())
            self._empty_label.move(0, 0)
            self._empty_label.show()
            self._empty_label.raise_()
        else:
            self._empty_label.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_empty_label"):
            self._empty_label.resize(self.viewport().size())

    def selected_row_data(self, col: int = 0):
        rows = self.selectedItems()
        if not rows:
            return None
        r = self.currentRow()
        return self.item(r, col).text() if self.item(r, col) else None

    def add_status_badge(self, row: int, col: int, status: str):
        lbl = QLabel(status)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFixedHeight(26)
        bg, fg = STATUS_COLORS.get(status, (C.SURFACE_2, C.TEXT_MUTED))
        lbl.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: 13px;"
            "padding: 0px 14px; font-size: 11px; font-weight: 700;"
        )
        container = QWidget()
        cl = QHBoxLayout(container)
        cl.setContentsMargins(6, 0, 6, 0)
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addStretch()
        cl.addWidget(lbl)
        cl.addStretch()
        self.setCellWidget(row, col, container)


# ── Horizontal Separator ─────────────────────────────────────────────────────

class HSep(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background-color: {C.SEPARATOR}; border: none;")


# ── Form Row ─────────────────────────────────────────────────────────────────

class FormRow(QHBoxLayout):
    def __init__(self, label: str, widget: QWidget, required: bool = False):
        super().__init__()
        lbl = QLabel(("* " if required else "") + label)
        lbl.setObjectName("lbl_form")
        lbl.setFixedWidth(140)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.addWidget(lbl)
        self.addWidget(widget, 1)


# ── Search Bar ───────────────────────────────────────────────────────────────

class SearchBar(QLineEdit):
    def __init__(self, placeholder="Search...", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(34)
        self.setStyleSheet(
            "QLineEdit { padding-left: 12px; border-radius: 5px; }"
        )


# ── Action Button group ───────────────────────────────────────────────────────

class ActionButtons(QWidget):
    edit_clicked = pyqtSignal()
    delete_clicked = pyqtSignal()
    view_clicked = pyqtSignal()

    def __init__(self, show_view=False, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(4)

        if show_view:
            self._view_btn = QPushButton("View")
            self._view_btn.setObjectName("btn_flat")
            self._view_btn.setFixedHeight(26)
            self._view_btn.clicked.connect(self.view_clicked)
            lay.addWidget(self._view_btn)

        self._edit_btn = QPushButton("Edit")
        self._edit_btn.setObjectName("btn_flat")
        self._edit_btn.setFixedHeight(26)
        self._edit_btn.setStyleSheet(f"color: {C.BLUE};")
        self._edit_btn.clicked.connect(self.edit_clicked)

        self._del_btn = QPushButton("Delete")
        self._del_btn.setObjectName("btn_flat")
        self._del_btn.setFixedHeight(26)
        self._del_btn.setStyleSheet(f"color: {C.RED};")
        self._del_btn.clicked.connect(self.delete_clicked)

        lay.addWidget(self._edit_btn)
        lay.addWidget(self._del_btn)
        lay.addStretch()


# ── Info Panel ────────────────────────────────────────────────────────────────

class InfoPanel(QWidget):
    def __init__(self, rows: list, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        for label, value in rows:
            rl = QHBoxLayout()
            lbl = QLabel(label + ":")
            lbl.setObjectName("lbl_form")
            lbl.setFixedWidth(130)
            val = QLabel(str(value))
            val.setObjectName("lbl_value")
            val.setWordWrap(True)
            rl.addWidget(lbl)
            rl.addWidget(val, 1)
            lay.addLayout(rl)
