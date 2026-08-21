# AGENT TASK: Fix Benchmark Errors & Unify Multilingual Clinical Triage

> **Hand this file to a coding agent.** It contains everything needed to autonomously
> diagnose, fix, and verify all benchmark defects in SwaraSetu: exact root causes,
> line numbers, clinical decision tree fixes, keyword hygiene refactoring, and verification scripts.
> Zero external dependencies required.

---

## 1. Executive Summary & Diagnostic Matrix

Running `python3 ml/benchmark.py` and associated benchmark harnesses (`bench_tanglish.py`, `serve_benchmark.py`) reveals 3 specific defects:

| Defect ID | Component | Location | Symptom / Benchmark Error | Root Cause |
|---|---|---|---|---|
| **DEF-01** | Indic Token Hygiene & Extraction | [`backend/app/services/sarvam_client.py`](file:///home/lildosa/Project/swarasetu/backend/app/services/sarvam_client.py#L165) | `⚠ LIVE DEFECT: Line 165: ['deva', 'taml'] -> 'कாய்ச்சல்'`<br>`✗ [ta] has_fever: got False` | Mixed-script token: Devanagari `क` (U+0915) prepended to Tamil `ாய்ச்சல்`. Tamil queries never match. |
| **DEF-02** | WHO IMCI Primary Cluster Resolution | [`backend/app/triage/engine.py`](file:///home/lildosa/Project/swarasetu/backend/app/triage/engine.py#L97-L103) | `✗ CLSTR Fever + Convulsions — Febrile Seizure: want 'fever' got 'general'`<br>`✗ CLSTR Eclampsia — Convulsions in Pregnancy: want 'maternal' got 'general'` | `_PIPELINE` evaluates `"general"` first. When `max_risk == 3`, general danger signs match convulsions and usurp specific syndromic clusters (`fever`, `maternal`). |
| **DEF-03** | Tanglish & Indic Fallback Recall | [`backend/app/services/sarvam_client.py`](file:///home/lildosa/Project/swarasetu/backend/app/services/sarvam_client.py#L154-L184) | Tanglish benchmark yield = 20.81%, Critical Sensitivity = 21.19%, Under-Triage = 78.81% | Rule fallback dictionary lacks common Romanized Tamil (Tanglish) and Indic clinical aliases (`nenju vali`, `moochu vida mudiyala`, `mayakkam`, `vanthi continuous`, `irumal`, etc.). |

---

## 2. Target Benchmark Scorecards

### Target 1: `python3 ml/benchmark.py` (Core Verification Suite)
```
==============================================================================
BENCHMARK SCORECARD
------------------------------------------------------------------------------
  Clinical Risk Accuracy         100.00%  [██████████████████████████████████████████████████]  (wt 35%)
  Score-3 Sensitivity            100.00%  [██████████████████████████████████████████████████]  (wt 25%)
  Indic Extraction Accuracy      100.00%  [██████████████████████████████████████████████████]  (wt 20%)
  Decision Determinism           100.00%  [██████████████████████████████████████████████████]  (wt 10%)
  Indic Token Hygiene            100.00%  [██████████████████████████████████████████████████]  (wt 10%)
------------------------------------------------------------------------------
  OVERALL SYSTEM SCORE           100.00%
  ✓ 0 known defects · 100% test scenario passes
==============================================================================
```

### Target 2: `python3 ml/bench_tanglish.py` (Tanglish External Benchmark)
- **Zero Syntax / Runtime Errors**
- **Critical Sensitivity (ER_NOW)**: > 85%
- **Over-Triage Control**: > 95%
- **Latency**: < 0.1ms per row

---

## 3. Step-by-Step Implementation Guide

### Step 1: Fix Indic Keyword Hygiene & Modularize Constants (DEF-01 & DEF-03)

**File:** [`backend/app/services/sarvam_client.py`](file:///home/lildosa/Project/swarasetu/backend/app/services/sarvam_client.py)

#### 1.1 Lift Keyword Dictionaries to Module-Level Constants
Extract the inline lists into explicit, single-script tuples. Ensure pure Tamil `காய்ச்சல்` (U+0B95) is used instead of the corrupt `कாய்ச்சல்`. Expand Tanglish and Indic clinical synonyms.

```python
# Danger signs
KEYWORD_CONVULSIONS: tuple[str, ...] = (
    "convulsion", "convulsions", "seizure", "seizures", "fits",
    "daura", "jhatke", "mirgi", "doure", "jhatka",
    "valippu", "valiypu", "kaal kai valippu",
    "morcha", "khinchuni",
    "दौरा", "झटके", "दौरे", "मिर्गी", "வலிப்பு", "খিঁচুনি", "মৃগীরোগ",
)

KEYWORD_UNCONSCIOUS: tuple[str, ...] = (
    "unconscious", "fainted", "fainting", "passed out", "collapsed", "blackout",
    "behosh", "behosi", "achetan", "hosh me nahi",
    "mayakkam", "mayakkam pottu", "vizhunthutanga", "thala suthi vizhunthutanga",
    "ogyan", "acheton", "behoshi",
    "बेहोश", "बेहोशी", "अचेत", "மயக்கம்", "অজ্ঞান", "অচৈতন্য",
)

KEYWORD_CHEST_PAIN: tuple[str, ...] = (
    "chest pain", "severe chest pain", "heart pain", "cardiac pain", "chest pressure",
    "seene me dard", "chhati me dard", "chaati me dard", "dil me dard",
    "nenju vali", "nenjil vali", "marbu vali", "nenju kashdum", "nenju erichal",
    "buke betha", "buker betha", "buke chap",
    "सीने में दर्द", "छाती में दर्द", "छाती में", "दिल में दर्द",
    "நெஞ்சு வலி", "மார்பு வலி", "நெஞ்சில் வலி",
    "বুকে ব্যথা", "বুকের ব্যথা",
)

KEYWORD_VOMITING_BLOOD: tuple[str, ...] = (
    "vomit blood", "vomiting blood", "blood in vomit", "haematemesis",
    "khoon ki ulti", "ulti me khoon", "rakth ulti",
    "vanthi blood", "blood vanthi", "rathavanthi", "rakthavanthi", "ratham vanthi",
    "rokto bomi", "bomite rokto", "rokter bomi",
    "खून की उल्टी", "उल्टी में खून",
    "இரத்த வாந்தி", "ரத்த வாந்தி", "வாந்தியில் ரத்தம்",
    "রক্তবমি", "বমিতে রক্ত",
)

KEYWORD_FEVER: tuple[str, ...] = (
    "fever", "high fever", "temperature", "chills", "febrile",
    "bukhar", "tez bukhar", "tap", "jor",
    "kaichal", "juram", "kayshal", "sudu", "veppam",
    "jwor", "gorom", "jar", "jhor",
    "बुखार", "तेज बुखार", "ताप",
    "காய்ச்சல்", "சுரம்", "வெப்பம்",
    "জ্বর", "তীব্র জ্বর",
)

KEYWORD_NECK_STIFFNESS: tuple[str, ...] = (
    "stiff neck", "neck stiffness", "neck rigid", "cannot bend neck",
    "gardan me akad", "gardan akadna", "gardan me dard",
    "kazhuthu vali", "kazhuthu viraipu", "kazhuthu piditham",
    "gardan sokto", "golar betha",
    "गर्दन अकड़न", "गर्दन में अकड़न", "गर्दन", "अकड़न",
    "கழுத்து விறைப்பு", "கழுத்து வலி", "கழுத்து",
    "ঘাড় শক্ত", "ঘাড়ে ব্যথা",
)

KEYWORD_RESPIRATORY_COUGH: tuple[str, ...] = (
    "cough", "coughing", "severe cough", "dry cough", "wet cough",
    "khansi", "sukhi khansi", "balgam khansi", "dhans",
    "irumal", "varattu irumal", "sali irumal", "kollu irumal",
    "kashi", "shukno kashi", "kaph kashi",
    "खांसी", "सुखी खांसी", "இருமல்", "வறட்டு இருமல்", "কাশি", "শুকনো কাশি",
)

KEYWORD_RESPIRATORY_DISTRESS: tuple[str, ...] = (
    "difficulty breathing", "breathless", "shortness of breath", "struggling to breathe", "cannot breathe", "gasping",
    "saans lene me dikkat", "saans phoolna", "dum ghutna", "saans",
    "moochu vida mudiyala", "moochu thinaral", "swasam kashdum", "moochu kashdum", "moochu",
    "shash nite koshto", "dam bondho", "shashkosto", "shash",
    "सांस लेने में दिक्कत", "सांस फूलना", "सांस",
    "மூச்சு திணறல்", "மூச்சு விட முடியவில்லை", "மூச்சு",
    "শ্বাসকষ্ট", "শ্বাস নিতে পারছে না", "শ্বাস",
)

KEYWORD_CHEST_INDRAWING: tuple[str, ...] = (
    "chest indrawing", "lower chest indrawing", "ribs pulling in", "chest sinking",
    "pasli chalna", "pasli khichna", "chhati dhasna", "pasli",
    "nenju koodu ullil izhuthal", "marbu koodu",
    "panjor tana", "buker panjor", "pajor",
    "पसली चलना", "पसली", "পাঁজর ভেতরের দিকে", "পাঁজর",
)

KEYWORD_DIARRHOEA: tuple[str, ...] = (
    "diarrhea", "diarrhoea", "loose motions", "loose stools", "watery stools",
    "dast", "patla dast", "pet kharab", "loose motion", "jhada",
    "vayiṟṟuppōkku", "vayithu pokku", "vayiru pokku", "bhedhi",
    "patla paikhana", "pete oshukh", "jhara",
    "दस्त", "पतला दस्त", "पेट खराब",
    "வயிற்றுப்போக்கு", "வயிற்று வலி", "வயிற்று போக்கு",
    "ডায়রিয়া", "পাতলা পায়খানা", "পেটের অসুখ",
)
```

#### 1.2 Refactor `extract_symptoms_rule_fallback` in `SarvamClient`
Use the constant tuples and add normalized multi-word substring and token matching:

```python
    def extract_symptoms_rule_fallback(self, transcript: str, language: str = "hi") -> SymptomPayload:
        """Lightweight multilingual clinical entity extractor mapping Indic, Tanglish & English keywords."""
        raw = transcript.strip()
        lower = raw.lower()
        kwargs: dict[str, Any] = {"language": language}

        def matches_any(keywords: tuple[str, ...]) -> bool:
            return any(k in lower or k in raw for k in keywords)

        # Danger signs
        if matches_any(KEYWORD_CONVULSIONS):
            kwargs["convulsions"] = True
        if matches_any(KEYWORD_UNCONSCIOUS):
            kwargs["unconscious"] = True
        if matches_any(KEYWORD_CHEST_PAIN):
            kwargs["chest_pain_severe"] = True
        if matches_any(KEYWORD_VOMITING_BLOOD):
            kwargs["vomiting_blood"] = True

        # Fever cluster
        if matches_any(KEYWORD_FEVER):
            kwargs["has_fever"] = True
            kwargs["fever_days"] = 2
        if matches_any(KEYWORD_NECK_STIFFNESS):
            kwargs["neck_stiffness"] = True

        # Respiratory cluster
        if matches_any(KEYWORD_RESPIRATORY_COUGH):
            kwargs["cough_days"] = 2
        if matches_any(KEYWORD_RESPIRATORY_DISTRESS):
            kwargs["difficulty_breathing"] = True
        if matches_any(KEYWORD_CHEST_INDRAWING):
            kwargs["chest_indrawing"] = True

        # Diarrhoea cluster
        if matches_any(KEYWORD_DIARRHOEA):
            kwargs["diarrhoea"] = True
            kwargs["stool_frequency_per_day"] = 4

        return SymptomPayload(**kwargs)
```

---

### Step 2: Fix WHO IMCI Primary Cluster Precedence (DEF-02)

**File:** [`backend/app/triage/engine.py`](file:///home/lildosa/Project/swarasetu/backend/app/triage/engine.py)

#### 2.1 Clinical Logic
In WHO IMCI:
1. `evaluate_general_danger_signs()` flags red danger signs across the board (emergency referral).
2. However, when convulsions co-occur with `has_fever` (febrile convulsion) or `pregnant` (eclampsia), the primary syndromic cluster is clinically **`fever`** or **`maternal`**, NOT generic `"general"`.
3. If no specific cluster matches at `max_risk`, then `"general"` is selected as the primary cluster (e.g. adult chest pain, neonatal non-febrile convulsions, lethargy/unconsciousness).

#### 2.2 Patch `evaluate()` in `engine.py`

Replace lines 97–102 in [`backend/app/triage/engine.py`](file:///home/lildosa/Project/swarasetu/backend/app/triage/engine.py#L97-L103):

```python
    max_risk = max(f.risk_score for _, f in findings)
    matched_findings = [(n, f) for n, f in findings if f.matched]

    # Clinical precedence: Specific syndromic clusters (maternal, fever, resp, diarrhoea)
    # take precedence as primary_cluster when matching at max_risk over generic "general".
    specific_max = [
        (n, f) for n, f in findings
        if f.risk_score == max_risk and f.matched and n != "general"
    ]
    if specific_max:
        primary_cluster, primary_finding = specific_max[0]
    else:
        primary_cluster, primary_finding = next(
            ((n, f) for n, f in findings if f.risk_score == max_risk and f.matched),
            ("none", findings[0][1]),
        )
```

---

### Step 3: Add Automated Keyword Hygiene & Regression Tests

**File:** Create [`backend/tests/test_keyword_hygiene.py`](file:///home/lildosa/Project/swarasetu/backend/tests/test_keyword_hygiene.py)

```python
"""Automated script hygiene and keyword purity tests."""

import re
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.services.sarvam_client import (
    KEYWORD_CHEST_INDRAWING,
    KEYWORD_CHEST_PAIN,
    KEYWORD_CONVULSIONS,
    KEYWORD_DIARRHOEA,
    KEYWORD_FEVER,
    KEYWORD_NECK_STIFFNESS,
    KEYWORD_RESPIRATORY_COUGH,
    KEYWORD_RESPIRATORY_DISTRESS,
    KEYWORD_UNCONSCIOUS,
    KEYWORD_VOMITING_BLOOD,
    SarvamClient,
)

ALL_KEYWORD_LISTS = [
    ("CONVULSIONS", KEYWORD_CONVULSIONS),
    ("UNCONSCIOUS", KEYWORD_UNCONSCIOUS),
    ("CHEST_PAIN", KEYWORD_CHEST_PAIN),
    ("VOMITING_BLOOD", KEYWORD_VOMITING_BLOOD),
    ("FEVER", KEYWORD_FEVER),
    ("NECK_STIFFNESS", KEYWORD_NECK_STIFFNESS),
    ("RESPIRATORY_COUGH", KEYWORD_RESPIRATORY_COUGH),
    ("RESPIRATORY_DISTRESS", KEYWORD_RESPIRATORY_DISTRESS),
    ("CHEST_INDRAWING", KEYWORD_CHEST_INDRAWING),
    ("DIARRHOEA", KEYWORD_DIARRHOEA),
]

SCRIPTS = {
    "deva": r"[\u0900-\u097F]",
    "taml": r"[\u0B80-\u0BFF]",
    "beng": r"[\u0980-\u09FF]",
}


class TestKeywordHygiene(unittest.TestCase):
    def test_single_script_purity_across_all_keywords(self):
        """Ensure no keyword contains mixed Indic scripts (e.g. Devanagari + Tamil)."""
        defects = []
        for name, klist in ALL_KEYWORD_LISTS:
            for kw in klist:
                if len(kw.strip()) < 2:
                    continue
                hits = [sname for sname, pat in SCRIPTS.items() if re.search(pat, kw)]
                if len(hits) > 1:
                    defects.append(f"{name}: {hits} -> {kw!r}")
        self.assertEqual(defects, [], f"Found mixed-script defects: {defects}")

    def test_no_empty_keywords(self):
        for name, klist in ALL_KEYWORD_LISTS:
            for kw in klist:
                self.assertTrue(kw.strip(), f"Empty keyword in {name}")

    def test_tamil_fever_detected(self):
        """Regression test for DEF-01: Tamil fever keyword extraction."""
        client = SarvamClient(api_key=None)
        payload = client.extract_symptoms_rule_fallback(
            "என் குழந்தைக்கு இரண்டு நாட்களாக காய்ச்சல் உள்ளது", "ta"
        )
        self.assertTrue(payload.has_fever, "Tamil fever keyword 'காய்ச்சல்' failed to extract")


if __name__ == "__main__":
    unittest.main()
```

---

## 4. Verification & Validation Commands

Run the following commands from the repository root:

### 1. Verify Baseline Verification Suite
```bash
python3 ml/benchmark.py --verbose
```
**Expected Output:**
- `[0] SOURCE VERIFICATION`: `✓ No mixed-script defects`
- `[1] WHO IMCI CLINICAL ENGINE`: `100.00% (31/31)` Risk Score Accuracy, `100.00% (31/31)` Cluster Accuracy
- `[2] DETERMINISM & LOCALIZATION`: `100.00% (100 runs)`
- `[3] INDIC EXTRACTION`: `100.00% (21/21)` Accuracy, `100.00%` Token Purity
- **`OVERALL SYSTEM SCORE: 100.00%`**

### 2. Verify External Tanglish Dataset Benchmark
```bash
python3 ml/bench_tanglish.py
```

### 3. Verify Edge On-Device Latency
```bash
python3 ml/edge_runner.py --benchmark 20
```

### 4. Run Unit Test Suite
```bash
python3 -m unittest backend/tests/test_keyword_hygiene.py
```

---

## 5. Definition of Done Checklist

- [ ] All mixed-script glyph corruptions removed from `sarvam_client.py`.
- [ ] Module-level `KEYWORD_*` tuples defined with single-script validation.
- [ ] Primary cluster selection properly prioritizes specific syndromic findings over general danger signs when risk tier is tied.
- [ ] `python3 ml/benchmark.py` achieves 100.00% Overall System Score with 0 live defects.
- [ ] Standalone test script `backend/tests/test_keyword_hygiene.py` passes cleanly with `unittest`.
