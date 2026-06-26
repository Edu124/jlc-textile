"""Seed default reference data + company letterhead settings (idempotent)."""
from .models import Unit, ProductCategory, Setting


def seed_defaults(db):
    if db.query(Unit).count() == 0:
        for name, abbr in [("Meters", "m"), ("Kilograms", "kg"), ("Pieces", "pcs"),
                           ("Rolls", "rolls"), ("Liters", "L"), ("Yards", "yd"),
                           ("Grams", "g"), ("Dozens", "doz")]:
            db.add(Unit(name=name, abbreviation=abbr))

    if db.query(ProductCategory).count() == 0:
        for name in ["Shirts", "Trousers", "Fabric Rolls", "Sarees", "Suits", "Other"]:
            db.add(ProductCategory(name=name))

    defaults = {
        "company_name": "Jai Laxmi Creation",
        "company_tagline": "MFG. OF EXCLUSIVE SALWAR KAMEEZ",
        "company_slogan": "Your Style is Important",
        "address": "Shop No. 174, Main Bazar, Siru Chowk, Ulhasnagar - 421 002.",
        "gst_number": "27ADTPG1220E1ZW",
        "phone": "9158707077",
        "email": "jailaxmicreation174@gmail.com",
        "instagram": "jlc.jai.laxmi.creation",
        "footer_note1": "For Sizes XL, XXL, 3XL Extra Charges 25-50 Rs.",
        "footer_note2": "Goods Once Sold will not be taken back.",
        "logo_mode": "vector",
    }
    for key, val in defaults.items():
        if db.query(Setting).filter_by(key=key).first() is None:
            db.add(Setting(key=key, value=val))

    db.commit()
