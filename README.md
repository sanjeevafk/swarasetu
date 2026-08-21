# SwaraSetu (स्वर सेतु)

> "Your voice, your village, your first doctor."

SwaraSetu is an offline-first, voice-native clinical triage and rural emergency response platform designed to bridge India's last-mile healthcare gap. It empowers patients and frontline Community Health Workers (ASHA / ANM) to report medical symptoms in native Indic languages—via voice notes or visual touch interfaces—and receive immediate, evidence-based clinical triage, emergency response pre-alerts, and localized care guidance.

Powered by **Sarvam AI's Indic language stack** (supporting 22+ Indian languages) and a **100% deterministic WHO IMCI (Integrated Management of Childhood Illness) decision tree**, SwaraSetu operates across **Telegram (`@swarasetubot`)**, **Meta WhatsApp Cloud API**, **Twilio SMS/WhatsApp**, and as a fully offline **Progressive Web App (PWA)** on CHW tablets.

---

## 1. The Problem Space & Clinical Context

Rural healthcare across India faces structural access disparities, language barriers, and critical resource constraints:

- **Severe Doctor Shortages**: India has ~0.7 doctors per 1,000 rural citizens, with 80% of healthcare resources concentrated in urban hubs serving 31% of the population. Rural patients face median travel times of 40–60 minutes to reach a Primary Health Centre (PHC).
- **Language & Literacy Barriers**: Systems operating in English or rigid Hindi exclude non-literate populations. Unassisted text input often misinterprets colloquial Indic symptom descriptions (e.g. Tamil *"nenju vali"*, Hindi *"saans phulna"*, Hinglish/Tanglish slang).
- **Network & Hardware Reality**: Over 55% of rural areas experience frequent low-bandwidth or zero-connectivity states ("media-dark" zones). Solutions must work online via messaging bots and 100% offline on low-cost ASHA tablets.

---

## 2. Core Capabilities & Multi-Tier Architecture

SwaraSetu uses a 3-tier hybrid architecture ensuring seamless operation from high-speed cloud channels to disconnected 2GB RAM field tablets.

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                 Patient / CHW Ingestion                 │
                  └────────────────────────────┬────────────────────────────┘
                                               │
               ┌───────────────────────────────┴───────────────────────────────┐
               ▼                                                               ▼
  ┌─────────────────────────┐                                     ┌─────────────────────────┐
  │  Online Messaging Stack │                                     │  Offline CHW Edge Stack │
  │ Telegram / WhatsApp API │                                     │ Tablet PWA (IndexedDB)  │
  └────────────┬────────────┘                                     └────────────┬────────────┘
               │                                                               │
               ▼                                                               ▼
  ┌─────────────────────────┐                                     ┌─────────────────────────┐
  │ Sarvam AI Cloud Engine  │                                     │ Client-Side JS IMCI     │
  │ (ASR, N-Gram NER, TTS)  │                                     │ + Touch-to-Hear Panel   │
  └────────────┬────────────┘                                     └────────────┬────────────┘
               │                                                               │
               └───────────────────────────────┬───────────────────────────────┘
                                               │
                                               ▼
                              ┌──────────────────────────────────┐
                              │ Deterministic WHO IMCI Engine    │
                              │ (Zero-Hallucination Risk Scores) │
                              └────────────────┬─────────────────┘
                                               │
            ┌──────────────────────────────────┼──────────────────────────────────┐
            ▼                                  ▼                                  ▼
 🟢 Risk Score 1: Self-Care      🟡 Risk Score 2: ASHA Dispatch     🔴 Risk Score 3: Emergency
 • Native voice guidance         • Automated SMS / WhatsApp alert   • 108 CAD ambulance dispatch
 • Localized home remedies       • 24h CHW evaluation task          • Hospital/PHC pre-alerts
                                                                    • Spoken first-aid guidance
```

### Key Technical Capabilities

1. **Deterministic WHO IMCI Triage**: Risk scores (1 Self-Care, 2 ASHA Dispatch, 3 Emergency) are computed strictly by deterministic rule trees across *Fever, Respiratory, Diarrhoea, Maternal, and Acute Envenomation/Trauma* protocols. Generative LLMs are **never** permitted to calculate clinical risk scores or fabricate numerical vitals.
2. **Hybrid N-Gram Statistical Prior**: Combines multi-scale n-gram statistical classification with rule lexicons to handle code-mixed Indic inputs (Tanglish, Hinglish, Banglish), boosting triage concordance from 29.2% to **95.15%** on complex colloquial datasets.
3. **4-Pillar Rural Emergency Response System**:
   - **Ambulance Dispatch**: Automated 108 Computer-Aided Dispatch (CAD) ticket creation.
   - **Hospital Pre-Alerts**: Proactive readiness alerts sent to nearest PHC for required anti-venom, ECG, or resuscitation setup.
   - **Native Spoken First Aid**: Audio and visual step-by-step guidance for snake bites, trauma, burns, and eclampsia.
   - **Spatial GPS Navigation**: Haversine facility routing to nearest 24/7 PHC.
4. **Touch-to-Hear CHW Panel**: Visual icon interface on field tablets enabling zero-literacy ASHA workers to tap symptom icons, hear localized audio prompts, and generate structured JSON payloads with **100% engine parity** offline.
5. **Omnichannel Messaging Integration**: Full webhook implementations for **Telegram ([`@swarasetubot`](https://t.me/swarasetubot))**, **Meta WhatsApp Cloud API**, and **Twilio SMS/WhatsApp** featuring cryptographic signature validation (HMAC-SHA256 & secret tokens).

---

## 3. Technology Stack & Component Structure

### Backend Engine (`backend/`)
- **Framework**: Python 3.11 with FastAPI (async ASGI performance)
- **Database & ORM**: SQLite (default local) / PostgreSQL with SQLAlchemy ORM
- **Clinical Engine**: Pure Python WHO IMCI deterministic protocol decision trees (`backend/app/triage/`)
- **Voice Stack**: Sarvam AI Cloud SDK (`sarvam_client.py`) supporting `saarika:v2.5` ASR, dialect translation, and `bulbul:v2` TTS
- **Emergency Dispatch**: CAD integration, PHC spatial indexing (`backend/app/services/emergency_service.py`), and localized first-aid protocols (`backend/app/triage/first_aid.py`)
- **Testing**: 67 unit and integration tests covering clinical safety, authentication, and emergency workflows (`pytest`)

### Frontend & Tablet PWA (`src/`)
- **Core Framework**: React 18, Vite, TypeScript, Tailwind CSS v3.4, shadcn/ui
- **Offline Edge Mode**: Service Worker caching, client-side IMCI mirror (`src/lib/triageLocal.ts`), IndexedDB outbox queue with auto-retry
- **Components**:
  - `DemoChat.tsx`: Interactive voice/text patient triage interface
  - `TouchToHearPanel.tsx`: Touch-to-Hear visual icon panel for ASHA field tablets
  - `CHWTablet.tsx`: Offline CHW tablet view with local triage & outbox status
  - `SupervisorDashboard.tsx`: Epidemiological analytics tracking endemic disease trends and risk distributions
  - `PHCMap.tsx`: Live Leaflet spatial locator map for primary healthcare centers

### Machine Learning & Benchmarking (`ml/`)
- **N-Gram Prior Engine**: Multi-scale n-gram prior for code-mixed Indic triage (`ml/train_tanglish_prior.py`)
- **ONNX Edge Runner**: On-device ONNX Runtime latency benchmarking (`ml/edge_runner.py`)
- **Benchmarking Suite**: Automated evaluation scripts across multi-thousand case datasets (`bench_tanglish.py`, `bench_hindi_only.py`, `bench_hindi_hinglish.py`)

---

## 4. Multilingual Clinical Evaluation Summary

SwaraSetu has been evaluated across **29,188 multilingual patient presentations**:

| Corpus / Language | Dataset Source | Cases | Accuracy / Concordance | Critical ER Recall | Inference Latency |
|---|---|---|---|---|---|
| **Tanglish (Tamil-English)** | `Adhik6495/tanglish-medical-triage-data` | 7,985 | **95.15%** Mapped Acc | **99.58%** | **0.049 ms** |
| **Pure Hindi (Devanagari)** | `Tulsiandhare/Multilingual_medical_symptom_triage` | 4,532 | **70.70%** Safety Conc. | Verified Lexicon | **0.818 ms** |
| **Hinglish (Hindi-English)** | `Tulsiandhare/Multilingual_medical_symptom_triage` | 4,821 | **73.80%** Safety Conc. | Code-Mixed Regex | **0.320 ms** |
| **Bengali & Banglish** | `Irtisum/bengali-medical-triage-conversations` | 2,724 | **65.97%** Safety Conc. | Bengali Lexicon | **0.056 ms** |
| **WHO IMCI Danger Gate** | Canonical Golden Scenarios | 31 | **100.00%** (31/31) | **100.00%** (13/13) | **0.025 ms** |
| **Touch-to-Hear Tablet UI** | Structured Visual Icon Input | End-to-End | **100.00%** Engine Parity | **100.00%** | **< 1.0 ms** |

---

## 5. Quickstart & Local Setup

### Environment Configuration
Copy the template environment configuration:
```bash
cp .env.example .env
```
Fill in required credentials in `.env`:
```env
DATABASE_URL=sqlite:///./swarasetu.db
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Sarvam AI API Credentials
SARVAM_API_KEY=your_sarvam_api_key_here

# Telegram Bot Token (Optional for Telegram Webhook)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

### Running Backend API & Unit Tests
```bash
# Set up Python virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Run full backend test suite (67 tests)
pytest backend/tests/

# Start FastAPI dev server
uvicorn backend.app.main:app --reload --port 8000
```

### Running Frontend Application
```bash
# Install node dependencies
npm install

# Build & verify TypeScript
npm run build

# Start Vite dev server
npm run dev
```

---

## 6. Technical Documentation Directory (`docs/`)

Explore in-depth architectural and benchmark guides in the [`docs/`](./docs) directory:

- 📱 **[Dual-Channel Architecture (Online WhatsApp vs. Offline Tablet)](./docs/HOW_SWARASETU_WORKS.md)**: Breakdown explaining online cloud bots vs. 100% offline tablet PWA execution.
- 🗺️ **[Geospatial Facility Routing & ABDM Registry Guide](./docs/SWARASETU_GEOSPATIAL_FACILITY_ROUTING_GUIDE.md)**: Hardware GPS routing, Haversine spatial indexing, and ABDM Health Facility Registry integration.
- 🏗️ **[System Architecture & 3-Tier Deployment](./docs/SWARASETU_PRODUCT_ARCHITECTURE.md)**: In-depth technical breakdown of Cloud Sarvam, on-device quantized Indic-Seamless, and Touch-to-Hear 2GB tablet fallback tiers.
- 🏆 **[Comprehensive Evaluation Guide](./docs/SWARASETU_COMPREHENSIVE_GUIDE.md)**: Problem statement alignment, clinical safety defense, technical Q&A responses, and competitive moats.
- 📊 **[Clinical Evaluation & Benchmarks](./docs/EVALUATION.md)**: Detailed benchmark reports, statistical n-gram accuracy analysis, and 0% under-triage clinical safety matrices.

---

## License

Distributed under the **Apache License 2.0**. See [`LICENSE`](./LICENSE) for details.
