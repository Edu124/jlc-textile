import os
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QComboBox, QDoubleSpinBox, QMessageBox,
    QFormLayout, QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QLineEdit, QDateEdit, QAbstractItemView, QSpinBox, QFrame
)
from PyQt6.QtCore import Qt, QDate
import core.database as db
from ui.widgets.components import DataTable, SectionHeader, SearchBar
from utils.pdf_generator import generate_purchase_bill


class PurchaseBillsScreen(QWidget):
    def __init__(self, app_dir: str, parent=None):
        super().__init__(parent)
        self._app_dir = app_dir
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        hdr = SectionHeader("Purchase Bills", "+ New Purchase Bill")
        if hdr.btn:
            hdr.btn.clicked.connect(self._new_bill)
        lay.addWidget(hdr)

        self._search = SearchBar("Search by bill number, supplier...")
        self._search.textChanged.connect(self._filter)
        lay.addWidget(self._search)

        self._table = DataTable(
            ["Bill No", "Date", "Supplier", "Items", "Subtotal", "GST", "Total", "PDF", "Actions"]
        )
        self._table.setColumnWidth(0, 130)
        self._table.setColumnWidth(1, 90)
        self._table.setColumnWidth(2, 160)
        lay.addWidget(self._table, 1)
        self.refresh()

    def refresh(self):
        rows = db.fetchall(
            """SELECT pb.id, pb.bill_number, pb.bill_date, s.name as supplier,
                      pb.subtotal, pb.gst_amount, pb.total_amount, pb.pdf_path,
                      COUNT(pbi.id) as item_count
               FROM purchase_bills pb
               JOIN suppliers s ON s.id=pb.supplier_id
               LEFT JOIN purchase_bill_items pbi ON pbi.bill_id=pb.id
               GROUP BY pb.id ORDER BY pb.id DESC"""
        )
        self._all_rows = rows
        self._render(rows)

    def _render(self, rows):
        display = []
        for r in rows:
            display.append([
                r["bill_number"], r["bill_date"], r["supplier"],
                str(r["item_count"]),
                f"₹ {r['subtotal']:,.2f}",
                f"₹ {r['gst_amount']:,.2f}",
                f"₹ {r['total_amount']:,.2f}",
                "✓" if r["pdf_path"] and os.path.exists(r["pdf_path"]) else "—"
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
            view_btn.clicked.connect(lambda _, p=pdf_path: self._open_pdf(p))

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
            self._table.setCellWidget(row_idx, 8, w)

    def _filter(self, text):
        if not text:
            self._render(self._all_rows)
        else:
            filtered = [r for r in self._all_rows
                        if text.lower() in (r["bill_number"] or "").lower()
                        or text.lower() in (r["supplier"] or "").lower()]
            self._render(filtered)

    def _new_bill(self):
        dlg = _PurchaseBillDialog(self._app_dir, self)
        if dlg.exec():
            self.refresh()

    def _open_pdf(self, path: str):
        if path and os.path.exists(path):
            os.startfile(path)

    def _gen_pdf(self, bill_id: int):
        try:
            path = generate_purchase_bill(bill_id, self._app_dir)
            QMessageBox.information(self, "PDF Generated", f"Saved to:\n{path}")
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not generate PDF:\n{e}")

    def _delete(self, bill_id: int):
        reply = QMessageBox.question(
            self, "Delete Bill",
            "Delete this purchase bill? Stock adjustments will NOT be reversed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.execute("DELETE FROM purchase_bill_items WHERE bill_id=?", (bill_id,))
            db.execute("DELETE FROM purchase_bills WHERE id=?", (bill_id,))
            self.refresh()


class _PurchaseBillDialog(QDialog):
    def __init__(self, app_dir: str, parent=None):
        super().__init__(parent)
        self._app_dir = app_dir
        self.setWindowTitle("New Purchase Bill")
        self.setMinimumSize(760, 580)
        self.setModal(True)
        self._items = []  # list of (mat_id, mat_name, qty, unit_id, unit_name, rate, amount)
        self._build_ui()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(14)

        # Header fields
        top = QHBoxLayout()
        top.setSpacing(16)

        # Supplier
        sup_col = QVBoxLayout()
        sup_col.setSpacing(4)
        sup_col.addWidget(QLabel("Supplier *"))
        self._supplier = QComboBox()
        self._supplier.setFixedHeight(36)
        self._supplier.setMinimumWidth(220)
        suppliers = db.fetchall("SELECT id, name FROM suppliers WHERE is_active=1 ORDER BY name")
        self._sup_ids = [s["id"] for s in suppliers]
        self._supplier.addItem("— Select Supplier —")
        for s in suppliers:
            self._supplier.addItem(s["name"])
        self._supplier.currentIndexChanged.connect(self._on_supplier_change)
        sup_col.addWidget(self._supplier)
        top.addLayout(sup_col)

        # Bill date
        date_col = QVBoxLayout()
        date_col.setSpacing(4)
        date_col.addWidget(QLabel("Bill Date *"))
        self._date = QDateEdit()
        self._date.setFixedHeight(36)
        self._date.setCalendarPopup(True)
        self._date.setDate(QDate.currentDate())
        self._date.setDisplayFormat("dd-MM-yyyy")
        date_col.addWidget(self._date)
        top.addLayout(date_col)

        # Bill number
        num_col = QVBoxLayout()
        num_col.setSpacing(4)
        num_col.addWidget(QLabel("Bill Number (auto)"))
        self._bill_num = QLineEdit()
        self._bill_num.setFixedHeight(36)
        self._bill_num.setText(db.next_bill_number("PUR", "purchase_bills"))
        self._bill_num.setReadOnly(True)
        self._bill_num.setStyleSheet("color: #AEAEB2;")
        num_col.addWidget(self._bill_num)
        top.addLayout(num_col)

        top.addStretch()
        main.addLayout(top)

        # GST row
        gst_row = QHBoxLayout()
        gst_row.setSpacing(16)

        gst_col = QVBoxLayout()
        gst_col.setSpacing(4)
        gst_col.addWidget(QLabel("GST Type"))
        self._gst_type = QComboBox()
        self._gst_type.setFixedHeight(34)
        self._gst_type.addItems(["No GST", "CGST + SGST", "IGST"])
        self._gst_type.currentIndexChanged.connect(self._recalc)
        gst_col.addWidget(self._gst_type)
        gst_row.addLayout(gst_col)

        pct_col = QVBoxLayout()
        pct_col.setSpacing(4)
        pct_col.addWidget(QLabel("GST %"))
        self._gst_pct = QDoubleSpinBox()
        self._gst_pct.setFixedHeight(34)
        self._gst_pct.setRange(0, 28)
        self._gst_pct.setValue(5)
        self._gst_pct.setSuffix(" %")
        self._gst_pct.valueChanged.connect(self._recalc)
        pct_col.addWidget(self._gst_pct)
        gst_row.addLayout(pct_col)

        note_col = QVBoxLayout()
        note_col.setSpacing(4)
        note_col.addWidget(QLabel("Notes"))
        self._notes = QLineEdit()
        self._notes.setFixedHeight(34)
        self._notes.setPlaceholderText("Optional notes")
        note_col.addWidget(self._notes)
        gst_row.addLayout(note_col, 1)
        main.addLayout(gst_row)

        # Items section
        items_lbl = QLabel("ITEMS")
        items_lbl.setObjectName("card_title")
        main.addWidget(items_lbl)

        # Add item row
        add_row = QHBoxLayout()
        add_row.setSpacing(8)

        self._mat_combo = QComboBox()
        self._mat_combo.setFixedHeight(34)
        self._mat_combo.setMinimumWidth(200)
        mats = db.fetchall(
            """SELECT rmt.id, rmt.name, u.id as unit_id, u.abbreviation
               FROM raw_material_types rmt
               LEFT JOIN units u ON u.id=rmt.unit_id
               ORDER BY rmt.name"""
        )
        self._mat_data = mats
        self._mat_combo.addItem("— Select Material —")
        for m in mats:
            self._mat_combo.addItem(m["name"])
        add_row.addWidget(self._mat_combo)

        self._item_qty = QDoubleSpinBox()
        self._item_qty.setFixedHeight(34)
        self._item_qty.setRange(0.01, 99999)
        self._item_qty.setDecimals(2)
        self._item_qty.setFixedWidth(90)
        add_row.addWidget(self._item_qty)

        self._item_rate = QDoubleSpinBox()
        self._item_rate.setFixedHeight(34)
        self._item_rate.setRange(0.01, 9999999)
        self._item_rate.setDecimals(2)
        self._item_rate.setPrefix("₹ ")
        self._item_rate.setFixedWidth(120)
        add_row.addWidget(self._item_rate)

        add_btn = QPushButton("+ Add Item")
        add_btn.setObjectName("btn_primary")
        add_btn.setFixedHeight(34)
        add_btn.clicked.connect(self._add_item)
        add_row.addWidget(add_btn)
        add_row.addStretch()
        main.addLayout(add_row)

        # Items table
        self._items_table = QTableWidget()
        self._items_table.setColumnCount(6)
        self._items_table.setHorizontalHeaderLabels(
            ["Material", "Qty", "Unit", "Rate (₹)", "Amount (₹)", "Remove"]
        )
        self._items_table.verticalHeader().setVisible(False)
        self._items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._items_table.setAlternatingRowColors(True)
        self._items_table.horizontalHeader().setStretchLastSection(True)
        self._items_table.setShowGrid(False)
        self._items_table.setMaximumHeight(200)
        main.addWidget(self._items_table)

        # Totals
        totals_row = QHBoxLayout()
        totals_row.addStretch()
        self._totals_lbl = QLabel("")
        self._totals_lbl.setStyleSheet("font-size: 13px; color: #C7C7CC;")
        self._totals_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        totals_row.addWidget(self._totals_lbl)
        main.addLayout(totals_row)

        # Save button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(36)
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Bill & Generate PDF")
        save_btn.setObjectName("btn_primary")
        save_btn.setFixedHeight(36)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        main.addLayout(btn_row)

        self._recalc()

    def _on_supplier_change(self, idx):
        pass

    def _add_item(self):
        mat_idx = self._mat_combo.currentIndex()
        if mat_idx <= 0 or mat_idx - 1 >= len(self._mat_data):
            QMessageBox.warning(self, "Select Material", "Please select a material first.")
            return
        mat = self._mat_data[mat_idx - 1]
        qty = self._item_qty.value()
        rate = self._item_rate.value()
        amount = qty * rate
        self._items.append({
            "mat_id": mat["id"], "name": mat["name"],
            "qty": qty, "unit_id": mat["unit_id"],
            "unit": mat["abbreviation"] or "", "rate": rate, "amount": amount
        })
        self._refresh_items_table()
        self._recalc()

    def _refresh_items_table(self):
        self._items_table.setRowCount(0)
        for i, item in enumerate(self._items):
            r = self._items_table.rowCount()
            self._items_table.insertRow(r)
            for c, val in enumerate([
                item["name"], f"{item['qty']:.2f}", item["unit"],
                f"₹ {item['rate']:,.2f}", f"₹ {item['amount']:,.2f}"
            ]):
                cell = QTableWidgetItem(val)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self._items_table.setItem(r, c, cell)

            rem_btn = QPushButton("×")
            rem_btn.setFixedHeight(26)
            rem_btn.setStyleSheet("color: #D9685F; font-size: 16px; border: none; background: transparent; min-height: 0;")
            rem_btn.clicked.connect(lambda _, idx=i: self._remove_item(idx))
            self._items_table.setCellWidget(r, 5, rem_btn)

    def _remove_item(self, idx: int):
        if 0 <= idx < len(self._items):
            self._items.pop(idx)
            self._refresh_items_table()
            self._recalc()

    def _recalc(self):
        subtotal = sum(it["amount"] for it in self._items)
        gst_map = {0: ("none", 0), 1: ("cgst_sgst", self._gst_pct.value()),
                   2: ("igst", self._gst_pct.value())}
        gst_type_str, gst_pct = gst_map.get(self._gst_type.currentIndex(), ("none", 0))
        gst_amt = subtotal * gst_pct / 100 if gst_pct else 0
        total = subtotal + gst_amt
        self._totals_lbl.setText(
            f"Subtotal: ₹ {subtotal:,.2f}   |   "
            f"GST: ₹ {gst_amt:,.2f}   |   "
            f"<b>Total: ₹ {total:,.2f}</b>"
        )

    def _save(self):
        sup_idx = self._supplier.currentIndex()
        if sup_idx <= 0:
            QMessageBox.warning(self, "Required", "Please select a supplier.")
            return
        if not self._items:
            QMessageBox.warning(self, "Required", "Add at least one item.")
            return

        sup_id = self._sup_ids[sup_idx - 1]
        bill_date = self._date.date().toString("yyyy-MM-dd")
        bill_num = self._bill_num.text()

        subtotal = sum(it["amount"] for it in self._items)
        gst_map = {0: ("none", 0), 1: ("cgst_sgst", self._gst_pct.value()),
                   2: ("igst", self._gst_pct.value())}
        gst_type_str, gst_pct = gst_map.get(self._gst_type.currentIndex(), ("none", 0))
        gst_amt = subtotal * gst_pct / 100 if gst_pct else 0
        total = subtotal + gst_amt

        db.execute(
            """INSERT INTO purchase_bills
               (bill_number, supplier_id, bill_date, subtotal, gst_type, gst_percent,
                gst_amount, total_amount, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (bill_num, sup_id, bill_date, subtotal, gst_type_str, gst_pct,
             gst_amt, total, self._notes.text().strip())
        )
        bill_id = db.fetchone("SELECT last_insert_rowid() as id")["id"]

        for it in self._items:
            db.execute(
                """INSERT INTO purchase_bill_items
                   (bill_id, material_type_id, quantity, unit_id, rate, amount)
                   VALUES (?,?,?,?,?,?)""",
                (bill_id, it["mat_id"], it["qty"], it["unit_id"], it["rate"], it["amount"])
            )
            db.adjust_raw_stock(it["mat_id"], it["qty"], it["rate"])
            db.execute(
                """INSERT INTO raw_material_transactions
                   (material_type_id, transaction_type, quantity, rate, reference_id, reference_type)
                   VALUES (?,?,?,?,?,?)""",
                (it["mat_id"], "purchase", it["qty"], it["rate"], bill_id, "purchase_bill")
            )

        try:
            path = generate_purchase_bill(bill_id, self._app_dir)
            QMessageBox.information(self, "Bill Saved",
                                    f"Purchase bill saved!\nPDF: {path}")
        except Exception as e:
            QMessageBox.warning(self, "PDF Error",
                                f"Bill saved but PDF failed:\n{e}")

        self.accept()
