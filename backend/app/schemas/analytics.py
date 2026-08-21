"""Supervisor analytics summary schemas."""

from __future__ import annotations

from pydantic import BaseModel


class RiskDistribution(BaseModel):
    green: int  # risk score 1
    yellow: int  # risk score 2
    red: int  # risk score 3


class SymptomBreakdown(BaseModel):
    cluster: str
    count: int


class DistrictStats(BaseModel):
    district: str
    volume: int
    red_cases: int
    fever: int = 0
    respiratory: int = 0
    diarrhoea: int = 0
    maternal: int = 0
    other: int = 0


class RecentCaseOut(BaseModel):
    id: int
    client_uuid: str
    created_at: str | None
    age_group: str
    language: str
    district: str | None
    risk_score: int
    primary_cluster: str
    source: str


class AnalyticsSummary(BaseModel):
    total_cases: int
    risk_distribution: RiskDistribution
    symptom_breakdown: list[SymptomBreakdown]
    districts: list[DistrictStats]
    recent_cases: list[RecentCaseOut]
