from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QComboBox, QDoubleSpinBox, QMessageBox, QFormLayout,
    QDialogButtonBox, QTextEdit, QDateEdit, QLineEdit,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QFrame
)
from PyQt6.QtCore import Qt, QDate
import core.database as db
from ui.widgets.components import DataTable, SectionHeader, SearchBar
from ui.styles import STATUS_COLORS

ORDER_STATUSES = ["Received", "In Production", "Ready", "Dispatched", "Delivered", "Cancelled"]


class OrdersScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        hdr = SectionHeader("Customer Orders", "+ New Order")
        if hdr.btn:
            hdr.btn.clicked.connect(self._new_order)
        lay.addWidget(hdr)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)
        self._search = SearchBar("Search order number, customer...")
        self._search.textChanged.connect(self._filter)
        self._status_filter = QComboBox()
        self._status_filter.setFixedHeight(34)
        self._status_filter.addItem("All Statuses")
        self._status_filter.addItems(ORDER_STATUSES)
        self._status_filter.currentIndexChanged.connect(self._filter)
        filter_row.addWidget(self._search, 1)
        filter_row.addWidget(self._status_filter)
        lay.addLayout(filter_row)

        self._table = DataTable(
            ["Order #", "Customer", "Items", "Total", "Status", "Delivery Date", "Created", "Actions"]
        )
        self._table.setColumnWidth(0, 120)
        self._table.setColumnWidth(1, 160)
        self._table.setColumnWidth(4, 120)
        lay.addWidget(self._table, 1)

        # Order items preview
        items_lbl = QLabel("ORDER ITEMS (selected order)")
        items_lbl.setObjectName("card_title")
        items_lbl.setContentsMargins(0, 8, 0, 4)
        lay.addWidget(items_lbl)

        self._items_table = DataTable(["Product", "Qty", "Rate", "Amount"])
        self._items_table.setMaximumHeight(130)
        lay.addWidget(self._items_table)

        self._table.itemSelectionChanged.connect(self._on_select)
        self.refresh()

    def refresh(self):
        rows = db.fetchall(
            """SELECT o.id, o.order_number, c.name as customer,
                      COUNT(oi.id) as item_count, o.total_amount,
                      o.status, o.delivery_date, o.created_at
               FROM orders o
               JOIN customers c ON c.id=o.customer_id
               LEFT JOIN order_items oi ON oi.order_id=o.id
               GROUP BY o.id ORDER BY o.id DESC"""
        )
        self._all_rows = rows
        self._render(rows)

    def _render(self, rows):
        display = []
        for r in rows:
            display.append([
                r["order_number"], r["customer"],
                str(r["item_count"]),
                f"₹ {r['total_amount']:,.2f}",
                r["status"],
                r["delivery_date"] or "—",
                str(r["created_at"])[:10]
            ])
        self._table.load_rows(display)
        self._ids = [r["id"] for r in rows]

        for row_idx in range(self._table.rowCount()):
            order_id = self._ids[row_idx]
            status = rows[row_idx]["status"]
            self._table.add_status_badge(row_idx, 4, status)

            status_btn = QPushButton("Update Status")
            status_btn.setObjectName("btn_flat")
            status_btn.setStyleSheet("color: #D9A45B; font-size: 12px;")
            status_btn.setFixedHeight(28)
            status_btn.clicked.connect(lambda _, oid=order_id, s=status: self._update_status(oid, s))

            view_btn = QPushButton("View")
            view_btn.setObjectName("btn_flat")
            view_btn.setStyleSheet("color: #5E7E9B; font-size: 12px;")
            view_btn.setFixedHeight(28)
            view_btn.clicked.connect(lambda _, oid=order_id: self._view_order(oid))

            del_btn = QPushButton("Cancel")
            del_btn.setObjectName("btn_flat")
            del_btn.setStyleSheet("color: #D9685F; font-size: 12px;")
            del_btn.setFixedHeight(28)
            del_btn.setEnabled(status not in ("Delivered", "Cancelled"))
            del_btn.clicked.connect(lambda _, oid=order_id: self._cancel_order(oid))

            w = QWidget()
            wl = QHBoxLayout(w)
            wl.setContentsMargins(4, 0, 4, 0)
            wl.setSpacing(4)
            wl.addWidget(status_btn)
            wl.addWidget(view_btn)
            wl.addWidget(del_btn)
            wl.addStretch()
            self._table.setCellWidget(row_idx, 7, w)

    def _filter(self):
        text = self._search.text().lower()
        status = self._status_filter.currentText()
        filtered = self._all_rows
        if text:
            filtered = [r for r in filtered
                        if text in (r["order_number"] or "").lower()
                        or text in (r["customer"] or "").lower()]
        if status != "All Statuses":
            filtered = [r for r in filtered if r["status"] == status]
        self._render(filtered)

    def _new_order(self):
        dlg = _NewOrderDialog(self)
        if dlg.exec():
            self.refresh()

    def _update_status(self, order_id: int, current: str):
        dlg = _UpdateStatusDialog(order_id, current, self)
        if dlg.exec():
            self.refresh()

    def _view_order(self, order_id: int):
        dlg = _ViewOrderDialog(order_id, self)
        dlg.exec()

    def _cancel_order(self, order_id: int):
        reply = QMessageBox.question(
            self, "Cancel Order", "Mark this order as Cancelled?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.execute("UPDATE orders SET status='Cancelled' WHERE id=?", (order_id,))
            self.refresh()

    def _on_select(self):
        row_idx = self._table.currentRow()
        if row_idx < 0 or row_idx >= len(self._ids):
            return
        order_id = self._ids[row_idx]
        items = db.fetchall(
            """SELECT p.name, oi.quantity, oi.rate, oi.amount
               FROM order_items oi JOIN products p ON p.id=oi.product_id
               WHERE oi.order_id=?""",
            (order_id,)
        )
        self._items_table.load_rows([
            [it["name"], f"{it['quantity']:.2f}",
             f"₹ {it['rate']:,.2f}", f"₹ {it['amount']:,.2f}"]
            for it in items
        ])


class _UpdateStatusDialog(QDialog):
    def __init__(self, order_id: int, current: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update Order Status")
        self.setMinimumWidth(340)
        self.setModal(True)
        self._oid = order_id

        lay = QFormLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)
        lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        cur_lbl = QLabel(f"Current: <b>{current}</b>")
        cur_lbl.setStyleSheet("color: #C7C7CC;")
        lay.addRow("", cur_lbl)

        self._status = QComboBox()
        self._status.setFixedHeight(36)
        self._status.addItems(ORDER_STATUSES)
        if current in ORDER_STATUSES:
            self._status.setCurrentIndex(ORDER_STATUSES.index(current))
        lay.addRow("New Status *", self._status)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("btn_primary")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay.addRow("", buttons)

    def _save(self):
        db.execute("UPDATE orders SET status=? WHERE id=?",
                   (self._status.currentText(), self._oid))
        self.accept()


class _NewOrderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Customer Order")
        self.setMinimumSize(720, 560)
        self.setModal(True)
        self._items = []
        self._build_ui()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(12)

        # Top row
        top = QHBoxLayout()
        top.setSpacing(16)

        cus_col = QVBoxLayout()
        cus_col.setSpacing(4)
        cus_col.addWidget(QLabel("Customer *"))
        self._customer = QComboBox()
        self._customer.setFixedHeight(36)
        self._customer.setMinimumWidth(220)
        custs = db.fetchall("SELECT id, name FROM customers WHERE is_active=1 ORDER BY name")
        self._cust_ids = [c["id"] for c in custs]
        self._customer.addItem("— Select Customer —")
        for c in custs:
            self._customer.addItem(c["name"])
        cus_col.addWidget(self._customer)
        top.addLayout(cus_col)

        del_col = QVBoxLayout()
        del_col.setSpacing(4)
        del_col.addWidget(QLabel("Delivery Date"))
        self._delivery = QDateEdit()
        self._delivery.setFixedHeight(36)
        self._delivery.setCalendarPopup(True)
        self._delivery.setDate(QDate.currentDate().addDays(7))
        self._delivery.setDisplayFormat("dd-MM-yyyy")
        del_col.addWidget(self._delivery)
        top.addLayout(del_col)

        ord_col = QVBoxLayout()
        ord_col.setSpacing(4)
        ord_col.addWidget(QLabel("Order #"))
        self._ord_num = QLineEdit()
        self._ord_num.setText(db.next_order_number())
        self._ord_num.setReadOnly(True)
        self._ord_num.setFixedHeight(36)
        self._ord_num.setStyleSheet("color: #AEAEB2;")
        ord_col.addWidget(self._ord_num)
        top.addLayout(ord_col)

        top.addStretch()
        main.addLayout(top)

        # Add item row
        item_lbl = QLabel("ADD ITEMS")
        item_lbl.setObjectName("card_title")
        main.addWidget(item_lbl)

        add_row = QHBoxLayout()
        add_row.setSpacing(8)

        self._prod_combo = QComboBox()
        self._prod_combo.setFixedHeight(34)
        self._prod_combo.setMinimumWidth(200)
        prods = db.fetchall("SELECT id, name, sale_rate FROM products WHERE is_active=1 ORDER BY name")
        self._prod_data = prods
        self._prod_combo.addItem("— Select Product —")
        for p in prods:
            self._prod_combo.addItem(p["name"])
        self._prod_combo.currentIndexChanged.connect(self._on_prod_select)
        add_row.addWidget(self._prod_combo)

        self._item_qty = QDoubleSpinBox()
        self._item_qty.setFixedHeight(34)
        self._item_qty.setRange(1, 99999)
        self._item_qty.setDecimals(0)
        self._item_qty.setFixedWidth(80)
        add_row.addWidget(self._item_qty)

        self._item_rate = QDoubleSpinBox()
        self._item_rate.setFixedHeight(34)
        self._item_rate.setRange(0, 9999999)
        self._item_rate.setDecimals(2)
        self._item_rate.setPrefix("₹ ")
        self._item_rate.setFixedWidth(130)
        add_row.addWidget(self._item_rate)

        add_btn = QPushButton("+ Add")
        add_btn.setObjectName("btn_primary")
        add_btn.setFixedHeight(34)
        add_btn.clicked.connect(self._add_item)
        add_row.addWidget(add_btn)
        add_row.addStretch()
        main.addLayout(add_row)

        # Items table
        self._items_table = QTableWidget()
        self._items_table.setColumnCount(5)
        self._items_table.setHorizontalHeaderLabels(["Product", "Qty", "Rate (₹)", "Amount (₹)", "Remove"])
        self._items_table.verticalHeader().setVisible(False)
        self._items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._items_table.setAlternatingRowColors(True)
        self._items_table.horizontalHeader().setStretchLastSection(True)
        self._items_table.setShowGrid(False)
        self._items_table.setMaximumHeight(180)
        main.addWidget(self._items_table)

        # Total
        tot_row = QHBoxLayout()
        tot_row.addStretch()
        self._total_lbl = QLabel("Total: ₹ 0.00")
        self._total_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #F5F5F7;")
        tot_row.addWidget(self._total_lbl)
        main.addLayout(tot_row)

        # Notes + buttons
        note_row = QHBoxLayout()
        note_row.addWidget(QLabel("Notes:"))
        self._notes = QLineEdit()
        self._notes.setFixedHeight(34)
        self._notes.setPlaceholderText("Optional order notes")
        note_row.addWidget(self._notes, 1)
        main.addLayout(note_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setFixedHeight(36)
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save Order")
        save.setObjectName("btn_success")
        save.setFixedHeight(36)
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        main.addLayout(btn_row)

    def _on_prod_select(self, idx):
        if idx <= 0 or idx - 1 >= len(self._prod_data):
            return
        rate = self._prod_data[idx - 1]["sale_rate"]
        self._item_rate.setValue(rate)

    def _add_item(self):
        idx = self._prod_combo.currentIndex()
        if idx <= 0:
            QMessageBox.warning(self, "Select", "Please select a product.")
            return
        prod = self._prod_data[idx - 1]
        qty = self._item_qty.value()
        rate = self._item_rate.value()
        self._items.append({"prod_id": prod["id"], "name": prod["name"],
                             "qty": qty, "rate": rate, "amount": qty * rate})
        self._refresh_table()

    def _refresh_table(self):
        self._items_table.setRowCount(0)
        for i, it in enumerate(self._items):
            r = self._items_table.rowCount()
            self._items_table.insertRow(r)
            for c, val in enumerate([
                it["name"], f"{it['qty']:.0f}",
                f"₹ {it['rate']:,.2f}", f"₹ {it['amount']:,.2f}"
            ]):
                cell = QTableWidgetItem(val)
                self._items_table.setItem(r, c, cell)
            rem = QPushButton("×")
            rem.setFixedHeight(26)
            rem.setStyleSheet("color: #D9685F; font-size: 16px; border: none; background: transparent; min-height: 0;")
            rem.clicked.connect(lambda _, idx=i: self._remove(idx))
            self._items_table.setCellWidget(r, 4, rem)
        total = sum(it["amount"] for it in self._items)
        self._total_lbl.setText(f"Total: ₹ {total:,.2f}")

    def _remove(self, idx: int):
        if 0 <= idx < len(self._items):
            self._items.pop(idx)
            self._refresh_table()

    def _save(self):
        cus_idx = self._customer.currentIndex()
        if cus_idx <= 0:
            QMessageBox.warning(self, "Required", "Please select a customer.")
            return
        if not self._items:
            QMessageBox.warning(self, "Required", "Add at least one product.")
            return
        cus_id = self._cust_ids[cus_idx - 1]
        total = sum(it["amount"] for it in self._items)
        delivery = self._delivery.date().toString("yyyy-MM-dd")
        ord_num = self._ord_num.text()

        db.execute(
            """INSERT INTO orders (order_number, customer_id, total_amount, notes, delivery_date)
               VALUES (?,?,?,?,?)""",
            (ord_num, cus_id, total, self._notes.text().strip(), delivery)
        )
        order_id = db.fetchone("SELECT last_insert_rowid() as id")["id"]
        for it in self._items:
            db.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, rate, amount) VALUES (?,?,?,?,?)",
                (order_id, it["prod_id"], it["qty"], it["rate"], it["amount"])
            )
        self.accept()


class _ViewOrderDialog(QDialog):
    def __init__(self, order_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Order Details")
        self.setMinimumSize(540, 420)

        order = db.fetchone(
            """SELECT o.*, c.name as customer, c.phone, c.address
               FROM orders o JOIN customers c ON c.id=o.customer_id
               WHERE o.id=?""",
            (order_id,)
        )
        items = db.fetchall(
            """SELECT p.name, oi.quantity, oi.rate, oi.amount
               FROM order_items oi JOIN products p ON p.id=oi.product_id
               WHERE oi.order_id=?""",
            (order_id,)
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)

        for label, val in [
            ("Order #", order["order_number"]),
            ("Customer", order["customer"]),
            ("Phone", order["phone"] or "—"),
            ("Status", order["status"]),
            ("Delivery Date", order["delivery_date"] or "—"),
            ("Total Amount", f"₹ {order['total_amount']:,.2f}"),
            ("Notes", order["notes"] or "—"),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(label + ":")
            lbl.setStyleSheet("color: #AEAEB2; font-size: 12px;")
            lbl.setFixedWidth(110)
            v = QLabel(str(val))
            v.setStyleSheet("color: #E5E5EA;")
            row.addWidget(lbl)
            row.addWidget(v, 1)
            lay.addLayout(row)

        lay.addWidget(QLabel("Products:"))
        t = DataTable(["Product", "Qty", "Rate", "Amount"])
        t.load_rows([[it["name"], f"{it['quantity']:.0f}",
                      f"₹ {it['rate']:,.2f}", f"₹ {it['amount']:,.2f}"] for it in items])
        lay.addWidget(t, 1)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close)
        lay.addLayout(row)
