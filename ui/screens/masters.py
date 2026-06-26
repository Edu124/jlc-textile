import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit,
    QMessageBox, QFormLayout, QDialogButtonBox, QFrame,
    QFileDialog, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
import core.database as db
from ui.widgets.components import DataTable, SectionHeader, SearchBar, HSep


# ── Base Master Screen ────────────────────────────────────────────────────────

class BaseMasterScreen(QWidget):
    SOFT_DELETE = False  # tables with an is_active column hide instead of delete

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        # Header
        hdr = SectionHeader(self.TITLE, f"+ Add {self.ITEM_NAME}")
        if hdr.btn:
            hdr.btn.clicked.connect(self._open_add_dialog)
        lay.addWidget(hdr)

        # Search
        self._search = SearchBar(f"Search {self.TITLE.lower()}...")
        self._search.textChanged.connect(self._filter_table)
        lay.addWidget(self._search)

        # Table
        self._table = DataTable(self.HEADERS)
        self._table.doubleClicked.connect(self._on_double_click)
        lay.addWidget(self._table, 1)

        self.refresh()

    def refresh(self):
        rows = self._fetch_rows()
        self._all_rows = rows
        self._table.load_rows(rows)
        self._add_action_buttons()

    def _filter_table(self, text: str):
        if not hasattr(self, "_all_rows"):
            return
        if not text:
            self._table.load_rows(self._all_rows)
            self._add_action_buttons()
            return
        filtered = [
            r for r in self._all_rows
            if any(text.lower() in str(v).lower() for v in r)
        ]
        self._table.load_rows(filtered)
        self._add_action_buttons()

    def _add_action_buttons(self):
        for r in range(self._table.rowCount()):
            edit_btn = QPushButton("Edit")
            edit_btn.setObjectName("btn_flat")
            edit_btn.setStyleSheet("color: #5E7E9B; font-size: 12px;")
            edit_btn.setFixedHeight(28)
            edit_btn.clicked.connect(lambda _, row=r: self._edit_row(row))

            del_btn = QPushButton("Delete")
            del_btn.setObjectName("btn_flat")
            del_btn.setStyleSheet("color: #D9685F; font-size: 12px;")
            del_btn.setFixedHeight(28)
            del_btn.clicked.connect(lambda _, row=r: self._delete_row(row))

            w = QWidget()
            wl = QHBoxLayout(w)
            wl.setContentsMargins(4, 0, 4, 0)
            wl.setSpacing(4)
            wl.addWidget(edit_btn)
            wl.addWidget(del_btn)
            wl.addStretch()
            self._table.setCellWidget(r, self._action_col(), w)

    def _action_col(self):
        return len(self.HEADERS) - 1

    def _on_double_click(self, index):
        self._edit_row(index.row())

    def _open_add_dialog(self):
        dlg = self._make_dialog(None)
        if dlg.exec():
            self.refresh()

    def _edit_row(self, row: int):
        row_id = int(self._table.item(row, 0).text())
        dlg = self._make_dialog(row_id)
        if dlg.exec():
            self.refresh()

    def _delete_row(self, row: int):
        row_id = int(self._table.item(row, 0).text())
        name = self._table.item(row, 1).text()
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.SOFT_DELETE:
                    # Keep the record (it may be referenced by bills/orders),
                    # just hide it from active lists.
                    db.execute(f"UPDATE {self.TABLE} SET is_active=0 WHERE id=?", (row_id,))
                else:
                    db.execute(f"DELETE FROM {self.TABLE} WHERE id=?", (row_id,))
                self.refresh()
            except Exception as e:
                QMessageBox.warning(
                    self, "Cannot Delete",
                    f"'{name}' is used in existing bills or orders, so it can't be "
                    f"removed.\n\nYou can edit it instead.")

    def _fetch_rows(self):
        raise NotImplementedError

    def _make_dialog(self, row_id):
        raise NotImplementedError


# ── Dialog helpers ────────────────────────────────────────────────────────────

def _make_field(placeholder="", max_length=200) -> QLineEdit:
    f = QLineEdit()
    f.setPlaceholderText(placeholder)
    f.setMaxLength(max_length)
    f.setFixedHeight(34)
    return f


def _make_text_area(placeholder="") -> QTextEdit:
    t = QTextEdit()
    t.setPlaceholderText(placeholder)
    t.setFixedHeight(70)
    return t


class _BaseDialog(QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(440)
        self.setModal(True)
        self._lay = QFormLayout(self)
        self._lay.setContentsMargins(24, 20, 24, 20)
        self._lay.setSpacing(12)
        self._lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

    def _add_buttons(self):
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setObjectName("btn_primary")
        self._lay.addRow("", buttons)

    def _on_save(self):
        raise NotImplementedError


# ══════════════════════════════════════════════════════════════════════════════
# SUPPLIERS
# ══════════════════════════════════════════════════════════════════════════════

class SuppliersScreen(BaseMasterScreen):
    SOFT_DELETE = True
    TITLE = "Suppliers"
    ITEM_NAME = "Supplier"
    TABLE = "suppliers"
    HEADERS = ["ID", "Name", "Phone", "Email", "GST Number", "Actions"]

    def _fetch_rows(self):
        rows = db.fetchall(
            "SELECT id, name, phone, email, gst_number FROM suppliers WHERE is_active=1 ORDER BY name"
        )
        return [[r["id"], r["name"], r["phone"] or "", r["email"] or "", r["gst_number"] or ""]
                for r in rows]

    def _make_dialog(self, row_id):
        return _SupplierDialog(row_id, self)


class _SupplierDialog(_BaseDialog):
    def __init__(self, row_id, parent=None):
        super().__init__("Add Supplier" if row_id is None else "Edit Supplier", parent)
        self._id = row_id

        self._name = _make_field("Full supplier name", 100)
        self._phone = _make_field("Phone number", 20)
        self._email = _make_field("Email address", 100)
        self._gst = _make_field("GST Number (e.g. 24XXXXX)", 20)
        self._addr = _make_text_area("Full address")

        self._lay.addRow("Name *", self._name)
        self._lay.addRow("Phone", self._phone)
        self._lay.addRow("Email", self._email)
        self._lay.addRow("GST Number", self._gst)
        self._lay.addRow("Address", self._addr)
        self._add_buttons()

        if row_id:
            row = db.fetchone("SELECT * FROM suppliers WHERE id=?", (row_id,))
            if row:
                self._name.setText(row["name"])
                self._phone.setText(row["phone"] or "")
                self._email.setText(row["email"] or "")
                self._gst.setText(row["gst_number"] or "")
                self._addr.setText(row["address"] or "")

    def _on_save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "Required", "Supplier name is required.")
            return
        data = (name, self._phone.text().strip(), self._email.text().strip(),
                self._addr.toPlainText().strip(), self._gst.text().strip().upper())
        if self._id:
            db.execute(
                "UPDATE suppliers SET name=?,phone=?,email=?,address=?,gst_number=? WHERE id=?",
                (*data, self._id)
            )
        else:
            db.execute(
                "INSERT INTO suppliers (name,phone,email,address,gst_number) VALUES (?,?,?,?,?)",
                data
            )
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOMERS
# ══════════════════════════════════════════════════════════════════════════════

class CustomersScreen(BaseMasterScreen):
    SOFT_DELETE = True
    TITLE = "Customers"
    ITEM_NAME = "Customer"
    TABLE = "customers"
    HEADERS = ["ID", "Name", "Phone", "Email", "GST Number", "Actions"]

    def _fetch_rows(self):
        rows = db.fetchall(
            "SELECT id, name, phone, email, gst_number FROM customers WHERE is_active=1 ORDER BY name"
        )
        return [[r["id"], r["name"], r["phone"] or "", r["email"] or "", r["gst_number"] or ""]
                for r in rows]

    def _make_dialog(self, row_id):
        return _CustomerDialog(row_id, self)


class _CustomerDialog(_BaseDialog):
    def __init__(self, row_id, parent=None):
        super().__init__("Add Customer" if row_id is None else "Edit Customer", parent)
        self._id = row_id

        self._name = _make_field("Full customer name", 100)
        self._phone = _make_field("Phone number", 20)
        self._email = _make_field("Email address", 100)
        self._gst = _make_field("GST Number", 20)
        self._addr = _make_text_area("Full address")

        self._lay.addRow("Name *", self._name)
        self._lay.addRow("Phone", self._phone)
        self._lay.addRow("Email", self._email)
        self._lay.addRow("GST Number", self._gst)
        self._lay.addRow("Address", self._addr)
        self._add_buttons()

        if row_id:
            row = db.fetchone("SELECT * FROM customers WHERE id=?", (row_id,))
            if row:
                self._name.setText(row["name"])
                self._phone.setText(row["phone"] or "")
                self._email.setText(row["email"] or "")
                self._gst.setText(row["gst_number"] or "")
                self._addr.setText(row["address"] or "")

    def _on_save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "Required", "Customer name is required.")
            return
        data = (name, self._phone.text().strip(), self._email.text().strip(),
                self._addr.toPlainText().strip(), self._gst.text().strip().upper())
        if self._id:
            db.execute(
                "UPDATE customers SET name=?,phone=?,email=?,address=?,gst_number=? WHERE id=?",
                (*data, self._id)
            )
        else:
            db.execute(
                "INSERT INTO customers (name,phone,email,address,gst_number) VALUES (?,?,?,?,?)",
                data
            )
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
# MATERIAL TYPES
# ══════════════════════════════════════════════════════════════════════════════

class MaterialTypesScreen(BaseMasterScreen):
    TITLE = "Raw Material Types"
    ITEM_NAME = "Material Type"
    TABLE = "raw_material_types"
    HEADERS = ["ID", "Name", "Unit", "Low Stock Alert", "Description", "Actions"]

    def _fetch_rows(self):
        rows = db.fetchall(
            """SELECT rmt.id, rmt.name, u.name as unit, rmt.low_stock_threshold, rmt.description
               FROM raw_material_types rmt
               LEFT JOIN units u ON u.id = rmt.unit_id
               ORDER BY rmt.name"""
        )
        return [[r["id"], r["name"], r["unit"] or "", r["low_stock_threshold"], r["description"] or ""]
                for r in rows]

    def _make_dialog(self, row_id):
        return _MaterialTypeDialog(row_id, self)


class _MaterialTypeDialog(_BaseDialog):
    def __init__(self, row_id, parent=None):
        super().__init__("Add Material Type" if row_id is None else "Edit Material Type", parent)
        self._id = row_id

        self._name = _make_field("e.g. Cotton Fabric, Polyester Yarn...", 100)

        self._unit = QComboBox()
        self._unit.setFixedHeight(34)
        units = db.fetchall("SELECT id, name FROM units ORDER BY name")
        self._unit_ids = [u["id"] for u in units]
        for u in units:
            self._unit.addItem(u["name"])

        self._threshold = QDoubleSpinBox()
        self._threshold.setFixedHeight(34)
        self._threshold.setRange(0, 99999)
        self._threshold.setDecimals(2)
        self._threshold.setSuffix("  (unit quantity)")

        self._desc = _make_field("Optional description")

        self._lay.addRow("Name *", self._name)
        self._lay.addRow("Unit *", self._unit)
        self._lay.addRow("Low Stock Alert", self._threshold)
        self._lay.addRow("Description", self._desc)
        self._add_buttons()

        if row_id:
            row = db.fetchone("SELECT * FROM raw_material_types WHERE id=?", (row_id,))
            if row:
                self._name.setText(row["name"])
                if row["unit_id"] and row["unit_id"] in self._unit_ids:
                    self._unit.setCurrentIndex(self._unit_ids.index(row["unit_id"]))
                self._threshold.setValue(row["low_stock_threshold"] or 0)
                self._desc.setText(row["description"] or "")

    def _on_save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "Required", "Material type name is required.")
            return
        unit_id = self._unit_ids[self._unit.currentIndex()] if self._unit_ids else None
        data = (name, unit_id, self._threshold.value(), self._desc.text().strip())
        if self._id:
            db.execute(
                "UPDATE raw_material_types SET name=?,unit_id=?,low_stock_threshold=?,description=? WHERE id=?",
                (*data, self._id)
            )
        else:
            db.execute(
                "INSERT INTO raw_material_types (name,unit_id,low_stock_threshold,description) VALUES (?,?,?,?)",
                data
            )
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCTS
# ══════════════════════════════════════════════════════════════════════════════

class ProductsScreen(BaseMasterScreen):
    SOFT_DELETE = True
    TITLE = "Products"
    ITEM_NAME = "Product"
    TABLE = "products"
    HEADERS = ["ID", "Name", "Category", "Unit", "Sale Rate", "Actions"]

    def __init__(self, app_dir: str, parent=None):
        self._app_dir = app_dir
        super().__init__(parent)

    def _fetch_rows(self):
        rows = db.fetchall(
            """SELECT p.id, p.name, pc.name as cat, u.name as unit, p.sale_rate
               FROM products p
               LEFT JOIN product_categories pc ON pc.id=p.category_id
               LEFT JOIN units u ON u.id=p.unit_id
               WHERE p.is_active=1 ORDER BY p.name"""
        )
        return [[r["id"], r["name"], r["cat"] or "", r["unit"] or "",
                 f"₹ {r['sale_rate']:,.2f}"] for r in rows]

    def _make_dialog(self, row_id):
        return _ProductDialog(row_id, self._app_dir, self)


class _ProductDialog(_BaseDialog):
    def __init__(self, row_id, app_dir: str, parent=None):
        super().__init__("Add Product" if row_id is None else "Edit Product", parent)
        self._id = row_id
        self._app_dir = app_dir
        self._image_path = ""
        self.setMinimumWidth(520)

        self._name = _make_field("Product name", 100)

        self._category = QComboBox()
        self._category.setFixedHeight(34)
        cats = db.fetchall("SELECT id, name FROM product_categories ORDER BY name")
        self._cat_ids = [c["id"] for c in cats]
        for c in cats:
            self._category.addItem(c["name"])

        self._unit = QComboBox()
        self._unit.setFixedHeight(34)
        units = db.fetchall("SELECT id, name FROM units ORDER BY name")
        self._unit_ids = [u["id"] for u in units]
        for u in units:
            self._unit.addItem(u["name"])

        self._rate = QDoubleSpinBox()
        self._rate.setFixedHeight(34)
        self._rate.setRange(0, 9999999)
        self._rate.setDecimals(2)
        self._rate.setPrefix("₹ ")

        self._desc = _make_text_area("Optional description")

        img_row = QHBoxLayout()
        self._img_lbl = QLabel("No image")
        self._img_lbl.setFixedSize(80, 80)
        self._img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_lbl.setStyleSheet(
            "background:#2C2C2E; border:1px solid #48484A; border-radius:10px; color:#8E8E93;"
        )
        img_btn = QPushButton("Browse Image")
        img_btn.setFixedHeight(32)
        img_btn.clicked.connect(self._pick_image)
        img_row.addWidget(self._img_lbl)
        img_row.addWidget(img_btn)
        img_row.addStretch()
        img_widget = QWidget()
        img_widget.setLayout(img_row)

        self._lay.addRow("Name *", self._name)
        self._lay.addRow("Category *", self._category)
        self._lay.addRow("Unit *", self._unit)
        self._lay.addRow("Default Sale Rate", self._rate)
        self._lay.addRow("Description", self._desc)
        self._lay.addRow("Product Image", img_widget)
        self._add_buttons()

        if row_id:
            row = db.fetchone("SELECT * FROM products WHERE id=?", (row_id,))
            if row:
                self._name.setText(row["name"])
                if row["category_id"] and row["category_id"] in self._cat_ids:
                    self._category.setCurrentIndex(self._cat_ids.index(row["category_id"]))
                if row["unit_id"] and row["unit_id"] in self._unit_ids:
                    self._unit.setCurrentIndex(self._unit_ids.index(row["unit_id"]))
                self._rate.setValue(row["sale_rate"] or 0)
                self._desc.setText(row["description"] or "")
                if row["image_path"] and os.path.exists(row["image_path"]):
                    self._image_path = row["image_path"]
                    px = QPixmap(row["image_path"]).scaled(
                        80, 80, Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self._img_lbl.setPixmap(px)

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            import shutil
            dest_dir = os.path.join(self._app_dir, "images", "products")
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, os.path.basename(path))
            shutil.copy2(path, dest)
            self._image_path = dest
            px = QPixmap(dest).scaled(
                80, 80, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._img_lbl.setPixmap(px)

    def _on_save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "Required", "Product name is required.")
            return
        cat_id = self._cat_ids[self._category.currentIndex()] if self._cat_ids else None
        unit_id = self._unit_ids[self._unit.currentIndex()] if self._unit_ids else None
        data = (name, cat_id, unit_id, self._rate.value(),
                self._desc.toPlainText().strip(), self._image_path or None)
        if self._id:
            db.execute(
                "UPDATE products SET name=?,category_id=?,unit_id=?,sale_rate=?,description=?,image_path=? WHERE id=?",
                (*data, self._id)
            )
        else:
            db.execute(
                "INSERT INTO products (name,category_id,unit_id,sale_rate,description,image_path) VALUES (?,?,?,?,?,?)",
                data
            )
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
# UNITS
# ══════════════════════════════════════════════════════════════════════════════

class UnitsScreen(BaseMasterScreen):
    TITLE = "Units of Measurement"
    ITEM_NAME = "Unit"
    TABLE = "units"
    HEADERS = ["ID", "Name", "Abbreviation", "Actions"]

    def _fetch_rows(self):
        rows = db.fetchall("SELECT id, name, abbreviation FROM units ORDER BY name")
        return [[r["id"], r["name"], r["abbreviation"]] for r in rows]

    def _make_dialog(self, row_id):
        return _UnitDialog(row_id, self)


class _UnitDialog(_BaseDialog):
    def __init__(self, row_id, parent=None):
        super().__init__("Add Unit" if row_id is None else "Edit Unit", parent)
        self._id = row_id

        self._name = _make_field("e.g. Meters, Kilograms, Pieces", 50)
        self._abbr = _make_field("e.g. m, kg, pcs", 10)

        self._lay.addRow("Unit Name *", self._name)
        self._lay.addRow("Abbreviation *", self._abbr)
        self._add_buttons()

        if row_id:
            row = db.fetchone("SELECT * FROM units WHERE id=?", (row_id,))
            if row:
                self._name.setText(row["name"])
                self._abbr.setText(row["abbreviation"])

    def _on_save(self):
        name = self._name.text().strip()
        abbr = self._abbr.text().strip()
        if not name or not abbr:
            QMessageBox.warning(self, "Required", "Both name and abbreviation are required.")
            return
        try:
            if self._id:
                db.execute("UPDATE units SET name=?,abbreviation=? WHERE id=?", (name, abbr, self._id))
            else:
                db.execute("INSERT INTO units (name,abbreviation) VALUES (?,?)", (name, abbr))
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Unit name may already exist.\n{e}")
