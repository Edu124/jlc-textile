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
            "id": m.id, "name": m.name, "design_no": m.design_no or "",
            "unit": unit.abbreviation if unit else "",
            "quantity": qty, "avg_rate": rate, "value": qty * rate,
            "description": m.description or "",
            "low_stock_threshold": thr,
            "status": "Low Stock" if (thr > 0 and qty <= thr) else "OK",
        })
    return out


class StockEntryIn(BaseModel):
    name: str                       # design name
    design_no: Optional[str] = ""   # design number
    unit_id: Optional[int] = None   # metres / pieces / etc.
    quantity: float
    rate: float = 0
    description: Optional[str] = ""
    note: Optional[str] = ""


def _get_or_create_type(db: Session, name: str, unit_id, design_no="", description=""):
    """Stock is added by free-text design name now (no separate material-type
    master). Same name reuses one stock line; new names create one."""
    name = name.strip()
    existing = (db.query(models.RawMaterialType)
                .filter(models.RawMaterialType.name.ilike(name)).first())
    if existing:
        if unit_id and not existing.unit_id:
            existing.unit_id = unit_id
        if (design_no or "").strip():
            existing.design_no = design_no.strip()
        if (description or "").strip():
            existing.description = description.strip()
        return existing
    m = models.RawMaterialType(name=name, unit_id=unit_id,
                               design_no=(design_no or "").strip(),
                               description=(description or "").strip())
    db.add(m); db.flush()
    return m


@router.post("/stock-entry")
def add_stock(body: StockEntryIn, db: Session = Depends(get_db)):
    if not body.name.strip():
        raise HTTPException(400, "Enter the design name")
    if body.quantity <= 0:
        raise HTTPException(400, "Quantity must be greater than 0")
    m = _get_or_create_type(db, body.name, body.unit_id, body.design_no, body.description)
    services.adjust_raw_stock(db, m.id, body.quantity, body.rate)
    db.add(models.RawMaterialTransaction(
        material_type_id=m.id, transaction_type="manual_addition",
        quantity=body.quantity, rate=body.rate, reference_type="manual", notes=body.note))
    db.commit()
    return {"ok": True, "material_type_id": m.id}


REASONS = ["Given to tailor", "Given to customer", "Other"]
TAILOR_TYPES = ["work", "final"]


class SizeBreakdown(BaseModel):
    m: float = 0
    l: float = 0
    xl: float = 0
    xxl: float = 0
    mxxl: float = 0


class AdjustIn(BaseModel):
    new_quantity: float
    reason_type: str = "Other"
    recipient_name: Optional[str] = ""
    tailor_type: str = "work"        # only used when reason_type == "Given to tailor"
    sizes: Optional[SizeBreakdown] = None   # optional per-size piece breakdown


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

    # "Given to tailor" creates a job-work record in Production. The tailor
    # type (work | final) decides which stage of the pipeline it enters.
    if body.reason_type == "Given to tailor" and given > 0:
        ttype = body.tailor_type if body.tailor_type in TAILOR_TYPES else "work"
        s = body.sizes
        size_total = (s.m + s.l + s.xl + s.xxl + s.mxxl) if s else 0
        # For work jobs the optional size breakdown also seeds the piece target.
        target = size_total if size_total > 0 else (given if ttype == "final" else 0)
        db.add(models.TailorJob(
            material_type_id=material_type_id,
            tailor_name=(body.recipient_name or "").strip() or "Tailor",
            tailor_type=ttype, qty_given=given, qty_returned=0, target_pieces=target,
            size_m=s.m if s else 0, size_l=s.l if s else 0, size_xl=s.xl if s else 0,
            size_xxl=s.xxl if s else 0, size_mxxl=s.mxxl if s else 0))

    db.commit()
    return {"ok": True}


@router.delete("/{material_type_id}")
def delete_material(material_type_id: int, db: Session = Depends(get_db)):
    """Remove a design completely: stock, history and its tailor jobs.
    Postgres enforces the foreign keys, so dependents must go first."""
    job_ids = [j.id for j in db.query(models.TailorJob)
               .filter_by(material_type_id=material_type_id).all()]
    if job_ids:
        db.query(models.TailorDelivery).filter(
            models.TailorDelivery.job_id.in_(job_ids)).delete(synchronize_session=False)
        db.query(models.TailorJob).filter(
            models.TailorJob.parent_job_id.in_(job_ids)).update(
            {"parent_job_id": None}, synchronize_session=False)
        db.query(models.TailorJob).filter(
            models.TailorJob.id.in_(job_ids)).delete(synchronize_session=False)
    db.query(models.ProductBOM).filter_by(material_type_id=material_type_id).delete()
    db.query(models.RawMaterialStock).filter_by(material_type_id=material_type_id).delete()
    db.query(models.RawMaterialTransaction).filter_by(material_type_id=material_type_id).delete()
    m = db.query(models.RawMaterialType).get(material_type_id)
    if m:
        db.delete(m)
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
