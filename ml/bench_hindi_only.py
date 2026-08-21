#!/usr/bin/env python3
"""
Extract Hindi-only dataset from Multilingual_medical_symptom_triage.csv
and run comprehensive benchmark on SwaraSetu's clinical triage pipeline.
"""

import csv
import json
import time
import re
import sys
from pathlib import Path
from collections import defaultdict, Counter

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT))

# Mock external config / httpx dependencies for standalone run
from unittest.mock import MagicMock
for mod in ("httpx", "app.config"):
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

import importlib.util
spec = importlib.util.spec_from_file_location("sarvam_client", REPO_ROOT / "backend/app/services/sarvam_client.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SarvamClient = mod.SarvamClient

from backend.app.triage.engine import evaluate
from backend.app.triage.types import SymptomPayload

CSV_SOURCE = REPO_ROOT / "Multilingual_medical_symptom_triage/multilingual_medical_symptom_triage.csv"
OUTPUT_JSON = REPO_ROOT / "ml/data/hindi_medical_triage.json"
OUTPUT_CSV = REPO_ROOT / "ml/data/hindi_medical_triage.csv"

# 1. Extraction Phase
print(f"--> Extracting Hindi rows from {CSV_SOURCE.name}...")
hindi_rows = []
total_rows = 0

with open(CSV_SOURCE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        total_rows += 1
        if row.get("language") == "Hindi" or row.get("language_tag") == "hi":
            # Extract key fields
            hindi_rows.append({
                "patient_id": row.get("patient_id"),
                "patient_query": row.get("patient_query"),
                "age": row.get("age"),
                "gender": row.get("gender"),
                "disease": row.get("disease"),
                "severity": row.get("severity"),
                "urgency": row.get("urgency"),
                "symptom_1": row.get("symptom_1"),
                "symptom_2": row.get("symptom_2"),
                "symptom_3": row.get("symptom_3"),
                "recommended_action": row.get("recommended_action")
            })

OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(hindi_rows, f, ensure_ascii=False, indent=2)

with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
    if hindi_rows:
        writer = csv.DictWriter(f, fieldnames=list(hindi_rows[0].keys()))
        writer.writeheader()
        writer.writerows(hindi_rows)

print(f"✅ Extracted {len(hindi_rows):,} Hindi cases out of {total_rows:,} total cases.")
print(f"📁 Saved to: {OUTPUT_JSON} and {OUTPUT_CSV}")

# 2. Benchmark Phase
print("\n--> Running SwaraSetu Clinical Triage Benchmark on Hindi Data...")
client = SarvamClient(api_key=None)

SEV_MAP = {"Mild": 1, "Moderate": 2, "Severe": 3, "Critical": 3}
CONFUSION = [[0, 0, 0], [0, 0, 0], [0, 0, 0]] # [actual_1, 2, 3][pred_1, 2, 3]

latencies = []
exact_matches = 0
safe_concordant = 0
critical_total = 0
critical_caught = 0
under_triage_errors = 0
over_triage_count = 0

disease_stats = defaultdict(lambda: {"total": 0, "correct": 0})
flag_counts = Counter()

t_start = time.perf_counter()

for row in hindi_rows:
    query = row["patient_query"]
    sev = row.get("severity", "Mild")
    gold_risk = SEV_MAP.get(sev, 1) # 1: Low/Self-care, 2: Moderate/ASHA, 3: Critical/Emergency
    
    t0 = time.perf_counter()
    payload = client.extract_symptoms_rule_fallback(query, "hi")
    outcome = evaluate(payload)
    t1 = time.perf_counter()
    
    latencies.append((t1 - t0) * 1000.0) # in ms
    pred_risk = outcome.risk_score # 1, 2, 3
    
    # Update confusion matrix
    CONFUSION[gold_risk - 1][pred_risk - 1] += 1
    
    if gold_risk == pred_risk:
        exact_matches += 1
        safe_concordant += 1
    elif pred_risk > gold_risk:
        # Over-triage is clinically safe (conservative bias)
        safe_concordant += 1
        over_triage_count += 1
    else:
        # Under-triage
        under_triage_errors += 1
        
    if gold_risk == 3:
        critical_total += 1
        if pred_risk == 3:
            critical_caught += 1
            
    disease_stats[row.get("disease", "Unknown")]["total"] += 1
    if pred_risk >= gold_risk:
        disease_stats[row.get("disease", "Unknown")]["correct"] += 1

t_end = time.perf_counter()
total_time = t_end - t_start

total_n = len(hindi_rows)
exact_acc = (exact_matches / total_n) * 100.0
safety_concordance = (safe_concordant / total_n) * 100.0
er_sensitivity = (critical_caught / critical_total * 100.0) if critical_total else 100.0
under_triage_rate = (under_triage_errors / total_n) * 100.0
over_triage_rate = (over_triage_count / total_n) * 100.0
mean_lat = sum(latencies) / len(latencies)
sorted_lat = sorted(latencies)
p95_lat = sorted_lat[int(len(latencies) * 0.95)]
p99_lat = sorted_lat[int(len(latencies) * 0.99)]
throughput = total_n / total_time

# Print Full Report
print("\n" + "="*70)
print("📊 SWARASETU HINDI CLINICAL BENCHMARK REPORT")
print("="*70)
print(f"Total Evaluated Cases (Pure Hindi) : {total_n:,}")
print(f"Total Execution Time               : {total_time:.3f} s")
print(f"Mean Latency per Patient           : {mean_lat:.3f} ms ({mean_lat*1000:.1f} µs)")
print(f"p95 Latency                        : {p95_lat:.3f} ms")
print(f"Throughput                         : {throughput:,.0f} evals/sec")
print("-"*70)
print(f"Exact Match Accuracy               : {exact_acc:.2f}% ({exact_matches}/{total_n})")
print(f"Clinical Safety Concordance        : {safety_concordance:.2f}% ({safe_concordant}/{total_n})")
print(f"Critical ER Sensitivity (Score 3)  : {er_sensitivity:.2f}% ({critical_caught}/{critical_total})")
print(f"Under-Triage Miss Rate             : {under_triage_rate:.2f}% ({under_triage_errors}/{total_n})")
print(f"Safe Over-Triage Rate              : {over_triage_rate:.2f}% ({over_triage_count}/{total_n})")
print("-"*70)
print("CONFUSION MATRIX (Actual [rows] vs Predicted [cols]):")
print("               Pred Self-Care(1)   Pred ASHA(2)   Pred Emergency(3)   Total")
print(f"Actual Mild(1)       {CONFUSION[0][0]:<17} {CONFUSION[0][1]:<14} {CONFUSION[0][2]:<19} {sum(CONFUSION[0])}")
print(f"Actual Mod(2)        {CONFUSION[1][0]:<17} {CONFUSION[1][1]:<14} {CONFUSION[1][2]:<19} {sum(CONFUSION[1])}")
print(f"Actual Severe(3)     {CONFUSION[2][0]:<17} {CONFUSION[2][1]:<14} {CONFUSION[2][2]:<19} {sum(CONFUSION[2])}")
print("="*70)

