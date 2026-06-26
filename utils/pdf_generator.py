import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Flowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import core.database as db


# ── Unicode font registration (so ₹ and symbols render) ─────────────────────
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def _register_fonts():
    global FONT, FONT_BOLD
    win = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    candidates = [
        ("JLCFont", "arial.ttf", "JLCFont-Bold", "arialbd.ttf"),
        ("JLCFont", "segoeui.ttf", "JLCFont-Bold", "segoeuib.ttf"),
        ("JLCFont", "calibri.ttf", "JLCFont-Bold", "calibrib.ttf"),
    ]
    for reg, rf, regb, bf in candidates:
        rp, bp = os.path.join(win, rf), os.path.join(win, bf)
        if os.path.exists(rp) and os.path.exists(bp):
            try:
                pdfmetrics.registerFont(TTFont(reg, rp))
                pdfmetrics.registerFont(TTFont(regb, bp))
                FONT, FONT_BOLD = reg, regb
                return
            except Exception:
                continue


_register_fonts()


# Script font for the cursive "Jlc" logo mark.
SCRIPT_FONT = FONT_BOLD


def _register_script():
    global SCRIPT_FONT
    win = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    for fn in ["segoescb.ttf", "segoesc.ttf", "Inkfree.ttf", "Gabriola.ttf"]:
        p = os.path.join(win, fn)
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont("JLCScript", p))
                SCRIPT_FONT = "JLCScript"
                return
            except Exception:
                continue


_register_script()


# ── Colors ──────────────────────────────────────────────────────────────────
COL_TEXT   = colors.HexColor("#1a1a1a")
COL_MUTED  = colors.HexColor("#555555")
COL_LINE   = colors.HexColor("#000000")
COL_GRID   = colors.HexColor("#333333")
COL_HEADBG = colors.HexColor("#ECECEC")
COL_WHITE  = colors.white


def _company() -> dict:
    return {
        "name":     db.get_setting("company_name", "Jai Laxmi Creation"),
        "tagline":  db.get_setting("company_tagline", "MFG. OF EXCLUSIVE SALWAR KAMEEZ"),
        "slogan":   db.get_setting("company_slogan", "Your Style is Important"),
        "address":  db.get_setting("address", ""),
        "gst":      db.get_setting("gst_number", ""),
        "phone":    db.get_setting("phone", ""),
        "email":    db.get_setting("email", ""),
        "instagram": db.get_setting("instagram", ""),
        "note1":    db.get_setting("footer_note1", "For Sizes XL, XXL, 3XL Extra Charges 25-50 Rs."),
        "note2":    db.get_setting("footer_note2", "Goods Once Sold will not be taken back."),
    }


# ── Swastika (drawn, no font dependency) ─────────────────────────────────────
class Swastika(Flowable):
    def __init__(self, size=13):
        Flowable.__init__(self)
        self.size = size
        self.width = size
        self.height = size

    def draw(self):
        c = self.canv
        s = self.size
        u = s / 4.0
        cx = cy = s / 2.0
        c.setLineWidth(1.2)
        c.setStrokeColor(COL_LINE)
        c.line(cx, cy - 2 * u, cx, cy + 2 * u)          # vertical
        c.line(cx - 2 * u, cy, cx + 2 * u, cy)          # horizontal
        c.line(cx, cy + 2 * u, cx + 2 * u, cy + 2 * u)  # top -> right
        c.line(cx + 2 * u, cy, cx + 2 * u, cy - 2 * u)  # right -> down
        c.line(cx, cy - 2 * u, cx - 2 * u, cy - 2 * u)  # bottom -> left
        c.line(cx - 2 * u, cy, cx - 2 * u, cy + 2 * u)  # left -> up


# ── Logo monogram (fallback when no logo image is set) ───────────────────────
class Monogram(Flowable):
    def __init__(self, size=40):
        Flowable.__init__(self)
        self.size = size
        self.width = size
        self.height = size

    def draw(self):
        c = self.canv
        s = self.size
        c.setLineWidth(1.1)
        c.setStrokeColor(COL_TEXT)
        c.ellipse(1, 1, s - 1, s - 1)
        c.setFillColor(COL_TEXT)
        # Slanted, script-like monogram
        c.saveState()
        try:
            c.setFont("Helvetica-BoldOblique", s * 0.46)
        except Exception:
            c.setFont(FONT_BOLD, s * 0.46)
        c.drawCentredString(s / 2.0, s / 2.0 - s * 0.15, "Jlc")
        c.setFont(FONT, s * 0.13)
        c.drawString(s * 0.70, s * 0.62, "™")  # small TM
        c.restoreState()


class VectorLogo(Flowable):
    """Crisp vector recreation of the Jlc logo: a swoosh arc, the cursive
    'Jlc' in a script font, and the tagline curved along the bottom."""
    def __init__(self, w=104, h=74):
        Flowable.__init__(self)
        self.width = w
        self.height = h

    def draw(self):
        import math
        c = self.canv
        W, H = self.width, self.height
        # Swoosh arc across the top
        c.setLineWidth(1.8)
        c.setStrokeColor(COL_TEXT)
        path = c.beginPath()
        path.arc(W * 0.04, H * 0.18, W * 0.96, H * 1.02, 20, 140)
        c.drawPath(path, stroke=1, fill=0)
        # Cursive Jlc
        c.setFillColor(COL_TEXT)
        c.setFont(SCRIPT_FONT, H * 0.50)
        c.drawCentredString(W / 2.0, H * 0.30, "Jlc")
        # Curved tagline
        text = db.get_setting("company_slogan", "Your Style is Important")
        c.setFont(FONT, H * 0.085)
        c.setFillColor(COL_MUTED)
        R = W * 0.47
        ccx, ccy = W / 2.0, H * 0.66
        n = len(text)
        start, end = 233, 307
        for i, ch in enumerate(text):
            ang = start + (end - start) * i / max(1, n - 1)
            r = math.radians(ang)
            x = ccx + R * math.cos(r)
            y = ccy + R * math.sin(r)
            c.saveState()
            c.translate(x, y)
            c.rotate(ang + 90)
            c.drawCentredString(0, 0, ch)
            c.restoreState()


def _logo_cell(app_dir: str):
    """Return the logo flowable for the header.
    logo_mode = 'vector' (drawn), 'image' (uploaded file), else monogram."""
    slogan = db.get_setting("company_slogan", "Your Style is Important")
    slogan_p = Paragraph(slogan, ParagraphStyle(
        "lt", fontName=FONT, fontSize=6.5, alignment=TA_CENTER,
        textColor=COL_MUTED, leading=8, spaceBefore=3))

    mode = db.get_setting("logo_mode", "vector")
    path = db.get_setting("logo_path", "")

    if mode == "image" and path and os.path.exists(path):
        try:
            from reportlab.lib.utils import ImageReader
            from reportlab.platypus import Image
            iw, ih = ImageReader(path).getSize()
            max_w, max_h = 34 * mm, 20 * mm
            ratio = min(max_w / iw, max_h / ih)
            img = Image(path, width=iw * ratio, height=ih * ratio)
            img.hAlign = "CENTER"
            return [img, slogan_p]
        except Exception:
            pass

    if mode == "vector":
        return [VectorLogo()]   # tagline is drawn inside the vector

    return [Monogram(40), slogan_p]


def _make_watermark(app_dir: str):
    """Return an onPage callback that draws a faint centered watermark
    behind the form content — the logo image if set, else the company name."""
    logo = db.get_setting("logo_path", "")
    mode = db.get_setting("logo_mode", "vector")
    name = db.get_setting("company_name", "Jai Laxmi Creation")

    def draw(c, doc):
        w, h = A4
        c.saveState()
        try:
            if mode == "image" and logo and os.path.exists(logo):
                from reportlab.lib.utils import ImageReader
                img = ImageReader(logo)
                iw, ih = img.getSize()
                tw = 100 * mm
                th = tw * ih / iw
                c.setFillAlpha(0.06)
                c.drawImage(img, (w - tw) / 2.0, (h - th) / 2.0, tw, th,
                            mask="auto", preserveAspectRatio=True)
            else:
                # Faint cursive "Jlc" watermark (matches the vector logo).
                # setFillColor resets alpha, so set alpha AFTER the color.
                c.setFillColor(colors.black)
                c.setFillAlpha(0.06)
                c.translate(w / 2.0, h / 2.0)
                c.setFont(SCRIPT_FONT, 150)
                c.drawCentredString(0, -10, "Jlc")
                c.setFont(FONT_BOLD, 22)
                c.drawCentredString(0, -85, name)
        except Exception:
            pass
        c.restoreState()

    return draw


# ═══════════════════════════════════════════════════════════════════════════
#  SALES — Jai Laxmi Creation Order Form
# ═══════════════════════════════════════════════════════════════════════════

def generate_sales_bill(bill_id: int, app_dir: str) -> str:
    bill = db.fetchone("SELECT * FROM sales_bills WHERE id=?", (bill_id,))
    items = db.fetchall(
        """SELECT design_no, qty_m, qty_l, qty_xl, qty_xxl, qty_mxxl, row_qty, mrp
           FROM sales_bill_items WHERE bill_id=? ORDER BY id""",
        (bill_id,)
    )
    customer = db.fetchone("SELECT * FROM customers WHERE id=?", (bill["customer_id"],))
    co = _company()

    out_dir = os.path.join(app_dir, "bills", "sales")
    os.makedirs(out_dir, exist_ok=True)
    filename = f"{bill['bill_number'].replace('/', '_')}.pdf"
    path = os.path.join(out_dir, filename)

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=11 * mm, rightMargin=11 * mm,
        topMargin=10 * mm, bottomMargin=12 * mm
    )

    s_center = ParagraphStyle("c", fontName=FONT, fontSize=9, alignment=TA_CENTER,
                              textColor=COL_TEXT, leading=12)
    s_company = ParagraphStyle("co", fontName=FONT_BOLD, fontSize=30, alignment=TA_CENTER,
                               textColor=COL_TEXT, leading=32)
    s_tag = ParagraphStyle("tg", fontName=FONT_BOLD, fontSize=10.5, alignment=TA_CENTER,
                           textColor=COL_TEXT, leading=13)
    s_small = ParagraphStyle("sm", fontName=FONT, fontSize=9, alignment=TA_CENTER,
                             textColor=COL_TEXT, leading=12)
    s_field = ParagraphStyle("fl", fontName=FONT, fontSize=9.5, textColor=COL_TEXT, leading=13)
    s_field_b = ParagraphStyle("flb", fontName=FONT_BOLD, fontSize=9.5, textColor=COL_TEXT, leading=13)

    story = []

    # ── Top line: swastika centered, mobile right ──
    top = Table(
        [["",
          Swastika(13),
          Paragraph(f"Mob.: {co['phone']}", ParagraphStyle("mob", fontName=FONT_BOLD,
                    fontSize=9, alignment=TA_RIGHT, textColor=COL_TEXT))]],
        colWidths=[62 * mm, 64 * mm, 62 * mm]
    )
    top.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(top)
    story.append(Paragraph("ORDER FORM", ParagraphStyle(
        "of", fontName=FONT_BOLD, fontSize=11, alignment=TA_CENTER,
        textColor=COL_TEXT, spaceBefore=1, spaceAfter=2)))

    # ── Company header: logo far-left, name+details CENTERED on the page ──
    # Equal-width left (logo) and right (spacer) columns keep the centre
    # block centred across the whole page, exactly like the printed form.
    center_block = [
        Paragraph(co["name"], s_company),
        Paragraph(co["tagline"], s_tag),
        Paragraph(co["address"], s_small),
        Paragraph(f"GST No.: {co['gst']}  |  Email : {co['email']}", s_small),
    ]
    header = Table(
        [[_logo_cell(app_dir), center_block, ""]],
        colWidths=[38 * mm, 112 * mm, 38 * mm]
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(header)
    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=COL_LINE))
    story.append(Spacer(1, 3 * mm))

    # ── Party / meta block (4-column, underlined values) ──
    addr = (customer["address"] or "") if customer else ""
    addr1, addr2 = (addr.split("\n", 1) + [""])[:2] if addr else ("", "")
    cust_name = customer["name"] if customer else ""
    cust_phone = (customer["phone"] or "") if customer else ""
    cust_gst = (customer["gst_number"] or "") if customer else ""

    def fld(label):
        return Paragraph(label, s_field_b)

    def val(text):
        return Paragraph(text or "", s_field)

    meta = Table(
        [
            [fld("Party"),   val(cust_name),  fld("No."),           val(bill["bill_number"])],
            [fld("Contact"), val(cust_phone), fld("Date"),          val(_fmt_date(bill["bill_date"]))],
            [fld("Add."),    val(addr1),      fld("Delivery Date"), val(_fmt_date(bill["delivery_date"]))],
            [fld(""),        val(addr2),      fld("Transport"),     val(bill["transport"])],
            [fld("GST No."), val(cust_gst),   fld("Agent"),         val(bill["agent"])],
        ],
        colWidths=[20 * mm, 90 * mm, 28 * mm, 50 * mm]
    )
    meta.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (1, 0), (1, -1), 0.6, COL_MUTED),
        ("LINEBELOW", (3, 0), (3, -1), 0.6, COL_MUTED),
    ]))
    story.append(meta)
    story.append(Spacer(1, 3 * mm))

    # ── Size grid ──
    col_w = [10 * mm, 42 * mm, 16 * mm, 16 * mm, 16 * mm, 16 * mm,
             20 * mm, 18 * mm, 32 * mm]
    head = ["Sr.", "Design No.", "M", "L", "XL", "XXL", "M-XXL", "", "MRP"]
    data = [head]

    def z(v):
        return str(int(v)) if v else ""

    total_qty = 0
    DISPLAY_ROWS = 20
    for i in range(DISPLAY_ROWS):
        if i < len(items):
            it = items[i]
            total_qty += it["row_qty"] or 0
            data.append([
                str(i + 1), it["design_no"] or "",
                z(it["qty_m"]), z(it["qty_l"]), z(it["qty_xl"]),
                z(it["qty_xxl"]), z(it["qty_mxxl"]), "",
                f"{it['mrp']:,.0f}" if it["mrp"] else ""
            ])
        else:
            data.append([str(i + 1), "", "", "", "", "", "", "", ""])

    grid = Table(data, colWidths=col_w, repeatRows=1)
    grid.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, 0), 9.5),
        ("BACKGROUND", (0, 0), (-1, 0), COL_HEADBG),
        ("FONTNAME", (0, 1), (-1, -1), FONT),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.6, COL_GRID),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (1, 0), (1, -1), 6),
    ]))
    story.append(grid)

    # ── Bottom: notes + TOTAL QUANTITY ──
    bottom = Table(
        [[Paragraph(co["note1"], ParagraphStyle("n1", fontName=FONT_BOLD, fontSize=9,
                    textColor=COL_TEXT, leading=12)),
          Paragraph("TOTAL QUANTITY", ParagraphStyle("tq", fontName=FONT_BOLD, fontSize=10,
                    alignment=TA_CENTER, textColor=COL_TEXT)),
          Paragraph(f"{total_qty:.0f}", ParagraphStyle("tqv", fontName=FONT_BOLD, fontSize=11,
                    alignment=TA_CENTER, textColor=COL_TEXT))]],
        colWidths=[112 * mm, 42 * mm, 32 * mm]
    )
    bottom.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (1, 0), (2, 0), 0.6, COL_GRID),
        ("LINEAFTER", (1, 0), (1, 0), 0.6, COL_GRID),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (0, 0), 2),
    ]))
    story.append(bottom)
    story.append(Spacer(1, 4 * mm))

    # ── Footer ──
    foot_txt = co["note2"]
    if co["instagram"]:
        foot_txt += f"      Follow us on (IG)  {co['instagram']}"
    story.append(Paragraph(foot_txt, ParagraphStyle(
        "ft", fontName=FONT, fontSize=8.5, alignment=TA_LEFT, textColor=COL_MUTED)))

    wm = _make_watermark(app_dir)
    doc.build(story, onFirstPage=wm, onLaterPages=wm)
    db.execute("UPDATE sales_bills SET pdf_path=? WHERE id=?", (path, bill_id))
    return path


def _fmt_date(d: str) -> str:
    if not d:
        return ""
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return d


# ═══════════════════════════════════════════════════════════════════════════
#  PURCHASE BILL (kept; uses Unicode font for ₹)
# ═══════════════════════════════════════════════════════════════════════════

def generate_purchase_bill(bill_id: int, app_dir: str) -> str:
    bill = db.fetchone("SELECT * FROM purchase_bills WHERE id=?", (bill_id,))
    items = db.fetchall(
        """SELECT pbi.quantity, rmt.name as material, u.abbreviation as unit,
                  pbi.rate, pbi.amount
           FROM purchase_bill_items pbi
           JOIN raw_material_types rmt ON rmt.id=pbi.material_type_id
           LEFT JOIN units u ON u.id=pbi.unit_id
           WHERE pbi.bill_id=?""",
        (bill_id,)
    )
    supplier = db.fetchone("SELECT * FROM suppliers WHERE id=?", (bill["supplier_id"],))
    co = _company()

    out_dir = os.path.join(app_dir, "bills", "purchase")
    os.makedirs(out_dir, exist_ok=True)
    filename = f"{bill['bill_number'].replace('/', '_')}.pdf"
    path = os.path.join(out_dir, filename)

    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=20 * mm)
    accent = colors.HexColor("#37474f")
    border = colors.HexColor("#cccccc")

    s_company = ParagraphStyle("co", fontName=FONT_BOLD, fontSize=18, textColor=COL_TEXT)
    s_sub = ParagraphStyle("sub", fontName=FONT, fontSize=9, textColor=COL_MUTED, leading=12)
    s_title = ParagraphStyle("ti", fontName=FONT_BOLD, fontSize=13, alignment=TA_RIGHT, textColor=accent)
    s_meta = ParagraphStyle("me", fontName=FONT, fontSize=9, alignment=TA_RIGHT, textColor=COL_TEXT, leading=14)
    s_party = ParagraphStyle("pa", fontName=FONT, fontSize=10, textColor=COL_TEXT, leading=14)
    s_sec = ParagraphStyle("se", fontName=FONT_BOLD, fontSize=8, textColor=COL_MUTED, spaceAfter=3)

    story = []
    head = Table([[
        [Paragraph(co["name"], s_company),
         Paragraph(co["address"].replace("\n", "<br/>"), s_sub),
         Paragraph(f"Ph: {co['phone']}  |  GST: {co['gst']}", s_sub)],
        [Paragraph("PURCHASE BILL", s_title),
         Paragraph(f"Bill No: <b>{bill['bill_number']}</b><br/>Date: <b>{_fmt_date(bill['bill_date'])}</b>", s_meta)]
    ]], colWidths=[95 * mm, 85 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(head)
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=border))
    story.append(Spacer(1, 4 * mm))

    sup = dict(supplier) if supplier else {}
    info = f"<b>{sup.get('name','')}</b><br/>"
    if sup.get("address"): info += sup["address"].replace("\n", "<br/>") + "<br/>"
    if sup.get("phone"): info += f"Ph: {sup['phone']}<br/>"
    if sup.get("gst_number"): info += f"GSTIN: {sup['gst_number']}"
    party = Table([[Paragraph("SUPPLIER", s_sec)], [Paragraph(info, s_party)]], colWidths=[180 * mm])
    party.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story.append(party)
    story.append(Spacer(1, 5 * mm))

    rows = [["#", "Material", "Qty", "Unit", "Rate (₹)", "Amount (₹)"]]
    for i, it in enumerate(items, 1):
        rows.append([str(i), it["material"], f"{it['quantity']:.2f}", it["unit"] or "",
                     f"{it['rate']:,.2f}", f"{it['amount']:,.2f}"])
    tbl = Table(rows, colWidths=[10 * mm, 65 * mm, 20 * mm, 20 * mm, 30 * mm, 35 * mm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("TEXTCOLOR", (0, 0), (-1, 0), COL_WHITE),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (1, -1), "LEFT"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, border),
    ]
    for i in range(1, len(rows)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f8f9fa")))
    tbl.setStyle(TableStyle(style))
    story.append(tbl)
    story.append(Spacer(1, 4 * mm))

    trows = [["Subtotal", f"₹  {bill['subtotal']:,.2f}"]]
    if (bill["gst_type"] or "none") != "none" and bill["gst_percent"]:
        if bill["gst_type"] == "cgst_sgst":
            half = bill["gst_amount"] / 2
            trows.append([f"CGST ({bill['gst_percent']/2:.1f}%)", f"₹  {half:,.2f}"])
            trows.append([f"SGST ({bill['gst_percent']/2:.1f}%)", f"₹  {half:,.2f}"])
        else:
            trows.append([f"IGST ({bill['gst_percent']:.1f}%)", f"₹  {bill['gst_amount']:,.2f}"])
    trows.append(["TOTAL", f"₹  {bill['total_amount']:,.2f}"])
    tt = Table(trows, colWidths=[40 * mm, 40 * mm], hAlign="RIGHT")
    tt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -2), FONT),
        ("FONTNAME", (0, -1), (-1, -1), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTSIZE", (0, -1), (-1, -1), 11),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEABOVE", (0, -1), (-1, -1), 1, border),
    ]))
    story.append(tt)
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("Thank you for your business. This is a computer-generated bill.",
                           ParagraphStyle("ft", fontName=FONT, fontSize=8, alignment=TA_CENTER, textColor=COL_MUTED)))

    doc.build(story)
    db.execute("UPDATE purchase_bills SET pdf_path=? WHERE id=?", (path, bill_id))
    return path
