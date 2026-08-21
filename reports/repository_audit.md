# SwaraSetu Repository Audit

**Date:** 2026-08-22 · **Repo:** `kendallcore/swarasetu` @ `main` (`68bf3b1`) · **Scope:** read-only inspection, no code modified.

---

## 1. Executive Summary

SwaraSetu is an offline-first, voice-native clinical triage assistant for rural India. The repo is a **working full-stack prototype**: React PWA frontend + FastAPI backend + deterministic WHO IMCI triage engine + rule-based multilingual NER + Sarvam AI cloud ASR/TTS integration stubs + an ONNX edge-ASR runner. There is **no trained ML model and no training pipeline** — all "intelligence" is a hand-written decision tree plus keyword lexicons.

The headline README claim — *"0% under-triage across 2,251 rural emergency cases"* — **is not reproducible with the current code**: running `backend/scripts/benchmark_protocols.py` yields **6.75% exact accuracy and a 91.74% under-triage rate** (details §8). Closing this gap is the single most important benchmark work item.

---

## 2. Current Architecture

```
Channels (WhatsApp/IVRS/Telegram webhooks)      Frontend (React 18 + Vite + TS + Tailwind)
        │  backend/app/routers/channels.py              │ src/lib/triageLocal.ts (offline engine mirror)
        ▼                                               │ src/lib/outbox.ts (IndexedDB-style sync)
FastAPI  backend/app/main.py  ◄────────────────────────┘ REST /api/v1/*
  ├── routers: triage, phcs, analytics, sync, channels
  ├── services: triage_service, sarvam_client, twilio_client, phc_service, analytics_service, sync_service
  ├── triage/  ← THE CORE: engine.py + clusters.py + types.py + messages.py
  └── models: Case, AshaAssignment, PHC (SQLAlchemy; SQLite default, Postgres-ready)
Edge ML   ml/edge_runner.py   audio → ONNX ASR → keyword NER → IMCI engine (+ latency/RAM benchmark)
Data      triage_input_output_clean.json (2,251) · triage_protocols_structured.json (2,251)
Tests     backend/tests (engine/API/channels, ~40 tests) · tests_e2e/ · CI .github/workflows/deploy.yml
```

Key properties:
- **Determinism by design** (`backend/app/triage/engine.py`): same payload ⇒ same outcome; no LLM/network in the decision path. Final risk = max over 5 clusters.
- **Online/offline parity contract**: `src/lib/triageLocal.ts` mirrors the Python engine 1:1 so offline tablet outcomes match cloud outcomes.
- **Fail-safe external calls**: `sarvam_client.py` returns empty transcripts / passes text through on any error ("zero-hallucination" policy).

## 3. Current "Model"

There is no learned model in the decision path:

| Component | Implementation | Location |
|---|---|---|
| Triage logic | Hand-coded WHO IMCI severity ladders over 5 clusters (general danger signs, fever, respiratory, diarrhoea/dehydration, maternal). Risk ∈ {1 Green self-care, 2 Yellow ASHA dispatch, 3 Red emergency referral}. | `backend/app/triage/clusters.py` |
| NER / normalization | Rule-based keyword lexicons with word-boundary matching for English/transliterations and Indic-script token matching; regex duration extraction; age-group heuristics. Two variants exist (backend lexicon ~10 langs incl. Telugu bite terms; edge lexicon en/hi/ta/bn only). | `backend/app/services/sarvam_client.py:extract_symptoms_rule_fallback`, `ml/edge_runner.py:LEXICON` |
| ASR | Cloud: Sarvam `/speech-to-text` (10 BCP-47 locales mapped). Edge: ONNX Whisper-family loader (`indicwhisper-base` default) with log-mel frontend; **falls back to canned fixture transcripts when weights absent**. | `sarvam_client.py`, `ml/edge_runner.py` |
| TTS / Translate | Sarvam `bulbul:v2` TTS (8 kHz), `/translate`. | `sarvam_client.py` |

What it predicts: a **risk score 1–3**, primary syndromic cluster, red-flag codes, rationale keys (i18n catalog), and action codes (`act_refer_phc_now`, `act_notify_asha`, ORS/zinc/paracetamol home care…).

## 4. Current Dataset & Format

Two paired JSON files at repo root, **2,251 records each, same `id`s**:

1. **`triage_input_output_clean.json`** — flat strings:
   `{ id, input: "<clinical vignette>", output: "Triage Level: RED (...). Suspected Condition: ... Action Protocol: ..." }`
2. **`triage_protocols_structured.json`** — machine-readable:
   ```
   { id,
     input: { demographics{age,gender,context}, presentation_english, vitals{bp,hr,rr},
              clinical_observations[], formatted_input },
     output: { triage_level: RED|YELLOW|GREEN|BLACK, urgency, suspected_condition,
               action_protocol[], formatted_output } }
   ```

**Label distribution** (ground truth): YELLOW 1,382 (61%) · RED 819 (36%) · GREEN 39 · BLACK 11.
**Top conditions:** General Medical Evaluation 1,298 · Rabies/Category-III Animal Bite 670 · PPH 65 · Pulmonary TB 46 · Asthma 20 · SAM 11 · Pediatric pneumonia 10 · OP poisoning 9 · Severe malaria 9 · Dengue 7 …

Properties / caveats:
- **English-only vignettes** despite the product being Indic-first; no patient-voice phrasing (formal clinician prose).
- Condition taxonomy is much wider than the 5 IMCI clusters (rabies, TB, asthma, malnutrition…), which the engine can only reach via keyword hacks added in `68bf3b1` (e.g., "dog bit"/"pesticide" → `unconscious=True`).
- BLACK (deceased/expectant) maps to SELF_CARE(=1) in `map_ground_truth` — semantically wrong for scoring.
- Some `suspected_condition` values are parsing debris ("and treatment", "Patient Profile:").
- Provenance/licensing of the dataset is undocumented.

## 5. Preprocessing

`benchmark_protocols.py:parse_vitals_and_symptoms()` converts structured JSON → `SymptomPayload`: regex vitals (RR, °C), keyword→boolean flag mapping (with Hindi/Tamil/Bengali transliteration tokens like "bukhar", "dast", "saans"), crude age-band inference, hardcoded fallbacks (`fever_days=3`, `stool_frequency=6`). This adapter is where most signal is lost (see §8).

## 6. Training Pipeline

**None exists.** No training scripts, model registry, requirements beyond FastAPI stack, or experiment tracking. `ml/` contains only the inference/benchmark runner; `--export` shells out to `optimum.exporters.onnx` to convert HF weights.

## 7. Inference Pipeline

- **API path:** `POST /api/v1/triage/evaluate` → `triage_service.evaluate_and_log` → engine → persist `Case` (idempotent by `client_uuid`) → directive + nearest-PHC lookup (Haversine over seeded PHC table).
- **Channel path:** WhatsApp/voice webhook → Twilio signature validation → Sarvam ASR → rule-NER → engine → localized actions + optional TTS voice reply; Telegram/Meta webhooks similar.
- **Offline/edge path:** `triageLocal.ts` in-browser engine; `ml/edge_runner.py` CLI for on-device pipeline with per-stage latency (ingest/stt/ner/imci) + peak RSS reporting.

## 8. Evaluation Pipeline & Measured Results

Runner: `python3 backend/scripts/benchmark_protocols.py` (loads `triage_protocols_structured.json`, maps RED/YELLOW/GREEN→3/2/1, reports exact/safe/under/over-triage + condition-wise breakdown).

**Measured today (this audit):**
| Metric | Value |
|---|---|
| Exact match accuracy | **6.75 %** (152/2,251) |
| Safety concordance (pred ≥ GT) | **8.26 %** |
| **Under-triage rate** | **91.74 %** (2,065 cases) |
| Over-triage rate | 1.51 % |
| Latency | 0.103 ms/case (~9.7 k evals/s) |
| Predicted distribution | Red 86 · Yellow 86 · **Green 2,079** vs GT Red 819 · Yellow 1,382 · Green+Black 50 |

Root causes of under-triage: (a) keyword adapter rarely fires red-flag booleans on formal vignettes; (b) GT skew toward conditions outside IMCI cluster coverage; (c) engine defaults to Green when flags don't fire. The README's "0% under-triage" claim does not match this reproducible result and should be re-based before any submission/judging.

Unit tests (`test_imci_engine.py`, ~35 cases) pass against curated payloads — i.e., **the engine is internally consistent but the end-to-end dataset benchmark diverges sharply**.

## 9. Supported Languages

| Layer | Languages |
|---|---|
| Message catalog (`messages.py:SUPPORTED_LANGUAGES`) | **en, hi, ta, bn** (localized rationale/actions) |
| Sarvam client `LANGUAGE_MAP` | hi, ta, bn, te, kn, ml, mr, gu, pa, en (ASR/TTS/translate capable) |
| Edge/online rule-NER lexicons | en, hi, ta, bn (+ te bite/trauma terms via recent commit) |
| Demo scenarios (`mockSymptoms.ts`) | Tamil (Score 1), Hindi (Score 2), Bengali (Score 3) |
| Benchmark dataset | English only |

Gap: NER lexicon coverage ≪ ASR locale coverage; language auto-detection is rudimentary (defaults to `hi`).

## 10. Where to Integrate External Assets (exact anchors)

### 10.1 Medical / triage datasets (BODHI-S, MIETIC, Multilingual_symptom_triage, indian-rural-triage-data)
- New dir **`data/external/<name>/`** (gitignored raw files + committed adapters/README).
- New module **`backend/scripts/dataset_adapters.py`**: each source gets `load() -> list[TriageCase]` normalizing to one internal schema (`SymptomPayload`-style input + risk label + provenance + license field).
- Reuse the conversion pattern already in `benchmark_protocols.py:parse_vitals_and_symptoms` but move it into the shared adapter layer so API, benchmark and future training share one preprocessing truth.
- BODHI-S additionally feeds **`backend/app/triage/`**: its symptom-node triage levels can validate/extend the ladders in `clusters.py`; its symptom vocabulary can seed `LEXICON`.
- Extend `map_ground_truth` to handle ESI 1–5 (MIETIC) and fix the BLACK mapping.

### 10.2 Multilingual Indian-language datasets (IHQID-WebMD/1mg, IndicMedDialog, Hinglish triage sets)
- NER lexicons: extend **`ml/edge_runner.py:LEXICON` / `DURATION_PATTERNS`** and **`sarvam_client.extract_symptoms_rule_fallback`** term lists from IHQID entity tags (drugs/diseases/treatments × 6 Indic languages). Consider generating a single versioned lexicon file `data/lexicons/*.json` loaded by both Python paths to kill duplication.
- Add translated eval slices of the 2,251 set (ta/te/bn patient-phrased versions) as `data/multilingual/` for cross-lingual consistency benchmarks (same case must yield same risk regardless of language).
- New languages plug into **`backend/app/triage/messages.py:LANG_TEXT/ACTIONS`** (catalog design already supports this without touching engine logic).

### 10.3 Speech datasets (Kathbath, IndicVoices, Vistaar, DISPLACE-M, GramVaani/MUCS)
- WER harness: new **`ml/eval/asr_bench.py`** driving `edge_runner.load_audio/transcribe` over downloaded test splits (manifest-driven, `data/audio_manifests/*.jsonl`); report per-language WER/CER + stage latency on CPU.
- DISPLACE-M (real ASHA↔patient Hinglish consultations): end-to-end Voice→NER benchmark wired through `normalize_symptoms` + `evaluate`; also the best fine-tuning corpus if ASR adaptation begins.
- GramVaani/MUCS 8 kHz slices to emulate IVRS channel acoustics.
- Frontend counterpart: `src/lib/edge/sttRunner.ts` stays as-is until real weights ship; keep mock fixtures flagged.

### 10.4 Benchmark / evaluation code
- Promote `benchmark_protocols.py` into a package **`backend/scripts/benchmarks/`** with: pluggable dataset loaders (10.1), metric definitions (exact, safety concordance, under-/over-triage, per-language, per-condition, calibration), CI gate (e.g., fail if under-triage > 0 on RED cases), and JSON output to `reports/` for trend tracking (this file's sibling directory).
- Add parity tests asserting `triageLocal.ts` ≡ Python engine on the same generated payload matrix (currently **already drifting**: TS mirror lacks `snake_bite_emergency`/`severe_trauma_burn` from commit `68bf3b1`).
- Fix latent bug found during audit: `extract_symptoms_rule_fallback` sets `headache_severe` (invalid field → `TypeError` when transcript matches pregnant+headache); also hardcodes `breathing_rate_per_min=55`, `stool_frequency_per_day=5`.

## 11. Summary

**What the system does today:** voice/text intake (WhatsApp/IVR/Telegram/PWA) → Sarvam ASR or ONNX edge ASR → rule-based multilingual symptom normalization → deterministic WHO IMCI 5-cluster decision tree → risk 1–3 with localized rationale/actions, ASHA dispatch or nearest-PHC routing, case persistence + supervisor analytics, with an offline-parity frontend engine.

**What the current dataset contains:** 2,251 English clinical vignettes (structured + flat string forms) with RED/YELLOW/GREEN(+BLACK) triage labels, free-text condition names and action protocols — skewed 61% YELLOW / 36% RED, dominated by "General Medical Evaluation" and rabies-bite presentations; no audio, no non-English text, unknown provenance.

**What the current model predicts:** integer risk tier (1/2/3), primary syndromic cluster, red-flag codes, rationale keys, action codes — entirely rule-based; no statistical/learned component.

**Current limitations:** (1) reproducible benchmark contradicts the advertised 0%-under-triage claim (actual 91.7% under-triage via lossy keyword adapter + IMCI-cluster coverage mismatch); (2) English-only evaluation vs Indic-first product; (3) NER lexicons tiny and duplicated across three modules; (4) no training/fine-tuning pipeline at all; (5) TS/Python engine drift after latest commit; (6) label-quality issues (BLACK mapping, debris condition names); (7) ASR falls back to canned fixtures, so "offline latency" numbers are not true ASR numbers.

**Recommended next steps (in order):**
1. Fix the benchmark first: repair `parse_vitals_and_symptoms` recall, remap BLACK, add per-condition coverage rules for rabies/TB/asthma/SAM/poisoning (or split the dataset into in-scope IMCI vs extended-scope subsets and publish both scores).
2. Stand up `backend/scripts/benchmarks/` package + dataset adapters (`data/external/`), integrate BODHI-S symptom graph and the Hinglish/Hindi triage CSVs; add CI gate on RED-case under-triage = 0.
3. Build the ASR WER harness (`ml/eval/asr_bench.py`) against Kathbath/IndicVoices test slices and DISPLACE-M; replace mock-fixture fallback reporting with honest engine labels.
4. Unify lexicons into versioned JSON shared by backend + edge; add IHQID-derived terms for te/kn/ml/mr/gu/pa; add translated multilingual eval slices.
5. Only then consider modeling: distill BODHI-S/MIETIC into an auxiliary ML risk prior behind the deterministic tree (kept auditable), using the now-trustworthy benchmark as the gate.
