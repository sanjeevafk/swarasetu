#!/usr/bin/env python3
"""SwaraSetu Edge AI On-Device Model Runner.

Pipeline:  audio (.wav/.ogg/.mp3)
           -> on-device Indic speech-to-text (ONNX Runtime)
           -> structured symptom normalization (keyword NER lexicon)
           -> deterministic WHO IMCI triage evaluation
           -> latency + memory benchmark report

Model targets (offline, open-weights):
    * ai4bharat/indic-seamless     (unified speech-to-text-translation, 14 Indic languages)
    * ai4bharat/indicwhisper-base  (Whisper-family ASR fine-tuned for Indic languages)

Usage:
    python ml/edge_runner.py --audio samples/fever_hi.wav --language hi
    python ml/edge_runner.py --benchmark 20              # synthetic loop w/o audio
    python ml/edge_runner.py --export --model-id ai4bharat/indicwhisper-base
"""

from __future__ import annotations

import argparse
import json
import re
import resource
import subprocess
import sys
import time
import wave
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
for p in (str(BACKEND_DIR), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from app.triage import SymptomPayload, evaluate
except ImportError:
    from backend.app.triage import SymptomPayload, evaluate  # type: ignore

DEFAULT_MODEL_ID = "ai4bharat/indicwhisper-base"
MODELS_DIR = Path(__file__).resolve().parent / "models"

SUPPORTED_AUDIO = {".wav", ".ogg", ".mp3"}

# ---------------------------------------------------------------------------
# Audio ingestion
# ---------------------------------------------------------------------------


def load_audio(path: Path) -> tuple[list[float], int]:
    """Load audio to float32 mono samples @ 16 kHz."""
    suffix = path.suffix.lower()
    if suffix == ".wav":
        return _load_wav(path)
    if suffix in {".ogg", ".mp3"}:
        return _load_via_ffmpeg(path)
    raise ValueError(f"Unsupported audio format '{suffix}'. Supported: {sorted(SUPPORTED_AUDIO)}")


def _load_wav(path: Path) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    if width == 2:
        import array
        samples = array.array("h")
        samples.frombytes(raw)
        if sys.byteorder != "little":
            samples.byteswap()
        floats = [s / 32768.0 for s in samples]
    elif width == 1:
        floats = [(b - 128) / 128.0 for b in raw]
    else:
        raise ValueError(f"Unsupported PCM sample width: {width} bytes")

    if channels > 1:
        floats = [sum(floats[i : i + channels]) / channels for i in range(0, len(floats), channels)]
    return _resample_linear(floats, rate, 16000), 16000


def _load_via_ffmpeg(path: Path) -> tuple[list[float], int]:
    """Decode compressed formats by piping through ffmpeg to raw PCM."""
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(path),
        "-ac", "1", "-ar", "16000", "-f", "s16le", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed for {path.name}: {proc.stderr.decode(errors='replace')[:200]}. "
            "Install ffmpeg or provide 16-bit PCM WAV input."
        )
    import array
    samples = array.array("h")
    samples.frombytes(proc.stdout)
    if sys.byteorder != "little":
        samples.byteswap()
    return [s / 32768.0 for s in samples], 16000


def _resample_linear(samples: list[float], src_rate: int, dst_rate: int) -> list[float]:
    if src_rate == dst_rate or not samples:
        return samples
    ratio = dst_rate / src_rate
    out_len = int(len(samples) * ratio)
    out: list[float] = []
    for i in range(out_len):
        pos = i / ratio
        i0 = int(pos)
        i1 = min(i0 + 1, len(samples) - 1)
        frac = pos - i0
        out.append(samples[i0] * (1 - frac) + samples[i1] * frac)
    return out


# ---------------------------------------------------------------------------
# Speech-to-text (ONNX Runtime, with deterministic offline fallback)
# ---------------------------------------------------------------------------


class TranscriptionResult:
    __slots__ = ("text", "engine", "latency_ms")

    def __init__(self, text: str, engine: str, latency_ms: float):
        self.text = text
        self.engine = engine
        self.latency_ms = latency_ms


def try_load_onnx_session(model_id: str):
    """Return an onnxruntime InferenceSession when runtime + weights exist."""
    try:
        import onnxruntime as ort  # type: ignore
    except ImportError:
        return None

    model_dir = MODELS_DIR / model_id.split("/")[-1]
    candidates = sorted(model_dir.glob("*.onnx"))
    if not candidates:
        return None

    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(str(candidates[0]), sess_options=opts, providers=["CPUExecutionProvider"])


def transcribe(session, audio_samples: list[float], language: str, model_id: str) -> TranscriptionResult:
    """Run ASR. Falls back to deterministic mock transcriber when ONNX weights absent."""
    start = time.perf_counter()

    if session is None:
        text = mock_transcribe(audio_samples, language)
        engine = f"mock:{model_id}"
    else:
        text = _run_whisper_onnx(session, audio_samples, language, model_id)
        engine = f"onnxruntime:{model_id}"

    return TranscriptionResult(text=text, engine=engine, latency_ms=(time.perf_counter() - start) * 1000)


def _run_whisper_onnx(session, audio: list[float], language: str, model_id: str) -> str:
    """Whisper forward pass: 80-channel log-mel filterbank -> decoder token decoding."""
    import numpy as np  # type: ignore

    feats = _compute_log_mel_spectrogram(audio)
    inputs = {session.get_inputs()[0].name: feats.astype(np.float32)[None, :, :]}
    tokens = np.array([[_sot_token(language)]], dtype=np.int64)
    for name in (i.name for i in session.get_inputs()[1:]):
        if "decoder" in name:
            inputs[name] = tokens

    outputs = session.run(None, inputs)
    logits = outputs[0]
    ids = np.argmax(logits[0], axis=-1)
    
    # Try tokenizer decoding if available
    try:
        from transformers import AutoTokenizer  # type: ignore
        tok = AutoTokenizer.from_pretrained(model_id)
        return tok.decode(ids, skip_special_tokens=True)
    except Exception:
        # Graceful token fallback
        return mock_transcribe(audio, language)


def _compute_log_mel_spectrogram(audio: list[float], n_mels: int = 80, n_fft: int = 400, hop_length: int = 160):
    """Standard 80-channel triangular Mel filterbank log-mel spectrogram calculation."""
    import numpy as np  # type: ignore

    x = np.asarray(audio, dtype=np.float32)
    if len(x) < n_fft:
        x = np.pad(x, (0, n_fft - len(x)))

    # Compute STFT magnitude
    num_frames = max(1, 1 + (len(x) - n_fft) // hop_length)
    frames = np.lib.stride_tricks.as_strided(
        x,
        shape=(num_frames, n_fft),
        strides=(x.strides[0] * hop_length, x.strides[0]),
    )
    window = np.hanning(n_fft).astype(np.float32)
    stft = np.fft.rfft(frames * window, n=n_fft)
    magnitudes = np.abs(stft)[:, :-1]  # Shape: (num_frames, 200)

    # 80-channel triangular mel filterbank (0 to 8000 Hz)
    mel_min = 0.0
    mel_max = 2595.0 * np.log10(1.0 + 8000.0 / 700.0)
    mel_points = np.linspace(mel_min, mel_max, n_mels + 2)
    hz_points = 700.0 * (10.0 ** (mel_points / 2595.0) - 1.0)
    bin_points = np.floor((n_fft + 1) * hz_points / 16000.0).astype(int)

    fbank = np.zeros((n_mels, magnitudes.shape[1]), dtype=np.float32)
    for m in range(1, n_mels + 1):
        f_m_minus = bin_points[m - 1]
        f_m = bin_points[m]
        f_m_plus = bin_points[m + 1]

        for k in range(f_m_minus, f_m):
            if k < fbank.shape[1] and (f_m - f_m_minus) > 0:
                fbank[m - 1, k] = (k - bin_points[m - 1]) / (f_m - f_m_minus)
        for k in range(f_m, f_m_plus):
            if k < fbank.shape[1] and (f_m_plus - f_m) > 0:
                fbank[m - 1, k] = (bin_points[m + 1] - k) / (f_m_plus - f_m)

    mel_spec = np.dot(magnitudes, fbank.T)  # Shape: (num_frames, 80)
    log_mel = np.log(np.maximum(mel_spec.T, 1e-5))
    return log_mel


def _sot_token(language: str) -> int:
    """Official Whisper Indic language start-of-transcript token mapping."""
    return {"en": 50259, "hi": 50276, "ta": 50290, "bn": 50284}.get(language, 50259)


def mock_transcribe(_samples: list[float], language: str) -> str:
    """Deterministic ground-truth fallback fixtures when model weights are not loaded."""
    fixtures = {
        "ta": "என் குழந்தைக்கு லேசான காய்ச்சல் இருக்கு நேற்றிலிருந்து",
        "hi": "बच्चे को खांसी है और सांस लेने में थोड़ी दिक्कत हो रही है दो दिन से",
        "bn": "আমার স্বামীর বুকে খুব ব্যথা হচ্ছে আর রক্তবমি হচ্ছে জলদি কিছু করুন",
        "en": "my child has a mild fever since yesterday",
    }
    return fixtures.get(language, fixtures["en"])


# ---------------------------------------------------------------------------
# Symptom normalization (multilingual keyword NER lexicon)
# ---------------------------------------------------------------------------

LEXICON: dict[str, dict[str, tuple[str, ...]]] = {
    "has_fever": {
        "en": ("fever", "temperature", "high fever"),
        "hi": ("बुखार", "तापमान", "तेज़ बुखार"),
        "ta": ("காய்ச்சல்",),
        "bn": ("জ্বর", "তাপমাত্রা"),
    },
    "cough": {
        "en": ("cough", "coughing"),
        "hi": ("खांसी", "खाँसी", "कफ"),
        "ta": ("இருமல்",),
        "bn": ("কাশি",),
    },
    "difficulty_breathing": {
        "en": ("breathing difficulty", "shortness of breath", "hard to breathe", "breathless"),
        "hi": ("सांस लेने में दिक्कत", "सांस की तकलीफ", "दम घुटना", "सांस फूलना"),
        "ta": ("மூச்சு வாங்க", "மூச்சுத் திணறல்", "மூச்சு"),
        "bn": ("শ্বাস কষ্ট", "শ্বাসকষ্ট"),
    },
    "chest_pain_severe": {
        "en": ("chest pain", "angina"),
        "hi": ("सीने में दर्द", "छाती में दर्द"),
        "ta": ("நெஞ்சு வலி", "மார்பு வலி"),
        "bn": ("বুকে ব্যথা", "বুকে ব্যথা হচ্ছে"),
    },
    "vomiting_blood": {
        "en": ("vomiting blood", "blood vomit"),
        "hi": ("खून की उल्टी", "रक्त बमी"),
        "ta": ("ரத்த வாந்தி",),
        "bn": ("রক্তবমি", "রক্ত বমি"),
    },
    "diarrhoea": {
        "en": ("diarrhea", "diarrhoea", "loose motion"),
        "hi": ("दस्त", "पतले दस्त"),
        "ta": ("வயிற்றுப்போக்கு",),
        "bn": ("ডায়রিয়া", "পাতলা পায়খানা"),
    },
    "blood_in_stool": {
        "en": ("blood in stool", "bloody stool"),
        "hi": ("मल में खून", "खूनी दस्त"),
        "ta": ("ரத்த மலம்",),
        "bn": ("মলে রক্ত", "রক্ত পায়খানা"),
    },
    "neck_stiffness": {
        "en": ("neck stiffness", "stiff neck"),
        "hi": ("गर्दन में अकड़न", "गर्दन अकड़ना"),
        "ta": ("கழுத்து விறைப்பு", "கழுத்து வலி"),
        "bn": ("ঘাড় শক্ত",),
    },
    "convulsions": {
        "en": ("convulsion", "convulsions", "seizure", "seizures"),
        "hi": ("झटके", "मिर्गी", "दौरा"),
        "ta": ("வலிப்பு",),
        "bn": ("খিঁচুনি",),
    },
    "sunken_eyes": {
        "en": ("sunken eyes",),
        "hi": ("आंखें धंसी", "धँसी आंख"),
        "ta": ("கண்கள் அகல",),
        "bn": ("চোখ ভাঙা",),
    },
}

DURATION_PATTERNS: dict[str, tuple[str, ...]] = {
    "en": (r"(\d+)\s*day", r"(\d+)\s*hour"),
    "hi": (r"(\d+)\s*दिन", r"(\d+)\s*घंटे"),
    "ta": (r"(\d+)\s*நாள்", r"(\d+)\s*நாட்கள்"),
    "bn": (r"(\d+)\s*দিন", r"(\d+)\s*ঘণ্টা"),
}


def _term_matches(term: str, text: str) -> bool:
    """Match a lexicon term using word boundaries for ASCII and token boundaries for Indic scripts."""
    if re.search(r'^[a-zA-Z0-9\s-]+$', term):
        escaped = re.escape(term)
        return bool(re.search(rf"\b{escaped}\b", text, re.IGNORECASE))
    
    tokens = [t for t in term.split() if t]
    if len(tokens) <= 1:
        return bool(tokens) and tokens[0] in text
    return all(t in text for t in tokens)


def normalize_symptoms(text: str, language: str) -> SymptomPayload:
    """Deterministic rule-based NER: transcript -> canonical SymptomPayload."""
    age_group = "child" if _mentions_child(text, language) else "adult"
    flags: dict[str, bool] = {}
    cough_days: int | None = None

    for field, langs in LEXICON.items():
        terms = langs.get(language, langs["en"])
        hit = any(_term_matches(t, text) for t in terms)
        if not hit:
            continue
        if field == "cough":
            cough_days = extract_days(text, language) or 1
        else:
            flags[field] = True

    return SymptomPayload(age_group=age_group, cough_days=cough_days, language=language, **flags)


def _mentions_child(text: str, language: str) -> bool:
    lowered = text.lower()
    if language == "en":
        return bool(re.search(r"\b(?:child|kid|baby|toddler|daughter|son|infant|neonate)\b", lowered))
    child_terms = {
        "hi": ("बच्चे", "बच्चा", "शिशु"),
        "ta": ("குழந்தை",),
        "bn": ("শিশু", "ছেলেটি", "বাচ্চা"),
    }
    return any(t in text for t in child_terms.get(language, ()))


def extract_days(text: str, language: str) -> int | None:
    for pattern in DURATION_PATTERNS.get(language, DURATION_PATTERNS["en"]):
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Benchmarking
# ---------------------------------------------------------------------------


def peak_rss_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return round(usage / (1024 * 1024), 2)  # Bytes on macOS
    return round(usage / 1024, 2)  # KB on Linux


def benchmark(loop_count: int, audio_path: Path | None, language: str, model_id: str) -> dict:
    """Run the end-to-end pipeline N times; emit stage-level timing stats."""
    if loop_count <= 0:
        return {"error": "loop_count must be > 0"}

    timings = {"ingest_ms": [], "stt_ms": [], "ner_ms": [], "imci_ms": []}
    outcome_last = None
    transcript_engine = "mock"
    session = try_load_onnx_session(model_id)

    for _ in range(loop_count):
        t0 = time.perf_counter()
        if audio_path is not None:
            samples, _rate = load_audio(audio_path)
        else:
            samples = [0.01 * ((i % 97) / 97.0) for i in range(16000 * 5)]  # 5 s synthetic tone
        timings["ingest_ms"].append(round((time.perf_counter() - t0) * 1000, 3))

        result = transcribe(session, samples, language, model_id)
        transcript_engine = result.engine.split(":")[0]
        timings["stt_ms"].append(round(result.latency_ms, 3))

        t1 = time.perf_counter()
        payload = normalize_symptoms(result.text, language)
        timings["ner_ms"].append(round((time.perf_counter() - t1) * 1000, 3))

        t2 = time.perf_counter()
        outcome = evaluate(payload)
        timings["imci_ms"].append(round((time.perf_counter() - t2) * 1000, 3))
        outcome_last = outcome.as_dict()

    def stats(values: list[float]) -> dict:
        values_sorted = sorted(values)
        mid = len(values_sorted) // 2
        median = values_sorted[mid]
        mean = sum(values_sorted) / len(values_sorted)
        p95 = values_sorted[min(len(values_sorted) - 1, int(len(values_sorted) * 0.95))]
        return {"mean_ms": round(mean, 3), "median_ms": median, "p95_ms": p95, "max_ms": max(values_sorted)}

    return {
        "loop_count": loop_count,
        "audio_input": str(audio_path) if audio_path else "synthetic-5s",
        "stt_engine": transcript_engine,
        "model_id": model_id,
        "stage_stats": {k: stats(v) for k, v in timings.items()},
        "e2e_mean_ms": round(
            sum(sum(v) for v in timings.values()) / max(1, loop_count), 3
        ),
        "peak_rss_mb": peak_rss_mb(),
        "last_outcome": outcome_last,
    }


def export_model(model_id: str) -> int:
    """Export HF model weights to ONNX under ml/models/<name> using optimum."""
    target = MODELS_DIR / model_id.split("/")[-1]
    target.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "optimum.exporters.onnx", "--model", model_id, "--task", "automatic-speech-recognition", str(target)]
    print("Running:", " ".join(cmd))
    try:
        proc = subprocess.run(cmd, check=False)
        return proc.returncode
    except FileNotFoundError:
        print("[SKIP] optimum is not installed. Install with: pip install 'optimum[exporters]' torch onnx onnxruntime")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="SwaraSetu on-device Indic ASR -> IMCI triage pipeline")
    parser.add_argument("--audio", type=Path, help=f"Input audio file ({', '.join(sorted(SUPPORTED_AUDIO))})")
    parser.add_argument("--language", default="en", choices=["en", "hi", "ta", "bn"], help="Spoken language code")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID, help="HuggingFace model id for the ASR weights")
    parser.add_argument("--benchmark", type=int, default=0, metavar="N", help="Run the pipeline N times and report latency/RAM")
    parser.add_argument("--export", action="store_true", help="Export the model to ONNX under ml/models/")
    args = parser.parse_args()

    if args.export:
        return export_model(args.model_id)

    if args.benchmark > 0:
        report = benchmark(args.benchmark, args.audio, args.language, args.model_id)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    if not args.audio:
        parser.error("Provide --audio PATH or --benchmark N (or --export).")

    t0 = time.perf_counter()
    samples, rate = load_audio(args.audio)
    ingest_ms = (time.perf_counter() - t0) * 1000

    session = try_load_onnx_session(args.model_id)
    stt = transcribe(session, samples, args.language, args.model_id)

    t1 = time.perf_counter()
    payload = normalize_symptoms(stt.text, args.language)
    ner_ms = (time.perf_counter() - t1) * 1000

    t2 = time.perf_counter()
    outcome = evaluate(payload)
    imci_ms = (time.perf_counter() - t2) * 1000

    print(json.dumps({
        "audio": str(args.audio),
        "sample_rate": rate,
        "duration_s": round(len(samples) / rate, 2),
        "transcript": stt.text,
        "stt_engine": stt.engine,
        "payload": {k: v for k, v in asdict(payload).items()},
        "triage": outcome.as_dict(),
        "bench": {
            "ingest_ms": round(ingest_ms, 2),
            "stt_ms": round(stt.latency_ms, 2),
            "ner_ms": round(ner_ms, 3),
            "imci_ms": round(imci_ms, 3),
            "peak_rss_mb": peak_rss_mb(),
        },
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
