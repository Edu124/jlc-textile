from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import require_user
from .. import models, services

router = APIRouter(prefix="/api/orders", tags=["orders"], dependencies=[Depends(require_user)])

STATUSES = ["Received", "In Production", "Ready", "Dispatched", "Partially Delivered", "Delivered", "Cancelled"]


class OrderItemIn(BaseModel):
    product_id: int
    quantity: float
    rate: float


class OrderIn(BaseModel):
    customer_id: int
    delivery_date: Optional[str] = None
    notes: Optional[str] = ""
    items: List[OrderItemIn]


@router.get("/next-number")
def next_number(db: Session = Depends(get_db)):
    return {"order_number": services.next_order_number(db)}


def _recompute_status(db: Session, order: models.Order):
    """Status follows delivery progress once any delivery is recorded.
    Cancelled is a manual terminal state and is never overwritten here."""
    if order.status == "Cancelled":
        return
    items = db.query(models.OrderItem).filter_by(order_id=order.id).all()
    total = sum(it.quantity or 0 for it in items)
    delivered = sum(it.delivered_qty or 0 for it in items)
    if total > 0 and delivered >= total:
        order.status = "Delivered"
    elif delivered > 0:
        order.status = "Partially Delivered"


@router.get("")
def list_orders(db: Session = Depends(get_db)):
    out = []
    for o in db.query(models.Order).order_by(models.Order.id.desc()).all():
        cust = db.query(models.Customer).get(o.customer_id)
        items = db.query(models.OrderItem).filter_by(order_id=o.id).all()
        total_qty = sum(it.quantity or 0 for it in items)
        delivered_qty = sum(it.delivered_qty or 0 for it in items)
        out.append({"id": o.id, "order_number": o.order_number,
                    "customer": cust.name if cust else "", "items": len(items),
                    "total_amount": o.total_amount, "status": o.status,
                    "delivery_date": o.delivery_date,
                    "total_qty": total_qty, "delivered_qty": delivered_qty,
                    "created_at": o.created_at.isoformat() if o.created_at else ""})
    return out


@router.get("/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    o = db.query(models.Order).get(order_id)
    if not o: raise HTTPException(404, "Not found")
    cust = db.query(models.Customer).get(o.customer_id)
    items = db.query(models.OrderItem).filter_by(order_id=order_id).all()
    prods = {p.id: p.name for p in db.query(models.Product).all()}
    return {"id": o.id, "order_number": o.order_number, "status": o.status,
            "customer_id": o.customer_id, "customer": cust.name if cust else "",
            "delivery_date": o.delivery_date,
            "total_amount": o.total_amount, "notes": o.notes,
            "items": [{"id": it.id, "product_id": it.product_id, "product": prods.get(it.product_id, ""),
                       "design_no": it.design_no or "",
                       "quantity": it.quantity, "rate": it.rate, "amount": it.amount,
                       "delivered_qty": it.delivered_qty or 0,
                       "has_sizes": any((getattr(it, f"qty_{k}") or 0) for k in SIZE_KEYS),
                       **{f"qty_{k}": getattr(it, f"qty_{k}") or 0 for k in SIZE_KEYS},
                       **{f"delivered_{k}": getattr(it, f"delivered_{k}") or 0 for k in SIZE_KEYS}} for it in items]}


@router.post("")
def create_order(body: OrderIn, db: Session = Depends(get_db)):
    if not body.items:
        raise HTTPException(400, "Add at least one product")
    total = sum(i.quantity * i.rate for i in body.items)
    o = models.Order(order_number=services.next_order_number(db),
                     customer_id=body.customer_id, total_amount=total,
                     notes=body.notes, delivery_date=body.delivery_date)
    db.add(o); db.flush()
    for it in body.items:
        db.add(models.OrderItem(order_id=o.id, product_id=it.product_id,
                                quantity=it.quantity, rate=it.rate,
                                amount=it.quantity * it.rate))
    db.commit()
    return {"id": o.id, "order_number": o.order_number}


@router.put("/{order_id}")
def update_order(order_id: int, body: OrderIn, db: Session = Depends(get_db)):
    o = db.query(models.Order).get(order_id)
    if not o: raise HTTPException(404, "Not found")
    if not body.items:
        raise HTTPException(400, "Add at least one product")

    o.customer_id = body.customer_id
    o.delivery_date = body.delivery_date
    o.notes = body.notes

    existing = {it.product_id: it for it in db.query(models.OrderItem).filter_by(order_id=order_id).all()}
    if any((it.delivered_qty or 0) > 0 for it in existing.values()):
        # Deliveries already recorded against this order — keep items (and
        # their delivered_qty) untouched, only header fields are editable.
        o.total_amount = sum(it.amount or 0 for it in existing.values())
        db.commit()
        return {"id": o.id, "order_number": o.order_number}

    db.query(models.OrderItem).filter_by(order_id=order_id).delete()
    total = sum(i.quantity * i.rate for i in body.items)
    o.total_amount = total
    for it in body.items:
        db.add(models.OrderItem(order_id=o.id, product_id=it.product_id,
                                quantity=it.quantity, rate=it.rate,
                                amount=it.quantity * it.rate))
    db.commit()
    return {"id": o.id, "order_number": o.order_number}


class StatusIn(BaseModel):
    status: str


@router.put("/{order_id}/status")
def update_status(order_id: int, body: StatusIn, db: Session = Depends(get_db)):
    if body.status not in STATUSES:
        raise HTTPException(400, "Invalid status")
    o = db.query(models.Order).get(order_id)
    if not o: raise HTTPException(404, "Not found")
    o.status = body.status
    db.commit()
    return {"ok": True}


SIZE_KEYS = ["s", "m", "l", "xl", "xxl", "xxxl", "xxxxl", "mxxl"]


class DeliverIn(BaseModel):
    delivered_qty: Optional[float] = None
    delivered_s: Optional[float] = None
    delivered_m: Optional[float] = None
    delivered_l: Optional[float] = None
    delivered_xl: Optional[float] = None
    delivered_xxl: Optional[float] = None
    delivered_mxxl: Optional[float] = None
    delivered_xxxl: Optional[float] = None
    delivered_xxxxl: Optional[float] = None


@router.put("/{order_id}/items/{item_id}/deliver")
def deliver_item(order_id: int, item_id: int, body: DeliverIn, db: Session = Depends(get_db)):
    o = db.query(models.Order).get(order_id)
    if not o: raise HTTPException(404, "Order not found")
    it = db.query(models.OrderItem).filter_by(id=item_id, order_id=order_id).first()
    if not it: raise HTTPException(404, "Item not found")

    has_sizes = any(getattr(it, f"qty_{k}", 0) for k in SIZE_KEYS)
    if has_sizes:
        for k in SIZE_KEYS:
            val = getattr(body, f"delivered_{k}")
            if val is None:
                continue
            ordered = getattr(it, f"qty_{k}") or 0
            if val < 0 or val > ordered:
                raise HTTPException(400, f"Delivered {k.upper()} must be between 0 and {ordered}")
            setattr(it, f"delivered_{k}", val)
        it.delivered_qty = sum(getattr(it, f"delivered_{k}") or 0 for k in SIZE_KEYS)
    else:
        if body.delivered_qty is None:
            raise HTTPException(400, "delivered_qty required")
        if body.delivered_qty < 0 or body.delivered_qty > (it.quantity or 0):
            raise HTTPException(400, f"Delivered qty must be between 0 and {it.quantity}")
        it.delivered_qty = body.delivered_qty

    _recompute_status(db, o)
    db.commit()
    return {"ok": True, "status": o.status}


SIZE_KEYS = ["s", "m", "l", "xl", "xxl", "xxxl", "xxxxl", "mxxl"]


class DeliverLogIn(BaseModel):
    delivery_date: Optional[str] = None
    reference_no: Optional[str] = ""
    s: float = 0
    m: float = 0
    l: float = 0
    xl: float = 0
    xxl: float = 0
    mxxl: float = 0
    xxxl: float = 0
    xxxxl: float = 0
    notes: Optional[str] = ""


def _received_for_design(db: Session, design: str):
    """Pieces of this design physically received (final-tailor deliveries and
    direct entries), per size + total."""
    rows = (db.query(models.TailorDelivery)
            .join(models.TailorJob, models.TailorDelivery.job_id == models.TailorJob.id)
            .join(models.RawMaterialType, models.TailorJob.material_type_id == models.RawMaterialType.id)
            .filter(models.TailorJob.tailor_type == "final",
                    models.RawMaterialType.name.ilike(design)).all())
    per_size = {k: 0.0 for k in SIZE_KEYS}
    total = 0.0
    for d in rows:
        for k in SIZE_KEYS:
            per_size[k] += getattr(d, f"size_{k}") or 0
        total += d.pieces or 0
    return per_size, total


def _delivered_for_design(db: Session, design: str):
    """Pieces of this design already handed to customers, across every order."""
    items = db.query(models.OrderItem).filter(models.OrderItem.design_no.ilike(design)).all()
    per_size = {k: sum(getattr(i, f"delivered_{k}") or 0 for i in items) for k in SIZE_KEYS}
    total = sum(i.delivered_qty or 0 for i in items)
    return per_size, total


@router.post("/{order_id}/items/{item_id}/deliver-log")
def add_delivery_log(order_id: int, item_id: int, body: DeliverLogIn, db: Session = Depends(get_db)):
    """Record a dated delivery of some pieces against one order line. The values
    are the amount delivered NOW (a delta); running totals live on the item."""
    o = db.query(models.Order).get(order_id)
    if not o: raise HTTPException(404, "Order not found")
    it = db.query(models.OrderItem).filter_by(id=item_id, order_id=order_id).first()
    if not it: raise HTTPException(404, "Item not found")

    deltas = {k: max(0.0, getattr(body, k) or 0) for k in SIZE_KEYS}
    total = sum(deltas.values())
    if total <= 0:
        raise HTTPException(400, "Enter pieces delivered")
    # Validate against remaining per size (or, for no-size items, the total).
    has_sizes = any((getattr(it, f"qty_{k}") or 0) for k in SIZE_KEYS)

    # You can only hand over pieces that have physically arrived — check the
    # design's received stock (tailor deliveries + direct entries) minus what
    # was already delivered on any order.
    design = (it.design_no or "").strip()
    if design:
        recv, recv_total = _received_for_design(db, design)
        done, done_total = _delivered_for_design(db, design)
        # receipts logged without a size split form a shared untagged pool
        untagged = max(0.0, recv_total - sum(recv.values()))
        if has_sizes:
            for k in SIZE_KEYS:
                if deltas[k] <= 0:
                    continue
                left = recv[k] + untagged - done[k]
                if deltas[k] > left + 1e-9:
                    raise HTTPException(400,
                        f"{k.upper()}: only {max(0, left):.0f} pcs of {design} in hand — "
                        "that size hasn't arrived in Finished Goods yet")
        else:
            left = recv_total - done_total
            if total > left + 1e-9:
                raise HTTPException(400,
                    f"Only {max(0, left):.0f} pcs of {design} in hand — "
                    "stock hasn't arrived in Finished Goods yet")
    if has_sizes:
        for k in SIZE_KEYS:
            ordered = getattr(it, f"qty_{k}") or 0
            already = getattr(it, f"delivered_{k}") or 0
            if already + deltas[k] > ordered:
                raise HTTPException(400, f"{k.upper()}: only {ordered - already:.0f} left to deliver")
        for k in SIZE_KEYS:
            setattr(it, f"delivered_{k}", (getattr(it, f"delivered_{k}") or 0) + deltas[k])
        it.delivered_qty = sum(getattr(it, f"delivered_{k}") or 0 for k in SIZE_KEYS)
    else:
        if (it.delivered_qty or 0) + total > (it.quantity or 0):
            raise HTTPException(400, f"Only {(it.quantity or 0) - (it.delivered_qty or 0):.0f} left to deliver")
        it.delivered_qty = (it.delivered_qty or 0) + total

    db.add(models.OrderDelivery(
        order_id=order_id, order_item_id=item_id, design_no=it.design_no,
        delivery_date=body.delivery_date or date.today().isoformat(), pieces=total,
        reference_no=(body.reference_no or "").strip(),
        notes=(body.notes or "").strip(),
        **{f"size_{k}": deltas[k] for k in SIZE_KEYS}))
    _recompute_status(db, o)
    db.commit()
    return {"ok": True, "status": o.status}


@router.get("/{order_id}/deliveries")
def list_order_deliveries(order_id: int, db: Session = Depends(get_db)):
    rows = (db.query(models.OrderDelivery).filter_by(order_id=order_id)
            .order_by(models.OrderDelivery.id.desc()).all())
    return [{"id": d.id, "order_item_id": d.order_item_id, "design_no": d.design_no,
             "date": d.delivery_date, "pieces": d.pieces or 0, "notes": d.notes or "",
             "reference_no": d.reference_no or "",
             "sizes": {k: getattr(d, f"size_{k}") or 0 for k in SIZE_KEYS}}
            for d in rows]


@router.delete("/{order_id}/deliveries/{delivery_id}")
def delete_order_delivery(order_id: int, delivery_id: int, db: Session = Depends(get_db)):
    """Undo a delivery log entry — subtracts its pieces back off the running totals."""
    d = db.query(models.OrderDelivery).filter_by(id=delivery_id, order_id=order_id).first()
    if not d:
        return {"ok": True}
    it = db.query(models.OrderItem).get(d.order_item_id) if d.order_item_id else None
    if it:
        for k in SIZE_KEYS:
            cur = getattr(it, f"delivered_{k}") or 0
            setattr(it, f"delivered_{k}", max(0.0, cur - (getattr(d, f"size_{k}") or 0)))
        has_sizes = any((getattr(it, f"qty_{k}") or 0) for k in SIZE_KEYS)
        if has_sizes:
            it.delivered_qty = sum(getattr(it, f"delivered_{k}") or 0 for k in SIZE_KEYS)
        else:
            it.delivered_qty = max(0.0, (it.delivered_qty or 0) - (d.pieces or 0))
    db.delete(d)
    o = db.query(models.Order).get(order_id)
    if o:
        _recompute_status(db, o)
    db.commit()
    return {"ok": True}


@router.delete("/{order_id}")
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    o = db.query(models.Order).get(order_id)
    if o:
        o.status = "Cancelled"
        db.commit()
    return {"ok": True}
