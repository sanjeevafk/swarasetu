"""Analytics aggregation for the supervisor dashboard."""

from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Case
from app.schemas.analytics import (
    AnalyticsSummary,
    DistrictStats,
    RecentCaseOut,
    RiskDistribution,
    SymptomBreakdown,
)

import time

CLUSTERS = ("fever", "respiratory", "diarrhoea", "maternal")

_CACHE_SUMMARY: AnalyticsSummary | None = None
_CACHE_TIMESTAMP: float = 0.0
_CACHE_TTL_SECONDS: float = 5.0


def build_summary(db: Session, limit_recent: int = 8, bypass_cache: bool = False) -> AnalyticsSummary:
    global _CACHE_SUMMARY, _CACHE_TIMESTAMP

    now = time.time()
    if not bypass_cache and _CACHE_SUMMARY is not None and (now - _CACHE_TIMESTAMP) < _CACHE_TTL_SECONDS:
        return _CACHE_SUMMARY

    cases: list[Case] = list(db.execute(select(Case)).scalars())

    risk_counter = Counter(c.risk_score for c in cases)
    cluster_counter = Counter(c.primary_cluster for c in cases if c.primary_cluster != "none")

    district_rows: dict[str, Counter] = {}
    for c in cases:
        name = c.district or "Unknown"
        counter = district_rows.setdefault(name, Counter())
        counter["volume"] += 1
        if c.risk_score == 3:
            counter["red_cases"] += 1
        bucket = c.primary_cluster if c.primary_cluster in CLUSTERS else "other"
        counter[bucket] += 1

    districts = [
        DistrictStats(
            district=name,
            volume=ctr["volume"],
            red_cases=ctr["red_cases"],
            fever=ctr["fever"],
            respiratory=ctr["respiratory"],
            diarrhoea=ctr["diarrhoea"],
            maternal=ctr["maternal"],
            other=ctr["other"],
        )
        for name, ctr in sorted(district_rows.items(), key=lambda kv: (-kv[1]["volume"], kv[0]))
    ]

    recent = sorted(
        cases,
        key=lambda c: ((c.created_at is not None), c.created_at, -c.id),
        reverse=True,
    )[:limit_recent]

    result = AnalyticsSummary(
        total_cases=len(cases),
        risk_distribution=RiskDistribution(
            green=risk_counter.get(1, 0),
            yellow=risk_counter.get(2, 0),
            red=risk_counter.get(3, 0),
        ),
        symptom_breakdown=[
            SymptomBreakdown(cluster=c, count=n)
            for c, n in sorted(cluster_counter.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        districts=districts,
        recent_cases=[
            RecentCaseOut(
                id=c.id,
                client_uuid=c.client_uuid,
                created_at=c.created_at.isoformat() if c.created_at else None,
                age_group=c.age_group,
                language=c.language,
                district=c.district,
                risk_score=c.risk_score,
                primary_cluster=c.primary_cluster,
                source=c.source,
            )
            for c in recent
        ],
    )
    _CACHE_SUMMARY = result
    _CACHE_TIMESTAMP = time.time()
    return result
