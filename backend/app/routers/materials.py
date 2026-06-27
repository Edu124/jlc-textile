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


REASONS = ["Given to tailor", "Given to customer", "Other"]


class AdjustIn(BaseModel):
    new_quantity: float
    reason_type: str = "Other"
    recipient_name: Optional[str] = ""


@router.post("/{material_type_id}/adjust")
def adjust(material_type_id: int, body: AdjustIn, db: Session = Depends(get_db)):
    if body.reason_type not in REASONS:
        raise HTTPException(400, "Invalid reason")
    stock = db.query(models.RawMaterialStock).filter_by(material_type_id=material_type_id).first()
    current = stock.quantity if stock else 0
    delta = body.new_quantity - current          # negative when stock is reduced
    given = max(0.0, current - body.new_quantity)  # amount sent out

    if stock:
        stock.quantity = body.new_quantity
    else:
        db.add(models.RawMaterialStock(material_type_id=material_type_id,
                                       quantity=max(0, body.new_quantity)))

    db.add(models.RawMaterialTransaction(
        material_type_id=material_type_id, transaction_type="adjustment",
        quantity=delta, reference_type="adjustment",
        recipient_type=body.reason_type, recipient_name=(body.recipient_name or "").strip()))

    # "Given to tailor" creates a job-work record in Production.
    if body.reason_type == "Given to tailor" and given > 0:
        db.add(models.TailorJob(
            material_type_id=material_type_id,
            tailor_name=(body.recipient_name or "").strip() or "Tailor",
            qty_given=given, qty_returned=0))

    db.commit()
    return {"ok": True}


@router.get("/{material_type_id}/distributions")
def distributions(material_type_id: int, db: Session = Depends(get_db)):
    """Who this material was given to, and how much (for the clickable popup)."""
    rows = (db.query(models.RawMaterialTransaction)
            .filter(models.RawMaterialTransaction.material_type_id == material_type_id,
                    models.RawMaterialTransaction.recipient_type.isnot(None),
                    models.RawMaterialTransaction.quantity < 0)
            .order_by(models.RawMaterialTransaction.id.desc()).all())
    mat = db.query(models.RawMaterialType).get(material_type_id)
    return {
        "material": mat.name if mat else "",
        "items": [{"recipient_type": t.recipient_type, "name": t.recipient_name or "—",
                   "quantity": abs(t.quantity or 0),
                   "date": t.created_at.isoformat()[:16] if t.created_at else ""}
                  for t in rows],
    }


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
