"""Offline outbox sync schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.triage import SymptomPayloadIn


class SyncCaseItem(BaseModel):
    """A queued case record created offline in the browser IndexedDB outbox."""

    client_uuid: str = Field(min_length=8, max_length=64)
    payload: SymptomPayloadIn
    district: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    created_at: Optional[str] = None  # ISO timestamp from the client clock
    # Snapshot of the client-side engine result (re-evaluated server-side anyway)
    client_risk_score: Optional[int] = Field(default=None, ge=1, le=3)


class SyncResponse(BaseModel):
    accepted: int
    duplicates: int
    rejected: int = 0
    total: int
    accepted_uuids: list[str] = Field(default_factory=list)
    duplicate_uuids: list[str] = Field(default_factory=list)
    rejected_uuids: list[str] = Field(default_factory=list)

