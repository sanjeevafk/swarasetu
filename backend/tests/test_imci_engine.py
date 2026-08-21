"""Unit tests for the deterministic WHO IMCI triage engine.

Ground-truth scenarios mirror src/data/mockSymptoms.ts:
  sc-1 Tamil  : child, mild fever 1 day, no flags            -> risk 1
  sc-2 Hindi  : child, cough + slight breathing difficulty 2d -> risk 2
  sc-3 Bengali: adult male, severe chest pain + haematemesis  -> risk 3

Plus edge cases across all four IMCI clusters and determinism guarantees.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.triage import (  # noqa: E402
    AGE_ADULT,
    AGE_CHILD,
    AGE_INFANT,
    AGE_NEONATE,
    RiskScore,
    SymptomPayload,
    evaluate,
)


# ---------------------------------------------------------------------------
# Ground-truth scenarios from src/data/mockSymptoms.ts
# ---------------------------------------------------------------------------


class TestGroundTruthScenarios:
    def test_scenario_1_tamil_mild_fever_child(self):
        """sc-1: 'My child has a mild fever. Since yesterday...' -> Score 1."""
        payload = SymptomPayload(
            age_group=AGE_CHILD,
            has_fever=True,
            fever_days=1,
        )
        outcome = evaluate(payload)
        assert int(outcome.risk_score) == 1
        assert outcome.rationale_keys == ("fever_self_care",)
        assert outcome.red_flags == ()
        assert outcome.primary_cluster == "fever"
        # Self-care must include home monitoring guidance.
        assert any("Monitor at home" in a or "paracetamol" in a.lower() for a in outcome.actions)

    def test_scenario_2_hindi_cough_breathing_difficulty_child(self):
        """sc-2: child cough + slight difficulty breathing for 2 days -> Score 2."""
        payload = SymptomPayload(
            age_group=AGE_CHILD,
            cough_days=2,
            difficulty_breathing=True,
        )
        outcome = evaluate(payload)
        assert int(outcome.risk_score) == 2
        assert outcome.primary_cluster == "respiratory"
        assert "breathing_difficulty_reported" in [f.code for f in outcome.red_flags]
        # ASHA dispatch action present.
        assert any("ASHA" in a for a in outcome.actions)

    def test_scenario_3_bengali_chest_pain_haematemesis_adult(self):
        """sc-3: adult male severe chest pain + vomiting blood -> Score 3."""
        payload = SymptomPayload(
            age_group=AGE_ADULT,
            chest_pain_severe=True,
            vomiting_blood=True,
        )
        outcome = evaluate(payload)
        assert int(outcome.risk_score) == 3
        assert outcome.primary_cluster == "general"
        codes = {f.code for f in outcome.red_flags}
        assert {"severe_chest_pain", "vomiting_blood"} <= codes
        # Emergency actions must include referral + ambulance.
        joined = " ".join(outcome.actions).lower()
        assert "phc" in joined and "ambulance" in joined


# ---------------------------------------------------------------------------
# Fever cluster edge cases
# ---------------------------------------------------------------------------


class TestFeverCluster:
    def test_neonatal_any_fever_is_emergency(self):
        payload = SymptomPayload(age_group=AGE_NEONATE, has_fever=True)
        assert evaluate(payload).risk_score == RiskScore.EMERGENCY_REFERRAL

    def test_neck_stiffness_meningitis_flag(self):
        payload = SymptomPayload(age_group=AGE_CHILD, has_fever=True, neck_stiffness=True)
        outcome = evaluate(payload)
        assert outcome.risk_score == RiskScore.EMERGENCY_REFERRAL
        assert "neck_stiffness_meningitis" in [f.code for f in outcome.red_flags]

    def test_febrile_convulsions_emergency(self):
        payload = SymptomPayload(age_group=AGE_CHILD, has_fever=True, convulsions=True)
        assert evaluate(payload).risk_score == RiskScore.EMERGENCY_REFERRAL

    def test_rash_with_fever_is_yellow(self):
        payload = SymptomPayload(age_group=AGE_CHILD, has_fever=True, rash_with_fever=True)
        outcome = evaluate(payload)
        assert outcome.risk_score == RiskScore.ASHA_DISPATCH
        assert "fever_with_rash" in [f.code for f in outcome.red_flags]

    def test_high_temperature_threshold(self):
        payload = SymptomPayload(age_group=AGE_CHILD, temperature_c=39.5)
        assert evaluate(payload).risk_score == RiskScore.ASHA_DISPATCH

    def test_prolonged_fever_over_seven_days(self):
        payload = SymptomPayload(age_group=AGE_CHILD, has_fever=True, fever_days=8)
        assert evaluate(payload).risk_score == RiskScore.ASHA_DISPATCH

    def test_malaria_endemic_area_dispatches_asha(self):
        payload = SymptomPayload(
            age_group=AGE_CHILD, has_fever=True, fever_days=2, malaria_risk_area=True
        )
        outcome = evaluate(payload)
        assert outcome.risk_score == RiskScore.ASHA_DISPATCH
        assert any("malaria" in k for k in outcome.rationale_keys)

    def test_subfebrile_temperature_not_treated_as_fever(self):
        payload = SymptomPayload(age_group=AGE_CHILD, temperature_c=37.0)
        outcome = evaluate(payload)
        assert int(outcome.risk_score) == 1
        assert outcome.primary_cluster == "none"


# ---------------------------------------------------------------------------
# Respiratory cluster edge cases
# ---------------------------------------------------------------------------


class TestRespiratoryCluster:
    @pytest.mark.parametrize(
        "age,rate",
        [
            (AGE_NEONATE, 60),
            (AGE_INFANT, 50),
            (AGE_CHILD, 40),
        ],
    )
    def test_fast_breathing_thresholds_trigger_yellow(self, age, rate):
        payload = SymptomPayload(age_group=age, breathing_rate_per_min=rate)
        outcome = evaluate(payload)
        assert outcome.risk_score == RiskScore.ASHA_DISPATCH

    @pytest.mark.parametrize(
        "age,rate",
        [(AGE_NEONATE, 55), (AGE_INFANT, 45), (AGE_CHILD, 35)],
    )
    def test_normal_breathing_rates_do_not_escalate(self, age, rate):
        payload = SymptomPayload(age_group=age, cough_days=2, breathing_rate_per_min=rate)
        assert evaluate(payload).risk_score == RiskScore.SELF_CARE

    @pytest.mark.parametrize("flag", ["stridor", "chest_indrawing"])
    def test_severe_distress_is_red(self, flag):
        kwargs = {flag: True}
        payload = SymptomPayload(age_group=AGE_CHILD, **kwargs)
        outcome = evaluate(payload)
        assert outcome.risk_score == RiskScore.EMERGENCY_REFERRAL
        assert outcome.primary_cluster == "respiratory"

    def test_prolonged_cough_over_14_days_is_yellow(self):
        payload = SymptomPayload(age_group=AGE_CHILD, cough_days=21)
        assert evaluate(payload).risk_score == RiskScore.ASHA_DISPATCH


# ---------------------------------------------------------------------------
# Diarrhoea & dehydration cluster edge cases
# ---------------------------------------------------------------------------


class TestDiarrhoeaCluster:
    def test_severe_dehydration_two_signs_is_red(self):
        payload = SymptomPayload(
            age_group=AGE_CHILD,
            diarrhoea=True,
            stool_frequency_per_day=10,
            sunken_eyes=True,
            skin_pinch_slow=True,
        )
        outcome = evaluate(payload)
        assert outcome.risk_score == RiskScore.EMERGENCY_REFERRAL
        assert outcome.primary_cluster == "diarrhoea"

    def test_dysentery_blood_in_stool_is_yellow(self):
        payload = SymptomPayload(age_group=AGE_CHILD, diarrhoea=True, blood_in_stool=True)
        outcome = evaluate(payload)
        assert outcome.risk_score == RiskScore.ASHA_DISPATCH
        assert "blood_in_stool_dysentery" in [f.code for f in outcome.red_flags]

    def test_some_dehydration_single_sign_is_yellow(self):
        payload = SymptomPayload(
            age_group=AGE_CHILD, diarrhoea=True, stool_frequency_per_day=5, sunken_eyes=True
        )
        assert evaluate(payload).risk_score == RiskScore.ASHA_DISPATCH

    def test_no_dehydration_is_green(self):
        payload = SymptomPayload(
            age_group=AGE_CHILD, diarrhoea=True, stool_frequency_per_day=4
        )
        outcome = evaluate(payload)
        assert int(outcome.risk_score) == 1
        assert any("ORS" in a for a in outcome.actions)


# ---------------------------------------------------------------------------
# Maternal danger-sign cluster edge cases
# ---------------------------------------------------------------------------


class TestMaternalCluster:
    def test_pre_eclampsia_headache_blurred_vision_is_red(self):
        payload = SymptomPayload(
            pregnant=True, severe_headache=True, blurred_vision=True
        )
        outcome = evaluate(payload)
        assert outcome.risk_score == RiskScore.EMERGENCY_REFERRAL
        assert "pre_eclampsia" in [f.code for f in outcome.red_flags]

    def test_vaginal_bleeding_is_red(self):
        payload = SymptomPayload(pregnant=True, vaginal_bleeding=True)
        assert evaluate(payload).risk_score == RiskScore.EMERGENCY_REFERRAL

    def test_reduced_fetal_movement_is_red(self):
        payload = SymptomPayload(pregnant=True, reduced_fetal_movement=True)
        assert evaluate(payload).risk_score == RiskScore.EMERGENCY_REFERRAL

    def test_maternal_convulsions_are_red(self):
        payload = SymptomPayload(pregnant=True, convulsions=True)
        assert evaluate(payload).risk_score == RiskScore.EMERGENCY_REFERRAL

    def test_lone_headache_in_pregnancy_is_yellow(self):
        payload = SymptomPayload(pregnant=True, severe_headache=True)
        assert evaluate(payload).risk_score == RiskScore.ASHA_DISPATCH

    def test_non_pregnant_headache_ignored_by_maternal_cluster(self):
        payload = SymptomPayload(pregnant=False, severe_headache=True, blurred_vision=True)
        outcome = evaluate(payload)
        assert outcome.primary_cluster != "maternal"


# ---------------------------------------------------------------------------
# Cross-cluster escalation & general danger signs
# ---------------------------------------------------------------------------


class TestCrossClusterEscalation:
    def test_general_danger_sign_overrides_low_clusters(self):
        """A red fever case with an unrelated green respiratory finding stays red."""
        payload = SymptomPayload(
            age_group=AGE_CHILD,
            has_fever=True,
            neck_stiffness=True,
            cough_days=2,
        )
        outcome = evaluate(payload)
        assert outcome.risk_score == RiskScore.EMERGENCY_REFERRAL

    def test_unable_to_drink_is_general_danger_sign(self):
        payload = SymptomPayload(age_group=AGE_INFANT, unable_to_drink_or_breastfeed=True)
        assert evaluate(payload).risk_score == RiskScore.EMERGENCY_REFERRAL

    def test_max_risk_wins_across_multiple_clusters(self):
        payload = SymptomPayload(
            age_group=AGE_CHILD,
            diarrhoea=True,
            sunken_eyes=True,
            skin_pinch_slow=True,   # red via diarrhoea
            has_fever=True,         # yellow via fever
        )
        outcome = evaluate(payload)
        assert outcome.risk_score == RiskScore.EMERGENCY_REFERRAL

    def test_empty_payload_is_safe_green(self):
        outcome = evaluate(SymptomPayload())
        assert int(outcome.risk_score) == 1
        assert outcome.rationale_keys == ("no_symptoms_matched",)


# ---------------------------------------------------------------------------
# Determinism guarantees
# ---------------------------------------------------------------------------


class TestDeterminism:
    PAYLOADS = [
        SymptomPayload(),
        SymptomPayload(has_fever=True, fever_days=1),
        SymptomPayload(cough_days=2, difficulty_breathing=True),
        SymptomPayload(chest_pain_severe=True, vomiting_blood=True),
        SymptomPayload(diarrhoea=True, blood_in_stool=True, restless_irritable=True),
        SymptomPayload(pregnant=True, vaginal_bleeding=True),
    ]

    @pytest.mark.parametrize(
        "payload",
        PAYLOADS,
        ids=[
            "empty",
            "mild-fever",
            "resp-difficulty",
            "chest-pain-emergency",
            "dysentery",
            "maternal-bleeding",
        ],
    )
    def test_repeated_evaluation_identical(self, payload):
        first = evaluate(payload)
        for _ in range(10):
            again = evaluate(payload)
            assert again.as_dict() == first.as_dict()

    def test_language_only_changes_text_not_decision(self):
        payload = SymptomPayload(has_fever=True, neck_stiffness=True)
        en = evaluate(payload, language="en")
        hi = evaluate(payload, language="hi")
        assert en.risk_score == hi.risk_score
        assert en.rationale_keys == hi.rationale_keys
        assert en.actions != hi.actions  # localized action text differs

    def test_localized_output_supported_languages(self):
        payload = SymptomPayload(has_fever=True, fever_days=9)
        for lang in ("en", "hi", "ta", "bn"):
            outcome = evaluate(payload, language=lang)
            assert outcome.actions and all(outcome.actions)
