# Touch-to-Hear — Zero-Literacy Visual Symptom Input

**Component:** [`src/components/TouchToHearPanel.tsx`](../src/components/TouchToHearPanel.tsx)  
**Integrated into:** [`src/components/CHWTablet.tsx`](../src/components/CHWTablet.tsx)  
**Tests:** [`src/components/TouchToHearPanel.test.ts`](../src/components/TouchToHearPanel.test.ts)  
**Status:** ✅ Fully implemented and build-verified

---

## 1. Purpose

Touch-to-Hear replaces free-form text/voice entry in the ASHA CHW tablet with large visual
symptom tiles. The ASHA worker taps the speaker button on each tile to hear a 2-second clinical
instruction in their regional dialect, then taps **Yes** or **No**. The UI builds a 100% clean,
structured `SymptomPayload` directly from the taps — no text parsing, no AI extraction, no
network call — and evaluates it using the on-device WHO IMCI engine in < 1 ms.

This is the **Tier 3 failsafe path**: 2 GB RAM tablets, zero bandwidth, zero English literacy.

---

## 2. How It Works

### 2.1 Visual Tiles

Eight symptom tiles are displayed in a 2-column grid:

| Tile | Emoji | Payload Key | Severity |
|------|-------|------------|----------|
| Fever | 🌡️ | `has_fever` | Yellow |
| Chest Indrawing | 🫁 | `chest_indrawing` | Red |
| Fast Breathing | 💨 | `difficulty_breathing` | Red |
| Diarrhoea | 💧 | `diarrhoea` | Yellow |
| Convulsions | ⚡ | `convulsions` | Red |
| Vomiting Everything | 🤢 | `vomiting_everything` | Red |
| Cannot Drink | 🚫 | `unable_to_drink_or_breastfeed` | Red |
| Snake Bite / Poisoning | 🐍 | `acute_poisoning_or_bite` | Red |

### 2.2 Touch-to-Hear Audio

Tapping the **Touch-to-Hear** button on any tile calls `window.speechSynthesis.speak()` with:
- A pre-authored clinical instruction string (not synthesized — exact text is hardcoded in `AUDIO_PROMPTS`)
- Language set to `hi-IN` (Hindi), `ta-IN` (Tamil), or `bn-IN` (Bengali) based on the active
  tablet language selected in the parent app store
- Rate `0.9` (slightly slower for clarity)

This is **100% offline** — the Web Speech API is a browser built-in, no network request.

### 2.3 Fever Sub-Question

When the ASHA worker answers **Yes** to Fever, a duration sub-question appears:
- ☀️ **1–2 days** → sets `fever_days = 1` (shorter duration, lower severity)
- ☀️☀️☀️ **3+ days** → sets `fever_days = 4` (prolonged fever, triggers higher risk)

### 2.4 Age Group

A row of age-group chips (Neonate / Infant / Child / Adolescent / Adult) at the top of the panel
sets `payload.age_group`. The chip row also has a Touch-to-Hear button. Default is `'child'`.

### 2.5 Evaluation Gate

The **Run WHO IMCI Triage** button is disabled until ≥ 3 tiles have been answered (Yes or No).
This prevents accidental submissions with too little data.

### 2.6 Triage Result

On submit, the UI calls `evaluateLocal(payload)` (the on-device TypeScript mirror of the Python
WHO IMCI engine) and renders the result using `<TriageResultCard>` inline below the tiles.

---

## 3. Tab Switcher in ASHA Tablet

The **Swara ASHA Portal** header (`CHWTablet.tsx`) now shows a two-button tab switcher:

- **Voice** (💬) → renders `<DemoChat>` (existing voice/text chat flow using Sarvam Cloud or offline STT)
- **Touch-to-Hear** (🔊) → renders `<TouchToHearPanel>` (visual icon-tap flow)

The active tab is stored in local `useState` and persists for the current session.

---

## 4. Language Coverage

All 8 tile audio prompts + age group prompt are authored in all 3 tablet languages:

| Language | BCP-47 Tag | Coverage |
|----------|-----------|---------|
| Hindi | `hi-IN` | All 9 prompts |
| Tamil | `ta-IN` | All 9 prompts |
| Bengali | `bn-IN` | All 9 prompts |

Language is read from `useAppStore().activeLanguage` and passed as a prop to `TouchToHearPanel`.

---

## 5. Testing

### 5.1 Unit Tests (TypeScript — logic layer)

File: [`src/components/TouchToHearPanel.test.ts`](../src/components/TouchToHearPanel.test.ts)

Tests cover:
- All 8 tile IDs map to a valid `SymptomPayload` key
- Each Yes answer sets the correct boolean field
- Fever + `long` duration → `fever_days = 4`
- Snake bite → `risk_score = 3`
- Convulsions → `risk_score = 3`
- Chest indrawing + fever → `risk_score = 3`
- Vomiting everything → `risk_score = 3`
- Cannot drink → `risk_score = 3`
- Mild fever short duration → `risk_score ≤ 2`
- All clear → `risk_score = 1`
- Result always has non-empty `rationale_en` and `actions[]`
- `canEvaluate` gate: < 3 answers blocked, ≥ 3 allowed

> **Note:** `window.speechSynthesis` is a browser API and cannot run in Node.js.
> The `speak()` helper is excluded from unit tests. Verify it manually:
> open the ASHA Tablet tab in the app, switch to **Touch-to-Hear**, tap any speaker button.

### 5.2 Backend Safety Gate (Python — engine layer)

File: [`backend/tests/test_benchmark_safety.py`](../backend/tests/test_benchmark_safety.py)

The 30-test Python safety gate confirms that the **same clinical logic** the Touch-to-Hear
panel feeds payloads into is 100% correct at the danger-sign level. All 30 pass.

```
pytest backend/tests/test_benchmark_safety.py -v
# 30 passed in 0.12s
```

### 5.3 TypeScript Build

```
npm run build
# ✓ built in 2.87s — 0 TypeScript errors
```

---

## 6. Limitations & Future Work

| Limitation | Planned Fix |
|---|---|
| Web Speech API voice quality varies by OS/browser | Pre-record Sarvam TTS audio clips (< 5 MB total) as `.webm` files, cache in Service Worker, fall back to Speech API |
| Only 3 languages (Hindi, Tamil, Bengali) | Add Kannada, Telugu, Marathi, Gujarati, Odia, Punjabi |
| No persistence to IndexedDB outbox | Wire the triage result to `saveOfflineCase()` so it syncs when connectivity returns |
| No age-appropriate fast-breathing threshold | Expose age group in the tile to let the engine use neonate/infant/child thresholds |

---

*SwaraSetu is a prototype decision-support tool. It is not a medical device and not a substitute
for professional clinical judgment.*
