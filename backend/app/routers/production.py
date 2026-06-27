from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import require_user
from .. import models, services

router = APIRouter(prefix="/api/production", tags=["production"],
                   dependencies=[Depends(require_user)])

STAGES = ["Cutting", "Stitching", "Dyeing", "Finishing", "QC", "Completed"]


@router.get("/next-number")
def next_number(db: Session = Depends(get_db)):
    return {"batch_number": services.next_batch_number(db)}


@router.get("")
def list_batches(db: Session = Depends(get_db)):
    out = []
    prods = {p.id: p for p in db.query(models.Product).all()}
    for b in db.query(models.ProductionBatch).order_by(models.ProductionBatch.id.desc()).all():
        p = prods.get(b.product_id)
        out.append({"id": b.id, "batch_number": b.batch_number,
                    "product": p.name if p else "", "quantity": b.quantity,
                    "current_stage": b.current_stage, "order_id": b.order_id,
                    "started_at": b.started_at.isoformat() if b.started_at else "",
                    "completed_at": b.completed_at.isoformat() if b.completed_at else None})
    return out


@router.get("/{batch_id:int}")
def get_batch(batch_id: int, db: Session = Depends(get_db)):
    b = db.query(models.ProductionBatch).get(batch_id)
    if not b: raise HTTPException(404, "Not found")
    p = db.query(models.Product).get(b.product_id)
    hist = db.query(models.BatchStageHistory).filter_by(batch_id=batch_id)\
        .order_by(models.BatchStageHistory.id).all()
    return {"id": b.id, "batch_number": b.batch_number, "product": p.name if p else "",
            "quantity": b.quantity, "current_stage": b.current_stage,
            "history": [{"stage": h.stage, "notes": h.notes,
                         "changed_at": h.changed_at.isoformat() if h.changed_at else ""}
                        for h in hist]}


class BatchIn(BaseModel):
    product_id: int
    quantity: float
    order_id: Optional[int] = None
    notes: Optional[str] = ""


@router.post("")
def create_batch(body: BatchIn, db: Session = Depends(get_db)):
    # Check BOM stock availability
    bom = db.query(models.ProductBOM).filter_by(product_id=body.product_id).all()
    for item in bom:
        needed = (item.quantity_required or 0) * body.quantity
        stock = db.query(models.RawMaterialStock).filter_by(
            material_type_id=item.material_type_id).first()
        avail = stock.quantity if stock else 0
        if avail < needed:
            mat = db.query(models.RawMaterialType).get(item.material_type_id)
            raise HTTPException(400, f"Not enough {mat.name if mat else 'material'} "
                                     f"(need {needed:.2f}, have {avail:.2f})")

    batch = models.ProductionBatch(
        batch_number=services.next_batch_number(db), product_id=body.product_id,
        quantity=body.quantity, order_id=body.order_id, current_stage="Cutting",
        notes=body.notes)
    db.add(batch); db.flush()
    db.add(models.BatchStageHistory(batch_id=batch.id, stage="Cutting", notes="Batch started"))

    for item in bom:
        consumed = (item.quantity_required or 0) * body.quantity
        services.adjust_raw_stock(db, item.material_type_id, -consumed)
        db.add(models.RawMaterialTransaction(
            material_type_id=item.material_type_id, transaction_type="consumption",
            quantity=-consumed, reference_id=batch.id, reference_type="production_batch"))
    db.commit()
    return {"id": batch.id, "batch_number": batch.batch_number}


class AdvanceIn(BaseModel):
    notes: Optional[str] = ""


@router.post("/{batch_id}/advance")
def advance_stage(batch_id: int, body: AdvanceIn, db: Session = Depends(get_db)):
    b = db.query(models.ProductionBatch).get(batch_id)
    if not b: raise HTTPException(404, "Not found")
    if b.current_stage not in STAGES or b.current_stage == "Completed":
        raise HTTPException(400, "Batch already completed")
    nxt = STAGES[STAGES.index(b.current_stage) + 1]
    b.current_stage = nxt
    db.add(models.BatchStageHistory(batch_id=batch_id, stage=nxt, notes=body.notes))
    if nxt == "Completed":
        b.completed_at = datetime.utcnow()
        services.adjust_finished_stock(db, b.product_id, b.quantity)
        db.add(models.FinishedGoodsTransaction(
            product_id=b.product_id, transaction_type="production", quantity=b.quantity,
            reference_id=batch_id, reference_type="production_batch"))
    db.commit()
    return {"ok": True, "stage": nxt}


# ── Tailor jobs (fabric given to tailors for stitching) ──────────────────────
#
# Flow: Adjust "with tailor" down → the returned delta lands as `pending_qty`
# on a linked Product (named "Material (Tailor)") — NOT finished goods yet.
# The client sets a rate on that Product (Products screen), which is what
# moves the quantity into Finished Goods stock. This keeps every stage
# (with tailor / awaiting rate / in finished goods) visible and explicit.

def _get_or_create_job_product(db: Session, job: "models.TailorJob"):
    if job.product_id:
        p = db.query(models.Product).get(job.product_id)
        if p:
            return p
    mat = db.query(models.RawMaterialType).get(job.material_type_id)
    p = models.Product(
        name=f"{mat.name if mat else 'Material'} ({job.tailor_name})",
        unit_id=mat.unit_id if mat else None, sale_rate=0, pending_qty=0, is_active=1)
    db.add(p); db.flush()
    job.product_id = p.id
    return p


def _job_dict(db, j):
    mat = db.query(models.RawMaterialType).get(j.material_type_id)
    unit = db.query(models.Unit).get(mat.unit_id) if mat and mat.unit_id else None
    given = j.qty_given or 0
    returned = j.qty_returned or 0
    pending = finished = 0.0
    if j.product_id:
        p = db.query(models.Product).get(j.product_id)
        if p:
            pending = p.pending_qty or 0
            fg = db.query(models.FinishedGoodsStock).filter_by(product_id=p.id).first()
            finished = fg.quantity if fg else 0
    return {"id": j.id, "material": mat.name if mat else "", "material_id": j.material_type_id,
            "tailor": j.tailor_name, "unit": unit.abbreviation if unit else "",
            "qty_given": given, "qty_returned": returned, "held": max(0, given - returned),
            "pending_qty": pending, "finished_qty": finished, "product_id": j.product_id,
            "created_at": j.created_at.isoformat()[:10] if j.created_at else ""}


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    rows = db.query(models.TailorJob).order_by(models.TailorJob.id.desc()).all()
    return [_job_dict(db, j) for j in rows]


@router.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    j = db.query(models.TailorJob).get(job_id)
    if not j:
        raise HTTPException(404, "Not found")
    return _job_dict(db, j)


class JobAdjustIn(BaseModel):
    new_held: float          # quantity still with the tailor; the rest is returned


@router.post("/jobs/{job_id}/adjust")
def adjust_job(job_id: int, body: JobAdjustIn, db: Session = Depends(get_db)):
    j = db.query(models.TailorJob).get(job_id)
    if not j:
        raise HTTPException(404, "Not found")
    given = j.qty_given or 0
    new_held = max(0.0, min(given, body.new_held))   # clamp to 0..given
    old_returned = j.qty_returned or 0
    new_returned = given - new_held
    delta = new_returned - old_returned              # +ve = more returned, -ve = correction
    j.qty_returned = new_returned

    if delta != 0:
        p = _get_or_create_job_product(db, j)
        p.pending_qty = max(0.0, (p.pending_qty or 0) + delta)

    db.commit()
    return _job_dict(db, j)


@router.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    # Clear only removes the job-tracking row. Any product already created
    # from it (pending or already in finished goods) is left untouched —
    # that stock is real and shouldn't disappear because the job row is gone.
    j = db.query(models.TailorJob).get(job_id)
    if j:
        db.delete(j); db.commit()
    return {"ok": True}
