"""Tests for omnichannel WhatsApp webhook, Sarvam integration, and voice endpoints."""

from __future__ import annotations

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.sarvam_client import sarvam_client
from app.services.twilio_client import twilio_client

client = TestClient(app)


def test_sarvam_client_fallback_extraction():
    """Verify rule-based symptom extraction fallback produces correct clinical indicators."""
    text_hindi = "बच्चे को बहुत तेज बुखार है और गर्दन में अकड़न है"
    payload = sarvam_client.extract_symptoms_rule_fallback(text_hindi, language="hi")
    assert payload.has_fever is True
    assert payload.neck_stiffness is True
    assert payload.language == "hi"



def test_twilio_mock_dispatch():
    """Verify twilio client provides graceful mock return when API keys are not live."""
    import asyncio
    res = asyncio.run(twilio_client.send_sms(to_number="+919876543210", body="Test ASHA Alert"))
    assert "sid" in res or "status" in res


def test_whatsapp_webhook_text_triage():
    """Verify incoming text message over WhatsApp generates TwiML response with triage advice."""
    data = {
        "From": "whatsapp:+919876543210",
        "Body": "My child has mild fever since yesterday",
    }
    response = client.post("/channels/whatsapp", data=data)
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "SwaraSetu Triage Result" in response.text
    assert "<Response>" in response.text


def test_whatsapp_webhook_emergency_triage():
    """Verify emergency symptom triggers red flag and nearest PHC details in TwiML response."""
    data = {
        "From": "whatsapp:+919876543210",
        "Body": "Patient is unconscious and having severe chest pain and vomiting blood",
    }
    response = client.post("/channels/whatsapp", data=data)
    assert response.status_code == 200
    assert "Nearest PHC" in response.text or "Emergency" in response.text


def test_voice_transcribe_endpoint():
    """Verify voice transcription testing endpoint accepts audio files."""
    dummy_wav = io.BytesIO(b"RIFF....WAVEfmt ....data....")
    files = {"file": ("test.wav", dummy_wav, "audio/wav")}
    response = client.post("/channels/voice/transcribe?language=hi", files=files)

    assert response.status_code == 200
    res_data = response.json()
    assert "transcript" in res_data


def test_whatsapp_webhook_empty_message_returns_retry_prompt():
    """Verify empty/inaudible WhatsApp payload returns safe retry prompt instead of fake symptoms."""
    data = {
        "From": "whatsapp:+919876543210",
        "Body": "",
    }
    response = client.post("/channels/whatsapp", data=data)
    assert response.status_code == 200
    assert "could not hear your voice note clearly" in response.text or "SwaraSetu Healthcare" in response.text
    assert "Fever and cough" not in response.text

