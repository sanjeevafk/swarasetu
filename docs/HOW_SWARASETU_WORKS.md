# How SwaraSetu Works: The Dual-Channel (Online WhatsApp + Offline Tablet) Architecture

A frequent question from technical evaluators and Smart India Hackathon (SIH) judges is:
> **"How is SwaraSetu an offline healthcare app if it integrates with WhatsApp?"**

The answer lies in SwaraSetu's **Dual-Channel / 3-Tier Architecture**, designed specifically for the dual realities of India's rural healthcare landscape.

---

## 1. The Dual Reality of Rural Healthcare

```
┌────────────────────────────────────────────────────────────────────────┐
│                          RURAL HEALTHCARE ECOSYSTEM                    │
│                                                                        │
│   [ Patient at Home ]                       [ ASHA Worker in Field ]   │
│   • Has basic 2G/3G/4G signal               • Travels to remote hamlets│
│   • Zero English literacy                   • 0% cellular reception    │
│   • Refuses to install heavy apps           • Needs clinical decision  │
│   • Already uses WhatsApp / Voice             support on-device        │
│                │                                         │             │
│                ▼                                         ▼             │
│   [ CHANNEL 1: ONLINE WHATSAPP ]            [ CHANNEL 2: OFFLINE PWA ] │
│   (Zero-Install Patient Gateway)            (100% On-Device Tablet)    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Channel 1: The Online Patient Gateway (WhatsApp & IVRS)

### Target User:
Rural and semi-urban patients sitting at home with basic mobile connectivity.

### The Problem it Solves:
800 million rural Indians cannot read English health apps and will never download an 80MB Android application from the Play Store. However, **nearly all of them already know how to send voice notes on WhatsApp**.

### How it Works:
1. **Dedicated Number:** The health department provisions a verified WhatsApp Business number (e.g. `+91-XXXXX-XXXXX` or Twilio Sandbox `+1 415 523 8886`).
2. **Voice Intake:** The patient opens a regular 1-on-1 chat, taps the microphone icon, and speaks in their native language (Hindi, Tamil, Bengali, Telugu, etc.):
   > *"बच्चे को दो दिन से तेज बुखार है और सांस लेने में तकलीफ हो रही है।"*
3. **Cloud Processing Pipeline:**
   - **Sarvam Indic ASR:** Transcribes rural accents and code-mixed dialects in real time.
   - **Clinical NER:** Converts unstructured speech into a structured clinical JSON payload.
   - **Deterministic WHO IMCI Engine:** Computes risk score (1 = Self-Care, 2 = ASHA Dispatch, 3 = Immediate Emergency).
   - **Sarvam TTS:** Synthesizes the clinical advice into a spoken voice note and returns it directly inside WhatsApp.
4. **Automated ASHA Worker Dispatch (Score 2 / Yellow):**
   - The backend queries the `AshaAssignment` database table and immediately fires an **automated SMS alert** to the local village ASHA worker's phone:
   > *"🚨 ASHA ALERT: Moderate fever and cough reported in Belsand village. Home visit required within 24 hours."*
5. **Nearest PHC Emergency Routing (Score 3 / Red):**
   - For critical emergencies, the engine calculates the closest Primary Health Centre using the **Haversine spatial algorithm** and sends the patient the facility name, distance, 24/7 hours, and doctor contact number.

---

## 3. Channel 2: The 100% Offline ASHA Field Tablet (Zero Internet)

### Target User:
Frontline ASHA workers and ANMs conducting doorstep home visits in deep rural, tribal, or "media-dark" hamlets where **there are zero mobile towers and NO internet signal**.

### The Problem it Solves:
WhatsApp and cloud voice APIs cannot function without internet packets. In deep rural India (where 55% of geographical territory lacks reliable 4G), frontline workers need a clinical decision support tool that works in **total network blackout**.

### How it Works:
1. **Progressive Web App (PWA):** Pre-installed on state-issued Android tablets and cached locally via Service Workers.
2. **Hardware Satellite GPS:** Determines latitude and longitude directly from orbital satellite radio signals (1575.42 MHz) on the device baseband chip without mobile data.
3. **On-Device Speech & IMCI Execution:**
   - Runs a 4-bit quantized speech model (`ai4bharat/indic-seamless` / `indicwhisper-base`) via ONNX Runtime Mobile / WASM.
   - The deterministic WHO IMCI clinical decision tree executes **100% locally on the tablet CPU in under 1 millisecond**.
4. **IndexedDB Outbox Queue:**
   - Every patient assessment, risk score, and clinical note is written to on-device IndexedDB storage.
5. **Automated Background Sync:**
   - When the ASHA worker finishes her village rounds and returns to network coverage (or connects to the PHC Wi-Fi), the tablet's online event listener (`window.addEventListener('online')`) **automatically flushes all queued cases to the central district supervisor PostgreSQL database**.

---

## 4. Architectural Comparison Matrix

| Feature | Channel 1: Online Patient (WhatsApp) | Channel 2: Offline Worker (ASHA Tablet) |
|---|---|---|
| **Primary User** | Rural Patient / Family | Frontline ASHA Health Worker |
| **Internet Requirement** | Active 2G/3G/4G / Cellular Signal | **0% Internet (100% Offline)** |
| **App Installation** | **Zero Install** (Runs inside native WhatsApp) | Pre-cached PWA on tablet |
| **Speech Processing** | Sarvam AI Cloud Indic Pipeline | Quantized On-Device Edge ONNX Model |
| **Clinical Decision Logic** | Server-side Python WHO IMCI Engine | Local TypeScript / Python IMCI Engine |
| **Emergency Escalation** | Automated SMS to local ASHA + PHC card | Immediate on-screen referral card |
| **Data Persistence** | Direct PostgreSQL / SQLite writes | Local IndexedDB Queue → Background Sync |
| **Literacy Barrier** | **Bypassed via Spoken Audio Voice Notes** | Visual Touch-to-Hear Form & Voice |

---

## 5. Technical Defense for SIH Judges

When presenting to evaluation committees, highlight this clear distinction:

1. **"WhatsApp provides consumer accessibility (Zero App Install)."**
   - It eliminates the adoption barrier for 800M citizens who refuse to install complex apps.
2. **"The Tablet App provides clinical reliability (Zero Internet Failure)."**
   - It equips frontline health workers to deliver standardized WHO-grade pediatric and maternal triage even in the most remote tribal corners of India.
3. **"The two channels interconnect through the District Health Database."**
   - An online voice note from a patient triggers an offline visit assignment on the ASHA worker's tablet, closing the loop between village and hospital.
