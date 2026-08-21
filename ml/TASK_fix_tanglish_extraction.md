# AGENT TASK: Fix Tanglish Extraction Gaps → External Benchmark Uplift

> **Hand this file to a coding agent.** It contains everything needed to implement
> autonomously: context, evidence-backed root causes, exact interfaces, phase plan,
> regression guards, and acceptance criteria. Human review is required only at
> points marked 🔑.

---

## 1. Context

SwaraSetu triages patient speech offline via a **deterministic WHO IMCI engine**:

```
symptom_text ──► SarvamClient.extract_symptoms_rule_fallback(text, lang)  [rule NER]
                    └──► SymptomPayload ──► backend/app/triage/engine.evaluate()
                                               └──► TriageOutcome(risk_score 1|2|3)
```

The external benchmark (`ml/bench_tanglish.py`) runs this exact pipeline over all
rows of the Hugging Face dataset **Adhik6495/tanglish-medical-triage-data**
(local copy: `ml/data_tanglish_triage.csv`, 7,985 rows, Tamil script + Tanglish +
English), mapping dataset tiers → IMCI levels:

| Dataset tier | Mapped IMCI level | Support |
|---|---|---|
| `ER_NOW`     | 3 EMERGENCY_REFERRAL | 2,128 |
| `CALL_ASHA`  | 2 ASHA_DISPATCH      | 2,204 |
| `CLINIC_24H` | 2 ASHA_DISPATCH      | 1,778 |
| `HOME_CARE`  | 1 SELF_CARE          | 1,875 |

### Baseline (do not regress below these)

Run `python3 ml/bench_tanglish.py` to reproduce:

| Metric | Baseline |
|---|---|
| Mapped accuracy | 29.20% |
| Macro F1 | 25.71% |
| Critical sensitivity (ER_NOW→RED recall) | **21.19%** |
| Under-triage rate (gold RED predicted ≤2) | **78.81%** |
| Over-triage rate (gold GREEN predicted RED) | 0.32% |
| Extraction yield (≥1 flag fired) | 20.81% |
| External benchmark score | 31.95% |

Per-level precision/recall/F1: GREEN 26.4/99.6/41.7 · YELLOW 2.9/0.3/0.6 · RED 97.2/21.2/34.8.
The engine is fine — **RED precision is 97%**. The bottleneck is extraction recall.

---

## 2. Root causes (evidence-backed)

Token frequencies below are from the dataset itself (count of tier rows containing token).

### RC1 — Missing Tanglish keyword variants in the rule extractor
File: `backend/app/services/sarvam_client.py` → `extract_symptoms_rule_fallback()`.

| Payload field | Currently matched (subset) | MISSING variants seen in data (hits) |
|---|---|---|
| `chest_pain_severe` | "chest pain", "marbu vali", "seene me dard" | **nenju vali** (nenju=85 in ER_NOW), "chestpain" |
| `has_fever` | "fever", "kaichal", "bukhar", "jwor" | **juram**, "jwaram" |
| `convulsions` | "convulsion", "valippu", "daura" | **fits**, "fit vanthuchu" |
| `unconscious` | "mayakkam", "unconscious", "ogyan" | **fainted** (89), **fainting** (73), "vizhunthutanga", "vizhunthen" |
| `difficulty_breathing` | "breath", "moochu", "saans" | "breathing difficulty" (56), "heavy breathing", "moochu kashdum", "moochu vida mudiyala", "moochu sari illa" |
| `vomiting_blood` | "vomit blood", "rakthavanthi" | "blood vanthi", "vanthi blood", "raktham vanthi". ⚠️ **NEVER map "rathiri" here — it means "night" ("rathiri irundhu vomiting" = vomiting *since last night*), NOT blood.** |
| `unable_to_drink_or_breastfeed` | (no keywords at all) | "not drinking milk", "pal kudikala", "baby not drinking" |
| `rash_with_fever` | (no keywords at all) | "rash" (co-occurring with fever) |
| `diarrhoea` | "loose motion", "dast", "bedhi" | "loose motions", "stools" |
| `severe_headache` (maternal) | none | "thala vali", "headache", "talai vali" — only meaningful when `pregnant` |

Because these miss, most rows extract nothing → payload defaults → predicted GREEN.

### RC2 — Negation blindness (hurts GREEN precision)
Naive substring matching fires on negations: *"my mother has **no fever** just tiredness"* → `has_fever=True`. Negated cues appear in HOME_CARE ("no fever", "fever illa", "paravaala", "sari ayiducha").

### RC3 — No code path for advice/supply requests (caps accuracy at ~72.5%)
`CALL_ASHA` rows (27.6% of data) are questions like *"baby ku iron syrup epo"*,
*"calcium venum"*, *"when is nxt vaccination"*. Top tokens: tablet(204), when(186),
epo(166), iron(123), enna(122), venum(112), calcium(110), vitamin(68), medicine(66).
These are **non-symptom intents** that should dispatch an ASHA worker (level 2),
but `SymptomPayload` cannot express them, so they always predict GREEN.

### RC4 — Demographic signals unused
`pregnant`(86–89 hits/tier), relatives (paati/thatha/amma/husband/wife → adult;
baby/payyan/ponnu/son/daughter → child). Setting `pregnant=True` unlocks maternal
cluster rules (e.g., severe_headache → YELLOW, convulsions/vaginal_bleeding → RED);
age band fixes fast-breathing thresholds.

### RC5 — Severity/intensity modifiers ignored
HOME_CARE markers: light(401), mild(372), slight(118), konjam(109), saadharana(59).
Strong markers in ER_NOW: severe(184), sudden(141), high(103), continuous(92),
romba(87), nonstop/thudarchiya/repeat. Without them, CLINIC_24H vs ER_NOW within
the same symptom family is indistinguishable, and "continuous vomiting" (plain
`vanthi`) has no safe mapping path.

---

## 3. Ground rules (hard constraints)

1. **Determinism**: pure functions only. Same input ⇒ byte-identical output. No randomness, time, network, LLM, API keys.
2. **Offline stdlib-only**: no new dependencies anywhere.
3. **Safety-first direction**: over-triage is tolerable, under-triage is not. Never downgrade an existing risk path.
4. **Do NOT touch**: `ml/data_tanglish_triage.csv`, `TIER_TO_LEVEL` mapping, metric computation in `ml/bench_tanglish.py`, or anything under `ml/data/`.
5. **No memorization**: do not hardcode full dataset sentences or near-exact matches. Generalizable keyword families/transliteration variants only (they transfer to real users).
6. **Script hygiene**: `ml/benchmark.py bench_source()` audits string literals for mixed Indic scripts. Add Tanglish keywords in Latin script; never mix scripts inside one literal. This check must stay clean.
7. **Existing suites must stay green**: every case in `ml/benchmark.py` (31 clinical + 21 extraction + determinism 100%) must pass unchanged. You may only *append* new cases.
8. Repo style: minimal comments unless documenting clinical rationale (see existing code).

---

## 4. Deliverables

```
backend/app/services/sarvam_client.py   # MODIFIED — keyword expansion, negation, severity gating, intent+detection
backend/app/triage/types.py             # MODIFIED — new payload fields (Phase 3/5)
backend/app/triage/clusters.py          # MODIFIED — adhoc-request finding (Phase 3)
backend/app/triage/messages.py          # MODIFIED — rationale keys in ALL languages (Phase 3)
ml/benchmark.py                         # MODIFIED — append EXTRACTION_CASES for every new keyword family
ml/tanglish_report.html                 # REGENERATED
/tmp or ml/reports/tanglish_before_after.md  # NEW — before/after metrics summary
```

Work loop: implement one phase → run verification (§6) → inspect misses → next phase.

Error-analysis helper (mine the residual misses yourself):

```bash
python3 ml/bench_tanglish.py --json > /tmp/opencode/tanglish.json
python3 - <<'EOF'
import json, collections, re
d = json.load(open('/tmp/opencode/tanglish.json'))
c = collections.Counter()
for m in d['miss_examples']:
    if m['kind'] == 'under':
        for w in re.findall(r"[a-z]{3,}", m['text'].lower()): c[w] += 1
print(c.most_common(40))
EOF
```

---

## 5. Implementation phases (execute in order)

### Phase 1 — Keyword expansion (biggest win, zero risk)
Edit the keyword lists in `extract_symptoms_rule_fallback()` per the RC1 table.
Notes:
- Match against both `lower` and `raw` exactly as the current code does.
- Word-boundary care: prefer substring lists that can't false-hit (e.g., `"fits"` also
  matches "benefits" — acceptable here, but note it; do NOT add bare `"fit"`).
- `rash_with_fever`: set only when a rash cue **and** a fever cue both fired.
- `severe_headache`: set whenever headache cues fire; the maternal cluster already
  gates on `pregnant` internally — so also do Phase 4.

### Phase 2 — Negation guard (targeted, not global)
Skip firing a flag when a negator occurs within a small token window **before** the cue:
negators = `no, not, illa, illai, illame, paravaala, ledu, without`.
- Apply ONLY to: `has_fever`, `cough_days`, `diarrhoea`, `chest_pain_severe`, `unconscious`.
- Exception: for `unable_to_drink_or_breastfeed`, "not drinking / kudikala" IS the
  positive cue — never negation-guard that field.
- Implement as a small deterministic helper (tokenize once per call, check window ≤3 tokens).

### Phase 3 — 🔑 Advice/supply intent → ASHA dispatch (engine extension; product decision)
Makes `CALL_ASHA` reachable. Max-risk aggregation keeps all RED paths dominant.
1. `types.py`: add field `advice_request: bool = False` to `SymptomPayload` (keep frozen dataclass; defaults preserve all existing behavior).
2. `sarvam_client.py`: set `advice_request=True` when the text contains supply/advice cues:
   `venum, veendum, epo, eppo, eppavum, when, enna, what, which, tablet, syrup, tonic,
   iron, calcium, vitamin, folic acid, zinc, vaccination, vaccine, immunization, camp,
   diet, medicine, marunthu, oil, cream, weight` — combined with question/request framing
   (`?`, or any of the interrogatives above). Require BOTH a supply noun and request framing
   to avoid firing on statements like "chest pain bad".
3. `clusters.py`: add `evaluate_adhoc(p)` to `_PIPELINE`:
   ```python
   def evaluate_adhoc(p):
       if p.advice_request:
           return ClusterFinding(cluster="general",
                                 risk_score=RiskScore.ASHA_DISPATCH,
                                 rationale_keys=("adhoc_supply_request",))
       return ClusterFinding(cluster="general", risk_score=RiskScore.SELF_CARE, matched=False)
   ```
4. `messages.py`: add rationale key `"adhoc_supply_request"` to RATIONALE for **all four
   locales** (en/hi/ta/bn), e.g., EN: "Supply or advisory request — ASHA follow-up scheduled."
   Actions resolve automatically via `_actions_for(RiskScore.ASHA_DISPATCH, ...)`.

🔑 **STOP for human approval before merging Phase 3** (extends IMCI engine semantics beyond pure symptoms). Phases 1–2 stand alone.

### Phase 4 — Demographics
- `pregnant=True` on: `pregnant, pregnancy, garbhini, karpini, karpam` (+ "expecting").
- `age_group`: `AGE_ADULT` for `paati, thatha, amma, appa, husband, wife, mother, father,
  akka, anna, grandmother, grandfather, grandma, grandpa`; keep default child for
  `baby, payyan, ponnu, son, daughter, child, kid`. Do not override an explicitly set group.

### Phase 5 — Severity gating (safe escalation only)
- Define `STRONG = {severe, romba, mosama, mosam, heavy, continuous, thudarchiya,
  nonstop, repeat, thirumb, serious, high, sudden, bad}`.
- Map plain vomiting cues (`vanthi, vomiting, vamathal`) to `vomiting_everything=True`
  **only when** a STRONG modifier co-occurs in the sentence (IMCI "vomits everything"
  is a RED danger sign; ungated mapping would flood RED and destroy over-triage).
- Diarrhoea + nonstop/continuous → `stool_frequency_per_day=10` **only if** you first
  confirm in `clusters.py` + tests what frequency alone yields (never guess a level change).
- Mild markers (`light, mild, slight, konjam, saadharana`) do NOT downgrade existing
  engine paths in this phase (constraint #3); they only suppress *new* aggressive mappings
  introduced above (e.g., no vomiting_everything when "mild vomiting").

### Phase 6 — Lock in regressions
Append to `EXTRACTION_CASES` in `ml/benchmark.py` (one per new family), e.g.:
```python
{"lang": "ta", "text": "en payyanuku fits vanthuchu",        "field": "convulsions",              "expected": True},
{"lang": "ta", "text": "en amma juram romba irukku",         "field": "has_fever",                "expected": True},
{"lang": "ta", "text": "en appaku nenju vali udane vanga",   "field": "chest_pain_severe",        "expected": True},
{"lang": "ta", "text": "en ponnu fainted ippo",              "field": "unconscious",              "expected": True},
{"lang": "ta", "text": "en paati ku rathiri irundhu vomiting","field": "advice_request",          "expected": False},
{"lang": "ta", "text": "baby ku iron syrup epo kudukkanum",  "field": "advice_request",           "expected": True},
```

---

## 6. Verification (run after EVERY phase)

```bash
# 1. Existing suites — must stay green
python3 ml/benchmark.py            # clinical 100%, extraction >= baseline, determinism 100%

# 2. Backend tests (if deps available; else rely on harnesses)
python3 -m pytest backend/tests -q || true

# 3. The external benchmark
python3 ml/bench_tanglish.py
python3 ml/bench_tanglish.py --html ml/tanglish_report.html

# 4. Dashboard visual check
python3 ml/serve_benchmark.py      # http://localhost:7860 — Section 5 updates
```

## 7. Acceptance criteria

Minimum (all required):

| Metric | Baseline | Required |
|---|---|---|
| Critical sensitivity (ER_NOW→RED) | 21.19% | **≥ 70%** |
| Under-triage rate | 78.81% | **≤ 30%** |
| Mapped accuracy | 29.20% | **≥ 45%** |
| Macro F1 | 25.71% | **≥ 40%** |
| Extraction yield | 20.81% | **≥ 50%** |
| Over-triage rate (guard) | 0.32% | **≤ 15%** |
| `ml/benchmark.py` clinical / determinism | 100% / 100% | unchanged |
| Mixed-script defects | 0 | 0 |

Stretch (expected if Phase 3 lands): accuracy ≥ 60%, critical sensitivity ≥ 85%,
score ≥ 70%. Known ceiling: breathing-difficulty-without-red-flag rows gold-labeled
ER_NOW predict YELLOW by design (IMCI ladder) — document them, don't hack around.

Final step: write `ml/reports/tanglish_before_after.md` with the two scorecards side
by side and a 5-line changelog of keyword families added. 🔑 Human sign-off on metrics.
