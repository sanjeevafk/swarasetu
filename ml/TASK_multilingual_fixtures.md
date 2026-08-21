# AGENT TASK: Multilingual Fixture Suite — Test the Indic Extraction Layer

> **Hand this file to a coding agent.** Extends `ml/TASK_convert_intents.md`
> (read it first for context on the fixture system). While that task tests the
> engine with structured payloads, THIS task tests the layer that actually
> processes Hindi/Tamil/Bengali text: `extract_symptoms_rule_fallback()`.
>
> **Dependency:** Phase 0 is standalone. Phases 1–4 assume
> `backend/tests/fixtures/triage_cases.json` exists (base task done). If it does
> not exist yet, complete the base task first OR seed 10+ minimal cases by hand
> following its §4 schema.

---

## 1. Why this matters (context)

SwaraSetu's triage engine is language-blind — it consumes `SymptomPayload`.
Language enters exactly one place at inference time:

```
transcript (hi/ta/bn/en) ──► SarvamClient.extract_symptoms_rule_fallback()
                             (backend/app/services/sarvam_client.py)
                             ──► SymptomPayload ──► engine.evaluate()
```

This rule-based fallback is the offline Tier-2/3 path AND the confidence-fallback
path online. It has **zero test coverage today**, and it contains at least one
live defect of a class only multilingual tests can catch (see Phase 0).

---

## 2. Phase 0 — Mixed-script keyword audit & fix (standalone, do FIRST)

### 2.1 Known defect

In `extract_symptoms_rule_fallback`, the fever keyword list contains a token that
mixes Devanagari and Tamil characters (rendered roughly as `"कாய்ச்சல்"`): it
begins with Devanagari `क` (U+0915) followed by Tamil letters, where pure Tamil
`காய்ச்சல்` ("fever") is intended. Such a string can never match real Tamil input,
so **Tamil fever mentions are silently dropped**.

⚠️ Do not trust the exact glyphs in this spec — verify actual bytes at the site
before editing. Locate via:

```bash
cd /home/lildosa/Project/swarasetu
python - <<'EOF'
import re, pathlib
src = pathlib.Path("backend/app/services/sarvam_client.py").read_text()
# flag any quoted token containing characters from 2+ Indic scripts
scripts = {"deva": r"\u0900-\u097F", "taml": r"\u0B80-\u0BFF", "beng": r"\u0980-\u09FF"}
for i, line in enumerate(src.splitlines(), 1):
    for tok in re.findall(r'"([^"]*)"|\'([^\']*)\'', line):
        s = tok[0] or tok[1]
        hits = [name for name, pat in scripts.items() if re.search(pat, s)]
        if len(hits) > 1:
            print(f"{i}: {hits} -> {s!r}")
EOF
```

### 2.2 Required changes

1. **Fix every token the audit finds** (expected: the Tamil fever word; scan ALL
   keyword lists in the function, not just fever).
   Correct value: `காய்ச்சல்` (verify against a reliable source; also sanity-check
   neighbouring Tamil/Bengali keywords while you are there).
2. **Refactor for testability:** lift the inline keyword lists out of the function
   body into module-level constants with clinical names:

   ```python
   KEYWORD_DANGER_SIGNS_CONVULSIONS: tuple[str, ...] = (...)
   KEYWORD_FEVER: tuple[str, ...] = (...)
   KEYWORD_RESPIRATORY_COUGH: tuple[str, ...] = (...)
   # etc. — behaviour of extract_symptoms_rule_fallback must be byte-identical
   ```

   Pure mechanical move — no logic changes. Existing behaviour/tests must not change.
3. **Add a static hygiene test** `backend/tests/test_keyword_hygiene.py`:
   - every keyword in every `KEYWORD_*` constant is single-script (the audit
     regex above, inverted into an assertion);
   - no empty/whitespace-only keywords;
   - no duplicate keywords within or across lists.
4. **Regression test for the live bug** (add to the same file):

   ```python
   def test_tamil_fever_is_detected():
       p = SarvamClient().extract_symptoms_rule_fallback(
           "என் குழந்தைக்கு காய்ச்சல் உள்ளது", "ta")
       assert p.has_fever is True
   ```

### 2.3 Phase 0 exit criteria

```bash
python -m pytest backend/tests/test_keyword_hygiene.py -v   # green
python -m pytest backend/tests -q                           # whole suite still green
```

---

## 3. Phase 1 — Fixture schema v2 (language-keyed utterances)

Extend each record in `triage_cases.json` (converter emits this from now on):

```json
{
  "id": "fever_0",
  "tag": "fever",
  "utterances": {
    "en": "my child has had fever since two days",
    "hi": "मेरे बच्चे को दो दिन से बुखार है",
    "ta": "என் குழந்தைக்கு இரண்டு நாட்களாக காய்ச்சல் உள்ளது",
    "bn": "আমার সন্তানের দুই দিন ধরে জ্বর রয়েছে"
  },
  "assert_fields": ["has_fever"],
  "expect_payload": { "age_group": "child", "has_fever": true, "fever_days": 2 },
  "expect_cluster": "fever",
  "expect_risk_score": 1,
  "source": "kaggle:first-aid-intents"
}
```

Two new keys:

- **`utterances`** — map of BCP-47 short codes → patient-style sentence. `en` is
  the template authored in the base task; other languages are added in Phase 3.
  Keep existing top-level `utterance` as an alias of `utterances.en` during
  migration so old consumers don't break.
- **`assert_fields`** — REQUIRED for extractor tests. The rule fallback applies
  hardcoded defaults (`fever_days=2`, `stool_frequency_per_day=4`, `cough_days=2`)
  and cannot detect numeric nuance, so full-payload equality is impossible.
  Tests assert ONLY the listed fields against `expect_payload`. Choose the
  minimal set of clinically decisive fields per case (usually 1–3 booleans).
  Example: a `fever_days: 8 → risk 2` engine case asserts just `["has_fever"]`
  at the extraction layer.

Update `ml/convert_intents.py` accordingly:
- `UTTERANCE_TEMPLATES` gains per-language dicts (agent may author `hi`/`bn`
  directly; `ta` MAY be authored directly too but MUST pass the review gate in
  Phase 4);
- emit `assert_fields` from a new column in `TAG_MAP` case specs;
- keep `--check-only` semantics working against v2 records.

---

## 4. Phase 2 — Extractor test mode (offline, the core deliverable)

New file `backend/tests/test_multilingual_extraction.py`. Import conventions as
in `test_imci_engine.py`. `extract_symptoms_rule_fallback` is synchronous and
needs no API key — safe to call directly:

```python
from backend.app.services.sarvam_client import SarvamClient

EXTRACTOR = SarvamClient(api_key=None)

@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_extraction_per_language(case):
    for lang, text in case["utterances"].items():
        payload = EXTRACTOR.extract_symptoms_rule_fallback(text, lang)
        for field in case.get("assert_fields", []):
            expected = case["expect_payload"].get(field)
            assert getattr(payload, field) == expected, (
                f"{case['id']} [{lang}]: {field}={getattr(payload, field)!r}, "
                f"expected {expected!r}"
            )
```

Plus a **keyword-hit guard** per utterance — this is the assertion class that
catches missing vocabulary (including the Phase 0 bug class):

For every `(lang, text)` there must be ≥1 content word of `text` present in the
corresponding cluster's `KEYWORD_*` constant (deterministic mapping table
`tag → KEYWORD_*` defined once in the test module). If a translated utterance
shares zero keywords with its cluster list, the test fails with a message
telling the maintainer to either fix the translation or extend the keyword list.

---

## 5. Phase 3 — Translation augmentation script (`ml/augment_translations.py`)

One-time batch job. Network access required ONLY here — never in tests.

```python
# Behaviour spec (stdlib + httpx already in backend deps; reuse the client):
#   inputs : backend/tests/fixtures/triage_cases.json
#   for each case, for each target lang in --langs (default: hi ta bn):
#       skip if utterances[lang] exists (idempotent; --force overrides)
#       translated = await sarvam_client.translate_text(en_text, "en", lang)
#       tag entry with "auto": true
#   writes file back (json.dumps indent=2), prints count summary
#   rate-limit: >=0.5s sleep between API calls
```

Notes:
- `SarvamClient.translate_text` is async — run under `asyncio.run(...)`.
- If `SARVAM_API_KEY` unset, exit with clear message (do NOT silently write
  untranslated copies).
- Records marked `"auto": true` are flagged for the human review gate below;
  review flips them to `false`.

---

## 6. Phase 4 — Review gates & docs

1. 🔑 **HUMAN REVIEW of machine translations.** Clinical meaning of symptom
   sentences must survive translation. Print a side-by-side table
   (`en | hi | ta | bn`) at the end of `augment_translations.py` for review.
   Reviewed-by line appended to the report.
2. Update `ml/reports/tag_coverage.md` generation to include per-language
   coverage stats (cases having hi/ta/bn utterances).
3. Add a short section to `EVALUATION.md` → "Multilingual regression suite":
   what it tests, how to re-run augmentation, known limitations of the rule
   fallback (numeric detail like duration/count is engine-tested, not
   extraction-tested).

---

## 7. Verification checklist (ALL must pass)

```bash
cd /home/lildosa/Project/swarasetu
python ml/convert_intents.py                # regenerates v2 fixtures cleanly
python ml/convert_intents.py --check-only   # idempotent
python ml/augment_translations.py           # only with key set; else exits with message
python -m pytest backend/tests/test_keyword_hygiene.py -v
python -m pytest backend/tests/test_multilingual_extraction.py -v
python -m pytest backend/tests -q           # entire suite green
```

---

## 8. Constraints

- Phase 2 tests MUST remain fully offline (no network, no API key) — CI-safe.
- Refactor in Phase 0 is mechanical only; `extract_symptoms_rule_fallback`
  output for any given input must be unchanged (prove via existing suite +
  spot checks in the hygiene test).
- Do not touch runtime behaviour beyond the keyword fixes and the
  constants extraction. No new dependencies.
- Fixture JSON stays committed and frozen; network-derived data enters only via
  the augmentation script + human review.
- Match repo style: module docstrings, sparse comments, type hints.

## 9. Out of scope

- Real Sarvam NER end-to-end tests (Mode C) — future task behind API-key skipif.
- Expanding keyword lists for GAP_EMERGENCY conditions (snake bite, choking...)
  — those are engine gaps tracked in the base coverage report, not extraction gaps.
- Voice/ASR testing — out of scope for pytest entirely.

## 10. 🔑 Human review gates

1. Corrected Tamil/Bengali keyword spellings (Phase 0) verified by a native reader.
2. All machine-translated utterances reviewed before `"auto"` flags cleared.
3. Choice of `assert_fields` per case accepted as clinically decisive.
