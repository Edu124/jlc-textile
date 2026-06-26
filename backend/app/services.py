"""Shared business logic: auto-numbering and stock adjustments."""
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from . import models


# ── Auto-numbering (PREFIX/yymm/0001) ─────────────────────────────────────────

def _next_number(db: Session, model, col, prefix: str) -> str:
    period = datetime.now().strftime("%y%m")
    like = f"{prefix}/{period}/%"
    rows = db.query(getattr(model, col)).filter(getattr(model, col).like(like)).all()
    seq = 1
    for (val,) in rows:
        try:
            seq = max(seq, int(val.split("/")[-1]) + 1)
        except (ValueError, AttributeError, IndexError):
            continue
    return f"{prefix}/{period}/{seq:04d}"


def next_purchase_number(db: Session) -> str:
    return _next_number(db, models.PurchaseBill, "bill_number", "PUR")


def next_sales_number(db: Session) -> str:
    return _next_number(db, models.SalesBill, "bill_number", "SAL")


def next_order_number(db: Session) -> str:
    return _next_number(db, models.Order, "order_number", "ORD")


def next_batch_number(db: Session) -> str:
    return _next_number(db, models.ProductionBatch, "batch_number", "BATCH")


# ── Stock adjustments ─────────────────────────────────────────────────────────

def adjust_raw_stock(db: Session, material_type_id: int, qty_delta: float, rate: float = 0):
    row = db.query(models.RawMaterialStock).filter_by(material_type_id=material_type_id).first()
    if row:
        old_qty, old_rate = row.quantity or 0, row.avg_rate or 0
        if qty_delta > 0 and rate > 0:
            new_qty = old_qty + qty_delta
            row.avg_rate = ((old_qty * old_rate) + (qty_delta * rate)) / new_qty if new_qty else rate
            row.quantity = new_qty
        else:
            row.quantity = max(0, old_qty + qty_delta)
        row.last_updated = datetime.utcnow()
    else:
        db.add(models.RawMaterialStock(
            material_type_id=material_type_id,
            quantity=max(0, qty_delta), avg_rate=rate))


def adjust_finished_stock(db: Session, product_id: int, qty_delta: float):
    row = db.query(models.FinishedGoodsStock).filter_by(product_id=product_id).first()
    if row:
        row.quantity = max(0, (row.quantity or 0) + qty_delta)
        row.last_updated = datetime.utcnow()
    else:
        db.add(models.FinishedGoodsStock(product_id=product_id, quantity=max(0, qty_delta)))


def get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(models.Setting).filter_by(key=key).first()
    return row.value if row else default


def set_setting(db: Session, key: str, value: str):
    row = db.query(models.Setting).filter_by(key=key).first()
    if row:
        row.value = value
    else:
        db.add(models.Setting(key=key, value=value))
