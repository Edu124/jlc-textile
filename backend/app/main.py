import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import settings
from .db import Base, engine, SessionLocal
from . import models  # noqa: F401  (register tables)
from .seed import seed_defaults
from .routers import (
    auth as auth_router, masters, materials, sales, purchases, orders,
    production, finished_goods, settings as settings_router,
    dashboard, ai, backup,
)


def _run_migrations():
    """Add columns introduced after a DB was first created (SQLite + Postgres)."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    if insp.has_table("raw_material_transactions"):
        cols = {c["name"] for c in insp.get_columns("raw_material_transactions")}
        with engine.begin() as conn:
            for name in ("recipient_type", "recipient_name"):
                if name not in cols:
                    conn.execute(text(
                        f"ALTER TABLE raw_material_transactions ADD COLUMN {name} VARCHAR"))
    if insp.has_table("tailor_jobs"):
        cols = {c["name"] for c in insp.get_columns("tailor_jobs")}
        if "product_id" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE tailor_jobs ADD COLUMN product_id INTEGER"))
    if insp.has_table("products"):
        cols = {c["name"] for c in insp.get_columns("products")}
        with engine.begin() as conn:
            if "pending_qty" not in cols:
                conn.execute(text("ALTER TABLE products ADD COLUMN pending_qty FLOAT DEFAULT 0"))
            for col in ("rate_m", "rate_l", "rate_xl", "rate_xxl", "rate_mxxl"):
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE products ADD COLUMN {col} FLOAT DEFAULT 0"))
    if insp.has_table("sales_bill_items"):
        cols = {c["name"] for c in insp.get_columns("sales_bill_items")}
        with engine.begin() as conn:
            for col in ("rate_m", "rate_l", "rate_xl", "rate_xxl", "rate_mxxl"):
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE sales_bill_items ADD COLUMN {col} FLOAT DEFAULT 0"))
    if insp.has_table("order_items"):
        cols = {c["name"] for c in insp.get_columns("order_items")}
        with engine.begin() as conn:
            if "delivered_qty" not in cols:
                conn.execute(text("ALTER TABLE order_items ADD COLUMN delivered_qty FLOAT DEFAULT 0"))
            if "design_no" not in cols:
                conn.execute(text("ALTER TABLE order_items ADD COLUMN design_no VARCHAR"))
            for col in ("qty_m", "qty_l", "qty_xl", "qty_xxl", "qty_mxxl",
                        "delivered_m", "delivered_l", "delivered_xl", "delivered_xxl", "delivered_mxxl"):
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE order_items ADD COLUMN {col} FLOAT DEFAULT 0"))
    if insp.has_table("sales_bills"):
        cols = {c["name"] for c in insp.get_columns("sales_bills")}
        if "reference_no" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE sales_bills ADD COLUMN reference_no VARCHAR"))
    if insp.has_table("order_deliveries"):
        cols = {c["name"] for c in insp.get_columns("order_deliveries")}
        if "reference_no" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE order_deliveries ADD COLUMN reference_no VARCHAR"))
    if insp.has_table("tailor_deliveries"):
        cols = {c["name"] for c in insp.get_columns("tailor_deliveries")}
        with engine.begin() as conn:
            for col in ("size_m", "size_l", "size_xl", "size_xxl", "size_mxxl"):
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE tailor_deliveries ADD COLUMN {col} FLOAT DEFAULT 0"))
    if insp.has_table("tailor_jobs"):
        cols = {c["name"] for c in insp.get_columns("tailor_jobs")}
        with engine.begin() as conn:
            if "target_pieces" not in cols:
                conn.execute(text("ALTER TABLE tailor_jobs ADD COLUMN target_pieces FLOAT DEFAULT 0"))
            if "tailor_type" not in cols:
                conn.execute(text("ALTER TABLE tailor_jobs ADD COLUMN tailor_type VARCHAR DEFAULT 'work'"))
            if "assigned_pieces" not in cols:
                conn.execute(text("ALTER TABLE tailor_jobs ADD COLUMN assigned_pieces FLOAT DEFAULT 0"))
            if "parent_job_id" not in cols:
                conn.execute(text("ALTER TABLE tailor_jobs ADD COLUMN parent_job_id INTEGER"))
            for col in ("size_m", "size_l", "size_xl", "size_xxl", "size_mxxl"):
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE tailor_jobs ADD COLUMN {col} FLOAT DEFAULT 0"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables, run migrations, seed defaults on startup.
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    db = SessionLocal()
    try:
        seed_defaults(db)
    finally:
        db.close()
    yield


app = FastAPI(title="JLC Textile Manager API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(masters.router)
app.include_router(materials.router)
app.include_router(sales.router)
app.include_router(purchases.router)
app.include_router(orders.router)
app.include_router(production.router)
app.include_router(finished_goods.router)
app.include_router(settings_router.router)
app.include_router(dashboard.router)
app.include_router(ai.router)
app.include_router(backup.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "db": settings.DATABASE_URL.split(":")[0]}


# ── Serve the built React app (production single-service deploy) ──────────────
# In the Docker image the frontend build is copied to /app/static.
_STATIC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(_STATIC):
    assets = os.path.join(_STATIC, "assets")
    if os.path.isdir(assets):
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        # API routes are registered above and take precedence. Everything
        # else falls back to index.html so client-side routing works.
        candidate = os.path.join(_STATIC, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_STATIC, "index.html"))
