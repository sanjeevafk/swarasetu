"""Batch sync service for offline outbox records."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.schemas.sync import SyncCaseItem
from backend.app.services.triage_service import evaluate_payload, persist_case


def sync_cases(db: Session, items: list[SyncCaseItem]) -> dict:
    """Re-evaluate each queued record server-side and upsert idempotently.

    The client's own risk snapshot is advisory; the deterministic engine result
    is authoritative so offline and online outcomes can never diverge.
    """
    accepted = 0
    duplicates = 0

    for item in items:
        outcome = evaluate_payload(item.payload)
        _case, created = persist_case(
            db,
            client_uuid=item.client_uuid,
            payload_in=item.payload,
            outcome=outcome,
            district=item.district,
            latitude=item.latitude,
            longitude=item.longitude,
            source="offline_sync",
        )
        if created:
            accepted += 1
        else:
            duplicates += 1

    return {"accepted": accepted, "duplicates": duplicates, "total": len(items)}
