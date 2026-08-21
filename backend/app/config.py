"""Application configuration via environment variables (12-factor)."""

from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    """Runtime settings. Defaults allow zero-config local development:
    SQLite for persistence and no Redis (cache becomes a no-op)."""

    app_name: str = "SwaraSetu API"
    api_version: str = "v1"

    @property
    def database_url(self) -> str:
        url = os.getenv("DATABASE_URL", "sqlite:///./swarasetu.db")
        # Normalize legacy scheme names to SQLAlchemy drivers.
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg2://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    @property
    def redis_url(self) -> str | None:
        return os.getenv("REDIS_URL") or None

    @property
    def cors_origins(self) -> list[str]:
        raw = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173",
        )
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def default_search_radius_km(self) -> float:
        return float(os.getenv("PHC_SEARCH_RADIUS_KM", "100"))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
