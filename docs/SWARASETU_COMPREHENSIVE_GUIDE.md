# SwaraSetu: Comprehensive Strategic, Technical & Presentation Guide

---

## 1. Terms & Concepts Glossary

### CHW (Community Health Worker)
* **In Simple Terms:** Frontline village healthcare workers in India, primarily **ASHA workers** (Accredited Social Health Activists) and **ANMs** (Auxiliary Nurse Midwives).
* **Role:** They visit homes in rural areas to provide basic healthcare guidance, track pregnancies, and check on sick children. Because they are not medical doctors, they rely on decision-support tools to identify high-risk patients.
* **In SwaraSetu:** SwaraSetu provides ASHA workers with an offline-first digital PWA tablet app that guides symptom assessment step-by-step in remote areas with zero internet connectivity.

### NER (Named Entity Recognition)
* **In Simple Terms:** An NLP/AI technique that extracts structured parameters ("important facts") from unstructured text or speech.
* **Example:**
  * **Input (Patient Speech):** *"My 3-year-old child has had a high fever and cough for two days."*
  * **Extracted Entities:**
    ```json
    {
      "patient_age": "3 years",
      "symptoms": ["fever", "cough"],
      "severity": "high",
      "duration": "2 days"
    }
    ```
* **In SwaraSetu:** Enables rural patients to speak naturally in their dialect without filling out complex forms. Sarvam AI's NER translates unstructured spoken language into canonical clinical entities for decision tree processing.

---

## 2. Project Concept in Plain Terms

SwaraSetu (*"Voice Bridge"*) is an offline-first, voice-native triage assistant built for India's last-mile healthcare gap.

### The 4-Step User Journey:
1. **Voice Intake:** Patients report symptoms by speaking naturally via WhatsApp voice note, toll-free IVRS call, or feature phone in their native language (e.g., Hindi, Tamil, Bengali).
2. **Entity Extraction (Sarvam AI):** Sarvam Speech-to-Text transcribes speech; Sarvam NER extracts structured clinical indicators (`symptom`, `duration`, `severity`, `red_flags`).
3. **Deterministic Triage (WHO IMCI Engine):** Clinical logic evaluates the extracted data against the WHO Integrated Management of Childhood Illness protocol:
   * **Score 1 (Self-Care):** Home care instructions (e.g., Paracetamol, hydration).
   * **Score 2 (CHW Follow-Up):** Medium risk; triggers automated SMS alert to the local ASHA worker within 24 hours.
   * **Score 3 (Urgent Emergency):** Critical risk; calculates coordinates and routes the patient to the nearest open Primary Health Centre (PHC).
4. **Localized Voice Output:** Outcome is translated back to the patient's dialect and delivered as an audio voice note (Sarvam TTS) to bypass literacy barriers.

---

## 3. Dual-Engine Hybrid Architecture & Offline Strategy

Because cloud-based AI APIs (Sarvam STT/NER/TTS) require active internet, SwaraSetu uses a **Dual-Engine Hybrid Architecture** combining cloud AI with on-device edge AI.

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                            SWARASETU HYBRID                             │
 └─────────────────────────────────────────────────────────────────────────┘
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         ▼                                                       ▼
  ONLINE CHANNEL                                         OFFLINE CHANNEL
  (Patient WhatsApp / IVRS)                              (ASHA Worker Mobile App / Tablet)
  • Sarvam Cloud ASR / NER / TTS                         • On-Device Quantized `indic-seamless` (4-bit ONNX)
  • Natural Voice Intake (22+ Dialects)                  • Local Direct Speech-to-Translation (S2TT)
  • Dynamic Localized Audio Generation                   • Embedded Client-Side WHO IMCI Engine
  • Zero Smartphone App Install                          • Pre-seeded Local PHC Database (IndexedDB/SQLite)
  • Centralized DB Telemetry                             • Local Outbox -> Auto-Syncs on Reconnect
```

### Technical Feature Matrix: Online vs. Offline

| Capability | Online Mode (WhatsApp / IVRS) | Offline Mode (4GB+ Android App) | Offline Failsafe (2GB Legacy Tablet) |
|---|---|---|---|
| **Intake Mechanism** | Spoken Voice Note / Audio | Spoken Voice Note (On-Device) | Touch-to-Hear Visual Form |
| **Parsing & Translation** | Sarvam Cloud ASR + NER | 4-bit Quantized `indic-seamless` S2TT | Pre-mapped Key Matrix / Direct Selection |
| **Triage Engine** | FastAPI Server IMCI Python Engine | Local In-Memory JS/Python IMCI Tree | Local Client-Side IMCI Decision Tree |
| **Audio Guidance** | Dynamic Sarvam TTS Voice | Cached / Embedded Voice Audio | Pre-cached Static Audio Clips (.mp3) |
| **PHC Mapping** | Live NHM API + Nominatim | Pre-seeded Local SQLite/JSON DB | Pre-seeded Local SQLite/JSON DB |
| **Alerts / Sync** | Instant SMS / Celery Dispatch | Local Outbox Queue $\rightarrow$ Background Sync | Local Outbox Queue $\rightarrow$ Background Sync |
| **Min Hardware** | Any feature phone / WhatsApp | Android 10+, 4GB+ RAM, NPU/GPU | 2GB RAM, Any Web/PWA Browser |


---

## 4. Ultra-Low / Zero-Literacy UX Framework

To support rural populations and semi-literate field workers:

### 1. Touch-to-Hear (Audio Tooltips)
* Tapping or holding any UI element plays a 2-second audio prompt in the regional dialect explaining the action or symptom.

### 2. Culturally Anchored Visual Symbols
* Replaces generic icons with culturally recognizable illustrations:
  * **Fever:** Mother feeling child's forehead with a cloth.
  * **Pneumonia/Breathing:** Child illustration with visible chest indrawing (ribcage sinking).
  * **Duration:** Sun/Moon rise and set symbols (1 Sun = 1 Day).

### 3. Traffic-Light Color Signals
* Universal severity indicators: **Green** (Home Care), **Yellow** (ASHA Visit), **Red** (Emergency Referral).

---

## 5. Deployment Execution & Pitching Strategy

### 10-Day Build Roadmap

```
Week 1 — Core Systems
├── Day 1–2: Implement WHO IMCI Triage Engine (Fever, Respiratory, Diarrhoea, Maternal)
├── Day 3–4: Integrate Sarvam AI Stack (STT, NER, TTS, Translate APIs)
└── Day 5–7: Build Dual-Mode Frontend (WhatsApp UI, ASHA PWA Tablet, Supervisor Dashboard)

Week 2 — Integration & Fail-Safes
├── Day 8: Build Offline PWA Caching (Service Worker, IndexedDB, Pre-cached Audio)
├── Day 9: Implement Pre-recorded API Fallback Switch (guards against Wi-Fi drops)
└── Day 10: Demo Run-Throughs & Pitch Refinement
```

### 3-Minute Product Pitch Script

1. **0:00 - 0:40 | Problem & Impact:**
   * *"India has 0.7 doctors per 1,000 rural citizens. 800M people live 45 minutes from healthcare. Text-based apps fail due to low literacy. SwaraSetu is an offline-first, voice-native triage assistant."*
2. **0:40 - 1:30 | Live Demo 1 (Online Voice AI):**
   * Demonstrate playing a voice note in Tamil/Hindi on the WhatsApp UI. Highlight real-time Sarvam transcription, NER extraction card, WHO IMCI rule execution, and TTS voice output.
3. **1:30 - 2:10 | Live Demo 2 (Offline CHW Tablet PWA):**
   * Toggle to "Offline Mode." Demonstrate the ASHA tablet UI using Touch-to-Hear icons, local IMCI calculation, pre-cached audio playback, and background data sync queuing.
4. **2:10 - 2:45 | Live Demo 3 (Supervisor Dashboard):**
   * Show the district-level analytics dashboard tracking epidemiological trends (fever spikes, escalation rates).
5. **2:45 - 3:00 | Conclusion & Alignment:**
   * Summarize alignment with UN SDGs 3, 4, 10 and India's National Health Mission (NHM).

### Evaluation Q&A Defense Matrix

| Evaluator Question | Strategy / Response |
|---|---|
| **Medical Accuracy & LLM Hallucination** | We do **not** use generative LLMs for medical reasoning. Sarvam AI is used strictly for translation and entity extraction. Medical triage relies 100% on deterministic decision trees executing official WHO IMCI protocols. |
| **Low-Literacy Usability** | Patients interact verbally via voice notes without viewing screens. For ASHA workers, the tablet PWA incorporates a Touch-to-Hear UX framework where every visual icon plays audio explanations in the local dialect. |
| **Regulatory Compliance (CDSCO)** | SwaraSetu operates as a clinical decision-support and navigation tool, not a diagnostic device. It incorporates medical disclaimers, routes users to accredited NHM PHCs, and integrates national helpline 104 as a fallback. |
| **Offline Capability Scope** | The patient-facing WhatsApp channel operates online via Sarvam Cloud APIs. The field-level ASHA Tablet PWA functions 100% offline using client-side JavaScript IMCI logic, pre-seeded PHC data, and cached audio clips. |

---

## 6. External References & Resources

1. **WHO IMCI Guidelines:** [Integrated Management of Childhood Illness (WHO)](https://www.who.int/publications/i/item/9789241506823)
2. **Sarvam AI Documentation:** [Sarvam Indic AI Stack Docs](https://sarvam.ai)
3. **NHM Health Facility Registry:** [Data.gov.in Health Facility Dataset](https://data.gov.in)
4. **NFHS-5 Data:** [National Family Health Survey (India)](https://rchiips.org/nfhs/)
5. **Ayushman Bharat Digital Mission (ABDM):** [ABDM Sandbox Portal](https://sandbox.abdm.gov.in)
