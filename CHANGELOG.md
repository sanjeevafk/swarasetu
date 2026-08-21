# SwaraSetu (स्वर सेतु) — Changelog

All notable changes, architectural enhancements, and protocol upgrades for SwaraSetu are documented here.

---

## [v1.2.0] - 2026-08-22

### 🚨 4-Pillar Extreme & Edge-Case Emergency Response System
- **Acute Envenomation & Snake Bite Protocol:**
  - Added deterministic recognition for snake bites (`பாம்பு கடி`, `பாம்பு கிடைச்சிருச்சு`, `सांप काटना`, `সাপের কামড়`, `snake bite`), scorpion stings, and animal bites.
  - Automatically routes to **🔴 RED EMERGENCY (Score 3)**, bypassing home care fallbacks.
- **108 CAD Ambulance Auto-Dispatch:**
  - Built [`backend/app/triage/first_aid.py`](file:///home/sanjeev/Downloads/swarasetu/backend/app/triage/first_aid.py) generating Computer-Aided Dispatch (CAD) incident tickets (e.g., `#108-EMRI-B391`, Priority `CRITICAL_P1`).
- **Hospital Pre-Arrival & ASHA Alerting:**
  - Pings the nearest Primary Health Centre (PHC) duty doctor with specific equipment readiness (Anti-Snake Venom vials, ECG bay, sterile trauma dressings, Magnesium Sulfate).
- **Localized Life-Saving First-Aid Directives:**
  - Spoken and written native first-aid directives across Tamil, Hindi, Bengali, and English (e.g., prohibiting tourniquets/cuts for snake bites, 20-min running water for burns, left lateral positioning for maternal emergencies).
- **Interactive UI Quadrant:**
  - Enhanced `<TriageResultCard />` and `<DemoChat />` with live ambulance status badge, hospital readiness cards, first-aid checklist, and 1-tap Google Maps PHC route.

---

## [v1.1.0] - 2026-08-21

### 🤖 Live Omnichannel Bot Integration & Native Voice Synthesis
- **Live Telegram Bot ([`@swarasetubot`](https://t.me/swarasetubot)):**
  - Webhook listener at `/channels/telegram` supporting native audio voice notes and text messages.
  - Automatic download and processing of Telegram `.ogg` voice files.
- **Meta WhatsApp Cloud API Router:**
  - Webhook verification (`GET /channels/meta-whatsapp`) and message intake (`POST /channels/meta-whatsapp`).
- **Dialect-Aware Native TTS & Speech Auto-Detection:**
  - Upgraded Sarvam ASR to `language_code="unknown"` for dynamic Indic language recognition (Hindi, Tamil, Bengali, Telugu, Marathi, Gujarati, Punjabi, English).
  - Dynamic translation of clinical advice into detected native dialects before Sarvam TTS synthesis.
  - Returns spoken voice notes matching the caller's native language with human intonation.

---

## [v1.0.0] - 2026-08-20

### 🏥 Core Rural Triage & Dual-Channel Engine
- **WHO IMCI Deterministic Rule Engine:**
  - Auditable syndromic decision trees across Fever, Respiratory, Diarrhoea, and Maternal clusters.
  - 100% deterministic (zero probabilistic LLM hallucination in clinical triage).
- **Offline ASHA Tablet Edge Mode:**
  - Local SQLite caching and background outbox queue with GSM SMS synchronization.
- **District Spatial PHC Routing:**
  - Haversine distance calculations linking patients to the nearest verified PHC and on-duty medical officers.
