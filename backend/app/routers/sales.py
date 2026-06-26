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
    qty_m: float = 0
    qty_l: float = 0
    qty_xl: float = 0
    qty_xxl: float = 0
    qty_mxxl: float = 0
    mrp: float = 0


class SalesBillIn(BaseModel):
    customer_id: int
    bill_date: Optional[str] = None
    delivery_date: Optional[str] = None
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
                    "customer": cust.name if cust else "", "designs": item_count,
                    "total_qty": b.total_qty or 0, "total_amount": b.total_amount or 0})
    return out


@router.get("/{bill_id}")
def get_bill(bill_id: int, db: Session = Depends(get_db)):
    b = db.query(models.SalesBill).get(bill_id)
    if not b: raise HTTPException(404, "Not found")
    cust = db.query(models.Customer).get(b.customer_id)
    items = db.query(models.SalesBillItem).filter_by(bill_id=bill_id).all()
    return {
        "id": b.id, "bill_number": b.bill_number, "bill_date": b.bill_date,
        "delivery_date": b.delivery_date, "transport": b.transport, "agent": b.agent,
        "customer": {"id": cust.id, "name": cust.name, "phone": cust.phone,
                     "address": cust.address, "gst_number": cust.gst_number} if cust else None,
        "total_qty": b.total_qty or 0, "total_amount": b.total_amount or 0,
        "items": [{"design_no": it.design_no, "qty_m": it.qty_m, "qty_l": it.qty_l,
                   "qty_xl": it.qty_xl, "qty_xxl": it.qty_xxl, "qty_mxxl": it.qty_mxxl,
                   "row_qty": it.row_qty, "mrp": it.mrp, "amount": it.amount}
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
        row_qty = (it.qty_m or 0) + (it.qty_l or 0) + (it.qty_xl or 0) + \
                  (it.qty_xxl or 0) + (it.qty_mxxl or 0)
        if row_qty <= 0:
            continue
        amount = row_qty * (it.mrp or 0)
        total_qty += row_qty
        total_amt += amount
        prepared.append((it, row_qty, amount))

    if not prepared:
        raise HTTPException(400, "Enter quantity for at least one size")

    bill = models.SalesBill(
        bill_number=services.next_sales_number(db), customer_id=body.customer_id,
        bill_date=body.bill_date or date.today().isoformat(),
        delivery_date=body.delivery_date, transport=body.transport, agent=body.agent,
        subtotal=total_amt, gst_type="none", total_qty=total_qty, total_amount=total_amt)
    db.add(bill); db.flush()

    for it, row_qty, amount in prepared:
        db.add(models.SalesBillItem(
            bill_id=bill.id, design_no=it.design_no, product_id=it.product_id,
            qty_m=it.qty_m, qty_l=it.qty_l, qty_xl=it.qty_xl, qty_xxl=it.qty_xxl,
            qty_mxxl=it.qty_mxxl, row_qty=row_qty, mrp=it.mrp, amount=amount))
    db.commit()
    return {"id": bill.id, "bill_number": bill.bill_number}


@router.get("/{bill_id}/pdf")
def bill_pdf(bill_id: int, db: Session = Depends(get_db)):
    b = db.query(models.SalesBill).get(bill_id)
    if not b:
        raise HTTPException(404, "Not found")
    pdf_bytes = generate_sales_pdf(db, bill_id)
    fname = (b.bill_number or "order").replace("/", "_") + ".pdf"
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{fname}"'})


@router.delete("/{bill_id}")
def delete_bill(bill_id: int, db: Session = Depends(get_db)):
    db.query(models.SalesBillItem).filter_by(bill_id=bill_id).delete()
    b = db.query(models.SalesBill).get(bill_id)
    if b: db.delete(b)
    db.commit()
    return {"ok": True}
