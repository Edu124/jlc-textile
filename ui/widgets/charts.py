"""Lightweight, theme-matched charts drawn with QPainter — no extra deps.
BarChart (vertical), HBarChart (horizontal ranked), DonutChart."""
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QRectF, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from ui.styles import C

# Muted categorical palette
PALETTE = ["#5E7E9B", "#5FB07C", "#D9A45B", "#D9685F", "#7FA8B8", "#9B85B0", "#8E9AA8"]


def _qc(hex_or_name: str) -> QColor:
    return QColor(hex_or_name)


class _Base(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._data = []
        self._fmt = lambda v: f"{v:,.0f}"

    def set_data(self, data, fmt=None):
        self._data = data or []
        if fmt:
            self._fmt = fmt
        self.update()

    def _empty(self, p: QPainter):
        p.setPen(_qc(C.TEXT_MUTED))
        f = QFont("Segoe UI", 10)
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No data yet")


class BarChart(_Base):
    """Vertical bars. data = list of (label, value)."""
    def __init__(self, parent=None, accent=None, max_labels=8):
        super().__init__(parent)
        self._accent = accent or C.BLUE
        self._max_labels = max_labels
        self.setMinimumHeight(180)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self._data:
            self._empty(p); return

        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 12, 12, 14, 26
        plot = QRectF(pad_l, pad_t, w - pad_l - pad_r, h - pad_t - pad_b)
        vals = [v for _, v in self._data]
        vmax = max(vals) if vals else 1
        vmax = vmax if vmax > 0 else 1

        # baseline
        p.setPen(QPen(_qc(C.SEPARATOR), 1))
        p.drawLine(int(plot.left()), int(plot.bottom()),
                   int(plot.right()), int(plot.bottom()))

        n = len(self._data)
        gap = max(2.0, plot.width() / n * 0.25)
        bw = (plot.width() - gap * (n - 1)) / n
        label_step = max(1, n // self._max_labels)

        for i, (lab, v) in enumerate(self._data):
            x = plot.left() + i * (bw + gap)
            bh = (v / vmax) * (plot.height() - 4)
            y = plot.bottom() - bh
            rect = QRectF(x, y, bw, bh)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(_qc(self._accent))
            p.drawRoundedRect(rect, min(3, bw / 2), min(3, bw / 2))
            if i % label_step == 0:
                p.setPen(_qc(C.TEXT_MUTED))
                p.setFont(QFont("Segoe UI", 7))
                p.drawText(QRectF(x - 6, plot.bottom() + 3, bw + 12, 18),
                           Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, str(lab))
        p.end()


class HBarChart(_Base):
    """Horizontal ranked bars. data = list of (label, value). Optional colors."""
    def __init__(self, parent=None, accent=None, colored=False):
        super().__init__(parent)
        self._accent = accent or C.BLUE
        self._colored = colored
        self.setMinimumHeight(150)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self._data:
            self._empty(p); return

        w, h = self.width(), self.height()
        vmax = max(v for _, v in self._data) or 1
        n = len(self._data)
        row_h = min(40, (h - 8) / n)
        label_w = 96
        val_w = 60
        bar_x = label_w + 8
        bar_w_full = w - bar_x - val_w - 8

        p.setFont(QFont("Segoe UI", 9))
        for i, (lab, v) in enumerate(self._data):
            y = 4 + i * row_h
            cy = y + row_h / 2
            # label
            p.setPen(_qc(C.TEXT_2))
            p.drawText(QRectF(0, y, label_w, row_h),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, str(lab))
            # track
            bh = min(16, row_h - 12)
            track = QRectF(bar_x, cy - bh / 2, bar_w_full, bh)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(_qc(C.SURFACE_2))
            p.drawRoundedRect(track, bh / 2, bh / 2)
            # bar
            bw = max(2.0, bar_w_full * (v / vmax))
            color = PALETTE[i % len(PALETTE)] if self._colored else self._accent
            p.setBrush(_qc(color))
            p.drawRoundedRect(QRectF(bar_x, cy - bh / 2, bw, bh), bh / 2, bh / 2)
            # value
            p.setPen(_qc(C.TEXT))
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            p.drawText(QRectF(bar_x + bar_w_full + 4, y, val_w, row_h),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._fmt(v))
            p.setFont(QFont("Segoe UI", 9))
        p.end()


class DonutChart(_Base):
    """Donut with legend. data = list of (label, value). Colors auto."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(170)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self._data or sum(v for _, v in self._data) == 0:
            self._empty(p); return

        w, h = self.width(), self.height()
        total = sum(v for _, v in self._data)
        # donut on left square, legend on right
        size = min(h - 16, w * 0.5)
        cx, cy = 8 + size / 2, h / 2
        ring = size * 0.26
        outer = QRectF(cx - size / 2, cy - size / 2, size, size)

        start = 90 * 16
        for i, (lab, v) in enumerate(self._data):
            span = -int(360 * 16 * v / total)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(_qc(PALETTE[i % len(PALETTE)]))
            p.drawPie(outer, start, span)
            start += span
        # punch hole
        p.setBrush(_qc(C.SURFACE))
        hole = QRectF(cx - ring, cy - ring, ring * 2, ring * 2)
        p.drawEllipse(hole)
        # center total
        p.setPen(_qc(C.TEXT))
        p.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        p.drawText(hole, Qt.AlignmentFlag.AlignCenter, f"{total:,.0f}")

        # legend
        lx = 8 + size + 14
        ly = (h - len(self._data) * 22) / 2
        p.setFont(QFont("Segoe UI", 9))
        for i, (lab, v) in enumerate(self._data):
            yy = ly + i * 22
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(_qc(PALETTE[i % len(PALETTE)]))
            p.drawRoundedRect(QRectF(lx, yy + 3, 11, 11), 3, 3)
            p.setPen(_qc(C.TEXT_2))
            p.drawText(QRectF(lx + 18, yy, w - lx - 18, 18),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       f"{lab}  ·  {v:,.0f}")
        p.end()


class CompareBars(_Base):
    """A couple of labelled horizontal bars sharing one scale.
    data = list of (label, value, color)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(110)

    def set_data(self, data, fmt=None):
        self._data = data or []
        if fmt:
            self._fmt = fmt
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self._data:
            self._empty(p); return
        w, h = self.width(), self.height()
        vmax = max(v for _, v, _ in self._data) or 1
        n = len(self._data)
        row_h = (h - 8) / n
        label_w = 90
        bar_x = label_w + 8
        val_w = 80
        bar_full = w - bar_x - val_w - 8
        for i, (lab, v, col) in enumerate(self._data):
            y = 4 + i * row_h
            cy = y + row_h / 2
            p.setPen(_qc(C.TEXT_2)); p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            p.drawText(QRectF(0, y, label_w, row_h),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, str(lab))
            bh = min(18, row_h - 14)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(_qc(C.SURFACE_2))
            p.drawRoundedRect(QRectF(bar_x, cy - bh / 2, bar_full, bh), bh / 2, bh / 2)
            bw = max(2.0, bar_full * (v / vmax))
            p.setBrush(_qc(col))
            p.drawRoundedRect(QRectF(bar_x, cy - bh / 2, bw, bh), bh / 2, bh / 2)
            p.setPen(_qc(C.TEXT)); p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            p.drawText(QRectF(bar_x + bar_full + 4, y, val_w, row_h),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._fmt(v))
        p.end()
