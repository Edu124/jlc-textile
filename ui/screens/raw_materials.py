from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QComboBox, QDoubleSpinBox, QMessageBox,
    QFormLayout, QDialogButtonBox, QFrame, QTabWidget, QLineEdit
)
from PyQt6.QtCore import Qt
import core.database as db
from ui.widgets.components import DataTable, SectionHeader, SearchBar, StatCard


class RawMaterialsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        hdr = SectionHeader("Raw Materials Stock", "+ Add Stock Entry")
        if hdr.btn:
            hdr.btn.clicked.connect(self._add_stock)
        lay.addWidget(hdr)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self._total_card = StatCard("Total Materials", "0", "◈", "#5E7E9B")
        self._value_card = StatCard("Total Stock Value", "₹ 0", "₹", "#5FB07C")
        self._low_card = StatCard("Low Stock Items", "0", "⚠", "#D9685F")
        stats_row.addWidget(self._total_card)
        stats_row.addWidget(self._value_card)
        stats_row.addWidget(self._low_card)
        stats_row.addStretch()
        lay.addLayout(stats_row)

        # Search + filter
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)
        self._search = SearchBar("Search material...")
        self._search.textChanged.connect(self._filter)
        self._low_btn = QPushButton("Show Low Stock Only")
        self._low_btn.setObjectName("btn_warning")
        self._low_btn.setFixedHeight(34)
        self._low_btn.setCheckable(True)
        self._low_btn.toggled.connect(self._toggle_low)
        filter_row.addWidget(self._search, 1)
        filter_row.addWidget(self._low_btn)
        lay.addLayout(filter_row)

        # Table
        self._table = DataTable(
            ["ID", "Material", "Unit", "Qty in Stock", "Avg Rate (₹)", "Stock Value (₹)",
             "Low Stock Alert", "Status", "Actions"]
        )
        self._table.setColumnWidth(0, 50)
        self._table.setColumnWidth(1, 200)
        self._table.setColumnWidth(3, 110)
        lay.addWidget(self._table, 1)

        # Transactions history tab area
        tx_label = QLabel("RECENT TRANSACTIONS")
        tx_label.setObjectName("card_title")
        tx_label.setContentsMargins(0, 8, 0, 4)
        lay.addWidget(tx_label)

        self._tx_table = DataTable(
            ["Date", "Material", "Type", "Qty", "Rate (₹)", "Reference"]
        )
        self._tx_table.setMaximumHeight(160)
        lay.addWidget(self._tx_table)

        self.refresh()

    def _fetch_rows(self):
        return db.fetchall(
            """SELECT rmt.id, rmt.name, u.abbreviation, rms.quantity, rms.avg_rate,
                      rmt.low_stock_threshold
               FROM raw_material_types rmt
               LEFT JOIN raw_material_stock rms ON rms.material_type_id = rmt.id
               LEFT JOIN units u ON u.id = rmt.unit_id
               ORDER BY rmt.name"""
        )

    def refresh(self):
        rows = self._fetch_rows()
        self._all_rows = rows
        self._render_table(rows)
        self._refresh_transactions()
        self._update_stats(rows)

    def _render_table(self, rows):
        display = []
        for r in rows:
            qty = r["quantity"] or 0
            rate = r["avg_rate"] or 0
            value = qty * rate
            threshold = r["low_stock_threshold"] or 0
            status = "Low Stock" if (threshold > 0 and qty <= threshold) else "OK"
            display.append([
                r["id"], r["name"], r["abbreviation"] or "",
                f"{qty:.2f}", f"{rate:.2f}", f"{value:,.2f}",
                f"{threshold:.2f}", status
            ])
        self._table.load_rows(display)

        for row_idx in range(self._table.rowCount()):
            status_item = self._table.item(row_idx, 7)
            if status_item:
                status_txt = status_item.text()
                self._table.add_status_badge(row_idx, 7,
                    "Received" if status_txt == "OK" else "Cancelled")
                status_item.setText(status_txt)

            # action buttons
            edit_btn = QPushButton("+ Stock")
            edit_btn.setObjectName("btn_flat")
            edit_btn.setStyleSheet("color: #5FB07C; font-size: 12px;")
            edit_btn.setFixedHeight(28)
            edit_btn.clicked.connect(lambda _, r=row_idx: self._add_stock_for_row(r))

            adj_btn = QPushButton("Adjust")
            adj_btn.setObjectName("btn_flat")
            adj_btn.setStyleSheet("color: #5E7E9B; font-size: 12px;")
            adj_btn.setFixedHeight(28)
            adj_btn.clicked.connect(lambda _, r=row_idx: self._adjust_row(r))

            w = QWidget()
            wl = QHBoxLayout(w)
            wl.setContentsMargins(4, 0, 4, 0)
            wl.setSpacing(4)
            wl.addWidget(edit_btn)
            wl.addWidget(adj_btn)
            wl.addStretch()
            self._table.setCellWidget(row_idx, 8, w)

    def _update_stats(self, rows):
        total = len(rows)
        value = sum((r["quantity"] or 0) * (r["avg_rate"] or 0) for r in rows)
        low = sum(1 for r in rows if (r["low_stock_threshold"] or 0) > 0
                  and (r["quantity"] or 0) <= r["low_stock_threshold"])
        self._total_card.set_value(str(total))
        self._value_card.set_value(f"₹ {value:,.0f}")
        self._low_card.set_value(str(low))

    def _refresh_transactions(self):
        txs = db.fetchall(
            """SELECT rmt.name as material, t.transaction_type, t.quantity, t.rate,
                      t.reference_type, t.created_at
               FROM raw_material_transactions t
               JOIN raw_material_types rmt ON rmt.id = t.material_type_id
               ORDER BY t.id DESC LIMIT 20"""
        )
        rows = []
        for t in txs:
            rows.append([
                str(t["created_at"])[:16],
                t["material"],
                t["transaction_type"].title(),
                f"{t['quantity']:.2f}",
                f"₹ {t['rate']:.2f}" if t["rate"] else "",
                t["reference_type"] or ""
            ])
        self._tx_table.load_rows(rows)

    def _filter(self, text):
        if not text:
            self._render_table(self._all_rows)
        else:
            filtered = [r for r in self._all_rows
                        if text.lower() in (r["name"] or "").lower()]
            self._render_table(filtered)

    def _toggle_low(self, checked):
        if checked:
            filtered = [r for r in self._all_rows
                        if (r["low_stock_threshold"] or 0) > 0
                        and (r["quantity"] or 0) <= r["low_stock_threshold"]]
            self._render_table(filtered)
        else:
            self._render_table(self._all_rows)

    def _add_stock(self):
        dlg = _StockEntryDialog(None, self)
        if dlg.exec():
            self.refresh()

    def _add_stock_for_row(self, row_idx):
        mat_id = int(self._table.item(row_idx, 0).text())
        dlg = _StockEntryDialog(mat_id, self)
        if dlg.exec():
            self.refresh()

    def _adjust_row(self, row_idx):
        mat_id = int(self._table.item(row_idx, 0).text())
        mat_name = self._table.item(row_idx, 1).text()
        cur_qty_text = self._table.item(row_idx, 3).text()
        dlg = _AdjustDialog(mat_id, mat_name, float(cur_qty_text), self)
        if dlg.exec():
            self.refresh()


class _StockEntryDialog(QDialog):
    def __init__(self, material_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Stock Entry")
        self.setMinimumWidth(420)
        self.setModal(True)

        lay = QFormLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)
        lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._material = QComboBox()
        self._material.setFixedHeight(34)
        mats = db.fetchall("SELECT id, name FROM raw_material_types ORDER BY name")
        self._mat_ids = [m["id"] for m in mats]
        for m in mats:
            self._material.addItem(m["name"])
        if material_id and material_id in self._mat_ids:
            self._material.setCurrentIndex(self._mat_ids.index(material_id))

        self._qty = QDoubleSpinBox()
        self._qty.setFixedHeight(34)
        self._qty.setRange(0.01, 999999)
        self._qty.setDecimals(2)

        self._rate = QDoubleSpinBox()
        self._rate.setFixedHeight(34)
        self._rate.setRange(0, 9999999)
        self._rate.setDecimals(2)
        self._rate.setPrefix("₹ ")

        self._note = QLineEdit()
        self._note.setFixedHeight(34)
        self._note.setPlaceholderText("Optional note")

        lay.addRow("Material *", self._material)
        lay.addRow("Quantity *", self._qty)
        lay.addRow("Rate per unit *", self._rate)
        lay.addRow("Note", self._note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("btn_primary")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay.addRow("", buttons)

    def _save(self):
        mat_id = self._mat_ids[self._material.currentIndex()]
        qty = self._qty.value()
        rate = self._rate.value()
        if qty <= 0:
            QMessageBox.warning(self, "Invalid", "Quantity must be greater than 0.")
            return
        db.adjust_raw_stock(mat_id, qty, rate)
        db.execute(
            """INSERT INTO raw_material_transactions
               (material_type_id, transaction_type, quantity, rate, reference_type, notes)
               VALUES (?,?,?,?,?,?)""",
            (mat_id, "manual_addition", qty, rate, "manual", self._note.text().strip())
        )
        self.accept()


class _AdjustDialog(QDialog):
    def __init__(self, material_id, material_name, current_qty, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Adjust Stock — {material_name}")
        self.setMinimumWidth(380)
        self.setModal(True)
        self._mat_id = material_id

        lay = QFormLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)
        lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        cur_lbl = QLabel(f"Current Stock: {current_qty:.2f}")
        cur_lbl.setStyleSheet("color: #C7C7CC;")
        lay.addRow("", cur_lbl)

        self._new_qty = QDoubleSpinBox()
        self._new_qty.setFixedHeight(34)
        self._new_qty.setRange(0, 999999)
        self._new_qty.setDecimals(2)
        self._new_qty.setValue(current_qty)

        self._note = QLineEdit()
        self._note.setFixedHeight(34)
        self._note.setPlaceholderText("Reason for adjustment")

        lay.addRow("New Quantity *", self._new_qty)
        lay.addRow("Reason *", self._note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("btn_warning")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay.addRow("", buttons)
        self._current_qty = current_qty

    def _save(self):
        note = self._note.text().strip()
        if not note:
            QMessageBox.warning(self, "Required", "Please enter a reason for adjustment.")
            return
        new_qty = self._new_qty.value()
        delta = new_qty - self._current_qty
        db.execute(
            "UPDATE raw_material_stock SET quantity=?, last_updated=datetime('now','localtime') WHERE material_type_id=?",
            (new_qty, self._mat_id)
        )
        db.execute(
            """INSERT INTO raw_material_transactions
               (material_type_id, transaction_type, quantity, reference_type, notes)
               VALUES (?,?,?,?,?)""",
            (self._mat_id, "adjustment", delta, "adjustment", note)
        )
        self.accept()
