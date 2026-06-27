from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, ForeignKey, DateTime, func
)
from .db import Base


def _now():
    return datetime.utcnow()


class Setting(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True)
    value = Column(Text)


class Unit(Base):
    __tablename__ = "units"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    abbreviation = Column(String, nullable=False)


class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String)
    email = Column(String)
    address = Column(Text)
    gst_number = Column(String)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=_now)


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String)
    email = Column(String)
    address = Column(Text)
    gst_number = Column(String)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=_now)


class RawMaterialType(Base):
    __tablename__ = "raw_material_types"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    unit_id = Column(Integer, ForeignKey("units.id"))
    low_stock_threshold = Column(Float, default=0)
    description = Column(Text)
    created_at = Column(DateTime, default=_now)


class RawMaterialStock(Base):
    __tablename__ = "raw_material_stock"
    id = Column(Integer, primary_key=True)
    material_type_id = Column(Integer, ForeignKey("raw_material_types.id"), unique=True)
    quantity = Column(Float, default=0)
    avg_rate = Column(Float, default=0)
    last_updated = Column(DateTime, default=_now)


class RawMaterialTransaction(Base):
    __tablename__ = "raw_material_transactions"
    id = Column(Integer, primary_key=True)
    material_type_id = Column(Integer, ForeignKey("raw_material_types.id"))
    transaction_type = Column(String)
    quantity = Column(Float)
    rate = Column(Float)
    reference_id = Column(Integer)
    reference_type = Column(String)
    recipient_type = Column(String)   # Given to tailor | Given to customer | Other
    recipient_name = Column(String)   # tailor/customer/person name
    notes = Column(Text)
    created_at = Column(DateTime, default=_now)


class TailorJob(Base):
    """Raw material given to a tailor for stitching (job work).
    held = qty_given - qty_returned. Returned quantity flows into the linked
    Product as 'pending_qty' (awaiting a rate) before it becomes finished
    goods stock."""
    __tablename__ = "tailor_jobs"
    id = Column(Integer, primary_key=True)
    material_type_id = Column(Integer, ForeignKey("raw_material_types.id"))
    tailor_name = Column(String)
    qty_given = Column(Float, default=0)
    qty_returned = Column(Float, default=0)
    product_id = Column(Integer, ForeignKey("products.id"))
    created_at = Column(DateTime, default=_now)


class ProductCategory(Base):
    __tablename__ = "product_categories"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("product_categories.id"))
    unit_id = Column(Integer, ForeignKey("units.id"))
    sale_rate = Column(Float, default=0)        # base rate (fallback for any size)
    # Per-size rates (a 0 here falls back to sale_rate for that size).
    rate_m = Column(Float, default=0)
    rate_l = Column(Float, default=0)
    rate_xl = Column(Float, default=0)
    rate_xxl = Column(Float, default=0)
    rate_mxxl = Column(Float, default=0)
    description = Column(Text)
    image_path = Column(String)
    # Quantity returned from job-work that is awaiting a rate before it
    # becomes finished-goods stock (see TailorJob).
    pending_qty = Column(Float, default=0)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=_now)


class ProductBOM(Base):
    __tablename__ = "product_bom"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    material_type_id = Column(Integer, ForeignKey("raw_material_types.id"))
    quantity_required = Column(Float)
    notes = Column(Text)


class ProductionBatch(Base):
    __tablename__ = "production_batches"
    id = Column(Integer, primary_key=True)
    batch_number = Column(String, unique=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float)
    order_id = Column(Integer)
    current_stage = Column(String, default="Cutting")
    notes = Column(Text)
    started_at = Column(DateTime, default=_now)
    completed_at = Column(DateTime)


class BatchStageHistory(Base):
    __tablename__ = "batch_stage_history"
    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("production_batches.id"))
    stage = Column(String)
    notes = Column(Text)
    changed_at = Column(DateTime, default=_now)


class FinishedGoodsStock(Base):
    __tablename__ = "finished_goods_stock"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), unique=True)
    quantity = Column(Float, default=0)
    last_updated = Column(DateTime, default=_now)


class FinishedGoodsTransaction(Base):
    __tablename__ = "finished_goods_transactions"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    transaction_type = Column(String)
    quantity = Column(Float)
    reference_id = Column(Integer)
    reference_type = Column(String)
    created_at = Column(DateTime, default=_now)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    order_number = Column(String, unique=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    status = Column(String, default="Received")
    total_amount = Column(Float, default=0)
    notes = Column(Text)
    delivery_date = Column(String)
    created_at = Column(DateTime, default=_now)


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float)
    rate = Column(Float)
    amount = Column(Float)
    delivered_qty = Column(Float, default=0)
    # Size breakdown (only populated when this item came from a size-grid
    # Order Form; manually-added Order items leave these at 0).
    qty_m = Column(Float, default=0)
    qty_l = Column(Float, default=0)
    qty_xl = Column(Float, default=0)
    qty_xxl = Column(Float, default=0)
    qty_mxxl = Column(Float, default=0)
    delivered_m = Column(Float, default=0)
    delivered_l = Column(Float, default=0)
    delivered_xl = Column(Float, default=0)
    delivered_xxl = Column(Float, default=0)
    delivered_mxxl = Column(Float, default=0)


class PurchaseBill(Base):
    __tablename__ = "purchase_bills"
    id = Column(Integer, primary_key=True)
    bill_number = Column(String, unique=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    bill_date = Column(String)
    subtotal = Column(Float, default=0)
    gst_type = Column(String, default="none")
    gst_percent = Column(Float, default=0)
    gst_amount = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    notes = Column(Text)
    pdf_path = Column(String)
    created_at = Column(DateTime, default=_now)


class PurchaseBillItem(Base):
    __tablename__ = "purchase_bill_items"
    id = Column(Integer, primary_key=True)
    bill_id = Column(Integer, ForeignKey("purchase_bills.id"))
    material_type_id = Column(Integer, ForeignKey("raw_material_types.id"))
    quantity = Column(Float)
    unit_id = Column(Integer, ForeignKey("units.id"))
    rate = Column(Float)
    amount = Column(Float)


class SalesBill(Base):
    __tablename__ = "sales_bills"
    id = Column(Integer, primary_key=True)
    bill_number = Column(String, unique=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    order_id = Column(Integer)
    bill_date = Column(String)
    delivery_date = Column(String)
    transport = Column(String)
    agent = Column(String)
    subtotal = Column(Float, default=0)
    gst_type = Column(String, default="none")
    gst_percent = Column(Float, default=0)
    gst_amount = Column(Float, default=0)
    total_qty = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    notes = Column(Text)
    pdf_path = Column(String)
    created_at = Column(DateTime, default=_now)


class SalesBillItem(Base):
    __tablename__ = "sales_bill_items"
    id = Column(Integer, primary_key=True)
    bill_id = Column(Integer, ForeignKey("sales_bills.id"))
    design_no = Column(String)
    product_id = Column(Integer, ForeignKey("products.id"))
    qty_m = Column(Float, default=0)
    qty_l = Column(Float, default=0)
    qty_xl = Column(Float, default=0)
    qty_xxl = Column(Float, default=0)
    qty_mxxl = Column(Float, default=0)
    # Per-size rate snapshot used on this bill (so totals stay correct even
    # if the product's rates change later).
    rate_m = Column(Float, default=0)
    rate_l = Column(Float, default=0)
    rate_xl = Column(Float, default=0)
    rate_xxl = Column(Float, default=0)
    rate_mxxl = Column(Float, default=0)
    row_qty = Column(Float, default=0)
    mrp = Column(Float, default=0)       # representative rate (kept for compatibility)
    amount = Column(Float, default=0)
    unit_id = Column(Integer)
    quantity = Column(Float)
    rate = Column(Float)


class AIDesign(Base):
    __tablename__ = "ai_designs"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    prompt = Column(Text)
    style = Column(String)
    source_image_path = Column(String)
    result_image_path = Column(String)
    created_at = Column(DateTime, default=_now)
