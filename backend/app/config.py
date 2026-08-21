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

    @property
    def sarvam_api_key(self) -> str | None:
        return os.getenv("SARVAM_API_KEY") or None

    @property
    def twilio_account_sid(self) -> str | None:
        return os.getenv("TWILIO_ACCOUNT_SID") or None

    @property
    def twilio_api_key_sid(self) -> str | None:
        return os.getenv("TWILIO_API_KEY_SID") or None

    @property
    def twilio_auth_token(self) -> str | None:
        return os.getenv("TWILIO_AUTH_TOKEN") or None

    @property
    def twilio_phone_number(self) -> str:
        return os.getenv("TWILIO_PHONE_NUMBER", "+14155238886")

    @property
    def meta_whatsapp_token(self) -> str | None:
        return os.getenv("META_WHATSAPP_TOKEN") or None

    @property
    def meta_phone_number_id(self) -> str | None:
        return os.getenv("META_PHONE_NUMBER_ID") or None

    @property
    def meta_verify_token(self) -> str:
        return os.getenv("META_VERIFY_TOKEN", "swarasetu_meta_verify_2026")




@lru_cache
def get_settings() -> Settings:
    # Attempt to load local .env if available
    try:
        from pathlib import Path
        env_path = Path(__file__).resolve().parents[2] / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        pass
    return Settings()



settings = get_settings()
