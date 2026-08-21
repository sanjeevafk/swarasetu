# SwaraSetu — Product Requirements Document

## 1. Executive Summary

SymptomBridge is an offline-capable, voice-first triage assistant designed for India's last-mile healthcare gap. It enables patients and community health workers (CHWs) in rural and semi-urban settings to report symptoms in their native language — by voice or text — and receive an evidence-based triage outcome: self-care guidance, a CHW follow-up alert, or an urgent referral with the nearest Primary Health Centre (PHC) location.

The core differentiator is language-first design powered by Sarvam AI's Indic language stack (22+ Indian languages), combined with the WHO IMCI decision protocol adapted for India's NHM context. It requires no smartphone app, no English literacy, and no persistent internet connection — operating across WhatsApp, IVRS, USSD, and an offline-capable PWA on CHW tablets.

---

## 2. Problem Definition — Indian Context

### 2.1 Access Gaps

- India has 0.7 doctors per 1,000 people (WHO recommends 1.0), with 80% of doctors concentrated in urban areas serving only 31% of the population.
- Rural patients face a median travel time of 40–60 minutes to reach a PHC, rising to 3–4 hours in tribal and hilly districts.
- The ASHA/ANM network comprises ~1 million community health workers — highly trusted but undertrained in clinical triage, using paper registers with no decision support and no feedback loop to supervisors.
- Out-of-pocket expenditure accounts for 62% of total health spending in India, driving delayed care-seeking. Patients wait until symptoms are severe, converting preventable cases into emergencies.

### 2.2 Language Barriers

- India has 22 officially recognised languages and over 780 dialects. National health systems (ABDM, NHM portals) operate primarily in English and Hindi.
- Symptom self-reporting in a non-native language introduces critical semantic errors. Terms like "dizziness", "shortness of breath", or "burning urine" translate inconsistently across tools.
- Voice-first interaction is not optional: NFHS-5 reports female literacy in rural India at ~67%, dropping below 50% in Bihar and Rajasthan.
- All major symptom checkers (Ada, WebMD, 1mg) operate exclusively in English.

### 2.3 Healthcare Infrastructure Constraints

- 4G penetration in rural India is ~45% with intermittent availability. USSD (2G) remains the only universal channel.
- Feature phone ownership exceeds smartphone ownership in rural India. Solutions requiring app installs or data plans exclude the target population.
- ASHA workers have been issued smartphones in some states under NHM, but connectivity is not guaranteed — offline-first design is mandatory.
- India's National Health Mission maintains a public PHC/CHC locator API and district-level health facility data available for integration without licensing.

---

## 3. Solution

### 3.1 Core Features

| Feature                 | Description                                                   | Sarvam Role                | Priority |
| ----------------------- | ------------------------------------------------------------- | -------------------------- | -------- |
| Voice symptom intake    | Patient speaks symptoms in any supported Indic language       | Sarvam STT (Indic ASR)     | P0 — MVP |
| Text symptom intake     | Typed input via WhatsApp or USSD                              | Sarvam NER + Translate     | P0 — MVP |
| Language auto-detection | Identifies input language without user selection              | Sarvam Language ID         | P0 — MVP |
| Symptom normalisation   | Extracts structured symptom entities from free-form input     | Sarvam NER pipeline        | P0 — MVP |
| IMCI triage engine      | Applies WHO IMCI decision tree, assigns risk score 1–3        | Internal Python logic      | P0 — MVP |
| Localised response      | Delivers outcome in patient's language via voice or text      | Sarvam TTS + Translate     | P0 — MVP |
| PHC locator             | Returns nearest open PHC for urgent cases                     | NHM Open API + geocoding   | P0 — MVP |
| CHW alert dispatch      | Notifies field worker by SMS/WhatsApp for medium-risk cases   | Twilio or Gupshup          | P0 — MVP |
| Offline PWA mode        | CHW completes triage without internet, syncs when online      | Service Worker + IndexedDB | P1       |
| Case dashboard          | Supervisor view of triage volume, symptom trends, escalations | Metabase + PostgreSQL      | P1       |
| ABDM integration        | Link case to patient ABHA ID for health record continuity     | ABDM Sandbox API           | P2       |

### 3.2 User Flow

**Step 1 — Entry**
Patient initiates contact via WhatsApp message/voice note, toll-free IVRS call, USSD code on a feature phone, or CHW-supervised PWA on tablet. No registration, no login, no app install required.

**Step 2 — Language and symptom capture**
Sarvam's language identification model detects the input language automatically. If voice, Sarvam's Indic ASR transcribes speech to text. The transcribed or typed text is passed through Sarvam's NER pipeline to extract a structured symptom object: `{symptom, duration, severity, associated_signs, patient_age_group}`.

**Step 3 — Clarification loop**
If the triage engine cannot resolve a risk score, it triggers a clarification prompt in the patient's language via Sarvam's translation model. At most 2 follow-up questions are asked to avoid drop-off.

**Step 4 — Triage decision**
The structured symptom object is passed to the IMCI decision tree engine, which returns:

- A risk score: 1 (self-care), 2 (CHW follow-up within 24h), 3 (urgent referral now)
- A plain-language outcome rationale
- For Score 3: nearest PHC coordinates and opening hours

**Step 5 — Response delivery**
The outcome is composed in the patient's language using Sarvam's translation model. For voice channels, Sarvam TTS generates audio. For Score 2 cases, a parallel alert is dispatched to the assigned CHW via SMS.

**Step 6 — Logging**
Every interaction is de-identified and written to PostgreSQL. Aggregated data surfaces to the supervisor dashboard showing triage volume, symptom distribution, escalation rates, and response time by district.

### 3.3 Sarvam AI Integration Points

| Sarvam Capability            | SymptomBridge Use                                                               |
| ---------------------------- | ------------------------------------------------------------------------------- |
| Indic ASR (Speech-to-Text)   | Transcribes patient voice input in 10+ Indian languages                         |
| Language identification      | Auto-detects input language — no selection required                             |
| NER / information extraction | Extracts symptom entities, durations, severity indicators from free-form input  |
| Translation (Indic ↔ Indic)  | Translates clarification questions and triage responses into patient's language |
| TTS (Text-to-Speech)         | Synthesises voice responses for low-literacy patients and IVRS delivery         |
| Sarvam-2B / Bulbul           | Fallback intent classification when NER confidence is below threshold           |

---

## 4. Target Users

### 4.1 Primary Users — Patients

| Segment                    | Profile                                                                                    |
| -------------------------- | ------------------------------------------------------------------------------------------ |
| Rural adult patients       | Age 18–60, speaks local Indic language, limited English, feature phone or basic smartphone |
| Mothers with sick children | Seeking triage for child illness; paediatric IMCI protocol applies; voice-first critical   |
| Pregnant women             | High-risk segment; maternal symptoms mapped to obstetric risk flags                        |
| Elderly patients           | Low digital literacy; voice channel preferred; simple slow TTS output required             |

### 4.2 Secondary Users

| Role                        | How They Use SymptomBridge                                                             |
| --------------------------- | -------------------------------------------------------------------------------------- |
| ASHA / ANM workers          | Conduct supervised triage on CHW tablet; receive WhatsApp alerts for medium-risk cases |
| PHC / CHC medical officers  | Receive aggregated referral data; view incoming high-risk cases before patient arrives |
| District health supervisors | Monitor triage volume, symptom trends, and CHW alert response times via dashboard      |
| NHM programme managers      | Use district-level data to identify disease burden patterns and deploy CHW resources   |

---

## 5. UN SDG Mapping

| SDG    | Goal                       | Specific Target                     | SymptomBridge Contribution                                                                  |
| ------ | -------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------- |
| SDG 3  | Good Health and Well-being | 3.8 — Universal health coverage     | Extends structured triage to populations with no physical access to a clinician             |
| SDG 3  | Good Health and Well-being | 3.c — Strengthen health workforce   | Augments ASHA/ANM workers with decision support without requiring medical degrees           |
| SDG 4  | Quality Education          | 4.6 — Literacy and numeracy for all | Voice-first interaction removes the education barrier from health access entirely           |
| SDG 10 | Reduced Inequalities       | 10.2 — Promote social inclusion     | Breaks urban-rural health access gap and language-based exclusion from digital health tools |
| SDG 17 | Partnerships for the Goals | 17.8 — Technology for development   | Uses open government data and open protocols with zero proprietary lock-in                  |

---

## 6. MVP Design — Hackathon Scope (24–48 Hours)

### 6.1 Essential Features (P0 — Must Ship)

- WhatsApp channel integration via Twilio or Gupshup sandbox
- Sarvam STT integration — transcribes voice notes for 3+ languages (Hindi, Tamil, Bengali)
- Sarvam language detection — auto-identifies language from input
- Symptom NER — Sarvam NER or Bulbul model extracts symptom entities into structured JSON
- IMCI triage engine — deterministic Python decision tree covering fever, respiratory distress, diarrhoea, and maternal danger signs
- Triage outcome response — composed in patient's language via Sarvam Translate + TTS
- PHC locator — for Score 3 cases, returns nearest PHC name, distance, and contact number
- Case logging to PostgreSQL — de-identified, stores symptom object + outcome + timestamp + district

### 6.2 Optional Features (P1 — If Time Permits)

- Metabase dashboard — case volume and symptom breakdown chart
- Offline PWA demo — CHW tablet mode with service worker caching of IMCI logic
- CHW SMS alert — Twilio SMS dispatch for medium-risk cases
- USSD stub — simulated USSD flow for feature phone demo
- Clarification loop — up to 2 follow-up questions when NER confidence is low

### 6.3 Explicitly Out of Scope

- ABDM / ABHA integration — deferred to Phase 2
- All 22 Indian languages — demo targets 3–4; architecture supports expansion
- Custom model fine-tuning — use Sarvam APIs as-is
- Production security hardening — DPDPA compliance deferred
- Real-world CHW onboarding flow — demo uses pre-seeded test accounts

### 6.4 Demo Script (3-Minute Presentation)

| Time | What the Judge Sees                                                                                                              |
| ---- | -------------------------------------------------------------------------------------------------------------------------------- |
| 0:00 | Map of India showing urban-rural doctor density gap. Opening line: "800M Indians have no reliable path to clinical triage."      |
| 0:30 | WhatsApp voice note in Tamil — child with fever + cough. Show Sarvam STT transcript → extracted symptom JSON → Score 2 assigned. |
| 1:30 | WhatsApp response in Tamil text + TTS audio played. Second phone receives CHW SMS alert.                                         |
| 2:00 | Pre-recorded voice note with severe respiratory distress. Score 3 assigned. Response shows nearest PHC address and phone number. |
| 2:30 | Metabase dashboard — 3 cases logged, symptom breakdown chart, district filter.                                                   |
| 2:50 | Closing slide: SDGs 3, 10, 4 mapped. Tech stack. Sarvam as the unique enabler for Indic language coverage.                       |

---

## 7. Tech Stack

### 7.1 Frontend

- React PWA — offline-capable via service workers and IndexedDB, runs on CHW tablets without internet
- Tailwind CSS — responsive layout, minimal bundle size
- react-leaflet — PHC location map using OpenStreetMap tiles
- Metabase — supervisor analytics dashboard embedded via iframe

### 7.2 Backend

- Python 3.11 + FastAPI — async API server with auto-generated OpenAPI docs
- PostgreSQL 15 — case storage, CHW assignments, PHC seed data
- Redis — session cache for multi-turn conversations (5-minute TTL)
- Celery + Redis — background task queue for SMS dispatch and async logging
- Docker Compose — single-command local dev environment

### 7.3 Sarvam AI Integration

- Sarvam ASR API — `POST /transcribe` with audio blob, returns transcript + detected language
- Sarvam Translate API — `POST /translate` for question and response localisation
- Sarvam TTS API — `POST /synthesise` for audio response generation
- Sarvam NER API — `POST /extract` for symptom entity extraction from transcript
- Sarvam-2B / Bulbul — intent classification fallback when NER confidence < 0.6

### 7.4 Channel Integrations

- Twilio WhatsApp sandbox — incoming message webhook for text and media/audio
- Gupshup — alternative India-specific WhatsApp BSP with stronger Hindi support
- Twilio Programmable SMS — CHW alert dispatch

### 7.5 External APIs and Datasets

- NHM Health Facility Registry — public PHC/CHC dataset with coordinates, contacts, hours (data.gov.in)
- WHO IMCI Pocket Guide — open protocol implemented as deterministic Python decision tree
- OpenStreetMap + Nominatim — reverse geocoding for PHC distance calculation
- ABDM Sandbox — Phase 2 ABHA linkage (Ayushman Bharat Digital Mission)

### 7.6 Infrastructure

- Render.com or Railway.app — free-tier deployment for hackathon demo
- Supabase — managed PostgreSQL with real-time subscriptions
- Cloudflare R2 — audio file storage for voice notes and TTS output

---

## 8. Differentiation

| Dimension             | Why SymptomBridge Is Different                                                                                                             |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Language              | 22+ Indian languages via Sarvam STT/TTS with auto-detection. No existing symptom checker offers this coverage.                             |
| Literacy independence | Voice-first across all channels. A completely illiterate user completes the full triage flow without typing a single character.            |
| Protocol basis        | Triage logic is grounded in WHO IMCI — a validated clinical protocol — not a general-purpose LLM. Outcomes are reproducible and auditable. |
| Channel diversity     | WhatsApp + IVRS + USSD + PWA. USSD reaches 300M+ feature phone users that all app-based solutions miss.                                    |
| CHW integration       | Medium-risk cases automatically alert the assigned ASHA worker — a human-in-the-loop safety net for ambiguous presentations.               |
| Zero friction entry   | No registration, no login, no app install, no English. One message in, one response out.                                                   |
| Open data foundation  | Built on NHM open data, WHO open protocols, and Sarvam's India-specific models. No proprietary lock-in.                                    |

---

## 9. Risks and Mitigations

| Risk                                                         | Severity | Likelihood | Mitigation                                                                                                              |
| ------------------------------------------------------------ | -------- | ---------- | ----------------------------------------------------------------------------------------------------------------------- |
| Sarvam NER misses a critical symptom, causing under-triage   | High     | Medium     | Apply conservative bias: NER confidence < 0.7 defaults upward to Score 2; < 0.5 routes to CHW review                    |
| Patient provides vague or idiomatic symptom descriptions     | Medium   | High       | Allow up to 2 clarification questions; append safety prompt to all Score 1 responses directing to helpline 104          |
| PHC locator data is stale or incorrect                       | Medium   | Medium     | Seed from NHM HFDR (updated quarterly); always include national health helpline 104 as fallback                         |
| WhatsApp / Twilio sandbox rate limits during demo            | Low      | High       | Pre-record demo flows as fallback; maintain local simulation mode replaying real conversations from DB                  |
| Regulatory concern: classified as medical device under CDSCO | High     | Low        | Position as triage navigation aid, not a diagnostic tool; include disclaimer in every response; no drug recommendations |

---

## 10. IMCI Condition Clusters — MVP Scope

The following four clusters cover the highest-burden acute presentations in rural India and are sufficient for a complete hackathon demo:

- **Fever cluster** — duration, temperature, neck stiffness, rash, convulsions, age → malaria risk, dengue risk, meningitis flag, febrile convulsion
- **Respiratory cluster** — cough duration, breathing rate, chest indrawing, stridor, SpO2 proxy indicators → URI vs pneumonia vs severe pneumonia
- **Diarrhoea cluster** — frequency, blood in stool, sunken eyes, skin turgor, recent feeds → no dehydration vs some vs severe dehydration
- **Maternal danger signs cluster** — headache + visual disturbance, reduced foetal movement, vaginal bleeding, convulsion → pre-eclampsia flag, obstetric emergency

---

## 11. Supported Languages — MVP Launch

The following three languages are targeted for the hackathon demo, selected by rural population coverage and Sarvam model maturity:

- **Hindi (hi-IN)** — ~530 million speakers across UP, Bihar, MP, Rajasthan
- **Tamil (ta-IN)** — ~75 million speakers in Tamil Nadu
- **Bengali (bn-IN)** — ~100 million speakers in West Bengal, Assam, Jharkhand

Architecture supports expansion to Telugu, Kannada, Marathi, Gujarati, Odia, Punjabi, and Malayalam without code changes — language coverage is a Sarvam API configuration parameter, not a model training task.

---

## 12. References

- WHO IMCI Pocket Guide — https://www.who.int/publications/i/item/9789241506823
- NHM Health Facility Registry — https://data.gov.in
- NFHS-5 National Family Health Survey — https://rchiips.org/nfhs/
- Sarvam AI APIs — https://sarvam.ai
- ABDM Sandbox — https://sandbox.abdm.gov.in
- WHO World Health Statistics — https://www.who.int/data/gho
