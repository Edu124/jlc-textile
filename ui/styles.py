# ═══════════════════════════════════════════════════════════════════════════
#  JLC Textile Manager — iOS-style Elevated Dark Theme
#  Layered greys (never pure black) + high-contrast text + soft rounded surfaces
# ═══════════════════════════════════════════════════════════════════════════

# ── Palette (iOS dark-mode system colors) ──────────────────────────────────
class C:
    # Backgrounds — elevated layers
    BG          = "#1C1C1E"   # app base
    BG_SIDEBAR  = "#161618"   # sidebar (slightly recessed)
    SURFACE     = "#2C2C2E"   # cards / inputs (raised one level)
    SURFACE_2   = "#3A3A3C"   # raised two levels / hovered input
    SURFACE_3   = "#48484A"   # strong fill

    # Separators / borders (opaque & visible even when dimmed)
    SEPARATOR   = "#38383A"
    BORDER      = "#48484A"

    # Text
    TEXT        = "#F5F5F7"   # primary label
    TEXT_2      = "#C7C7CC"   # secondary
    TEXT_3      = "#AEAEB2"   # tertiary (form labels)
    TEXT_MUTED  = "#8E8E93"   # quaternary (hints, captions)

    # Accents — muted, professional (steel blue-grey primary)
    BLUE        = "#5E7E9B"   # muted steel-blue (primary accent)
    BLUE_HOVER  = "#6E8FAC"
    BLUE_PRESS  = "#4E6B85"
    BLUE_SOFT   = "#2B3845"   # steel-tinted fill
    GREEN       = "#5FB07C"   # muted sage-green (success)
    GREEN_SOFT  = "#1E3325"
    RED         = "#D9685F"   # muted terracotta (danger)
    RED_SOFT    = "#36211F"
    ORANGE      = "#D9A45B"   # muted amber (warning)
    ORANGE_SOFT = "#332919"
    TEAL        = "#7FA8B8"   # muted steel-teal (info)
    PURPLE      = "#9B85B0"
    INDIGO      = "#7E84C0"


DARK = f"""
/* ── Base ─────────────────────────────────────────────── */
QMainWindow, QWidget {{
    background-color: {C.BG};
    color: {C.TEXT};
    font-family: "Segoe UI", "SF Pro Display", Arial, sans-serif;
    font-size: 13px;
}}

QDialog {{
    background-color: {C.BG};
    color: {C.TEXT};
}}

/* ── Sidebar ──────────────────────────────────────────── */
#sidebar {{
    background-color: {C.BG_SIDEBAR};
    border-right: 1px solid {C.SEPARATOR};
}}

#logo_area {{
    background-color: {C.BG_SIDEBAR};
    border-bottom: 1px solid {C.SEPARATOR};
}}

#app_title {{
    font-size: 17px;
    font-weight: 800;
    color: {C.TEXT};
    letter-spacing: 1px;
}}

#app_sub {{
    font-size: 10px;
    color: {C.TEXT_MUTED};
    letter-spacing: 1.5px;
}}

#section_label {{
    font-size: 11px;
    font-weight: 700;
    color: {C.TEXT_MUTED};
    letter-spacing: 1px;
    padding: 18px 20px 6px 20px;
    text-transform: uppercase;
}}

#nav_btn {{
    background: transparent;
    border: none;
    color: {C.TEXT_3};
    text-align: left;
    padding: 10px 16px;
    margin: 1px 10px;
    font-size: 13px;
    border-radius: 10px;
}}
#nav_btn:hover {{
    background-color: {C.SURFACE};
    color: {C.TEXT};
}}
#nav_btn[active="true"] {{
    background-color: {C.BLUE};
    color: #FFFFFF;
    font-weight: 600;
}}

#sub_nav_btn {{
    background: transparent;
    border: none;
    color: {C.TEXT_MUTED};
    text-align: left;
    padding: 8px 16px 8px 38px;
    margin: 1px 10px;
    font-size: 12px;
    border-radius: 8px;
}}
#sub_nav_btn:hover {{
    background-color: {C.SURFACE};
    color: {C.TEXT_2};
}}
#sub_nav_btn[active="true"] {{
    background-color: {C.SURFACE};
    color: {C.TEXT};
}}

#drive_status {{
    background-color: {C.BG_SIDEBAR};
    border-top: 1px solid {C.SEPARATOR};
    padding: 10px 16px;
}}

#drive_label {{
    font-size: 11px;
    color: {C.GREEN};
}}

#drive_label_warn {{
    font-size: 11px;
    color: {C.RED};
}}

/* ── Top Bar ──────────────────────────────────────────── */
#topbar {{
    background-color: {C.BG};
    border-bottom: 1px solid {C.SEPARATOR};
    min-height: 58px;
    max-height: 58px;
}}

#page_title {{
    font-size: 20px;
    font-weight: 800;
    color: {C.TEXT};
}}

#breadcrumb {{
    font-size: 11px;
    color: {C.TEXT_MUTED};
}}

/* ── Content Area ─────────────────────────────────────── */
#content_area {{
    background-color: {C.BG};
}}

/* ── Cards / Stat Cards ───────────────────────────────── */
#stat_card {{
    background-color: {C.SURFACE};
    border: 1px solid {C.SEPARATOR};
    border-radius: 16px;
}}

#stat_value {{
    font-size: 28px;
    font-weight: 800;
    color: {C.TEXT};
}}

#stat_label {{
    font-size: 11px;
    color: {C.TEXT_MUTED};
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

#stat_icon {{
    font-size: 22px;
    color: {C.BLUE};
}}

#card {{
    background-color: {C.SURFACE};
    border: 1px solid {C.SEPARATOR};
    border-radius: 16px;
}}

#card_title {{
    font-size: 12px;
    font-weight: 700;
    color: {C.TEXT_MUTED};
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}

/* ── Section Headers ──────────────────────────────────── */
#page_heading {{
    font-size: 22px;
    font-weight: 800;
    color: {C.TEXT};
}}

#section_title {{
    font-size: 18px;
    font-weight: 700;
    color: {C.TEXT};
    padding: 0;
    margin: 0;
}}

/* ── Tables ───────────────────────────────────────────── */
QTableWidget {{
    background-color: {C.SURFACE};
    alternate-background-color: #313134;
    gridline-color: transparent;
    border: 1px solid {C.SEPARATOR};
    border-radius: 14px;
    selection-background-color: {C.BLUE_SOFT};
    selection-color: {C.TEXT};
    outline: none;
}}

QTableWidget::item {{
    padding: 4px 14px;
    border: none;
    border-bottom: 1px solid {C.SEPARATOR};
    color: {C.TEXT_2};
}}

QTableWidget::item:selected {{
    background-color: {C.BLUE_SOFT};
    color: {C.TEXT};
}}

QTableWidget::item:hover {{
    background-color: {C.SURFACE_2};
}}

QHeaderView::section {{
    background-color: {C.SURFACE};
    color: {C.TEXT_MUTED};
    padding: 12px 14px;
    border: none;
    border-bottom: 1px solid {C.BORDER};
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.6px;
    text-transform: uppercase;
}}

QTableCornerButton::section {{
    background-color: {C.SURFACE};
    border: none;
    border-bottom: 1px solid {C.BORDER};
}}

/* ── Input Fields ─────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {C.SURFACE};
    border: 1px solid {C.SEPARATOR};
    border-radius: 10px;
    color: {C.TEXT};
    padding: 9px 12px;
    selection-background-color: {C.BLUE};
    selection-color: #FFFFFF;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1.5px solid {C.BLUE};
    background-color: {C.SURFACE_2};
}}

QLineEdit:disabled, QTextEdit:disabled {{
    color: {C.TEXT_MUTED};
    background-color: {C.BG};
}}

QLineEdit::placeholder {{
    color: {C.TEXT_MUTED};
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {C.SURFACE};
    border: 1px solid {C.SEPARATOR};
    border-radius: 10px;
    color: {C.TEXT};
    padding: 8px 10px;
    selection-background-color: {C.BLUE};
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1.5px solid {C.BLUE};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background-color: {C.SURFACE_2};
    border: none;
    width: 20px;
    border-radius: 4px;
    margin: 1px;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {C.SURFACE_3};
}}

QDateEdit {{
    background-color: {C.SURFACE};
    border: 1px solid {C.SEPARATOR};
    border-radius: 10px;
    color: {C.TEXT};
    padding: 8px 10px;
}}

QDateEdit:focus {{
    border: 1.5px solid {C.BLUE};
}}

QDateEdit::drop-down {{
    border: none;
    background: {C.SURFACE_2};
    width: 24px;
    border-radius: 0 9px 9px 0;
}}

QCalendarWidget {{
    background-color: {C.SURFACE};
    color: {C.TEXT};
}}

QCalendarWidget QAbstractItemView {{
    background-color: {C.SURFACE};
    selection-background-color: {C.BLUE};
    selection-color: #FFFFFF;
    color: {C.TEXT};
}}

QCalendarWidget QWidget {{
    alternate-background-color: {C.SURFACE_2};
}}

QCalendarWidget QToolButton {{
    color: {C.TEXT};
    background-color: transparent;
}}

/* ── ComboBox ─────────────────────────────────────────── */
QComboBox {{
    background-color: {C.SURFACE};
    border: 1px solid {C.SEPARATOR};
    border-radius: 10px;
    color: {C.TEXT};
    padding: 8px 12px;
    min-width: 120px;
}}

QComboBox:focus, QComboBox:hover {{
    border: 1.5px solid {C.BLUE};
}}

QComboBox::drop-down {{
    border: none;
    background: transparent;
    width: 28px;
}}

QComboBox::down-arrow {{
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {C.TEXT_3};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {C.SURFACE_2};
    border: 1px solid {C.BORDER};
    border-radius: 10px;
    selection-background-color: {C.BLUE};
    selection-color: #FFFFFF;
    color: {C.TEXT};
    padding: 4px;
    outline: none;
}}

QComboBox QAbstractItemView::item {{
    padding: 8px 10px;
    border-radius: 6px;
    min-height: 22px;
}}

/* ── Buttons ──────────────────────────────────────────── */
QPushButton {{
    background-color: {C.SURFACE_2};
    border: 1px solid {C.BORDER};
    border-radius: 10px;
    color: {C.TEXT};
    padding: 9px 18px;
    font-size: 13px;
    font-weight: 500;
    min-height: 32px;
}}

QPushButton:hover {{
    background-color: {C.SURFACE_3};
    border-color: {C.SURFACE_3};
}}

QPushButton:pressed {{
    background-color: {C.SURFACE};
}}

QPushButton:disabled {{
    color: {C.TEXT_MUTED};
    background-color: {C.SURFACE};
    border-color: {C.SEPARATOR};
}}

QPushButton#btn_primary {{
    background-color: {C.BLUE};
    border: none;
    color: #FFFFFF;
    font-weight: 600;
}}
QPushButton#btn_primary:hover {{
    background-color: {C.BLUE_HOVER};
}}
QPushButton#btn_primary:pressed {{
    background-color: {C.BLUE_PRESS};
}}

QPushButton#btn_success {{
    background-color: {C.GREEN};
    border: none;
    color: #0C2114;
    font-weight: 700;
}}
QPushButton#btn_success:hover {{
    background-color: #6FBF8B;
}}

QPushButton#btn_danger {{
    background-color: {C.RED_SOFT};
    border: 1px solid #5A2A28;
    color: {C.RED};
    font-weight: 600;
}}
QPushButton#btn_danger:hover {{
    background-color: #4A2220;
}}

QPushButton#btn_warning {{
    background-color: {C.ORANGE_SOFT};
    border: 1px solid #5A4318;
    color: {C.ORANGE};
    font-weight: 600;
}}
QPushButton#btn_warning:hover {{
    background-color: #4A360F;
}}

QPushButton#btn_flat {{
    background: transparent;
    border: none;
    color: {C.BLUE};
    padding: 4px 10px;
    margin: 0;
    min-height: 0;
    font-weight: 600;
}}
QPushButton#btn_flat:hover {{
    color: {C.BLUE_HOVER};
    background-color: {C.SURFACE_2};
    border-radius: 8px;
}}

/* ── Labels ───────────────────────────────────────────── */
QLabel#lbl_heading {{
    font-size: 24px;
    font-weight: 800;
    color: {C.TEXT};
}}

QLabel#lbl_form {{
    font-size: 13px;
    color: {C.TEXT_3};
    font-weight: 600;
}}

QLabel#lbl_value {{
    font-size: 13px;
    color: {C.TEXT};
}}

QLabel#badge_success {{
    background-color: {C.GREEN_SOFT};
    color: {C.GREEN};
    border-radius: 8px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 700;
}}

QLabel#badge_warning {{
    background-color: {C.ORANGE_SOFT};
    color: {C.ORANGE};
    border-radius: 8px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 700;
}}

QLabel#badge_danger {{
    background-color: {C.RED_SOFT};
    color: {C.RED};
    border-radius: 8px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 700;
}}

QLabel#badge_info {{
    background-color: {C.BLUE_SOFT};
    color: {C.TEAL};
    border-radius: 8px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 700;
}}

/* ── Scrollbar ────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    border-radius: 5px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: {C.SURFACE_3};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {C.TEXT_MUTED};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    height: 0;
    background: none;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    border-radius: 5px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background: {C.SURFACE_3};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {C.TEXT_MUTED};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    background: none;
}}

/* ── GroupBox ─────────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {C.SEPARATOR};
    border-radius: 14px;
    margin-top: 16px;
    padding: 14px 12px 12px 12px;
    background-color: {C.SURFACE};
    color: {C.TEXT_MUTED};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    color: {C.TEXT_3};
}}

/* ── TabWidget ────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {C.SEPARATOR};
    background-color: {C.SURFACE};
    border-radius: 14px;
    top: -1px;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {C.TEXT_MUTED};
    padding: 10px 22px;
    border: none;
    margin-right: 4px;
    border-radius: 9px;
    font-weight: 600;
}}

QTabBar::tab:selected {{
    background-color: {C.SURFACE_2};
    color: {C.TEXT};
}}

QTabBar::tab:hover:!selected {{
    color: {C.TEXT_2};
}}

/* ── MessageBox ───────────────────────────────────────── */
QMessageBox {{
    background-color: {C.SURFACE};
    color: {C.TEXT};
}}

QMessageBox QLabel {{
    color: {C.TEXT};
    font-size: 13px;
}}

/* ── Separators ───────────────────────────────────────── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {C.SEPARATOR};
    background-color: {C.SEPARATOR};
    border: none;
}}

/* ── Tooltips ─────────────────────────────────────────── */
QToolTip {{
    background-color: {C.SURFACE_3};
    color: {C.TEXT};
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ── Status Bar ───────────────────────────────────────── */
QStatusBar {{
    background-color: {C.BG_SIDEBAR};
    color: {C.TEXT_MUTED};
    border-top: 1px solid {C.SEPARATOR};
    font-size: 11px;
}}

/* ── ProgressBar ──────────────────────────────────────── */
QProgressBar {{
    background-color: {C.SURFACE};
    border: 1px solid {C.SEPARATOR};
    border-radius: 6px;
    text-align: center;
    color: {C.TEXT_2};
    height: 10px;
}}

QProgressBar::chunk {{
    background-color: {C.BLUE};
    border-radius: 6px;
}}

/* ── CheckBox ─────────────────────────────────────────── */
QCheckBox {{
    color: {C.TEXT_2};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    background-color: {C.SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: 6px;
}}

QCheckBox::indicator:checked {{
    background-color: {C.BLUE};
    border-color: {C.BLUE};
}}

QCheckBox::indicator:hover {{
    border-color: {C.BLUE};
}}
"""

# ── Status badge colors (bg, fg) — iOS soft fills ──────────────────────────
STATUS_COLORS = {
    "Received":      (C.BLUE_SOFT,   C.TEAL),
    "In Production": (C.ORANGE_SOFT, C.ORANGE),
    "Ready":         (C.GREEN_SOFT,  C.GREEN),
    "Dispatched":    ("#2E1A40",     C.PURPLE),
    "Delivered":     (C.GREEN_SOFT,  C.GREEN),
    "Cancelled":     (C.RED_SOFT,    C.RED),
    "Cutting":       (C.ORANGE_SOFT, C.ORANGE),
    "Stitching":     (C.BLUE_SOFT,   C.TEAL),
    "Dyeing":        ("#2E1A40",     C.PURPLE),
    "Finishing":     ("#10303A",     C.TEAL),
    "QC":            (C.ORANGE_SOFT, C.ORANGE),
    "Completed":     (C.GREEN_SOFT,  C.GREEN),
    "OK":            (C.GREEN_SOFT,  C.GREEN),
    "Low Stock":     (C.RED_SOFT,    C.RED),
}
