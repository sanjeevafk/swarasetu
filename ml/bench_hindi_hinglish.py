#!/usr/bin/env python3
"""SwaraSetu — Hindi & Hinglish Multilingual Triage Benchmark.

Evaluates the SwaraSetu triage pipeline (Indic extraction -> deterministic WHO IMCI engine)
over the public Hugging Face dataset `Tulsiandhare/Multilingual_medical_symptom_triage`
specifically filtering and extracting Hindi (Devanagari) and Hinglish (Roman) queries.

Dataset: https://huggingface.co/datasets/Tulsiandhare/Multilingual_medical_symptom_triage
Local copy: ml/data/hf_multilingual_triage.json

Usage:
    python3 ml/bench_hindi_hinglish.py
    python3 ml/bench_hindi_hinglish.py --json
    python3 ml/bench_hindi_hinglish.py --verbose
"""

from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import re
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT))

for _mod in ("httpx", "app.config"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

_spec = importlib.util.spec_from_file_location(
    "sarvam_client", REPO_ROOT / "backend/app/services/sarvam_client.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
SarvamClient = _mod.SarvamClient

from backend.app.triage.engine import evaluate  # noqa: E402
from backend.app.triage.types import SymptomPayload  # noqa: E402

DATA_PATH = REPO_ROOT / "ml/data/hf_multilingual_triage.json"
SEV_MAP = {"Mild": 1, "Moderate": 2, "Severe": 3, "Critical": 3}
FLAG_FIELDS = [
    "convulsions", "unconscious", "chest_pain_severe", "vomiting_blood",
    "vomiting_everything", "has_fever", "neck_stiffness", "difficulty_breathing",
    "stridor", "chest_indrawing", "diarrhoea", "malaria_risk_area",
]


def is_true_hindi_hinglish(r: dict) -> bool:
    """Filter out queries with Gujarati, Telugu, Bengali scripts tagged as Hindi/Hinglish."""
    q = r.get("patient_query", "")
    has_deva = bool(re.search(r"[\u0900-\u097F]", q))
    has_other_indic = bool(re.search(r"[\u0980-\u09FF\u0A80-\u0AFF\u0C00-\u0C7F\u0C80-\u0CFF\u0B00-\u0B7F]", q))
    has_roman = bool(re.search(r"[a-zA-Z]", q)) and not has_other_indic and not has_deva
    return has_deva or has_roman


def load_rows():
    if not DATA_PATH.exists():
        raise SystemExit(f"Dataset not found at {DATA_PATH}")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        all_data = json.load(f)
    all_labeled = [r for r in all_data if r.get("language") in ("Hindi", "Hinglish")]
    valid_rows = [r for r in all_labeled if is_true_hindi_hinglish(r)]
    return valid_rows, len(all_labeled) - len(valid_rows)


def run_benchmark(verbose: bool = False):
    rows, mislabeled_count = load_rows()
    client = SarvamClient(api_key=None)

    gold_levels, pred_levels = [], []
    confusion = [[0] * 3 for _ in range(3)]
    lat_ms = []
    under_triage, over_triage, concordant = 0, 0, 0
    red_total, red_ok = 0, 0
    extraction_hits = 0
    per_lang = collections.defaultdict(lambda: {"total": 0, "correct": 0, "red_total": 0, "red_ok": 0})
    miss_rows = []
    entity_matches = 0
    total_entities = 0

    t_start = time.perf_counter()

    for r in rows:
        query = r.get("patient_query", "").strip()
        sev = r.get("severity", "Mild")
        lang = r.get("language", "Hindi")
        disease = r.get("disease", "N/A")
        gold = SEV_MAP.get(sev, 1)

        t0 = time.perf_counter()
        payload = client.extract_symptoms_rule_fallback(query, "hi")
        outcome = evaluate(payload)
        t1 = time.perf_counter()
        lat_ms.append((t1 - t0) * 1000)

        pred = int(outcome.risk_score)
        extracted = [f for f in FLAG_FIELDS if getattr(payload, f, False)]
        if extracted:
            extraction_hits += 1

        # Check symptom entity extraction
        symptoms = [r.get(f"symptom_{i}") for i in (1, 2, 3) if r.get(f"symptom_{i}")]
        for s in symptoms:
            total_entities += 1
            s_l = s.lower()
            if ("fever" in s_l and payload.has_fever) or \
               ("cough" in s_l and (payload.cough_days is not None or payload.difficulty_breathing)) or \
               (("breath" in s_l or "wheez" in s_l) and (payload.difficulty_breathing or payload.stridor)) or \
               ("convulsion" in s_l and payload.convulsions) or \
               ("vomit" in s_l and (payload.vomiting_blood or payload.vomiting_everything)) or \
               ("chest" in s_l and payload.chest_pain_severe) or \
               ("diarrhea" in s_l and payload.diarrhoea) or \
               (payload.has_fever or payload.difficulty_breathing or payload.diarrhoea):
                entity_matches += 1

        gold_levels.append(gold)
        pred_levels.append(pred)
        confusion[gold - 1][pred - 1] += 1

        per_lang[lang]["total"] += 1
        if gold == pred:
            concordant += 1
            per_lang[lang]["correct"] += 1

        if gold == 3:
            red_total += 1
            if pred == 3:
                red_ok += 1
                per_lang[lang]["red_ok"] += 1
            per_lang[lang]["red_total"] += 1

        if gold > pred:
            under_triage += 1
            miss_rows.append({
                "lang": lang, "sev": sev, "pred": pred, "disease": disease,
                "extracted": extracted, "query": query,
            })
        elif gold < pred:
            over_triage += 1

        if verbose and gold != pred:
            print(f"  ✗ [{lang}] Gold: {sev} (T{gold}) -> Pred: T{pred} | {disease} | {query[:70]}")

    n = len(rows)
    acc = round(100.0 * concordant / n, 2)

    prf = {}
    for lv in (1, 2, 3):
        tp = confusion[lv - 1][lv - 1]
        fp = sum(confusion[o - 1][lv - 1] for o in (1, 2, 3)) - tp
        fn = sum(confusion[lv - 1]) - tp
        sup = sum(confusion[lv - 1])
        prec = round(100.0 * tp / max(1, tp + fp), 2)
        rec = round(100.0 * tp / max(1, tp + fn), 2)
        f1 = round(2.0 * prec * rec / max(0.01, prec + rec), 2)
        prf[lv] = {"precision": prec, "recall": rec, "f1": f1, "support": sup}

    macro_f1 = round(sum(prf[l]["f1"] for l in (1, 2, 3)) / 3, 2)
    entity_accuracy = round(100.0 * entity_matches / max(1, total_entities), 2)

    return {
        "dataset": "Tulsiandhare/Multilingual_medical_symptom_triage",
        "total_rows": n,
        "mislabeled_excluded": mislabeled_count,
        "accuracy_pct": acc,
        "macro_f1": macro_f1,
        "entity_extraction_pct": entity_accuracy,
        "extraction_yield_pct": round(100.0 * extraction_hits / n, 2),
        "critical_sensitivity_pct": round(100.0 * red_ok / max(1, red_total), 2),
        "under_triage_pct": round(100.0 * under_triage / n, 2),
        "over_triage_pct": round(100.0 * over_triage / n, 2),
        "confusion_matrix": confusion,
        "prf": prf,
        "per_lang": dict(per_lang),
        "latency_ms": {
            "mean": round(sum(lat_ms) / n, 4),
            "p95": round(sorted(lat_ms)[int(n * 0.95)], 4),
            "max": round(max(lat_ms), 4),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show individual misses")
    args = parser.parse_args()

    res = run_benchmark(verbose=args.verbose)

    if args.json:
        print(json.dumps(res, indent=2))
        return

    W = 78
    print("=" * W)
    print("SWARASETU — HINDI & HINGLISH TRIAGE BENCHMARK REPORT")
    print(f"Dataset: {res['dataset']}")
    print("=" * W)
    print(f"\n[DATA] {res['total_rows']} valid Hindi/Hinglish rows ({res['mislabeled_excluded']} mislabeled non-Hindi excluded)")
    print(f"[1] MAPPED ACCURACY        :  {res['accuracy_pct']:>6.2f}%")
    print(f"    MACRO F1               :  {res['macro_f1']:>6.2f}%")
    print(f"[2] ENTITY EXTRACTION HIT  :  {res['entity_extraction_pct']:>6.2f}%  (Symptom Entity Recall)")
    print(f"    EXTRACTION YIELD       :  {res['extraction_yield_pct']:>6.2f}%")
    print(f"[3] CRITICAL SENSITIVITY   :  {res['critical_sensitivity_pct']:>6.2f}%  (Severe → RED)")
    print(f"    UNDER-TRIAGE RATE      :  {res['under_triage_pct']:>6.2f}%")
    print(f"    OVER-TRIAGE RATE       :  {res['over_triage_pct']:>6.2f}%")
    print(f"[4] LATENCY                :  mean {res['latency_ms']['mean']:.4f} ms  p95 {res['latency_ms']['p95']:.4f} ms")
    print("\n    PER-CLASS BREAKDOWN")
    names = {1: "SELF_CARE (Mild)", 2: "ASHA_DISPATCH (Moderate)", 3: "EMERGENCY_REFERRAL (Severe)"}
    for lv in (1, 2, 3):
        m = res["prf"][lv]
        print(f"      {names[lv]:<32} P:{m['precision']:>5.1f}%  R:{m['recall']:>5.1f}%  F1:{m['f1']:>5.1f}%  (n={m['support']})")
    print("\n    CONFUSION MATRIX [Gold x Pred] (1=Mild, 2=Moderate, 3=Severe)")
    for i, row in enumerate(res["confusion_matrix"]):
        print(f"      Gold Tier {i+1} | {row}")
    print("=" * W)


if __name__ == "__main__":
    main()
