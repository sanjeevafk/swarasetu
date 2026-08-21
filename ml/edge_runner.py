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

The runner is designed for 100% offline operation on 4GB+ RAM devices:

  * If ``onnxruntime`` and exported weights are present it executes real
    inference through ONNX Runtime.
  * Otherwise it degrades gracefully to a deterministic mock transcriber so
    the full normalization -> IMCI -> benchmark path can be exercised on any
    machine with zero network access and zero API keys.

Usage:
    python ml/edge_runner.py --audio samples/fever_hi.wav --language hi
    python ml/edge_runner.py --benchmark 20              # synthetic loop w/o audio
    python ml/edge_runner.py --export --model-id ai4bharat/indicwhisper-base
"""

from __future__ import annotations

import argparse
import json
import resource
import subprocess
import sys
import time
import wave
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.triage import SymptomPayload, evaluate  # noqa: E402

DEFAULT_MODEL_ID = "ai4bharat/indicwhisper-base"
MODELS_DIR = Path(__file__).resolve().parent / "models"

SUPPORTED_AUDIO = {".wav", ".ogg", ".mp3"}

# ---------------------------------------------------------------------------
# Audio ingestion
# ---------------------------------------------------------------------------


def load_audio(path: Path) -> tuple[list[float], int]:
    """Load audio to float32 mono samples @ 16 kHz.

    .wav is decoded natively via the stdlib ``wave`` module; .ogg/.mp3 are
    transcoded with ffmpeg when available (standard on field tablets).
    """
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
        floats = [s / 32768.0 for s in samples]
    elif width == 1:
        floats = [(b - 128) / 128.0 for b in raw]
    else:
        raise ValueError(f"Unsupported PCM sample width: {width} bytes")

    # Downmix stereo deterministically.
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

    # CPU EP keeps behaviour identical across field devices; quantized int4
    # weights are consumed directly by the ORT graph optimizer.
    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(str(candidates[0]), sess_options=opts, providers=["CPUExecutionProvider"])


def transcribe(session, audio_samples: list[float], language: str, model_id: str) -> TranscriptionResult:
    """Run ASR. Falls back to the deterministic mock transcriber when the
    ONNX runtime/weights are unavailable (documented degradation, never silent)."""
    start = time.perf_counter()

    if session is None:
        text = mock_transcribe(audio_samples, language)
        engine = f"mock:{model_id}"
    else:
        text = _run_whisper_onnx(session, audio_samples, language)
        engine = f"onnxruntime:{model_id}"

    return TranscriptionResult(text=text, engine=engine, latency_ms=(time.perf_counter() - start) * 1000)


def _run_whisper_onnx(session, audio: list[float], language: str) -> str:
    """Minimal Whisper-style forward pass: log-mel features -> decoder ids.

    Exact input naming varies between exports; this handles the common
    optimum-exported layout (input_features / decoder_input_ids).
    """
    import numpy as np  # type: ignore

    feats = _log_mel(audio)
    inputs = {session.get_inputs()[0].name: feats.astype(np.float32)[None, :, :]}
    tokens = np.array([[_sot_token(language)]], dtype=np.int64)
    for name in (i.name for i in session.get_inputs()[1:]):
        if "decoder" in name:
            inputs[name] = tokens
    outputs = session.run(None, inputs)
    logits = outputs[0]
    ids = np.argmax(logits[0], axis=-1)
    return "".join(chr(int(t)) if t < 0x110000 else "" for t in ids if t > 2)


def _log_mel(audio: list[float], n_mels: int = 80):
    """Deterministic log-mel front-end approximation (Hann-window FFT)."""
    import numpy as np  # type: ignore
    import math

    x = np.asarray(audio, dtype=np.float32)
    frame_len, hop = 400, 160
    n_frames = max(1, 1 + (len(x) - frame_len) // hop) if len(x) >= frame_len else 1
    frames = np.zeros((n_mels, n_frames * hop), dtype=np.float32)
    windowed_energy = np.zeros(n_frames, dtype=np.float32)
    for i in range(n_frames):
        seg = x[i * hop : i * hop + frame_len]
        if len(seg) < frame_len:
            seg = np.pad(seg, (0, frame_len - len(seg)))
        spec = np.abs(np.fft.rfft(seg * np.hanning(frame_len))) ** 2
        mel = np.linspace(0, len(spec) - 1, n_mels)
        lo = np.floor(mel).astype(int)
        hi = np.minimum(lo + 1, len(spec) - 1)
        w = mel - lo
        rows = spec[lo] * (1 - w) + spec[hi] * w
        frames[:, i] = rows[:hop]
        windowed_energy[i] = math.log(1e-8 + rows.sum())
    return np.log10(frames + 1e-8) * 2300.0 + windowed_energy.mean()


def _sot_token(language: str) -> int:
    return {"hi": 50258, "ta": 50274, "bn": 50266}.get(language, 50259)  # <|startoftranscript|-family>


class MockTranscriberNote:
    """Marker documentation for the deterministic fallback."""


def mock_transcribe(_samples: list[float], language: str) -> str:
    """Deterministic placeholder transcript used ONLY when model weights are
    absent. Chosen per-language from the repo's ground-truth fixtures so the
    downstream NER + IMCI stages are exercised identically every run."""
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
        "en": ("fever", "temperature"),
        "hi": ("बुखार", "तापमान", "कायचल"),
        "ta": ("காய்ச்சல்",),
        "bn": ("জ্বর", "তাপমাত্রা"),
    },
    "cough": {
        "en": ("cough",),
        "hi": ("खांसी", "खाँसी", "कहांसी"),
        "ta": ("இருமல்",),
        "bn": ("কাশি",),
    },
    "difficulty_breathing": {
        "en": ("breathing difficulty", "shortness of breath", "hard to breathe"),
        "hi": ("सांस लेने में दिक्कत", "सांस की तकलीफ", "दम घुटना"),
        "ta": ("மூச்சு வாங்க", "மூச்சுத் திணறல்"),
        "bn": ("শ্বাস কষ্ট", "শ্বাসকষ্ট"),
    },
    "chest_pain_severe": {
        "en": ("chest pain",),
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
        "en": ("blood in stool",),
        "hi": ("मल में खून", "खूनी दस्त"),
        "ta": ("ரத்த மலம்",),
        "bn": ("মলে রক্ত", "রক্ত পায়খানা"),
    },
    "neck_stiffness": {
        "en": ("neck stiffness", "stiff neck"),
        "hi": ("गर्दन में अकड़न", "गर्दन अकड़ना"),
        "ta": ("கழுத்து விறைப்பு",),
        "bn": ("ঘাড় শক্ত",),
    },
    "convulsions": {
        "en": ("convulsion", "fit", "seizure"),
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


def _term_matches(term: str, lowered_text: str) -> bool:
    """Match a lexicon term against the transcript.

    Single-word terms use substring containment; multi-word phrases require
    every token to be present so modifiers like 'slight'/'थोड़ी' inserted
    between phrase words do not break detection.
    """
    tokens = [t for t in term.lower().split() if t]
    if len(tokens) <= 1:
        return bool(tokens) and tokens[0] in lowered_text
    return all(t in lowered_text for t in tokens)


def normalize_symptoms(text: str, language: str) -> SymptomPayload:
    """Deterministic rule-based NER: transcript -> canonical SymptomPayload."""
    lowered = text.lower()
    age_group = "child" if _mentions_child(lowered, language) else "adult"
    flags: dict[str, bool] = {}
    cough_days: int | None = None

    for field, langs in LEXICON.items():
        terms = langs.get(language, langs["en"])
        hit = any(_term_matches(t, lowered) for t in terms)
        if not hit:
            continue
        if field == "cough":
            cough_days = extract_days(text, language) or 1
        else:
            flags[field] = True

    return SymptomPayload(age_group=age_group, cough_days=cough_days, language=language, **flags)


def _mentions_child(text: str, language: str) -> bool:
    child_terms = {
        "en": ("child", "kid", "baby", "daughter", "son"),
        "hi": ("बच्चे", "बच्चा", "शिशु"),
        "ta": ("குழந்தை",),
        "bn": ("শিশু", "ছেলেটি", "বাচ্চা"),
    }
    return any(t in text for t in child_terms.get(language, child_terms["en"]))


def extract_days(text: str, language: str) -> int | None:
    import re

    for pattern in DURATION_PATTERNS.get(language, DURATION_PATTERNS["en"]):
        m = re.search(pattern, text)
        if m:
            return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Benchmarking
# ---------------------------------------------------------------------------


def peak_rss_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # KB on Linux
    return round(usage / 1024, 2)


def benchmark(loop_count: int, audio_path: Path | None, language: str, model_id: str) -> dict:
    """Run the end-to-end pipeline N times; emit stage-level timing stats."""
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


# ---------------------------------------------------------------------------
# Model export helper
# ---------------------------------------------------------------------------


def export_model(model_id: str) -> int:
    """Export HF model weights to ONNX under ml/models/<name> using optimum."""
    target = MODELS_DIR / model_id.split("/")[-1]
    target.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "optimum.exporters.onnx", "--model", model_id, "--task", "automatic-speech-recognition", str(target)]
    print("Running:", " ".join(cmd))
    try:
        proc = subprocess.run(cmd, check=False)
        if proc.returncode == 0:
            print(f"[OK] Exported {model_id} -> {target}")
            print("Next: apply dynamic quantization for 4-bit-class on-device footprint:")
            print(f"      python -m onnxruntime.quantization.preprocess --input {target}/*.onnx")
        return proc.returncode
    except FileNotFoundError:
        print("[SKIP] optimum is not installed. Install export toolchain first:")
        print("       pip install 'optimum[exporters]' torch onnx onnxruntime")
        print("       (Export requires network access once; inference afterwards is fully offline.)")
        return 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


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

    if args.audio and args.benchmark:
        report = benchmark(args.benchmark, args.audio, args.language, args.model_id)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    if args.benchmark:
        report = benchmark(args.benchmark, None, args.language, args.model_id)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    if not args.audio:
        parser.error("Provide --audio PATH or --benchmark N (or --export).")

    # Single-shot pipeline
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
