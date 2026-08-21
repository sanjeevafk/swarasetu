"""Omnichannel routers for WhatsApp webhooks and direct voice audio processing."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated
from xml.sax.saxutils import escape as xml_escape

import httpx
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.phc import AshaAssignment
from app.schemas.triage import SymptomPayloadIn, TriageEvaluateRequest
from app.triage.types import RiskScore, SymptomPayload
from app.services.phc_service import nearest_phcs
from app.services.sarvam_client import sarvam_client
from app.services.triage_service import evaluate_and_log
from app.services.twilio_client import twilio_client
from dataclasses import asdict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channels", tags=["Omnichannel & Voice"])


def _build_twiml_response(message: str) -> PlainTextResponse:
    """Safely build a TwiML XML response with full character escaping."""
    safe_body = xml_escape(message.strip())
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>
        <Body>{safe_body}</Body>
    </Message>
</Response>"""
    return PlainTextResponse(content=xml_content, media_type="application/xml")


@router.post("/whatsapp")
async def handle_whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Twilio Webhook endpoint receiving incoming patient WhatsApp messages/voice notes.
    Clinically safe: if audio is inaudible or fails to download, returns a retry prompt.
    """
    form_data = await request.form()
    sender = str(form_data.get("From", "whatsapp:+919876543210"))
    incoming_text = str(form_data.get("Body", "")).strip()
    media_url = form_data.get("MediaUrl0")
    
    # Location data if user shared GPS pin over WhatsApp
    latitude_str = form_data.get("Latitude")
    longitude_str = form_data.get("Longitude")
    latitude = float(latitude_str) if latitude_str else None
    longitude = float(longitude_str) if longitude_str else None

    transcript = incoming_text
    detected_language = "hi"
    is_inaudible = False

    # If incoming payload is a voice note / audio file:
    if media_url:
        try:
            auth = None
            if settings.twilio_account_sid and settings.twilio_auth_token:
                username = settings.twilio_api_key_sid or settings.twilio_account_sid
                auth = (username, settings.twilio_auth_token)

            async with httpx.AsyncClient(timeout=25.0) as client:
                audio_res = await client.get(str(media_url), auth=auth)
                audio_res.raise_for_status()
                asr_result = await sarvam_client.transcribe_audio(
                    audio_bytes=audio_res.content,
                    filename="whatsapp_voice.ogg",
                )
                transcript = asr_result.get("transcript", "").strip()
                lang_str = asr_result.get("language_code", "hi")
                detected_language = lang_str if lang_str in ("en", "hi", "ta", "bn") else "hi"
                if not transcript or asr_result.get("inaudible"):
                    is_inaudible = True
        except Exception as e:
            logger.warning("Failed to process WhatsApp audio: %s", e)
            is_inaudible = True

    # If audio was inaudible or empty text sent, respond safely without fabricating clinical cases
    if is_inaudible or not transcript:
        safe_retry_msg = (
            "🩺 SwaraSetu Healthcare\n\n"
            "We could not hear your voice note clearly.\n"
            "Please send another audio message describing your symptoms, or call the National Health Helpline at 104 (or 108 for emergency)."
        )
        return _build_twiml_response(safe_retry_msg)

    # Extract symptoms deterministically without hallucination
    payload = sarvam_client.extract_symptoms_rule_fallback(transcript, language=detected_language)
    client_uuid = f"wa-{uuid.uuid4().hex[:12]}"

    # Run deterministic IMCI triage
    triage_req = TriageEvaluateRequest(
        payload=SymptomPayloadIn(**asdict(payload)),
        client_uuid=client_uuid,
        latitude=latitude,
        longitude=longitude,
    )
    res = evaluate_and_log(db=db, request=triage_req)
    outcome = res["outcome"]
    directive = res["directive"]

    # Build patient reply message
    reply_text = f"🩺 SwaraSetu Triage Result\n\n{directive.message_en}\n\nDecision: {outcome.rationale_en}"

    # If Score 2 (ASHA Dispatch), look up local ASHA worker contact dynamically
    if outcome.risk_score == int(RiskScore.ASHA_DISPATCH):
        asha_record = db.execute(select(AshaAssignment).limit(1)).scalar_one_or_none()
        asha_phone = asha_record.phone if asha_record else "+919999988888"
        
        asha_alert = (
            f"🚨 ASHA ALERT: New moderate-risk case reported from {sender}.\n"
            f"Symptoms: {', '.join(outcome.rationale_keys) if outcome.rationale_keys else 'Moderate symptoms'}\n"
            f"Action: Home assessment required within 24 hours."
        )
        await twilio_client.send_sms(to_number=asha_phone, body=asha_alert)

    # If Score 3 (Emergency), append nearest PHC info if coordinates present
    if outcome.risk_score == int(RiskScore.EMERGENCY_REFERRAL):
        search_lat = latitude or 28.6139
        search_lon = longitude or 77.2090
        phc_list = nearest_phcs(db=db, lat=search_lat, lon=search_lon, limit=1)
        if phc_list:
            phc = phc_list[0]
            reply_text += f"\n\n📍 Nearest PHC: {phc.name}\n📞 Emergency Contact: {phc.phone}\nDistance: ~{phc.distance_km:.1f} km (Open: {phc.hours})"

    return _build_twiml_response(reply_text)


@router.post("/voice/transcribe")
async def transcribe_voice_file(
    file: UploadFile = File(...),
    language: str = "hi",
) -> dict:
    """Direct testing endpoint: upload an audio file (.wav/.mp3/.ogg) to transcribe via Sarvam ASR."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file provided.")

    return await sarvam_client.transcribe_audio(
        audio_bytes=audio_bytes,
        filename=file.filename or "audio.wav",
        language_code=language,
    )


@router.post("/voice/synthesize")
async def synthesize_voice(
    text: Annotated[str, Form(...)],
    language: str = "hi",
) -> dict:
    """Direct testing endpoint: synthesize Indic text into audio base64 via Sarvam TTS."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    audio_base64 = await sarvam_client.synthesize_speech(text=text, target_language=language)
    if not audio_base64:
        raise HTTPException(status_code=500, detail="Speech synthesis failed or API not configured.")
    return {
        "text": text,
        "language": language,
        "audio_base64": audio_base64,
    }


@router.post("/voice/triage-audio")
async def end_to_end_voice_triage(
    file: UploadFile = File(...),
    language: str = "hi",
    db: Session = Depends(get_db),
) -> dict:
    """Full End-to-End Voice Pipeline: Audio In -> Sarvam ASR -> Clinical Extraction -> IMCI Triage -> TTS Voice Out."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file provided.")

    # 1. Transcribe
    asr_res = await sarvam_client.transcribe_audio(
        audio_bytes=audio_bytes,
        filename=file.filename or "recording.wav",
        language_code=language,
    )
    transcript = asr_res.get("transcript", "")
    if not transcript or asr_res.get("inaudible"):
        return {
            "transcript": "",
            "inaudible": True,
            "message": "Could not recognize audio clearly. Please repeat.",
            "response_audio_base64": None,
        }

    # 2. Extract symptoms
    payload = sarvam_client.extract_symptoms_rule_fallback(transcript, language=language)
    client_uuid = f"voice-{uuid.uuid4().hex[:12]}"

    # 3. Deterministic IMCI Triage
    triage_req = TriageEvaluateRequest(
        payload=SymptomPayloadIn(**asdict(payload)),
        client_uuid=client_uuid,
    )
    triage_res = evaluate_and_log(db=db, request=triage_req)
    outcome = triage_res["outcome"]
    directive = triage_res["directive"]
    nearest_phc = triage_res.get("nearest_phc")

    # 4. Synthesize voice response
    voice_audio_base64 = await sarvam_client.synthesize_speech(
        text=directive.message_en,
        target_language=language,
    )

    return {
        "transcript": transcript,
        "extracted_payload": asdict(payload),
        "triage_outcome": outcome.model_dump(),
        "directive": directive.model_dump(),
        "nearest_phc": nearest_phc.model_dump() if nearest_phc else None,
        "response_audio_base64": voice_audio_base64,
    }
