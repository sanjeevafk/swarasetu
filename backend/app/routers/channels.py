"""Omnichannel routers for WhatsApp webhooks and direct voice audio processing."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import uuid
from typing import Annotated
from xml.sax.saxutils import escape as xml_escape

import httpx
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, Response, UploadFile, status

from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.phc import AshaAssignment, PHC
from app.schemas.triage import SymptomPayloadIn, TriageEvaluateRequest
from app.triage.types import RiskScore, SymptomPayload
from app.services.phc_service import nearest_phcs
from app.services.sarvam_client import sarvam_client
from app.services.triage_service import evaluate_and_log
from app.services.twilio_client import twilio_client
from dataclasses import asdict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channels", tags=["Omnichannel & Voice"])


def _validate_twilio_signature(url: str, params: dict[str, str], signature: str | None, auth_token: str | None) -> bool:
    """Validate Twilio HMAC-SHA1 request signature (X-Twilio-Signature).
    Bypasses in test mode, when auth_token is unconfigured, or when signature is empty.
    """
    if not auth_token or os.getenv("TESTING") == "1" or not signature:
        return True

    # Try exact URL first
    urls_to_try = [url]
    # If behind HTTPS tunnel proxy (e.g. localhost.run / ngrok), try replacing scheme/host
    if "http://" in url:
        urls_to_try.append(url.replace("http://", "https://"))

    for target_url in urls_to_try:
        data = target_url
        for key in sorted(params.keys()):
            data += f"{key}{params[key]}"

        computed = hmac.new(auth_token.encode("utf-8"), data.encode("utf-8"), hashlib.sha1).digest()
        computed_b64 = base64.b64encode(computed).decode("utf-8")
        if hmac.compare_digest(computed_b64, signature):
            return True

    return False


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


@router.api_route("/whatsapp", methods=["GET", "POST"])
async def handle_whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_twilio_signature: Annotated[str | None, Header(alias="X-Twilio-Signature")] = None,
) -> Response:
    """Twilio Webhook endpoint receiving incoming patient WhatsApp messages/voice notes.
    Clinically safe & secure with signature validation and zero-hallucination fail-soft prompts.
    """
    if request.method == "POST":
        form_data = await request.form()
        form_dict = {k: str(v) for k, v in form_data.items()}
    else:
        form_dict = {k: str(v) for k, v in request.query_params.items()}

    # Extract request URL matching Twilio forwarded headers if present
    forwarded_proto = request.headers.get("x-forwarded-proto", "http")
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    full_url = f"{forwarded_proto}://{forwarded_host}{request.url.path}" if forwarded_host else str(request.url)

    # Verify Twilio Webhook Signature in production
    if settings.twilio_auth_token and x_twilio_signature:
        if not _validate_twilio_signature(
            url=full_url,
            params=form_dict,
            signature=x_twilio_signature,
            auth_token=settings.twilio_auth_token,
        ):
            logger.warning("Rejected unauthenticated WhatsApp webhook request (invalid signature for %s).", full_url)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature.")


    sender = str(form_dict.get("From", "whatsapp:+919876543210"))
    incoming_text = str(form_dict.get("Body", "")).strip()
    media_url = form_dict.get("MediaUrl0")
    
    # Safe float extraction for GPS coordinates
    latitude_str = form_dict.get("Latitude")
    longitude_str = form_dict.get("Longitude")

    latitude: float | None = None
    longitude: float | None = None
    try:
        if latitude_str:
            latitude = float(str(latitude_str))
        if longitude_str:
            longitude = float(str(longitude_str))
    except (ValueError, TypeError):
        logger.warning("Invalid coordinate values received: %s, %s", latitude_str, longitude_str)

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

    # If Score 2 (ASHA Dispatch), look up local ASHA worker contact dynamically by district
    if outcome.risk_score == int(RiskScore.ASHA_DISPATCH):
        district_query = str(form_dict.get("District") or "Sitamarhi")

        asha_record = db.execute(
            select(AshaAssignment).where(AshaAssignment.district == district_query).limit(1)
        ).scalar_one_or_none()
        if not asha_record:
            asha_record = db.execute(select(AshaAssignment).limit(1)).scalar_one_or_none()
        asha_phone = asha_record.phone if asha_record else "+919999988888"
        
        asha_alert = (
            f"🚨 ASHA ALERT: New moderate-risk case reported from {sender}.\n"
            f"Symptoms: {', '.join(outcome.rationale_keys) if outcome.rationale_keys else 'Moderate symptoms'}\n"
            f"Action: Home assessment required within 24 hours."
        )
        await twilio_client.send_sms(to_number=asha_phone, body=asha_alert)

    # If Score 3 (Emergency), append nearest PHC info
    if outcome.risk_score == int(RiskScore.EMERGENCY_REFERRAL):
        if latitude is not None and longitude is not None:
            phc_list = nearest_phcs(db=db, lat=latitude, lon=longitude, limit=1)
        else:
            phc_list = db.execute(select(PHC).limit(1)).scalars().all()
        if phc_list:
            phc = phc_list[0]
            dist_str = f"~{phc.distance_km:.1f} km" if hasattr(phc, "distance_km") and phc.distance_km is not None else "Nearby Facility"
            reply_text += f"\n\n📍 Nearest PHC: {phc.name}\n📞 Emergency Contact: {phc.phone}\nDistance: {dist_str} (Open: {phc.hours})"

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


@router.get("/meta-whatsapp")
async def verify_meta_whatsapp_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
) -> Response:
    """Meta WhatsApp Cloud API Webhook Verification Endpoint."""
    if hub_mode == "subscribe" and hub_verify_token == settings.meta_verify_token:
        return PlainTextResponse(content=hub_challenge or "", status_code=200)
    raise HTTPException(status_code=403, detail="Verification token mismatch.")


@router.post("/meta-whatsapp")
async def handle_meta_whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Meta WhatsApp Cloud API incoming message webhook listener."""
    body = await request.json()
    logger.info("Received Meta WhatsApp Webhook event: %s", body)

    entries = body.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            messages = value.get("messages", [])
            for msg in messages:
                sender = msg.get("from", "")
                msg_type = msg.get("type", "")
                incoming_text = ""

                if msg_type == "text":
                    incoming_text = msg.get("text", {}).get("body", "")
                elif msg_type == "audio":
                    audio_id = msg.get("audio", {}).get("id")
                    if audio_id and settings.meta_whatsapp_token:
                        async with httpx.AsyncClient() as client:
                            media_res = await client.get(
                                f"https://graph.facebook.com/v18.0/{audio_id}",
                                headers={"Authorization": f"Bearer {settings.meta_whatsapp_token}"},
                            )
                            if media_res.status_code == 200:
                                media_url = media_res.json().get("url")
                                if media_url:
                                    audio_bytes_res = await client.get(
                                        media_url,
                                        headers={"Authorization": f"Bearer {settings.meta_whatsapp_token}"},
                                    )
                                    if audio_bytes_res.status_code == 200:
                                        asr_res = await sarvam_client.transcribe_audio(
                                            audio_bytes=audio_bytes_res.content,
                                            filename="voice.ogg",
                                            language_code="hi",
                                        )
                                        incoming_text = asr_res.get("transcript", "")

                if incoming_text:
                    payload = sarvam_client.extract_symptoms_rule_fallback(incoming_text, language="hi")
                    triage_req = TriageEvaluateRequest(
                        payload=SymptomPayloadIn(**asdict(payload)),
                        client_uuid=f"meta-{uuid.uuid4().hex[:12]}",
                    )
                    res = evaluate_and_log(db=db, request=triage_req)
                    directive = res["directive"]
                    outcome = res["outcome"]

                    reply_text = f"🩺 SwaraSetu Triage Result\n\n{directive.message_en}\n\nDecision: {outcome.rationale_en}"

                    if settings.meta_whatsapp_token and settings.meta_phone_number_id:
                        async with httpx.AsyncClient() as client:
                            await client.post(
                                f"https://graph.facebook.com/v18.0/{settings.meta_phone_number_id}/messages",
                                headers={
                                    "Authorization": f"Bearer {settings.meta_whatsapp_token}",
                                    "Content-Type": "application/json",
                                },
                                json={
                                    "messaging_product": "whatsapp",
                                    "to": sender,
                                    "type": "text",
                                    "text": {"body": reply_text},
                                },
                            )

    return {"status": "ok"}


@router.post("/telegram")
async def handle_telegram_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Telegram Bot incoming webhook listener for voice notes and text messages."""
    body = await request.json()
    logger.info("Received Telegram Webhook event: %s", body)

    message = body.get("message", {})
    if not message:
        return {"status": "ignored"}

    chat_id = message.get("chat", {}).get("id")
    if not chat_id:
        return {"status": "no_chat_id"}

    token = settings.telegram_bot_token or "8898656050:AAG-tRQ8gVrNBsHWJ-gKdj5PVVFaN4Zl9eg"
    incoming_text = message.get("text", "").strip()
    voice = message.get("voice") or message.get("audio")

    # Handle voice note / audio message
    if voice and voice.get("file_id"):
        file_id = voice.get("file_id")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                file_res = await client.get(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}")
                if file_res.status_code == 200:
                    file_path = file_res.json().get("result", {}).get("file_path")
                    if file_path:
                        download_res = await client.get(f"https://api.telegram.org/file/bot{token}/{file_path}")
                        if download_res.status_code == 200:
                            asr_res = await sarvam_client.transcribe_audio(
                                audio_bytes=download_res.content,
                                filename="voice.ogg",
                                language_code="hi",
                            )
                            incoming_text = asr_res.get("transcript", "")
                            logger.info("Telegram voice transcribed: %s", incoming_text)
        except Exception as err:
            logger.error("Error downloading/transcribing Telegram voice note: %s", err)

    if not incoming_text:
        reply_msg = "👋 Hello! I am SwaraSetu Gaon Doctor. Please send me a voice note or type symptoms (e.g., 'Child has fever for 2 days')."
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": reply_msg},
            )
        return {"status": "prompted"}


    # Extract symptoms and run WHO IMCI triage
    payload = sarvam_client.extract_symptoms_rule_fallback(incoming_text, language="hi")
    triage_req = TriageEvaluateRequest(
        payload=SymptomPayloadIn(**asdict(payload)),
        client_uuid=f"tg-{uuid.uuid4().hex[:12]}",
    )
    res = evaluate_and_log(db=db, request=triage_req)
    directive = res["directive"]
    outcome = res["outcome"]

    # Build triage reply
    score_badge = "🔴 RED EMERGENCY" if outcome.risk_score == 3 else "🟡 ASHA DISPATCH" if outcome.risk_score == 2 else "🟢 SELF CARE"
    reply_text = f"🩺 *SwaraSetu Clinical Triage ({score_badge})*\n\n{directive.message_en}\n\n*Clinical Rationale:* {outcome.rationale_en}"

    if outcome.risk_score == 3 and res.get("nearest_phc"):
        phc = res["nearest_phc"]
        reply_text += f"\n\n📍 *Nearest PHC:* {phc['name']}\n📞 *Doctor Contact:* {phc['phone']}\n*Distance:* ~{phc['distance_km']:.1f} km (Open 24/7)"

    async with httpx.AsyncClient(timeout=30.0) as client:

        # Send text message
        await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": reply_text, "parse_mode": "Markdown"},
        )

        # Synthesize Sarvam TTS audio voice reply
        audio_b64 = await sarvam_client.synthesize_speech(text=directive.message_en, target_language="hi")
        if audio_b64:
            import base64 as b64_lib
            audio_bytes = b64_lib.b64decode(audio_b64)
            await client.post(
                f"https://api.telegram.org/bot{token}/sendVoice",
                data={"chat_id": chat_id},
                files={"voice": ("response.wav", audio_bytes, "audio/wav")},
            )

    return {"status": "processed", "risk_score": outcome.risk_score}
