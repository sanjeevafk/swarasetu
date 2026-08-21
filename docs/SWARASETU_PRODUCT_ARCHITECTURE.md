# 🩺 SwaraSetu: Voice-Native Rural Healthcare AI Architecture

> *"Your voice, your village, your first doctor."*

**SwaraSetu** is an offline-first, voice-native medical triage assistant designed to bridge India's last-mile healthcare gap using Sarvam AI's Indic language stack and the WHO IMCI (Integrated Management of Childhood Illness) decision protocol.

---

## 🏗️ Technical Architecture & Stack

```
                                  PATIENT / CHW
            (Voice Note / IVRS / USSD / Offline PWA Tablet)
                                      │
                                      ▼
                      ┌──────────────────────────────┐
                      │    Sarvam Indic ASR & NER    │
                      │  (Speech-to-Text & Language) │
                      └───────────────┬──────────────┘
                                      │
                                      ▼
                      ┌──────────────────────────────┐
                      │   WHO IMCI Triage Engine     │
                      │ (Deterministic Python Tree)  │
                      └───────────────┬──────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
      Score 1 (Self-Care)    Score 2 (ASHA Dispatch)  Score 3 (Emergency)
      - Sarvam TTS Voice     - Asynchronous SMS to    - Spatial Route to
        Instructions           Local ASHA Worker        Nearest PHC Map
```

### Stack Components
- **Indic Cloud Voice Engine:** Sarvam AI Stack (ASR, Translation, TTS, 22+ languages for online WhatsApp/IVRS).
- **Indic Edge Voice Engine (Offline):** 4-bit Quantized `ai4bharat/indic-seamless` (Unified Speech-to-Text-Translation across 14 Indic languages) via ONNX Runtime Mobile / ExecuTorch.
- **Triage Engine:** Deterministic Python / TypeScript WHO IMCI decision tree (zero AI hallucination).
- **Frontend / Mobile:** React 18, Vite, TypeScript, Tailwind CSS, IndexedDB / SQLite (offline queue & sync), Android Native Wrapper.
- **Backend:** Python 3.11, FastAPI, PostgreSQL 15, Redis (session state), Celery.
- **Integrations:** WhatsApp (Twilio/Gupshup), NHM Open API, OpenStreetMap / Leaflet.

---

## 📱 3-Tier Deployment & Hardware Matrix

| Tier | Target User / Channel | Voice / AI Engine | Hardware / Connectivity Specs |
|---|---|---|---|
| **Tier 1: Online Cloud** | Patients via WhatsApp / IVRS | Sarvam AI Cloud (ASR, NER, TTS) | Any 2G/3G/4G/WhatsApp device; zero install |
| **Tier 2: Offline Edge AI** | ASHA / CHW Native Mobile App | Quantized `indic-seamless` (ONNX / ExecuTorch) + Local IMCI | Android 10+, 4GB–8GB RAM, NPU/GPU accelerated |
| **Tier 3: Offline Failsafe** | Legacy CHW Tablets & Low-RAM Devices | Touch-to-Hear Visual Form + Pre-cached Audio + Local IMCI | 2GB–3GB RAM tablets; zero memory crashes |

---

## 🏆 Core Architecture Advantages

1. **Deterministic Medical Logic vs. LLM Hallucination:**
   Using AI *only* for speech-to-text, translation, and entity extraction while running a **deterministic WHO decision tree** guarantees clinical accuracy and patient safety.

2. **True Edge-Native Offline Multilingual AI:**
   Unlike competitors with mocked offline modes or English-only voice, SwaraSetu runs **on-device quantized Indic speech translation (`indic-seamless`)** directly on field smartphones with zero internet.

3. **Omnichannel & Graceful Degradation:**
   Operates across USSD (2G), IVRS, WhatsApp, high-performance offline mobile apps, and low-spec 2GB tablet failsafes.

4. **High National Alignment:**
   Directly solves National Health Mission (NHM) objectives: rural doctor scarcity (0.7/1000), low literacy, and delayed triage.

---

## 📋 Recommended Enhancements

- [ ] **ABDM / ABHA ID Linkage:** Integrate Ayushman Bharat Digital Mission patient IDs.
- [ ] **On-Device ONNX Benchmark Suite:** Measure latency and RAM usage of quantized `indic-seamless` on Android devices.
- [ ] **Offline Sync Demo:** Show live IndexedDB / SQLite outbox sync when network reconnects.

