"""Core type definitions for the deterministic WHO IMCI triage engine.

The engine is 100% deterministic: no randomness, no network calls, no LLM.
Given the same SymptomPayload, evaluate() always returns the identical
TriageOutcome.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class RiskScore(IntEnum):
    """IMCI risk tier.

    1 = Self-Care (Green): home management with observation guidance.
    2 = CHW ASHA Dispatch (Yellow): ASHA worker assessment within 24 hours.
    3 = Immediate Emergency PHC Referral (Red): urgent referral required now.
    """

    SELF_CARE = 1
    ASHA_DISPATCH = 2
    EMERGENCY_REFERRAL = 3


class Cluster(str):
    """Syndromic cluster identifiers."""

    FEVER = "fever"
    RESPIRATORY = "respiratory"
    DIARRHOEA = "diarrhoea"
    MATERNAL = "maternal"
    GENERAL = "general"
    NONE = "none"


# Age groups aligned to WHO IMCI age bands.
AGE_NEONATE = "neonate"        # 0 - 2 months
AGE_INFANT = "infant"          # 2 months - 12 months
AGE_CHILD = "child"            # 12 months - 5 years
AGE_ADOLESCENT = "adolescent"  # 5 - 18 years
AGE_ADULT = "adult"            # >= 18 years

ALL_AGES = (
    AGE_NEONATE,
    AGE_INFANT,
    AGE_CHILD,
    AGE_ADOLESCENT,
    AGE_ADULT,
)

# WHO fast-breathing (pneumonia) thresholds: breaths per minute by age band.
FAST_BREATHING_THRESHOLDS = {
    AGE_NEONATE: 60,
    AGE_INFANT: 50,
    AGE_CHILD: 40,
    AGE_ADOLESCENT: 30,
    AGE_ADULT: 24,
}

FEVER_THRESHOLD_C = 37.5   # axillary fever threshold per IMCI
HIGH_FEVER_C = 39.0        # "very high fever" flag
MALARIA_FEVER_C = 38.5     # fever warranting malaria testing in endemic areas
COUGH_URI_DAYS_MAX = 14    # cough beyond this duration needs re-assessment
STOOL_SEVERE_DIARRHOEA_PER_DAY = 8


@dataclass(frozen=True)
class SymptomPayload:
    """Canonical structured symptom object (mirrors NER extraction output).

    All fields have deterministic defaults so that partial extractions from
    voice/NER pipelines still yield a stable triage outcome.
    """

    # Demographics
    age_group: str = AGE_CHILD
    pregnant: bool = False

    # General danger signs (any one => emergency referral per IMCI)
    convulsions: bool = False
    unconscious: bool = False
    unable_to_drink_or_breastfeed: bool = False
    vomiting_everything: bool = False

    # Fever cluster
    has_fever: bool = False
    temperature_c: Optional[float] = None
    fever_days: Optional[int] = None
    neck_stiffness: bool = False
    rash_with_fever: bool = False
    malaria_risk_area: bool = False

    # Respiratory cluster
    cough_days: Optional[int] = None
    difficulty_breathing: bool = False
    breathing_rate_per_min: Optional[int] = None
    chest_indrawing: bool = False
    stridor: bool = False
    wheezing: bool = False
    chest_pain_severe: bool = False
    vomiting_blood: bool = False

    # Diarrhoea / dehydration cluster
    diarrhoea: bool = False
    stool_frequency_per_day: Optional[int] = None
    blood_in_stool: bool = False
    sunken_eyes: bool = False
    skin_pinch_slow: bool = False
    restless_irritable: bool = False

    # Maternal danger signs
    severe_headache: bool = False
    blurred_vision: bool = False
    vaginal_bleeding: bool = False
    reduced_fetal_movement: bool = False

    # Provenance
    language: str = "en"


@dataclass(frozen=True)
class RedFlag:
    """A single extracted danger sign."""

    code: str
    description_en: str


@dataclass(frozen=True)
class TriageOutcome:
    """Deterministic triage result returned by the IMCI engine.

    rationale keys map into backend/app/triage/messages.py for localized
    plain-language explanations; rationale_en is always present for audit.
    """

    risk_score: RiskScore
    rationale_keys: tuple[str, ...]
    rationale_en: str
    actions: tuple[str, ...]
    red_flags: tuple[RedFlag, ...]
    primary_cluster: str

    def as_dict(self) -> dict:
        return {
            "risk_score": int(self.risk_score),
            "rationale_keys": list(self.rationale_keys),
            "rationale_en": self.rationale_en,
            "actions": list(self.actions),
            "red_flags": [f.__dict__ for f in self.red_flags],
            "primary_cluster": self.primary_cluster,
        }


@dataclass(frozen=True)
class ClusterFinding:
    """Internal evaluation result for a single syndromic cluster."""

    cluster: str
    risk_score: RiskScore
    rationale_keys: tuple[str, ...] = ()
    red_flag_codes: tuple[str, ...] = ()
    matched: bool = True  # False when payload shows no symptoms of the cluster
