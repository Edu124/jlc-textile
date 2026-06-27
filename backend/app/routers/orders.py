from typing import Optional, List
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
                       "quantity": it.quantity, "rate": it.rate, "amount": it.amount,
                       "delivered_qty": it.delivered_qty or 0,
                       "has_sizes": bool((it.qty_m or 0) + (it.qty_l or 0) + (it.qty_xl or 0) + (it.qty_xxl or 0) + (it.qty_mxxl or 0)),
                       "qty_m": it.qty_m or 0, "qty_l": it.qty_l or 0, "qty_xl": it.qty_xl or 0,
                       "qty_xxl": it.qty_xxl or 0, "qty_mxxl": it.qty_mxxl or 0,
                       "delivered_m": it.delivered_m or 0, "delivered_l": it.delivered_l or 0,
                       "delivered_xl": it.delivered_xl or 0, "delivered_xxl": it.delivered_xxl or 0,
                       "delivered_mxxl": it.delivered_mxxl or 0} for it in items]}


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


SIZE_KEYS = ["m", "l", "xl", "xxl", "mxxl"]


class DeliverIn(BaseModel):
    delivered_qty: Optional[float] = None
    delivered_m: Optional[float] = None
    delivered_l: Optional[float] = None
    delivered_xl: Optional[float] = None
    delivered_xxl: Optional[float] = None
    delivered_mxxl: Optional[float] = None


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


@router.delete("/{order_id}")
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    o = db.query(models.Order).get(order_id)
    if o:
        o.status = "Cancelled"
        db.commit()
    return {"ok": True}
