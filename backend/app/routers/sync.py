"""Batch sync endpoint for offline-queued case records."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.sync import SyncCaseItem, SyncResponse
from app.services.sync_service import sync_cases

from typing import Any

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.post("/cases", response_model=SyncResponse)
def sync_offline_cases(items: list[dict[str, Any]], db: Session = Depends(get_db)):
    if not items:
        return SyncResponse(accepted=0, duplicates=0, rejected=0, total=0)
    return sync_cases(db, items)

