#!/usr/bin/env python3
"""Compare baseline vs improved on the SAME held-out benchmark (no retraining).

Reads reports/baseline_metrics.json and reports/improved_metrics.json, verifies
they were computed on the identical test set, then writes:
    reports/before_after.csv
    reports/before_after.png
Deltas are computed honestly; regressions are labelled as regressions.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "reports"

METRICS = [
    ("Accuracy", "accuracy", "rate"),
    ("Macro F1", "macro_f1", "rate"),
    ("HIGH Precision", ("per_class", "HIGH", "precision"), "rate"),
    ("HIGH Recall", "high_risk_recall", "rate"),
    ("HIGH F1", ("per_class", "HIGH", "f1_score"), "rate"),
    ("HIGH -> LOW errors", "high_to_low_errors", "count_lower_better"),
    ("HIGH -> MEDIUM errors", "high_to_medium_errors", "count_lower_better"),
]


def dig(d, path):
    for k in path:
        d = d[k]
    return d


def main() -> int:
    b = json.loads((REPORTS / "baseline_metrics.json").read_text())
    i = json.loads((REPORTS / "improved_metrics.json").read_text())

    # ---- guard: identical held-out set -------------------------------------
    if b["metadata"]["dataset"] != i["metadata"]["dataset"]:
        print("FATAL: different benchmark datasets:", b["metadata"]["dataset"], "vs", i["metadata"]["dataset"])
        return 2
    if b["metadata"]["num_cases"] != i["metadata"]["num_cases"]:
        print("FATAL: different case counts:", b["metadata"]["num_cases"], "vs", i["metadata"]["num_cases"])
        return 2
    cm_b = json.dumps(b["confusion_matrix"]["matrix"], sort_keys=True)
    tot_b = sum(sum(r.values()) for r in b["confusion_matrix"]["matrix"].values())
    tot_i = sum(sum(r.values()) for r in i["confusion_matrix"]["matrix"].values())
    assert tot_b == tot_i == b["metadata"]["num_cases"], "confusion matrix total mismatch"

    rows = []
    for label, key, kind in METRICS:
        bv = dig(b, key) if isinstance(key, tuple) else b[key]
        iv = dig(i, key) if isinstance(key, tuple) else i[key]
        delta = iv - bv
        if kind == "rate":
            better = "improved" if delta > 1e-9 else ("regressed" if delta < -1e-9 else "unchanged")
        else:  # errors: lower is better
            better = "improved" if delta < 0 else ("regressed" if delta > 0 else "unchanged")
        rows.append({
            "metric": label,
            "baseline": round(bv, 6),
            "improved": round(iv, 6),
            "delta_improved_minus_baseline": round(delta, 6),
            "verdict": better,
            "note": "" ,
        })
    rows[5]["note"] = "error counts: lower is better"
    rows[6]["note"] = "error counts: lower is better"

    with open(REPORTS / "before_after.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "baseline", "improved",
                                          "delta_improved_minus_baseline", "verdict", "note"])
        w.writeheader()
        w.writerows(rows)

    render_png(b, i, rows)

    print(f"{'Metric':<24}{'Baseline':>12}{'Improved':>12}{'Delta':>12}  Verdict")
    for r in rows:
        print(f"{r['metric']:<24}{r['baseline']:>12.4f}{r['improved']:>12.4f}{r['delta_improved_minus_baseline']:>12.4f}  {r['verdict']}")
    print(f"\nTest set: {b['metadata']['dataset']} ({b['metadata']['num_cases']} cases) — identical for both models.")
    return 0


def render_png(b, i, rows):
    from PIL import Image, ImageDraw, ImageFont

    rates = [r for r in rows if r["note"] == ""]
    counts = [r for r in rows if r["note"] != ""]

    W, H = 1180, 560
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    try:
        f_t = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        f_l = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
        f_v = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
    except OSError:
        f_t = f_l = f_v = ImageFont.load_default()

    BLUE, ORANGE, GRID = (52, 110, 189), (232, 119, 34), (220, 224, 230)
    d.text((30, 16), "Baseline vs Improved — same held-out benchmark (triage_protocols_structured.json, 2,251 cases)",
           font=f_t, fill="black")

    # ---- left panel: rate metrics (%) ---------------------------------------
    px0, py0, pw, ph = 70, 90, 600, 360
    maxv = max(max(r["baseline"], r["improved"]) for r in rates) * 1.25
    for gy in range(6):
        y = py0 + ph - gy * ph / 5
        d.line([px0, y, px0 + pw, y], fill=GRID)
        d.text((10, y - 7), f"{maxv*gy/5*100:.0f}%", font=f_l, fill="#555")
    bw = pw / len(rates) / 3
    for idx, r in enumerate(rates):
        x = px0 + idx * pw / len(rates) + bw * 0.5
        for j, (val, col) in enumerate(((r["baseline"], BLUE), (r["improved"], ORANGE))):
            hgt = ph * val / maxv
            d.rectangle([x + j * bw, py0 + ph - hgt, x + (j + 1) * bw, py0 + ph], fill=col)
            d.text((x + j * bw + 2, py0 + ph - hgt - 16), f"{val:.3f}", font=f_v,
                   fill=(col))
        lbl = r["metric"].replace("HIGH ", "H").replace(" Precision", "P").replace(" Recall", "R").replace(" Macro F1", "F1")
        d.text((x - 6, py0 + ph + 8), lbl[:11], font=f_l, fill="black")
    d.line([px0, py0, px0, py0 + ph], fill="black")

    lx, ly = px0, py0 + ph + 34
    d.rectangle([lx, ly, lx + 14, ly + 14], fill=BLUE);  d.text((lx + 20, ly), "Baseline (deterministic IMCI engine)", font=f_l, fill="black")
    d.rectangle([lx, ly + 22, lx + 14, ly + 36], fill=ORANGE); d.text((lx + 20, ly + 22), "Improved (TF-IDF + LogReg, seed 42)", font=f_l, fill="black")

    # ---- right panel: error counts -------------------------------------------
    qx, qy, qw, qh = 760, 90, 340, 240
    maxc = max(max(r["baseline"], r["improved"]) for r in counts) * 1.25
    for gy in range(5):
        y = qy + qh - gy * qh / 4
        d.line([qx, y, qx + qw, y], fill=GRID)
        d.text((qx - 42, y - 7), f"{maxc*gy/4:.0f}", font=f_l, fill="#555")
    cw = qw / len(counts) / 3
    for idx, r in enumerate(counts):
        x = qx + idx * qw / len(counts) + cw * 0.5
        for j, (val, col) in enumerate(((r["baseline"], BLUE), (r["improved"], ORANGE))):
            hgt = qh * val / maxc
            d.rectangle([x + j * cw, qy + qh - hgt, x + (j + 1) * cw, qy + qh], fill=col)
            d.text((x + j * cw, qy + qh - hgt - 16), str(int(val)), font=f_v, fill=(col))
        d.text((x - 10, qy + qh + 8), r["metric"].replace("HIGH -> ", "H→").replace(" errors", ""), font=f_l, fill="black")
    d.line([qx, qy, qx, qy + qh], fill="black")
    d.text((qx - 40, qy - 26), "Safety-critical error counts (lower = better)", font=f_l, fill="#333")

    d.text((30, H - 46), "Verdicts are computed automatically: rate metrics higher=better; error counts lower=better.", font=f_l, fill="#333")
    d.text((30, H - 26), "NOT clinically validated. Improved model trained only on synthetic public data; see registry.", font=f_l, fill="#a33")
    img.save(REPORTS / "before_after.png")


if __name__ == "__main__":
    raise SystemExit(main())
