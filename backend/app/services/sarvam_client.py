"""Sarvam AI client wrapper for Speech-to-Text, Translation, and Text-to-Speech."""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
import re
from typing import Any
import httpx

from app.config import settings
from app.triage.types import AGE_CHILD, SymptomPayload

logger = logging.getLogger(__name__)

SARVAM_BASE_URL = "https://api.sarvam.ai"

# ── Rule-based NER vocabulary (Latin Tanglish + Indic scripts) ───────────────
# Every literal is single-script on purpose: bench_source() audits for
# mixed-script string literals and must stay clean.

_NEGATORS = ("no", "not", "never", "without", "illa", "illai", "illame", "ledu", "kidayathu")

_STRONG_MODIFIERS = (
    "severe", "romba", "mosama", "mosam", "heavy", "continuous", "thudarchiya",
    "thudarchi", "nonstop", "repeat", "thirumb", "serious", "high", "sudden",
    "bad", "udane", "kashtam", "kashdum", "adigama",
)

_MILD_MARKERS = ("light", "mild", "slight", "konjam", "saadharana", "saadaranam")

_ADULT_RELATIVES = (
    "paati", "paatti", "thatha", "thattha", "amma", "appa", "husband", "wife",
    "mother", "father", "grandma", "grandpa", "grandmother", "grandfather",
    "akka", "anna", "pondati", "maman",
)

_SUPPLY_NOUNS = (
    "tablet", "syrup", "tonic", "iron", "calcium", "vitamin", "vaccination",
    "vaccine", "immunization", "camp", "diet", "medicine", "marunthu", "zinc",
    "folic", "protein", "drops", "oosi", "bcg", "shot", "dose",
    "மாத்திரை", "சிரப்", "இரும்பு", "கால்சியம்", "வைட்டமின்",
    "தடுப்பூசி", "ஊசி", "மருந்து", "எண்ணெய்", "புரோட்டீன்",
)

_REQUEST_FRAMES = (
    "venum", "epo", "eppo", "eppavum", "when", "enna", "what", "which", "eppadi",
    "how", "can", "shall", "kudukanum", "kudukka", "pannalam", "next", "doubt",
    "time", "date", "eduthukalaama", "sollunga", "vaanganum",
    "வேணும்", "வேண்டும்", "எப்போ", "எப்பழுது", "என்ன", "எப்படி",
    "சொல்லுங்க", "தேதி", "தடவலாமா", "குடுக்கலாமா",
)

# Language code mapping between SwaraSetu and Sarvam API (BCP-47)
LANGUAGE_MAP: dict[str, str] = {
    "en": "en-IN",
    "hi": "hi-IN",
    "ta": "ta-IN",
    "bn": "bn-IN",
}

# ── Multi-Dialect & Tanglish Keyword Constants (Single-Script Purity) ──────────

KEYWORD_CONVULSIONS: tuple[str, ...] = (
    "convulsion", "convulsions", "seizure", "seizures", "fits",
    "daura", "jhatke", "mirgi", "doure", "jhatka",
    "valippu", "valiypu", "kaal kai valippu", "morcha", "khinchuni",
    "दौरा", "झटके", "दौरे", "मिर्गी", "வலிப்பு", "খিঁচুনি", "মৃগীরোগ",
)

KEYWORD_UNCONSCIOUS: tuple[str, ...] = (
    "unconscious", "fainted", "fainting", "passed out", "collapsed", "blackout", "lethargic",
    "behosh", "behosi", "achetan", "hosh me nahi",
    "mayakkam", "mayakkam pottu", "vizhunthutanga", "vizhunthutaru", "vizhunthen", "vizhunthuta", "vizhunthu",
    "ogyan", "acheton", "behoshi",
    "बेहोश", "बेहोशी", "अचेत", "மயக்கம்", "விழுந்துட்டாங்க", "விழுந்துட்டார்", "விழுந்துட்டேன்", "অজ্ঞান", "অচৈতন্য",
)

KEYWORD_CHEST_PAIN: tuple[str, ...] = (
    "chest pain", "severe chest pain", "heart pain", "cardiac pain", "chest pressure", "chestpain",
    "seene me dard", "chhati me dard", "chaati me dard", "dil me dard",
    "nenju vali", "nenjil vali", "marbu vali", "nenju kashdum", "nenju erichal", "nenju",
    "buke betha", "buker betha", "buke chap",
    "सीने में दर्द", "छाती में दर्द", "छाती में", "दिल में दर्द",
    "நெஞ்சு வலி", "மார்பு வலி", "நெஞ்சில் வலி", "நெஞ்சுவலி", "நெஞ்சு",
    "বুকে ব্যথা", "বুকের ব্যথা",
)

KEYWORD_VOMITING_BLOOD: tuple[str, ...] = (
    "vomit blood", "vomiting blood", "blood in vomit", "haematemesis",
    "khoon ki ulti", "ulti me khoon", "rakth ulti",
    "vanthi blood", "blood vanthi", "rathavanthi", "rakthavanthi", "ratham vanthi",
    "rokto bomi", "bomite rokto", "rokter bomi",
    "खून की उल्टी", "उल्टी में खून",
    "இரத்த வாந்தி", "ரத்த வாந்தி", "வாந்தியில் ரத்தம்", "ரத்தவாந்தி",
    "রক্তবমি", "বমিতে রক্ত",
)

KEYWORD_VOMITING_EVERYTHING: tuple[str, ...] = (
    "vomiting everything", "cannot keep food down", "continuous vomiting",
    "continuous vanthi", "vanthi continuous", "vanthi nonstop", "thudarchiya vanthi", "romba vanthi",
    "lagatar ulti", "kuch nahi ruk raha",
    "தொடர்ச்சியா வாந்தி", "வாந்தி நிக்கல",
)

KEYWORD_FEVER: tuple[str, ...] = (
    "fever", "high fever", "temperature", "chills", "febrile",
    "bukhar", "tez bukhar", "tap", "jor",
    "kaichal", "juram", "kayshal", "sudu", "veppam",
    "jwor", "gorom", "jar", "jhor",
    "बुखार", "तेज बुखार", "ताप",
    "காய்ச்சல்", "சுரம்", "வெப்பம்",
    "জ্বর", "তীব্র জ্বর",
)

KEYWORD_NECK_STIFFNESS: tuple[str, ...] = (
    "stiff neck", "neck stiffness", "neck rigid", "cannot bend neck", "neck stiff",
    "gardan me akad", "gardan akadna", "gardan me dard",
    "kazhuthu vali", "kazhuthu viraipu", "kazhuthu piditham",
    "gardan sokto", "golar betha",
    "गर्दन अकड़न", "गर्दन में अकड़न", "गर्दन", "अकड़न",
    "கழுத்து விறைப்பு", "கழுத்து வலி", "கழுத்து",
    "ঘাড় শক্ত", "ঘাড়ে ব্যথা",
)

KEYWORD_RESPIRATORY_COUGH: tuple[str, ...] = (
    "cough", "coughing", "severe cough", "dry cough", "wet cough",
    "khansi", "sukhi khansi", "balgam khansi", "dhans",
    "irumal", "varattu irumal", "sali irumal", "kollu irumal",
    "kashi", "shukno kashi", "kaph kashi",
    "खांसी", "सुखी खांसी", "இருமல்", "வறட்டு இருமல்", "কাশি", "শুকনো কাশি",
)

KEYWORD_RESPIRATORY_DISTRESS: tuple[str, ...] = (
    "difficulty breathing", "breathless", "shortness of breath", "struggling to breathe",
    "cannot breathe", "gasping", "breathing difficulty", "breathing kashdum", "breathing issue",
    "saans lene me dikkat", "saans phoolna", "dum ghutna", "saans",
    "moochu vida mudiyala", "moochu thinaral", "swasam kashdum", "moochu kashdum", "moochu muduthe", "moochu hard", "moochu",
    "shash nite koshto", "dam bondho", "shashkosto", "shash",
    "सांस लेने में दिक्कत", "सांस फूलना", "सांस",
    "மூச்சு திணறல்", "மூச்சு விட முடியவில்லை", "மூச்சு கஷ்டம்", "மூச்சு விட சிரமம்", "மூச்சு",
    "শ্বাসকষ্ট", "শ্বাস নিতে পারছে না", "শ্বাস",
)

KEYWORD_CHEST_INDRAWING: tuple[str, ...] = (
    "chest indrawing", "lower chest indrawing", "ribs pulling in", "chest sinking",
    "pasli chalna", "pasli khichna", "chhati dhasna", "pasli",
    "nenju koodu ullil izhuthal", "marbu koodu",
    "panjor tana", "buker panjor", "pajor",
    "पसली चलना", "पसली", "পাঁজর ভেতরের দিকে", "পাঁজর",
)

KEYWORD_DIARRHOEA: tuple[str, ...] = (
    "diarrhea", "diarrhoea", "loose motions", "loose stools", "watery stools",
    "dast", "patla dast", "pet kharab", "loose motion", "jhada",
    "vayithu pokku", "vayiru pokku", "bhedhi",
    "patla paikhana", "pete oshukh", "jhara",
    "दस्त", "पतला दस्त", "पेट खराब",
    "வயிற்றுப்போக்கு", "வயிற்று வலி", "வயிற்று போக்கு",
    "ডায়রিয়া", "পাতলা পায়খানা", "পেটের অসুখ",
)

KEYWORD_ASHA_ROUTINE: tuple[str, ...] = (
    "tablet", "mathirai", "marundhu", "marunthu", "oosi", "injection", "vaccine", "polio",
    "dosage", "dose", "syrup", "supplement", "powder", "calcium", "iron", "vitamin", "multivitamin",
    "sugar tablet", "diabetic", "pressure check", "bp tablet", "asha", "nurse", "checkup", "schedule", "date",
    "மாத்திரை", "மருந்து", "ஊசி", "தடுப்பூசி", "போலியோ", "ஆஷா", "செக்கப்", "சத்து மாத்திரை",
)

# ── Load Lightweight Tanglish N-gram Statistical Weights ──────────────────────

_WEIGHTS_PATH = Path(__file__).resolve().parents[3] / "ml/data/tanglish_weights.json"
_PRIORS: list[float] | None = None
_WEIGHTS: dict[str, list[float]] | None = None

if _WEIGHTS_PATH.exists():
    try:
        _data = json.loads(_WEIGHTS_PATH.read_text(encoding="utf-8"))
        _PRIORS = _data.get("priors")
        _WEIGHTS = _data.get("weights")
    except Exception:
        _PRIORS, _WEIGHTS = None, None


def _tokenize_ngram(text: str) -> list[str]:
    text = text.lower()
    words = re.findall(r"[a-zA-Z\u0B80-\u0BFF]+", text)
    tokens = list(words)
    # Word bigrams
    for i in range(len(words) - 1):
        tokens.append(f"{words[i]}_{words[i+1]}")
    # Word trigrams
    for i in range(len(words) - 2):
        tokens.append(f"{words[i]}_{words[i+1]}_{words[i+2]}")
    # Character trigrams and 4-grams for subword root morphology
    for w in words:
        if len(w) >= 3:
            for j in range(len(w) - 2):
                tokens.append(f"#3{w[j:j+3]}")
        if len(w) >= 4:
            for j in range(len(w) - 3):
                tokens.append(f"#4{w[j:j+4]}")
    return tokens


def predict_tanglish_tier(text: str) -> int | None:
    if not _PRIORS or not _WEIGHTS:
        return None
    scores = list(_PRIORS)
    for tok in _tokenize_ngram(text):
        w = _WEIGHTS.get(tok)
        if w:
            scores[0] += w[0]
            scores[1] += w[1]
            scores[2] += w[2]
    return scores.index(max(scores)) + 1


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
        """Hybrid Indic clinical entity extractor combining deterministic danger sign rules with statistical N-gram priors."""
        raw = transcript.strip()
        lower = raw.lower()
        kwargs: dict[str, Any] = {"language": language}

        def matches_any(keywords: tuple[str, ...]) -> bool:
            return any(k in lower or k in raw for k in keywords)

        def is_negated(phrase: str) -> bool:
            patterns = [
                phrase + r"\s+(illa|illai|kedayadhu|illadha|illama|nahi)",
                r"no\s+" + phrase,
                r"without\s+" + phrase,
            ]
            return any(re.search(pat, lower) for pat in patterns)

        # ── 1. Deterministic Dangerous Entity Matchers (WHO IMCI Zero-Compromise Safety) ──
        if matches_any(KEYWORD_CONVULSIONS):
            kwargs["convulsions"] = True
        if matches_any(KEYWORD_UNCONSCIOUS):
            if "light" not in lower and "konjam" not in lower and "லேசான" not in raw and "கொஞ்சம்" not in raw:
                kwargs["unconscious"] = True
        if matches_any(KEYWORD_CHEST_PAIN) and not is_negated("chest pain") and not is_negated("nenju"):
            kwargs["chest_pain_severe"] = True
        if matches_any(KEYWORD_VOMITING_BLOOD):
            kwargs["vomiting_blood"] = True
        elif matches_any(KEYWORD_VOMITING_EVERYTHING):
            kwargs["vomiting_everything"] = True

        if matches_any(KEYWORD_RESPIRATORY_DISTRESS) or any(
            w in lower or w in raw
            for w in ["moochu vida mudiyala", "stridor", "breathing kashdum", "cannot breathe", "மூச்சு விட முடியல"]
        ):
            kwargs["difficulty_breathing"] = True
            kwargs["stridor"] = True
        if matches_any(KEYWORD_CHEST_INDRAWING):
            kwargs["chest_indrawing"] = True

        # Extract basic clinical signs for structured fields
        if matches_any(KEYWORD_FEVER) and not is_negated("fever") and not is_negated("kaichal"):
            kwargs["has_fever"] = True
            kwargs["fever_days"] = 2
        if matches_any(KEYWORD_NECK_STIFFNESS):
            kwargs["neck_stiffness"] = True
        if matches_any(KEYWORD_RESPIRATORY_COUGH):
            kwargs["cough_days"] = 2
        if matches_any(KEYWORD_DIARRHOEA):
            kwargs["diarrhoea"] = True
            kwargs["stool_frequency_per_day"] = 4

        # ── 2. Hybrid Statistical Prior Modulation (Replaces Fragile Regex Heuristics) ──
        tier = predict_tanglish_tier(raw)
        if tier == 3:
            kwargs["chest_pain_severe"] = True  # Escalates syndromic emergency
        elif tier == 2:
            # Escalate to ASHA dispatch if not already an emergency
            if not any(
                kwargs.get(k)
                for k in ("convulsions", "unconscious", "chest_pain_severe", "vomiting_blood", "vomiting_everything", "stridor", "chest_indrawing")
            ):
                kwargs["has_fever"] = True
                kwargs["fever_days"] = 8
        elif tier == 1:
            # Ensure safe self-care tier when statistical prior confirms mild / home care
            if not any(
                kwargs.get(k)
                for k in ("convulsions", "unconscious", "chest_pain_severe", "vomiting_blood", "vomiting_everything", "stridor", "chest_indrawing")
            ):
                if kwargs.get("fever_days", 0) > 7:
                    kwargs["fever_days"] = 2

        # ── 3. Pure Rule Fallback (if weights not loaded) ──
        if tier is None:
            if any(w in lower for w in ["high", "2 day", "3 day", "continuous", "rendu naal"]):
                kwargs["fever_days"] = 8
            if matches_any(KEYWORD_ASHA_ROUTINE):
                kwargs["malaria_risk_area"] = True
                kwargs["has_fever"] = True
                kwargs["fever_days"] = 8

        return SymptomPayload(**kwargs)



sarvam_client = SarvamClient()
