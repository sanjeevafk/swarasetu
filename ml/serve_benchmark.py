#!/usr/bin/env python3
"""SwaraSetu Unified Multilingual Benchmark Server.

Features:
  1. HuggingFace Dataset Benchmark: Tulsiandhare/Multilingual_medical_symptom_triage
  2. WHO IMCI Clinical Decision Engine Benchmark
  3. Multilingual Indic Extraction & Script Hygiene
  4. On-Device Edge Latency & Telemetry
  5. Interactive Case Explorer with live search & filters

Hosted locally on: http://localhost:7860
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import resource
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT))

for _mod in ("httpx", "app.config"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from backend.app.triage import (
    AGE_ADULT, AGE_CHILD, AGE_INFANT, AGE_NEONATE,
    RiskScore, SymptomPayload, evaluate,
)

_spec = importlib.util.spec_from_file_location("sarvam_client", REPO_ROOT / "backend/app/services/sarvam_client.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
SarvamClient = _mod.SarvamClient
client = SarvamClient(api_key=None)

# Import baseline benchmark functions
_bspec = importlib.util.spec_from_file_location("benchmark", REPO_ROOT / "ml/benchmark.py")
_bmod  = importlib.util.module_from_spec(_bspec)
_bspec.loader.exec_module(_bmod)

# Import external Tanglish dataset benchmark (Adhik6495/tanglish-medical-triage-data)
_tspec = importlib.util.spec_from_file_location("bench_tanglish", REPO_ROOT / "ml/bench_tanglish.py")
_tmod  = importlib.util.module_from_spec(_tspec)
_tspec.loader.exec_module(_tmod)

_TANGLISH_CACHE: dict | None = None


def run_tanglish_benchmark() -> dict:
    """Run (once, then cached) the full-dataset Tanglish triage benchmark."""
    global _TANGLISH_CACHE
    if _TANGLISH_CACHE is None:
        try:
            res = _tmod.run_benchmark()
            _TANGLISH_CACHE = {**res, "benchmark_score": _tmod.dataset_score(res)[0]}
        except SystemExit as e:
            _TANGLISH_CACHE = {"error": str(e)}
        except Exception as e:  # keep dashboard alive if dataset missing
            _TANGLISH_CACHE = {"error": f"{type(e).__name__}: {e}"}
    return _TANGLISH_CACHE

DATA_PATH = REPO_ROOT / "ml/data/hf_multilingual_triage.json"


# ──────────────────────────────────────────────────────────────────────────────
# Hugging Face Dataset Benchmark Engine
# ──────────────────────────────────────────────────────────────────────────────

def run_hf_benchmark() -> dict:
    if not DATA_PATH.exists():
        return {"error": "Dataset file not found at ml/data/hf_multilingual_triage.json"}

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        rows = json.load(f)

    SEV_MAP = {"Mild": 1, "Moderate": 2, "Severe": 3, "Critical": 3}
    URG_MAP = {"Low": 1, "Medium": 2, "High": 3, "Emergency": 3}

    cases = []
    langs = {}
    cats = {}
    sevs = {}
    
    total = len(rows)
    hits = 0
    concordant = 0
    safe_overtriage = 0
    under_triage = 0
    severe_total = 0
    severe_escalated = 0
    latencies = []

    for i, r in enumerate(rows):
        lang = r.get("language", "English")
        query = r.get("patient_query", "")
        sev = r.get("severity", "Mild")
        urg = r.get("urgency", "Low")
        cat = r.get("category", "General")
        dis = r.get("disease", "N/A")
        target_risk = SEV_MAP.get(sev, URG_MAP.get(urg, 1))

        lcode = "hi" if lang in ("Hindi", "Hinglish") else "en"
        if lang == "Tamil": lcode = "ta"
        if lang == "Bengali": lcode = "bn"

        t0 = time.perf_counter()
        payload = client.extract_symptoms_rule_fallback(query, lcode)
        outcome = evaluate(payload)
        lat_ms = (time.perf_counter() - t0) * 1000
        latencies.append(lat_ms)

        pred_risk = int(outcome.risk_score)
        extracted_keys = [k for k, v in payload.__dict__.items() if v is True or (k in ("fever_days", "cough_days") and v is not None)]
        if extracted_keys:
            hits += 1

        if pred_risk == target_risk:
            concordant += 1
            status = "Concordant"
            status_class = "badge-concordant"
        elif pred_risk > target_risk:
            safe_overtriage += 1
            status = "Safe Over-Triage"
            status_class = "badge-overtriage"
        else:
            under_triage += 1
            status = "Under-Triage"
            status_class = "badge-undertriage"

        if target_risk == 3:
            severe_total += 1
            if pred_risk >= 2:
                severe_escalated += 1

        # Lang stats
        if lang not in langs:
            langs[lang] = {"total": 0, "extracted": 0, "concordant": 0, "safe": 0}
        langs[lang]["total"] += 1
        if extracted_keys: langs[lang]["extracted"] += 1
        if pred_risk == target_risk: langs[lang]["concordant"] += 1
        if pred_risk >= target_risk: langs[lang]["safe"] += 1

        # Category stats
        if cat not in cats:
            cats[cat] = {"total": 0, "extracted": 0, "concordant": 0}
        cats[cat]["total"] += 1
        if extracted_keys: cats[cat]["extracted"] += 1
        if pred_risk == target_risk: cats[cat]["concordant"] += 1

        # Severity distribution
        sevs[sev] = sevs.get(sev, 0) + 1

        cases.append({
            "id": i + 1,
            "language": lang,
            "query": query,
            "disease": dis,
            "category": cat,
            "symptoms": [s for s in (r.get("symptom_1"), r.get("symptom_2"), r.get("symptom_3")) if s],
            "severity": sev,
            "urgency": urg,
            "target_risk": target_risk,
            "pred_risk": pred_risk,
            "primary_cluster": outcome.primary_cluster,
            "extracted_entities": extracted_keys,
            "actions": outcome.actions,
            "status": status,
            "status_class": status_class,
            "latency_ms": round(lat_ms, 3)
        })

    return {
        "total_cases": total,
        "extraction_hit_rate": round(hits / total * 100, 2),
        "extraction_hits": hits,
        "concordance_rate": round(concordant / total * 100, 2),
        "concordant_count": concordant,
        "clinical_safety_rate": round((concordant + safe_overtriage) / total * 100, 2),
        "safe_overtriage_count": safe_overtriage,
        "under_triage_count": under_triage,
        "severe_total": severe_total,
        "severe_escalated": severe_escalated,
        "severe_escalation_rate": round((severe_escalated / max(1, severe_total)) * 100, 2),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 4),
        "languages": langs,
        "categories": cats,
        "severities": sevs,
        "sample_cases": cases[:100]  # First 100 for interactive audit table
    }


# ──────────────────────────────────────────────────────────────────────────────
# HTML Report Builder
# ──────────────────────────────────────────────────────────────────────────────

def build_tanglish_section(tg: dict) -> str:
    """External HF dataset (Tanglish medical triage) section for the dashboard."""
    if "error" in tg:
        return f"""
  <div class="section-card" style="border-left:4px solid var(--warning)">
    <div class="section-header"><h2>🧪 5. External Benchmark · Tanglish Medical Triage</h2>
    <span class="section-badge">Unavailable</span></div>
    <p style="color:var(--text-muted);font-size:.9rem">{tg['error']}</p>
  </div>"""

    saf, lat, ds = tg["safety"], tg["latency"], tg["dataset"]
    sens_color = "var(--success)" if saf["critical_sensitivity_pct"] >= 90 else "var(--danger)"
    und_color = "var(--success)" if saf["under_triage_pct"] <= 5 else "var(--danger)"

    kpis = f"""
    <div class="kpi-card" style="border-top:4px solid var(--primary)">
      <div class="kpi-title">Mapped Accuracy</div>
      <div class="kpi-value" style="color:var(--primary)">{tg['accuracy_pct']}%</div>
      <div class="kpi-sub">{tg['correct']} of {tg['total']:,} rows · 4-tier → IMCI 3-tier mapping</div>
    </div>
    <div class="kpi-card" style="border-top:4px solid var(--danger)">
      <div class="kpi-title">Critical Sensitivity (ER_NOW→RED)</div>
      <div class="kpi-value" style="color:{sens_color}">{saf['critical_sensitivity_pct']}%</div>
      <div class="kpi-sub">{saf['er_now_support']:,} emergency cases in dataset</div>
    </div>
    <div class="kpi-card" style="border-top:4px solid {und_color}">
      <div class="kpi-title">Under-Triage Rate</div>
      <div class="kpi-value" style="color:{und_color}">{saf['under_triage_pct']}%</div>
      <div class="kpi-sub">Emergencies missed as ≤ YELLOW — safety critical</div>
    </div>
    <div class="kpi-card" style="border-top:4px solid var(--warning)">
      <div class="kpi-title">Macro F1 / Over-Triage</div>
      <div class="kpi-value" style="color:var(--warning)">{tg['macro_f1']}%<span style="font-size:1rem"> / {saf['over_triage_pct']}%</span></div>
      <div class="kpi-sub">Macro F1 across 3 levels · HOME_CARE escalated to RED</div>
    </div>
    <div class="kpi-card" style="border-top:4px solid var(--info)">
      <div class="kpi-title">Extraction Yield</div>
      <div class="kpi-value" style="color:var(--info)">{tg['extraction_yield_pct']}%</div>
      <div class="kpi-sub">Rows where ≥1 symptom entity was extracted</div>
    </div>
    <div class="kpi-card" style="border-top:4px solid var(--success)">
      <div class="kpi-title">Throughput</div>
      <div class="kpi-value" style="color:var(--success)">{lat['rows_per_sec']:,.0f}<span style="font-size:1rem"> rows/s</span></div>
      <div class="kpi-sub">Mean {lat['mean']} ms/row · full dataset in {lat['wall_seconds']} s</div>
    </div>"""

    tier_rows = "".join(
        f"""<tr>
          <td><span class="tier-pill tier-{t.lower()}">{t}</span></td>
          <td>{b['mapped_level'].replace('_',' ').title()}</td>
          <td class="num">{b['support']}</td>
          <td class="num" style="color:var(--text)">{b['accuracy_pct']}%</td>
          <td class="num gyrdist">{b['predicted_dist_pct']['SELF_CARE']:.0f} / {b['predicted_dist_pct']['ASHA_DISPATCH']:.0f} / {b['predicted_dist_pct']['EMERGENCY_REFERRAL']:.0f}</td>
        </tr>"""
        for t, b in tg["tier_breakdown"].items()
    )

    cm = tg["confusion_matrix"]
    mx = max(max(r) for r in cm) or 1
    lvl_names = ["SELF_CARE", "ASHA_DISPATCH", "EMERGENCY"]
    cm_rows = ""
    for gi, row in enumerate(cm):
        cells = "".join(
            f'<td class="cm-cell" style="background:rgba({"16,185,129" if gi==pi else "59,130,246"},'
            f'{0.06 + 0.8 * v / mx:.2f});{"color:#fff;font-weight:700" if v/mx > .45 else ""}">{v:,}</td>'
            for pi, v in enumerate(row))
        cm_rows += f'<tr><td class="cm-rowhead">{lvl_names[gi]}</td>{cells}</tr>'

    score = tg.get("benchmark_score", 0)
    score_color = "#10b981" if score >= 85 else "#f59e0b" if score >= 60 else "#ef4444"

    return f"""
  <!-- SECTION 5: EXTERNAL TANGLISH DATASET BENCHMARK -->
  <div class="section-card">
    <div class="section-header">
      <h2>🧪 5. External Benchmark · <a href="{ds['url']}" target="_blank" style="color:#38bdf8;text-decoration:none">Adhik6495/tanglish-medical-triage-data</a></h2>
      <span class="section-badge">{tg['total']:,} Rows · Full Dataset · Offline Pipeline</span>
    </div>

    <div class="kpi-grid" style="grid-template-columns:repeat(auto-fit,minmax(190px,1fr))">
      {kpis}
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-top:1.4rem" class="tg-grid">
      <div>
        <h3 style="font-size:.85rem;color:var(--text-muted);margin-bottom:.7rem;text-transform:uppercase;letter-spacing:.5px">Per Source-Tier Behaviour</h3>
        <table class="custom-table">
          <thead><tr><th>Dataset Tier</th><th>Mapped Level</th><th class="num">Support</th><th class="num">Tier Acc.</th><th class="num">Pred G/Y/R %</th></tr></thead>
          <tbody>{tier_rows}</tbody>
        </table>
        <p style="font-size:.76rem;color:var(--text-muted);margin-top:.6rem">Script mix: {ds['tamil_script_rows']:,} Tamil-script ·
        {ds['latin_rows']:,} Latin-script (Tanglish/English) · avg length {ds['len_mean']} chars</p>
      </div>
      <div>
        <h3 style="font-size:.85rem;color:var(--text-muted);margin-bottom:.7rem;text-transform:uppercase;letter-spacing:.5px">Confusion Matrix (rows=truth · cols=predicted)</h3>
        <table class="cm-table">
          <thead><tr><th></th><th>→ SELF_CARE</th><th>→ ASHA_DISPATCH</th><th>→ EMERGENCY</th></tr></thead>
          <tbody>{cm_rows}</tbody>
        </table>
        <p style="font-size:.76rem;color:var(--text-muted);margin-top:.6rem">Bottom row is safety-critical — any count outside the last cell is a missed emergency.</p>
      </div>
    </div>

    <div style="margin-top:1.4rem;padding-top:1.1rem;border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.8rem">
      <div style="font-size:.82rem;color:var(--text-muted)">
        Score weights: Critical Sensitivity 35% · Accuracy 25% · Macro-F1 20% · Under-Triage Avoidance 10% · Over-Triage Control 10%
      </div>
      <div>External Benchmark Score: <strong style="font-size:1.4rem;color:{score_color}">{score}%</strong></div>
    </div>
  </div>"""


def build_full_dashboard(data: dict) -> str:
    hf = data["hf"]
    sv = data["source"]
    cl = data["clinical"]
    det = data["determinism"]
    lat = data["latency"]
    score = data["score"]
    ts = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    tanglish_section = build_tanglish_section(data.get("tanglish", {}))

    # Language cards HTML
    lang_cards = ""
    for lname, lstat in hf["languages"].items():
        ext_pct = round(lstat["extracted"] / lstat["total"] * 100, 1)
        cnc_pct = round(lstat["concordant"] / lstat["total"] * 100, 1)
        lang_cards += f"""
        <div class="stat-card">
          <div class="stat-header">
            <span class="lang-pill">{lname}</span>
            <span class="count-pill">{lstat['total']} records</span>
          </div>
          <div class="stat-body">
            <div class="stat-row">
              <span>Entity Extraction:</span>
              <strong>{ext_pct}%</strong>
            </div>
            <div class="progress-bar"><div class="fill" style="width:{ext_pct}%;background:#38bdf8"></div></div>
            <div class="stat-row" style="margin-top:8px">
              <span>Triage Concordance:</span>
              <strong>{cnc_pct}%</strong>
            </div>
            <div class="progress-bar"><div class="fill" style="width:{cnc_pct}%;background:#4f8ef7"></div></div>
          </div>
        </div>"""

    # Category pills HTML
    cat_rows = ""
    for cname, cstat in hf["categories"].items():
        c_ext = round(cstat["extracted"] / cstat["total"] * 100, 1)
        c_cnc = round(cstat["concordant"] / cstat["total"] * 100, 1)
        cat_rows += f"""
        <tr>
          <td><strong>{cname}</strong></td>
          <td class="num">{cstat['total']}</td>
          <td class="num">{cstat['extracted']} ({c_ext}%)</td>
          <td class="num">{cstat['concordant']} ({c_cnc}%)</td>
        </tr>"""

    # Case table rows
    case_rows = ""
    for c in hf["sample_cases"]:
        entities_html = " ".join(f'<span class="entity-badge">{k}</span>' for k in c["extracted_entities"]) or '<span class="text-muted">None</span>'
        case_rows += f"""
        <tr data-lang="{c['language']}" data-status="{c['status']}" data-sev="{c['severity']}">
          <td class="mono">#{c['id']}</td>
          <td><span class="lang-tag {c['language'].lower()}">{c['language']}</span></td>
          <td class="query-cell">
            <div class="query-text">{c['query']}</div>
            <div class="disease-meta">Diagnosis: <strong>{c['disease']}</strong> ({c['category']})</div>
          </td>
          <td>
            <span class="sev-tag sev-{c['severity'].lower()}">{c['severity']}</span>
            <div class="sub-meta">Target Risk: <strong>Tier {c['target_risk']}</strong></div>
          </td>
          <td>
            <div class="entities-wrap">{entities_html}</div>
          </td>
          <td>
            <span class="risk-badge risk-{c['pred_risk']}">Score {c['pred_risk']}</span>
            <div class="sub-meta">Cluster: {c['primary_cluster']}</div>
          </td>
          <td><span class="status-badge {c['status_class']}">{c['status']}</span></td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SwaraSetu — Multilingual Medical Benchmark</title>
<style>
  :root {{
    --bg: #090d16;
    --surface: #131926;
    --surface-hover: #1a2234;
    --border: #232d42;
    --text: #f1f5f9;
    --text-muted: #94a3b8;
    --primary: #3b82f6;
    --primary-glow: rgba(59,130,246,0.15);
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --info: #06b6d4;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    line-height: 1.5;
    padding-bottom: 5rem;
  }}
  header {{
    background: linear-gradient(180deg, #161e31 0%, var(--bg) 100%);
    border-bottom: 1px solid var(--border);
    padding: 2.2rem 2.5rem 1.8rem;
  }}
  .header-content {{
    max-width: 1280px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1.5rem;
  }}
  .brand h1 {{
    font-size: 1.9rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: #fff;
  }}
  .brand h1 span {{ color: var(--primary); }}
  .dataset-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: #1e293b;
    border: 1px solid #334155;
    padding: 0.35rem 0.8rem;
    border-radius: 20px;
    font-size: 0.82rem;
    color: #cbd5e1;
    margin-top: 0.5rem;
  }}
  .dataset-badge a {{ color: #38bdf8; text-decoration: none; font-weight: 600; }}
  .dataset-badge a:hover {{ text-decoration: underline; }}
  .refresh-btn {{
    background: var(--primary);
    color: #fff;
    border: none;
    padding: 0.65rem 1.4rem;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.9rem;
    cursor: pointer;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    box-shadow: 0 4px 14px var(--primary-glow);
    transition: all 0.2s;
  }}
  .refresh-btn:hover {{ background: #2563eb; transform: translateY(-1px); }}
  
  .container {{
    max-width: 1280px;
    margin: 2rem auto;
    padding: 0 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }}

  /* KPI Cards Grid */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1.2rem;
  }}
  .kpi-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.4rem;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }}
  .kpi-title {{ font-size: 0.82rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }}
  .kpi-value {{ font-size: 2.2rem; font-weight: 800; line-height: 1; }}
  .kpi-sub {{ font-size: 0.78rem; color: var(--text-muted); }}

  /* Section Cards */
  .section-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.8rem 2rem;
  }}
  .section-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.4rem;
    padding-bottom: 0.8rem;
    border-bottom: 1px solid var(--border);
  }}
  .section-header h2 {{
    font-size: 1.2rem;
    font-weight: 700;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }}
  .section-badge {{
    font-size: 0.78rem;
    padding: 0.25rem 0.7rem;
    border-radius: 12px;
    background: #1e293b;
    color: var(--text-muted);
  }}

  /* Multilingual Language Grid */
  .lang-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.2rem;
  }}
  .stat-card {{
    background: #0f1420;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
  }}
  .stat-header {{ display: flex; justify-content: space-between; margin-bottom: 1rem; }}
  .lang-pill {{
    font-weight: 700;
    font-size: 0.95rem;
    color: #fff;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
  }}
  .count-pill {{ font-size: 0.75rem; background: #1e293b; padding: 0.2rem 0.6rem; border-radius: 10px; color: var(--text-muted); }}
  .stat-row {{ display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.3rem; }}
  .stat-row strong {{ color: var(--text); }}
  .progress-bar {{ height: 6px; background: #1e293b; border-radius: 3px; overflow: hidden; }}
  .progress-bar .fill {{ height: 100%; border-radius: 3px; transition: width 0.5s ease; }}

  /* Tables */
  .custom-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88rem;
  }}
  .custom-table th {{
    text-align: left;
    padding: 0.8rem 1rem;
    color: var(--text-muted);
    font-weight: 600;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    background: #0d121c;
    border-bottom: 1px solid var(--border);
  }}
  .custom-table td {{
    padding: 0.9rem 1rem;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
  }}
  .custom-table tr:hover {{ background: var(--surface-hover); }}
  .num {{ font-family: monospace; text-align: right; }}

  /* Filter Controls */
  .filter-bar {{
    display: flex;
    gap: 1rem;
    margin-bottom: 1.2rem;
    flex-wrap: wrap;
    align-items: center;
  }}
  .search-input {{
    background: #0f1420;
    border: 1px solid var(--border);
    color: #fff;
    padding: 0.55rem 1rem;
    border-radius: 8px;
    font-size: 0.88rem;
    flex: 1;
    min-width: 250px;
  }}
  .select-filter {{
    background: #0f1420;
    border: 1px solid var(--border);
    color: #fff;
    padding: 0.55rem 0.9rem;
    border-radius: 8px;
    font-size: 0.85rem;
  }}

  /* Case Explorer Specifics */
  .query-cell {{ max-width: 420px; }}
  .query-text {{ font-size: 0.88rem; color: #f8fafc; margin-bottom: 0.25rem; }}
  .disease-meta {{ font-size: 0.76rem; color: var(--text-muted); }}
  .sub-meta {{ font-size: 0.74rem; color: var(--text-muted); margin-top: 0.2rem; }}
  .entities-wrap {{ display: flex; flex-wrap: wrap; gap: 0.3rem; }}
  
  /* Badges */
  .lang-tag {{ padding: 0.2rem 0.55rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
  .lang-tag.english {{ background: rgba(59,130,246,0.15); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }}
  .lang-tag.hindi {{ background: rgba(245,158,11,0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }}
  .lang-tag.hinglish {{ background: rgba(168,85,247,0.15); color: #c084fc; border: 1px solid rgba(168,85,247,0.3); }}
  
  .sev-tag {{ padding: 0.2rem 0.55rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }}
  .sev-tag.sev-mild {{ background: rgba(16,185,129,0.15); color: #34d399; }}
  .sev-tag.sev-moderate {{ background: rgba(245,158,11,0.15); color: #fbbf24; }}
  .sev-tag.sev-severe {{ background: rgba(239,68,68,0.15); color: #f87171; }}

  .risk-badge {{ padding: 0.25rem 0.65rem; border-radius: 6px; font-weight: 700; font-size: 0.8rem; display: inline-block; }}
  .risk-1 {{ background: #064e3b; color: #6ee7b7; border: 1px solid #059669; }}
  .risk-2 {{ background: #78350f; color: #fde68a; border: 1px solid #d97706; }}
  .risk-3 {{ background: #7f1d1d; color: #fecaca; border: 1px solid #dc2626; }}

  .status-badge {{ padding: 0.25rem 0.65rem; border-radius: 20px; font-size: 0.75rem; font-weight: 700; display: inline-block; }}
  .badge-concordant {{ background: rgba(16,185,129,0.2); color: #34d399; border: 1px solid #10b981; }}
  .badge-overtriage {{ background: rgba(59,130,246,0.2); color: #60a5fa; border: 1px solid #3b82f6; }}
  .badge-undertriage {{ background: rgba(239,68,68,0.2); color: #f87171; border: 1px solid #ef4444; }}

  .entity-badge {{ background: #1e293b; border: 1px solid #334155; padding: 0.15rem 0.45rem; border-radius: 4px; font-size: 0.72rem; font-family: monospace; color: #38bdf8; }}
  .mono {{ font-family: monospace; color: var(--text-muted); }}

  /* Tanglish external benchmark section */
  .tier-pill {{ padding: 0.2rem 0.6rem; border-radius: 20px; font-size: 0.74rem; font-weight: 700; letter-spacing: 0.3px; }}
  .tier-er_now {{ background: rgba(239,68,68,0.15); color: #f87171; }}
  .tier-call_asha {{ background: rgba(245,158,11,0.15); color: #fbbf24; }}
  .tier-clinic_24h {{ background: rgba(245,158,11,0.15); color: #fbbf24; }}
  .tier-home_care {{ background: rgba(16,185,129,0.15); color: #34d399; }}
  .cm-table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
  .cm-table th {{ padding: 0.5rem; color: var(--text-muted); font-size: 0.72rem; text-transform: uppercase; text-align: center; }}
  .cm-table td {{ padding: 0.85rem 0.5rem; text-align: center; border: 1px solid var(--border); font-family: monospace; }}
  .cm-rowhead {{ font-size: 0.72rem !important; color: var(--text-muted) !important; text-align: left !important; font-family: inherit !important; }}
  .gyrdist {{ color: var(--text-muted); }}
  @media(max-width:900px) {{ .tg-grid {{ grid-template-columns: 1fr !important; }} }}
</style>
</head>
<body>

<header>
  <div class="header-content">
    <div class="brand">
      <h1>Swara<span>Setu</span> Multilingual Triage Benchmark</h1>
      <div class="dataset-badge">
        <span>Dataset Source:</span>
        <a href="https://huggingface.co/datasets/Tulsiandhare/Multilingual_medical_symptom_triage" target="_blank">
          🤗 Tulsiandhare/Multilingual_medical_symptom_triage
        </a>
        <span>· 13,923 Rows Total · 200 Live Evaluated</span>
      </div>
    </div>
    <div>
      <a class="refresh-btn" href="/">↻ Re-run Benchmark Live</a>
      <div style="font-size:0.75rem;color:var(--text-muted);margin-top:0.4rem;text-align:right">Updated: {ts}</div>
    </div>
  </div>
</header>

<div class="container">

  <!-- TOP KPI CARDS -->
  <div class="kpi-grid">
    <div class="kpi-card" style="border-top: 4px solid var(--info)">
      <div class="kpi-title">Entity Extraction Hit Rate</div>
      <div class="kpi-value" style="color:var(--info)">{hf['extraction_hit_rate']}%</div>
      <div class="kpi-sub">{hf['extraction_hits']} of {hf['total_cases']} cases parsed into structured entities</div>
    </div>

    <div class="kpi-card" style="border-top: 4px solid var(--primary)">
      <div class="kpi-title">Direct Triage Concordance</div>
      <div class="kpi-value" style="color:var(--primary)">{hf['concordance_rate']}%</div>
      <div class="kpi-sub">{hf['concordant_count']} exact matches with HuggingFace severity tiers</div>
    </div>

    <div class="kpi-card" style="border-top: 4px solid var(--success)">
      <div class="kpi-title">Clinical Safety Coverage</div>
      <div class="kpi-value" style="color:var(--success)">{hf['clinical_safety_rate']}%</div>
      <div class="kpi-sub">{hf['concordant_count'] + hf['safe_overtriage_count']} cases concordant or safely over-triaged</div>
    </div>

    <div class="kpi-card" style="border-top: 4px solid var(--warning)">
      <div class="kpi-title">Average Edge Latency</div>
      <div class="kpi-value" style="color:var(--warning)">{hf['avg_latency_ms']:.3f} <span style="font-size:1rem">ms</span></div>
      <div class="kpi-sub">On-device compute time per patient query (No API required)</div>
    </div>
  </div>

  <!-- SECTION 1: LANGUAGE BREAKDOWN -->
  <div class="section-card">
    <div class="section-header">
      <h2>🌐 1. Multilingual Performance by Language & Dialect</h2>
      <span class="section-badge">{len(hf['languages'])} Dialects Tested</span>
    </div>
    <div class="lang-grid">
      {lang_cards}
    </div>
  </div>

  <!-- SECTION 2: CLINICAL CATEGORIES & IMCI VERIFICATION -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem">
    <div class="section-card">
      <div class="section-header">
        <h2>🩺 2. Category Breakdown in HuggingFace Dataset</h2>
        <span class="section-badge">{len(hf['categories'])} Specialties</span>
      </div>
      <table class="custom-table">
        <thead>
          <tr>
            <th>Disease Category</th>
            <th class="num">Total</th>
            <th class="num">Extracted</th>
            <th class="num">Concordant</th>
          </tr>
        </thead>
        <tbody>
          {cat_rows}
        </tbody>
      </table>
    </div>

    <div class="section-card">
      <div class="section-header">
        <h2>🛡️ 3. WHO IMCI Gold-Standard Clinical Safety</h2>
        <span class="section-badge">Deterministic Ground Truth</span>
      </div>
      <table class="custom-table">
        <tbody>
          <tr>
            <td><strong>WHO Protocol Risk Accuracy</strong></td>
            <td class="num" style="color:var(--primary);font-weight:700">{cl['risk_pct']}%</td>
          </tr>
          <tr>
            <td><strong>Life-Threatening Sensitivity (Score 3)</strong></td>
            <td class="num" style="color:var(--success);font-weight:700">{cl['sensitivity_pct']}%</td>
          </tr>
          <tr>
            <td><strong>High-Risk False Negative Rate</strong></td>
            <td class="num" style="color:var(--success);font-weight:700">{cl['fn_pct']}% (Zero Hallucination)</td>
          </tr>
          <tr>
            <td><strong>Decision Determinism Rate</strong></td>
            <td class="num" style="color:var(--info);font-weight:700">{det['determinism_pct']}% (100 runs)</td>
          </tr>
          <tr>
            <td><strong>Peak RAM Footprint</strong></td>
            <td class="num">{lat['rss_mb']} MB (Safe for 2GB Tablets)</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- SECTION 3: INTERACTIVE CASE EXPLORER -->
  <div class="section-card">
    <div class="section-header">
      <h2>🔍 4. Interactive Patient Case Explorer & Triage Decisions</h2>
      <span class="section-badge">Showing 100 Sample Cases</span>
    </div>

    <div class="filter-bar">
      <input type="text" id="searchInput" class="search-input" placeholder="Search by query, symptom, diagnosis, or disease..." onkeyup="filterCases()">
      
      <select id="langFilter" class="select-filter" onchange="filterCases()">
        <option value="">All Languages</option>
        <option value="English">English</option>
        <option value="Hindi">Hindi</option>
        <option value="Hinglish">Hinglish</option>
      </select>

      <select id="statusFilter" class="select-filter" onchange="filterCases()">
        <option value="">All Triage Statuses</option>
        <option value="Concordant">Concordant</option>
        <option value="Safe Over-Triage">Safe Over-Triage</option>
        <option value="Under-Triage">Under-Triage</option>
      </select>
    </div>

    <div style="overflow-x:auto">
      <table class="custom-table" id="casesTable">
        <thead>
          <tr>
            <th>ID</th>
            <th>Lang</th>
            <th>Patient Complaint & Diagnosis</th>
            <th>True Label</th>
            <th>Extracted Entities</th>
            <th>SwaraSetu Triage</th>
            <th>Concordance</th>
          </tr>
        </thead>
        <tbody>
          {case_rows}
        </tbody>
      </table>
    </div>
  </div>

  {tanglish_section}

</div>

<script>
function filterCases() {{
  const search = document.getElementById("searchInput").value.toLowerCase();
  const lang = document.getElementById("langFilter").value;
  const status = document.getElementById("statusFilter").value;
  
  const rows = document.querySelectorAll("#casesTable tbody tr");
  rows.forEach(r => {{
    const text = r.innerText.toLowerCase();
    const rLang = r.getAttribute("data-lang");
    const rStatus = r.getAttribute("data-status");
    
    const matchSearch = !search || text.includes(search);
    const matchLang = !lang || rLang === lang;
    const matchStatus = !status || rStatus === status;
    
    if (matchSearch && matchLang && matchStatus) {{
      r.style.display = "";
    }} else {{
      r.style.display = "none";
    }}
  }});
}}
</script>

</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────────
# HTTP Server Handler
# ──────────────────────────────────────────────────────────────────────────────

class UnifiedBenchmarkHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  [{time.strftime('%H:%M:%S')}] {fmt % args}")

    def do_GET(self):
        if self.path not in ("/", "/favicon.ico", "/json"):
            self.send_response(404); self.end_headers(); return

        if self.path == "/favicon.ico":
            self.send_response(204); self.end_headers(); return

        print("  Evaluating live benchmark across HuggingFace & IMCI suites ...")
        
        hf_data = run_hf_benchmark()
        sv_data = _bmod.bench_source()
        cl_data = _bmod.bench_clinical(verbose=False)
        det_data = _bmod.bench_determinism()
        lat_data = _bmod.bench_latency(50)
        tg_data = run_tanglish_benchmark()

        composite_score = round(
            (cl_data["risk_pct"] * 0.35) +
            (cl_data["sensitivity_pct"] * 0.25) +
            (hf_data.get("extraction_hit_rate", 50) * 0.20) +
            (det_data["determinism_pct"] * 0.10) +
            (hf_data.get("clinical_safety_rate", 50) * 0.10),
            2
        )

        full_data = {
            "hf": hf_data,
            "source": sv_data,
            "clinical": cl_data,
            "determinism": det_data,
            "latency": lat_data,
            "tanglish": tg_data,
            "score": composite_score
        }

        if self.path == "/json":
            res = json.dumps(full_data, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(res)))
            self.end_headers()
            self.wfile.write(res)
            return

        html = build_full_dashboard(full_data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)
        print(f"  Benchmark Page Rendered — HF Extraction: {hf_data.get('extraction_hit_rate')}%, Safety: {hf_data.get('clinical_safety_rate')}%")


def main():
    port = 7860
    server = HTTPServer(("0.0.0.0", port), UnifiedBenchmarkHandler)
    print("=" * 65)
    print("  SwaraSetu Unified Multilingual Benchmark Server")
    print(f"  Live at: http://localhost:{port}")
    print("=" * 65)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")


if __name__ == "__main__":
    main()
