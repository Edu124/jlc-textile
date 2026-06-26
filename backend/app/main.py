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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables and seed defaults on startup.
    Base.metadata.create_all(bind=engine)
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
