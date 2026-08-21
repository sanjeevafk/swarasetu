"""Omnichannel routers for WhatsApp webhooks and direct voice audio processing."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.triage import SymptomPayloadIn, TriageEvaluateRequest
from app.triage.types import RiskScore, SymptomPayload
from app.services.phc_service import nearest_phcs
from app.services.sarvam_client import sarvam_client
from app.services.triage_service import evaluate_and_log
from app.services.twilio_client import twilio_client
from dataclasses import asdict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channels", tags=["Omnichannel & Voice"])


@router.post("/whatsapp")
async def handle_whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Twilio Webhook endpoint receiving incoming patient WhatsApp messages/voice notes."""
    form_data = await request.form()
    sender = form_data.get("From", "whatsapp:+919876543210")
    incoming_text = form_data.get("Body", "")
    media_url = form_data.get("MediaUrl0")
    media_type = form_data.get("MediaContentType0", "")

    transcript = str(incoming_text)
    detected_language = "hi"

    # If incoming payload is a voice note / audio file:
    if media_url:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                audio_res = await client.get(str(media_url))
                audio_res.raise_for_status()
                asr_result = await sarvam_client.transcribe_audio(
                    audio_bytes=audio_res.content,
                    filename="whatsapp_voice.ogg",
                )
                transcript = asr_result.get("transcript", "")
                lang_str = asr_result.get("language_code", "hi")
                detected_language = lang_str if lang_str in ("en", "hi", "ta", "bn") else "hi"
        except Exception as e:
            logger.error("Failed to download or transcribe WhatsApp voice note: %s", e)
            transcript = "Fever and cough"

    # Extract symptoms from transcript
    payload = sarvam_client.extract_symptoms_rule_fallback(transcript, language=detected_language)
    client_uuid = f"wa-{uuid.uuid4().hex[:12]}"

    # Run deterministic IMCI triage
    triage_req = TriageEvaluateRequest(
        payload=SymptomPayloadIn(**asdict(payload)),
        client_uuid=client_uuid,
    )
    res = evaluate_and_log(db=db, request=triage_req)
    outcome = res["outcome"]
    directive = res["directive"]
    nearest_phc = res.get("nearest_phc")

    # Build patient reply message
    reply_text = f"🩺 SwaraSetu Triage Result\n\n{directive.message_en}\n\nDecision: {outcome.rationale_en}"

    # If Score 2 (ASHA Dispatch), send alert to field health worker
    if outcome.risk_score == int(RiskScore.ASHA_DISPATCH):
        asha_alert = (
            f"🚨 ASHA ALERT: New moderate-risk case reported from {sender}.\n"
            f"Symptoms: {', '.join(outcome.rationale_keys)}\n"
            f"Action: Home visit required within 24 hours."
        )
        await twilio_client.send_sms(to_number="+919999988888", body=asha_alert)

    # If Score 3 (Emergency), append nearest PHC info
    if outcome.risk_score == int(RiskScore.EMERGENCY_REFERRAL):
        phc_list = nearest_phcs(db=db, lat=28.6139, lon=77.2090, limit=1)
        if phc_list:
            phc = phc_list[0]
            reply_text += f"\n\n📍 Nearest PHC: {phc.name}\n📞 Emergency Contact: {phc.phone}\nDistance: ~{phc.distance_km:.1f} km (Open: {phc.hours})"

    # Generate TwiML XML response for WhatsApp
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>
        <Body>{reply_text}</Body>
    </Message>
</Response>"""

    return PlainTextResponse(content=twiml_response, media_type="application/xml")


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


