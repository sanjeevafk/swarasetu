#!/usr/bin/env python3
"""Baseline evaluation of the existing SwaraSetu pipeline.

Runs the UNMODIFIED pipeline exactly as it stands today:
  dataset   : triage_protocols_structured.json  (repo root)
  adapter   : benchmark_protocols.parse_vitals_and_symptoms  (verbatim reuse)
  gt mapping: benchmark_protocols.map_ground_truth            (verbatim reuse)
  model     : app.triage.engine.evaluate                      (deterministic IMCI)

Outputs (reports/):
  baseline_metrics.json
  baseline_classification_report.csv
  baseline_confusion_matrix.png

Label convention: engine risk 1 -> LOW, 2 -> MEDIUM, 3 -> HIGH.
NOTE: the existing map_ground_truth maps BLACK cases to SELF_CARE(=LOW);
this baseline preserves that behaviour unchanged.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
SCRIPTS_DIR = BACKEND_DIR / "scripts"
REPORTS_DIR = REPO_ROOT / "reports"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

from benchmark_protocols import map_ground_truth, parse_vitals_and_symptoms  # noqa: E402
from app.triage.engine import evaluate  # noqa: E402

CLASSES = ("HIGH", "MEDIUM", "LOW")
SCORE_TO_LABEL = {3: "HIGH", 2: "MEDIUM", 1: "LOW"}


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return round(precision, 6), round(recall, 6), round(f1, 6)


def render_confusion_png(matrix: dict[str, dict[str, int]], out: Path, accuracy: float, macro_f1: float) -> None:
    from PIL import Image, ImageDraw, ImageFont

    order = ["HIGH", "MEDIUM", "LOW"]  # display order: worst first
    cell, pad, left_w, top_h = 150, 12, 190, 110
    width = left_w + pad + cell * len(order) + pad
    height = top_h + pad + cell * len(order) + 120
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    try:
        f_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        f_head = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        f_cell = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        f_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except OSError:
        f_title = f_head = f_cell = f_small = ImageFont.load_default()

    d.text((pad, 18), "SwaraSetu Baseline Confusion Matrix (IMCI engine)", font=f_title, fill="black")

    max_count = max(
        matrix[t][p] for t in order for p in order
    ) or 1

    # Column headers (predicted)
    for j, p in enumerate(order):
        x = left_w + pad + j * cell
        d.text((x + cell // 2 - 40, top_h - 34), f"pred {p}", font=f_head, fill="black")
        d.rectangle([x, top_h, x + cell, height - 130], outline="#444", width=2)
    # Row headers (true) + cells
    total_high_errors = matrix["HIGH"]["LOW"] + matrix["HIGH"]["MEDIUM"]
    for i, t in enumerate(order):
        y = top_h + pad + i * cell
        d.text((10, y + cell // 2 - 12), f"true {t}", font=f_head, fill="black")
        for j, p in enumerate(order):
            x = left_w + pad + j * cell
            v = matrix[t][p]
            shade = int(245 - 200 * (v / max_count))
            diag = t == p
            color = (shade if not diag else min(shade, 210), 255 if not diag else min(shade, 240), shade if not diag else 160)
            d.rectangle([x + 2, y + 2, x + cell - 4, y + cell - 4], fill=color, outline="#999")
            pct = v / sum(matrix[t].values()) if any(matrix[t].values()) else 0.0
            d.text((x + cell // 2 - 26, y + cell // 2 - 24), str(v), font=f_cell, fill="black")
            d.text((x + cell // 2 - 30, y + cell // 2 + 8), f"{pct*100:.1f}%", font=f_small, fill="#333")

    y0 = height - 118
    d.text((pad, y0), f"Accuracy: {accuracy*100:.2f}%    Macro F1: {macro_f1:.4f}", font=f_head, fill="black")
    d.text((pad, y0 + 28), f"HIGH-risk recall: {prf(matrix['HIGH']['HIGH'], sum(matrix[o]['HIGH'] for o in order if o != 'HIGH'), matrix['HIGH']['MEDIUM'] + matrix['HIGH']['LOW'])[1]*100:.2f}%", font=f_small, fill="black")
    d.text((pad, y0 + 50), f"HIGH->LOW errors: {matrix['HIGH']['LOW']}    HIGH->MEDIUM errors: {matrix['HIGH']['MEDIUM']}    total HIGH misses: {total_high_errors}", font=f_small, fill="black")
    d.text((pad, y0 + 72), "Rows = ground truth, columns = predicted. Counts + row percentage.", font=f_small, fill="#555")
    img.save(out)


def main() -> int:
    dataset_path = REPO_ROOT / "triage_protocols_structured.json"
    if not dataset_path.exists():
        print(f"FATAL: dataset missing: {dataset_path}")
        return 1
    REPORTS_DIR.mkdir(exist_ok=True)

    cases = json.loads(dataset_path.read_text(encoding="utf-8"))
    n = len(cases)

    cm = {t: {p: 0 for p in CLASSES} for t in CLASSES}
    start = time.perf_counter()
    unmapped_gt = Counter()
    errors: list[dict] = []

    for item in cases:
        out_obj = item.get("output") or {}
        gt_label = SCORE_TO_LABEL[map_ground_truth(out_obj.get("triage_level", ""))]
        payload = parse_vitals_and_symptoms(item)
        pred_label = SCORE_TO_LABEL[int(evaluate(payload).risk_score)]
        cm[gt_label][pred_label] += 1
        if gt_label == "HIGH" and pred_label != "HIGH":
            errors.append({"id": item.get("id"), "gt": gt_label, "pred": pred_label,
                           "condition": out_obj.get("suspected_condition", "")})
        if str(out_obj.get("triage_level", "")).upper().startswith("BLACK"):
            unmapped_gt["BLACK->LOW (existing map_ground_truth behaviour)"] += 1
    elapsed = time.perf_counter() - start

    # ---- per-class stats -------------------------------------------------
    supports = {c: sum(cm[c].values()) for c in CLASSES}
    total = sum(supports.values())
    per_class: dict[str, dict] = {}
    for c in CLASSES:
        tp = cm[c][c]
        fp = sum(cm[o][c] for o in CLASSES if o != c)
        fn = supports[c] - tp
        p, r, f = prf(tp, fp, fn)
        per_class[c] = {"precision": p, "recall": r, "f1_score": f, "support": supports[c],
                        "tp": tp, "fp": fp, "fn": fn}

    correct = sum(cm[c][c] for c in CLASSES)
    accuracy = round(correct / total, 6)
    macro_precision = round(sum(per_class[c]["precision"] for c in CLASSES) / len(CLASSES), 6)
    macro_recall = round(sum(per_class[c]["recall"] for c in CLASSES) / len(CLASSES), 6)
    macro_f1 = round(sum(per_class[c]["f1_score"] for c in CLASSES) / len(CLASSES), 6)
    weighted_f1 = round(sum(per_class[c]["f1_score"] * supports[c] for c in CLASSES) / total, 6)

    high_recall = per_class["HIGH"]["recall"]
    high_to_low = cm["HIGH"]["LOW"]
    high_to_med = cm["HIGH"]["MEDIUM"]

    metrics = {
        "metadata": {
            "dataset": "triage_protocols_structured.json",
            "num_cases": n,
            "model": "deterministic WHO IMCI engine (backend/app/triage/engine.py @ "
                     + __import__("subprocess").check_output(
                         ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"]).decode().strip() + ")",
            "adapter": "benchmark_protocols.parse_vitals_and_symptoms + map_ground_truth (unmodified)",
            "label_mapping": {"engine_risk_1": "LOW", "engine_risk_2": "MEDIUM",
                              "engine_risk_3": "HIGH",
                              "ground_truth_RED": "HIGH", "ground_truth_YELLOW": "MEDIUM",
                              "ground_truth_GREEN": "LOW"},
            "notes": sorted(unmapped_gt.keys()),
            "evaluation_latency_seconds": round(elapsed, 3),
            "generated_by": "backend/scripts/eval_baseline.py",
        },
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "per_class": per_class,
        "high_risk_recall": high_recall,
        "high_to_low_errors": high_to_low,
        "high_to_medium_errors": high_to_med,
        "confusion_matrix": {
            "order_rows_true_cols_pred": list(CLASSES),
            "matrix": cm,
        },
    }
    (REPORTS_DIR / "baseline_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    # ---- CSV report ------------------------------------------------------
    with open(REPORTS_DIR / "baseline_classification_report.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["class", "precision", "recall", "f1_score", "support"])
        for c in CLASSES:
            pc = per_class[c]
            w.writerow([c, pc["precision"], pc["recall"], pc["f1_score"], pc["support"]])
        w.writerow(["macro_avg", macro_precision, macro_recall, macro_f1, total])
        w.writerow(["weighted_avg", "", "", weighted_f1, total])
        w.writerow(["accuracy", "", "", accuracy, total])
        w.writerow(["high_risk_recall", "", "", high_recall, supports["HIGH"]])
        w.writerow(["high_to_low_errors", "", "", high_to_low, supports["HIGH"]])
        w.writerow(["high_to_medium_errors", "", "", high_to_med, supports["HIGH"]])

    render_confusion_png(cm, REPORTS_DIR / "baseline_confusion_matrix.png", accuracy, macro_f1)

    # ---- console summary -------------------------------------------------
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
    print(f"\nHIGH-risk recall      : {high_recall*100:.2f}%")
    print(f"HIGH -> LOW errors    : {high_to_low}")
    print(f"HIGH -> MEDIUM errors : {high_to_med}")
    print("\nConfusion matrix (rows=true, cols=pred):")
    print("        " + "".join(f"{c:>9}" for c in CLASSES))
    for t in CLASSES:
        print(f"{t:<8}" + "".join(f"{cm[t][p]:>9}" for p in CLASSES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
