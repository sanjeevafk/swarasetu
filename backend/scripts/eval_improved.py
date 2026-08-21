#!/usr/bin/env python3
"""Evaluate the improved experiment with the SAME pipeline as the baseline.

Reuses verbatim from the baseline evaluation (backend/scripts/eval_baseline.py):
  - SCORE_TO_LABEL / CLASSES / prf()  -> identical metric definitions
  - map_ground_truth                  -> identical GT mapping (benchmark_protocols)
The only difference is the decision function: trained text classifier instead of
the deterministic IMCI engine. Benchmark: triage_protocols_structured.json (2251).
"""

from __future__ import annotations

import json
import pickle
import sys
import time
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "scripts"))

from eval_baseline import CLASSES, SCORE_TO_LABEL, prf  # noqa: E402  (baseline metric code)
from benchmark_protocols import map_ground_truth        # noqa: E402  (same GT mapping)

CONFIG_PATH = REPO_ROOT / "configs" / "experiment_improved.yaml"
import yaml  # noqa: E402


def main() -> int:
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    ckpt_path = REPO_ROOT / cfg["outputs"]["checkpoint"]
    report_path = REPO_ROOT / cfg["outputs"]["report"]
    bench_path = REPO_ROOT / cfg["evaluation"]["benchmark_dataset"]

    if not ckpt_path.exists():
        print(f"FATAL: checkpoint missing ({ckpt_path}). Run backend/scripts/train_improved.py first.")
        return 1

    with open(ckpt_path, "rb") as f:
        bundle = pickle.load(f)
    model = bundle["pipeline"]

    cases = json.loads(bench_path.read_text(encoding="utf-8"))
    n = len(cases)

    cm = {t: {p: 0 for p in CLASSES} for t in CLASSES}
    start = time.perf_counter()
    for item in cases:
        inp = item.get("input", {})
        text = inp.get("formatted_input") or inp.get("presentation_english") or ""
        gt_label = SCORE_TO_LABEL[map_ground_truth(item.get("output", {}).get("triage_level", ""))]
        pred_label = model.predict([text])[0]
        cm[gt_label][pred_label] += 1
    elapsed = time.perf_counter() - start

    supports = {c: sum(cm[c].values()) for c in CLASSES}
    total = sum(supports.values())
    per_class = {}
    for c in CLASSES:
        tp = cm[c][c]
        fp = sum(cm[o][c] for o in CLASSES if o != c)
        fn = supports[c] - tp
        p, r, f1 = prf(tp, fp, fn)
        per_class[c] = {"precision": p, "recall": r, "f1_score": f1, "support": supports[c],
                        "tp": tp, "fp": fp, "fn": fn}

    correct = sum(cm[c][c] for c in CLASSES)
    accuracy = round(correct / total, 6)
    macro_precision = round(sum(per_class[c]["precision"] for c in CLASSES) / len(CLASSES), 6)
    macro_recall = round(sum(per_class[c]["recall"] for c in CLASSES) / len(CLASSES), 6)
    macro_f1 = round(sum(per_class[c]["f1_score"] for c in CLASSES) / len(CLASSES), 6)
    weighted_f1 = round(sum(per_class[c]["f1_score"] * supports[c] for c in CLASSES) / total, 6)

    training_meta_path = REPO_ROOT / cfg["outputs"]["training_config"]
    hashes_path = REPO_ROOT / cfg["outputs"]["dataset_hashes"]
    training_meta = json.loads(training_meta_path.read_text()) if training_meta_path.exists() else {}
    dataset_hashes = json.loads(hashes_path.read_text()) if hashes_path.exists() else {}

    metrics = {
        "metadata": {
            "dataset": bench_path.name,
            "num_cases": n,
            "model": f"experiment_improved_{cfg['experiment']['version']} "
                     f"(tfidf_logreg seed={bundle['seed']}) — NOT the IMCI engine",
            "evaluation_pipeline": "identical to baseline (eval_baseline.prf + benchmark_protocols.map_ground_truth)",
            "label_mapping": {"ground_truth_RED": "HIGH", "ground_truth_YELLOW": "MEDIUM",
                              "ground_truth_GREEN_or_BLACK": "LOW"},
            "training_config": training_meta.get("experiment"),
            "training_datasets_sha256": {k: v["sha256"] for k, v in dataset_hashes.items()},
            "internal_holdout_accuracy": (training_meta.get("internal_holdout") or {}).get("accuracy"),
            "evaluation_latency_seconds": round(elapsed, 3),
            "generated_by": "backend/scripts/eval_improved.py",
        },
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "per_class": per_class,
        "high_risk_recall": per_class["HIGH"]["recall"],
        "high_to_low_errors": cm["HIGH"]["LOW"],
        "high_to_medium_errors": cm["HIGH"]["MEDIUM"],
        "confusion_matrix": {"order_rows_true_cols_pred": list(CLASSES), "matrix": cm},
    }
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"Evaluated {n:,} cases in {elapsed:.2f}s\n")
    print(f"Accuracy          : {accuracy*100:.2f}% ({correct}/{total})")
    print(f"Macro Precision   : {macro_precision:.4f}")
    print(f"Macro Recall      : {macro_recall:.4f}")
    print(f"Macro F1          : {macro_f1:.4f}")
    print(f"Weighted F1       : {weighted_f1:.4f}\n")
    print(f"{'class':<8}{'prec':>8}{'rec':>8}{'f1':>8}{'support':>9}")
    for c in CLASSES:
        pc = per_class[c]
        print(f"{c:<8}{pc['precision']:>8.4f}{pc['recall']:>8.4f}{pc['f1_score']:>8.4f}{pc['support']:>9}")
    print(f"\nHIGH-risk recall      : {per_class['HIGH']['recall']*100:.2f}%")
    print(f"HIGH -> LOW errors    : {cm['HIGH']['LOW']}")
    print(f"HIGH -> MEDIUM errors : {cm['HIGH']['MEDIUM']}")
    print("\nConfusion matrix (rows=true, cols=pred):")
    print("        " + "".join(f"{c:>9}" for c in CLASSES))
    for t in CLASSES:
        print(f"{t:<8}" + "".join(f"{cm[t][p]:>9}" for p in CLASSES))

    base = REPO_ROOT / "reports" / "baseline_metrics.json"
    if base.exists():
        b = json.loads(base.read_text())
        print("\n--- vs baseline (deterministic IMCI engine) ---")
        for k in ("accuracy", "macro_f1", "weighted_f1"):
            print(f"{k:<16}: baseline {b[k]:.4f} | improved {metrics[k]:.4f}")
        print(f"{'high_risk_recall':<16}: baseline {b['high_risk_recall']:.4f} | improved {metrics['high_risk_recall']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
