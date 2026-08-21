"""Nearest-PHC locator endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.schemas.triage import PHCNearby
from backend.app.services.phc_service import nearest_phcs

router = APIRouter(prefix="/api/v1/phcs", tags=["phcs"])


@router.get("/nearest", response_model=list[PHCNearby])
def get_nearest_phcs(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    limit: int = Query(5, ge=1, le=25),
    radius_km: float | None = Query(None, gt=0),
    db: Session = Depends(get_db),
):
    return nearest_phcs(
        db,
        lat,
        lon,
        limit=limit,
        radius_km=radius_km if radius_km is not None else settings.default_search_radius_km,
    )
