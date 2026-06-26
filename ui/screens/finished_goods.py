from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QComboBox, QDoubleSpinBox, QMessageBox, QFormLayout
)
from PyQt6.QtCore import Qt
import core.database as db
from ui.widgets.components import DataTable, SectionHeader, SearchBar, StatCard


class FinishedGoodsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        hdr = SectionHeader("Finished Goods Stock", "+ Manual Adjustment")
        if hdr.btn:
            hdr.btn.clicked.connect(self._adjust)
        lay.addWidget(hdr)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self._total_card = StatCard("Total Products", "0", "◼", "#5E7E9B")
        self._qty_card   = StatCard("Total Qty in Stock", "0", "◉", "#7FA8B8")
        self._val_card   = StatCard("Approx. Stock Value", "₹ 0", "₹", "#5FB07C")
        stats_row.addWidget(self._total_card)
        stats_row.addWidget(self._qty_card)
        stats_row.addWidget(self._val_card)
        stats_row.addStretch()
        lay.addLayout(stats_row)

        self._search = SearchBar("Search product, category...")
        self._search.textChanged.connect(self._filter)
        lay.addWidget(self._search)

        self._table = DataTable(
            ["ID", "Product", "Category", "Unit", "Qty in Stock", "Sale Rate (₹)",
             "Est. Value (₹)", "Actions"]
        )
        lay.addWidget(self._table, 1)

        hist_lbl = QLabel("RECENT TRANSACTIONS")
        hist_lbl.setObjectName("card_title")
        hist_lbl.setContentsMargins(0, 8, 0, 4)
        lay.addWidget(hist_lbl)

        self._tx_table = DataTable(["Date", "Product", "Type", "Qty"])
        self._tx_table.setMaximumHeight(150)
        lay.addWidget(self._tx_table)

        self.refresh()

    def refresh(self):
        rows = db.fetchall(
            """SELECT p.id, p.name, pc.name as category, u.abbreviation as unit,
                      COALESCE(fgs.quantity,0) as qty, p.sale_rate
               FROM products p
               LEFT JOIN product_categories pc ON pc.id=p.category_id
               LEFT JOIN units u ON u.id=p.unit_id
               LEFT JOIN finished_goods_stock fgs ON fgs.product_id=p.id
               WHERE p.is_active=1
               ORDER BY p.name"""
        )
        self._all_rows = rows
        self._render(rows)
        self._refresh_tx()
        self._update_stats(rows)

    def _render(self, rows):
        display = []
        for r in rows:
            value = r["qty"] * r["sale_rate"]
            display.append([
                r["id"], r["name"], r["category"] or "", r["unit"] or "",
                f"{r['qty']:.2f}", f"₹ {r['sale_rate']:,.2f}", f"₹ {value:,.2f}"
            ])
        self._table.load_rows(display)

        for row_idx, r in enumerate(rows):
            adj_btn = QPushButton("Adjust")
            adj_btn.setObjectName("btn_flat")
            adj_btn.setStyleSheet("color: #5E7E9B; font-size: 12px;")
            adj_btn.setFixedHeight(28)
            prod_id = r["id"]
            cur_qty = r["qty"]
            adj_btn.clicked.connect(lambda _, pid=prod_id, q=cur_qty: self._adjust_product(pid, q))

            w = QWidget()
            wl = QHBoxLayout(w)
            wl.setContentsMargins(4, 0, 4, 0)
            wl.addWidget(adj_btn)
            wl.addStretch()
            self._table.setCellWidget(row_idx, 7, w)

    def _update_stats(self, rows):
        total = len(rows)
        qty = sum(r["qty"] for r in rows)
        val = sum(r["qty"] * r["sale_rate"] for r in rows)
        self._total_card.set_value(str(total))
        self._qty_card.set_value(f"{qty:,.0f}")
        self._val_card.set_value(f"₹ {val:,.0f}")

    def _refresh_tx(self):
        txs = db.fetchall(
            """SELECT fgt.created_at, p.name, fgt.transaction_type, fgt.quantity
               FROM finished_goods_transactions fgt
               JOIN products p ON p.id=fgt.product_id
               ORDER BY fgt.id DESC LIMIT 20"""
        )
        self._tx_table.load_rows([
            [str(t["created_at"])[:16], t["name"],
             t["transaction_type"].title(), f"{t['quantity']:.2f}"]
            for t in txs
        ])

    def _filter(self, text):
        if not text:
            self._render(self._all_rows)
        else:
            filtered = [r for r in self._all_rows
                        if text.lower() in (r["name"] or "").lower()
                        or text.lower() in (r["category"] or "").lower()]
            self._render(filtered)

    def _adjust(self):
        dlg = _AdjustFGDialog(None, 0, self)
        if dlg.exec():
            self.refresh()

    def _adjust_product(self, product_id: int, current_qty: float):
        dlg = _AdjustFGDialog(product_id, current_qty, self)
        if dlg.exec():
            self.refresh()


class _AdjustFGDialog(QDialog):
    def __init__(self, product_id, current_qty, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Finished Goods Adjustment")
        self.setMinimumWidth(400)
        self.setModal(True)

        lay = QFormLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)
        lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._product = QComboBox()
        self._product.setFixedHeight(36)
        products = db.fetchall("SELECT id, name FROM products WHERE is_active=1 ORDER BY name")
        self._prod_ids = [p["id"] for p in products]
        self._product.addItem("— Select Product —")
        for p in products:
            self._product.addItem(p["name"])
        if product_id and product_id in self._prod_ids:
            self._product.setCurrentIndex(self._prod_ids.index(product_id) + 1)
            self._product.setEnabled(False)

        self._new_qty = QDoubleSpinBox()
        self._new_qty.setFixedHeight(36)
        self._new_qty.setRange(0, 999999)
        self._new_qty.setDecimals(2)
        self._new_qty.setValue(current_qty)

        self._reason = QComboBox()
        self._reason.setFixedHeight(36)
        self._reason.addItems(["Manual Adjustment", "Damage/Write-off", "Found in Stock", "Transfer"])

        lay.addRow("Product *", self._product)
        lay.addRow("New Quantity *", self._new_qty)
        lay.addRow("Reason", self._reason)

        from PyQt6.QtWidgets import QDialogButtonBox
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("btn_warning")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay.addRow("", buttons)
        self._current_qty = current_qty

    def _save(self):
        idx = self._product.currentIndex()
        if idx <= 0:
            QMessageBox.warning(self, "Required", "Please select a product.")
            return
        prod_id = self._prod_ids[idx - 1]
        new_qty = self._new_qty.value()
        delta = new_qty - self._current_qty
        db.adjust_finished_stock(prod_id, delta)
        db.execute(
            """INSERT INTO finished_goods_transactions
               (product_id, transaction_type, quantity, reference_type)
               VALUES (?,?,?,?)""",
            (prod_id, "adjustment", delta, self._reason.currentText())
        )
        self.accept()
