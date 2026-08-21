"""Unit tests for 4-pillar emergency response, acute danger signs, and first aid protocols."""

import pytest
from app.services.sarvam_client import sarvam_client
from app.triage.engine import evaluate
from app.triage.first_aid import get_first_aid_protocol
from app.triage.types import SymptomPayload


def test_snake_bite_escalates_to_score_3_emergency():
    """Verify snake bite in Indic scripts escalates to Score 3 Red Emergency."""
    tamil_bite = "என் தம்பிக்கு பாம்பு கிடைச்சிருச்சு"
    payload = sarvam_client.extract_symptoms_rule_fallback(tamil_bite, language="ta")
    assert payload.acute_poisoning_or_bite is True

    outcome = evaluate(payload)
    assert outcome.risk_score == 3
    assert "snake_bite_emergency" in outcome.rationale_keys
    assert outcome.primary_cluster == "general"


def test_severe_trauma_and_burn_escalation():
    """Verify severe trauma and burns escalate to Score 3 Red Emergency."""
    burn_query = "Severe burn accident with fire"
    payload = sarvam_client.extract_symptoms_rule_fallback(burn_query, language="en")
    assert payload.severe_trauma is True

    outcome = evaluate(payload)
    assert outcome.risk_score == 3
    assert "severe_trauma_burn" in outcome.rationale_keys


def test_first_aid_protocol_snake_bite_selection():
    """Verify snake bite first aid protocol contains Anti-Snake Venom preparation and immobilized limb directive."""
    protocol = get_first_aid_protocol(["snake_bite_emergency"], language="ta")
    assert protocol["protocol_key"] == "snake_bite_emergency"
    assert "108-EMRI" in protocol["ticket_id"]
    assert protocol["cad_priority"] == "CRITICAL_P1"
    assert "Anti-Snake Venom" in protocol["phc_readiness"]
    assert len(protocol["steps"]) >= 4
    assert any("பாம்பு" in step or "அசைக்காமல்" in step or "கீறவோ" in step for step in protocol["steps"])


def test_first_aid_protocol_maternal_selection():
    """Verify maternal eclampsia emergency generates Janani ambulance and Magnesium Sulfate alert."""
    protocol = get_first_aid_protocol(["maternal_emergency"], language="hi", primary_cluster="maternal")
    assert protocol["protocol_key"] == "maternal_emergency"
    assert "Magnesium Sulfate" in protocol["phc_readiness"]
    assert any("बाईं करवट" in step or "गर्भवती" in step for step in protocol["steps"])


def test_zero_fabricated_vitals_enforced():
    """Verify that symptom extraction does NOT fabricate breathing rate or stool frequency."""
    cough_breath_text = "बच्चे को खांसी और सांस लेने में बहुत दिक्कत है"
    payload = sarvam_client.extract_symptoms_rule_fallback(cough_breath_text, language="hi")
    assert payload.difficulty_breathing is True
    # Clinical safety invariant: breathing rate must remain None unless explicitly measured by instrument
    assert payload.breathing_rate_per_min is None

    diarrhoea_text = "दो दिन से दस्त हो रहे हैं"
    payload_d = sarvam_client.extract_symptoms_rule_fallback(diarrhoea_text, language="hi")
    assert payload_d.diarrhoea is True
    # Clinical safety invariant: stool frequency must remain None unless explicitly counted by user
    assert payload_d.stool_frequency_per_day is None
