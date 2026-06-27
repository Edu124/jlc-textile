from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import require_user
from .. import models, services

router = APIRouter(prefix="/api/finished-goods", tags=["finished-goods"],
                   dependencies=[Depends(require_user)])


@router.get("")
def list_stock(db: Session = Depends(get_db)):
    """Only priced products with actual finished-goods stock show here.
    Job-work returns awaiting a rate live under Products until priced."""
    out = []
    for p in db.query(models.Product).filter(models.Product.is_active == 1)\
            .order_by(models.Product.name).all():
        stock = db.query(models.FinishedGoodsStock).filter_by(product_id=p.id).first()
        qty = stock.quantity if stock else 0
        if qty <= 0:
            continue
        cat = db.query(models.ProductCategory).get(p.category_id) if p.category_id else None
        unit = db.query(models.Unit).get(p.unit_id) if p.unit_id else None
        out.append({"id": p.id, "product_id": p.id, "name": p.name,
                    "category": cat.name if cat else "",
                    "unit": unit.abbreviation if unit else "", "quantity": qty,
                    "sale_rate": p.sale_rate, "value": qty * (p.sale_rate or 0)})
    return out


class AdjustIn(BaseModel):
    product_id: int
    new_quantity: float
    reason: str = "Manual Adjustment"


@router.post("/adjust")
def adjust(body: AdjustIn, db: Session = Depends(get_db)):
    stock = db.query(models.FinishedGoodsStock).filter_by(product_id=body.product_id).first()
    current = stock.quantity if stock else 0
    delta = body.new_quantity - current
    services.adjust_finished_stock(db, body.product_id, delta)
    db.add(models.FinishedGoodsTransaction(
        product_id=body.product_id, transaction_type="adjustment", quantity=delta,
        reference_type=body.reason))
    db.commit()
    return {"ok": True}


@router.get("/transactions")
def transactions(db: Session = Depends(get_db), limit: int = 30):
    rows = (db.query(models.FinishedGoodsTransaction)
            .order_by(models.FinishedGoodsTransaction.id.desc()).limit(limit).all())
    prods = {p.id: p.name for p in db.query(models.Product).all()}
    return [{"date": t.created_at.isoformat() if t.created_at else "",
             "product": prods.get(t.product_id, ""),
             "type": (t.transaction_type or "").title(), "quantity": t.quantity}
            for t in rows]
