from typing import Optional
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
                    "sale_rate": p.sale_rate, "value": qty * (p.sale_rate or 0),
                    "rate_m": p.rate_m or 0, "rate_l": p.rate_l or 0,
                    "rate_xl": p.rate_xl or 0, "rate_xxl": p.rate_xxl or 0,
                    "rate_mxxl": p.rate_mxxl or 0,
                    "image": p.image_path})
    return out


SIZE_COLS = ["m", "l", "xl", "xxl", "mxxl"]


@router.get("/availability")
def availability(db: Session = Depends(get_db)):
    """Per-design, per-size availability = pieces received from final tailors
    minus pieces already committed on order forms (sold). Keyed by design name."""
    received = {}   # name -> {size: qty}
    sold = {}

    def bump(store, name, sizes):
        key = (name or "").strip().lower()
        if not key:
            return
        d = store.setdefault(key, {"name": name, **{k: 0.0 for k in SIZE_COLS}})
        for k in SIZE_COLS:
            d[k] += sizes.get(k, 0) or 0

    # Received from final tailors (by design name).
    fin = (db.query(models.TailorDelivery, models.RawMaterialType.name)
           .join(models.TailorJob, models.TailorDelivery.job_id == models.TailorJob.id)
           .join(models.RawMaterialType, models.TailorJob.material_type_id == models.RawMaterialType.id)
           .filter(models.TailorJob.tailor_type == "final").all())
    for d, name in fin:
        bump(received, name, {k: getattr(d, f"size_{k}") or 0 for k in SIZE_COLS})

    # Sold / committed on order forms (by design name via the linked product).
    sbi = (db.query(models.SalesBillItem, models.Product.name)
           .join(models.Product, models.SalesBillItem.product_id == models.Product.id).all())
    for it, name in sbi:
        bump(sold, name, {"m": it.qty_m, "l": it.qty_l, "xl": it.qty_xl,
                          "xxl": it.qty_xxl, "mxxl": it.qty_mxxl})

    out = []
    for key in set(received) | set(sold):
        r = received.get(key, {"name": key, **{k: 0.0 for k in SIZE_COLS}})
        s = sold.get(key, {k: 0.0 for k in SIZE_COLS})
        avail = {k: (r[k] - s.get(k, 0)) for k in SIZE_COLS}
        out.append({
            "name": r["name"],
            "received": {k: r[k] for k in SIZE_COLS},
            "sold": {k: s.get(k, 0) for k in SIZE_COLS},
            "available": avail,
            "total_received": sum(r[k] for k in SIZE_COLS),
            "total_sold": sum(s.get(k, 0) for k in SIZE_COLS),
            "total_available": sum(avail.values()),
        })
    out.sort(key=lambda x: x["name"].lower())
    return out


@router.get("/{product_id}/detail")
def detail(product_id: int, db: Session = Depends(get_db)):
    """Per-design breakdown: how much of this design came from final tailors,
    how much is still pending with them, and the size split received."""
    p = db.query(models.Product).get(product_id)
    if not p:
        raise HTTPException(404, "Not found")

    SIZE_COLS = ["m", "l", "xl", "xxl", "mxxl"]
    # Final-tailor jobs for this design (matched by name).
    jobs = (db.query(models.TailorJob)
            .join(models.RawMaterialType, models.TailorJob.material_type_id == models.RawMaterialType.id)
            .filter(models.TailorJob.tailor_type == "final",
                    models.RawMaterialType.name.ilike(p.name)).all())

    sizes_received = {k: 0.0 for k in SIZE_COLS}
    received_total = pending_total = assigned_total = 0.0
    by_tailor = []
    for j in jobs:
        deliveries = db.query(models.TailorDelivery).filter_by(job_id=j.id)\
            .order_by(models.TailorDelivery.id.desc()).all()
        recv = sum(d.pieces or 0 for d in deliveries)
        given = j.qty_given or 0
        pending = max(0.0, given - recv)
        jsizes = {k: 0.0 for k in SIZE_COLS}
        for d in deliveries:
            for k in SIZE_COLS:
                v = getattr(d, f"size_{k}") or 0
                jsizes[k] += v
                sizes_received[k] += v
        received_total += recv
        pending_total += pending
        assigned_total += given
        by_tailor.append({
            "job_id": j.id, "tailor": j.tailor_name, "assigned": given,
            "received": recv, "pending": pending, "sizes": jsizes,
            "deliveries": [{"date": d.delivery_date, "pieces": d.pieces or 0,
                            "sizes": {k: getattr(d, f"size_{k}") or 0 for k in SIZE_COLS},
                            "notes": d.notes or "", "image": d.image_path}
                           for d in deliveries]})

    stock = db.query(models.FinishedGoodsStock).filter_by(product_id=product_id).first()
    return {
        "name": p.name, "image": p.image_path,
        "in_stock": stock.quantity if stock else 0,
        "assigned_total": assigned_total, "received_total": received_total,
        "pending_total": pending_total, "sizes_received": sizes_received,
        "by_tailor": by_tailor,
    }


class EditIn(BaseModel):
    name: Optional[str] = None
    sale_rate: Optional[float] = None
    rate_m: Optional[float] = None
    rate_l: Optional[float] = None
    rate_xl: Optional[float] = None
    rate_xxl: Optional[float] = None
    rate_mxxl: Optional[float] = None
    image_base64: Optional[str] = None   # data URL; pass "" to clear


@router.put("/{product_id}")
def edit_product(product_id: int, body: EditIn, db: Session = Depends(get_db)):
    p = db.query(models.Product).get(product_id)
    if not p:
        raise HTTPException(404, "Not found")
    if body.name is not None and body.name.strip():
        p.name = body.name.strip()
    if body.sale_rate is not None:
        p.sale_rate = body.sale_rate
    for col in ("rate_m", "rate_l", "rate_xl", "rate_xxl", "rate_mxxl"):
        val = getattr(body, col)
        if val is not None:
            setattr(p, col, val)
    if body.image_base64 is not None:
        p.image_path = body.image_base64 or None
    db.commit()
    return {"ok": True}


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


@router.delete("/{product_id}")
def delete_good(product_id: int, db: Session = Depends(get_db)):
    """Remove a finished-goods entry: zero its stock and deactivate the product
    (kept inactive rather than hard-deleted in case bills reference it)."""
    stock = db.query(models.FinishedGoodsStock).filter_by(product_id=product_id).first()
    if stock:
        stock.quantity = 0
    p = db.query(models.Product).get(product_id)
    if p:
        p.is_active = 0
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
