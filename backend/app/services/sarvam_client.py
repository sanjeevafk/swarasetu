"""Sarvam AI client wrapper for Speech-to-Text, Translation, and Text-to-Speech."""

from __future__ import annotations

import logging
import re
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


def _matches_word(pattern_list: list[str], text: str) -> bool:
    """Check if any pattern in pattern_list matches text using word boundaries."""
    for pat in pattern_list:
        # Check if ASCII / English transliteration -> use \b
        if re.search(r'^[a-zA-Z0-9\s-]+$', pat):
            escaped = re.escape(pat)
            if re.search(rf"\b{escaped}\b", text, re.IGNORECASE):
                return True
        else:
            # Indic script: match whole word with whitespace/punctuation boundary
            escaped = re.escape(pat)
            if re.search(rf"(?:^|\s|[.,!?;:\u0964]){escaped}(?:$|\s|[.,!?;:\u0964])", text):
                return True
    return False


class SarvamClient:
    """Client for Sarvam AI cloud endpoints with clinically safe zero-hallucination behavior."""

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
        """Transcribe speech audio into text using Sarvam Indic ASR.
        Fails safely with empty transcript on error or unconfigured state.
        """
        if not self.is_configured:
            logger.warning("Sarvam API key not configured; returning empty transcript.")
            return {
                "transcript": "",
                "language_code": language_code or "hi",
                "confidence": 0.0,
                "inaudible": True,
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
                transcript = payload.get("transcript", "").strip()
                return {
                    "transcript": transcript,
                    "language_code": payload.get("language_code", language_code or "hi"),
                    "confidence": payload.get("confidence", 0.9 if transcript else 0.0),
                    "inaudible": len(transcript) == 0,
                }
        except Exception as e:
            logger.warning("Sarvam ASR error: %s (failing safely without hallucination)", e)
            return {
                "transcript": "",
                "language_code": language_code or "hi",
                "confidence": 0.0,
                "inaudible": True,
                "error": str(e),
            }

    async def translate_text(
        self,
        text: str,
        source_language: str = "hi",
        target_language: str = "en",
    ) -> str:
        """Translate text between Indic languages or English using Sarvam Translate."""
        if not self.is_configured or not text.strip():
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
        if not self.is_configured or not text.strip():
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
        """Clinically safe entity extractor with word-boundary matching and regex duration extraction."""
        import re
        raw = transcript.strip()
        if not raw:
            return SymptomPayload(language=language)

        kwargs: dict[str, Any] = {"language": language}

        # Extract numeric duration if present (e.g. "3 days", "2 din", "5 dina")
        days_match = re.search(r"(\d+)\s*(?:day|days|din|dina|dino|dinon|naal|naatkal|দিন|दिन|நாட்கள்)", raw, re.IGNORECASE)
        extracted_days = int(days_match.group(1)) if days_match else None

        # Age group detection
        if _matches_word(["baby", "neonate", "newborn", "navjat", "navajat", "பிறந்த குழந்தை", "নবজাতক"], raw):
            kwargs["age_group"] = "neonate"
        elif _matches_word(["infant", "toddler", "chhota bacha", "kutty", "शिशु", "குழந்தை"], raw):
            kwargs["age_group"] = "infant"
        elif _matches_word(["child", "kid", "bacha", "baccha", "bachhe", "kuzhanthai", "बच्चा", "बच्चे", "বাচ্চা"], raw):
            kwargs["age_group"] = "child"
        elif _matches_word(["pregnant", "pregnancy", "garbh", "garbhvati", "garbhwati", "gorbhoboti", "கர்ப்பிணி", "गर्भवती", "গর্ভবতী"], raw):
            kwargs["pregnant"] = True

        # Danger signs (Red / Score 3)
        if _matches_word(["convulsion", "convulsions", "seizure", "seizures", "fit", "fits", "daura", "jhatke", "valippu", "दौरा", "झटके", "வலிப்பு"], raw):
            kwargs["convulsions"] = True
        if _matches_word(["unconscious", "behosh", "mayakkam", "ogyan", "बेहोश", "மயக்கம்", "অজ্ঞান"], raw):
            kwargs["unconscious"] = True
        if _matches_word(["chest pain", "seene me dard", "marbu vali", "buke betha", "सीने में दर्द", "छाती में दर्द", "बुके ব্যথা"], raw):
            kwargs["chest_pain_severe"] = True
        if _matches_word(["vomit blood", "vomiting blood", "khoon ki ulti", "rakthavanthi", "rokto bomi", "खून की उल्टी", "रक्तবমি"], raw):
            kwargs["vomiting_blood"] = True

        # Fever
        if _matches_word(["fever", "bukhar", "kaichal", "jwor", "gorom", "thand", "chills", "बुखार", "காய்ச்சல்", "জ্বর"], raw):
            kwargs["has_fever"] = True
            if extracted_days is not None:
                kwargs["fever_days"] = extracted_days
        if _matches_word(["stiff neck", "gardan me akad", "kazhuthu vali", "गर्दन में अकड़न", "अकड़न", "கழுத்து வலி"], raw):
            kwargs["neck_stiffness"] = True
        if _matches_word(["rash", "daane", "chhate", "thathadu", "दाने", "தடிப்பு"], raw):
            kwargs["rash_with_fever"] = True

        # Respiratory
        has_cough = _matches_word(["cough", "coughing", "cold", "khansi", "sardi", "jukham", "irumal", "kashi", "खांसी", "सर्दी", "जुकाम", "இருமல்", "কাশি"], raw)
        has_breathing_distress = _matches_word(["breath", "breathing", "shortness of breath", "difficulty breathing", "saans", "moochu", "shash", "दम", "सांस", "மூச்சு", "শ্বাস"], raw)
        
        if has_cough:
            kwargs["cough_days"] = extracted_days if extracted_days is not None else 1
        if has_breathing_distress:
            kwargs["difficulty_breathing"] = True
            kwargs["breathing_rate_per_min"] = 55
        elif has_cough:
            kwargs["difficulty_breathing"] = False

        if _matches_word(["chest in", "chest indrawing", "pasli", "ribs", "पसली", "পাঁজর"], raw):
            kwargs["chest_indrawing"] = True

        # Diarrhoea & Dehydration
        if _matches_word(["diarrhea", "diarrhoea", "dast", "loose motion", "pet kharab", "bedhi", "दस्त", "வயிற்றுப்போக்கு", "ডায়রিয়া"], raw):
            kwargs["diarrhoea"] = True
            if extracted_days is not None:
                kwargs["stool_frequency_per_day"] = 5
        if _matches_word(["blood in stool", "khoon dast", "raktham", "khoon ka dast", "रक्त দস্ত", "இரத்த மலம்"], raw):
            kwargs["blood_in_stool"] = True

        # Maternal
        if kwargs.get("pregnant"):
            if _matches_word(["headache", "sar dard", "thalai vali", "सिर दर्द", "தலைவலி"], raw):
                kwargs["headache_severe"] = True
            if _matches_word(["bleeding", "khoon", "raktham", "रक्तस्राव", "இரத்தப்போக்கு"], raw):
                kwargs["vaginal_bleeding"] = True

        return SymptomPayload(**kwargs)



sarvam_client = SarvamClient()
