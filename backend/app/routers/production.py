from typing import Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import require_user
from .. import models, services

router = APIRouter(prefix="/api/production", tags=["production"],
                   dependencies=[Depends(require_user)])

STAGES = ["Cutting", "Stitching", "Dyeing", "Finishing", "QC", "Completed"]


class SizeBreakdown(BaseModel):
    m: float = 0
    l: float = 0
    xl: float = 0
    xxl: float = 0
    mxxl: float = 0


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
    target = j.target_pieces or 0
    delivered = sum(d.pieces or 0 for d in
                    db.query(models.TailorDelivery).filter_by(job_id=j.id).all())
    assigned = j.assigned_pieces or 0
    return {"id": j.id, "material": mat.name if mat else "", "material_id": j.material_type_id,
            "tailor": j.tailor_name, "tailor_type": j.tailor_type or "work",
            "unit": unit.abbreviation if unit else "",
            "qty_given": given, "qty_returned": returned, "held": max(0, given - returned),
            "pending_qty": pending, "finished_qty": finished, "product_id": j.product_id,
            "target_pieces": target, "delivered_pieces": delivered,
            "remaining_pieces": max(0, target - delivered),
            "assigned_pieces": assigned, "ready_to_assign": max(0, delivered - assigned),
            "parent_job_id": j.parent_job_id,
            "sizes": {"m": j.size_m or 0, "l": j.size_l or 0, "xl": j.size_xl or 0,
                      "xxl": j.size_xxl or 0, "mxxl": j.size_mxxl or 0},
            "created_at": j.created_at.isoformat()[:10] if j.created_at else ""}


def _delivery_dict(d):
    return {"id": d.id, "delivery_date": d.delivery_date, "pieces": d.pieces or 0,
            "image": d.image_path, "notes": d.notes or "",
            "sizes": {"m": d.size_m or 0, "l": d.size_l or 0, "xl": d.size_xl or 0,
                      "xxl": d.size_xxl or 0, "mxxl": d.size_mxxl or 0},
            "created_at": d.created_at.isoformat()[:16] if d.created_at else ""}


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
        db.query(models.TailorDelivery).filter_by(job_id=job_id).delete()
        db.delete(j); db.commit()
    return {"ok": True}


# ── Tailor targets & dated piece deliveries (with reference photos) ───────────

class TargetIn(BaseModel):
    target_pieces: float


@router.post("/jobs/{job_id}/target")
def set_target(job_id: int, body: TargetIn, db: Session = Depends(get_db)):
    j = db.query(models.TailorJob).get(job_id)
    if not j:
        raise HTTPException(404, "Not found")
    if body.target_pieces < 0:
        raise HTTPException(400, "Target cannot be negative")
    j.target_pieces = body.target_pieces
    db.commit()
    return _job_dict(db, j)


@router.get("/jobs/{job_id}/deliveries")
def list_deliveries(job_id: int, db: Session = Depends(get_db)):
    rows = (db.query(models.TailorDelivery).filter_by(job_id=job_id)
            .order_by(models.TailorDelivery.id.desc()).all())
    return [_delivery_dict(d) for d in rows]


def _pieces_unit_id(db: Session):
    u = (db.query(models.Unit)
         .filter((models.Unit.abbreviation.ilike("pcs")) | (models.Unit.name.ilike("Pieces")))
         .first())
    return u.id if u else None


def _get_or_create_finished_product(db: Session, name: str):
    """Final-tailor pieces land as a finished-goods Product, matched by design
    name (auto-created if new). The client can rename it / add an image after."""
    p = (db.query(models.Product)
         .filter(models.Product.is_active == 1, models.Product.name.ilike(name)).first())
    if p:
        return p
    p = models.Product(name=name, unit_id=_pieces_unit_id(db), sale_rate=0, is_active=1)
    db.add(p); db.flush()
    return p


class DeliveryIn(BaseModel):
    delivery_date: Optional[str] = None
    pieces: float = 0
    sizes: Optional[SizeBreakdown] = None   # optional per-size breakdown
    image_base64: Optional[str] = None   # data URL, optional reference photo
    notes: Optional[str] = ""


@router.post("/jobs/{job_id}/deliveries")
def add_delivery(job_id: int, body: DeliveryIn, db: Session = Depends(get_db)):
    j = db.query(models.TailorJob).get(job_id)
    if not j:
        raise HTTPException(404, "Not found")
    s = body.sizes
    size_total = (s.m + s.l + s.xl + s.xxl + s.mxxl) if s else 0
    pieces = size_total if size_total > 0 else body.pieces
    if pieces <= 0:
        raise HTTPException(400, "Pieces must be greater than 0")
    d = models.TailorDelivery(
        job_id=job_id, delivery_date=body.delivery_date or date.today().isoformat(),
        pieces=pieces, image_path=body.image_base64, notes=(body.notes or "").strip(),
        size_m=s.m if s else 0, size_l=s.l if s else 0, size_xl=s.xl if s else 0,
        size_xxl=s.xxl if s else 0, size_mxxl=s.mxxl if s else 0)
    db.add(d)

    # Pieces returned from a FINAL tailor become finished goods straight away.
    if (j.tailor_type or "work") == "final":
        mat = db.query(models.RawMaterialType).get(j.material_type_id)
        prod = _get_or_create_finished_product(db, mat.name if mat else f"Design {job_id}")
        if not j.product_id:
            j.product_id = prod.id
        # carry the reference photo onto the product if it has none yet
        if body.image_base64 and not prod.image_path:
            prod.image_path = body.image_base64
        services.adjust_finished_stock(db, prod.id, pieces)
        db.add(models.FinishedGoodsTransaction(
            product_id=prod.id, transaction_type="from_final_tailor", quantity=pieces,
            reference_id=job_id, reference_type="tailor_job"))

    db.commit(); db.refresh(d)
    return _delivery_dict(d)


class AssignFinalIn(BaseModel):
    tailor_name: str
    pieces: float = 0
    sizes: Optional[SizeBreakdown] = None


@router.post("/jobs/{job_id}/assign-final")
def assign_to_final(job_id: int, body: AssignFinalIn, db: Session = Depends(get_db)):
    """Hand a batch of work-tailor pieces onward to a final tailor. Creates a
    new 'final' job carved out of this work job's ready-to-assign pieces.
    A per-size breakdown can be given; if so the total is the sum of sizes."""
    w = db.query(models.TailorJob).get(job_id)
    if not w:
        raise HTTPException(404, "Not found")
    if (w.tailor_type or "work") != "work":
        raise HTTPException(400, "Only work-tailor jobs can be assigned onward")
    if not body.tailor_name.strip():
        raise HTTPException(400, "Enter the final tailor's name")

    s = body.sizes
    size_total = (s.m + s.l + s.xl + s.xxl + s.mxxl) if s else 0
    pieces = size_total if size_total > 0 else body.pieces
    if pieces <= 0:
        raise HTTPException(400, "Enter pieces to assign")

    delivered = sum(d.pieces or 0 for d in db.query(models.TailorDelivery).filter_by(job_id=job_id).all())
    ready = delivered - (w.assigned_pieces or 0)
    if pieces > ready:
        raise HTTPException(400, f"Only {ready:.0f} pieces ready to assign")

    f = models.TailorJob(
        material_type_id=w.material_type_id, tailor_name=body.tailor_name.strip(),
        tailor_type="final", qty_given=pieces, qty_returned=0,
        target_pieces=pieces, parent_job_id=w.id,
        size_m=s.m if s else 0, size_l=s.l if s else 0, size_xl=s.xl if s else 0,
        size_xxl=s.xxl if s else 0, size_mxxl=s.mxxl if s else 0)
    db.add(f)
    w.assigned_pieces = (w.assigned_pieces or 0) + pieces
    db.commit(); db.refresh(f)
    return _job_dict(db, f)


@router.delete("/jobs/{job_id}/deliveries/{delivery_id}")
def delete_delivery(job_id: int, delivery_id: int, db: Session = Depends(get_db)):
    d = db.query(models.TailorDelivery).filter_by(id=delivery_id, job_id=job_id).first()
    if d:
        db.delete(d); db.commit()
    return {"ok": True}
