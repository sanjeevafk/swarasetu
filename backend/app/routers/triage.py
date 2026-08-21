"""Triage evaluation endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.triage import TriageEvaluateRequest, TriageEvaluateResponse
from app.services.phc_service import nearest_phcs
from app.services.triage_service import evaluate_and_log

router = APIRouter(prefix="/api/v1/triage", tags=["triage"])


@router.post("/evaluate", response_model=TriageEvaluateResponse)
def evaluate_triage(request: TriageEvaluateRequest, db: Session = Depends(get_db)):
    result = evaluate_and_log(db, request)

    if request.latitude is not None and request.longitude is not None:
        nearby = nearest_phcs(db, request.latitude, request.longitude, limit=1)
        result["nearest_phc"] = nearby[0] if nearby else None

    return result
