from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QPushButton, QGridLayout
)
from PyQt6.QtCore import Qt
import core.database as db
from ui.widgets.components import StatCard, HSep, DataTable
from ui.widgets.charts import BarChart, HBarChart, DonutChart, CompareBars
from ui.styles import C


def _rupee(v):
    if v >= 100000:
        return f"₹ {v/100000:.2f}L"
    if v >= 1000:
        return f"₹ {v/1000:.1f}K"
    return f"₹ {v:,.0f}"


class DashboardScreen(QWidget):
    def __init__(self, navigate_fn=None, parent=None):
        super().__init__(parent)
        self._navigate = navigate_fn
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet(f"background-color: {C.BG};")
        scroll.setWidget(content)

        lay = QVBoxLayout(content)
        lay.setContentsMargins(28, 24, 28, 28)
        lay.setSpacing(16)

        # ── KPI cards ──
        self._kpi = {}
        kpis = [
            ("month_sales",   "Sales This Month",  "₹0", "₹", C.BLUE),
            ("month_qty",     "Pieces Sold (Month)", "0", "◷", C.TEAL),
            ("month_orders",  "Orders This Month", "0", "◎", C.ORANGE),
            ("avg_order",     "Avg Order Value",   "₹0", "⌀", C.GREEN),
        ]
        kpi_row = QHBoxLayout(); kpi_row.setSpacing(14)
        for key, label, val, icon, color in kpis:
            card = StatCard(label, val, icon, color)
            self._kpi[key] = card
            kpi_row.addWidget(card)
        lay.addLayout(kpi_row)

        # ── Quick actions ──
        qa = QHBoxLayout(); qa.setSpacing(10)
        for label, screen, obj in [
            ("+ New Order Form", "sales_bills", "btn_primary"),
            ("+ New Purchase", "purchase_bills", "btn_success"),
            ("+ New Order", "orders", "btn_warning"),
            ("+ New Production", "production", "btn_primary"),
        ]:
            b = QPushButton(label); b.setObjectName(obj); b.setFixedHeight(36)
            b.clicked.connect(lambda _, s=screen: self._navigate(s) if self._navigate else None)
            qa.addWidget(b)
        qa.addStretch()
        lay.addLayout(qa)

        # ── Sales trend (full width) ──
        self._trend = BarChart(accent=C.BLUE)
        lay.addWidget(self._card("Sales — Last 30 Days", self._trend, 210))

        # ── Row: Order status donut | Size mix ──
        row1 = QHBoxLayout(); row1.setSpacing(16)
        self._status = DonutChart()
        self._sizemix = HBarChart(colored=True)
        row1.addWidget(self._card("Orders by Status", self._status, 200), 1)
        row1.addWidget(self._card("Size Mix (pieces sold)", self._sizemix, 200), 1)
        lay.addLayout(row1)

        # ── Row: Top designs | Top customers ──
        row2 = QHBoxLayout(); row2.setSpacing(16)
        self._designs = HBarChart(accent=C.BLUE)
        self._customers = HBarChart(accent=C.TEAL)
        row2.addWidget(self._card("Top Designs (by qty)", self._designs, 200), 1)
        row2.addWidget(self._card("Top Customers (by ₹)", self._customers, 200), 1)
        lay.addLayout(row2)

        # ── Row: Sales vs Purchases | Low stock ──
        row3 = QHBoxLayout(); row3.setSpacing(16)
        self._cmp = CompareBars()
        row3.addWidget(self._card("This Month — Money In vs Out", self._cmp, 150), 1)

        low_card = QFrame(); low_card.setObjectName("card")
        lc = QVBoxLayout(low_card); lc.setContentsMargins(16, 14, 16, 14); lc.setSpacing(8)
        lt = QLabel("LOW STOCK ALERTS"); lt.setObjectName("card_title")
        lc.addWidget(lt)
        self._low_lay = QVBoxLayout(); self._low_lay.setSpacing(4)
        lc.addLayout(self._low_lay); lc.addStretch()
        low_card.setMinimumHeight(150)
        row3.addWidget(low_card, 1)
        lay.addLayout(row3)

        # ── Recent orders ──
        ro_card = QFrame(); ro_card.setObjectName("card")
        rl = QVBoxLayout(ro_card); rl.setContentsMargins(16, 14, 16, 14); rl.setSpacing(10)
        rt = QLabel("RECENT ORDERS"); rt.setObjectName("card_title")
        rl.addWidget(rt)
        self._orders_table = DataTable(["Order #", "Customer", "Status", "Amount", "Date"])
        # Tall enough to show the header + up to 5 recent orders without clipping.
        self._orders_table.setMinimumHeight(300)
        rl.addWidget(self._orders_table)
        ro_card.setMinimumHeight(360)
        lay.addWidget(ro_card)

    def _card(self, title, chart, min_h=200):
        card = QFrame(); card.setObjectName("card")
        v = QVBoxLayout(card); v.setContentsMargins(16, 14, 16, 14); v.setSpacing(10)
        t = QLabel(title.upper()); t.setObjectName("card_title")
        v.addWidget(t); v.addWidget(chart, 1)
        card.setMinimumHeight(min_h)
        return card

    def refresh(self):
        a = db.dashboard_analytics()

        self._kpi["month_sales"].set_value(_rupee(a["month_sales"]))
        self._kpi["month_qty"].set_value(f"{a['month_qty']:,.0f}")
        self._kpi["month_orders"].set_value(str(a["month_orders"]))
        self._kpi["avg_order"].set_value(_rupee(a["avg_order_value"]))

        self._trend.set_data(a["sales_trend"], fmt=lambda v: _rupee(v))
        self._status.set_data(a["order_status"])
        self._sizemix.set_data(a["size_mix"])
        self._designs.set_data(a["top_designs"])
        self._customers.set_data(a["top_customers"], fmt=lambda v: _rupee(v))
        self._cmp.set_data([
            ("Sales", a["month_sales"], C.GREEN),
            ("Purchases", a["month_purchases"], C.ORANGE),
        ], fmt=lambda v: _rupee(v))

        # low stock
        stats = db.dashboard_stats()
        while self._low_lay.count():
            ch = self._low_lay.takeAt(0)
            if ch.widget():
                ch.widget().deleteLater()
        if not stats["low_stock"]:
            ok = QLabel("  All materials well stocked ✓")
            ok.setStyleSheet(f"color: {C.GREEN}; font-size: 12px; padding: 6px;")
            self._low_lay.addWidget(ok)
        else:
            for r in stats["low_stock"]:
                w = QFrame()
                w.setStyleSheet(f"background-color: {C.ORANGE_SOFT}; border-radius: 8px;")
                il = QHBoxLayout(w); il.setContentsMargins(10, 6, 10, 6)
                nm = QLabel(r["name"]); nm.setStyleSheet(f"color: {C.ORANGE}; font-size: 12px; font-weight: 600;")
                qt = QLabel(f"{r['quantity']:.1f} / {r['low_stock_threshold']:.1f} {r['abbreviation'] or ''}")
                qt.setStyleSheet(f"color: {C.TEXT_MUTED}; font-size: 11px;")
                il.addWidget(nm); il.addStretch(); il.addWidget(qt)
                self._low_lay.addWidget(w)

        # recent orders
        rows = []
        for o in stats["recent_orders"]:
            rows.append([o["order_number"], o["customer"], o["status"],
                         f"₹ {o['total_amount']:,.0f}", str(o["created_at"])[:10]])
        self._orders_table.load_rows(rows)
        for rr in range(self._orders_table.rowCount()):
            it = self._orders_table.item(rr, 2)
            if it:
                self._orders_table.add_status_badge(rr, 2, it.text())
