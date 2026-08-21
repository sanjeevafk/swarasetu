"""Batch sync service for offline outbox records."""

from __future__ import annotations

import logging
from typing import Any
from sqlalchemy.orm import Session

from app.schemas.sync import SyncCaseItem
from app.services.triage_service import evaluate_payload, persist_case

logger = logging.getLogger(__name__)


def sync_cases(db: Session, items: list[dict[str, Any] | SyncCaseItem]) -> dict:
    """Re-evaluate each queued record server-side and upsert idempotently.
    Per-item isolation and transaction rollback ensures one corrupted record
    never wedges the entire batch or leaves the session in PendingRollbackError.
    """
    accepted = 0
    duplicates = 0
    rejected = 0
    accepted_uuids: list[str] = []
    duplicate_uuids: list[str] = []
    rejected_uuids: list[str] = []

    for raw in items:
        raw_uuid = "unknown"
        try:
            if isinstance(raw, SyncCaseItem):
                item = raw
            elif isinstance(raw, dict):
                raw_uuid = str(raw.get("client_uuid", "unknown"))
                item = SyncCaseItem.model_validate(raw)
            else:
                raise ValueError(f"Unsupported item format: {type(raw)}")

            raw_uuid = item.client_uuid
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
        except Exception as e:
            logger.warning("Error syncing item %s (rolling back sub-transaction): %s", raw_uuid, e)
            try:
                db.rollback()
            except Exception as rb_err:
                logger.error("DB rollback error: %s", rb_err)
            rejected += 1
            rejected_uuids.append(raw_uuid)

    return {
        "accepted": accepted,
        "duplicates": duplicates,
        "rejected": rejected,
        "total": len(items),
        "accepted_uuids": accepted_uuids,
        "duplicate_uuids": duplicate_uuids,
        "rejected_uuids": rejected_uuids,
    }
