from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import require_user
from .. import models, services

router = APIRouter(prefix="/api/purchases", tags=["purchases"],
                   dependencies=[Depends(require_user)])


class PurchaseItemIn(BaseModel):
    material_type_id: int
    unit_id: Optional[int] = None
    quantity: float
    rate: float


class PurchaseBillIn(BaseModel):
    supplier_id: int
    bill_date: Optional[str] = None
    gst_type: str = "none"          # none | cgst_sgst | igst
    gst_percent: float = 0
    notes: Optional[str] = ""
    items: List[PurchaseItemIn]


@router.get("/next-number")
def next_number(db: Session = Depends(get_db)):
    return {"bill_number": services.next_purchase_number(db)}


@router.get("")
def list_bills(db: Session = Depends(get_db)):
    out = []
    for b in db.query(models.PurchaseBill).order_by(models.PurchaseBill.id.desc()).all():
        sup = db.query(models.Supplier).get(b.supplier_id)
        count = db.query(models.PurchaseBillItem).filter_by(bill_id=b.id).count()
        out.append({"id": b.id, "bill_number": b.bill_number, "bill_date": b.bill_date,
                    "supplier": sup.name if sup else "", "items": count,
                    "subtotal": b.subtotal, "gst_amount": b.gst_amount,
                    "total_amount": b.total_amount})
    return out


@router.post("")
def create_bill(body: PurchaseBillIn, db: Session = Depends(get_db)):
    if not body.items:
        raise HTTPException(400, "Add at least one item")
    subtotal = sum(i.quantity * i.rate for i in body.items)
    gst_amount = subtotal * body.gst_percent / 100 if body.gst_type != "none" else 0
    total = subtotal + gst_amount

    bill = models.PurchaseBill(
        bill_number=services.next_purchase_number(db), supplier_id=body.supplier_id,
        bill_date=body.bill_date or date.today().isoformat(), subtotal=subtotal,
        gst_type=body.gst_type, gst_percent=body.gst_percent, gst_amount=gst_amount,
        total_amount=total, notes=body.notes)
    db.add(bill); db.flush()

    for it in body.items:
        amount = it.quantity * it.rate
        db.add(models.PurchaseBillItem(
            bill_id=bill.id, material_type_id=it.material_type_id, unit_id=it.unit_id,
            quantity=it.quantity, rate=it.rate, amount=amount))
        services.adjust_raw_stock(db, it.material_type_id, it.quantity, it.rate)
        db.add(models.RawMaterialTransaction(
            material_type_id=it.material_type_id, transaction_type="purchase",
            quantity=it.quantity, rate=it.rate, reference_id=bill.id,
            reference_type="purchase_bill"))
    db.commit()
    return {"id": bill.id, "bill_number": bill.bill_number}


@router.delete("/{bill_id}")
def delete_bill(bill_id: int, db: Session = Depends(get_db)):
    db.query(models.PurchaseBillItem).filter_by(bill_id=bill_id).delete()
    b = db.query(models.PurchaseBill).get(bill_id)
    if b: db.delete(b)
    db.commit()
    return {"ok": True}
