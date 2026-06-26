import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QComboBox, QSpinBox, QDoubleSpinBox, QMessageBox,
    QLineEdit, QDateEdit, QAbstractItemView, QAbstractSpinBox,
    QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import Qt, QDate
import core.database as db
from ui.widgets.components import DataTable, SectionHeader, SearchBar
from utils.pdf_generator import generate_sales_bill

SIZES = [("M", "qty_m"), ("L", "qty_l"), ("XL", "qty_xl"),
         ("XXL", "qty_xxl"), ("M-XXL", "qty_mxxl")]


class SalesBillsScreen(QWidget):
    def __init__(self, app_dir: str, parent=None):
        super().__init__(parent)
        self._app_dir = app_dir
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        hdr = SectionHeader("Sales / Order Forms", "+ New Order Form")
        if hdr.btn:
            hdr.btn.clicked.connect(self._new_bill)
        lay.addWidget(hdr)

        self._search = SearchBar("Search by bill number, party...")
        self._search.textChanged.connect(self._filter)
        lay.addWidget(self._search)

        self._table = DataTable(
            ["Bill No", "Date", "Party", "Designs", "Total Qty", "Total ₹", "PDF", "Actions"]
        )
        self._table.setColumnWidth(0, 130)
        self._table.setColumnWidth(1, 95)
        self._table.setColumnWidth(2, 170)
        lay.addWidget(self._table, 1)
        self.refresh()

    def refresh(self):
        rows = db.fetchall(
            """SELECT sb.id, sb.bill_number, sb.bill_date, c.name as customer,
                      COALESCE(sb.total_qty,0) as total_qty, sb.total_amount, sb.pdf_path,
                      COUNT(sbi.id) as item_count
               FROM sales_bills sb
               JOIN customers c ON c.id=sb.customer_id
               LEFT JOIN sales_bill_items sbi ON sbi.bill_id=sb.id
               GROUP BY sb.id ORDER BY sb.id DESC"""
        )
        self._all_rows = rows
        self._render(rows)

    def _render(self, rows):
        display = []
        for r in rows:
            display.append([
                r["bill_number"], r["bill_date"], r["customer"],
                str(r["item_count"]),
                f"{r['total_qty']:.0f}",
                f"₹ {r['total_amount']:,.2f}",
                "✓" if r["pdf_path"] and os.path.exists(r["pdf_path"] or "") else "—"
            ])
        self._table.load_rows(display)
        self._ids = [r["id"] for r in rows]

        for row_idx in range(self._table.rowCount()):
            bill_id = self._ids[row_idx]
            pdf_path = rows[row_idx]["pdf_path"]

            view_btn = QPushButton("View PDF")
            view_btn.setObjectName("btn_flat")
            view_btn.setStyleSheet("color: #5E7E9B; font-size: 12px;")
            view_btn.setFixedHeight(28)
            view_btn.setEnabled(bool(pdf_path and os.path.exists(pdf_path or "")))
            view_btn.clicked.connect(lambda _, p=pdf_path: os.startfile(p) if p else None)

            regen_btn = QPushButton("PDF")
            regen_btn.setObjectName("btn_flat")
            regen_btn.setStyleSheet("color: #5FB07C; font-size: 12px;")
            regen_btn.setFixedHeight(28)
            regen_btn.clicked.connect(lambda _, bid=bill_id: self._gen_pdf(bid))

            del_btn = QPushButton("Delete")
            del_btn.setObjectName("btn_flat")
            del_btn.setStyleSheet("color: #D9685F; font-size: 12px;")
            del_btn.setFixedHeight(28)
            del_btn.clicked.connect(lambda _, bid=bill_id: self._delete(bid))

            w = QWidget()
            wl = QHBoxLayout(w)
            wl.setContentsMargins(4, 0, 4, 0)
            wl.setSpacing(4)
            wl.addWidget(view_btn)
            wl.addWidget(regen_btn)
            wl.addWidget(del_btn)
            wl.addStretch()
            self._table.setCellWidget(row_idx, 7, w)

    def _filter(self, text):
        if not text:
            self._render(self._all_rows)
        else:
            filtered = [r for r in self._all_rows
                        if text.lower() in (r["bill_number"] or "").lower()
                        or text.lower() in (r["customer"] or "").lower()]
            self._render(filtered)

    def _new_bill(self):
        dlg = _SalesBillDialog(self._app_dir, self)
        if dlg.exec():
            self.refresh()

    def _gen_pdf(self, bill_id: int):
        try:
            path = generate_sales_bill(bill_id, self._app_dir)
            QMessageBox.information(self, "PDF Generated", f"Saved to:\n{path}")
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not generate PDF:\n{e}")

    def _delete(self, bill_id: int):
        reply = QMessageBox.question(
            self, "Delete Order Form",
            "Delete this order form?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.execute("DELETE FROM sales_bill_items WHERE bill_id=?", (bill_id,))
            db.execute("DELETE FROM sales_bills WHERE id=?", (bill_id,))
            self.refresh()


class _SalesBillDialog(QDialog):
    def __init__(self, app_dir: str, parent=None):
        super().__init__(parent)
        self._app_dir = app_dir
        self.setWindowTitle("New Order Form")
        self.setMinimumSize(880, 640)
        self.setModal(True)
        self._items = []  # dicts: design_no, sizes{}, row_qty, mrp, amount
        self._build_ui()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(12)

        # ── Header row 1: Party / Bill No / Date ──
        r1 = QHBoxLayout()
        r1.setSpacing(16)

        party_col = QVBoxLayout(); party_col.setSpacing(4)
        party_col.addWidget(QLabel("Party (Customer) *"))
        self._customer = QComboBox()
        self._customer.setFixedHeight(36)
        self._customer.setMinimumWidth(240)
        custs = db.fetchall("SELECT id, name FROM customers WHERE is_active=1 ORDER BY name")
        self._cust_ids = [c["id"] for c in custs]
        self._customer.addItem("— Select Party —")
        for c in custs:
            self._customer.addItem(c["name"])
        party_col.addWidget(self._customer)
        r1.addLayout(party_col, 1)

        num_col = QVBoxLayout(); num_col.setSpacing(4)
        num_col.addWidget(QLabel("No."))
        self._bill_num = QLineEdit()
        self._bill_num.setFixedHeight(36)
        self._bill_num.setText(db.next_bill_number("SAL", "sales_bills"))
        self._bill_num.setReadOnly(True)
        self._bill_num.setStyleSheet("color: #8E8E93;")
        num_col.addWidget(self._bill_num)
        r1.addLayout(num_col)

        date_col = QVBoxLayout(); date_col.setSpacing(4)
        date_col.addWidget(QLabel("Date *"))
        self._date = QDateEdit()
        self._date.setFixedHeight(36)
        self._date.setCalendarPopup(True)
        self._date.setDate(QDate.currentDate())
        self._date.setDisplayFormat("dd-MM-yyyy")
        date_col.addWidget(self._date)
        r1.addLayout(date_col)
        main.addLayout(r1)

        # ── Header row 2: Delivery / Transport / Agent ──
        r2 = QHBoxLayout()
        r2.setSpacing(16)

        deliv_col = QVBoxLayout(); deliv_col.setSpacing(4)
        deliv_col.addWidget(QLabel("Delivery Date"))
        self._delivery = QDateEdit()
        self._delivery.setFixedHeight(36)
        self._delivery.setCalendarPopup(True)
        self._delivery.setDate(QDate.currentDate().addDays(7))
        self._delivery.setDisplayFormat("dd-MM-yyyy")
        deliv_col.addWidget(self._delivery)
        r2.addLayout(deliv_col)

        trans_col = QVBoxLayout(); trans_col.setSpacing(4)
        trans_col.addWidget(QLabel("Transport"))
        self._transport = QLineEdit()
        self._transport.setFixedHeight(36)
        self._transport.setPlaceholderText("Transporter / courier")
        trans_col.addWidget(self._transport)
        r2.addLayout(trans_col, 1)

        agent_col = QVBoxLayout(); agent_col.setSpacing(4)
        agent_col.addWidget(QLabel("Agent"))
        self._agent = QLineEdit()
        self._agent.setFixedHeight(36)
        self._agent.setPlaceholderText("Sales agent")
        agent_col.addWidget(self._agent)
        r2.addLayout(agent_col, 1)
        main.addLayout(r2)

        # ── Add item row (size grid) ──
        grid_lbl = QLabel("ADD DESIGN")
        grid_lbl.setObjectName("card_title")
        main.addWidget(grid_lbl)

        add_row = QHBoxLayout()
        add_row.setSpacing(8)

        dn_col = QVBoxLayout(); dn_col.setSpacing(3)
        dn_col.addWidget(self._mini_lbl("Design / Product"))
        self._product = QComboBox()
        self._product.setFixedHeight(34)
        self._product.setMinimumWidth(170)
        prods = db.fetchall(
            "SELECT id, name, sale_rate FROM products WHERE is_active=1 ORDER BY name")
        self._prod_data = prods
        self._product.addItem("— Select Design —")
        for p in prods:
            self._product.addItem(p["name"])
        self._product.currentIndexChanged.connect(self._on_product_change)
        dn_col.addWidget(self._product)
        add_row.addLayout(dn_col)

        self._size_spins = {}
        for label, key in SIZES:
            col = QVBoxLayout(); col.setSpacing(3)
            col.addWidget(self._mini_lbl(label))
            sp = QSpinBox()
            sp.setFixedHeight(34)
            sp.setMinimumWidth(70)
            sp.setRange(0, 9999)
            # No up/down buttons → the whole field shows the number (e.g. 11)
            sp.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            sp.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._size_spins[key] = sp
            col.addWidget(sp)
            add_row.addLayout(col)

        mrp_col = QVBoxLayout(); mrp_col.setSpacing(3)
        mrp_col.addWidget(self._mini_lbl("MRP"))
        self._mrp = QDoubleSpinBox()
        self._mrp.setFixedHeight(34)
        self._mrp.setFixedWidth(110)
        self._mrp.setRange(0, 9999999)
        self._mrp.setDecimals(2)
        self._mrp.setPrefix("₹ ")
        mrp_col.addWidget(self._mrp)
        add_row.addLayout(mrp_col)

        btn_col = QVBoxLayout(); btn_col.setSpacing(3)
        btn_col.addWidget(self._mini_lbl(" "))
        add_btn = QPushButton("+ Add")
        add_btn.setObjectName("btn_primary")
        add_btn.setFixedHeight(34)
        add_btn.clicked.connect(self._add_item)
        btn_col.addWidget(add_btn)
        add_row.addLayout(btn_col)
        add_row.addStretch()
        main.addLayout(add_row)

        # ── Items table ──
        self._items_table = QTableWidget()
        headers = ["Design No.", "M", "L", "XL", "XXL", "M-XXL", "Qty", "MRP (₹)", ""]
        self._items_table.setColumnCount(len(headers))
        self._items_table.setHorizontalHeaderLabels(headers)
        self._items_table.verticalHeader().setVisible(False)
        self._items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._items_table.setAlternatingRowColors(True)
        self._items_table.setShowGrid(False)
        self._items_table.horizontalHeader().setStretchLastSection(True)
        self._items_table.verticalHeader().setDefaultSectionSize(44)
        self._items_table.setColumnWidth(0, 160)
        for col in range(1, 8):
            self._items_table.setColumnWidth(col, 70)
        self._items_table.setMaximumHeight(240)
        main.addWidget(self._items_table)

        # ── Total ──
        tot_row = QHBoxLayout()
        tot_row.addStretch()
        self._total_lbl = QLabel("Total Quantity: 0    |    Total: ₹ 0.00")
        self._total_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #F5F5F7;")
        tot_row.addWidget(self._total_lbl)
        main.addLayout(tot_row)

        # ── Buttons ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setFixedHeight(36)
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save & Generate PDF")
        save.setObjectName("btn_success")
        save.setFixedHeight(36)
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        main.addLayout(btn_row)

        self._recalc()

    def _mini_lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet("font-size: 10px; color: #8E8E93; font-weight: 700;")
        return l

    def _on_product_change(self, idx):
        # Auto-fill MRP from the selected product's sale rate.
        if idx > 0 and idx - 1 < len(self._prod_data):
            self._mrp.setValue(self._prod_data[idx - 1]["sale_rate"] or 0)

    def _add_item(self):
        idx = self._product.currentIndex()
        if idx <= 0:
            if not self._prod_data:
                QMessageBox.warning(
                    self, "No Products",
                    "No designs found. Add your designs under the Products "
                    "screen first, then select them here.")
            else:
                QMessageBox.warning(self, "Required", "Please select a design/product.")
            return
        product = self._prod_data[idx - 1]
        design = product["name"]
        product_id = product["id"]
        sizes = {key: self._size_spins[key].value() for _, key in SIZES}
        row_qty = sum(sizes.values())
        mrp = self._mrp.value()

        if row_qty <= 0:
            QMessageBox.warning(self, "Required", "Enter quantity for at least one size.")
            return

        self._items.append({
            "design_no": design, "product_id": product_id, "sizes": sizes,
            "row_qty": row_qty, "mrp": mrp, "amount": row_qty * mrp
        })
        # reset inputs
        self._product.setCurrentIndex(0)
        for _, key in SIZES:
            self._size_spins[key].setValue(0)
        self._mrp.setValue(0)
        self._product.setFocus()

        self._refresh_items_table()
        self._recalc()

    def _refresh_items_table(self):
        self._items_table.setRowCount(0)
        for i, it in enumerate(self._items):
            r = self._items_table.rowCount()
            self._items_table.insertRow(r)
            vals = [
                it["design_no"],
                self._z(it["sizes"]["qty_m"]), self._z(it["sizes"]["qty_l"]),
                self._z(it["sizes"]["qty_xl"]), self._z(it["sizes"]["qty_xxl"]),
                self._z(it["sizes"]["qty_mxxl"]),
                f"{it['row_qty']:.0f}", f"₹ {it['mrp']:,.2f}"
            ]
            for c, val in enumerate(vals):
                cell = QTableWidgetItem(str(val))
                if c >= 1:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._items_table.setItem(r, c, cell)
            rem = QPushButton("✕")
            rem.setFixedHeight(26)
            rem.setStyleSheet("color: #D9685F; font-size: 14px; border: none;"
                              "background: transparent; min-height: 0;")
            rem.clicked.connect(lambda _, idx=i: self._remove_item(idx))
            self._items_table.setCellWidget(r, 8, rem)

    def _z(self, v):
        return str(int(v)) if v else "—"

    def _remove_item(self, idx: int):
        if 0 <= idx < len(self._items):
            self._items.pop(idx)
            self._refresh_items_table()
            self._recalc()

    def _recalc(self):
        total_qty = sum(it["row_qty"] for it in self._items)
        total_amt = sum(it["amount"] for it in self._items)
        self._total_lbl.setText(
            f"Total Quantity: {total_qty:.0f}    |    Total: ₹ {total_amt:,.2f}"
        )

    def _save(self):
        cus_idx = self._customer.currentIndex()
        if cus_idx <= 0:
            QMessageBox.warning(self, "Required", "Please select a party (customer).")
            return
        if not self._items:
            QMessageBox.warning(self, "Required", "Add at least one design.")
            return

        cus_id = self._cust_ids[cus_idx - 1]
        bill_date = self._date.date().toString("yyyy-MM-dd")
        delivery = self._delivery.date().toString("yyyy-MM-dd")
        bill_num = self._bill_num.text()
        total_qty = sum(it["row_qty"] for it in self._items)
        total_amt = sum(it["amount"] for it in self._items)

        db.execute(
            """INSERT INTO sales_bills
               (bill_number, customer_id, bill_date, delivery_date, transport, agent,
                subtotal, gst_type, gst_percent, gst_amount, total_qty, total_amount, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (bill_num, cus_id, bill_date, delivery,
             self._transport.text().strip(), self._agent.text().strip(),
             total_amt, "none", 0, 0, total_qty, total_amt, "")
        )
        bill_id = db.fetchone("SELECT last_insert_rowid() as id")["id"]

        for it in self._items:
            s = it["sizes"]
            db.execute(
                """INSERT INTO sales_bill_items
                   (bill_id, design_no, product_id, qty_m, qty_l, qty_xl, qty_xxl, qty_mxxl,
                    row_qty, mrp, amount)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (bill_id, it["design_no"], it.get("product_id"),
                 s["qty_m"], s["qty_l"], s["qty_xl"],
                 s["qty_xxl"], s["qty_mxxl"], it["row_qty"], it["mrp"], it["amount"])
            )

        try:
            path = generate_sales_bill(bill_id, self._app_dir)
            QMessageBox.information(self, "Saved", f"Order form saved!\nPDF: {path}")
        except Exception as e:
            QMessageBox.warning(self, "PDF Error", f"Saved but PDF failed:\n{e}")

        self.accept()
