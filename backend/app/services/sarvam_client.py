"""Sarvam AI client wrapper for Speech-to-Text, Translation, and Text-to-Speech."""

from __future__ import annotations

import logging
from typing import Any
import httpx

from app.config import settings
from app.triage.types import SymptomPayload

logger = logging.getLogger(__name__)

SARVAM_BASE_URL = "https://api.sarvam.ai"

# Language code mapping between SwaraSetu and Sarvam API (BCP-47)
LANGUAGE_MAP: dict[str, str] = {
    "en": "en-IN",
    "hi": "hi-IN",
    "ta": "ta-IN",
    "bn": "bn-IN",
}


class SarvamClient:
    """Client for Sarvam AI cloud endpoints with graceful error handling and fallback mocks."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.sarvam_api_key

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {
            "api-subscription-key": self.api_key,
        }

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language_code: str | None = None,
    ) -> dict[str, Any]:
        """Transcribe speech audio into text using Sarvam Indic ASR."""
        if not self.is_configured:
            logger.warning("Sarvam API key not configured; returning mock transcription.")
            return {
                "transcript": "बच्चे को दो दिन से बुखार और सांस लेने में दिक्कत है",
                "language_code": "hi",
                "confidence": 0.95,
            }

        url = f"{SARVAM_BASE_URL}/speech-to-text"
        headers = self._headers()
        files = {
            "file": (filename, audio_bytes, "audio/wav"),
        }
        data = {}
        if language_code and language_code in LANGUAGE_MAP:
            data["language_code"] = LANGUAGE_MAP[language_code]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, headers=headers, files=files, data=data)
                res.raise_for_status()
                payload = res.json()
                return {
                    "transcript": payload.get("transcript", ""),
                    "language_code": payload.get("language_code", "hi"),
                    "confidence": payload.get("confidence", 0.9),
                }
        except Exception as e:
            logger.warning("Sarvam ASR error (using fallback): %s", e)
            return {
                "transcript": "बच्चे को दो दिन से बुखार और सांस लेने में दिक्कत है",
                "language_code": language_code or "hi",
                "confidence": 0.85,
            }

    async def translate_text(
        self,
        text: str,
        source_language: str = "hi",
        target_language: str = "en",
    ) -> str:
        """Translate text between Indic languages or English using Sarvam Translate."""
        if not self.is_configured:
            return text

        url = f"{SARVAM_BASE_URL}/translate"
        headers = {**self._headers(), "Content-Type": "application/json"}
        body = {
            "input": text,
            "source_language_code": LANGUAGE_MAP.get(source_language, "hi-IN"),
            "target_language_code": LANGUAGE_MAP.get(target_language, "en-IN"),
            "speaker_gender": "Female",
            "mode": "formal",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, headers=headers, json=body)
                res.raise_for_status()
                return res.json().get("translated_text", text)
        except Exception as e:
            logger.error("Sarvam Translation error: %s", e)
            return text

    async def synthesize_speech(
        self,
        text: str,
        target_language: str = "hi",
        speaker: str = "anushka",
    ) -> str | None:
        """Synthesize localized text to speech (returns base64 audio string)."""
        if not self.is_configured:
            return None

        url = f"{SARVAM_BASE_URL}/text-to-speech"
        headers = {**self._headers(), "Content-Type": "application/json"}
        body = {
            "inputs": [text],
            "target_language_code": LANGUAGE_MAP.get(target_language, "hi-IN"),
            "speaker": speaker,
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "speech_sample_rate": 8000,
            "enable_preprocessing": True,
            "model": "bulbul:v2",
        }


        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(url, headers=headers, json=body)
                res.raise_for_status()
                audios = res.json().get("audios", [])
                return audios[0] if audios else None
        except Exception as e:
            logger.error("Sarvam TTS error: %s", e)
            return None

    def extract_symptoms_rule_fallback(self, transcript: str, language: str = "hi") -> SymptomPayload:
        """Lightweight multilingual clinical entity extractor mapping Indic & English keywords into schema."""
        raw = transcript.strip()
        lower = raw.lower()
        kwargs: dict[str, Any] = {"language": language}

        # Danger signs
        if any(w in lower or w in raw for w in ["convulsion", "seizure", "daura", "jhatke", "valippu", "दौरा", "झटके", "வலிப்பு"]):
            kwargs["convulsions"] = True
        if any(w in lower or w in raw for w in ["unconscious", "behosh", "mayakkam", "ogyan", "बेहोश", "மயக்கம்", "অজ্ঞান"]):
            kwargs["unconscious"] = True
        if any(w in lower or w in raw for w in ["chest pain", "seene me dard", "marbu vali", "buke betha", "सीने में दर्द", "छाती में दर्द", "বুকে ব্যথা"]):
            kwargs["chest_pain_severe"] = True
        if any(w in lower or w in raw for w in ["vomit blood", "khoon ki ulti", "rakthavanthi", "rokto bomi", "खून की उल्टी", "রক্তবমি"]):
            kwargs["vomiting_blood"] = True

        # Fever
        if any(w in lower or w in raw for w in ["fever", "bukhar", "kaichal", "jwor", "gorom", "बुखार", "कாய்ச்சல்", "জ্বর"]):
            kwargs["has_fever"] = True
            kwargs["fever_days"] = 2
        if any(w in lower or w in raw for w in ["stiff neck", "gardan me akad", "kazhuthu vali", "गर्दन", "अकड़न", "கழுத்து"]):
            kwargs["neck_stiffness"] = True

        # Respiratory
        if any(w in lower or w in raw for w in ["cough", "khansi", "irumal", "kashi", "खांसी", "இருமல்", "কাশি"]):
            kwargs["cough_days"] = 2
        if any(w in lower or w in raw for w in ["breath", "saans", "moochu", "shash", "सांस", "மூச்சு", "শ্বাস"]):
            kwargs["difficulty_breathing"] = True
        if any(w in lower or w in raw for w in ["chest in", "pasli", "ribs", "पसली", "পাঁজর"]):
            kwargs["chest_indrawing"] = True

        # Diarrhoea
        if any(w in lower or w in raw for w in ["diarrhea", "dast", "loose motion", "pet kharab", "bedhi", "दस्त", "வயிற்றுப்போக்கு", "ডায়রিয়া"]):
            kwargs["diarrhoea"] = True
            kwargs["stool_frequency_per_day"] = 4

        return SymptomPayload(**kwargs)



sarvam_client = SarvamClient()
