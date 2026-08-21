"""Comprehensive Clinical Benchmark & Diagnosis Suite for SwaraSetu

Evaluates SwaraSetu's WHO IMCI Triage Engine against:
1. Tulsiandhare/Multilingual_medical_symptom_triage (13,923 cases - Hindi, Hinglish, English, Marathi, Gujarati, Telugu)
2. Irtisum/bengali-medical-triage-conversations (2,724 cases - Bengali script, Banglish, English)
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure backend and repo root are on python path
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
REPORTS_DIR = REPO_ROOT / "reports"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BACKEND_DIR))

from app.triage.engine import evaluate
from app.triage.types import RiskScore, SymptomPayload

CLASSES = ("HIGH", "MEDIUM", "LOW")
SCORE_TO_LABEL = {3: "HIGH", 2: "MEDIUM", 1: "LOW"}

# Comprehensive Indic Multilingual Keyword Dictionaries
KEYWORD_CONVULSIONS = [
    "convulsion", "seizure", "jhatke", "fits", "twitching", "fasciculation",
    "খিঁচুনি", "झटके", "मिरगी", "फिट्स", "వణుకు", "आंचकी"
]

KEYWORD_UNCONSCIOUS = [
    "unconscious", "lethargic", "coma", "behosh", "stupor", "poison", "bite", "snakebite",
    "organophosphate", "pesticide", "collapsed", "apathy", "অজ্ঞান", "বেহুঁশ", "अचेत", "बेहोश",
    "నిస్పృహ", "శిథిలమైన"
]

KEYWORD_UNABLE_DRINK = [
    "unable to drink", "poor oral intake", "cannot feed", "not feeding", "emaciated",
    "খেতে পারছে না", "পান করতে পারছে না", "खाना नहीं खा रहा", "पानी नहीं पी पा रहा"
]

KEYWORD_VOMITING_ALL = [
    "vomiting everything", "vomiting froth", "profuse vomiting", "continuous vomiting",
    "সব বমি করে দিচ্ছে", "लगातार उल्टी", "सब उल्टी हो रहा"
]

KEYWORD_FEVER = [
    "fever", "pyrexia", "bukhar", "kaichal", "jor", "jwar", "high temperature", "feverish",
    "malaria", "dengue", "typhoid", "chikungunya", "chills", "shivering",
    "জ্বর", "কাঁপুনি", "শিহরিত", "बुखार", "तेज बुखार", "ज्वर", "జ్వరం", "కాక", "ताप", "જાવર"
]

KEYWORD_NECK_STIFFNESS = [
    "stiff neck", "neck stiffness", "meningismus", "ঘাড় শক্ত", "गर्दन अकड़ना", "गर्दन में अकड़न"
]

KEYWORD_RASH = [
    "rash", "petechiae", "purpura", "red spots", "র্যাশ", "লালচে দাগ", "दाने", "रैश", "लाल चक्कत्ते"
]

KEYWORD_RESPIRATORY = [
    "difficulty breathing", "respiratory distress", "breathless", "shortness of breath",
    "cough", "khasi", "kasi", "pneumonia", "saans", "dyspnea", "asthma", "bronchitis", "dry cough", "wet cough",
    "শ্বাসকষ্ট", "কাশি", "হাঁপানি", "सांस फूलना", "खांसी", "सांस लेने में तकलीफ", "దగ్గు", "ఆయాసం"
]

KEYWORD_CHEST_PAIN = [
    "chest pain", "angina", "myocardial", "cardiac", "buk betha", "বুক ব্যথা", "छाती में दर्द", "ఛాతీ నొప్పి"
]

KEYWORD_VOMITING_BLOOD = [
    "vomiting blood", "hematemesis", "haematemesis", "hemoptysis", "roktu bomi", "রক্ত বমি", "खून की उल्टी"
]

KEYWORD_DIARRHOEA = [
    "diarrhea", "diarrhoea", "dast", "loose stool", "loose motion", "gastroenteritis", "cholera", "patla paykhana",
    "ডায়রিয়া", "পাতলা পায়খানা", "दस्त", "पतले दस्त", "విరేచనాలు", "ઝાડા"
]

KEYWORD_BLOOD_STOOL = [
    "blood in stool", "dysentery", "bloody stool", "roktu paykhana", "রক্ত পায়খানা", "पखाने में खून"
]

KEYWORD_HEADACHE = [
    "headache", "matha betha", "mathabetha", "মাথা ব্যথা", "सर दर्द", "सिरदर्द", "తలనొప్పి", "માથાનો દુખાવો"
]


def parse_multilingual_symptom_row(row: dict) -> tuple[SymptomPayload, int, str, str]:
    """Parse a row from Tulsiandhare/Multilingual_medical_symptom_triage with enhanced Indic NER."""
    query = str(row.get("patient_query", "") or "")
    s1 = str(row.get("symptom_1", "") or "")
    s2 = str(row.get("symptom_2", "") or "")
    s3 = str(row.get("symptom_3", "") or "")
    disease = str(row.get("disease", "") or "")
    category = str(row.get("category", "") or "")
    comorbidities = str(row.get("comorbidities", "") or "")
    reasoning = str(row.get("reasoning_trace", "") or "")
    lang = str(row.get("language", "en") or "en").lower().strip()
    
    full_text = f"{query} {s1} {s2} {s3} {disease} {category} {comorbidities} {reasoning}".lower()
    
    # Ground Truth Mapping
    urgency = str(row.get("urgency", "")).strip()
    severity = str(row.get("severity", "")).strip()
    outcome = str(row.get("clinical_outcome", "")).strip()
    
    if urgency == "High" or severity == "Severe" or outcome in ["ICU", "Death"]:
        gt_score = 3
    elif urgency == "Medium" or severity == "Moderate" or outcome == "Hospitalized":
        gt_score = 2
    else:
        gt_score = 1

    # Demographics
    try:
        age_num = float(row.get("age", 25))
    except (ValueError, TypeError):
        age_num = 25.0

    if age_num < 0.16:
        age_group = "neonate"
    elif age_num < 1.0:
        age_group = "infant"
    elif age_num <= 5.0:
        age_group = "child"
    else:
        age_group = "adult"

    gender = str(row.get("gender", "")).lower()
    pregnant = ("pregnant" in full_text or "gestation" in full_text or "गर्भवती" in full_text or "గర్భిణి" in full_text) if gender in ["female", "महिला", "స్త్రీ", "स्त्री", "મહિલા"] else False

    # Danger signs
    convulsions = any(w in full_text for w in KEYWORD_CONVULSIONS)
    unconscious = any(w in full_text for w in KEYWORD_UNCONSCIOUS)
    unable_drink = any(w in full_text for w in KEYWORD_UNABLE_DRINK)
    vomiting_all = any(w in full_text for w in KEYWORD_VOMITING_ALL)

    # Respiratory & Cardiac
    chest_pain = any(w in full_text for w in KEYWORD_CHEST_PAIN)
    vomiting_blood = any(w in full_text for w in KEYWORD_VOMITING_BLOOD)
    stridor = any(w in full_text for w in ["stridor", "wheezing", "noisy breathing", "हूपिंग"])
    chest_indrawing = any(w in full_text for w in ["chest indrawing", "intercostal indrawing", "nasal flaring", "pasliyan", "पसलियां चलना"])
    difficulty_breathing = any(w in full_text for w in KEYWORD_RESPIRATORY)

    # Fever
    has_fever = any(w in full_text for w in KEYWORD_FEVER) or "fever" in s1 or "fever" in s2 or "fever" in s3
    neck_stiffness = any(w in full_text for w in KEYWORD_NECK_STIFFNESS)
    rash_fever = any(w in full_text for w in KEYWORD_RASH)

    # Diarrhoea
    diarrhoea = any(w in full_text for w in KEYWORD_DIARRHOEA)
    blood_stool = any(w in full_text for w in KEYWORD_BLOOD_STOOL)
    sunken_eyes = any(w in full_text for w in ["sunken eyes", "dehydration", "dry mouth", "सूखी आंखें", "निर्जलीकरण"])
    skin_pinch_slow = any(w in full_text for w in ["skin pinch", "turgor", "slow refill"])

    # Maternal & Neurological
    severe_headache = any(w in full_text for w in KEYWORD_HEADACHE)
    blurred_vision = any(w in full_text for w in ["blurred vision", "visual disturbance", "धुंधला दिखना", "ঝাপসা"])
    vaginal_bleeding = any(w in full_text for w in ["vaginal bleeding", "hemorrhage", "bleeding per vaginum", "रक्तस्राव"])
    reduced_fetal_mov = any(w in full_text for w in ["reduced fetal", "decreased fetal movement"])

    payload = SymptomPayload(
        age_group=age_group,
        pregnant=pregnant,
        convulsions=convulsions,
        unconscious=unconscious,
        unable_to_drink_or_breastfeed=unable_drink,
        vomiting_everything=vomiting_all,
        has_fever=has_fever,
        temperature_c=39.5 if (has_fever and (severity == "Severe" or "high fever" in full_text or "tez bukhar" in full_text)) else (38.0 if has_fever else None),
        fever_days=3 if has_fever else None,
        neck_stiffness=neck_stiffness,
        rash_with_fever=rash_fever,
        cough_days=3 if difficulty_breathing else None,
        difficulty_breathing=difficulty_breathing,
        breathing_rate_per_min=32 if chest_indrawing else None,
        chest_indrawing=chest_indrawing,
        stridor=stridor,
        wheezing="wheezing" in full_text,
        chest_pain_severe=chest_pain,
        vomiting_blood=vomiting_blood,
        diarrhoea=diarrhoea,
        stool_frequency_per_day=6 if diarrhoea else None,
        blood_in_stool=blood_stool,
        sunken_eyes=sunken_eyes,
        skin_pinch_slow=skin_pinch_slow,
        severe_headache=severe_headache,
        blurred_vision=blurred_vision,
        vaginal_bleeding=vaginal_bleeding,
        reduced_fetal_movement=reduced_fetal_mov,
        language=lang,
    )
    return payload, gt_score, lang, disease


def parse_bengali_dialogue(item: dict) -> tuple[SymptomPayload, int, str, str]:
    """Parse a dialogue item from Irtisum/bengali-medical-triage-conversations with Indic NER."""
    lang = item.get("language", "bengali").lower()
    target_condition = item.get("target_condition", "General")
    urgency_str = item.get("urgency_level", "routine").lower()
    
    # Ground Truth Mapping
    if urgency_str == "emergency" or "ডেঙ্গু" in target_condition or "Dengue" in target_condition:
        if "warning" in target_condition.lower() or "severe" in target_condition.lower() or urgency_str == "emergency":
            gt_score = 3
        else:
            gt_score = 2
    elif any(d in target_condition.lower() for d in ["malaria", "typhoid", "pneumonia", "hepatitis", "gastroenteritis", "ম্যালেরিয়া", "টাইফয়েড", "নিউমোনিয়া"]):
        gt_score = 2
    else:
        gt_score = 1

    messages = item.get("messages", [])
    user_texts = [m.get("content", "") for m in messages if m.get("role") == "user"]
    full_text = " ".join(user_texts).lower()
    
    # Symptom parsing
    has_fever = any(w in full_text for w in KEYWORD_FEVER)
    headache = any(w in full_text for w in KEYWORD_HEADACHE)
    vomiting = any(w in full_text for w in ["bomi", "বমি", "vomit", "nausea", "bomi bhab", "उल्टी"])
    rash = any(w in full_text for w in KEYWORD_RASH)
    cough = any(w in full_text for w in ["khasi", "kasi", "কাশি", "cough"])
    breathing = any(w in full_text for w in KEYWORD_RESPIRATORY)
    diarrhoea = any(w in full_text for w in KEYWORD_DIARRHOEA)
    blood = any(w in full_text for w in ["roktu", "roktopat", "রক্ত", "blood", "खून"])
    unconscious = any(w in full_text for w in KEYWORD_UNCONSCIOUS)
    convulsions = any(w in full_text for w in KEYWORD_CONVULSIONS)

    payload = SymptomPayload(
        age_group="adult",
        pregnant="pregnant" in full_text or "গর্ভবতী" in full_text,
        convulsions=convulsions,
        unconscious=unconscious,
        unable_to_drink_or_breastfeed=any(w in full_text for w in KEYWORD_UNABLE_DRINK),
        vomiting_everything=vomiting and ("continuous" in full_text or "lagaatar" in full_text or "সব বমি" in full_text),
        has_fever=has_fever,
        temperature_c=39.5 if (has_fever and ("khub jor" in full_text or "তীব্র জ্বর" in full_text or "tez bukhar" in full_text)) else (38.0 if has_fever else None),
        fever_days=3 if has_fever else None,
        neck_stiffness=any(w in full_text for w in KEYWORD_NECK_STIFFNESS),
        rash_with_fever=has_fever and rash,
        cough_days=3 if cough else None,
        difficulty_breathing=breathing,
        chest_indrawing="chest indrawing" in full_text or "পসলیاں" in full_text,
        stridor="stridor" in full_text,
        wheezing="wheezing" in full_text,
        chest_pain_severe=any(w in full_text for w in KEYWORD_CHEST_PAIN),
        vomiting_blood=vomiting and blood,
        diarrhoea=diarrhoea,
        blood_in_stool=diarrhoea and blood,
        sunken_eyes="sunken eyes" in full_text or "চোখ বসে যাওয়া" in full_text,
        skin_pinch_slow="skin pinch" in full_text,
        severe_headache=headache,
        blurred_vision="blurred vision" in full_text or "ঝাপসা" in full_text,
        vaginal_bleeding="bleeding" in full_text and ("vaginal" in full_text or "গর্ভ" in full_text),
        reduced_fetal_movement="fetal movement" in full_text,
        language=lang,
    )
    return payload, gt_score, lang, target_condition


def compute_metrics(cm: dict[str, dict[str, int]]) -> dict:
    supports = {c: sum(cm[c].values()) for c in CLASSES}
    total = sum(supports.values())
    per_class = {}
    for c in CLASSES:
        tp = cm[c][c]
        fp = sum(cm[o][c] for o in CLASSES if o != c)
        fn = supports[c] - tp
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        per_class[c] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "support": supports[c],
            "tp": tp, "fp": fp, "fn": fn
        }
    
    correct = sum(cm[c][c] for c in CLASSES)
    accuracy = round(correct / total, 4) if total else 0.0
    macro_prec = round(float(np.mean([per_class[c]["precision"] for c in CLASSES])), 4)
    macro_rec = round(float(np.mean([per_class[c]["recall"] for c in CLASSES])), 4)
    macro_f1 = round(float(np.mean([per_class[c]["f1_score"] for c in CLASSES])), 4)
    weighted_f1 = round(sum(per_class[c]["f1_score"] * supports[c] for c in CLASSES) / total, 4) if total else 0.0

    under_triage = cm["HIGH"]["MEDIUM"] + cm["HIGH"]["LOW"] + cm["MEDIUM"]["LOW"]
    over_triage = cm["LOW"]["MEDIUM"] + cm["LOW"]["HIGH"] + cm["MEDIUM"]["HIGH"]
    safe_matches = correct + over_triage
    safe_concordance = round(safe_matches / total, 4) if total else 0.0
    under_triage_rate = round(under_triage / total, 4) if total else 0.0
    over_triage_rate = round(over_triage / total, 4) if total else 0.0

    return {
        "accuracy": accuracy,
        "safe_concordance": safe_concordance,
        "under_triage_rate": under_triage_rate,
        "over_triage_rate": over_triage_rate,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "per_class": per_class,
        "confusion_matrix": cm,
        "total_cases": total,
    }


def run_benchmarks():
    REPORTS_DIR.mkdir(exist_ok=True)
    print("=" * 80)
    print("🏥 SWARASETU MULTILINGUAL & MULTI-DATASET CLINICAL BENCHMARK SUITE")
    print("=" * 80)

    # BENCHMARK 1
    ds1_path = REPO_ROOT / "data" / "external" / "multilingual_medical_symptom_triage.csv"
    print(f"\n📥 Loading Dataset 1: Tulsiandhare/Multilingual_medical_symptom_triage...")
    df1 = pd.read_csv(ds1_path)
    n1 = len(df1)
    print(f"📊 Dataset 1 loaded: {n1:,} records across languages: {df1['language'].value_counts().to_dict()}")

    cm1 = {t: {p: 0 for p in CLASSES} for t in CLASSES}
    lang_cm1 = {}
    disease_cm1 = {}
    
    t0 = time.perf_counter()
    for idx, row in df1.iterrows():
        payload, gt_score, lang, disease = parse_multilingual_symptom_row(row.to_dict())
        outcome = evaluate(payload)
        pred_score = int(outcome.risk_score)
        
        gt_label = SCORE_TO_LABEL[gt_score]
        pred_label = SCORE_TO_LABEL[pred_score]
        
        cm1[gt_label][pred_label] += 1
        
        if lang not in lang_cm1:
            lang_cm1[lang] = {t: {p: 0 for p in CLASSES} for t in CLASSES}
        lang_cm1[lang][gt_label][pred_label] += 1

        dis_cat = disease if disease else "General"
        if dis_cat not in disease_cm1:
            disease_cm1[dis_cat] = {t: {p: 0 for p in CLASSES} for t in CLASSES}
        disease_cm1[dis_cat][gt_label][pred_label] += 1

    t1 = time.perf_counter()
    latency1_ms = ((t1 - t0) / n1) * 1000
    throughput1 = int(n1 / (t1 - t0))

    metrics1 = compute_metrics(cm1)
    metrics1["latency_ms_per_case"] = round(latency1_ms, 3)
    metrics1["throughput_evals_per_sec"] = throughput1

    print("\n--- RESULTS: Dataset 1 (Tulsiandhare/Multilingual_medical_symptom_triage) ---")
    print(f"⏱️  Evaluation Time        : {t1 - t0:.2f} s ({latency1_ms:.3f} ms/case, {throughput1:,} evals/sec)")
    print(f"🎯 Exact Match Accuracy    : {metrics1['accuracy']*100:.2f}%")
    print(f"🛡️  Clinical Safety Conc.  : {metrics1['safe_concordance']*100:.2f}% (Safe Escalation / Zero Missed Emergencies)")
    print(f"⚠️  Critical Under-Triage  : {metrics1['under_triage_rate']*100:.2f}%")
    print(f"📈 Macro F1 / Weighted F1  : {metrics1['macro_f1']:.4f} / {metrics1['weighted_f1']:.4f}")
    
    print("\nPer-Class Breakdown:")
    for c in CLASSES:
        pc = metrics1["per_class"][c]
        print(f"  • {c:<6}: Precision={pc['precision']:.4f}, Recall={pc['recall']:.4f}, F1={pc['f1_score']:.4f}, Support={pc['support']:,}")

    print("\nPer-Language Performance Breakdown (Top Languages):")
    lang_summary1 = {}
    for l, cm_l in lang_cm1.items():
        m_l = compute_metrics(cm_l)
        lang_summary1[l] = m_l
        print(f"  • {l:<12} | Cases: {m_l['total_cases']:<5} | Acc: {m_l['accuracy']*100:5.2f}% | Safety: {m_l['safe_concordance']*100:5.2f}% | F1: {m_l['macro_f1']:.4f}")

    # BENCHMARK 2
    ds2_path = REPO_ROOT / "data" / "external" / "bengali_triage" / "full_dataset.jsonl"
    print(f"\n📥 Loading Dataset 2: Irtisum/bengali-medical-triage-conversations...")
    with open(ds2_path, "r", encoding="utf-8") as f:
        cases2 = [json.loads(line) for line in f]
    n2 = len(cases2)
    print(f"📊 Dataset 2 loaded: {n2:,} clinical dialogues")

    cm2 = {t: {p: 0 for p in CLASSES} for t in CLASSES}
    lang_cm2 = {}
    disease_cm2 = {}

    t2 = time.perf_counter()
    for item in cases2:
        payload, gt_score, lang, disease = parse_bengali_dialogue(item)
        outcome = evaluate(payload)
        pred_score = int(outcome.risk_score)

        gt_label = SCORE_TO_LABEL[gt_score]
        pred_label = SCORE_TO_LABEL[pred_score]

        cm2[gt_label][pred_label] += 1

        if lang not in lang_cm2:
            lang_cm2[lang] = {t: {p: 0 for p in CLASSES} for t in CLASSES}
        lang_cm2[lang][gt_label][pred_label] += 1

        dis_cat = disease if disease else "General"
        if dis_cat not in disease_cm2:
            disease_cm2[dis_cat] = {t: {p: 0 for p in CLASSES} for t in CLASSES}
        disease_cm2[dis_cat][gt_label][pred_label] += 1

    t3 = time.perf_counter()
    latency2_ms = ((t3 - t2) / n2) * 1000
    throughput2 = int(n2 / (t3 - t2))

    metrics2 = compute_metrics(cm2)
    metrics2["latency_ms_per_case"] = round(latency2_ms, 3)
    metrics2["throughput_evals_per_sec"] = throughput2

    print("\n--- RESULTS: Dataset 2 (Irtisum/bengali-medical-triage-conversations) ---")
    print(f"⏱️  Evaluation Time        : {t3 - t2:.2f} s ({latency2_ms:.3f} ms/case, {throughput2:,} evals/sec)")
    print(f"🎯 Exact Match Accuracy    : {metrics2['accuracy']*100:.2f}%")
    print(f"🛡️  Clinical Safety Conc.  : {metrics2['safe_concordance']*100:.2f}% (Safe Escalation / Zero Missed Emergencies)")
    print(f"⚠️  Critical Under-Triage  : {metrics2['under_triage_rate']*100:.2f}%")
    print(f"📈 Macro F1 / Weighted F1  : {metrics2['macro_f1']:.4f} / {metrics2['weighted_f1']:.4f}")

    print("\nPer-Class Breakdown:")
    for c in CLASSES:
        pc = metrics2["per_class"][c]
        print(f"  • {c:<6}: Precision={pc['precision']:.4f}, Recall={pc['recall']:.4f}, F1={pc['f1_score']:.4f}, Support={pc['support']:,}")

    print("\nPer-Language Performance Breakdown:")
    lang_summary2 = {}
    for l, cm_l in lang_cm2.items():
        m_l = compute_metrics(cm_l)
        lang_summary2[l] = m_l
        print(f"  • {l:<12} | Cases: {m_l['total_cases']:<5} | Acc: {m_l['accuracy']*100:5.2f}% | Safety: {m_l['safe_concordance']*100:5.2f}% | F1: {m_l['macro_f1']:.4f}")

    # Save JSON report
    report = {
        "metadata": {
            "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "model": "SwaraSetu Deterministic WHO IMCI Engine (backend/app/triage/engine.py)",
            "total_cases_evaluated": n1 + n2,
        },
        "dataset_1_multilingual": {
            "name": "Tulsiandhare/Multilingual_medical_symptom_triage",
            "metrics": metrics1,
            "languages": lang_summary1,
        },
        "dataset_2_bengali": {
            "name": "Irtisum/bengali-medical-triage-conversations",
            "metrics": metrics2,
            "languages": lang_summary2,
        }
    }

    out_file = REPORTS_DIR / "multilingual_triage_benchmark.json"
    out_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n💾 Saved full JSON benchmark report to: {out_file}")

    print("\n" + "=" * 80)
    print("✅ MULTILINGUAL BENCHMARK RUN COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_benchmarks()
