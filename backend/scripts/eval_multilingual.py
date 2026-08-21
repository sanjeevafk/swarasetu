#!/usr/bin/env python3
"""Multilingual evaluation -> reports/language_benchmark.csv

Honesty rules:
 - only languages/subsets with actually available labelled data get numbers;
   everything else is an explicit N/A row;
 - Tulsiandhare slices are IN-SAMPLE for the improved model (it was trained on
   the whole CSV) and are labelled `in_sample` — they are NOT validation results;
 - the internal 2251-case English benchmark is `held_out`.
"""

from __future__ import annotations

import csv
import json
import pickle
import sys
import time
from collections import Counter
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "scripts"))

from eval_baseline import CLASSES, prf                    # noqa: E402
from app.triage.engine import evaluate as imci_evaluate    # noqa: E402
from app.services.sarvam_client import sarvam_client       # noqa: E402

SCORE_TO_LABEL = {1: "LOW", 2: "MEDIUM", 3: "HIGH"}
OUT = REPO_ROOT / "reports" / "language_benchmark.csv"


def metrics(preds, gts):
    pairs = [(p, g) for p, g in zip(preds, gts) if p is not None]
    n_err = sum(1 for p in preds if p is None)
    if not pairs:
        return {}
    per = {}
    for c in CLASSES:
        tp = sum(1 for p, g in pairs if p == c and g == c)
        fp = sum(1 for p, g in pairs if p == c and g != c)
        fn = sum(1 for p, g in pairs if p != c and g == c)
        _, rec, f1 = prf(tp, fp, fn)
        per[c] = (rec, f1)
    return {
        "n_cases": len(pairs),
        "accuracy": round(sum(1 for p, g in pairs if p == g) / len(pairs), 6),
        "macro_f1": round(sum(v[1] for v in per.values()) / len(CLASSES), 6),
        "high_recall": per["HIGH"][0],
        "high_support": sum(1 for _, g in pairs if g == "HIGH"),
        "high_to_low_errors": sum(1 for p, g in pairs if g == "HIGH" and p == "LOW"),
        "inference_errors": n_err,
    }


def run_improved(model, texts):
    t0 = time.perf_counter()
    preds = list(model.predict(texts))
    return preds, round(time.perf_counter() - t0, 2)


def run_imci(texts, lang):
    preds, t0 = [], time.perf_counter()
    for text in texts:
        try:
            payload = sarvam_client.extract_symptoms_rule_fallback(text, language=lang)
            preds.append(SCORE_TO_LABEL[int(imci_evaluate(payload).risk_score)])
        except Exception:
            preds.append(None)
    return preds, round(time.perf_counter() - t0, 2)


def na_row(subset, reason):
    return {"language_subset": subset, "dataset": "", "evaluation_type": "",
            "model": "", "n_cases": 0, "accuracy": "N/A", "macro_f1": "N/A",
            "high_recall": "N/A", "high_support": 0, "high_to_low_errors": "N/A",
            "inference_errors": "", "latency_seconds": "", "notes": reason}


def main() -> int:
    rows = []

    # ---- held-out internal English benchmark ---------------------------------
    bench = json.loads((REPO_ROOT / "triage_protocols_structured.json").read_text())
    from benchmark_protocols import map_ground_truth
    texts_b = [c["input"].get("formatted_input", "") for c in bench]
    gts_b = [SCORE_TO_LABEL[map_ground_truth(c.get("output", {}).get("triage_level", ""))] for c in bench]

    cfg = yaml.safe_load((REPO_ROOT / "configs" / "experiment_improved.yaml").read_text())
    ckpt = REPO_ROOT / cfg["outputs"]["checkpoint"]
    model = pickle.loads(ckpt.read_bytes())["pipeline"] if ckpt.exists() else None

    # baseline on benchmark: reuse recorded baseline_metrics.json instead of recompute
    bmet = json.loads((REPO_ROOT / "reports" / "baseline_metrics.json").read_text())
    pc = bmet["per_class"]
    cm = bmet["confusion_matrix"]["matrix"]
    macro_f1_b = bmet["macro_f1"]
    rows.append({
        "language_subset": "english", "dataset": "swarasetu_triage_protocols_2251",
        "evaluation_type": "held_out", "model": "baseline_imci_engine",
        "n_cases": bmet["metadata"]["num_cases"], "accuracy": bmet["accuracy"],
        "macro_f1": macro_f1_b, "high_recall": pc["HIGH"]["recall"],
        "high_support": pc["HIGH"]["support"],
        "high_to_low_errors": cm["HIGH"]["LOW"], "inference_errors": 0,
        "latency_seconds": bmet["metadata"].get("evaluation_latency_seconds", ""),
        "notes": "primary benchmark; GT via legacy map_ground_truth (BLACK->LOW)"})
    if model is not None:
        imet = json.loads((REPO_ROOT / "reports" / "improved_metrics.json").read_text())
        rows.append({
            "language_subset": "english", "dataset": "swarasetu_triage_protocols_2251",
            "evaluation_type": "held_out", "model": "improved_tfidf_logreg",
            "n_cases": imet["metadata"]["num_cases"], "accuracy": imet["accuracy"],
            "macro_f1": imet["macro_f1"], "high_recall": imet["per_class"]["HIGH"]["recall"],
            "high_support": imet["per_class"]["HIGH"]["support"],
            "high_to_low_errors": imet["confusion_matrix"]["matrix"]["HIGH"]["LOW"],
            "inference_errors": 0,
            "latency_seconds": imet["metadata"].get("evaluation_latency_seconds", ""),
            "notes": "same held-out set as baseline"})

    # ---- Tulsiandhare language slices (IN-SAMPLE for improved) ---------------
    import pandas as pd
    csv_path = REPO_ROOT / "data/external/multilingual_medical_symptom_triage.csv"
    df = pd.read_csv(csv_path, usecols=["patient_query", "urgency", "language_tag"], dtype=str).dropna()
    label_map = {"Low": "LOW", "Medium": "MEDIUM", "High": "HIGH"}
    lang_names = {"en": "english", "hi": "hindi", "hi-en": "code_mixed"}
    lang_ner = {"en": "en", "hi": "hi", "hi-en": "hi"}

    for tag in ("en", "hi", "hi-en"):
        sub = df[df["language_tag"] == tag]
        texts = sub["patient_query"].tolist()
        gts = [label_map[u.strip()] for u in sub["urgency"]]
        note = "SYNTHETIC public dataset; IN-SAMPLE for improved model (trained on full CSV)"
        if model is not None:
            preds, lat = run_improved(model, texts)
            m = metrics(preds, gts)
            rows.append({"language_subset": lang_names[tag], "dataset":
                         "tulsiandhare_multilingual_medical_symptom_triage",
                         "evaluation_type": "in_sample", "model": "improved_tfidf_logreg",
                         **m, "latency_seconds": lat, "notes": note})
        preds, lat = run_imci(texts, lang_ner[tag])
        m = metrics(preds, gts)
        rows.append({"language_subset": lang_names[tag], "dataset":
                     "tulsiandhare_multilingual_medical_symptom_triage",
                     "evaluation_type": "unseen_for_imci", "model": "baseline_imci_engine_via_rule_ner",
                     **m, "latency_seconds": lat,
                     "notes": "SYNTHETIC public dataset; engine sees text via production rule-NER fallback"})

    # ---- explicit N/A rows: no usable labelled data ---------------------------
    for subset, reason in [
        ("tamil", "no labelled triage data in repo (engine output localization exists, no test corpus)"),
        ("telugu", "no labelled triage data in repo"),
        ("kannada", "no labelled triage data in repo"),
        ("malayalam", "no labelled triade data in repo".replace("triade", "triage")),
        ("marathi", "Marathi-script rows exist inside Tulsiandhare 'hi-en' tag but are NOT reliably labelled as marathi -> excluded pending re-tagging"),
        ("bengali", "only quarantined banglish file (provenance undocumented, training/testing disallowed by registry)"),
        ("transliteration", "banglish transliteration data quarantined (registry: local_bengali_banglish_triage)"),
    ]:
        rows.append(na_row(subset, reason))

    fieldnames = ["language_subset", "dataset", "evaluation_type", "model", "n_cases",
                  "accuracy", "macro_f1", "high_recall", "high_support",
                  "high_to_low_errors", "inference_errors", "latency_seconds", "notes"]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"wrote {OUT} ({len(rows)} rows)\n")
    for r in rows:
        acc = r.get("accuracy", "")
        hi = r.get("high_recall", "")
        hl = r.get("high_to_low_errors", "")
        print(f"{r['language_subset']:<12} {r['evaluation_type']:<16} {str(r['model'])[:32]:<32} "
              f"n={r.get('n_cases','')!s:<5} acc={acc!s:<8} macF1={r.get('macro_f1','')!s:<8} "
              f"HIrec={hi!s:<8} H->L={hl!s:<4} {r['notes'][:48]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
