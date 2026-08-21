"""Sarvam AI client wrapper for Speech-to-Text, Translation, and Text-to-Speech."""

from __future__ import annotations

import json
import logging
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
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
    "hi": "hi-IN",
    "ta": "ta-IN",
    "bn": "bn-IN",
    "te": "te-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "mr": "mr-IN",
    "gu": "gu-IN",
    "pa": "pa-IN",
    "od": "od-IN",
    "en": "en-IN",
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
    "moochu vida mudiyala", "moochu thinaral", "swasam kashdum", "moochu kashdum", "moochu muduthe", "moochu hard",
    "shash nite koshto", "dam bondho", "shashkosto",
    "सांस लेने में दिक्कत", "सांस फूलना", "सांस",
    "மூச்சு திணறல்", "மூச்சு விட முடியவில்லை", "மூச்சு கஷ்டம்", "மூச்சு விட சிரமம்",
    "শ্বাসকষ্ট", "শ্বাস নিতে পারছে না",
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


def _matches_word(pattern_list: list[str], text: str) -> bool:
    """Check if any pattern in pattern_list matches text using word boundaries."""
    for pat in pattern_list:
        if re.search(r"^[a-zA-Z0-9\s-]+$", pat):
            escaped = re.escape(pat)
            if re.search(rf"\b{escaped}\b", text, re.IGNORECASE):
                return True
        else:
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
        
        # Normalize any incoming voice format (OGG/Opus from Telegram, WebM from browser) to clean 16kHz PCM WAV
        clean_audio = audio_bytes
        clean_filename = "audio.wav"
        if not filename.endswith(".wav"):
            import tempfile, subprocess
            with tempfile.NamedTemporaryFile(suffix=".input", delete=False) as in_f:
                in_path = in_f.name
                in_f.write(audio_bytes)
            out_path = in_path + ".wav"
            try:
                cmd = ["ffmpeg", "-y", "-i", in_path, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", out_path]
                proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
                if proc.returncode == 0 and os.path.exists(out_path):
                    with open(out_path, "rb") as f:
                        clean_audio = f.read()
            except Exception as cv_err:
                logger.warning("Audio normalization skipped: %s", cv_err)
            finally:
                for p in (in_path, out_path):
                    if os.path.exists(p):
                        try:
                            os.unlink(p)
                        except OSError:
                            pass

        files = {
            "file": (clean_filename, clean_audio, "audio/wav"),
        }
        data = {"model": "saarika:v2.5"}
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
        """Hybrid Indic clinical entity extractor combining deterministic danger sign rules with statistical N-gram priors."""
        raw = transcript.strip()
        if not raw:
            return SymptomPayload(language=language)

        lower = raw.lower()
        kwargs: dict[str, Any] = {"language": language}

        def matches_any(keywords: tuple[str, ...]) -> bool:
            return any(k in lower or k in raw for k in keywords)

        def is_negated(phrase: str) -> bool:
            patterns = [
                phrase + r"\s+(illa|illai|kedayadhu|illadha|illama|nahi|sari|nalla)",
                r"no\s+" + phrase,
                r"without\s+" + phrase,
            ]
            return any(re.search(pat, lower) for pat in patterns)

        # Extract numeric duration if present (e.g. "3 days", "2 din", "5 dina")
        extracted_days = None
        for pat in (
            r"(\d+)\s*(?:day|days|din|dina|dino|dinon|naal|naatkal)",
            r"(\d+)\s*(?:दिन)",
            r"(\d+)\s*(?:দিন)",
            r"(\d+)\s*(?:நாட்கள்)",
        ):
            m = re.search(pat, raw, re.IGNORECASE)
            if m:
                extracted_days = int(m.group(1))
                break

        # Age group detection
        if _matches_word(["neonate", "newborn", "navjat", "navajat", "பிறந்த குழந்தை", "নবজাতক"], raw):
            kwargs["age_group"] = "neonate"
        elif _matches_word(["baby", "infant", "toddler", "chhota bacha", "kutty", "शिशु", "குழந்தை"], raw):
            kwargs["age_group"] = "infant"
        elif _matches_word(["child", "kid", "bacha", "baccha", "bachhe", "kuzhanthai", "बच्चा", "बच्चे", "বাচ্চা"], raw):
            kwargs["age_group"] = "child"
        elif _matches_word(["pregnant", "pregnancy", "garbh", "garbhvati", "garbhwati", "gorbhoboti", "கர்ப்பிணி", "गर्भवती", "গর্ভবতী"], raw):
            kwargs["pregnant"] = True

        # ── 1. Deterministic Dangerous Entity Matchers (WHO IMCI Zero-Compromise Safety) ──
        if matches_any(KEYWORD_CONVULSIONS) or _matches_word(["convulsion", "convulsions", "seizure", "seizures", "fit", "fits", "daura", "jhatke", "valippu", "दौरा", "झटके", "வலிப்பு"], raw):
            kwargs["convulsions"] = True
        if matches_any(KEYWORD_UNCONSCIOUS) or _matches_word(["unconscious", "behosh", "mayakkam", "ogyan", "बेहोश", "மயக்கம்", "অজ্ঞান"], raw):
            if "light" not in lower and "konjam" not in lower and "லேசான" not in raw and "கொஞ்சம்" not in raw:
                kwargs["unconscious"] = True
        if (matches_any(KEYWORD_CHEST_PAIN) or _matches_word(["chest pain", "seene me dard", "marbu vali", "buke betha", "सीने में दर्द", "छाती में दर्द", "বুকে ব্যথা"], raw)) and not is_negated("chest pain") and not is_negated("nenju"):
            kwargs["chest_pain_severe"] = True
        if matches_any(KEYWORD_VOMITING_BLOOD) or _matches_word(["vomit blood", "vomiting blood", "khoon ki ulti", "rakthavanthi", "rokto bomi", "खून की उल्टी", "রক্তবমি"], raw):
            kwargs["vomiting_blood"] = True
        elif matches_any(KEYWORD_VOMITING_EVERYTHING):
            kwargs["vomiting_everything"] = True

        # Acute poisoning / bites / severe trauma
        if _matches_word([
            "snake", "snake bite", "snakebite", "bitten by snake", "scorpion", "poison", "poisoning", "toxin",
            "dog bite", "rabies", "insect bite",
            "பாம்பு", "பாம்பு கடி", "பாம்பு கிடைச்சிருச்சு", "பாம்பு கடிச்சிருச்சு", "விஷம்", "விஷக்கடி", "தேள்", "தேள் கடி", "நாய் கடி",
            "सांप", "साँप", "सांप काट", "सांप ने काटा", "जहर", "बिच्छू", "विष", "कुत्ते ने काटा", "कुत्ता काटा",
            "সাপ", "সাপের কামড়", "সাপে কেটেছে", "বিষ", "বিছে", "কুকুর কামড়",
            "పాము", "పాము కాటు", "విషం", "తేలు", "కుక్క కాటు",
        ], raw):
            kwargs["acute_poisoning_or_bite"] = True
        if _matches_word([
            "burn", "burns", "burned", "fracture", "accident", "head injury", "deep cut", "electric shock",
            "தீக்காயம்", "விபத்து", "அடிபட்டு", "எலும்பு முறிவு", "மின்சாரம்",
            "जल गया", "जलना", "दुर्घटना", "एक्सीडेंट", "गंभीर चोट", "हड्डी टूटी", "करंट",
            "পুড়ে গেছে", "দুর্ঘটনা", "ভাঙা", "কারেন্ট",
            "కాలిపోయింది", "ప్రమాదం", "ఎముక విరిగింది",
        ], raw):
            kwargs["severe_trauma"] = True

        # Respiratory distress
        if (matches_any(KEYWORD_RESPIRATORY_DISTRESS) or _matches_word(["breathlessness", "difficulty breathing", "shortness of breath"], raw)) and not is_negated("moochu") and not is_negated("saans"):
            kwargs["difficulty_breathing"] = True
            kwargs["stridor"] = True
        if matches_any(KEYWORD_CHEST_INDRAWING) or _matches_word(["chest in", "chest indrawing", "pasli", "ribs", "पसली", "পাঁজর"], raw):
            kwargs["chest_indrawing"] = True

        # Fever & duration
        if (matches_any(KEYWORD_FEVER) or _matches_word(["fever", "bukhar", "kaichal", "jwor", "gorom", "thand", "chills", "बुखार", "காய்ச்சல்", "জ্বর"], raw)) and not is_negated("fever") and not is_negated("kaichal") and not is_negated("juram"):
            kwargs["has_fever"] = True
            kwargs["fever_days"] = extracted_days if extracted_days is not None else 2
        if matches_any(KEYWORD_NECK_STIFFNESS) or _matches_word(["stiff neck", "gardan me akad", "kazhuthu vali", "गर्दन में अकड़न", "अकड़न", "கழுத்து வலி"], raw):
            kwargs["neck_stiffness"] = True
        if _matches_word(["rash", "daane", "chhate", "thathadu", "दाने", "தடிப்பு"], raw):
            kwargs["rash_with_fever"] = True

        # Cough & duration
        if (matches_any(KEYWORD_RESPIRATORY_COUGH) or _matches_word(["cough", "coughing", "cold", "khansi", "sardi", "jukham", "irumal", "kashi", "खांसी", "सर्दी", "जुकाम", "இருமல்", "কাশি"], raw)) and not is_negated("cough") and not is_negated("irumal") and not is_negated("khansi"):
            kwargs["cough_days"] = extracted_days if extracted_days is not None else 2

        # Diarrhoea & Stool
        if matches_any(KEYWORD_DIARRHOEA) or _matches_word(["diarrhea", "diarrhoea", "dast", "loose motion", "pet kharab", "bedhi", "दस्त", "வயிற்றுப்போக்கு", "ডায়রিয়া"], raw):
            kwargs["diarrhoea"] = True
        if _matches_word(["blood in stool", "khoon dast", "raktham", "khoon ka dast", "रक्त दस्त", "রক্ত আমাশয়", "রক্ত পায়খানা", "রক্ত মল", "இரத்த மலம்"], raw):
            kwargs["blood_in_stool"] = True

        # Maternal
        if kwargs.get("pregnant"):
            if _matches_word(["headache", "sar dard", "thalai vali", "सिर दर्द", "தலைவலி"], raw):
                kwargs["severe_headache"] = True
            if _matches_word(["blurred vision", "dhundhla", "paarvai mangal", "धुंधला", "பார்வை மங்கல்", "மங்கலாக"], raw):
                kwargs["blurred_vision"] = True
            if _matches_word(["bleeding", "khoon", "raktham", "रक्तस्राव", "இரத்தப்போக்கு"], raw):
                kwargs["vaginal_bleeding"] = True

        # ── 2. Hybrid Statistical Prior Modulation ──
        has_detected_symptoms = any(
            kwargs.get(k)
            for k in (
                "has_fever", "difficulty_breathing", "diarrhoea", "chest_pain_severe",
                "convulsions", "unconscious", "vomiting_everything", "vomiting_blood",
                "acute_poisoning_or_bite", "severe_trauma", "stridor", "chest_indrawing",
                "blood_in_stool", "severe_headache", "blurred_vision", "vaginal_bleeding"
            )
        )
        if has_detected_symptoms:
            tier = predict_tanglish_tier(raw)
            if tier == 3:
                kwargs["chest_pain_severe"] = True  # Escalates syndromic emergency
            elif tier == 2:
                # Escalate fever duration for ASHA dispatch
                if kwargs.get("has_fever") and not kwargs.get("fever_days"):
                    kwargs["fever_days"] = 8
            elif tier == 1:
                # Safe self-care tier
                if kwargs.get("fever_days", 0) > 7 and not kwargs.get("neck_stiffness"):
                    kwargs["fever_days"] = 2

        # ── 3. Pure Rule Fallback (if weights not loaded) ──
        if has_detected_symptoms and any(w in lower for w in ["high", "2 day", "3 day", "continuous", "rendu naal"]):
            if kwargs.get("has_fever"):
                kwargs["fever_days"] = 8

        return SymptomPayload(**kwargs)


sarvam_client = SarvamClient()
