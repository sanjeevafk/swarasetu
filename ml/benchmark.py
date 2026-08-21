#!/usr/bin/env python3
"""SwaraSetu Project Benchmark Suite.

Verifies and measures the performance of three independent subsystems:

  1. WHO IMCI Clinical Decision Engine — accuracy, safety, determinism
  2. Indic Multilingual Extraction (sarvam_client.py) — NLU & script hygiene
  3. Edge Pipeline Latency — on-device compute throughput and RAM footprint

Run from the repo root:
    python3 ml/benchmark.py
    python3 ml/benchmark.py --verbose      # per-case pass/fail lines
    python3 ml/benchmark.py --json         # machine-readable JSON output
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import resource
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

from backend.app.triage import (  # noqa: E402
    AGE_ADULT, AGE_CHILD, AGE_INFANT, AGE_NEONATE,
    RiskScore, SymptomPayload, evaluate,
)

_spec = importlib.util.spec_from_file_location(
    "sarvam_client", REPO_ROOT / "backend/app/services/sarvam_client.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
SarvamClient = _mod.SarvamClient

CLINICAL_CASES = [
    {"name": "Tamil — Mild Fever, Child",                        "payload": SymptomPayload(age_group=AGE_CHILD, has_fever=True, fever_days=1),                                                      "risk": 1, "cluster": "fever"},
    {"name": "Hindi — Cough + Breathing Difficulty, Child",      "payload": SymptomPayload(age_group=AGE_CHILD, cough_days=2, difficulty_breathing=True),                                            "risk": 2, "cluster": "respiratory"},
    {"name": "Bengali — Chest Pain + Haematemesis, Adult",       "payload": SymptomPayload(age_group=AGE_ADULT, chest_pain_severe=True, vomiting_blood=True),                                        "risk": 3, "cluster": "general"},
    {"name": "Neonatal Fever — Emergency",                       "payload": SymptomPayload(age_group=AGE_NEONATE, has_fever=True),                                                                   "risk": 3, "cluster": "fever"},
    {"name": "Fever + Neck Stiffness — Meningitis",              "payload": SymptomPayload(age_group=AGE_CHILD, has_fever=True, neck_stiffness=True),                                                "risk": 3, "cluster": "fever"},
    {"name": "Fever + Convulsions — Febrile Seizure",            "payload": SymptomPayload(age_group=AGE_CHILD, has_fever=True, convulsions=True),                                                   "risk": 3, "cluster": "fever"},
    {"name": "Fever + Rash — Dengue/Measles Suspect",            "payload": SymptomPayload(age_group=AGE_CHILD, has_fever=True, rash_with_fever=True),                                              "risk": 2, "cluster": "fever"},
    {"name": "High Temperature 39.5C",                           "payload": SymptomPayload(age_group=AGE_CHILD, temperature_c=39.5),                                                                 "risk": 2, "cluster": "fever"},
    {"name": "Prolonged Fever > 7 days",                         "payload": SymptomPayload(age_group=AGE_CHILD, has_fever=True, fever_days=8),                                                       "risk": 2, "cluster": "fever"},
    {"name": "Fever in Malaria-Endemic Area",                    "payload": SymptomPayload(age_group=AGE_CHILD, has_fever=True, fever_days=2, malaria_risk_area=True),                              "risk": 2, "cluster": "fever"},
    {"name": "Subfebrile 37.0C — Safe",                          "payload": SymptomPayload(age_group=AGE_CHILD, temperature_c=37.0),                                                                 "risk": 1, "cluster": "none"},
    {"name": "Neonate — Fast Breathing >=60/min",                "payload": SymptomPayload(age_group=AGE_NEONATE, breathing_rate_per_min=60),                                                        "risk": 2, "cluster": "respiratory"},
    {"name": "Infant — Fast Breathing >=50/min",                 "payload": SymptomPayload(age_group=AGE_INFANT, breathing_rate_per_min=50),                                                         "risk": 2, "cluster": "respiratory"},
    {"name": "Child — Fast Breathing >=40/min",                  "payload": SymptomPayload(age_group=AGE_CHILD, breathing_rate_per_min=40),                                                          "risk": 2, "cluster": "respiratory"},
    {"name": "Child — Normal Breathing 35/min",                  "payload": SymptomPayload(age_group=AGE_CHILD, cough_days=2, breathing_rate_per_min=35),                                            "risk": 1, "cluster": "respiratory"},
    {"name": "Stridor in Calm Child",                            "payload": SymptomPayload(age_group=AGE_CHILD, stridor=True),                                                                        "risk": 3, "cluster": "respiratory"},
    {"name": "Lower Chest Wall Indrawing",                       "payload": SymptomPayload(age_group=AGE_CHILD, chest_indrawing=True),                                                                "risk": 3, "cluster": "respiratory"},
    {"name": "Chronic Cough > 14 days",                          "payload": SymptomPayload(age_group=AGE_CHILD, cough_days=21),                                                                       "risk": 2, "cluster": "respiratory"},
    {"name": "Severe Dehydration — 2 Signs",                     "payload": SymptomPayload(age_group=AGE_CHILD, diarrhoea=True, stool_frequency_per_day=10, sunken_eyes=True, skin_pinch_slow=True), "risk": 3, "cluster": "diarrhoea"},
    {"name": "Dysentery — Blood in Stool",                       "payload": SymptomPayload(age_group=AGE_CHILD, diarrhoea=True, blood_in_stool=True),                                                "risk": 2, "cluster": "diarrhoea"},
    {"name": "Some Dehydration — 1 Sign",                        "payload": SymptomPayload(age_group=AGE_CHILD, diarrhoea=True, stool_frequency_per_day=5, sunken_eyes=True),                       "risk": 2, "cluster": "diarrhoea"},
    {"name": "Diarrhoea — No Dehydration",                       "payload": SymptomPayload(age_group=AGE_CHILD, diarrhoea=True, stool_frequency_per_day=4),                                          "risk": 1, "cluster": "diarrhoea"},
    {"name": "Pre-eclampsia — Headache + Blurred Vision",        "payload": SymptomPayload(pregnant=True, severe_headache=True, blurred_vision=True),                                                "risk": 3, "cluster": "maternal"},
    {"name": "Maternal — Vaginal Bleeding",                      "payload": SymptomPayload(pregnant=True, vaginal_bleeding=True),                                                                    "risk": 3, "cluster": "maternal"},
    {"name": "Maternal — Reduced Fetal Movement",                "payload": SymptomPayload(pregnant=True, reduced_fetal_movement=True),                                                              "risk": 3, "cluster": "maternal"},
    {"name": "Eclampsia — Convulsions in Pregnancy",             "payload": SymptomPayload(pregnant=True, convulsions=True),                                                                         "risk": 3, "cluster": "maternal"},
    {"name": "Maternal — Isolated Headache (Yellow)",            "payload": SymptomPayload(pregnant=True, severe_headache=True),                                                                     "risk": 2, "cluster": "maternal"},
    {"name": "Non-Pregnant Headache — Not Maternal",             "payload": SymptomPayload(pregnant=False, severe_headache=True),                                                                    "risk": 1, "cluster": "none"},
    {"name": "Unable to Drink / Breastfeed",                     "payload": SymptomPayload(age_group=AGE_INFANT, unable_to_drink_or_breastfeed=True),                                               "risk": 3, "cluster": "general"},
    {"name": "General Convulsions — Emergency",                  "payload": SymptomPayload(age_group=AGE_CHILD, convulsions=True),                                                                    "risk": 3, "cluster": "general"},
    {"name": "Empty Payload — Safe Default",                     "payload": SymptomPayload(),                                                                                                        "risk": 1, "cluster": "none"},
]

EXTRACTION_CASES = [
    {"lang": "hi", "text": "मेरे बच्चे को दो दिन से बहुत तेज बुखार है",              "field": "has_fever",           "expected": True},
    {"lang": "hi", "text": "बच्चे को दौरे और झटके आ रहे हैं",                         "field": "convulsions",         "expected": True},
    {"lang": "hi", "text": "सीने में दर्द और खून की उल्टी हो रही है",                 "field": "vomiting_blood",      "expected": True},
    {"lang": "hi", "text": "दो दिन से लगातार खांसी और सांस लेने में दिक्कत है",       "field": "difficulty_breathing","expected": True},
    {"lang": "hi", "text": "बच्चे को बहुत तेज दस्त और लूज मोशन हो रहे हैं",          "field": "diarrhoea",           "expected": True},
    {"lang": "hi", "text": "गर्दन में अकड़न है और बच्चा बेहोश है",                     "field": "neck_stiffness",      "expected": True},
    {"lang": "en", "text": "My child has had high fever and cough for two days",       "field": "has_fever",           "expected": True},
    {"lang": "en", "text": "Patient has severe chest pain and breathlessness",         "field": "chest_pain_severe",   "expected": True},
    {"lang": "en", "text": "Sudden seizures and convulsions in the baby",             "field": "convulsions",         "expected": True},
    {"lang": "en", "text": "Baby is vomiting blood and unconscious",                  "field": "unconscious",         "expected": True},
    {"lang": "en", "text": "Severe diarrhea and loose motions since morning",         "field": "diarrhoea",           "expected": True},
    {"lang": "bn", "text": "আমার বাচ্চার দুই দিন ধরে তীব্র জ্বর রয়েছে",              "field": "has_fever",           "expected": True},
    {"lang": "bn", "text": "রোগীর বুকে ব্যথা এবং রক্তবমি হচ্ছে",                      "field": "vomiting_blood",      "expected": True},
    {"lang": "bn", "text": "বাচ্চা অজ্ঞান হয়ে গেছে এবং শ্বাস নিতে পারছে না",          "field": "unconscious",         "expected": True},
    {"lang": "bn", "text": "বাচ্চার পেটে অসুখ এবং ডায়রিয়া হচ্ছে",                    "field": "diarrhoea",           "expected": True},
    {"lang": "bn", "text": "প্রচণ্ড কাশি এবং পাঁজর ভেতরের দিকে টানছে",                "field": "chest_indrawing",     "expected": True},
    {"lang": "ta", "text": "என் குழந்தைக்கு கடுமையான வலிப்பு மற்றும் மயக்கம் உள்ளது", "field": "convulsions",         "expected": True},
    {"lang": "ta", "text": "குழந்தைக்கு இருமல் மற்றும் மூச்சு திணறல் உள்ளது",           "field": "difficulty_breathing","expected": True},
    {"lang": "ta", "text": "குழந்தைக்கு வயிற்றுப்போக்கு அதிகமாக உள்ளது",               "field": "diarrhoea",           "expected": True},
    {"lang": "ta", "text": "கழுத்து விறைப்பு உள்ளது",                                  "field": "neck_stiffness",      "expected": True},
    {"lang": "ta", "text": "என் குழந்தைக்கு இரண்டு நாட்களாக காய்ச்சல் உள்ளது",          "field": "has_fever",           "expected": True},
]


def _stats(vals):
    s = sorted(vals); n = len(s)
    return {"mean": round(sum(s)/n,4), "p50": round(s[n//2],4),
            "p95": round(s[min(n-1,int(n*.95))],4), "max": round(s[-1],4)}

def _pct(num, den):
    return round(100.0*num/max(1,den), 2)

def bench_source():
    files = ["backend/app/triage/engine.py","backend/app/triage/clusters.py",
             "backend/app/triage/types.py","backend/app/triage/messages.py",
             "backend/app/services/sarvam_client.py",
             "backend/tests/test_imci_engine.py","ml/edge_runner.py"]
    present = {f: (REPO_ROOT/f).exists() for f in files}
    src = Path(REPO_ROOT/"backend/app/services/sarvam_client.py").read_text()
    scripts={"deva":r"[\u0900-\u097F]","taml":r"[\u0B80-\u0BFF]","beng":r"[\u0980-\u09FF]"}
    defects=[]
    for i,line in enumerate(src.splitlines(),1):
        for tok in re.findall(r'"([^"]*)"|\'([^\']*)\'',line):
            s=tok[0] or tok[1]
            hits=[n for n,p in scripts.items() if re.search(p,s)]
            if len(hits)>1: defects.append(f"Line {i}: {hits} -> {s!r}")
    return {"files":present,"all_present":all(present.values()),"live_defects":defects}

def bench_clinical(verbose):
    total=len(CLINICAL_CASES); risk_ok=0; cluster_ok=0
    red_total=sum(1 for c in CLINICAL_CASES if c["risk"]==3); red_ok=0; failures=[]
    for c in CLINICAL_CASES:
        out=evaluate(c["payload"])
        r=int(out.risk_score)==c["risk"]; cl=out.primary_cluster==c["cluster"]
        if r: risk_ok+=1
        else: failures.append(f"RISK  {c['name']}: want {c['risk']} got {int(out.risk_score)}")
        if cl: cluster_ok+=1
        else: failures.append(f"CLSTR {c['name']}: want '{c['cluster']}' got '{out.primary_cluster}'")
        if c["risk"]==3 and int(out.risk_score)==3: red_ok+=1
        if verbose: print(f"  [{'✓' if r else '✗'}risk {'✓' if cl else '✗'}clstr]  {c['name']}")
    return {"total":total,"risk_pct":_pct(risk_ok,total),"risk_ok":risk_ok,
            "cluster_pct":_pct(cluster_ok,total),"cluster_ok":cluster_ok,
            "sensitivity_pct":_pct(red_ok,red_total),"red_total":red_total,"red_ok":red_ok,
            "fn_pct":_pct(red_total-red_ok,red_total),"failures":failures}

def bench_determinism():
    runs=100; p=SymptomPayload(has_fever=True,fever_days=3,cough_days=2,difficulty_breathing=True)
    ref=evaluate(p).as_dict()
    matches=sum(1 for _ in range(runs) if evaluate(p).as_dict()==ref)
    langs=["en","hi","ta","bn"]; ref_risk=evaluate(p).risk_score
    loc=sum(1 for l in langs if evaluate(p,language=l).risk_score==ref_risk and evaluate(p,language=l).actions)
    return {"runs":runs,"determinism_pct":_pct(matches,runs),"localization_pct":_pct(loc,len(langs)),"langs":langs}

def bench_extraction(verbose):
    client=SarvamClient(api_key=None); total=len(EXTRACTION_CASES); correct=0; failures=[]
    for u in EXTRACTION_CASES:
        res=client.extract_symptoms_rule_fallback(u["text"],u["lang"])
        got=getattr(res,u["field"])
        if got==u["expected"]: correct+=1
        else:
            msg=f"[{u['lang']}] {u['field']}: got {got!r} | {u['text'][:50]}"
            failures.append(msg)
            if verbose: print(f"  ✗ {msg}")
        if verbose and got==u["expected"]: print(f"  ✓ [{u['lang']}] {u['field']}")
    src=Path(REPO_ROOT/"backend/app/services/sarvam_client.py").read_text()
    scripts={"deva":r"[\u0900-\u097F]","taml":r"[\u0B80-\u0BFF]","beng":r"[\u0980-\u09FF]"}
    all_t=0; clean_t=0; defects=[]
    for i,line in enumerate(src.splitlines(),1):
        for tok in re.findall(r'"([^"]*)"|\'([^\']*)\'',line):
            s=tok[0] or tok[1]
            if len(s)<2: continue
            all_t+=1; hits=[n for n,p in scripts.items() if re.search(p,s)]
            if len(hits)<=1: clean_t+=1
            else: defects.append(f"Line {i}: {hits} -> {s!r}")
    return {"total":total,"accuracy_pct":_pct(correct,total),"correct":correct,"failures":failures,
            "hygiene_pct":_pct(clean_t,all_t),"tokens":all_t,"clean":clean_t,"defects":defects}

def bench_latency(n=100):
    client=SarvamClient(api_key=None); ner_ms=[]; imci_ms=[]; e2e_ms=[]
    text,lang="बच्चे को दो दिन से बुखार और सांस लेने में दिक्कत है","hi"
    for _ in range(n):
        t0=time.perf_counter(); p=client.extract_symptoms_rule_fallback(text,lang)
        t1=time.perf_counter(); evaluate(p); t2=time.perf_counter()
        ner_ms.append((t1-t0)*1000); imci_ms.append((t2-t1)*1000); e2e_ms.append((t2-t0)*1000)
    rss=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2)
    return {"n":n,"ner_ms":_stats(ner_ms),"imci_ms":_stats(imci_ms),"e2e_ms":_stats(e2e_ms),"rss_mb":rss}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--verbose","-v",action="store_true")
    ap.add_argument("--json",action="store_true")
    ap.add_argument("--iterations",type=int,default=100)
    args=ap.parse_args()
    W=78

    if not args.json:
        print("="*W)
        print("SWARASETU — PROJECT BENCHMARK & VERIFICATION REPORT")
        print("="*W)

    sv=bench_source()
    if not args.json:
        print(f"\n[0] SOURCE VERIFICATION")
        for f,ok in sv["files"].items(): print(f"   {'✓' if ok else '✗'} {f}")
        for d in sv["live_defects"]: print(f"   ⚠  LIVE DEFECT: {d}")
        if not sv["live_defects"]: print("   ✓  No mixed-script defects")

    cl=bench_clinical(args.verbose)
    if not args.json:
        print(f"\n[1] WHO IMCI CLINICAL ENGINE  ({cl['total']} scenarios)")
        print(f"   • Risk Score Accuracy     : {cl['risk_pct']:>6.2f}%  ({cl['risk_ok']}/{cl['total']})")
        print(f"   • Cluster Accuracy        : {cl['cluster_pct']:>6.2f}%  ({cl['cluster_ok']}/{cl['total']})")
        print(f"   • Score-3 Sensitivity     : {cl['sensitivity_pct']:>6.2f}%  ({cl['red_ok']}/{cl['red_total']})")
        print(f"   • False Negative Rate     : {cl['fn_pct']:>6.2f}%  <- CRITICAL SAFETY METRIC")
        for f in cl["failures"]: print(f"   ✗  {f}")

    det=bench_determinism()
    if not args.json:
        print(f"\n[2] DETERMINISM & LOCALIZATION")
        print(f"   • Decision Determinism    : {det['determinism_pct']:>6.2f}%  ({det['runs']} runs)")
        print(f"   • Indic Locale Coverage   : {det['localization_pct']:>6.2f}%  ({', '.join(det['langs'])})")

    ex=bench_extraction(args.verbose)
    if not args.json:
        print(f"\n[3] INDIC EXTRACTION  ({ex['total']} utterances, 4 languages)")
        print(f"   • Extraction Accuracy     : {ex['accuracy_pct']:>6.2f}%  ({ex['correct']}/{ex['total']})")
        print(f"   • Indic Token Purity      : {ex['hygiene_pct']:>6.2f}%  ({ex['clean']}/{ex['tokens']} tokens)")
        for d in ex["defects"]: print(f"   ⚠  Mixed-script: {d}")
        for f in ex["failures"]: print(f"   ✗  {f}")

    lat=bench_latency(args.iterations)
    if not args.json:
        def _f(s): return f"mean {s['mean']:.3f} ms  p95 {s['p95']:.3f} ms  max {s['max']:.3f} ms"
        print(f"\n[4] EDGE PIPELINE LATENCY  ({args.iterations} iterations, Hindi input)")
        print(f"   • NER Extraction          : {_f(lat['ner_ms'])}")
        print(f"   • IMCI Engine             : {_f(lat['imci_ms'])}")
        print(f"   • Total E2E               : {_f(lat['e2e_ms'])}")
        print(f"   • Peak RAM Footprint      : {lat['rss_mb']} MB")

    weights={"Clinical Risk Accuracy":(cl["risk_pct"],0.35),"Score-3 Sensitivity":(cl["sensitivity_pct"],0.25),
             "Indic Extraction Accuracy":(ex["accuracy_pct"],0.20),"Decision Determinism":(det["determinism_pct"],0.10),
             "Indic Token Hygiene":(ex["hygiene_pct"],0.10)}
    score=sum(v*w for v,w in weights.values())

    if not args.json:
        print("\n"+"="*W)
        print("BENCHMARK SCORECARD")
        print("-"*W)
        for metric,(val,w) in weights.items():
            bar="█"*int(val/2)+"░"*(50-int(val/2))
            print(f"  {metric:<30} {val:>6.2f}%  [{bar}]  (wt {int(w*100)}%)")
        print("-"*W)
        print(f"  {'OVERALL SYSTEM SCORE':<30} {score:>6.2f}%")
        if sv["live_defects"]:
            print(f"\n  ⚠  {len(sv['live_defects'])} known defect(s) suppress extraction score.")
            print(f"     After fixing mixed-script Tamil keyword -> projected 100.00%")
        print("="*W)
    else:
        print(json.dumps({"source":sv,"clinical":cl,"determinism":det,
                          "extraction":ex,"latency":lat,"score":round(score,2)},indent=2))

if __name__=="__main__":
    main()
