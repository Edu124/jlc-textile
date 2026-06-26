from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame,
    QSizePolicy, QScrollArea, QStatusBar
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon
import core.database as db


NAV_ITEMS = [
    ("Dashboard",       "dashboard",      "⊞",  None),
    ("",                "sep",            "",   None),
    ("INVENTORY",       "group",          "",   None),
    ("Raw Materials",   "raw_materials",  "◈",  None),
    ("Finished Goods",  "finished_goods", "◉",  None),
    ("Production",      "production",     "⚙",  None),
    ("",                "sep",            "",   None),
    ("COMMERCE",        "group",          "",   None),
    ("Orders",          "orders",         "◎",  None),
    ("Purchase Bills",  "purchase_bills", "↓",  None),
    ("Sales Bills",     "sales_bills",    "↑",  None),
    ("",                "sep",            "",   None),
    ("MASTERS",         "group",          "",   None),
    ("Suppliers",       "suppliers",      "◷",  None),
    ("Customers",       "customers",      "◶",  None),
    ("Material Types",  "material_types", "◻",  None),
    ("Products",        "products",       "◼",  None),
    ("Units",           "units",          "◫",  None),
    ("",                "sep",            "",   None),
    ("TOOLS",           "group",          "",   None),
    ("AI Design Studio","ai_studio",      "✦",  None),
    ("Reports",         "reports",        "≡",  None),
    ("Settings",        "settings",       "◈",  None),
]


class MainWindow(QMainWindow):
    def __init__(self, app_dir: str, drive_label: str, parent=None):
        super().__init__(parent)
        self._app_dir = app_dir
        self._drive_label = drive_label
        self._screens = {}
        self._nav_btns = {}
        self._current = None

        self.setWindowTitle("JLC Textile Manager")
        self.setMinimumSize(1200, 700)
        self.showMaximized()

        self._build_ui()
        self._navigate("dashboard")

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("main_root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_sidebar())

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        right.addWidget(self._build_topbar())

        self._stack = QStackedWidget()
        self._stack.setObjectName("content_area")
        right.addWidget(self._stack, 1)

        right_w = QWidget()
        right_w.setLayout(right)
        layout.addWidget(right_w, 1)

        status = QStatusBar()
        status.showMessage(f"  Data stored on: {self._drive_label}")
        self.setStatusBar(status)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)

        vlay = QVBoxLayout(sidebar)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        # Logo area
        logo_area = QWidget()
        logo_area.setObjectName("logo_area")
        logo_area.setFixedHeight(72)
        ll = QVBoxLayout(logo_area)
        ll.setContentsMargins(18, 14, 18, 14)
        ll.setSpacing(2)
        t1 = QLabel("JLC")
        t1.setObjectName("app_title")
        t2 = QLabel("TEXTILE MANAGER")
        t2.setObjectName("app_sub")
        ll.addWidget(t1)
        ll.addWidget(t2)
        vlay.addWidget(logo_area)

        # Scrollable nav area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )

        nav_w = QWidget()
        nav_w.setStyleSheet("background: transparent;")
        nav_lay = QVBoxLayout(nav_w)
        nav_lay.setContentsMargins(0, 8, 0, 8)
        nav_lay.setSpacing(0)

        for label, key, icon, _ in NAV_ITEMS:
            if key == "sep":
                sep = QFrame()
                sep.setFixedHeight(1)
                sep.setStyleSheet("background-color: #38383A; margin: 6px 12px;")
                nav_lay.addWidget(sep)
            elif key == "group":
                gl = QLabel(label)
                gl.setObjectName("section_label")
                nav_lay.addWidget(gl)
            else:
                btn = QPushButton(f"  {icon}  {label}")
                btn.setObjectName("nav_btn")
                btn.setFixedHeight(38)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setCheckable(False)
                btn.clicked.connect(lambda _, k=key: self._navigate(k))
                self._nav_btns[key] = btn
                nav_lay.addWidget(btn)

        nav_lay.addStretch()
        scroll.setWidget(nav_w)
        vlay.addWidget(scroll, 1)

        # Drive status
        drive_status = QWidget()
        drive_status.setObjectName("drive_status")
        drive_status.setFixedHeight(48)
        dl = QHBoxLayout(drive_status)
        dl.setContentsMargins(14, 0, 14, 0)
        dl.setSpacing(8)

        dot = QLabel("●")
        dot.setStyleSheet("color: #4caf50; font-size: 10px;")
        lbl = QLabel(f"Drive: {self._drive_label}")
        lbl.setObjectName("drive_label")
        lbl.setWordWrap(False)

        dl.addWidget(dot)
        dl.addWidget(lbl, 1)
        vlay.addWidget(drive_status)

        return sidebar

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("topbar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(12)

        self._title_lbl = QLabel("Dashboard")
        self._title_lbl.setObjectName("page_title")

        lay.addWidget(self._title_lbl)
        lay.addStretch()

        company = db.get_setting("company_name", "JLC Textiles")
        co_lbl = QLabel(company)
        co_lbl.setStyleSheet("color: #8E8E93; font-size: 13px; font-weight: 600;")
        lay.addWidget(co_lbl)

        return bar

    def _navigate(self, key: str):
        if self._current == key:
            return
        self._current = key

        # Update nav button styles
        for k, btn in self._nav_btns.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Page title
        titles = {
            "dashboard": "Dashboard", "raw_materials": "Raw Materials",
            "finished_goods": "Finished Goods", "production": "Production",
            "orders": "Orders", "purchase_bills": "Purchase Bills",
            "sales_bills": "Sales Bills", "suppliers": "Suppliers",
            "customers": "Customers", "material_types": "Material Types",
            "products": "Products", "units": "Units",
            "ai_studio": "AI Design Studio", "reports": "Reports",
            "settings": "Settings",
        }
        self._title_lbl.setText(titles.get(key, key.replace("_", " ").title()))

        # Lazy-load screen
        if key not in self._screens:
            screen = self._load_screen(key)
            if screen:
                self._screens[key] = screen
                self._stack.addWidget(screen)

        if key in self._screens:
            self._stack.setCurrentWidget(self._screens[key])
            if hasattr(self._screens[key], "refresh"):
                self._screens[key].refresh()

    def _load_screen(self, key: str) -> QWidget:
        app_dir = self._app_dir
        try:
            if key == "dashboard":
                from ui.screens.dashboard import DashboardScreen
                return DashboardScreen(navigate_fn=self._navigate)
            elif key == "raw_materials":
                from ui.screens.raw_materials import RawMaterialsScreen
                return RawMaterialsScreen()
            elif key == "finished_goods":
                from ui.screens.finished_goods import FinishedGoodsScreen
                return FinishedGoodsScreen()
            elif key == "production":
                from ui.screens.production import ProductionScreen
                return ProductionScreen()
            elif key == "orders":
                from ui.screens.orders import OrdersScreen
                return OrdersScreen()
            elif key == "purchase_bills":
                from ui.screens.purchase_bills import PurchaseBillsScreen
                return PurchaseBillsScreen(app_dir)
            elif key == "sales_bills":
                from ui.screens.sales_bills import SalesBillsScreen
                return SalesBillsScreen(app_dir)
            elif key == "suppliers":
                from ui.screens.masters import SuppliersScreen
                return SuppliersScreen()
            elif key == "customers":
                from ui.screens.masters import CustomersScreen
                return CustomersScreen()
            elif key == "material_types":
                from ui.screens.masters import MaterialTypesScreen
                return MaterialTypesScreen()
            elif key == "products":
                from ui.screens.masters import ProductsScreen
                return ProductsScreen(app_dir)
            elif key == "units":
                from ui.screens.masters import UnitsScreen
                return UnitsScreen()
            elif key == "ai_studio":
                from ui.screens.ai_studio import AIStudioScreen
                return AIStudioScreen(app_dir)
            elif key == "reports":
                from ui.screens.reports import ReportsScreen
                return ReportsScreen()
            elif key == "settings":
                from ui.screens.settings import SettingsScreen
                return SettingsScreen(app_dir)
        except Exception as e:
            from ui.screens._placeholder import PlaceholderScreen
            return PlaceholderScreen(key, str(e))
        return None
