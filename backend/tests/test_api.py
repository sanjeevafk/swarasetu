"""API-level tests exercising the FastAPI endpoints end-to-end (SQLite)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.database import init_db  # noqa: E402
from backend.scripts.seed_phc_data import PHCS  # noqa: E402


@pytest.fixture(scope="module")
def client():
    init_db()
    # Seed PHC data directly for the module.
    from app.database import SessionLocal
    from app.models import PHC

    db = SessionLocal()
    if db.query(PHC).count() == 0:
        db.add_all([PHC(**p) for p in PHCS])
        db.commit()
    db.close()

    with TestClient(app) as c:
        yield c


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_evaluate_green_case(client):
    body = {
        "payload": {"age_group": "child", "has_fever": True, "fever_days": 1},
        "client_uuid": "test-green-0001",
        "district": "Sitamarhi",
    }
    res = client.post("/api/v1/triage/evaluate", json=body)
    assert res.status_code == 200
    data = res.json()
    assert data["outcome"]["risk_score"] == 1
    assert data["directive"]["type"] == "self_care"


def test_evaluate_red_case_returns_nearest_phc(client):
    body = {
        "payload": {
            "age_group": "adult",
            "chest_pain_severe": True,
            "vomiting_blood": True,
            "language": "bn",
        },
        "client_uuid": "test-red-0001",
        "district": "Sitamarhi",
        "latitude": 26.45,
        "longitude": 85.35,
    }
    res = client.post("/api/v1/triage/evaluate", json=body)
    assert res.status_code == 200
    data = res.json()
    assert data["outcome"]["risk_score"] == 3
    assert data["directive"]["type"] == "phc_referral"
    assert data["nearest_phc"] is not None
    assert data["nearest_phc"]["distance_km"] >= 0


def test_evaluate_is_idempotent_on_client_uuid(client):
    body = {
        "payload": {"cough_days": 3, "difficulty_breathing": False},
        "client_uuid": "test-dup-0001",
    }
    r1 = client.post("/api/v1/triage/evaluate", json=body)
    r2 = client.post("/api/v1/triage/evaluate", json=body)
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["case_id"] == r2.json()["case_id"]


def test_nearest_phcs_sorted_by_distance(client):
    res = client.get("/api/v1/phcs/nearest", params={"lat": 26.4468, "lon": 85.3402})
    assert res.status_code == 200
    phcs = res.json()
    assert len(phcs) >= 2
    dists = [p["distance_km"] for p in phcs]
    assert dists == sorted(dists)
    assert all("phone" in p for p in phcs)


def test_analytics_summary_shape(client):
    res = client.get("/api/v1/analytics/summary")
    assert res.status_code == 200
    data = res.json()
    assert set(data.keys()) == {
        "total_cases",
        "risk_distribution",
        "symptom_breakdown",
        "districts",
        "recent_cases",
    }
    assert data["total_cases"] >= 1


def test_sync_batch_idempotent(client):
    items = [
        {
            "client_uuid": "sync-0000-aaaa",
            "payload": {"diarrhoea": True, "blood_in_stool": True},
            "district": "Sheohar",
        },
        {
            "client_uuid": "sync-0000-bbbb",
            "payload": {"pregnant": True, "vaginal_bleeding": True},
            "district": "Muzaffarpur",
        },
    ]
    r1 = client.post("/api/v1/sync/cases", json=items)
    assert r1.status_code == 200
    assert r1.json()["accepted"] == 2

    r2 = client.post("/api/v1/sync/cases", json=items)
    assert r2.status_code == 200
    assert r2.json()["duplicates"] == 2
    assert r2.json()["accepted"] == 0


def test_sync_empty_list(client):
    res = client.post("/api/v1/sync/cases", json=[])
    assert res.status_code == 200
    assert res.json()["total"] == 0
