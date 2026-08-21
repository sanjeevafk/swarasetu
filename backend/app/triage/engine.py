"""Deterministic WHO IMCI triage engine.

Pure, side-effect-free decision logic. Given an identical SymptomPayload the
engine always returns an identical TriageOutcome — no randomness, no network,
no LLM. This is what makes outcomes clinically auditable and unit-testable.
"""

from __future__ import annotations

from app.triage import clusters as C
from app.triage.messages import ACTIONS, RATIONALE, resolve
from app.triage.types import (
    ClusterFinding,
    RedFlag,
    RiskScore,
    SymptomPayload,
    TriageOutcome,
)

__all__ = ["evaluate", "evaluate_finding", "TriageOutcome", "RiskScore", "SymptomPayload"]

# Ordered evaluation pipeline. General danger signs run first and short-circuit;
# remaining clusters are all evaluated so red flags from every cluster surface.
_PIPELINE = (
    ("general", C.evaluate_general_danger_signs),
    ("fever", C.evaluate_fever),
    ("respiratory", C.evaluate_respiratory),
    ("diarrhoea", C.evaluate_diarrhoea),
    ("maternal", C.evaluate_maternal),
    ("adhoc", C.evaluate_adhoc_request),
)

# Deterministic action sets per risk tier (keys into messages.ACTIONS).
_ACTIONS_BY_RISK: dict[int, tuple[str, ...]] = {
    1: ("act_monitor_home", "act_return_if_worse"),
    2: ("act_notify_asha", "act_return_if_worse"),
    3: ("act_refer_phc_now", "act_call_ambulance"),
}


def _actions_for(risk: RiskScore, primary_cluster: str) -> tuple[str, ...]:
    base = list(_ACTIONS_BY_RISK[int(risk)])
    if int(risk) == 1:
        # Domain-specific home-care advice appended deterministically.
        if primary_cluster == "fever":
            base.insert(0, "act_paracetamol_home_care")
        elif primary_cluster == "diarrhoea":
            base = ["act_ors_fluids", "act_zinc_supplement"] + base
    return tuple(base)


def evaluate_finding(finding: ClusterFinding) -> list[RedFlag]:
    """Map a finding's red-flag codes to canonical RedFlag records."""
    descriptions = {
        "convulsions": "Convulsions / fits",
        "unconscious": "Unconsciousness or lethargy",
        "unable_to_drink": "Unable to drink or breastfeed",
        "vomiting_everything": "Vomiting everything",
        "severe_chest_pain": "Severe chest pain",
        "vomiting_blood": "Vomiting blood (haematemesis)",
        "neonatal_fever": "Fever in baby under 2 months",
        "neck_stiffness_meningitis": "Fever with neck stiffness (suspected meningitis)",
        "febrile_convulsions": "Fever with convulsions",
        "fever_with_rash": "Fever with rash (possible dengue/measles)",
        "stridor": "Stridor — noisy breathing on inspiration",
        "chest_indrawing": "Lower chest wall indrawing",
        "fast_breathing": "Fast breathing for age (possible pneumonia)",
        "breathing_difficulty_reported": "Reported difficulty breathing",
        "prolonged_cough": "Cough lasting more than 14 days",
        "severe_dehydration": "Severe dehydration (sunken eyes + slow skin pinch)",
        "some_dehydration": "Some dehydration signs",
        "blood_in_stool_dysentery": "Blood in stool (dysentery)",
        "frequent_stools": "Very frequent stools (>=8/day)",
        "pre_eclampsia": "Severe headache with blurred vision (pre-eclampsia)",
        "maternal_headache_or_visual": "Headache or visual disturbance in pregnancy",
        "vaginal_bleeding": "Vaginal bleeding in pregnancy",
        "reduced_fetal_movement": "Reduced fetal movement",
        "eclampsia_convulsions": "Convulsions in pregnancy (possible eclampsia)",
    }
    return [
        RedFlag(code=code, description_en=descriptions.get(code, code.replace("_", " ").title()))
        for code in finding.red_flag_codes
    ]


def evaluate(payload: SymptomPayload, language: str | None = None) -> TriageOutcome:
    """Run the full IMCI pipeline deterministically.

    The final risk score is the maximum across clusters; rationale keys are
    ordered by descending cluster severity for stable output.
    """
    lang = language or payload.language

    findings: list[tuple[str, ClusterFinding]] = []
    for name, fn in _PIPELINE:
        findings.append((name, fn(payload)))

    max_risk = max(f.risk_score for _, f in findings)
    matched_findings = [(n, f) for n, f in findings if f.matched]
    specific_max = [
        (n, f) for n, f in findings
        if f.risk_score == max_risk and f.matched and n != "general"
    ]
    if specific_max:
        primary_cluster, primary_finding = specific_max[0]
    else:
        primary_cluster, primary_finding = next(
            ((n, f) for n, f in findings if f.risk_score == max_risk and f.matched),
            ("none", findings[0][1]),
        )

    # Rationale keys: emergency findings first, then lower tiers, in
    # fixed pipeline order within each tier (deterministic ordering).
    ordered: list[ClusterFinding] = []
    for tier in (3, 2, 1):
        for _, f in matched_findings:
            if int(f.risk_score) == tier:
                ordered.append(f)

    rationale_keys: list[str] = []
    for f in ordered:
        for k in f.rationale_keys:
            if k not in rationale_keys:
                rationale_keys.append(k)

    if not rationale_keys:
        rationale_keys = ["no_symptoms_matched"]

    red_flags: list[RedFlag] = []
    seen_codes: set[str] = set()
    for f in ordered:
        for rf in evaluate_finding(f):
            if rf.code not in seen_codes:
                red_flags.append(rf)
                seen_codes.add(rf.code)

    rationale_en = " ".join(resolve(RATIONALE, rationale_keys, "en"))
    actions = resolve(ACTIONS, _actions_for(max_risk, primary_cluster), lang)

    return TriageOutcome(
        risk_score=max_risk,
        rationale_keys=tuple(rationale_keys),
        rationale_en=rationale_en,
        actions=tuple(actions),
        red_flags=tuple(red_flags),
        primary_cluster=primary_cluster,
    )
