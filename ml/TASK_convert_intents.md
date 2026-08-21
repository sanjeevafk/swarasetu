# AGENT TASK: First-Aid Intents Dataset → Triage Fixture Converter

> **Hand this file to a coding agent.** It contains everything needed to implement
> autonomously: context, exact interfaces, file specs, clinical mapping rules,
> and verification steps. Human review is required only at the points marked 🔑.

---

## 1. Context

SwaraSetu is an offline-first voice triage assistant. Its core is a **deterministic
WHO IMCI engine** at `backend/app/triage/`:

```
SymptomPayload (structured fields) ──► engine.evaluate() ──► TriageOutcome
                                                              ├─ risk_score: 1|2|3
                                                              ├─ primary_cluster: general|fever|respiratory|diarrhoea|maternal|none
                                                              └─ red_flags / actions / rationale_keys
```

Current test coverage (`backend/tests/test_imci_engine.py`) is hand-written and thin.
We want to convert the Kaggle **First Aid Intents dataset**
(https://www.kaggle.com/datasets/mahmoudahmed6/first-aid-intents-dataset) into:

1. **Executable regression fixtures** for the triage engine, and
2. **A coverage audit** showing which real-world conditions our engine has NO path for.

**Explicitly NOT a goal:** using the dataset's English `responses` strings as
user-facing replies. SwaraSetu replies come exclusively from IMCI-derived localized
messages. Do not wire dataset responses into any runtime code path.

---

## 2. Deliverables (file tree)

```
ml/
├── TASK_convert_intents.md            # this file (already exists)
├── convert_intents.py                 # NEW — converter script (stdlib only)
├── data/
│   └── intents.json                   # NEW — raw Kaggle input (committed)
└── reports/
    └── tag_coverage.md                # GENERATED — coverage audit (committed)

backend/
├── tests/
│   ├── fixtures/
│   │   └── triage_cases.json          # GENERATED — committed
│   └── test_triage_fixtures.py        # NEW — parametrized test consumer
```

---

## 3. Step A — Acquire input data

Try, in order:

```bash
kaggle datasets download -d mahmoudahmed6/first-aid-intents-dataset \
  -p ml/data --unzip
mv ml/data/intents.json ml/data/intents.json  # keep canonical name; delete other extracted files
```

If the `kaggle` CLI is unavailable or lacks credentials (likely — needs
`~/.kaggle/kaggle.json`):

1. Create `ml/data/intents.json` with the documented schema below, populated with
   the ~46 known tags (see §6 seed list).
2. Emit a loud warning in your final summary: `🔑 HUMAN ACTION REQUIRED: download
   the real dataset from Kaggle and replace ml/data/intents.json`.

**Input schema** (top-level key is `"root"` in the original file — normalize for it):

```json
{
  "root": {
    "intents": [
      { "tag": "Snake Bite",
        "patterns": ["How do you treat a snake bite?", "..."],
        "responses": ["Keep calm..."] }
    ]
  }
}
```

Handle BOTH `{"root": {...}}` and bare `{"intents": [...]}` shapes defensively.

---

## 4. Step B — `ml/convert_intents.py`

Stdlib only (`argparse`, `json`, `pathlib`). Python 3.11. Match repo style:
module docstring at top, sparse inline comments, type hints.

### 4.1 Core mapping table (the heart of the script)

```python
from backend.app.triage.types import (
    AGE_ADULT, AGE_CHILD, AGE_INFANT,
)  # add repo root to sys.path like backend/conftest.py does

# Category semantics:
#   MAPPED          -> tag converts to fixture cases (cluster/risk/payload below)
#   GAP_EMERGENCY   -> real emergency condition, engine has NO evaluator for it.
#                      Goes to coverage report as a finding. NEVER fabricate
#                      engine behaviour for these.
#   OUT_OF_SCOPE    -> minor first-aid condition intentionally unsupported.
#                      Documented in report, no fixture.
TAG_MAP: dict[str, dict] = {
    "fever": {
        "category": "MAPPED",
        "cases": [
            {"expect_payload": {"age_group": AGE_CHILD, "has_fever": True, "fever_days": 2},
             "expect_cluster": "fever", "expect_risk_score": 1},
            {"expect_payload": {"age_group": AGE_CHILD, "has_fever": True, "fever_days": 8},
             "expect_cluster": "fever", "expect_risk_score": 2},
        ],
    },
    "diarrhea": {
        "category": "MAPPED",
        "cases": [
            {"expect_payload": {"age_group": AGE_CHILD, "diarrhoea": True,
                                "blood_in_stool": True},
             "expect_cluster": "diarrhoea", "expect_risk_score": 2},
        ],
    },
    "cough": {
        "category": "MAPPED",
        "cases": [
            {"expect_payload": {"age_group": AGE_ADULT, "cough_days": 20},
             "expect_cluster": "respiratory", "expect_risk_score": 2},
        ],
    },
    "seizure": {
        "category": "MAPPED",
        "cases": [
            {"expect_payload": {"age_group": AGE_CHILD, "convulsions": True},
             "expect_cluster": "general", "expect_risk_score": 3},
        ],
    },
    "snake_bite":     {"category": "GAP_EMERGENCY"},
    "choking":        {"category": "GAP_EMERGENCY"},
    "poison":         {"category": "GAP_EMERGENCY"},
    "head_injury":    {"category": "GAP_EMERGENCY"},
    "nose_bleeding":  {"category": "GAP_EMERGENCY"},   # no epistaxis field in payload
    "sprain":         {"category": "OUT_OF_SCOPE"},
    "splinter":       {"category": "OUT_OF_SCOPE"},
    # ... one entry per dataset tag. See §6 for the full tag inventory.
}

# Symptom-style patient utterances per tag (NOT the dataset's question patterns).
# 2–4 per mapped tag; include at least one Hinglish variant where natural.
UTTERANCE_TEMPLATES: dict[str, list[str]] = {
    "fever": [
        "my child has had fever since two days",
        "bachhe ko bukhar hai do din se",
        "body is burning hot since last night",
    ],
    "seizure": [
        "my father suddenly fell and his body started shaking violently",
        "daura pad gaya jhatke aa rahe hain",
    ],
    # ...
}

UNMAPPED_DEFAULT = "OUT_OF_SCOPE"  # tags found in data but absent from TAG_MAP land here
```

### 4.2 Pipeline (functions, in order)

1. `load_intents(path) -> list[dict]` — read JSON, normalize both container shapes,
   normalize tags: `tag.lower().strip().replace(" ", "_").replace("-", "_")`.
2. `build_cases(intents) -> tuple[list[dict], list[dict]]` — returns `(cases, findings)`:
   - For each `MAPPED` tag × each template × each case-spec → one fixture record:
     ```json
     {
       "id": "fever_0",
       "tag": "fever",
       "utterance": "my child has had fever since two days",
       "expect_payload": {"age_group": "child", "has_fever": true, "fever_days": 2},
       "expect_cluster": "fever",
       "expect_risk_score": 1,
       "source": "kaggle:first-aid-intents"
     }
     ```
     Cycle templates across case-specs; `id` = `{tag}_{index}`.
   - Every `GAP_EMERGENCY` / `OUT_OF_SCOPE` tag → a finding row.
   - Tags present in data but missing from `TAG_MAP` → `UNMAPPED_DEFAULT` finding row.
3. `verify_cases(cases) -> list[str]` — **self-check against the live engine.**
   Import `backend.app.triage.evaluate` and `SymptomPayload`; for each case run
   `evaluate(SymptomPayload(**case["expect_payload"]))` and assert:
   `int(outcome.risk_score) == case["expect_risk_score"]` and
   `outcome.primary_cluster == case["expect_cluster"]`.
   Return mismatch descriptions. This prevents shipping clinically wrong expectations.
4. `write_report(findings, mismatches, stats) -> None` — emits `ml/reports/tag_coverage.md`
   (format in §7).
5. `main()` — argparse with:
   - `--data PATH` (default `ml/data/intents.json`)
   - `--check-only` : load existing fixture file, re-run verification, exit non-zero on drift
   - default: build → verify → if mismatches exist, print them and exit 1 WITHOUT writing
     fixtures → else write `backend/tests/fixtures/triage_cases.json` + report.

### 4.3 Payload-field safety rule

`SymptomPayload` is a frozen dataclass — unknown kwargs raise `TypeError`. That is
the safety net: **the converter may only reference fields that exist in
`backend/app/triage/types.py`** (`has_fever`, `fever_days`, `cough_days`,
`difficulty_breathing`, `breathing_rate_per_min`, `chest_indrawing`, `stridor`,
`wheezing`, `chest_pain_severe`, `vomiting_blood`, `diarrhoea`,
`stool_frequency_per_day`, `blood_in_stool`, `sunken_eyes`, `skin_pinch_slow`,
`restless_irritable`, `convulsions`, `unconscious`, `unable_to_drink_or_breastfeed`,
`vomiting_everything`, `neck_stiffness`, `rash_with_fever`, `malaria_risk_area`,
`temperature_c`, `severe_headache`, `blurred_vision`, `vaginal_bleeding`,
`reduced_fetal_movement`, `pregnant`, `age_group`). If a condition has no matching
field, it MUST be `GAP_EMERGENCY` or `OUT_OF_SCOPE` — never invent a field.

---

## 5. Step C — `backend/tests/test_triage_fixtures.py`

Follow the import convention of `test_imci_engine.py` (sys.path insert, then
`from backend.app.triage import ...`). Full intended shape:

```python
"""Fixture-driven regression tests for the IMCI engine.

Cases are generated by ml/convert_intents.py from the Kaggle first-aid
intents dataset. Regenerate with: python ml/convert_intents.py
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.triage import SymptomPayload, evaluate  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "triage_cases.json"
CASES = json.loads(FIXTURES.read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_kaggle_intent_case(case):
    payload = SymptomPayload(**case["expect_payload"])
    outcome = evaluate(payload)
    assert int(outcome.risk_score) == case["expect_risk_score"], (
        f"{case['id']}: expected risk {case['expect_risk_score']}, "
        f"got {int(outcome.risk_score)}"
    )
    assert outcome.primary_cluster == case["expect_cluster"], (
        f"{case['id']}: expected cluster '{case['expect_cluster']}', "
        f"got '{outcome.primary_cluster}'"
    )
```

Add a guard test: fixture file exists and has ≥ 10 cases (fails loudly if someone
deletes the generated artifacts).

---

## 6. Clinical mapping rules + tag inventory

Dataset contains ~46 tags. Known inventory (normalize spellings to these keys):
`cuts, abrasions, stings, splinter, sprain, strain, fever, nasal_congestion, cough,
sore_throat, gas_problems, skin_allergy, abdominal_pain, bruises, broken_toe,
choking, wound_care, diarrhea, frost_bite, heat_exhaustion, heat_stroke,
insect_bite, nose_bleeding, pulled_muscle, rectal_bleeding, sunburn, testicle_pain,
vertigo, bleeding, eye_injury, chemical_burn, poison, broken_teeth, seizure,
head_injury, faint, headache, cold_sores, rashes, snake_bite`.

Rules for filling `TAG_MAP`:

1. **Conservative by default.** Only classify `MAPPED` when you can name the exact
   `SymptomPayload` fields AND the engine's expected behaviour is confirmed by the
   built-in verifier. When unsure → `GAP_EMERGENCY` (if plausibly serious) or
   `OUT_OF_SCOPE`.
2. **Do not force-fit.** e.g. `nose_bleeding` ≠ `vomiting_blood` (haematemesis);
   `faint` ≈ `unconscious` only if you document the approximation in the report;
   `headache` alone maps nowhere unless `pregnant` + `severe_headache`.
3. **Maternal variants welcome.** For any tag, adding one extra `pregnant=True`
   case is encouraged (e.g., fever in pregnancy).
4. Seed ~8–12 `MAPPED` tags minimum across all five clusters so the fixture file
   exercises every evaluator.
5. Every `GAP_EMERGENCY` entry must appear in the final report as a numbered
   finding — this audit output is a deliverable, not a byproduct.

---

## 7. Coverage report format (`ml/reports/tag_coverage.md`)

Generated, deterministic, tables only. Sections:

```markdown
# IMCI Coverage Audit vs Kaggle First-Aid Intents Dataset
_Generated by ml/convert_intents.py — do not edit by hand._

## Summary
| Metric | Count |
|---|---|
| Dataset tags | 40 |
| MAPPED (fixtures emitted) | 11 |
| GAP_EMERGENCY (no engine path) | 9 |
| OUT_OF_SCOPE | 20 |
| Fixture cases written | 34 |
| Verification mismatches | 0 |

## Emergency coverage gaps  ← action items for maintainers
| # | Tag | Example utterances | Suggested disposition |
|---|-----|--------------------|-----------------------|
| 1 | snake_bite | "a snake bit my leg" | Add animal_bite red flag → Score 3 |
...

## Out of scope
| Tag | Rationale |
...

## Mapped matrix
| Tag | Cases | Clusters exercised | Risk tiers |
...
```

---

## 8. Verification checklist (agent MUST run all of these)

```bash
cd /home/lildosa/Project/swarasetu
python ml/convert_intents.py                     # exits 0; writes fixture + report
python ml/convert_intents.py --check-only        # idempotent re-verification
python -m pytest backend/tests/test_triage_fixtures.py -v      # all pass
python -m pytest backend/tests/test_imci_engine.py -v          # pre-existing tests still pass
python -m pytest backend/tests -q                              # whole suite green
```

All must pass before declaring done. If `pytest` isn't installed, install
backend deps first (`pip install -r backend/requirements.txt`) or report the blocker.

---

## 9. Constraints

- Stdlib only for the converter; **no new dependencies** without explicit approval.
- Do not modify anything under `backend/app/` — this task adds tests + tooling only.
- Never let dataset `responses` strings reach runtime/user-facing code.
- Commit generated artifacts (`triage_cases.json`, `tag_coverage.md`) — CI relies on them.
- Match existing repo style: module docstrings, minimal inline comments, type hints.

## 10. Out of scope (do NOT build now)

- Fallback intent classifier training (`ml/fallback_classifier.py`) — separate task.
- Multilingual utterance expansion beyond a few Hinglish samples.
- Any NER integration — fixtures currently bypass NER and test engine logic only.
  (Later flip: swap `SymptomPayload(**expect_payload)` for real NER extraction of
  `utterance`, turning the same fixtures into a full-pipeline benchmark.)

## 11. 🔑 Human review gates

1. **Clinical sign-off of `TAG_MAP`** — especially every `expect_risk_score`.
2. **Kaggle license check** before committing `ml/data/intents.json`.
3. **Gap dispositions** in the coverage report (accept vs defer each GAP_EMERGENCY).
