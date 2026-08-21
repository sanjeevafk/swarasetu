"""SwaraSetu deterministic WHO IMCI triage engine.

Usage:
    from backend.app.triage import SymptomPayload, evaluate

    outcome = evaluate(SymptomPayload(has_fever=True, fever_days=1))
    assert int(outcome.risk_score) == 1
"""

from backend.app.triage.engine import RiskScore, SymptomPayload, TriageOutcome, evaluate
from backend.app.triage.types import (
    AGE_ADULT,
    AGE_ADOLESCENT,
    AGE_CHILD,
    AGE_INFANT,
    AGE_NEONATE,
    ClusterFinding,
)

__all__ = [
    "evaluate",
    "SymptomPayload",
    "TriageOutcome",
    "RiskScore",
    "ClusterFinding",
    "AGE_NEONATE",
    "AGE_INFANT",
    "AGE_CHILD",
    "AGE_ADOLESCENT",
    "AGE_ADULT",
]
