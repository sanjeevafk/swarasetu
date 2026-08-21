#!/usr/bin/env python3
"""Seed the database with rural PHC facilities and ASHA assignments.

Usage:
    python -m backend.scripts.seed_phc_data            # via app DATABASE_URL
    DATABASE_URL=postgresql+psycopg2://... python -m backend.scripts.seed_phc_data
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import AshaAssignment, PHC

# Facilities anchored around Sitamarhi district, North Bihar (matches demo map).
PHCS = [
    dict(
        name="Belsand Primary Health Center",
        district="Sitamarhi",
        facility_type="PHC",
        phone="+91-6226-282234",
        latitude=26.4468,
        longitude=85.3402,
        is_24x7=True,
        doctor_available=True,
        hours="24/7",
    ),
    dict(
        name="Runnisaidpur Block Hospital",
        district="Sitamarhi",
        facility_type="CHC",
        phone="+91-6226-254410",
        latitude=26.3768,
        longitude=85.3852,
        is_24x7=False,
        doctor_available=False,
        hours="9 AM - 5 PM",
    ),
    dict(
        name="Dumra Community Health Centre",
        district="Sitamarhi",
        facility_type="CHC",
        phone="+91-6226-224480",
        latitude=26.5868,
        longitude=85.3902,
        is_24x7=True,
        doctor_available=True,
        hours="24/7",
    ),
    dict(
        name="Pupri Referral Hospital",
        district="Sitamarhi",
        facility_type="PHC",
        phone="+91-6226-260233",
        latitude=26.5068,
        longitude=85.6402,
        is_24x7=True,
        doctor_available=True,
        hours="24/7",
    ),
    dict(
        name="Sursand Health Sub-Center",
        district="Sitamarhi",
        facility_type="SubCenter",
        phone="+91-6226-276118",
        latitude=26.6168,
        longitude=85.5402,
        is_24x7=False,
        doctor_available=False,
        hours="9 AM - 2 PM",
    ),
    dict(
        name="Sheohar District Hospital",
        district="Sheohar",
        facility_type="District Hospital",
        phone="+91-6290-222100",
        latitude=26.5158,
        longitude=85.2911,
        is_24x7=True,
        doctor_available=True,
        hours="24/7",
    ),
    dict(
        name="Muzaffarpur Sadar Hospital",
        district="Muzaffarpur",
        facility_type="District Hospital",
        phone="+91-6212-222214",
        latitude=26.1209,
        longitude=85.3647,
        is_24x7=True,
        doctor_available=True,
        hours="24/7",
    ),
]

ASHA_WORKERS = [
    dict(asha_name="Sunita Devi", phone="+91-98XXXX1201", village="Belsand", district="Sitamarhi"),
    dict(asha_name="Rekha Kumari", phone="+91-98XXXX1202", village="Dumra", district="Sitamarhi"),
    dict(asha_name="Poonam Singh", phone="+91-98XXXX1203", village="Runnisaidpur", district="Sitamarhi"),
    dict(asha_name="Anita Devi", phone="+91-98XXXX1301", village="Sheohar", district="Sheohar"),
]


def seed() -> None:
    init_db()
    db: Session = SessionLocal()
    try:
        existing = db.query(PHC).count()
        if existing > 0:
            print(f"Database already seeded ({existing} PHCs). Skipping.")
            return

        phc_rows = [PHC(**p) for p in PHCS]
        db.add_all(phc_rows)
        db.flush()

        for worker in ASHA_WORKERS:
            match = next((p for p in phc_rows if p.district == worker["district"]), None)
            db.add(AshaAssignment(phc_id=match.id if match else None, **worker))

        db.commit()
        print(f"Seeded {len(phc_rows)} PHCs and {len(ASHA_WORKERS)} ASHA assignments.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
