"""Triage case record (de-identified interaction log)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Idempotency key for offline outbox sync (client-generated UUID).
    client_uuid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Patient context (de-identified: no names/IDs stored)
    age_group: Mapped[str] = mapped_column(String(20), nullable=False, default="child")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    district: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Triage outcome
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    primary_cluster: Mapped[str] = mapped_column(String(30), nullable=False)
    rationale_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rationale_keys: Mapped[str] = mapped_column(Text, nullable=False, default="[]")   # JSON array
    actions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")     # JSON array
    red_flags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")   # JSON array

    # Provenance: 'online' (evaluated server-side) or 'offline_sync'
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="online")

    def to_dict(self) -> dict:
        import json

        return {
            "id": self.id,
            "client_uuid": self.client_uuid,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "age_group": self.age_group,
            "language": self.language,
            "district": self.district,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "risk_score": self.risk_score,
            "primary_cluster": self.primary_cluster,
            "rationale_en": self.rationale_en,
            "rationale_keys": json.loads(self.rationale_keys or "[]"),
            "actions": json.loads(self.actions_json or "[]"),
            "red_flags": json.loads(self.red_flags_json or "[]"),
            "source": self.source,
        }
