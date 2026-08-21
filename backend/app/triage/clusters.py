"""Syndromic cluster evaluators for the WHO IMCI decision tree.

Each evaluator is a pure function of SymptomPayload -> ClusterFinding.
Evaluation order inside every cluster is a fixed severity ladder so outcomes
are fully deterministic and auditable.
"""

from app.triage.types import (
    AGE_ADULT,
    AGE_ADOLESCENT,
    AGE_CHILD,
    AGE_INFANT,
    AGE_NEONATE,
    COUGH_URI_DAYS_MAX,
    FAST_BREATHING_THRESHOLDS,
    FEVER_THRESHOLD_C,
    HIGH_FEVER_C,
    ClusterFinding,
    RiskScore,
    STOOL_SEVERE_DIARRHOEA_PER_DAY,
    SymptomPayload,
)

__all__ = [
    "evaluate_general_danger_signs",
    "evaluate_fever",
    "evaluate_respiratory",
    "evaluate_diarrhoea",
    "evaluate_maternal",
    "evaluate_adhoc_request",
]


def evaluate_adhoc_request(p: SymptomPayload) -> ClusterFinding:
    """Non-symptom intent: supply/logistics/advisory requests.

    Vitamin, vaccination-schedule and medicine queries carry no clinical
    danger sign but still warrant an ASHA worker touchpoint (level 2).
    Max-risk aggregation keeps every red-flag path dominant over this.
    """
    if p.advice_request:
        return ClusterFinding(
            cluster="general",
            risk_score=RiskScore.ASHA_DISPATCH,
            rationale_keys=("adhoc_supply_request",),
        )
    return ClusterFinding(cluster="general", risk_score=RiskScore.SELF_CARE, matched=False)


def evaluate_general_danger_signs(p: SymptomPayload) -> ClusterFinding:
    """IMCI general danger signs apply across all ages and override everything.

    Includes adult emergencies from ground-truth demo scenario 3
    (severe chest pain, haematemesis) which route to emergency referral.
    """
    checks = [
        (p.convulsions, "convulsions", "Convulsions / fits"),
        (p.unconscious, "unconscious", "Unconsciousness or lethargy"),
        (p.unable_to_drink_or_breastfeed, "unable_to_drink", "Unable to drink or breastfeed"),
        (p.vomiting_everything, "vomiting_everything", "Vomiting everything"),
        (p.chest_pain_severe, "severe_chest_pain", "Severe chest pain"),
        (p.vomiting_blood, "vomiting_blood", "Vomiting blood (haematemesis)"),
        (p.acute_poisoning_or_bite, "snake_bite_emergency", "Snake bite / acute poisoning"),
        (p.severe_trauma, "severe_trauma_burn", "Severe trauma / burn / deep injury"),
    ]

    codes: list[str] = []
    for present, code, desc in checks:
        if present:
            codes.append(code)

    if not codes:
        return ClusterFinding(cluster="general", risk_score=RiskScore.SELF_CARE, matched=False)

    keys = ["general_danger_sign"]
    if "severe_chest_pain" in codes or "vomiting_blood" in codes:
        keys.append("severe_chest_pain")
    if "snake_bite_emergency" in codes:
        keys.append("snake_bite_emergency")
    if "severe_trauma_burn" in codes:
        keys.append("severe_trauma_burn")


    return ClusterFinding(
        cluster="general",
        risk_score=RiskScore.EMERGENCY_REFERRAL,
        rationale_keys=tuple(keys),
        red_flag_codes=tuple(codes),
    )


def evaluate_fever(p: SymptomPayload) -> ClusterFinding:
    """Fever cluster: meningitis flag, febrile convulsions, dengue-like rash,
    malaria endemicity, high/prolonged fever thresholds."""
    measured_fever = p.temperature_c is not None and p.temperature_c >= FEVER_THRESHOLD_C
    if not (p.has_fever or measured_fever):
        return ClusterFinding(cluster="fever", risk_score=RiskScore.SELF_CARE, matched=False)

    # Ladder rung 1: neonatal fever (<2 months) is always serious per IMCI.
    if p.age_group == AGE_NEONATE:
        return ClusterFinding(
            cluster="fever",
            risk_score=RiskScore.EMERGENCY_REFERRAL,
            rationale_keys=("neonatal_fever",),
            red_flag_codes=("neonatal_fever",),
        )

    # Rung 2: neck stiffness => suspected meningitis.
    if p.neck_stiffness:
        return ClusterFinding(
            cluster="fever",
            risk_score=RiskScore.EMERGENCY_REFERRAL,
            rationale_keys=("fever_neck_stiffness_meningitis",),
            red_flag_codes=("neck_stiffness_meningitis",),
        )

    # Rung 3: convulsions with fever (kept explicit so the cluster is
    # self-contained when evaluated alone).
    if p.convulsions:
        return ClusterFinding(
            cluster="fever",
            risk_score=RiskScore.EMERGENCY_REFERRAL,
            rationale_keys=("fever_convulsions",),
            red_flag_codes=("febrile_convulsions",),
        )

    red_flags: list[str] = []
    keys: list[str] = []

    # Rung 4: rash with fever => possible dengue/measles complication.
    if p.rash_with_fever:
        red_flags.append("fever_with_rash")
        keys.append("fever_rash_urgent")

    high_or_prolonged = (
        (p.temperature_c is not None and p.temperature_c >= HIGH_FEVER_C)
        or (p.fever_days is not None and p.fever_days > 7)
    )
    malaria_suspect = p.malaria_risk_area

    if not (red_flags or high_or_prolonged or malaria_suspect):
        return ClusterFinding(
            cluster="fever",
            risk_score=RiskScore.SELF_CARE,
            rationale_keys=("fever_self_care",),
        )

    # Rung 5: high/prolonged fever and/or malaria-prone area => CHW dispatch.
    if high_or_prolonged:
        keys.append("fever_high_or_prolonged")
    if malaria_suspect:
        keys.append("malaria_risk_fever")

    return ClusterFinding(
        cluster="fever",
        risk_score=RiskScore.ASHA_DISPATCH,
        rationale_keys=tuple(keys),
        red_flag_codes=tuple(red_flags),
    )


def evaluate_respiratory(p: SymptomPayload) -> ClusterFinding:
    """Respiratory cluster: URI vs pneumonia vs severe acute distress.

    Severity ladder (deterministic):
      stridor OR chest indrawing                    -> RED (3)
      fast breathing for age band                   -> YELLOW (2)
      reported difficulty breathing                 -> YELLOW (2)
      cough >14 days                                -> YELLOW (2)
      cough <=14 days with no other signs           -> GREEN (1)
      wheezing only                                 -> GREEN (1)
    """
    resp_present = (
        p.cough_days is not None
        or p.difficulty_breathing
        or p.breathing_rate_per_min is not None
        or p.chest_indrawing
        or p.stridor
        or p.wheezing
    )
    if not resp_present:
        return ClusterFinding(cluster="respiratory", risk_score=RiskScore.SELF_CARE, matched=False)

    if p.stridor:
        return ClusterFinding(
            cluster="respiratory",
            risk_score=RiskScore.EMERGENCY_REFERRAL,
            rationale_keys=("resp_severe_distress",),
            red_flag_codes=("stridor",),
        )

    if p.chest_indrawing:
        return ClusterFinding(
            cluster="respiratory",
            risk_score=RiskScore.EMERGENCY_REFERRAL,
            rationale_keys=("resp_severe_distress",),
            red_flag_codes=("chest_indrawing",),
        )

    threshold = FAST_BREATHING_THRESHOLDS.get(
        p.age_group if p.age_group in FAST_BREATHING_THRESHOLDS else AGE_CHILD
    )
    fast_breathing = (
        threshold is not None
        and p.breathing_rate_per_min is not None
        and p.breathing_rate_per_min >= threshold
    )
    if fast_breathing:
        return ClusterFinding(
            cluster="respiratory",
            risk_score=RiskScore.ASHA_DISPATCH,
            rationale_keys=("resp_fast_breathing_pneumonia",),
            red_flag_codes=("fast_breathing",),
        )

    if p.difficulty_breathing:
        # Reported breathing difficulty without measurable tachypnoea:
        # moderate concern requiring CHW assessment (demo scenario 2).
        return ClusterFinding(
            cluster="respiratory",
            risk_score=RiskScore.ASHA_DISPATCH,
            rationale_keys=("resp_fast_breathing_pneumonia",),
            red_flag_codes=("breathing_difficulty_reported",),
        )

    if p.cough_days is not None:
        if p.cough_days <= COUGH_URI_DAYS_MAX:
            return ClusterFinding(
                cluster="respiratory",
                risk_score=RiskScore.SELF_CARE,
                rationale_keys=("resp_uri_self_care",),
            )
        return ClusterFinding(
            cluster="respiratory",
            risk_score=RiskScore.ASHA_DISPATCH,
            rationale_keys=("resp_fast_breathing_pneumonia",),
            red_flag_codes=("prolonged_cough",),
        )

    return ClusterFinding(
        cluster="respiratory",
        risk_score=RiskScore.SELF_CARE,
        rationale_keys=("resp_uri_self_care",),
    )


def evaluate_diarrhoea(p: SymptomPayload) -> ClusterFinding:
    """Diarrhoea & dehydration cluster per IMCI treatment plans A/B/C.

    Ladder:
      severe dehydration (sunken eyes AND slow skin pinch)          -> RED (3)
      some dehydration (restless/irritable OR one sign), dysentery,
      or heavy stool frequency                                      -> YELLOW (2)
      no dehydration                                                -> GREEN (1)
    """
    if not p.diarrhoea and p.stool_frequency_per_day is None:
        return ClusterFinding(cluster="diarrhoea", risk_score=RiskScore.SELF_CARE, matched=False)

    severe_sign_count = int(p.sunken_eyes) + int(p.skin_pinch_slow)
    if severe_sign_count == 2:
        return ClusterFinding(
            cluster="diarrhoea",
            risk_score=RiskScore.EMERGENCY_REFERRAL,
            rationale_keys=("diarrhoea_severe_dehydration",),
            red_flag_codes=("severe_dehydration",),
        )

    dysentery = p.blood_in_stool
    heavy_frequency = (
        p.stool_frequency_per_day is not None
        and p.stool_frequency_per_day >= STOOL_SEVERE_DIARRHOEA_PER_DAY
    )
    some_dehydration = bool(
        p.restless_irritable or severe_sign_count == 1 or p.unable_to_drink_or_breastfeed
    )

    if some_dehydration or dysentery or heavy_frequency:
        red_flags: list[str] = []
        if dysentery:
            red_flags.append("blood_in_stool_dysentery")
        if some_dehydration:
            red_flags.append("some_dehydration")
        if heavy_frequency:
            red_flags.append("frequent_stools")
        return ClusterFinding(
            cluster="diarrhoea",
            risk_score=RiskScore.ASHA_DISPATCH,
            rationale_keys=("diarrhoea_some_dehydration_or_dysentery",),
            red_flag_codes=tuple(red_flags),
        )

    return ClusterFinding(
        cluster="diarrhoea",
        risk_score=RiskScore.SELF_CARE,
        rationale_keys=("diarrhoea_no_dehydration",),
    )


def evaluate_maternal(p: SymptomPayload) -> ClusterFinding:
    """Maternal danger-sign cluster (pregnancy-related obstetric emergencies).

    Any of: severe headache WITH blurred vision (pre-eclampsia), vaginal
    bleeding, reduced fetal movement, or convulsion in pregnancy -> RED (3).
    A lone headache/visual symptom -> YELLOW (2).
    """
    if not p.pregnant:
        return ClusterFinding(cluster="maternal", risk_score=RiskScore.SELF_CARE, matched=False)

    if p.severe_headache and p.blurred_vision:
        return ClusterFinding(
            cluster="maternal",
            risk_score=RiskScore.EMERGENCY_REFERRAL,
            rationale_keys=("maternal_emergency",),
            red_flag_codes=("pre_eclampsia",),
        )
    if p.severe_headache or p.blurred_vision:
        return ClusterFinding(
            cluster="maternal",
            risk_score=RiskScore.ASHA_DISPATCH,
            rationale_keys=("maternal_emergency",),
            red_flag_codes=("maternal_headache_or_visual",),
        )
    if p.vaginal_bleeding:
        return ClusterFinding(
            cluster="maternal",
            risk_score=RiskScore.EMERGENCY_REFERRAL,
            rationale_keys=("maternal_emergency",),
            red_flag_codes=("vaginal_bleeding",),
        )
    if p.reduced_fetal_movement:
        return ClusterFinding(
            cluster="maternal",
            risk_score=RiskScore.EMERGENCY_REFERRAL,
            rationale_keys=("maternal_emergency",),
            red_flag_codes=("reduced_fetal_movement",),
        )
    if p.convulsions:
        return ClusterFinding(
            cluster="maternal",
            risk_score=RiskScore.EMERGENCY_REFERRAL,
            rationale_keys=("maternal_emergency",),
            red_flag_codes=("eclampsia_convulsions",),
        )
    return ClusterFinding(cluster="maternal", risk_score=RiskScore.SELF_CARE, matched=True)


# Re-export for engine convenience.
AGE_BANDS = (AGE_NEONATE, AGE_INFANT, AGE_CHILD, AGE_ADOLESCENT, AGE_ADULT)
