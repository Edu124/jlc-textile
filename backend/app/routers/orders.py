from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import require_user
from .. import models, services

router = APIRouter(prefix="/api/orders", tags=["orders"], dependencies=[Depends(require_user)])

STATUSES = ["Received", "In Production", "Ready", "Dispatched", "Delivered", "Cancelled"]


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


@router.get("")
def list_orders(db: Session = Depends(get_db)):
    out = []
    for o in db.query(models.Order).order_by(models.Order.id.desc()).all():
        cust = db.query(models.Customer).get(o.customer_id)
        count = db.query(models.OrderItem).filter_by(order_id=o.id).count()
        out.append({"id": o.id, "order_number": o.order_number,
                    "customer": cust.name if cust else "", "items": count,
                    "total_amount": o.total_amount, "status": o.status,
                    "delivery_date": o.delivery_date,
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
            "customer": cust.name if cust else "", "delivery_date": o.delivery_date,
            "total_amount": o.total_amount, "notes": o.notes,
            "items": [{"product": prods.get(it.product_id, ""), "quantity": it.quantity,
                       "rate": it.rate, "amount": it.amount} for it in items]}


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


@router.delete("/{order_id}")
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    o = db.query(models.Order).get(order_id)
    if o:
        o.status = "Cancelled"
        db.commit()
    return {"ok": True}
