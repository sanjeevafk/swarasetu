# SwaraSetu (Voicebridge) — Changelog

All notable changes, architectural enhancements, and protocol upgrades for SwaraSetu are documented here.

---

## [v1.2.1] - 2026-08-22

### 🔒 Security, Clinical Safety & Resilience Hardening
- **P1 Security Hardening:**
  - Fixed Twilio signature validation auth bypass regression: missing `X-Twilio-Signature` header now strictly returns `403 Forbidden` when `TWILIO_AUTH_TOKEN` is configured.
  - Implemented Telegram Webhook secret authentication: validates `X-Telegram-Bot-Api-Secret-Token` via constant-time comparison.
  - Implemented Meta WhatsApp HMAC-SHA256 signature verification: validates raw request body against `X-Hub-Signature-256` using `META_APP_SECRET`.
  - Upgraded privacy & PII logging: redacted raw webhook payload logging across all channels.
  - Required environment-configured `META_VERIFY_TOKEN` (removed guessable defaults).
- **P1 Clinical Safety Invariant Enforced:**
  - Removed all fabricated numerical vitals (`breathing_rate_per_min = 55` and `stool_frequency_per_day = 5`). Reported symptoms drive severity purely via deterministic qualitative syndromic flags.
- **P2 Bug Fixes & Edge Mirroring:**
  - Fixed Telegram language detection dead-code bug: ASR-detected BCP-47 language is now preserved and script regex expanded to all 10 Indian scripts (Hindi, Tamil, Bengali, Telugu, Kannada, Malayalam, Gujarati, Punjabi, Odia, Marathi).
  - Fixed corrupted multilingual keyword `"रक्त দস্ত"` into separate clean Hindi and Bengali clinical lexicons.
  - Fixed Telegram nearest PHC fallback routing.
  - Synchronized client-side offline edge engine ([`src/lib/triageLocal.ts`](file:///home/sanjeev/Downloads/swarasetu/src/lib/triageLocal.ts)) with snake bite and severe trauma rules.
  - Restricted `GET /channels/whatsapp` to lightweight status/health check.
  - Added unit test suite covering emergency protocols, zero-fabricated vitals, and webhook security (67 tests passing).

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
  - Spoken and written native first-aid directives across Tamil, Hindi, Bengali, and English.
- **Interactive UI Quadrant:**
  - Enhanced `<TriageResultCard />` and `<DemoChat />` with live ambulance status badge, hospital readiness cards, first-aid checklist, and 1-tap Google Maps PHC route.

---

## [v1.1.0] - 2026-08-21

### 🤖 Live Omnichannel Bot Integration & Native Voice Synthesis
- **Live Telegram Bot ([`@swarasetubot`](https://t.me/swarasetubot)):**
  - Webhook listener at `/channels/telegram` supporting native audio voice notes and text messages.
- **Meta WhatsApp Cloud API Router:**
  - Webhook verification (`GET /channels/meta-whatsapp`) and message intake (`POST /channels/meta-whatsapp`).
- **Dialect-Aware Native TTS & Speech Auto-Detection:**
  - Upgraded Sarvam ASR for dynamic Indic language recognition.
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
