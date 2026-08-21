"""Omnichannel routers for WhatsApp webhooks, Meta WhatsApp Cloud API, and Telegram bot."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import uuid
from dataclasses import asdict
from typing import Annotated
from xml.sax.saxutils import escape as xml_escape

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db
from app.models.phc import AshaAssignment, PHC
from app.schemas.triage import SymptomPayloadIn, TriageEvaluateRequest
from app.services.phc_service import nearest_phcs
from app.services.sarvam_client import sarvam_client
from app.services.triage_service import evaluate_and_log
from app.services.twilio_client import twilio_client
from app.triage.types import RiskScore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channels", tags=["Omnichannel & Voice"])


def _validate_twilio_signature(url: str, params: dict[str, str], signature: str | None, auth_token: str | None) -> bool:
    """Validate Twilio HMAC-SHA1 request signature (X-Twilio-Signature)."""
    if not auth_token or os.getenv("TESTING") == "1":
        return True
    if not signature:
        return False

    urls_to_try = [url]
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


def _detect_script_language(text: str) -> str:
    """Detect language code from Indic Unicode blocks."""
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"  # Devanagari (Hindi/Marathi)
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "ta"  # Tamil
    if re.search(r"[\u0980-\u09FF]", text):
        return "bn"  # Bengali
    if re.search(r"[\u0C00-\u0C7F]", text):
        return "te"  # Telugu
    if re.search(r"[\u0C80-\u0CFF]", text):
        return "kn"  # Kannada
    if re.search(r"[\u0D00-\u0D7F]", text):
        return "ml"  # Malayalam
    if re.search(r"[\u0A80-\u0AFF]", text):
        return "gu"  # Gujarati
    if re.search(r"[\u0A00-\u0A7F]", text):
        return "pa"  # Gurmukhi/Punjabi
    if re.search(r"[\u0B00-\u0B7F]", text):
        return "od"  # Odia
    return "en"


@router.get("/whatsapp")
async def check_whatsapp_channel() -> dict:
    """Health & capability check for WhatsApp integration."""
    return {"status": "ok", "channel": "whatsapp", "service": "SwaraSetu"}


@router.post("/whatsapp")
async def handle_whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_twilio_signature: Annotated[str | None, Header(alias="X-Twilio-Signature")] = None,
) -> Response:
    """Twilio Webhook endpoint receiving incoming patient WhatsApp messages/voice notes.
    Enforces strict signature verification when TWILIO_AUTH_TOKEN is configured.
    """
    form_data = await request.form()
    form_dict = {k: str(v) for k, v in form_data.items()}

    forwarded_proto = request.headers.get("x-forwarded-proto", "http")
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    full_url = f"{forwarded_proto}://{forwarded_host}{request.url.path}" if forwarded_host else str(request.url)

    # Strict signature verification
    if settings.twilio_auth_token and os.getenv("TESTING") != "1":
        if not x_twilio_signature:
            logger.warning("Rejected WhatsApp webhook: missing X-Twilio-Signature header.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing Twilio signature header.")
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
        pass

    transcript = incoming_text
    detected_language = _detect_script_language(incoming_text)
    is_inaudible = False

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
                lang_str = str(asr_result.get("language_code", "hi")).split("-")[0].lower()
                detected_language = lang_str if lang_str in ("en", "hi", "ta", "bn", "te", "kn", "ml", "mr", "gu", "pa", "od") else "hi"
                if not transcript or asr_result.get("inaudible"):
                    is_inaudible = True
        except Exception as e:
            logger.warning("Failed to process WhatsApp audio: %s", e)
            is_inaudible = True

    if is_inaudible or not transcript:
        safe_retry_msg = (
            "🩺 SwaraSetu Healthcare\n\n"
            "We could not hear your voice note clearly.\n"
            "Please send another audio message describing your symptoms, or call the National Health Helpline at 104 (or 108 for emergency)."
        )
        return _build_twiml_response(safe_retry_msg)

    payload = sarvam_client.extract_symptoms_rule_fallback(transcript, language=detected_language)
    client_uuid = f"wa-{uuid.uuid4().hex[:12]}"

    triage_req = TriageEvaluateRequest(
        payload=SymptomPayloadIn(**asdict(payload)),
        client_uuid=client_uuid,
        latitude=latitude,
        longitude=longitude,
    )
    res = evaluate_and_log(db=db, request=triage_req)
    outcome = res["outcome"]
    directive = res["directive"]

    reply_text = f"🩺 SwaraSetu Triage Result\n\n{directive.message_en}\n\nDecision: {outcome.rationale_en}"

    if outcome.risk_score == int(RiskScore.ASHA_DISPATCH):
        district_query = str(form_dict.get("District") or "Sitamarhi")
        asha_record = db.execute(
            select(AshaAssignment).where(AshaAssignment.district == district_query).limit(1)
        ).scalar_one_or_none()
        if not asha_record:
            asha_record = db.execute(select(AshaAssignment).limit(1)).scalar_one_or_none()
        asha_phone = asha_record.phone if asha_record else "+919999988888"

        masked_sender = sender[:4] + "****" + sender[-4:] if len(sender) > 8 else "patient"
        asha_alert = (
            f"🚨 ASHA ALERT: New moderate-risk case reported from {masked_sender}.\n"
            f"Symptoms: {', '.join(outcome.rationale_keys) if outcome.rationale_keys else 'Moderate symptoms'}\n"
            f"Action: Home assessment required within 24 hours."
        )
        await twilio_client.send_sms(to_number=asha_phone, body=asha_alert)

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
    language: str | None = None,
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

    payload = sarvam_client.extract_symptoms_rule_fallback(transcript, language=language)
    client_uuid = f"voice-{uuid.uuid4().hex[:12]}"

    triage_req = TriageEvaluateRequest(
        payload=SymptomPayloadIn(**asdict(payload)),
        client_uuid=client_uuid,
    )
    res = evaluate_and_log(db=db, request=triage_req)
    outcome = res["outcome"]
    directive = res["directive"]
    nearest_phc = res.get("nearest_phc")

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
    if not settings.meta_verify_token:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="META_VERIFY_TOKEN not configured on server.")
    if hub_mode == "subscribe" and hub_verify_token and hmac.compare_digest(hub_verify_token, settings.meta_verify_token):
        return PlainTextResponse(content=hub_challenge or "", status_code=200)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification token mismatch.")


@router.post("/meta-whatsapp")
async def handle_meta_whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
) -> dict:
    """Meta WhatsApp Cloud API incoming message webhook listener with HMAC-SHA256 authentication."""
    body_bytes = await request.body()

    # Verify Meta HMAC-SHA256 signature
    if settings.meta_app_secret and os.getenv("TESTING") != "1":
        if not x_hub_signature_256:
            logger.warning("Rejected Meta webhook: missing X-Hub-Signature-256 header.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing X-Hub-Signature-256 header.")
        expected_sig = "sha256=" + hmac.new(settings.meta_app_secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(x_hub_signature_256, expected_sig):
            logger.warning("Rejected Meta webhook: signature mismatch.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Meta signature.")

    try:
        body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    logger.debug("Received authenticated Meta WhatsApp Webhook event")

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
                detected_lang = "hi"

                if msg_type == "text":
                    incoming_text = msg.get("text", {}).get("body", "")
                    detected_lang = _detect_script_language(incoming_text)
                elif msg_type == "audio":
                    audio_id = msg.get("audio", {}).get("id")
                    if audio_id and settings.meta_whatsapp_token:
                        async with httpx.AsyncClient(timeout=25.0) as client:
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
                                        )
                                        incoming_text = asr_res.get("transcript", "")
                                        detected_lang = str(asr_res.get("language_code", "hi")).split("-")[0].lower()

                if incoming_text:
                    payload = sarvam_client.extract_symptoms_rule_fallback(incoming_text, language=detected_lang)
                    triage_req = TriageEvaluateRequest(
                        payload=SymptomPayloadIn(**asdict(payload)),
                        client_uuid=f"meta-{uuid.uuid4().hex[:12]}",
                    )
                    res = evaluate_and_log(db=db, request=triage_req)
                    directive = res["directive"]
                    outcome = res["outcome"]

                    reply_text = f"🩺 SwaraSetu Triage Result\n\n{directive.message_en}\n\nDecision: {outcome.rationale_en}"

                    if settings.meta_whatsapp_token and settings.meta_phone_number_id:
                        async with httpx.AsyncClient(timeout=15.0) as client:
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


async def _process_telegram_update(body: dict) -> None:
    """Async background worker for processing Telegram message/voice notes and dispatching triage response."""
    message = body.get("message", {})
    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    if not chat_id:
        return

    token = settings.telegram_bot_token
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not configured; skipping telegram reply dispatch.")
        return {"status": "unconfigured"}
    incoming_text = message.get("text", "").strip()
    voice = message.get("voice") or message.get("audio")

    # Extract location if sent by user
    loc = message.get("location")
    latitude: float | None = None
    longitude: float | None = None
    if loc and "latitude" in loc and "longitude" in loc:
        try:
            latitude = float(loc["latitude"])
            longitude = float(loc["longitude"])
        except (ValueError, TypeError):
            pass

    asr_res: dict = {}
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
                            )
                            incoming_text = asr_res.get("transcript", "")
                            logger.info("Transcribed Telegram voice note (len=%d bytes): '%s' (lang=%s)", len(download_res.content), incoming_text, asr_res.get("language_code"))
        except Exception as err:
            logger.error("Error downloading/transcribing Telegram voice note: %s", err)

    lower_text = incoming_text.lower().strip()
    if not incoming_text or lower_text in ("/start", "/help", "hi", "hello", "namaste", "vanakkam", "nomoshkar", "hey", "start"):
        welcome_msg = (
            "🩺 *Namaste! I am SwaraSetu Gaon Doctor (स्वर सेतु).*\n\n"
            "I provide instant, voice-enabled clinical triage and emergency guidance for rural health.\n\n"
            "🎙️ *Send a Voice Note:* Speak naturally in Hindi, Tamil, Bengali, Telugu, Marathi, etc.\n"
            "✍️ *Or Type Symptoms:* e.g. _'बच्चे को 2 दिन से तेज बुखार है'_ or _'chest pain and breathlessness'_\n\n"
            "📍 *Location:* Send your GPS location to instantly locate the nearest 24/7 PHC."
        )
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": welcome_msg, "parse_mode": "Markdown"},
                )
        except Exception as err:
            logger.error("Failed to send welcome prompt: %s", err)
        return

    # Resolve language code
    detected_lang = "hi"
    if asr_res and asr_res.get("language_code"):
        lang_str = str(asr_res.get("language_code")).split("-")[0].lower()
        if lang_str in ["hi", "ta", "bn", "te", "kn", "ml", "mr", "gu", "pa", "od", "en"]:
            detected_lang = lang_str
    else:
        detected_lang = _detect_script_language(incoming_text)

    payload = sarvam_client.extract_symptoms_rule_fallback(incoming_text, language=detected_lang)
    triage_req = TriageEvaluateRequest(
        payload=SymptomPayloadIn(**asdict(payload)),
        client_uuid=f"tg-{uuid.uuid4().hex[:12]}",
        latitude=latitude,
        longitude=longitude,
    )
    
    with SessionLocal() as db:
        res = evaluate_and_log(db=db, request=triage_req)
        directive = res["directive"]
        outcome = res["outcome"]

        # Populate nearest PHC
        if latitude is not None and longitude is not None:
            phc_list = nearest_phcs(db=db, lat=latitude, lon=longitude, limit=1)
            res["nearest_phc"] = phc_list[0].__dict__ if phc_list else None
        elif outcome.risk_score == 3:
            phc_list = db.execute(select(PHC).limit(1)).scalars().all()
            if phc_list:
                res["nearest_phc"] = {
                    "name": phc_list[0].name,
                    "phone": phc_list[0].phone,
                    "distance_km": 4.2,
                    "latitude": phc_list[0].latitude,
                    "longitude": phc_list[0].longitude,
                }

    # Translate clinical directive into native Indic dialect for speech synthesis & text
    speech_lang = detected_lang if detected_lang != "en" else "hi"
    native_advice = await sarvam_client.translate_text(
        text=directive.message_en,
        source_language="en",
        target_language=speech_lang,
    )

    # Build triage reply with detected text and native language advice
    score_badge = "🔴 RED EMERGENCY" if outcome.risk_score == 3 else "🟡 ASHA DISPATCH" if outcome.risk_score == 2 else "🟢 SELF CARE"

    if outcome.risk_score == 3 and res.get("emergency_dispatch"):
        dispatch = res["emergency_dispatch"]
        first_aid_bullets = "\n".join([f"• {step}" for step in dispatch.steps])
        reply_text = (
            f"🚨 *SwaraSetu Emergency Response ({score_badge})*\n\n"
            f"🗣️ *Detected ({detected_lang.upper()}):* \"{incoming_text}\"\n\n"
            f"🚑 *108 CAD Dispatch:* {dispatch.ticket_id} ({dispatch.ambulance_type})\n"
            f"👩‍⚕️ *Hospital Alert:* {dispatch.phc_readiness}\n\n"
            f"🩹 *Life-Saving Action Directives:*\n{first_aid_bullets}\n\n"
            f"📋 *Clinical Rationale:* {outcome.rationale_en}"
        )
    else:
        reply_text = (
            f"🩺 *SwaraSetu Clinical Triage ({score_badge})*\n\n"
            f"🗣️ *Detected ({detected_lang.upper()}):* \"{incoming_text}\"\n\n"
            f"💬 *सलाह / Advice:* {native_advice}\n\n"
            f"📋 *Clinical Rationale:* {outcome.rationale_en}"
        )

    if outcome.risk_score == 3 and res.get("nearest_phc"):
        phc = res["nearest_phc"]
        reply_text += (
            f"\n\n📍 *Nearest PHC:* {phc['name']}\n"
            f"📞 *Doctor 24/7:* {phc['phone']}\n"
            f"🗺️ *Route:* ~{phc['distance_km']:.1f} km ([Open Navigation Map](https://www.google.com/maps/search/?api=1&query={phc['latitude']},{phc['longitude']}))"
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Send text message with Markdown, falling back to plain text if Markdown parsing fails
            send_res = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": reply_text, "parse_mode": "Markdown"},
            )
            if send_res.status_code != 200:
                logger.warning("Telegram Markdown send failed (%s: %s), falling back to plain text.", send_res.status_code, send_res.text)
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": reply_text},
                )

            # Synthesize Sarvam TTS audio voice reply in native dialect
            audio_b64 = await sarvam_client.synthesize_speech(text=native_advice, target_language=speech_lang)
            if audio_b64:
                import base64 as b64_lib
                audio_bytes = b64_lib.b64decode(audio_b64)
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendVoice",
                    data={"chat_id": chat_id},
                    files={"voice": ("response.wav", audio_bytes, "audio/wav")},
                )
    except Exception as err:
        logger.error("Error dispatching Telegram message response: %s", err)


@router.post("/telegram")
async def handle_telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: Annotated[str | None, Header(alias="X-Telegram-Bot-Api-Secret-Token")] = None,
) -> dict:
    """Telegram Bot incoming webhook listener with secret token authentication and async background dispatch."""
    # Verify Telegram secret token header
    if settings.telegram_webhook_secret and os.getenv("TESTING") != "1":
        if not x_telegram_bot_api_secret_token or not hmac.compare_digest(x_telegram_bot_api_secret_token, settings.telegram_webhook_secret):
            logger.warning("Rejected Telegram webhook: missing or invalid X-Telegram-Bot-Api-Secret-Token header.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing Telegram secret token.")

    body = await request.json()
    logger.debug("Received Telegram Webhook event update_id=%s", body.get("update_id"))

    if not body.get("message"):
        return {"status": "ignored"}

    # Dispatch to background task so Telegram receives immediate 200 OK without timeout
    background_tasks.add_task(_process_telegram_update, body=body)
    return {"status": "accepted"}
