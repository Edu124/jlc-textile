from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import require_user
from .. import models

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"],
                   dependencies=[Depends(require_user)])


@router.get("/analytics")
def analytics(db: Session = Depends(get_db)):
    SB, SBI, O, PB, C = (models.SalesBill, models.SalesBillItem, models.Order,
                         models.PurchaseBill, models.Customer)
    month = datetime.now().strftime("%Y-%m")

    def month_sum(model, col, datecol):
        return db.query(func.coalesce(func.sum(getattr(model, col)), 0)).filter(
            func.substr(getattr(model, datecol), 1, 7) == month).scalar() or 0

    month_sales = month_sum(SB, "total_amount", "bill_date")
    month_qty = month_sum(SB, "total_qty", "bill_date")
    month_purchases = month_sum(PB, "total_amount", "bill_date")
    month_bills = db.query(func.count(SB.id)).filter(
        func.substr(SB.bill_date, 1, 7) == month).scalar() or 0
    month_orders = db.query(func.count(O.id)).filter(
        func.substr(O.created_at, 1, 7) == month).scalar() or 0
    avg_order_value = (month_sales / month_bills) if month_bills else 0

    # sales trend — last 30 days
    start = (date.today() - timedelta(days=29)).isoformat()
    rows = (db.query(SB.bill_date, func.coalesce(func.sum(SB.total_amount), 0))
            .filter(SB.bill_date >= start).group_by(SB.bill_date).all())
    by_day = {d: float(a) for d, a in rows}
    trend = []
    for i in range(29, -1, -1):
        d = date.today() - timedelta(days=i)
        trend.append({"label": d.strftime("%d/%m"), "value": by_day.get(d.isoformat(), 0)})

    # size mix
    sz = db.query(
        func.coalesce(func.sum(SBI.qty_m), 0), func.coalesce(func.sum(SBI.qty_l), 0),
        func.coalesce(func.sum(SBI.qty_xl), 0), func.coalesce(func.sum(SBI.qty_xxl), 0),
        func.coalesce(func.sum(SBI.qty_mxxl), 0)).one()
    size_mix = [{"label": l, "value": float(v)} for l, v in
                zip(["M", "L", "XL", "XXL", "M-XXL"], sz)]

    # order status
    status_rows = (db.query(O.status, func.count(O.id)).group_by(O.status)
                   .order_by(func.count(O.id).desc()).all())
    order_status = [{"label": s or "—", "value": n} for s, n in status_rows]

    # top designs
    td = (db.query(SBI.design_no, func.coalesce(func.sum(SBI.row_qty), 0))
          .filter(SBI.design_no.isnot(None), SBI.design_no != "")
          .group_by(SBI.design_no).order_by(func.sum(SBI.row_qty).desc()).limit(6).all())
    top_designs = [{"label": d, "value": float(q)} for d, q in td]

    # top customers
    tc = (db.query(C.name, func.coalesce(func.sum(SB.total_amount), 0))
          .join(SB, SB.customer_id == C.id).group_by(C.id)
          .order_by(func.sum(SB.total_amount).desc()).limit(5).all())
    top_customers = [{"label": n, "value": float(v)} for n, v in tc]

    return {
        "month_sales": float(month_sales), "month_qty": float(month_qty),
        "month_orders": month_orders, "month_purchases": float(month_purchases),
        "avg_order_value": float(avg_order_value), "sales_trend": trend,
        "size_mix": size_mix, "order_status": order_status,
        "top_designs": top_designs, "top_customers": top_customers,
    }


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    raw_val = db.query(func.coalesce(func.sum(
        models.RawMaterialStock.quantity * models.RawMaterialStock.avg_rate), 0)).scalar() or 0
    fg_qty = db.query(func.coalesce(func.sum(models.FinishedGoodsStock.quantity), 0)).scalar() or 0
    pending = db.query(func.count(models.Order.id)).filter(
        ~models.Order.status.in_(["Delivered", "Cancelled"])).scalar() or 0
    today = date.today().isoformat()
    today_sales = db.query(func.coalesce(func.sum(models.SalesBill.total_amount), 0)).filter(
        models.SalesBill.bill_date == today).scalar() or 0

    low = []
    for m in db.query(models.RawMaterialType).filter(
            models.RawMaterialType.low_stock_threshold > 0).all():
        st = db.query(models.RawMaterialStock).filter_by(material_type_id=m.id).first()
        qty = st.quantity if st else 0
        if qty <= m.low_stock_threshold:
            unit = db.query(models.Unit).get(m.unit_id) if m.unit_id else None
            low.append({"name": m.name, "quantity": qty,
                        "threshold": m.low_stock_threshold,
                        "unit": unit.abbreviation if unit else ""})

    recent = []
    for o in db.query(models.Order).order_by(models.Order.id.desc()).limit(8).all():
        cust = db.query(models.Customer).get(o.customer_id)
        items = db.query(models.OrderItem).filter_by(order_id=o.id).all()
        tq = sum(it.quantity or 0 for it in items)
        dq = sum(it.delivered_qty or 0 for it in items)
        # The client works by the bill's reference number, not the auto order no.
        bill = db.query(models.SalesBill).filter_by(order_id=o.id).first()
        ref = (bill.reference_no if bill and bill.reference_no else "") or o.order_number
        recent.append({"id": o.id, "order_number": ref, "customer": cust.name if cust else "",
                       "status": o.status, "total_amount": o.total_amount,
                       "total_qty": tq, "delivered_qty": dq,
                       "date": o.created_at.isoformat()[:10] if o.created_at else ""})

    return {"raw_stock_value": float(raw_val), "finished_goods_qty": float(fg_qty),
            "pending_orders": pending, "today_sales": float(today_sales),
            "low_stock": low, "recent_orders": recent}
