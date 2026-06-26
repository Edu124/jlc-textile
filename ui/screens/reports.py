import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QFrame, QTabWidget, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QDate
import core.database as db
from ui.widgets.components import DataTable, SectionHeader


class ReportsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        hdr = QLabel("Reports")
        hdr.setObjectName("section_title")
        lay.addWidget(hdr)

        # Date filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        filter_row.addWidget(QLabel("From:"))
        self._from_date = QDateEdit()
        self._from_date.setCalendarPopup(True)
        self._from_date.setDate(QDate.currentDate().addMonths(-1))
        self._from_date.setDisplayFormat("dd-MM-yyyy")
        self._from_date.setFixedHeight(34)
        filter_row.addWidget(self._from_date)

        filter_row.addWidget(QLabel("To:"))
        self._to_date = QDateEdit()
        self._to_date.setCalendarPopup(True)
        self._to_date.setDate(QDate.currentDate())
        self._to_date.setDisplayFormat("dd-MM-yyyy")
        self._to_date.setFixedHeight(34)
        filter_row.addWidget(self._to_date)

        run_btn = QPushButton("Generate Reports")
        run_btn.setObjectName("btn_primary")
        run_btn.setFixedHeight(34)
        run_btn.clicked.connect(self.refresh)
        filter_row.addWidget(run_btn)
        filter_row.addStretch()
        lay.addLayout(filter_row)

        # Tabs
        self._tabs = QTabWidget()
        lay.addWidget(self._tabs, 1)

        # Stock Report tab
        stock_w = QWidget()
        stock_lay = QVBoxLayout(stock_w)
        stock_lay.setContentsMargins(12, 12, 12, 12)
        self._stock_table = DataTable(
            ["Material", "Unit", "Qty in Stock", "Avg Rate (₹)", "Value (₹)", "Low Stock Alert"]
        )
        stock_lay.addWidget(self._stock_table)
        self._tabs.addTab(stock_w, "Raw Materials Stock")

        # Finished goods tab
        fg_w = QWidget()
        fg_lay = QVBoxLayout(fg_w)
        fg_lay.setContentsMargins(12, 12, 12, 12)
        self._fg_table = DataTable(
            ["Product", "Category", "Unit", "Qty in Stock", "Sale Rate (₹)", "Est. Value (₹)"]
        )
        fg_lay.addWidget(self._fg_table)
        self._tabs.addTab(fg_w, "Finished Goods Stock")

        # Purchase Report tab
        pur_w = QWidget()
        pur_lay = QVBoxLayout(pur_w)
        pur_lay.setContentsMargins(12, 12, 12, 12)
        self._pur_sum = QLabel("")
        self._pur_sum.setStyleSheet("font-size: 13px; color: #C7C7CC; padding: 4px;")
        pur_lay.addWidget(self._pur_sum)
        self._pur_table = DataTable(
            ["Bill No", "Date", "Supplier", "Subtotal (₹)", "GST (₹)", "Total (₹)"]
        )
        pur_lay.addWidget(self._pur_table)
        self._tabs.addTab(pur_w, "Purchases")

        # Sales Report tab
        sal_w = QWidget()
        sal_lay = QVBoxLayout(sal_w)
        sal_lay.setContentsMargins(12, 12, 12, 12)
        self._sal_sum = QLabel("")
        self._sal_sum.setStyleSheet("font-size: 13px; color: #C7C7CC; padding: 4px;")
        sal_lay.addWidget(self._sal_sum)
        self._sal_table = DataTable(
            ["Bill No", "Date", "Customer", "Subtotal (₹)", "GST (₹)", "Total (₹)"]
        )
        sal_lay.addWidget(self._sal_table)
        self._tabs.addTab(sal_w, "Sales")

        # Orders Report tab
        ord_w = QWidget()
        ord_lay = QVBoxLayout(ord_w)
        ord_lay.setContentsMargins(12, 12, 12, 12)
        self._ord_table = DataTable(
            ["Order #", "Customer", "Items", "Total (₹)", "Status", "Delivery Date", "Created"]
        )
        ord_lay.addWidget(self._ord_table)
        self._tabs.addTab(ord_w, "Orders")

        # Production Report tab
        prod_w = QWidget()
        prod_lay = QVBoxLayout(prod_w)
        prod_lay.setContentsMargins(12, 12, 12, 12)
        self._prod_table = DataTable(
            ["Batch #", "Product", "Qty", "Stage", "Started", "Completed"]
        )
        prod_lay.addWidget(self._prod_table)
        self._tabs.addTab(prod_w, "Production")

        self.refresh()

    def refresh(self):
        from_dt = self._from_date.date().toString("yyyy-MM-dd")
        to_dt = self._to_date.date().toString("yyyy-MM-dd")

        # Raw material stock (not date-filtered, always current)
        rm = db.fetchall(
            """SELECT rmt.name, u.abbreviation, rms.quantity, rms.avg_rate,
                      rmt.low_stock_threshold
               FROM raw_material_types rmt
               LEFT JOIN raw_material_stock rms ON rms.material_type_id=rmt.id
               LEFT JOIN units u ON u.id=rmt.unit_id
               ORDER BY rmt.name"""
        )
        self._stock_table.load_rows([
            [r["name"], r["abbreviation"] or "",
             f"{r['quantity'] or 0:.2f}",
             f"₹ {r['avg_rate'] or 0:.2f}",
             f"₹ {(r['quantity'] or 0) * (r['avg_rate'] or 0):,.2f}",
             f"{r['low_stock_threshold'] or 0:.2f}"]
            for r in rm
        ])

        # Finished goods stock
        fg = db.fetchall(
            """SELECT p.name, pc.name as cat, u.abbreviation, fgs.quantity, p.sale_rate
               FROM products p
               LEFT JOIN product_categories pc ON pc.id=p.category_id
               LEFT JOIN units u ON u.id=p.unit_id
               LEFT JOIN finished_goods_stock fgs ON fgs.product_id=p.id
               WHERE p.is_active=1 ORDER BY p.name"""
        )
        self._fg_table.load_rows([
            [r["name"], r["cat"] or "", r["abbreviation"] or "",
             f"{r['quantity'] or 0:.2f}",
             f"₹ {r['sale_rate']:,.2f}",
             f"₹ {(r['quantity'] or 0) * r['sale_rate']:,.2f}"]
            for r in fg
        ])

        # Purchases in date range
        purs = db.fetchall(
            """SELECT pb.bill_number, pb.bill_date, s.name, pb.subtotal, pb.gst_amount, pb.total_amount
               FROM purchase_bills pb JOIN suppliers s ON s.id=pb.supplier_id
               WHERE pb.bill_date BETWEEN ? AND ? ORDER BY pb.bill_date""",
            (from_dt, to_dt)
        )
        self._pur_table.load_rows([
            [r["bill_number"], r["bill_date"], r["name"],
             f"₹ {r['subtotal']:,.2f}", f"₹ {r['gst_amount']:,.2f}", f"₹ {r['total_amount']:,.2f}"]
            for r in purs
        ])
        pur_total = sum(r["total_amount"] for r in purs)
        self._pur_sum.setText(
            f"  {len(purs)} bills   |   Total Purchases: ₹ {pur_total:,.2f}"
        )

        # Sales in date range
        sales = db.fetchall(
            """SELECT sb.bill_number, sb.bill_date, c.name, sb.subtotal, sb.gst_amount, sb.total_amount
               FROM sales_bills sb JOIN customers c ON c.id=sb.customer_id
               WHERE sb.bill_date BETWEEN ? AND ? ORDER BY sb.bill_date""",
            (from_dt, to_dt)
        )
        self._sal_table.load_rows([
            [r["bill_number"], r["bill_date"], r["name"],
             f"₹ {r['subtotal']:,.2f}", f"₹ {r['gst_amount']:,.2f}", f"₹ {r['total_amount']:,.2f}"]
            for r in sales
        ])
        sal_total = sum(r["total_amount"] for r in sales)
        self._sal_sum.setText(
            f"  {len(sales)} bills   |   Total Sales: ₹ {sal_total:,.2f}"
        )

        # Orders in date range
        orders = db.fetchall(
            """SELECT o.order_number, c.name, COUNT(oi.id) as items,
                      o.total_amount, o.status, o.delivery_date, o.created_at
               FROM orders o JOIN customers c ON c.id=o.customer_id
               LEFT JOIN order_items oi ON oi.order_id=o.id
               WHERE DATE(o.created_at) BETWEEN ? AND ?
               GROUP BY o.id ORDER BY o.created_at""",
            (from_dt, to_dt)
        )
        self._ord_table.load_rows([
            [r["order_number"], r["name"], str(r["items"]),
             f"₹ {r['total_amount']:,.2f}", r["status"],
             r["delivery_date"] or "—", str(r["created_at"])[:10]]
            for r in orders
        ])
        for row_idx in range(self._ord_table.rowCount()):
            status_item = self._ord_table.item(row_idx, 4)
            if status_item:
                self._ord_table.add_status_badge(row_idx, 4, status_item.text())

        # Production batches
        batches = db.fetchall(
            """SELECT pb.batch_number, p.name, pb.quantity, pb.current_stage,
                      pb.started_at, pb.completed_at
               FROM production_batches pb JOIN products p ON p.id=pb.product_id
               WHERE DATE(pb.started_at) BETWEEN ? AND ?
               ORDER BY pb.started_at""",
            (from_dt, to_dt)
        )
        self._prod_table.load_rows([
            [b["batch_number"], b["name"], f"{b['quantity']:.0f}",
             b["current_stage"], str(b["started_at"])[:10],
             str(b["completed_at"])[:10] if b["completed_at"] else "—"]
            for b in batches
        ])
        for row_idx in range(self._prod_table.rowCount()):
            stage_item = self._prod_table.item(row_idx, 3)
            if stage_item:
                self._prod_table.add_status_badge(row_idx, 3, stage_item.text())
