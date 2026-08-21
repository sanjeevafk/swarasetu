# SwaraSetu — Project Evaluation & Agent Feasibility

## TL;DR
**Yes — e2e completion by agents is feasible within 1–2 weeks**, with realistic caveats on third-party API access (Sarvam AI, Twilio). The project is very well-scoped for a hackathon; most of the hard design work is already done. Agents can close the delta from the current prototype to a polished, fully integrated MVP.

---

## Current State of the Repo

| Layer | Status | Quality |
|---|---|---|
| **Documentation** | ✅ Complete | Excellent — PRD, architecture, user flow SVGs, SIH pitch doc |
| **Frontend Shell** | ✅ Exists | React 18 + Vite + TypeScript + Tailwind + shadcn/ui, good component structure |
| **UI Components** | 🟡 Partial | `DemoChat`, `CHWTablet`, `SupervisorDashboard`, `PHCMap`, `TriageResultCard`, `LanguageBadge` — all built but **entirely mocked** |
| **State Management** | ✅ Exists | Zustand store (`useAppStore`) wired up correctly |
| **Mock Data** | ✅ Exists | 3 language scenarios (Tamil/Hindi/Bengali), dashboard data, PHC seed data |
| **Backend** | ❌ Missing | FastAPI, PostgreSQL, Redis, Celery — none exist yet |
| **Sarvam API Integration** | ❌ Missing | STT, NER, TTS, Translate — all hardcoded mocks |
| **IMCI Triage Engine** | ❌ Missing | Deterministic Python logic tree — not implemented |
| **WhatsApp / Twilio** | ❌ Missing | Webhook server not started |
| **PHC Locator** | ❌ Missing | NHM API not integrated (Leaflet map exists but uses static mock pins) |
| **Offline PWA** | ❌ Missing | Service Worker and IndexedDB not configured |
| **Supervisor Dashboard** | 🟡 Partial | UI shell is done with Recharts; needs live data from backend |

---

## What's Good 👍

1. **Extremely strong documentation.** The PRD + architecture are production-grade. Any agent can read these and know *exactly* what to build — this is the biggest time saver.
2. **Clean frontend scaffolding.** Tech stack choices (React, Zustand, shadcn/ui, Leaflet, Recharts) are correct and all dependencies are already in `package.json`. No wasted decisions.
3. **Scenario data model is correct.** The `SymptomScenario` interface (`symptoms`, `duration`, `redFlags`, `imciDecision`, `riskScore`) directly mirrors what the Sarvam NER output would produce — very little schema translation needed.
4. **Three demo scenarios are real.** Tamil (Score 1), Hindi (Score 2), Bengali (Score 3) cover the full triage spectrum and match the IMCI clusters from the PRD.
5. **Scope is locked.** The "Explicitly Out of Scope" section in the PRD is clear — ABDM, full 22 languages, model fine-tuning are all deferred. Agents won't over-engineer.

---

## Gaps to Close (Ordered by Priority)

### 🔴 Critical / Blocking
| Task | Effort | Notes |
|---|---|---|
| **Python backend bootstrapping** | 2–3 days | FastAPI + PostgreSQL + Redis + Celery, Docker Compose. Boilerplate but comprehensive. |
| **IMCI Triage Engine (Python)** | 1–2 days | Deterministic decision tree for 4 clusters (fever, respiratory, diarrhoea, maternal). WHO protocol is openly documented. |
| **Sarvam STT/NER/TTS/Translate wiring** | 1–2 days | Replace mocks with real API calls. Requires Sarvam API key and understanding of their endpoint schemas. |
| **Frontend ↔ Backend API wiring** | 1 day | Replace all mock data fetches in Zustand store with live FastAPI calls. |

### 🟡 Important / Demo-Critical
| Task | Effort | Notes |
|---|---|---|
| **WhatsApp webhook (Twilio/Gupshup)** | 1 day | Receives voice notes, pipes to STT → NER → IMCI → response composer. Sandbox is free. |
| **PHC Locator (NHM Open API)** | 1 day | Replace mock Leaflet pins with real NHM HFDR data + Nominatim geocoding. |
| **CHW SMS Alert (Twilio SMS)** | 0.5 days | Celery task for Score 2 dispatch. Straightforward once backend exists. |
| **Case logging to PostgreSQL** | 0.5 days | De-identified writes per interaction. Schema is already implied by the PRD. |
| **Supervisor Dashboard live data** | 0.5 days | Wire Recharts to real aggregated DB queries instead of `mockDashboardData.ts`. |

### 🟢 Nice-to-Have / P1
| Task | Effort | Notes |
|---|---|---|
| **Offline PWA (Service Worker + IndexedDB)** | 1–2 days | Cache IMCI logic and mock scenarios offline; background sync on reconnect. |
| **Clarification loop (2 follow-up Qs)** | 1 day | If NER confidence < 0.6, Sarvam Translate generates dialect-aware follow-up. |
| **USSD stub** | 0.5 days | Simulated terminal-style flow for demo purposes. |

---

## Agent Feasibility Assessment

### What agents can do well here:
- ✅ **Backend scaffolding** — FastAPI/Docker boilerplate is mechanical; agents excel at this.
- ✅ **IMCI logic tree** — Fully deterministic, documented by WHO. Agents can implement this precisely from the PRD's IMCI condition clusters (Section 10).
- ✅ **API wiring** — Replacing mock calls with real HTTP requests is straightforward once API schemas are known.
- ✅ **Frontend completions** — Connecting Zustand actions to the backend, making the Leaflet map live, wiring CHW SMS confirmation UI.
- ✅ **Test harnesses** — Generating test suites for each triage scenario.

### Where agents need your input:
- 🔑 **Sarvam AI API key** — Agents cannot generate this; you need to register at sarvam.ai.
- 🔑 **Twilio sandbox credentials** — Same: account SID, auth token, WhatsApp sandbox number.
- 🔑 **NHM HFDR dataset** — Download the PHC CSV from data.gov.in; agents can seed it into Postgres.
- ⚠️ **Sarvam NER output schema** — The actual JSON structure from Sarvam's `/extract` endpoint needs to be validated against the `SymptomScenario` interface. This may require 1–2 iterations.
- ⚠️ **Audio file handling** — Twilio sends voice notes as `.ogg` / `.mp3` blobs to a public webhook URL; local dev needs `ngrok` or Render/Railway deployment.

---

## 1–2 Week Agent Execution Plan

```
Week 1 — Core Infrastructure
├── Day 1: Python backend scaffold (FastAPI, Docker Compose, DB schema, Celery)
├── Day 2: IMCI Triage Engine (4 clusters, unit-tested against PRD scenarios)
├── Day 3: Sarvam API client module (STT, NER, TTS, Translate, fallback)
├── Day 4: WhatsApp webhook + end-to-end flow (voice note → triage response)
└── Day 5: Frontend ↔ backend wiring + case logging

Week 2 — Edge AI, Integration & Polish
├── Day 1: PHC locator (NHM data seed + Nominatim + live Leaflet map)
├── Day 2: CHW SMS alert + Supervisor dashboard live data
├── Day 3: Offline storage & sync (IndexedDB outbox + background sync queue)
├── Day 4: Edge AI model pipeline (4-bit quantized `indic-seamless` ONNX export & benchmark)
└── Day 5: Demo hardening (3-tier failsafe toggle, rate limit fallbacks, demo script run-through)
```

> [!IMPORTANT]
> The biggest single risk is **Sarvam NER schema compatibility** with your existing `SymptomScenario` type. Resolve this on Day 3 of Week 1 — it unblocks everything else.

---

## 🤖 Coding Agent Handoff Readiness Checklist

Can this project be safely handed off to a coding agent right now? **Yes, with 3 specific input keys provided.**

| Component | Agent Autonomous? | What the Agent Can Execute Directly | What Requires Human Input |
|---|---|---|---|
| **Python Backend & DB** | ✅ 100% Autonomous | Scaffold FastAPI, PostgreSQL tables, Redis session store, Celery queue. | None (runs in Docker Compose) |
| **WHO IMCI Engine** | ✅ 100% Autonomous | Implement deterministic triage logic tree for 4 clusters with full unit tests. | None (WHO protocol is deterministic) |
| **Zustand & Frontend UI** | ✅ 100% Autonomous | Connect mock UI components to real FastAPI endpoints & Leaflet live map. | None |
| **Sarvam Cloud Pipeline** | 🟡 Needs API Key | Build client wrapper (`sarvam_client.py`), fallback handler, and mock test harness. | Sarvam AI API Key |
| **WhatsApp / SMS Webhook** | 🟡 Needs Credentials | Implement Twilio webhook handler and Celery SMS dispatch tasks. | Twilio Sandbox Account SID / Token |
| **Edge AI ONNX Runner** | ✅ 100% Autonomous | Write ONNX Runtime script/Wasm runner for quantized Indic speech model. | None (HuggingFace model is open-weights) |

---

## Verdict

| Dimension | Score |
|---|---|
| Concept & Design | ⭐⭐⭐⭐⭐ |
| Documentation Quality | ⭐⭐⭐⭐⭐ |
| Frontend Polish | ⭐⭐⭐⭐☆ |
| Backend Completion | ⭐☆☆☆☆ |
| Agent-Friendliness | ⭐⭐⭐⭐⭐ |
| **E2E in 1–2 weeks?** | **✅ Yes, confidently** |

The project is in an ideal state for agent-assisted completion: the vision is crystal clear, the frontend skeleton exists, and all the hardest design decisions are already made in the PRD. The remaining work is largely mechanical (scaffold, wire, test) — exactly what agents are best at.

