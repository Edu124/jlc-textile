import sqlite3
import os
from datetime import datetime, date, timedelta

_conn: sqlite3.Connection = None
_db_path: str = None


def init(db_path: str):
    global _conn, _db_path
    _db_path = db_path
    _conn = sqlite3.connect(db_path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.execute("PRAGMA foreign_keys=ON")
    _create_schema()


def get_conn() -> sqlite3.Connection:
    return _conn


def close():
    global _conn
    if _conn:
        _conn.close()
        _conn = None


def _create_schema():
    c = _conn
    c.executescript("""
    CREATE TABLE IF NOT EXISTS settings (
        key   TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS units (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT NOT NULL UNIQUE,
        abbreviation TEXT NOT NULL,
        created_at   TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS suppliers (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT NOT NULL,
        phone      TEXT,
        email      TEXT,
        address    TEXT,
        gst_number TEXT,
        is_active  INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS customers (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT NOT NULL,
        phone      TEXT,
        email      TEXT,
        address    TEXT,
        gst_number TEXT,
        is_active  INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS raw_material_types (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        name                TEXT NOT NULL UNIQUE,
        unit_id             INTEGER REFERENCES units(id),
        low_stock_threshold REAL DEFAULT 0,
        description         TEXT,
        created_at          TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS raw_material_stock (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        material_type_id INTEGER UNIQUE REFERENCES raw_material_types(id),
        quantity         REAL DEFAULT 0,
        avg_rate         REAL DEFAULT 0,
        last_updated     TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS raw_material_transactions (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        material_type_id INTEGER REFERENCES raw_material_types(id),
        transaction_type TEXT,
        quantity         REAL,
        rate             REAL,
        reference_id     INTEGER,
        reference_type   TEXT,
        notes            TEXT,
        created_at       TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS product_categories (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT NOT NULL UNIQUE,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS products (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        category_id INTEGER REFERENCES product_categories(id),
        unit_id     INTEGER REFERENCES units(id),
        sale_rate   REAL DEFAULT 0,
        description TEXT,
        image_path  TEXT,
        is_active   INTEGER DEFAULT 1,
        created_at  TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS product_bom (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id         INTEGER REFERENCES products(id),
        material_type_id   INTEGER REFERENCES raw_material_types(id),
        quantity_required  REAL,
        notes              TEXT
    );

    CREATE TABLE IF NOT EXISTS production_batches (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_number  TEXT UNIQUE,
        product_id    INTEGER REFERENCES products(id),
        quantity      REAL,
        order_id      INTEGER,
        current_stage TEXT DEFAULT 'Cutting',
        notes         TEXT,
        started_at    TEXT DEFAULT (datetime('now','localtime')),
        completed_at  TEXT
    );

    CREATE TABLE IF NOT EXISTS batch_stage_history (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id   INTEGER REFERENCES production_batches(id),
        stage      TEXT,
        notes      TEXT,
        changed_at TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS finished_goods_stock (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id   INTEGER UNIQUE REFERENCES products(id),
        quantity     REAL DEFAULT 0,
        last_updated TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS finished_goods_transactions (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id       INTEGER REFERENCES products(id),
        transaction_type TEXT,
        quantity         REAL,
        reference_id     INTEGER,
        reference_type   TEXT,
        created_at       TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS orders (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number  TEXT UNIQUE,
        customer_id   INTEGER REFERENCES customers(id),
        status        TEXT DEFAULT 'Received',
        total_amount  REAL DEFAULT 0,
        notes         TEXT,
        delivery_date TEXT,
        created_at    TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS order_items (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id   INTEGER REFERENCES orders(id) ON DELETE CASCADE,
        product_id INTEGER REFERENCES products(id),
        quantity   REAL,
        rate       REAL,
        amount     REAL
    );

    CREATE TABLE IF NOT EXISTS purchase_bills (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_number  TEXT UNIQUE,
        supplier_id  INTEGER REFERENCES suppliers(id),
        bill_date    TEXT,
        subtotal     REAL DEFAULT 0,
        gst_type     TEXT DEFAULT 'none',
        gst_percent  REAL DEFAULT 0,
        gst_amount   REAL DEFAULT 0,
        total_amount REAL DEFAULT 0,
        notes        TEXT,
        pdf_path     TEXT,
        created_at   TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS purchase_bill_items (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id          INTEGER REFERENCES purchase_bills(id) ON DELETE CASCADE,
        material_type_id INTEGER REFERENCES raw_material_types(id),
        quantity         REAL,
        unit_id          INTEGER REFERENCES units(id),
        rate             REAL,
        amount           REAL
    );

    CREATE TABLE IF NOT EXISTS sales_bills (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_number   TEXT UNIQUE,
        customer_id   INTEGER REFERENCES customers(id),
        order_id      INTEGER,
        bill_date     TEXT,
        delivery_date TEXT,
        transport     TEXT,
        agent         TEXT,
        subtotal      REAL DEFAULT 0,
        gst_type      TEXT DEFAULT 'none',
        gst_percent   REAL DEFAULT 0,
        gst_amount    REAL DEFAULT 0,
        total_qty     REAL DEFAULT 0,
        total_amount  REAL DEFAULT 0,
        notes         TEXT,
        pdf_path      TEXT,
        created_at    TEXT DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS sales_bill_items (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id    INTEGER REFERENCES sales_bills(id) ON DELETE CASCADE,
        design_no  TEXT,
        qty_m      REAL DEFAULT 0,
        qty_l      REAL DEFAULT 0,
        qty_xl     REAL DEFAULT 0,
        qty_xxl    REAL DEFAULT 0,
        qty_mxxl   REAL DEFAULT 0,
        row_qty    REAL DEFAULT 0,
        mrp        REAL DEFAULT 0,
        amount     REAL DEFAULT 0,
        product_id INTEGER REFERENCES products(id),
        quantity   REAL,
        unit_id    INTEGER REFERENCES units(id),
        rate       REAL
    );

    CREATE TABLE IF NOT EXISTS ai_designs (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        name              TEXT,
        prompt            TEXT,
        style             TEXT,
        source_image_path TEXT,
        result_image_path TEXT,
        created_at        TEXT DEFAULT (datetime('now','localtime'))
    );
    """)
    _migrate()
    _seed_defaults()
    _conn.commit()


def _migrate():
    """Add columns introduced after a DB was first created (SQLite ADD COLUMN)."""
    def cols(table):
        return {r["name"] for r in _conn.execute(f"PRAGMA table_info({table})")}

    sb = cols("sales_bills")
    for name, decl in [("delivery_date", "TEXT"), ("transport", "TEXT"),
                       ("agent", "TEXT"), ("total_qty", "REAL DEFAULT 0")]:
        if name not in sb:
            _conn.execute(f"ALTER TABLE sales_bills ADD COLUMN {name} {decl}")

    sbi = cols("sales_bill_items")
    for name, decl in [("design_no", "TEXT"), ("qty_m", "REAL DEFAULT 0"),
                       ("qty_l", "REAL DEFAULT 0"), ("qty_xl", "REAL DEFAULT 0"),
                       ("qty_xxl", "REAL DEFAULT 0"), ("qty_mxxl", "REAL DEFAULT 0"),
                       ("row_qty", "REAL DEFAULT 0"), ("mrp", "REAL DEFAULT 0")]:
        if name not in sbi:
            _conn.execute(f"ALTER TABLE sales_bill_items ADD COLUMN {name} {decl}")
    _conn.commit()


def _seed_defaults():
    rows = _conn.execute("SELECT COUNT(*) FROM units").fetchone()[0]
    if rows == 0:
        _conn.executemany(
            "INSERT OR IGNORE INTO units (name, abbreviation) VALUES (?,?)",
            [("Meters", "m"), ("Kilograms", "kg"), ("Pieces", "pcs"),
             ("Rolls", "rolls"), ("Liters", "L"), ("Yards", "yd"),
             ("Grams", "g"), ("Dozens", "doz")]
        )
    cats = _conn.execute("SELECT COUNT(*) FROM product_categories").fetchone()[0]
    if cats == 0:
        _conn.executemany(
            "INSERT OR IGNORE INTO product_categories (name) VALUES (?)",
            [("Shirts",), ("Trousers",), ("Fabric Rolls",),
             ("Sarees",), ("Suits",), ("Other",)]
        )

    # Company letterhead defaults (Jai Laxmi Creation) — only if not set yet.
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
        row = _conn.execute("SELECT 1 FROM settings WHERE key=?", (key,)).fetchone()
        if row is None:
            _conn.execute("INSERT INTO settings (key, value) VALUES (?,?)", (key, val))


# ── Generic helpers ──────────────────────────────────────────────────────────

def fetchall(sql: str, params=()):
    return _conn.execute(sql, params).fetchall()


def fetchone(sql: str, params=()):
    return _conn.execute(sql, params).fetchone()


def execute(sql: str, params=()):
    cur = _conn.execute(sql, params)
    _conn.commit()
    return cur


def executemany(sql: str, params_list):
    cur = _conn.executemany(sql, params_list)
    _conn.commit()
    return cur


# ── Settings ─────────────────────────────────────────────────────────────────

def get_setting(key: str, default="") -> str:
    row = fetchone("SELECT value FROM settings WHERE key=?", (key,))
    return row[0] if row else default


def set_setting(key: str, value: str):
    execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (key, value))


# ── Auto-number helpers ───────────────────────────────────────────────────────

def next_bill_number(prefix: str, table: str, col: str = "bill_number") -> str:
    year = datetime.now().strftime("%y%m")
    like = f"{prefix}/{year}/%"
    row = fetchone(f"SELECT MAX({col}) FROM {table} WHERE {col} LIKE ?", (like,))
    if row and row[0]:
        seq = int(row[0].split("/")[-1]) + 1
    else:
        seq = 1
    return f"{prefix}/{year}/{seq:04d}"


def next_batch_number() -> str:
    year = datetime.now().strftime("%y%m")
    like = f"BATCH/{year}/%"
    row = fetchone("SELECT MAX(batch_number) FROM production_batches WHERE batch_number LIKE ?", (like,))
    if row and row[0]:
        seq = int(row[0].split("/")[-1]) + 1
    else:
        seq = 1
    return f"BATCH/{year}/{seq:04d}"


def next_order_number() -> str:
    year = datetime.now().strftime("%y%m")
    like = f"ORD/{year}/%"
    row = fetchone("SELECT MAX(order_number) FROM orders WHERE order_number LIKE ?", (like,))
    if row and row[0]:
        seq = int(row[0].split("/")[-1]) + 1
    else:
        seq = 1
    return f"ORD/{year}/{seq:04d}"


# ── Stock helpers ─────────────────────────────────────────────────────────────

def adjust_raw_stock(material_type_id: int, qty_delta: float, rate: float = 0):
    row = fetchone("SELECT id, quantity, avg_rate FROM raw_material_stock WHERE material_type_id=?",
                   (material_type_id,))
    if row:
        old_qty = row["quantity"]
        old_rate = row["avg_rate"]
        if qty_delta > 0 and rate > 0:
            new_qty = old_qty + qty_delta
            new_rate = ((old_qty * old_rate) + (qty_delta * rate)) / new_qty if new_qty else rate
        else:
            new_qty = max(0, old_qty + qty_delta)
            new_rate = old_rate
        execute(
            "UPDATE raw_material_stock SET quantity=?, avg_rate=?, last_updated=datetime('now','localtime') WHERE material_type_id=?",
            (new_qty, new_rate, material_type_id)
        )
    else:
        execute(
            "INSERT INTO raw_material_stock (material_type_id, quantity, avg_rate) VALUES (?,?,?)",
            (material_type_id, max(0, qty_delta), rate)
        )


def adjust_finished_stock(product_id: int, qty_delta: float):
    row = fetchone("SELECT id, quantity FROM finished_goods_stock WHERE product_id=?", (product_id,))
    if row:
        new_qty = max(0, row["quantity"] + qty_delta)
        execute(
            "UPDATE finished_goods_stock SET quantity=?, last_updated=datetime('now','localtime') WHERE product_id=?",
            (new_qty, product_id)
        )
    else:
        execute(
            "INSERT INTO finished_goods_stock (product_id, quantity) VALUES (?,?)",
            (product_id, max(0, qty_delta))
        )


# ── Dashboard stats ───────────────────────────────────────────────────────────

def dashboard_stats() -> dict:
    raw_val = fetchone(
        "SELECT COALESCE(SUM(s.quantity * s.avg_rate),0) FROM raw_material_stock s"
    )[0]
    fg_qty = fetchone(
        "SELECT COALESCE(SUM(quantity),0) FROM finished_goods_stock"
    )[0]
    pending_orders = fetchone(
        "SELECT COUNT(*) FROM orders WHERE status NOT IN ('Delivered','Cancelled')"
    )[0]
    today = datetime.now().strftime("%Y-%m-%d")
    today_sales = fetchone(
        "SELECT COALESCE(SUM(total_amount),0) FROM sales_bills WHERE bill_date=?", (today,)
    )[0]
    low_stock = fetchall(
        """SELECT rmt.name, rms.quantity, rmt.low_stock_threshold, u.abbreviation
           FROM raw_material_stock rms
           JOIN raw_material_types rmt ON rmt.id=rms.material_type_id
           LEFT JOIN units u ON u.id=rmt.unit_id
           WHERE rmt.low_stock_threshold > 0 AND rms.quantity <= rmt.low_stock_threshold"""
    )
    recent_orders = fetchall(
        """SELECT o.order_number, c.name as customer, o.status, o.total_amount, o.created_at
           FROM orders o JOIN customers c ON c.id=o.customer_id
           ORDER BY o.id DESC LIMIT 5"""
    )
    return {
        "raw_stock_value": raw_val,
        "finished_goods_qty": fg_qty,
        "pending_orders": pending_orders,
        "today_sales": today_sales,
        "low_stock": low_stock,
        "recent_orders": recent_orders,
    }


# ── Dashboard analytics ───────────────────────────────────────────────────────

def dashboard_analytics() -> dict:
    month = datetime.now().strftime("%Y-%m")

    month_sales = fetchone(
        "SELECT COALESCE(SUM(total_amount),0) FROM sales_bills WHERE substr(bill_date,1,7)=?",
        (month,))[0]
    month_qty = fetchone(
        "SELECT COALESCE(SUM(total_qty),0) FROM sales_bills WHERE substr(bill_date,1,7)=?",
        (month,))[0]
    month_bills = fetchone(
        "SELECT COUNT(*) FROM sales_bills WHERE substr(bill_date,1,7)=?", (month,))[0]
    month_orders = fetchone(
        "SELECT COUNT(*) FROM orders WHERE substr(created_at,1,7)=?", (month,))[0]
    month_purchases = fetchone(
        "SELECT COALESCE(SUM(total_amount),0) FROM purchase_bills WHERE substr(bill_date,1,7)=?",
        (month,))[0]
    avg_order_value = (month_sales / month_bills) if month_bills else 0

    # ── Sales trend: last 30 days (fill empty days with 0) ──
    start = (date.today() - timedelta(days=29)).isoformat()
    rows = fetchall(
        """SELECT bill_date, COALESCE(SUM(total_amount),0) amt
           FROM sales_bills WHERE bill_date >= ? GROUP BY bill_date""", (start,))
    by_day = {r["bill_date"]: r["amt"] for r in rows}
    trend = []
    for i in range(29, -1, -1):
        d = date.today() - timedelta(days=i)
        trend.append((d.strftime("%d/%m"), by_day.get(d.isoformat(), 0)))

    # ── Size mix ──
    sz = fetchone(
        """SELECT COALESCE(SUM(qty_m),0) m, COALESCE(SUM(qty_l),0) l,
                  COALESCE(SUM(qty_xl),0) xl, COALESCE(SUM(qty_xxl),0) xxl,
                  COALESCE(SUM(qty_mxxl),0) mx FROM sales_bill_items""")
    size_mix = [("M", sz["m"]), ("L", sz["l"]), ("XL", sz["xl"]),
                ("XXL", sz["xxl"]), ("M-XXL", sz["mx"])]

    # ── Order status breakdown ──
    status_rows = fetchall(
        "SELECT status, COUNT(*) c FROM orders GROUP BY status ORDER BY c DESC")
    order_status = [(r["status"], r["c"]) for r in status_rows]

    # ── Top designs by quantity ──
    td = fetchall(
        """SELECT design_no, COALESCE(SUM(row_qty),0) q FROM sales_bill_items
           WHERE design_no IS NOT NULL AND design_no <> ''
           GROUP BY design_no ORDER BY q DESC LIMIT 6""")
    top_designs = [(r["design_no"], r["q"]) for r in td]

    # ── Top customers by sales value ──
    tc = fetchall(
        """SELECT c.name, COALESCE(SUM(sb.total_amount),0) v
           FROM sales_bills sb JOIN customers c ON c.id=sb.customer_id
           GROUP BY c.id ORDER BY v DESC LIMIT 5""")
    top_customers = [(r["name"], r["v"]) for r in tc]

    return {
        "month_sales": month_sales,
        "month_qty": month_qty,
        "month_orders": month_orders,
        "month_purchases": month_purchases,
        "avg_order_value": avg_order_value,
        "sales_trend": trend,
        "size_mix": size_mix,
        "order_status": order_status,
        "top_designs": top_designs,
        "top_customers": top_customers,
    }
