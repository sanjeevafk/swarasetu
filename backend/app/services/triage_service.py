"""Triage service: runs the IMCI engine, persists cases, composes directives."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import AshaAssignment, Case
from backend.app.schemas.triage import (
    Directive,
    RedFlagOut,
    SymptomPayloadIn,
    TriageOutcomeOut,
)
from backend.app.triage import SymptomPayload as EnginePayload
from backend.app.triage import evaluate


def _to_engine_payload(p: SymptomPayloadIn) -> EnginePayload:
    return EnginePayload(**p.model_dump())


def evaluate_payload(payload: SymptomPayloadIn):
    """Pure evaluation without persistence (also used by sync service)."""
    return evaluate(_to_engine_payload(payload))


def build_outcome(payload: SymptomPayloadIn) -> TriageOutcomeOut:
    outcome = evaluate_payload(payload)
    return TriageOutcomeOut(
        risk_score=int(outcome.risk_score),
        rationale_keys=list(outcome.rationale_keys),
        rationale_en=outcome.rationale_en,
        actions=list(outcome.actions),
        red_flags=[RedFlagOut(code=f.code, description_en=f.description_en) for f in outcome.red_flags],
        primary_cluster=outcome.primary_cluster,
    )


def compose_directive(risk: int) -> Directive:
    if risk >= 3:
        return Directive(
            type="phc_referral",
            message_en="Immediate referral: proceed to the nearest PHC now. Coordinates and contact shared.",
        )
    if risk == 2:
        return Directive(
            type="asha_dispatch",
            message_en="ASHA worker alerted for a home assessment within 24 hours.",
        )
    return Directive(
        type="self_care",
        message_en="Home care advised. Return immediately if symptoms worsen.",
    )


def find_assigned_asha(db: Session, district: str | None) -> AshaAssignment | None:
    if not district:
        return None
    stmt = select(AshaAssignment).where(AshaAssignment.district == district).limit(1)
    return db.execute(stmt).scalar_one_or_none()


def persist_case(
    db: Session,
    *,
    client_uuid: str,
    payload_in: SymptomPayloadIn,
    outcome,
    district: str | None,
    latitude: float | None,
    longitude: float | None,
    source: str = "online",
) -> tuple[Case | None, bool]:
    """Insert a case row. Returns ``(case, created)``.

    ``created`` is False when ``client_uuid`` already exists, making offline
    outbox retries idempotent."""
    existing = db.execute(
        select(Case).where(Case.client_uuid == client_uuid)
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False

    case = Case(
        client_uuid=client_uuid,
        age_group=payload_in.age_group,
        language=payload_in.language,
        district=district,
        latitude=latitude,
        longitude=longitude,
        risk_score=int(outcome.risk_score),
        primary_cluster=outcome.primary_cluster,
        rationale_en=outcome.rationale_en,
        rationale_keys=json.dumps(list(outcome.rationale_keys)),
        actions_json=json.dumps(list(outcome.actions)),
        red_flags_json=json.dumps([{"code": f.code, "description_en": f.description_en} for f in outcome.red_flags]),
        source=source,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case, True


def evaluate_and_log(db: Session, request) -> dict:
    """Full online evaluation flow used by POST /api/v1/triage/evaluate."""
    outcome = evaluate_payload(request.payload)

    case, _created = persist_case(
        db,
        client_uuid=request.client_uuid,
        payload_in=request.payload,
        outcome=outcome,
        district=request.district,
        latitude=request.latitude,
        longitude=request.longitude,
        source="online",
    )

    directive = compose_directive(int(outcome.risk_score))
    result = {
        "case_id": case.id if case else None,
        "client_uuid": request.client_uuid,
        "outcome": build_outcome(request.payload),
        "directive": directive,
        "nearest_phc": None,  # populated by router when lat/lon present
    }
    return result
