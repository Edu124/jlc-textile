from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import require_user
from .. import models, services
from ..pdf import generate_sales_pdf

router = APIRouter(prefix="/api/sales", tags=["sales"], dependencies=[Depends(require_user)])


class SalesItemIn(BaseModel):
    design_no: str
    product_id: Optional[int] = None
    qty_s: float = 0
    qty_m: float = 0
    qty_l: float = 0
    qty_xl: float = 0
    qty_xxl: float = 0
    qty_mxxl: float = 0
    qty_xxxl: float = 0
    qty_xxxxl: float = 0


SIZE_KEYS = [("qty_s", "rate_s"), ("qty_m", "rate_m"), ("qty_l", "rate_l"),
             ("qty_xl", "rate_xl"), ("qty_xxl", "rate_xxl"), ("qty_xxxl", "rate_xxxl"),
             ("qty_xxxxl", "rate_xxxxl"), ("qty_mxxl", "rate_mxxl")]


def _effective_rates(product):
    """Per-size rate, falling back to the product's base sale_rate when a
    specific size rate is 0/unset."""
    base = (product.sale_rate or 0) if product else 0
    out = {}
    for _, rk in SIZE_KEYS:
        out[rk] = (getattr(product, rk, 0) or 0) if product else 0
        if out[rk] <= 0:
            out[rk] = base
    return out


class SalesBillIn(BaseModel):
    customer_id: int
    bill_date: Optional[str] = None
    delivery_date: Optional[str] = None
    reference_no: Optional[str] = ""
    transport: Optional[str] = ""
    agent: Optional[str] = ""
    items: List[SalesItemIn]


@router.get("/next-number")
def next_number(db: Session = Depends(get_db)):
    return {"bill_number": services.next_sales_number(db)}


@router.get("")
def list_bills(db: Session = Depends(get_db)):
    out = []
    for b in db.query(models.SalesBill).order_by(models.SalesBill.id.desc()).all():
        cust = db.query(models.Customer).get(b.customer_id)
        item_count = db.query(models.SalesBillItem).filter_by(bill_id=b.id).count()
        out.append({"id": b.id, "bill_number": b.bill_number, "bill_date": b.bill_date,
                    "reference_no": b.reference_no or "",
                    "customer": cust.name if cust else "", "customer_id": b.customer_id,
                    "designs": item_count, "order_id": b.order_id,
                    "total_qty": b.total_qty or 0, "total_amount": b.total_amount or 0})
    return out


SIZE_LABELS = {"s": "S", "m": "M", "l": "L", "xl": "XL", "xxl": "XXL",
               "xxxl": "3XL", "xxxxl": "4XL", "mxxl": "M-XXL"}


@router.get("/pending")
def pending_deliveries(db: Session = Depends(get_db)):
    """Ordered-but-undelivered pieces per design+size across all order forms,
    matched against pieces PHYSICALLY IN HAND (received from tailors / direct
    entries minus already handed over) — the same check the delivery popup
    enforces, so 'Ready' here always means the delivery will go through."""
    from .orders import _received_for_design, _delivered_for_design
    cache = {}

    def in_hand(design, size_key=None):
        key = design.lower()
        if key not in cache:
            recv, rt = _received_for_design(db, design)
            done, dt = _delivered_for_design(db, design)
            untagged = max(0.0, rt - sum(recv.values()))
            cache[key] = (recv, done, untagged, rt, dt)
        recv, done, untagged, rt, dt = cache[key]
        if size_key:
            return max(0.0, recv[size_key] + untagged - done[size_key])
        return max(0.0, rt - dt)

    out = []
    for b in db.query(models.SalesBill).order_by(models.SalesBill.id.desc()).all():
        if not b.order_id:
            continue
        cust = db.query(models.Customer).get(b.customer_id)
        for it in db.query(models.OrderItem).filter_by(order_id=b.order_id).all():
            design = (it.design_no or "").strip()
            has_sizes = any((getattr(it, f"qty_{k}") or 0) for k in SIZE_LABELS)
            if has_sizes:
                for k, lbl in SIZE_LABELS.items():
                    pend = (getattr(it, f"qty_{k}") or 0) - (getattr(it, f"delivered_{k}") or 0)
                    if pend <= 0:
                        continue
                    stock = in_hand(design, k) if design else 0
                    out.append({"bill_id": b.id, "ref": b.reference_no or b.bill_number,
                                "customer": cust.name if cust else "", "design_no": design,
                                "size": lbl, "pending": pend, "in_stock": stock,
                                "ready": stock >= pend})
            else:
                pend = (it.quantity or 0) - (it.delivered_qty or 0)
                if pend <= 0:
                    continue
                stock = in_hand(design) if design else 0
                out.append({"bill_id": b.id, "ref": b.reference_no or b.bill_number,
                            "customer": cust.name if cust else "", "design_no": design,
                            "size": "—", "pending": pend, "in_stock": stock,
                            "ready": stock >= pend})
    return out


@router.get("/{bill_id}")
def get_bill(bill_id: int, db: Session = Depends(get_db)):
    b = db.query(models.SalesBill).get(bill_id)
    if not b: raise HTTPException(404, "Not found")
    cust = db.query(models.Customer).get(b.customer_id)
    items = db.query(models.SalesBillItem).filter_by(bill_id=bill_id).all()
    return {
        "id": b.id, "bill_number": b.bill_number, "bill_date": b.bill_date,
        "delivery_date": b.delivery_date, "reference_no": b.reference_no or "",
        "transport": b.transport, "agent": b.agent,
        "customer": {"id": cust.id, "name": cust.name, "phone": cust.phone,
                     "address": cust.address, "gst_number": cust.gst_number} if cust else None,
        "total_qty": b.total_qty or 0, "total_amount": b.total_amount or 0,
        "items": [{"design_no": it.design_no, "row_qty": it.row_qty,
                   "mrp": it.mrp, "amount": it.amount,
                   **{qk: getattr(it, qk) or 0 for qk, _ in SIZE_KEYS}}
                  for it in items],
    }


@router.post("")
def create_bill(body: SalesBillIn, db: Session = Depends(get_db)):
    if not body.items:
        raise HTTPException(400, "Add at least one design")

    total_qty = 0.0
    total_amt = 0.0
    prepared = []
    for it in body.items:
        row_qty = sum((getattr(it, qk) or 0) for qk, _ in SIZE_KEYS)
        if row_qty <= 0:
            continue
        product = db.query(models.Product).get(it.product_id) if it.product_id else None
        rates = _effective_rates(product)
        # amount = Σ qty_size × rate_size
        amount = sum((getattr(it, qk) or 0) * rates[rk] for qk, rk in SIZE_KEYS)
        # representative MRP (max size rate, for the single-column display)
        rep_mrp = max(rates.values()) if rates else 0
        total_qty += row_qty
        total_amt += amount
        prepared.append((it, row_qty, amount, rates, rep_mrp))

    if not prepared:
        raise HTTPException(400, "Enter quantity for at least one size")

    bill = models.SalesBill(
        bill_number=services.next_sales_number(db), customer_id=body.customer_id,
        bill_date=body.bill_date or date.today().isoformat(),
        delivery_date=body.delivery_date, reference_no=body.reference_no,
        transport=body.transport, agent=body.agent,
        subtotal=total_amt, gst_type="none", total_qty=total_qty, total_amount=total_amt)
    db.add(bill); db.flush()

    for it, row_qty, amount, rates, rep_mrp in prepared:
        db.add(models.SalesBillItem(
            bill_id=bill.id, design_no=it.design_no, product_id=it.product_id,
            row_qty=row_qty, mrp=rep_mrp, amount=amount,
            **{qk: getattr(it, qk) for qk, _ in SIZE_KEYS},
            **{rk: rates[rk] for _, rk in SIZE_KEYS}))
        _deduct_stock(db, it.product_id, row_qty, bill.id)
    services.sync_order_from_bill(db, bill, prepared)
    db.commit()
    return {"id": bill.id, "bill_number": bill.bill_number}


def _deduct_stock(db: Session, product_id, row_qty, bill_id):
    """Sold pieces leave finished-goods stock immediately."""
    if product_id and row_qty > 0:
        services.adjust_finished_stock(db, product_id, -row_qty)
        db.add(models.FinishedGoodsTransaction(
            product_id=product_id, transaction_type="sale", quantity=-row_qty,
            reference_id=bill_id, reference_type="sales_bill"))


def _restore_stock(db: Session, bill_id, reason):
    """Put a bill's pieces back into finished goods (bill edited or deleted)."""
    for old in db.query(models.SalesBillItem).filter_by(bill_id=bill_id).all():
        if old.product_id and (old.row_qty or 0) > 0:
            services.adjust_finished_stock(db, old.product_id, old.row_qty or 0)
            db.add(models.FinishedGoodsTransaction(
                product_id=old.product_id, transaction_type=reason, quantity=old.row_qty or 0,
                reference_id=bill_id, reference_type="sales_bill"))


@router.put("/{bill_id}")
def update_bill(bill_id: int, body: SalesBillIn, db: Session = Depends(get_db)):
    bill = db.query(models.SalesBill).get(bill_id)
    if not bill:
        raise HTTPException(404, "Not found")
    if not body.items:
        raise HTTPException(400, "Add at least one design")

    total_qty = 0.0
    total_amt = 0.0
    prepared = []
    for it in body.items:
        row_qty = sum((getattr(it, qk) or 0) for qk, _ in SIZE_KEYS)
        if row_qty <= 0:
            continue
        product = db.query(models.Product).get(it.product_id) if it.product_id else None
        rates = _effective_rates(product)
        amount = sum((getattr(it, qk) or 0) * rates[rk] for qk, rk in SIZE_KEYS)
        rep_mrp = max(rates.values()) if rates else 0
        total_qty += row_qty
        total_amt += amount
        prepared.append((it, row_qty, amount, rates, rep_mrp))

    if not prepared:
        raise HTTPException(400, "Enter quantity for at least one size")

    bill.customer_id = body.customer_id
    bill.bill_date = body.bill_date or bill.bill_date
    bill.delivery_date = body.delivery_date
    bill.reference_no = body.reference_no
    bill.transport = body.transport
    bill.agent = body.agent
    bill.subtotal = total_amt
    bill.total_qty = total_qty
    bill.total_amount = total_amt

    _restore_stock(db, bill.id, "sale_edit")
    db.query(models.SalesBillItem).filter_by(bill_id=bill.id).delete()
    for it, row_qty, amount, rates, rep_mrp in prepared:
        db.add(models.SalesBillItem(
            bill_id=bill.id, design_no=it.design_no, product_id=it.product_id,
            row_qty=row_qty, mrp=rep_mrp, amount=amount,
            **{qk: getattr(it, qk) for qk, _ in SIZE_KEYS},
            **{rk: rates[rk] for _, rk in SIZE_KEYS}))
        _deduct_stock(db, it.product_id, row_qty, bill.id)
    services.sync_order_from_bill(db, bill, prepared)
    db.commit()
    return {"id": bill.id, "bill_number": bill.bill_number}


@router.get("/{bill_id}/pdf")
def bill_pdf(bill_id: int, amounts: int = 0, ref: int = 1, delivery: int = 1,
             transport: int = 1, agent: int = 1, db: Session = Depends(get_db)):
    b = db.query(models.SalesBill).get(bill_id)
    if not b:
        raise HTTPException(404, "Not found")
    pdf_bytes = generate_sales_pdf(db, bill_id, show_amounts=bool(amounts),
                                   show_ref=bool(ref), show_delivery=bool(delivery),
                                   show_transport=bool(transport), show_agent=bool(agent))
    fname = (b.bill_number or "order").replace("/", "_") + ".pdf"
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{fname}"'})


@router.delete("/{bill_id}")
def delete_bill(bill_id: int, db: Session = Depends(get_db)):
    _restore_stock(db, bill_id, "sale_deleted")
    db.query(models.SalesBillItem).filter_by(bill_id=bill_id).delete()
    b = db.query(models.SalesBill).get(bill_id)
    if b:
        if b.order_id:
            # Postgres enforces FKs — remove/unlink everything pointing at the order
            db.query(models.OrderDelivery).filter_by(order_id=b.order_id).delete()
            db.query(models.ProductionBatch).filter_by(order_id=b.order_id).update({"order_id": None})
            db.query(models.OrderItem).filter_by(order_id=b.order_id).delete()
            order = db.query(models.Order).get(b.order_id)
            if order: db.delete(order)
        db.delete(b)
    db.commit()
    return {"ok": True}
