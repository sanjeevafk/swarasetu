"""Triage evaluation schemas (mirrors frontend types in src/types/api.ts)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.app.triage.types import ALL_AGES

AgeGroup = Literal["neonate", "infant", "child", "adolescent", "adult"]
LanguageCode = Literal["en", "hi", "ta", "bn"]


class SymptomPayloadIn(BaseModel):
    """Canonical structured symptom payload (NER output contract).

    All fields default to safe values so partial extractions still evaluate.
    """

    age_group: AgeGroup = "child"
    pregnant: bool = False

    # General danger signs
    convulsions: bool = False
    unconscious: bool = False
    unable_to_drink_or_breastfeed: bool = False
    vomiting_everything: bool = False

    # Fever cluster
    has_fever: bool = False
    temperature_c: Optional[float] = Field(default=None, ge=30.0, le=45.0)
    fever_days: Optional[int] = Field(default=None, ge=0)
    neck_stiffness: bool = False
    rash_with_fever: bool = False
    malaria_risk_area: bool = False

    # Respiratory cluster
    cough_days: Optional[int] = Field(default=None, ge=0)
    difficulty_breathing: bool = False
    breathing_rate_per_min: Optional[int] = Field(default=None, ge=0, le=120)
    chest_indrawing: bool = False
    stridor: bool = False
    wheezing: bool = False
    chest_pain_severe: bool = False
    vomiting_blood: bool = False

    # Diarrhoea cluster
    diarrhoea: bool = False
    stool_frequency_per_day: Optional[int] = Field(default=None, ge=0)
    blood_in_stool: bool = False
    sunken_eyes: bool = False
    skin_pinch_slow: bool = False
    restless_irritable: bool = False

    # Maternal cluster
    severe_headache: bool = False
    blurred_vision: bool = False
    vaginal_bleeding: bool = False
    reduced_fetal_movement: bool = False

    language: LanguageCode = "en"


class RedFlagOut(BaseModel):
    code: str
    description_en: str


class TriageOutcomeOut(BaseModel):
    risk_score: int = Field(ge=1, le=3)
    rationale_keys: list[str]
    rationale_en: str
    actions: list[str]
    red_flags: list[RedFlagOut]
    primary_cluster: str


class Directive(BaseModel):
    """Operational directive attached to the triage outcome."""

    type: Literal["self_care", "asha_dispatch", "phc_referral"]
    message_en: str


class PHCNearby(BaseModel):
    id: int
    name: str
    district: str
    facility_type: str
    phone: str
    distance_km: float
    hours: str
    is_24x7: bool
    doctor_available: bool
    latitude: float
    longitude: float


class TriageEvaluateRequest(BaseModel):
    payload: SymptomPayloadIn
    client_uuid: str = Field(min_length=8, max_length=64)
    district: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class TriageEvaluateResponse(BaseModel):
    case_id: int | None = None
    client_uuid: str
    outcome: TriageOutcomeOut
    directive: Directive
    nearest_phc: Optional[PHCNearby] = None
