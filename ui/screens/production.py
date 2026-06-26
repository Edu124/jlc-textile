from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QComboBox, QDoubleSpinBox, QMessageBox,
    QFormLayout, QDialogButtonBox, QTextEdit, QFrame, QLineEdit,
    QAbstractItemView
)
from PyQt6.QtCore import Qt
import core.database as db
from ui.widgets.components import DataTable, SectionHeader, SearchBar
from ui.styles import STATUS_COLORS

STAGES = ["Cutting", "Stitching", "Dyeing", "Finishing", "QC", "Completed"]


class ProductionScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        hdr = SectionHeader("Production Batches", "+ New Batch")
        if hdr.btn:
            hdr.btn.clicked.connect(self._new_batch)
        lay.addWidget(hdr)

        # Filter bar
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)
        self._search = SearchBar("Search batch number, product...")
        self._search.textChanged.connect(self._filter)
        self._stage_filter = QComboBox()
        self._stage_filter.setFixedHeight(34)
        self._stage_filter.addItem("All Stages")
        self._stage_filter.addItems(STAGES)
        self._stage_filter.currentIndexChanged.connect(self._filter)
        filter_row.addWidget(self._search, 1)
        filter_row.addWidget(self._stage_filter)
        lay.addLayout(filter_row)

        # Table
        self._table = DataTable(
            ["Batch #", "Product", "Qty", "Stage", "Order #", "Started", "Actions"]
        )
        self._table.setColumnWidth(0, 120)
        self._table.setColumnWidth(1, 200)
        self._table.setColumnWidth(3, 120)
        lay.addWidget(self._table, 1)

        # Stage history
        hist_lbl = QLabel("STAGE HISTORY (selected batch)")
        hist_lbl.setObjectName("card_title")
        hist_lbl.setContentsMargins(0, 8, 0, 4)
        lay.addWidget(hist_lbl)

        self._hist_table = DataTable(["Date", "Stage", "Notes"])
        self._hist_table.setMaximumHeight(140)
        lay.addWidget(self._hist_table)

        self._table.itemSelectionChanged.connect(self._on_select)
        self.refresh()

    def refresh(self):
        rows = db.fetchall(
            """SELECT pb.id, pb.batch_number, p.name as product,
                      pb.quantity, pb.current_stage, pb.order_id, pb.started_at,
                      u.abbreviation
               FROM production_batches pb
               JOIN products p ON p.id=pb.product_id
               LEFT JOIN units u ON u.id=p.unit_id
               ORDER BY pb.id DESC"""
        )
        self._all_rows = rows
        self._render(rows)

    def _render(self, rows):
        display = []
        for r in rows:
            display.append([
                r["batch_number"], r["product"],
                f"{r['quantity']:.0f} {r['abbreviation'] or ''}",
                r["current_stage"],
                str(r["order_id"]) if r["order_id"] else "—",
                str(r["started_at"])[:10]
            ])
        self._table.load_rows(display)
        self._ids = [r["id"] for r in rows]

        for row_idx in range(self._table.rowCount()):
            batch_id = self._ids[row_idx]
            stage = rows[row_idx]["current_stage"]

            self._table.add_status_badge(row_idx, 3, stage)

            advance_btn = QPushButton("Advance Stage")
            advance_btn.setObjectName("btn_flat")
            advance_btn.setStyleSheet("color: #5FB07C; font-size: 12px;")
            advance_btn.setFixedHeight(28)
            advance_btn.setEnabled(stage != "Completed")
            advance_btn.clicked.connect(lambda _, bid=batch_id, s=stage: self._advance(bid, s))

            view_btn = QPushButton("View")
            view_btn.setObjectName("btn_flat")
            view_btn.setStyleSheet("color: #5E7E9B; font-size: 12px;")
            view_btn.setFixedHeight(28)
            view_btn.clicked.connect(lambda _, bid=batch_id: self._view_batch(bid))

            w = QWidget()
            wl = QHBoxLayout(w)
            wl.setContentsMargins(4, 0, 4, 0)
            wl.setSpacing(4)
            wl.addWidget(advance_btn)
            wl.addWidget(view_btn)
            wl.addStretch()
            self._table.setCellWidget(row_idx, 6, w)

    def _filter(self):
        text = self._search.text().lower()
        stage = self._stage_filter.currentText()
        filtered = self._all_rows
        if text:
            filtered = [r for r in filtered
                        if text in (r["batch_number"] or "").lower()
                        or text in (r["product"] or "").lower()]
        if stage != "All Stages":
            filtered = [r for r in filtered if r["current_stage"] == stage]
        self._render(filtered)

    def _new_batch(self):
        dlg = _NewBatchDialog(self)
        if dlg.exec():
            self.refresh()

    def _advance(self, batch_id: int, current_stage: str):
        idx = STAGES.index(current_stage) if current_stage in STAGES else -1
        if idx < 0 or idx >= len(STAGES) - 1:
            QMessageBox.information(self, "Done", "Batch is already completed.")
            return
        next_stage = STAGES[idx + 1]

        dlg = _AdvanceStageDialog(current_stage, next_stage, self)
        if dlg.exec():
            note = dlg.get_note()
            db.execute(
                "UPDATE production_batches SET current_stage=? WHERE id=?",
                (next_stage, batch_id)
            )
            db.execute(
                "INSERT INTO batch_stage_history (batch_id, stage, notes) VALUES (?,?,?)",
                (batch_id, next_stage, note)
            )
            if next_stage == "Completed":
                batch = db.fetchone(
                    "SELECT product_id, quantity FROM production_batches WHERE id=?",
                    (batch_id,)
                )
                if batch:
                    db.adjust_finished_stock(batch["product_id"], batch["quantity"])
                    db.execute(
                        """INSERT INTO finished_goods_transactions
                           (product_id, transaction_type, quantity, reference_id, reference_type)
                           VALUES (?,?,?,?,?)""",
                        (batch["product_id"], "production", batch["quantity"],
                         batch_id, "production_batch")
                    )
                    db.execute(
                        "UPDATE production_batches SET completed_at=datetime('now','localtime') WHERE id=?",
                        (batch_id,)
                    )
                    QMessageBox.information(
                        self, "Production Complete",
                        "Batch completed! Finished goods stock has been updated."
                    )
            self.refresh()

    def _view_batch(self, batch_id: int):
        dlg = _ViewBatchDialog(batch_id, self)
        dlg.exec()

    def _on_select(self):
        rows = self._table.selectedItems()
        if not rows:
            return
        row_idx = self._table.currentRow()
        if row_idx < 0 or row_idx >= len(self._ids):
            return
        batch_id = self._ids[row_idx]
        hist = db.fetchall(
            "SELECT changed_at, stage, notes FROM batch_stage_history WHERE batch_id=? ORDER BY id",
            (batch_id,)
        )
        self._hist_table.load_rows([
            [str(h["changed_at"])[:16], h["stage"], h["notes"] or ""]
            for h in hist
        ])


class _AdvanceStageDialog(QDialog):
    def __init__(self, from_stage: str, to_stage: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Advance: {from_stage} → {to_stage}")
        self.setMinimumWidth(380)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        msg = QLabel(f"Moving batch from <b>{from_stage}</b> to <b>{to_stage}</b>")
        msg.setStyleSheet("color: #C7C7CC; font-size: 13px;")
        lay.addWidget(msg)

        lay.addWidget(QLabel("Notes (optional):"))
        self._note = QTextEdit()
        self._note.setFixedHeight(80)
        self._note.setPlaceholderText("Any notes about this stage...")
        lay.addWidget(self._note)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        ok = QPushButton(f"Advance to {to_stage}")
        ok.setObjectName("btn_primary")
        ok.clicked.connect(self.accept)
        btn_row.addWidget(cancel)
        btn_row.addWidget(ok)
        lay.addLayout(btn_row)

    def get_note(self) -> str:
        return self._note.toPlainText().strip()


class _NewBatchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Production Batch")
        self.setMinimumWidth(460)
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

        self._qty = QDoubleSpinBox()
        self._qty.setFixedHeight(36)
        self._qty.setRange(1, 99999)
        self._qty.setDecimals(0)

        self._order = QComboBox()
        self._order.setFixedHeight(36)
        orders = db.fetchall(
            "SELECT id, order_number FROM orders WHERE status NOT IN ('Delivered','Cancelled') ORDER BY id DESC"
        )
        self._order_ids = [None] + [o["id"] for o in orders]
        self._order.addItem("— Not linked to order (stock production) —")
        for o in orders:
            self._order.addItem(o["order_number"])

        self._notes = QTextEdit()
        self._notes.setFixedHeight(60)
        self._notes.setPlaceholderText("Optional notes about this batch")

        self._batch_num = QLineEdit()
        self._batch_num.setText(db.next_batch_number())
        self._batch_num.setReadOnly(True)
        self._batch_num.setStyleSheet("color: #AEAEB2;")

        lay.addRow("Batch #", self._batch_num)
        lay.addRow("Product *", self._product)
        lay.addRow("Quantity *", self._qty)
        lay.addRow("Linked Order", self._order)
        lay.addRow("Notes", self._notes)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("btn_primary")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay.addRow("", buttons)

    def _save(self):
        prod_idx = self._product.currentIndex()
        if prod_idx <= 0:
            QMessageBox.warning(self, "Required", "Please select a product.")
            return
        prod_id = self._prod_ids[prod_idx - 1]
        qty = self._qty.value()
        order_id = self._order_ids[self._order.currentIndex()]

        bom = db.fetchall(
            "SELECT material_type_id, quantity_required FROM product_bom WHERE product_id=?",
            (prod_id,)
        )
        for bom_item in bom:
            needed = bom_item["quantity_required"] * qty
            stock = db.fetchone(
                "SELECT quantity FROM raw_material_stock WHERE material_type_id=?",
                (bom_item["material_type_id"],)
            )
            avail = stock["quantity"] if stock else 0
            if avail < needed:
                mat = db.fetchone(
                    "SELECT name FROM raw_material_types WHERE id=?",
                    (bom_item["material_type_id"],)
                )
                QMessageBox.warning(
                    self, "Insufficient Stock",
                    f"Not enough stock for {mat['name']}.\n"
                    f"Needed: {needed:.2f}, Available: {avail:.2f}"
                )
                return

        batch_num = self._batch_num.text()
        db.execute(
            """INSERT INTO production_batches
               (batch_number, product_id, quantity, order_id, current_stage, notes)
               VALUES (?,?,?,?,?,?)""",
            (batch_num, prod_id, qty, order_id, "Cutting",
             self._notes.toPlainText().strip())
        )
        batch_id = db.fetchone("SELECT last_insert_rowid() as id")["id"]

        db.execute(
            "INSERT INTO batch_stage_history (batch_id, stage, notes) VALUES (?,?,?)",
            (batch_id, "Cutting", "Batch started")
        )

        for bom_item in bom:
            consumed = bom_item["quantity_required"] * qty
            db.adjust_raw_stock(bom_item["material_type_id"], -consumed)
            db.execute(
                """INSERT INTO raw_material_transactions
                   (material_type_id, transaction_type, quantity, reference_id, reference_type)
                   VALUES (?,?,?,?,?)""",
                (bom_item["material_type_id"], "consumption", -consumed,
                 batch_id, "production_batch")
            )

        self.accept()


class _ViewBatchDialog(QDialog):
    def __init__(self, batch_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Details")
        self.setMinimumSize(520, 400)
        self.setModal(True)

        batch = db.fetchone(
            """SELECT pb.*, p.name as product, u.abbreviation
               FROM production_batches pb
               JOIN products p ON p.id=pb.product_id
               LEFT JOIN units u ON u.id=p.unit_id
               WHERE pb.id=?""",
            (batch_id,)
        )
        hist = db.fetchall(
            "SELECT changed_at, stage, notes FROM batch_stage_history WHERE batch_id=? ORDER BY id",
            (batch_id,)
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)

        for label, value in [
            ("Batch #", batch["batch_number"]),
            ("Product", batch["product"]),
            ("Quantity", f"{batch['quantity']:.0f} {batch['abbreviation'] or ''}"),
            ("Current Stage", batch["current_stage"]),
            ("Started", str(batch["started_at"])[:16]),
            ("Completed", str(batch["completed_at"])[:16] if batch["completed_at"] else "—"),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(label + ":")
            lbl.setStyleSheet("color: #AEAEB2; font-size: 12px;")
            lbl.setFixedWidth(100)
            val = QLabel(str(value))
            val.setStyleSheet("color: #E5E5EA;")
            row.addWidget(lbl)
            row.addWidget(val, 1)
            lay.addLayout(row)

        lay.addWidget(QLabel("Stage History:"))
        hist_table = DataTable(["Date", "Stage", "Notes"])
        hist_table.load_rows([
            [str(h["changed_at"])[:16], h["stage"], h["notes"] or ""]
            for h in hist
        ])
        lay.addWidget(hist_table, 1)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(close_btn)
        lay.addLayout(close_row)
