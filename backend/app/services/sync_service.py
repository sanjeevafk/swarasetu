"""Batch sync service for offline outbox records."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.sync import SyncCaseItem
from app.services.triage_service import evaluate_payload, persist_case


def sync_cases(db: Session, items: list[SyncCaseItem]) -> dict:
    """Re-evaluate each queued record server-side and upsert idempotently.
    Per-item isolation ensures one corrupted record never wedges the entire sync queue.
    """
    accepted = 0
    duplicates = 0
    rejected = 0
    accepted_uuids: list[str] = []
    duplicate_uuids: list[str] = []
    rejected_uuids: list[str] = []

    for item in items:
        try:
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
                accepted_uuids.append(item.client_uuid)
            else:
                duplicates += 1
                duplicate_uuids.append(item.client_uuid)
        except Exception:
            rejected += 1
            rejected_uuids.append(item.client_uuid)

    return {
        "accepted": accepted,
        "duplicates": duplicates,
        "rejected": rejected,
        "total": len(items),
        "accepted_uuids": accepted_uuids,
        "duplicate_uuids": duplicate_uuids,
        "rejected_uuids": rejected_uuids,
    }

