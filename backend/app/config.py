import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database — Railway injects DATABASE_URL (PostgreSQL). Locally falls back
    # to a SQLite file so we can build/test without a Postgres server.
    DATABASE_URL: str = "sqlite:///./jlc_local.db"

    # Auth — single shared shop login. Override on Railway via env vars.
    SHOP_USERNAME: str = "jailaxmi"
    SHOP_PASSWORD: str = "jlc@2026"          # CHANGE in production env
    SECRET_KEY: str = "change-me-in-production-please"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24 * 14  # 2 weeks

    # AI image generation (Stability key optional; text->image is free)
    STABILITY_API_KEY: str = ""

    # CORS (frontend dev server). "*" is fine since auth gates everything.
    CORS_ORIGINS: str = "*"

    class Config:
        env_file = ".env"
        extra = "ignore"


def _normalize_db_url(url: str) -> str:
    # Railway/Heroku style "postgres://" -> SQLAlchemy "postgresql://"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


settings = Settings()
settings.DATABASE_URL = _normalize_db_url(
    os.environ.get("DATABASE_URL", settings.DATABASE_URL)
)
