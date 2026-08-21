"""PHC proximity service using the Haversine formula (no external APIs)."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from sqlalchemy.orm import Session

from backend.app.models import PHC
from backend.app.schemas.triage import PHCNearby

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def nearest_phcs(
    db: Session,
    lat: float,
    lon: float,
    limit: int = 5,
    radius_km: float | None = None,
) -> list[PHCNearby]:
    """Return facilities sorted by distance from (lat, lon), nearest first.

    Deterministic ordering: distance ascending, then facility id ascending.
    """
    stmt = db.query(PHC).all()
    results: list[tuple[float, int, PHCNearby]] = []
    for phc in stmt:
        dist = haversine_km(lat, lon, phc.latitude, phc.longitude)
        if radius_km is not None and dist > radius_km:
            continue
        results.append(
            (
                dist,
                phc.id,
                PHCNearby(
                    id=phc.id,
                    name=phc.name,
                    district=phc.district,
                    facility_type=phc.facility_type,
                    phone=phc.phone,
                    distance_km=round(dist, 2),
                    hours="24/7" if phc.is_24x7 else phc.hours,
                    is_24x7=phc.is_24x7,
                    doctor_available=phc.doctor_available,
                    latitude=phc.latitude,
                    longitude=phc.longitude,
                ),
            )
        )
    results.sort(key=lambda t: (t[0], t[1]))
    return [r[2] for r in results[:limit]]
