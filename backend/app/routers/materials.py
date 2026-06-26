from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import require_user
from .. import models, services

router = APIRouter(prefix="/api/raw-materials", tags=["raw-materials"],
                   dependencies=[Depends(require_user)])


@router.get("")
def list_stock(db: Session = Depends(get_db)):
    out = []
    for m in db.query(models.RawMaterialType).order_by(models.RawMaterialType.name).all():
        stock = db.query(models.RawMaterialStock).filter_by(material_type_id=m.id).first()
        unit = db.query(models.Unit).get(m.unit_id) if m.unit_id else None
        qty = stock.quantity if stock else 0
        rate = stock.avg_rate if stock else 0
        thr = m.low_stock_threshold or 0
        out.append({
            "id": m.id, "name": m.name, "unit": unit.abbreviation if unit else "",
            "quantity": qty, "avg_rate": rate, "value": qty * rate,
            "low_stock_threshold": thr,
            "status": "Low Stock" if (thr > 0 and qty <= thr) else "OK",
        })
    return out


class StockEntryIn(BaseModel):
    material_type_id: int
    quantity: float
    rate: float
    note: Optional[str] = ""


@router.post("/stock-entry")
def add_stock(body: StockEntryIn, db: Session = Depends(get_db)):
    if body.quantity <= 0:
        raise HTTPException(400, "Quantity must be greater than 0")
    services.adjust_raw_stock(db, body.material_type_id, body.quantity, body.rate)
    db.add(models.RawMaterialTransaction(
        material_type_id=body.material_type_id, transaction_type="manual_addition",
        quantity=body.quantity, rate=body.rate, reference_type="manual", notes=body.note))
    db.commit()
    return {"ok": True}


class AdjustIn(BaseModel):
    new_quantity: float
    reason: str


@router.post("/{material_type_id}/adjust")
def adjust(material_type_id: int, body: AdjustIn, db: Session = Depends(get_db)):
    if not body.reason.strip():
        raise HTTPException(400, "Reason is required")
    stock = db.query(models.RawMaterialStock).filter_by(material_type_id=material_type_id).first()
    current = stock.quantity if stock else 0
    delta = body.new_quantity - current
    if stock:
        stock.quantity = body.new_quantity
    else:
        db.add(models.RawMaterialStock(material_type_id=material_type_id,
                                       quantity=max(0, body.new_quantity)))
    db.add(models.RawMaterialTransaction(
        material_type_id=material_type_id, transaction_type="adjustment",
        quantity=delta, reference_type="adjustment", notes=body.reason))
    db.commit()
    return {"ok": True}


@router.get("/transactions")
def transactions(db: Session = Depends(get_db), limit: int = 30):
    rows = (db.query(models.RawMaterialTransaction)
            .order_by(models.RawMaterialTransaction.id.desc()).limit(limit).all())
    out = []
    for t in rows:
        mat = db.query(models.RawMaterialType).get(t.material_type_id)
        out.append({"date": t.created_at.isoformat() if t.created_at else "",
                    "material": mat.name if mat else "",
                    "type": (t.transaction_type or "").replace("_", " ").title(),
                    "quantity": t.quantity, "rate": t.rate,
                    "reference": t.reference_type or ""})
    return out
