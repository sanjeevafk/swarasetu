#!/usr/bin/env python3
"""SwaraSetu — Tanglish Medical Triage Dataset Benchmark.

Runs the full SwaraSetu triage pipeline (rule-based Indic NER extraction ->
deterministic WHO IMCI engine) over the public Hugging Face dataset
`Adhik6495/tanglish-medical-triage-data` and reports accuracy, per-class
precision/recall/F1, confusion matrix, clinical-safety metrics and latency.

Dataset: https://huggingface.co/datasets/Adhik6495/tanglish-medical-triage-data
Local copy expected at ml/data_tanglish_triage.csv (download with:
  curl -sL -o ml/data_tanglish_triage.csv \
    https://huggingface.co/datasets/Adhik6495/tanglish-medical-triage-data/resolve/main/full_cleaned_dataset.csv)

Tier mapping (dataset 4-tier -> SwaraSetu IMCI 3-tier):
  ER_NOW      -> 3 EMERGENCY_REFERRAL
  CALL_ASHA   -> 2 ASHA_DISPATCH
  CLINIC_24H  -> 2 ASHA_DISPATCH
  HOME_CARE   -> 1 SELF_CARE

Usage:
    python3 ml/bench_tanglish.py            # console summary
    python3 ml/bench_tanglish.py --json     # machine-readable JSON
    python3 ml/bench_tanglish.py --html out.html   # standalone single-file report
"""

from __future__ import annotations

import argparse
import collections
import csv
import importlib.util
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT))

from unittest.mock import MagicMock

for _mod in ("httpx", "app.config"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Load sarvam_client directly from its file path so the heavy backend.app.services
# package __init__ (sqlalchemy etc.) is not pulled in.
_spec = importlib.util.spec_from_file_location(
    "sarvam_client", REPO_ROOT / "backend/app/services/sarvam_client.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
SarvamClient = _mod.SarvamClient

from backend.app.triage.engine import evaluate  # noqa: E402
from backend.app.triage.types import SymptomPayload  # noqa: E402

DATASET_CSV = Path(__file__).resolve().parent / "data_tanglish_triage.csv"
DATASET_URL = "https://huggingface.co/datasets/Adhik6495/tanglish-medical-triage-data"

# Dataset tier -> canonical IMCI risk level (1..3)
TIER_TO_LEVEL = {"ER_NOW": 3, "CALL_ASHA": 2, "CLINIC_24H": 2, "HOME_CARE": 1}
LEVEL_NAMES = {1: "SELF_CARE", 2: "ASHA_DISPATCH", 3: "EMERGENCY_REFERRAL"}
LEVEL_COLORS = {1: "#22c55e", 2: "#f59e0b", 3: "#ef4444"}

# Payload fields the NER extractor can set (used to measure extraction yield).
_FLAG_FIELDS = [
    "convulsions", "unconscious", "chest_pain_severe", "vomiting_blood",
    "has_fever", "neck_stiffness", "difficulty_breathing", "chest_indrawing",
    "diarrhoea", "unable_to_drink_or_breastfeed",
]


def load_rows(path: Path = DATASET_CSV):
    if not path.exists():
        raise SystemExit(
            f"Dataset CSV not found at {path}.\nDownload it first:\n"
            f"  curl -sL -o {path}\n"
            f"    '{DATASET_URL}/resolve/main/full_cleaned_dataset.csv'"
        )
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            text = (r.get("symptom_text") or "").strip()
            tier = (r.get("risk_tier") or "").strip()
            if text and tier in TIER_TO_LEVEL:
                rows.append((text, tier))
    return rows


def _stats(vals_ms):
    s = sorted(vals_ms); n = len(s)
    return {"mean": round(sum(s) / n, 4), "p50": round(s[n // 2], 4),
            "p95": round(s[min(n - 1, int(n * .95))], 4), "max": round(s[-1], 4)}


def _pct(num, den):
    return round(100.0 * num / max(1, den), 2)


def run_benchmark(verbose=False):
    rows = load_rows()
    client = SarvamClient(api_key=None)

    gold_levels, pred_levels, tiers = [], [], []
    per_tier = collections.Counter()          # (tier, pred_level) counts
    confusion = [[0] * 3 for _ in range(3)]   # [gold][pred], levels 1..3
    lat_ms = []
    extraction_hits = 0
    miss_examples = []                        # under-/over-triage samples
    t_start = time.perf_counter()

    for i, (text, tier) in enumerate(rows):
        g = TIER_TO_LEVEL[tier]
        t0 = time.perf_counter()
        payload = client.extract_symptoms_rule_fallback(text, "ta")
        outcome = evaluate(payload)
        t1 = time.perf_counter()
        p = int(outcome.risk_score)

        if any(getattr(payload, f) for f in _FLAG_FIELDS):
            extraction_hits += 1

        gold_levels.append(g); pred_levels.append(p); tiers.append(tier)
        confusion[g - 1][p - 1] += 1
        per_tier[(tier, p)] += 1
        lat_ms.append((t1 - t0) * 1000)
        if g != p and len(miss_examples) < 400:
            miss_examples.append({
                "text": text, "tier": tier,
                "gold": LEVEL_NAMES[g], "pred": LEVEL_NAMES[p],
                "flags": [f for f in _FLAG_FIELDS if getattr(payload, f)],
                "cluster": outcome.primary_cluster,
                "kind": ("under" if g > p else "over"),
            })
        if verbose and (i + 1) % 1000 == 0:
            print(f"  … {i + 1}/{len(rows)} rows evaluated")

    wall_s = time.perf_counter() - t_start
    n = len(rows)
    correct = sum(1 for g, p in zip(gold_levels, pred_levels) if g == p)
    accuracy = _pct(correct, n)

    # Per-level precision / recall / F1
    prf = {}
    for lv in (1, 2, 3):
        tp = confusion[lv - 1][lv - 1]
        fp = sum(confusion[o - 1][lv - 1] for o in (1, 2, 3)) - tp
        fn = sum(confusion[lv - 1]) - tp
        support = sum(confusion[lv - 1])
        prec = _pct(tp, tp + fp)
        rec = _pct(tp, tp + fn)
        f1 = round(2 * prec * rec / max(1e-9, prec + rec), 2) if (prec + rec) else 0.0
        prf[lv] = {"level": LEVEL_NAMES[lv], "precision": prec, "recall": rec,
                   "f1": f1, "support": support}
    macro_f1 = round(sum(prf[lv]["f1"] for lv in (1, 2, 3)) / 3, 2)

    # Clinical safety metrics
    er_total = sum(1 for t in tiers if t == "ER_NOW")
    er_recall = _pct(per_tier[("ER_NOW", 3)], er_total)              # sensitivity on emergencies
    under_triage = _pct(confusion[2][0] + confusion[2][1], er_total)  # gold=3, pred<3
    home_total = sum(1 for t in tiers if t == "HOME_CARE")
    over_triage = _pct(confusion[0][2], home_total)                   # gold=1, pred=3

    # Per source-tier breakdown
    tier_breakdown = {}
    for tier in ("ER_NOW", "CALL_ASHA", "CLINIC_24H", "HOME_CARE"):
        total = sum(c for (t, _), c in per_tier.items() if t == tier)
        dist = {LEVEL_NAMES[lv]: _pct(per_tier[(tier, lv)], total) for lv in (1, 2, 3)}
        acc = _pct(per_tier[(tier, TIER_TO_LEVEL[tier])], total)
        tier_breakdown[tier] = {
            "support": total, "mapped_level": LEVEL_NAMES[TIER_TO_LEVEL[tier]],
            "accuracy_pct": acc, "predicted_dist_pct": dist,
        }

    # Language/script mix
    import re
    tamil_script = sum(1 for txt, _ in rows if re.search(r"[\u0B80-\u0BFF]", txt))
    lengths = sorted(len(txt) for txt, _ in rows)

    return {
        "dataset": {
            "name": "Adhik6495/tanglish-medical-triage-data",
            "url": DATASET_URL, "file": DATASET_CSV.name,
            "rows": n, "classes": dict(collections.Counter(t for _, t in rows)),
            "tamil_script_rows": tamil_script,
            "latin_rows": n - tamil_script,
            "len_mean": round(sum(lengths) / n, 1),
        },
        "mapping": {k: LEVEL_NAMES[v] for k, v in TIER_TO_LEVEL.items()},
        "accuracy_pct": accuracy, "correct": correct, "total": n,
        "macro_f1": macro_f1, "per_level": prf,
        "confusion_matrix": confusion,
        "safety": {
            "er_now_support": er_total,
            "critical_sensitivity_pct": er_recall,
            "under_triage_pct": under_triage,
            "home_care_support": home_total,
            "over_triage_pct": over_triage,
        },
        "extraction_yield_pct": _pct(extraction_hits, n),
        "latency": {
            **_stats(lat_ms),
            "wall_seconds": round(wall_s, 2),
            "rows_per_sec": round(n / wall_s, 1),
        },
        "tier_breakdown": tier_breakdown,
        "miss_examples": miss_examples,
    }


def dataset_score(res):
    """Composite score for this external benchmark (safety-weighted)."""
    weights = [
        ("Critical Sensitivity (ER_NOW recall)", res["safety"]["critical_sensitivity_pct"], 35),
        ("Overall Accuracy",                     res["accuracy_pct"],                    25),
        ("Macro F1",                             res["macro_f1"],                        20),
        ("Under-Triage Avoidance (100−miss%)",   100 - res["safety"]["under_triage_pct"], 10),
        ("Over-Triage Control (100−over%)",      100 - res["safety"]["over_triage_pct"],  10),
    ]
    score = round(sum(v * w for _, v, w in weights) / 100, 2)
    return score, weights


# ──────────────────────────────────────────────────────────────────────────────
# Standalone single-file HTML report
# ──────────────────────────────────────────────────────────────────────────────

def build_html(res) -> str:
    ds, saf, lat = res["dataset"], res["safety"], res["latency"]
    score, weights = dataset_score(res)

    def bar(pct, color="#4f8ef7"):
        return (f'<div class="bar-wrap"><div class="bar-fill" '
                f'style="width:{max(0, min(100, pct)):.2f}%;background:{color}"></div></div>')

    # Card 1 — dataset overview
    total = ds["rows"]
    tier_rows = "".join(
        f'<tr><td><span class="pill pill-{t.lower()}">{t}</span></td>'
        f'<td class="num">{c}</td><td>{bar(100 * c / total)}</td></tr>'
        for t, c in ds["classes"].items()
    )
    card_ds = f"""
    <div class="card" style="border-top:4px solid #6c63ff">
      <h2>Dataset · Tanglish Medical Triage</h2>
      <table class="tbl">
        <tr><td>Source</td><td><a href="{ds['url']}" target="_blank">{ds['name']}</a> ({ds['file']})</td></tr>
        <tr><td>Rows evaluated</td><td class="num">{total:,}</td></tr>
        <tr><td>Tamil-script rows</td><td class="num">{ds['tamil_script_rows']:,} ({100*ds['tamil_script_rows']/total:.1f}%)</td></tr>
        <tr><td>Latin-script (Tanglish/English)</td><td class="num">{ds['latin_rows']:,} ({100*ds['latin_rows']/total:.1f}%)</td></tr>
        <tr><td>Avg. symptom length</td><td class="num">{ds['len_mean']} chars</td></tr>
      </table>
      <table class="tbl tiers">
        <thead><tr><th>Risk tier</th><th>Support</th><th></th></tr></thead>
        <tbody>{tier_rows}</tbody>
      </table>
    </div>"""

    # Card 2 — headline metrics
    und_color = "#22c55e" if res["safety"]["under_triage_pct"] <= 5 else "#ef4444"
    metrics_html = f"""
    <div class="grid">
      <div class="metric"><div class="metric-val" style="color:#4f8ef7">{res['accuracy_pct']}%</div>
        <div class="metric-lbl">Mapped Accuracy<span class="sub"> ({res['correct']}/{res['total']} rows)</span></div>{bar(res['accuracy_pct'])}</div>
      <div class="metric"><div class="metric-val" style="color:#a855f7">{res['macro_f1']}%</div>
        <div class="metric-lbl">Macro F1<span class="sub"> (3 IMCI levels)</span></div>{bar(res['macro_f1'], '#a855f7')}</div>
      <div class="metric"><div class="metric-val" style="color:{'#22c55e' if saf['critical_sensitivity_pct']>=90 else '#ef4444'}">{saf['critical_sensitivity_pct']}%</div>
        <div class="metric-lbl">Critical Sensitivity<span class="sub"> ER_NOW → RED ({saf['er_now_support']} cases)</span></div>{bar(saf['critical_sensitivity_pct'], '#ef4444')}</div>
      <div class="metric"><div class="metric-val" style="color:{und_color}">{saf['under_triage_pct']}%</div>
        <div class="metric-lbl">Under-Triage Rate<span class="sub"> emergency missed as ≤ YELLOW</span></div>{bar(saf['under_triage_pct'], '#ef4444')}</div>
      <div class="metric"><div class="metric-val" style="color:#f59e0b">{saf['over_triage_pct']}%</div>
        <div class="metric-lbl">Over-Triage Rate<span class="sub"> HOME_CARE escalated to RED</span></div>{bar(saf['over_triage_pct'], '#f59e0b')}</div>
      <div class="metric"><div class="metric-val" style="color:#38bdf8">{res['extraction_yield_pct']}%</div>
        <div class="metric-lbl">Extraction Yield<span class="sub"> rows where ≥1 symptom flag fired</span></div>{bar(res['extraction_yield_pct'], '#38bdf8')}</div>
    </div>"""

    # Card 3 — per-class table
    prf_rows = "".join(
        f'<tr><td><span class="lvl lvl-{p["level"].split("_")[0].lower()}">{p["level"]}</span></td>'
        f'<td class="num">{p["support"]}</td>'
        f'<td class="num">{p["precision"]}%</td><td class="num">{p["recall"]}%</td>'
        f'<td class="num">{p["f1"]}%</td><td>{bar(p["f1"], LEVEL_COLORS[i+1])}</td></tr>'
        for i, p in enumerate(res["per_level"].values())
    )
    # Card 3b — per source-tier breakdown
    tb_rows = "".join(
        f'<tr><td><span class="pill pill-{t.lower()}">{t}</span></td>'
        f'<td>{b["mapped_level"]}</td><td class="num">{b["support"]}</td>'
        f'<td class="num">{b["accuracy_pct"]}%</td>'
        f'<td class="num sub2">{b["predicted_dist_pct"]["SELF_CARE"]}/{b["predicted_dist_pct"]["ASHA_DISPATCH"]}/{b["predicted_dist_pct"]["EMERGENCY_REFERRAL"]}</td></tr>'
        for t, b in res["tier_breakdown"].items()
    )
    card_cls = f"""
    <div class="card" style="border-top:4px solid #a855f7">
      <h2>Per-Level Precision / Recall / F1</h2>
      <table class="tbl">
        <thead><tr><th>Predicted level</th><th>Support</th><th>Precision</th><th>Recall</th><th>F1</th><th></th></tr></thead>
        <tbody>{prf_rows}</tbody>
      </table>
      <h2 style="margin-top:1.6rem">Per Source-Tier Behaviour</h2>
      <table class="tbl">
        <thead><tr><th>Dataset tier</th><th>Mapped level</th><th>Support</th><th>Tier acc.</th><th>Predicted G/Y/R %</th></tr></thead>
        <tbody>{tb_rows}</tbody>
      </table>
    </div>"""

    # Card 4 — confusion matrix
    cm = res["confusion_matrix"]
    mx = max(max(r) for r in cm) or 1
    cm_rows = ""
    for gi, row in enumerate(cm):
        cells = "".join(
            f'<td class="cm-cell" style="background:rgba({"34,197,94" if gi==pi else "79,142,247"},{0.08+0.75*v/mx});'
            f'{"color:#fff;font-weight:700" if v/mx > .45 else ""}">{v:,}</td>'
            for pi, v in enumerate(row))
        cm_rows += f'<tr><td class="cm-head">{LEVEL_NAMES[gi+1]}</td>{cells}</tr>'
    card_cm = f"""
    <div class="card" style="border-top:4px solid #38bdf8">
      <h2>Confusion Matrix <span class="sub2">(rows = ground truth · cols = predicted)</span></h2>
      <table class="cm">
        <thead><tr><th></th><th>→ SELF_CARE</th><th>→ ASHA_DISPATCH</th><th>→ EMERGENCY_REFERRAL</th></tr></thead>
        <tbody>{cm_rows}</tbody>
      </table>
      <p class="note">Green diagonal = correct dispatch level. Bottom row is safety-critical:
      any value outside the last cell is a missed emergency.</p>
    </div>"""

    # Card 5 — latency
    card_lat = f"""
    <div class="card" style="border-top:4px solid #22c55e">
      <h2>Pipeline Latency over {res['total']:,} Rows</h2>
      <table class="tbl lat">
        <thead><tr><th>Metric</th><th>Mean</th><th>P50</th><th>P95</th><th>Max</th></tr></thead>
        <tbody>
          <tr><td>NER + IMCI (ms)</td><td class="num">{lat['mean']}</td><td class="num">{lat['p50']}</td>
              <td class="num">{lat['p95']}</td><td class="num">{lat['max']}</td></tr>
        </tbody>
      </table>
      <div class="rss-badge">Wall clock: <strong>{lat['wall_seconds']} s</strong> ·
          Throughput: <strong>{lat['rows_per_sec']:,.0f} rows/s</strong> · Pure CPU, zero network calls</div>
    </div>"""

    # Card 6 — sample misses
    misses = [m for m in res["miss_examples"] if m["kind"] == "under"][:6] or res["miss_examples"][:8]
    overs = [m for m in res["miss_examples"] if m["kind"] == "over"][:4]
    def ex_rows(items):
        return "".join(
            f'<tr><td class="mono">{m["text"]}</td><td><span class="pill pill-{m["tier"].lower()}">{m["tier"]}</span></td>'
            f'<td>{m["gold"].replace("_"," ").title()}</td><td>{m["pred"].replace("_"," ").title()}</td>'
            f'<td class="mono flags">{", ".join(m["flags"]) or "— none —"}</td></tr>'
            for m in items)
    card_miss = f"""
    <div class="card" style="border-top:4px solid #ef4444">
      <h2>Error Analysis — Sample Misclassifications</h2>
      <h3 style="margin-bottom:.4rem">⚠ Under-triage (dangerous direction)</h3>
      <table class="tbl ex"><thead><tr><th>Symptom text</th><th>Gold</th><th>Expected</th><th>Predicted</th><th>Extracted flags</th></tr></thead>
        <tbody>{ex_rows(misses)}</tbody></table>
      <h3 style="margin:1rem 0 .4rem">△ Over-triage (safe direction)</h3>
      <table class="tbl ex"><thead><tr><th>Symptom text</th><th>Gold</th><th>Expected</th><th>Predicted</th><th>Extracted flags</th></tr></thead>
        <tbody>{ex_rows(overs)}</tbody></table>
    </div>"""

    # Scorecard
    sc_rows = "".join(
        f"""<div class="score-row"><div class="score-label">{name} <span class="wt">wt {w}%</span></div>
        <div class="score-bar-wrap"><div class="score-bar-fill" style="width:{max(0,min(100,v)):.2f}%;background:{col}"></div></div>
        <div class="score-val" style="color:{col}">{v:.2f}%</div></div>"""
        for (name, v, w), col in zip(weights, ["#ef4444", "#4f8ef7", "#a855f7", "#22c55e", "#f59e0b"]))
    score_color = "#22c55e" if score >= 85 else "#f59e0b" if score >= 65 else "#ef4444"
    scorecard = f"""
    <div class="scorecard"><h2>External Dataset Scorecard</h2>
      <div class="score-rows">{sc_rows}</div>
      <div class="overall-score" style="color:{score_color}">
        <span class="overall-label">External Benchmark Score</span>
        <span class="overall-val">{score:.2f}%</span></div>
    </div>"""

    mapping_rows = "".join(f"<li><code>{k}</code> → <strong>{v}</strong></li>"
                           for k, v in res["mapping"].items())
    ts = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SwaraSetu — Tanglish Medical Triage Benchmark</title>
<style>
  :root{{--bg:#0f1117;--surface:#1a1d27;--border:#2a2d3a;--text:#e2e8f0;--muted:#94a3b8;--accent:#4f8ef7}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;line-height:1.6}}
  header{{background:linear-gradient(135deg,#1a1d27,#0f1117);border-bottom:1px solid var(--border);padding:2rem 2.5rem 1.5rem}}
  header h1{{font-size:1.9rem;font-weight:700;color:#fff;letter-spacing:-.5px}}
  header h1 span{{color:var(--accent)}}
  header .subtitle{{color:var(--muted);margin-top:.3rem;font-size:.95rem}}
  header .ts{{color:#475569;font-size:.8rem;margin-top:.5rem}}
  .container{{max-width:1100px;margin:0 auto;padding:2rem 2rem 4rem}}
  .card{{background:var(--surface);border-radius:12px;padding:1.6rem 1.8rem;border:1px solid var(--border)}}
  .card h2{{font-size:1rem;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:1.2rem}}
  .card h3{{font-size:.86rem;color:#cbd5e1;text-transform:uppercase;letter-spacing:.05em}}
  .grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:1.2rem;margin-top:1.5rem}}
  @media(max-width:800px){{.grid{{grid-template-columns:1fr 1fr}}}}
  @media(max-width:520px){{.grid{{grid-template-columns:1fr}}}}
  .metric{{background:#12151e;border-radius:8px;padding:1rem 1.1rem}}
  .metric-val{{font-size:1.9rem;font-weight:700;line-height:1}}
  .metric-lbl{{font-size:.8rem;color:var(--muted);margin:.4rem 0 .6rem}}
  .metric-lbl .sub{{display:block;font-size:.72rem;opacity:.75}}
  .bar-wrap{{height:6px;background:#1e2230;border-radius:3px;overflow:hidden}}
  .bar-fill{{height:100%;border-radius:3px}}
  .tbl{{width:100%;border-collapse:collapse;font-size:.88rem}}
  .tbl td,.tbl th{{padding:.42rem .55rem;border-bottom:1px solid #232736;text-align:left;vertical-align:middle}}
  .tbl th{{color:var(--muted);font-weight:600;font-size:.78rem;text-transform:uppercase;letter-spacing:.04em}}
  .tbl .num{{font-family:monospace;text-align:right;color:#cbd5e1}}
  .tbl.tiers td{{padding:.3rem .55rem}}
  .sub2{{color:#64748b;font-family:monospace;font-size:.82em}}
  .pill{{display:inline-block;padding:.12rem .55rem;border-radius:99px;font-size:.74rem;font-weight:700;letter-spacing:.03em}}
  .pill-er_now{{background:#450a0a;color:#fca5a5}} .pill-high{{background:#450a0a;color:#fca5a5}}
  .pill-call_asha{{background:#422006;color:#fcd34d}} .pill-clinic_24h{{background:#422006;color:#fcd34d}}
  .pill-medium{{background:#422006;color:#fcd34d}} .pill-home_care{{background:#052e16;color:#86efac}}
  .lvl{{font-size:.8rem;font-weight:700}} .lvl-self{{color:#22c55e}} .lvl-asha{{color:#f59e0b}} .lvl-emergency{{color:#ef4444}}
  .cm{{width:100%;border-collapse:collapse;font-size:.9rem;margin-top:.4rem}}
  .cm th{{padding:.5rem;color:var(--muted);font-size:.76rem;text-transform:uppercase}}
  .cm td{{padding:.9rem;text-align:center;border:1px solid #232736;font-family:monospace}}
  .cm-head{{font-size:.78rem;color:var(--muted)!important;font-family:sans-serif!important;text-align:left!important}}
  .note{{font-size:.78rem;color:#475569;margin-top:1rem;font-style:italic}}
  .rss-badge{{margin-top:1rem;font-size:.88rem;color:var(--muted)}}
  .mono{{font-family:monospace;font-size:.84rem;color:#94a3b8;word-break:break-word}}
  .flags{{color:#38bdf8}}
  .scorecard{{background:var(--surface);border-radius:14px;padding:2rem 2.2rem;border:1px solid var(--border);margin-top:1.5rem}}
  .scorecard h2{{font-size:1rem;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:1.5rem}}
  .score-rows{{display:flex;flex-direction:column;gap:.85rem}}
  .score-row{{display:grid;grid-template-columns:280px 1fr 90px;align-items:center;gap:1rem}}
  @media(max-width:700px){{.score-row{{grid-template-columns:1fr 1fr}}}}
  .score-label{{font-size:.88rem;color:var(--muted)}} .score-label .wt{{font-size:.74rem;color:#475569;margin-left:.4rem}}
  .score-bar-wrap{{height:8px;background:#1e2230;border-radius:4px;overflow:hidden}}
  .score-bar-fill{{height:100%;border-radius:4px}}
  .score-val{{font-weight:700;font-size:.95rem;text-align:right}}
  .overall-score{{display:flex;justify-content:space-between;align-items:center;margin-top:1.8rem;padding-top:1.2rem;border-top:1px solid var(--border)}}
  .overall-label{{font-size:1.1rem;font-weight:600}} .overall-val{{font-size:2.8rem;font-weight:800;letter-spacing:-1px}}
  .basis-section{{margin-top:1.5rem;padding:1.2rem 1.5rem;background:#12151e;border-radius:10px;border:1px solid var(--border);font-size:.85rem;color:var(--muted)}}
  .basis-section h3{{color:#94a3b8;font-size:.88rem;margin-bottom:.6rem;text-transform:uppercase;letter-spacing:.05em}}
  .basis-section ul{{padding-left:1.2rem}} .basis-section li{{margin:.35rem 0}}
  code{{background:#1e2230;padding:.08rem .35rem;border-radius:4px;font-size:.82em;color:#7dd3fc}}
  a{{color:var(--accent)}}
</style>
</head>
<body>
<header>
  <h1>Swara<span>Setu</span> — External Dataset Benchmark</h1>
  <div class="subtitle">Tanglish Medical Triage Data · rule-based Indic NER → deterministic WHO IMCI engine · end-to-end offline pipeline</div>
  <div class="ts">Generated: {ts} · Pipeline: extract_symptoms_rule_fallback() → evaluate()</div>
</header>
<div class="container">
  <div class="grid" style="grid-template-columns:1fr">{card_ds}</div>
  {metrics_html}
  <div class="grid">{card_lat}{card_cm}</div>
  <div class="grid">{card_cls}</div>
  <div class="grid" style="grid-template-columns:1fr">{card_miss}</div>
  {scorecard}
  <div class="basis-section">
    <h3>Benchmark Basis &amp; Methodology</h3>
    <ul>
      <li><strong>Data</strong> — all {res['total']:,} rows of <code>{ds['file']}</code> from the Hugging Face dataset;
          fields: <code>symptom_text</code> (spoken-style Tamil/Tanglish/English) → <code>risk_tier</code>.</li>
      <li><strong>Tier mapping</strong> (dataset 4-tier → SwaraSetu IMCI 3-tier): {mapping_rows[4:-4]}</li>
      <li><strong>Pipeline</strong> — every row runs the production offline path:
          <code>SarvamClient.extract_symptoms_rule_fallback(text, 'ta')</code> → <code>SymptomPayload</code> →
          <code>engine.evaluate()</code>. No API key, no network, no LLM.</li>
      <li><strong>Defaults</strong> — dataset has no age column, so payloads use the engine default
          (<code>age_group='child'</code>); severity words (severe/romba/light/mild) are not yet extracted
          and therefore do not modulate risk.</li>
      <li><strong>Safety weighting</strong> — Critical Sensitivity 35% · Accuracy 25% · Macro-F1 20% ·
          Under-triage avoidance 10% · Over-triage control 10%. Under-triage (missing an emergency) is the
          clinically dangerous direction and dominates error analysis above.</li>
    </ul>
  </div>
</div>
</body>
</html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--html", metavar="PATH", help="write standalone HTML report")
    args = ap.parse_args()

    res = run_benchmark(verbose=args.verbose)
    score, weights = dataset_score(res)

    if args.json:
        print(json.dumps({**res, "benchmark_score": score}, indent=2))
    else:
        W = 78
        print("=" * W)
        print("SWARASETU — EXTERNAL BENCHMARK: TANGLISH MEDICAL TRIAGE DATA")
        print("=" * W)
        print(f"\n[DATA] {res['dataset']['url']}")
        print(f"       {res['total']:,} rows · tiers: {res['dataset']['classes']}")
        print(f"\n[1] MAPPED ACCURACY        : {res['accuracy_pct']:>6.2f}%  ({res['correct']}/{res['total']})")
        print(f"    MACRO F1               : {res['macro_f1']:>6.2f}%")
        print(f"[2] CRITICAL SENSITIVITY   : {res['safety']['critical_sensitivity_pct']:>6.2f}%  "
              f"(ER_NOW → RED, n={res['safety']['er_now_support']})")
        print(f"    UNDER-TRIAGE RATE      : {res['safety']['under_triage_pct']:>6.2f}%  <- SAFETY CRITICAL")
        print(f"    OVER-TRIAGE RATE       : {res['safety']['over_triage_pct']:>6.2f}%")
        print(f"[3] EXTRACTION YIELD       : {res['extraction_yield_pct']:>6.2f}%")
        print(f"[4] LATENCY (ms)           : mean {res['latency']['mean']}  p95 {res['latency']['p95']}"
              f"  max {res['latency']['max']}  |  {res['latency']['rows_per_sec']:,.0f} rows/s")
        print("\n    PER-LEVEL  precision / recall / f1")
        for p in res["per_level"].values():
            print(f"      {p['level']:<18} {p['precision']:>6.2f}% / {p['recall']:>6.2f}% / {p['f1']:>6.2f}%   (n={p['support']})")
        print("\n" + "-" * W)
        for name, v, w in weights:
            print(f"  {name:<40} {v:>6.2f}%  (wt {w}%)")
        print("-" * W)
        print(f"  {'EXTERNAL BENCHMARK SCORE':<40} {score:>6.2f}%")
        print("=" * W)

    if args.html:
        out = Path(args.html)
        out.write_text(build_html(res), encoding="utf-8")
        print(f"\nHTML report written -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
