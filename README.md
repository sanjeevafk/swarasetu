# SwaraSetu

> "Your voice, your village, your first doctor."

SwaraSetu is an offline-first, voice-native triage assistant engineered to bridge India's last-mile healthcare gap. It empowers patients and community health workers (CHWs) in rural and semi-urban settings to report symptoms in native Indic languages—via voice or text—and receive an evidence-based clinical triage outcome.

The platform pairs a language-first architecture powered by Sarvam AI's Indic stack (supporting 22+ languages) with a deterministic decision tree adapting the WHO Integrated Management of Childhood Illness (IMCI) protocol for India's National Health Mission (NHM) context. SwaraSetu operates across WhatsApp, IVRS, USSD, and as an offline-capable Progressive Web App (PWA) on CHW tablets, requiring zero smartphone app installation and no English literacy.

---

## 1. Problem Space

India's healthcare infrastructure faces severe structural access disparities and language barriers:

- **Resource Scarcity**: India averages 0.7 doctors per 1,000 people, with 80% concentrated in urban centers serving only 31% of the population. Rural patients face median travel times of 40–60 minutes to reach a Primary Health Centre (PHC).
- **Language and Literacy**: Official health systems primarily operate in English and Hindi. With rural female literacy at ~67% (and under 50% in several regions), text-only tools introduce critical communication barriers.
- **Connectivity Constraints**: 4G penetration in rural areas remains near 45%. Clinical tools must function reliably over low-bandwidth connections, USSD networks (2G), and fully offline modalities on CHW tablets.

---

## 2. Core Capabilities

SwaraSetu extracts structured clinical entities from free-form input and deterministically maps them to actionable care outcomes:

- **Voice and Text Intake**: Native speech and text processing across Indic languages and regional dialects.
- **Language Auto-Detection**: Real-time dialect identification powered by Sarvam Language ID.
- **Symptom Normalization (NER)**: Translates colloquial descriptions into standardized medical entities (symptoms, duration, severity, red flags).
- **IMCI Triage Engine**: Python-led deterministic logic evaluating WHO IMCI rules to assign a clinical risk score (1–3).
- **Localized Voice Synthesis**: Returns triage outcomes and self-care advice as localized speech (Sarvam TTS) to overcome literacy barriers.
- **Geospatial Auto-Routing**: Resolves nearest state-operated PHCs with contact details via NHM/ABDM registry data for emergency cases (Score 3).
- **Automated CHW Dispatch**: Triggers asynchronous SMS/WhatsApp follow-up notifications to assigned local ASHA workers for moderate-risk cases (Score 2).
- **Offline PWA Architecture**: Operates fully offline on CHW tablets using IndexedDB and Service Workers, syncing queued records automatically upon network reconnection.

---

## 3. System Architecture

The platform utilizes a decoupled microservices architecture designed for resilience and low-latency execution across heterogeneous environments.

```
                      +---------------------------------------+
                      |   Patient Intake Channels             |
                      |   (WhatsApp / IVRS / USSD / PWA)      |
                      +-------------------+-------------------+
                                          |
                                          v
                      +-------------------+-------------------+
                      |       Sarvam AI Cloud Pipeline        |
                      |   ASR  ->  LangID  ->  NER  ->  TTS   |
                      +-------------------+-------------------+
                                          |
                                          v
                      +-------------------+-------------------+
                      |      Deterministic IMCI Engine        |
                      |  (Risk Scoring & Protocol Routing)    |
                      +---------+-------------------+---------+
                                |                   |
               +----------------+       +-----------+----------------+
               |                        |                            |
               v                        v                            v
    [ Score 1: Self-Care ]     [ Score 2: ASHA Dispatch ]    [ Score 3: PHC Referral ]
    Localized Audio Guidance   Async SMS / WhatsApp Alert    ABDM Facility & Route GPS
```

### Technical Stack

- **Frontend & Mobile**: React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui. PWA enabled with IndexedDB/SQLite for offline triage.
- **Edge Voice Engine**: 4-bit Quantized `ai4bharat/indic-seamless` (ONNX Runtime / ExecuTorch) for on-device STT across 14 Indic languages on tablet hardware.
- **Backend API**: Python 3.11 with FastAPI, PostgreSQL 15 for data persistence, Redis for session state (5-min multi-turn TTL), and Celery for async dispatch.
- **Channels & APIs**: Twilio/Gupshup for messaging, ABDM Health Facility Registry API, and OpenStreetMap/Leaflet for geospatial facility routing.

### 3-Tier Deployment Model

1. **Tier 1 (Online Patients)**: Cloud Sarvam AI (ASR, NER, TTS) over WhatsApp/IVRS for fast, code-mixed Hinglish and dialect processing with zero app installation.
2. **Tier 2 (Offline CHW Tablets)**: On-device quantized `indic-seamless` STT + local IMCI execution on 4GB+ RAM Android devices.
3. **Tier 3 (Legacy Hardware Fallback)**: Touch-to-Hear visual form interface + pre-cached audio prompts + local IMCI logic for 2GB RAM devices.

---

## 4. Interaction Lifecycle

1. **Intake Activation**: Patient or worker initiates contact via WhatsApp, IVRS call, USSD prompt, or tablet PWA.
2. **Entity Extraction**: Audio is transcribed and processed through NER into a structured symptom payload (`{symptom, duration, severity, red_flags}`).
3. **Clarification Loop**: If required entities are missing or ambiguous, up to two targeted follow-up questions are generated in the user's dialect.
4. **IMCI Protocol Execution**:
   - **Score 1 (Self-Care)**: Localized guidance for home care and monitoring.
   - **Score 2 (Evaluation Needed)**: Dispatches an automated parallel SMS alert to the local ASHA worker for 24-hour follow-up.
   - **Score 3 (Immediate Emergency)**: Computes distance to the nearest operational PHC and issues contact details and directions.
5. **Response Delivery**: Outputs are translated, synthesized into localized speech, and transmitted over the active channel.
6. **Audit & Analytics**: De-identified interaction telemetry is recorded asynchronously to feed supervisor analytics dashboards.

---

## 5. Documentation Directory

Detailed technical and architectural specifications are maintained in the [`docs/`](./docs) directory:

- [Dual-Channel Architecture](./docs/HOW_SWARASETU_WORKS.md) — Online WhatsApp vs. offline tablet operation.
- [Geospatial Facility Routing & ABDM Registry Guide](./docs/SWARASETU_GEOSPATIAL_FACILITY_ROUTING_GUIDE.md) — Haversine routing, ABDM schema, and offline GPS integration.
- [System Architecture & 3-Tier Deployment](./docs/SWARASETU_PRODUCT_ARCHITECTURE_SIH2026.md) — Multi-tier cloud, edge, and fallback technical architecture.
- [SIH 2026 Comprehensive Evaluation Guide](./docs/SWARASETU_SIH_COMPREHENSIVE_GUIDE.md) — Problem statement alignment, clinical defense, and moats.
- [Clinical Evaluation & Benchmarks](./docs/EVALUATION.md) — System evaluation methodologies and safety performance metrics.
- [Benchmark Dataset Catalog](./docs/BENCHMARK_DATASETS.md) — Curated open datasets for triage, ASR, NER, and epidemiological priors.
- [Hindi & Hinglish Triage Benchmark](./docs/BENCHMARK_HINDI_HINGLISH.md) — Evaluation results on code-mixed Hinglish clinical queries.
- [Touch-to-Hear Accessibility Panel](./docs/TOUCH_TO_HEAR.md) — Visual-audio fallback interface for low-spec hardware.

---

## 6. Benchmarks & Reproducibility

> **Note:** Research prototype for engineering evaluation. Metrics below represent benchmark performance on internal structured cases and public physician-labeled vignette datasets.

### Measured Triage Performance (Held-out Benchmark, 2,251 cases)

| Metric | Baseline (Deterministic IMCI) | Improved (TF-IDF + LogReg v1) |
|---|---|---|
| Accuracy | 6.75% | 29.41% |
| Macro F1 | 0.077 | 0.237 |
| High-Risk Recall | 6.50% | 15.00% |
| High-to-Low Errors | 732 | 386 |

Detailed analysis and artifacts: [`reports/SwaraSetu_Benchmark_Report.pdf`](reports/SwaraSetu_Benchmark_Report.pdf), [`reports/repository_audit.md`](reports/repository_audit.md), and dataset policies in [`data/dataset_registry.yaml`](data/dataset_registry.yaml).

### Reproducing Benchmarks

```bash
# 1. Install dependencies
python3 -m pip install --user pyyaml pandas scikit-learn sqlalchemy httpx "pydantic>=2" reportlab pypdf

# 2. Run baseline evaluation
python3 backend/scripts/benchmark_protocols.py
python3 backend/scripts/eval_baseline.py

# 3. Train policy-gated model and evaluate
python3 backend/scripts/train_improved.py
python3 backend/scripts/eval_improved.py

# 4. Generate comparison and multilingual reports
python3 backend/scripts/compare_before_after.py
python3 backend/scripts/eval_multilingual.py
python3 backend/scripts/run_external_validation.py

# 5. Build PDF report
python3 backend/scripts/build_report_pdf.py

# 6. Run backend test suite
cd backend && python3 -m pytest tests -q
```
