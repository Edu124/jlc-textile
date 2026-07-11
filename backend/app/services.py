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


# ── Order Form -> Orders sync ─────────────────────────────────────────────────

def sync_order_from_bill(db: Session, bill, prepared):
    """Mirror a sales (order form) bill into the Orders section so dispatch
    progress can be tracked there. `prepared` is the (item, row_qty, amount, ...)
    tuples already computed by the sales router."""
    order = db.query(models.Order).get(bill.order_id) if bill.order_id else None
    if order is None:
        order = models.Order(order_number=next_order_number(db), customer_id=bill.customer_id,
                             delivery_date=bill.delivery_date,
                             notes=f"Order Form {bill.bill_number}")
        db.add(order); db.flush()
        bill.order_id = order.id
    else:
        order.customer_id = bill.customer_id
        order.delivery_date = bill.delivery_date
        order.notes = f"Order Form {bill.bill_number}"

    existing = db.query(models.OrderItem).filter_by(order_id=order.id).all()
    if existing and any((it.delivered_qty or 0) > 0 for it in existing):
        # Deliveries already recorded — don't touch items, just totals/header.
        order.total_amount = sum(it.amount or 0 for it in existing)
        return

    db.query(models.OrderItem).filter_by(order_id=order.id).delete()
    total = 0.0
    for it, row_qty, amount, rates, rep_mrp in prepared:
        rate = (amount / row_qty) if row_qty else 0
        _SZ = ["s", "m", "l", "xl", "xxl", "xxxl", "xxxxl", "mxxl"]
        db.add(models.OrderItem(order_id=order.id, product_id=it.product_id,
                                quantity=row_qty, rate=rate, amount=amount,
                                design_no=getattr(it, "design_no", "") or "",
                                **{f"qty_{k}": getattr(it, f"qty_{k}", 0) or 0 for k in _SZ}))
        total += amount
    order.total_amount = total


def get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(models.Setting).filter_by(key=key).first()
    return row.value if row else default


def set_setting(db: Session, key: str, value: str):
    row = db.query(models.Setting).filter_by(key=key).first()
    if row:
        row.value = value
    else:
        db.add(models.Setting(key=key, value=value))
