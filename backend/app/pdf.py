"""Jai Laxmi Creation order-form PDF — server-side, returns bytes.
Cross-platform fonts (Linux/Railway, Windows) with Helvetica fallback."""
import os
import io
import math
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Flowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlalchemy.orm import Session
from . import models

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
SCRIPT_FONT = "Helvetica-Bold"

_HERE = os.path.dirname(os.path.abspath(__file__))
_BUNDLED = os.path.join(_HERE, "fonts")
_WIN = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
_LINUX = "/usr/share/fonts"


def _try_register(name, *paths):
    for p in paths:
        if p and os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont(name, p))
                return True
            except Exception:
                continue
    return False


def _register_fonts():
    global FONT, FONT_BOLD, SCRIPT_FONT
    # Regular + bold body font with ₹ support (DejaVu / Arial / Segoe).
    if _try_register("JLCFont",
                     os.path.join(_BUNDLED, "DejaVuSans.ttf"),
                     os.path.join(_WIN, "arial.ttf"),
                     os.path.join(_LINUX, "truetype/dejavu/DejaVuSans.ttf"),
                     os.path.join(_WIN, "segoeui.ttf")):
        FONT = "JLCFont"
    if _try_register("JLCFont-Bold",
                     os.path.join(_BUNDLED, "DejaVuSans-Bold.ttf"),
                     os.path.join(_WIN, "arialbd.ttf"),
                     os.path.join(_LINUX, "truetype/dejavu/DejaVuSans-Bold.ttf"),
                     os.path.join(_WIN, "segoeuib.ttf")):
        FONT_BOLD = "JLCFont-Bold"
    # Script font for the cursive "Jlc" mark (falls back to bold).
    if _try_register("JLCScript",
                     os.path.join(_BUNDLED, "Script.ttf"),
                     os.path.join(_WIN, "segoescb.ttf"),
                     os.path.join(_WIN, "segoesc.ttf"),
                     os.path.join(_WIN, "Inkfree.ttf")):
        SCRIPT_FONT = "JLCScript"
    else:
        SCRIPT_FONT = FONT_BOLD


_register_fonts()

COL_TEXT = colors.HexColor("#1a1a1a")
COL_MUTED = colors.HexColor("#555555")
COL_LINE = colors.HexColor("#000000")
COL_GRID = colors.HexColor("#333333")
COL_HEADBG = colors.HexColor("#ECECEC")


def _settings(db: Session) -> dict:
    rows = {s.key: s.value for s in db.query(models.Setting).all()}
    g = lambda k, d="": rows.get(k, d)
    return {
        "name": g("company_name", "Jai Laxmi Creation"),
        "tagline": g("company_tagline", "MFG. OF EXCLUSIVE SALWAR KAMEEZ"),
        "slogan": g("company_slogan", "Your Style is Important"),
        "address": g("address", ""), "gst": g("gst_number", ""),
        "phone": g("phone", ""), "email": g("email", ""),
        "instagram": g("instagram", ""),
        "note1": g("footer_note1", "For Sizes XL, XXL, 3XL Extra Charges 25-50 Rs."),
        "note2": g("footer_note2", "Goods Once Sold will not be taken back."),
    }


class Swastika(Flowable):
    def __init__(self, size=13):
        Flowable.__init__(self); self.size = size
        self.width = self.height = size

    def draw(self):
        c = self.canv; s = self.size; u = s / 4.0; cx = cy = s / 2.0
        c.setLineWidth(1.2); c.setStrokeColor(COL_LINE)
        c.line(cx, cy - 2 * u, cx, cy + 2 * u)
        c.line(cx - 2 * u, cy, cx + 2 * u, cy)
        c.line(cx, cy + 2 * u, cx + 2 * u, cy + 2 * u)
        c.line(cx + 2 * u, cy, cx + 2 * u, cy - 2 * u)
        c.line(cx, cy - 2 * u, cx - 2 * u, cy - 2 * u)
        c.line(cx - 2 * u, cy, cx - 2 * u, cy + 2 * u)


class VectorLogo(Flowable):
    def __init__(self, slogan, w=104, h=74):
        Flowable.__init__(self); self.width = w; self.height = h; self.slogan = slogan

    def draw(self):
        c = self.canv; W, H = self.width, self.height
        c.setLineWidth(1.8); c.setStrokeColor(COL_TEXT)
        path = c.beginPath()
        path.arc(W * 0.04, H * 0.18, W * 0.96, H * 1.02, 20, 140)
        c.drawPath(path, stroke=1, fill=0)
        c.setFillColor(COL_TEXT); c.setFont(SCRIPT_FONT, H * 0.50)
        c.drawCentredString(W / 2.0, H * 0.30, "Jlc")
        c.setFont(FONT, H * 0.085); c.setFillColor(COL_MUTED)
        R = W * 0.47; ccx, ccy = W / 2.0, H * 0.66; n = len(self.slogan)
        for i, ch in enumerate(self.slogan):
            ang = 233 + (307 - 233) * i / max(1, n - 1); r = math.radians(ang)
            c.saveState(); c.translate(ccx + R * math.cos(r), ccy + R * math.sin(r))
            c.rotate(ang + 90); c.drawCentredString(0, 0, ch); c.restoreState()


def _fmt_date(d):
    if not d: return ""
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return d


def _watermark(co):
    def draw(c, doc):
        w, h = A4
        c.saveState()
        try:
            c.setFillColor(colors.black); c.setFillAlpha(0.06)
            c.translate(w / 2.0, h / 2.0)
            c.setFont(SCRIPT_FONT, 150); c.drawCentredString(0, -10, "Jlc")
            c.setFont(FONT_BOLD, 22); c.drawCentredString(0, -85, co["name"])
        except Exception:
            pass
        c.restoreState()
    return draw


def generate_sales_pdf(db: Session, bill_id: int) -> bytes:
    bill = db.query(models.SalesBill).get(bill_id)
    if not bill:
        raise ValueError("Bill not found")
    items = db.query(models.SalesBillItem).filter_by(bill_id=bill_id)\
        .order_by(models.SalesBillItem.id).all()
    cust = db.query(models.Customer).get(bill.customer_id)
    co = _settings(db)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=11 * mm, rightMargin=11 * mm,
                            topMargin=10 * mm, bottomMargin=12 * mm)

    s_center = ParagraphStyle("c", fontName=FONT, fontSize=9, alignment=TA_CENTER, textColor=COL_TEXT, leading=12)
    s_company = ParagraphStyle("co", fontName=FONT_BOLD, fontSize=30, alignment=TA_CENTER, textColor=COL_TEXT, leading=32)
    s_tag = ParagraphStyle("tg", fontName=FONT_BOLD, fontSize=10.5, alignment=TA_CENTER, textColor=COL_TEXT, leading=13)
    s_field = ParagraphStyle("fl", fontName=FONT, fontSize=9.5, textColor=COL_TEXT, leading=13)
    s_field_b = ParagraphStyle("flb", fontName=FONT_BOLD, fontSize=9.5, textColor=COL_TEXT, leading=13)

    story = []
    top = Table([["", Swastika(13),
                  Paragraph(f"Mob.: {co['phone']}", ParagraphStyle("m", fontName=FONT_BOLD, fontSize=9, alignment=TA_RIGHT, textColor=COL_TEXT))]],
                colWidths=[62 * mm, 64 * mm, 62 * mm])
    top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 0), (1, 0), "CENTER"),
                             ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(top)
    story.append(Paragraph("ORDER FORM", ParagraphStyle("of", fontName=FONT_BOLD, fontSize=11, alignment=TA_CENTER, textColor=COL_TEXT, spaceBefore=1, spaceAfter=2)))

    center_block = [Paragraph(co["name"], s_company), Paragraph(co["tagline"], s_tag),
                    Paragraph(co["address"], s_center),
                    Paragraph(f"GST No.: {co['gst']}  |  Email : {co['email']}", s_center)]
    header = Table([[VectorLogo(co["slogan"]), center_block, ""]], colWidths=[38 * mm, 112 * mm, 38 * mm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (0, 0), "CENTER"),
                                ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(header)
    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=COL_LINE))
    story.append(Spacer(1, 3 * mm))

    addr = (cust.address or "") if cust else ""
    addr1, addr2 = (addr.split("\n", 1) + [""])[:2] if addr else ("", "")
    fld = lambda t: Paragraph(t, s_field_b)
    val = lambda t: Paragraph(t or "", s_field)
    meta = Table([
        [fld("Party"), val(cust.name if cust else ""), fld("No."), val(bill.bill_number)],
        [fld("Contact"), val(cust.phone if cust else ""), fld("Ref. No."), val(getattr(bill, "reference_no", "") or "")],
        [fld("Add."), val(addr1), fld("Date"), val(_fmt_date(bill.bill_date))],
        [fld(""), val(addr2), fld("Delivery Date"), val(_fmt_date(bill.delivery_date))],
        [fld("GST No."), val(cust.gst_number if cust else ""), fld("Transport"), val(bill.transport)],
        [fld(""), val(""), fld("Agent"), val(bill.agent)],
    ], colWidths=[20 * mm, 90 * mm, 28 * mm, 50 * mm])
    meta.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                              ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                              ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                              ("LINEBELOW", (1, 0), (1, -1), 0.6, COL_MUTED),
                              ("LINEBELOW", (3, 0), (3, -1), 0.6, COL_MUTED)]))
    story.append(meta)
    story.append(Spacer(1, 3 * mm))

    col_w = [10 * mm, 42 * mm, 16 * mm, 16 * mm, 16 * mm, 16 * mm, 20 * mm, 18 * mm, 32 * mm]
    data = [["Sr.", "Design No.", "M", "L", "XL", "XXL", "M-XXL", "", "Amount"]]
    z = lambda v: str(int(v)) if v else ""
    total_qty = 0
    total_amount = 0
    for i in range(20):
        if i < len(items):
            it = items[i]; total_qty += it.row_qty or 0; total_amount += it.amount or 0
            data.append([str(i + 1), it.design_no or "", z(it.qty_m), z(it.qty_l),
                         z(it.qty_xl), z(it.qty_xxl), z(it.qty_mxxl), "",
                         f"{it.amount:,.0f}" if it.amount else ""])
        else:
            data.append([str(i + 1), "", "", "", "", "", "", "", ""])
    grid = Table(data, colWidths=col_w, repeatRows=1)
    grid.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD), ("FONTSIZE", (0, 0), (-1, 0), 9.5),
        ("BACKGROUND", (0, 0), (-1, 0), COL_HEADBG),
        ("FONTNAME", (0, 1), (-1, -1), FONT), ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (0, 0), (0, -1), "CENTER"), ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.6, COL_GRID),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (1, 0), (1, -1), 6)]))
    story.append(grid)

    lbl_q = ParagraphStyle("tq", fontName=FONT_BOLD, fontSize=10, alignment=TA_CENTER, textColor=COL_TEXT)
    val_q = ParagraphStyle("tv", fontName=FONT_BOLD, fontSize=11, alignment=TA_CENTER, textColor=COL_TEXT)
    bottom = Table([[
        Paragraph(co["note1"], ParagraphStyle("n", fontName=FONT_BOLD, fontSize=9, textColor=COL_TEXT, leading=12)),
        Paragraph("TOTAL QTY", lbl_q), Paragraph(f"{total_qty:.0f}", val_q),
        Paragraph("TOTAL", lbl_q), Paragraph(f"₹ {total_amount:,.0f}", val_q),
    ]], colWidths=[78 * mm, 28 * mm, 22 * mm, 24 * mm, 34 * mm])
    bottom.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("BOX", (1, 0), (2, 0), 0.6, COL_GRID),
                                ("LINEAFTER", (1, 0), (1, 0), 0.6, COL_GRID),
                                ("BOX", (3, 0), (4, 0), 0.6, COL_GRID),
                                ("LINEAFTER", (3, 0), (3, 0), 0.6, COL_GRID),
                                ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(bottom)
    story.append(Spacer(1, 4 * mm))
    foot = co["note2"] + (f"      Follow us on (IG)  {co['instagram']}" if co["instagram"] else "")
    story.append(Paragraph(foot, ParagraphStyle("f", fontName=FONT, fontSize=8.5, alignment=TA_LEFT, textColor=COL_MUTED)))

    wm = _watermark(co)
    doc.build(story, onFirstPage=wm, onLaterPages=wm)
    return buf.getvalue()
