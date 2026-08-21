#!/usr/bin/env python3
"""External validation runner.

Policy:
  - only registry entries with external_test_allowed: true are eligible (fail-closed);
  - any candidate whose sha256 matches a dataset used in training is rejected as seen;
  - labels are mapped ONLY via the documented, clinically-defensible mapping below
    and source labels are preserved verbatim in outputs;
  - models are NOT modified here; results are recorded for review.

Label mapping for ai_triage_benchmark_78vignettes (Ramaswamy et al. A-D scale):
    A (monitor at home)        -> LOW
    B (doctor within weeks)    -> MEDIUM
    C (care within 24-48h)     -> MEDIUM   (matches SwaraSetu ASHA/clinic-within-24h)
    D (emergency dept now)     -> HIGH     (matches SwaraSetu emergency referral)
Split gold labels (e.g. "C/D") keep their SET; strict metrics use the most severe
element; lenient accuracy credits predictions matching ANY element of the set.
"""

from __future__ import annotations

import csv
import hashlib
import json
import pickle
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "scripts"))

from eval_baseline import CLASSES, prf                       # noqa: E402
from benchmark_protocols import map_ground_truth             # noqa: E402  (unused here but kept for parity docs)
from app.triage.engine import evaluate as imci_evaluate      # noqa: E402
from app.services.sarvam_client import sarvam_client         # noqa: E402

REGISTRY_PATH = REPO_ROOT / "data" / "dataset_registry.yaml"
CONFIG_PATH = REPO_ROOT / "configs" / "experiment_improved.yaml"
OUT_CSV = REPO_ROOT / "reports" / "external_validation.csv"

LETTER_TO_SWARA = {"A": "LOW", "B": "MEDIUM", "C": "MEDIUM", "D": "HIGH"}
SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_models():
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    ckpt = REPO_ROOT / cfg["outputs"]["checkpoint"]
    trained_model = None
    training_hashes: dict[str, dict] = {}
    if ckpt.exists():
        with open(ckpt, "rb") as f:
            bundle = pickle.load(f)
        trained_model = bundle["pipeline"]
        hashes_path = REPO_ROOT / cfg["outputs"]["dataset_hashes"]
        if hashes_path.exists():
            training_hashes = json.loads(hashes_path.read_text())
    return trained_model, training_hashes


def run_improved(model, texts):
    t0 = time.perf_counter()
    preds = list(model.predict(texts))
    return preds, (time.perf_counter() - t0)


def run_imci(texts):
    """Baseline engine via the production text-intake NER path (channels.py)."""
    preds, errors = [], 0
    t0 = time.perf_counter()
    for text in texts:
        try:
            payload = sarvam_client.extract_symptoms_rule_fallback(text, language="en")
            preds.append(SCORE_TO_LABEL[int(imci_evaluate(payload).risk_score)])
        except Exception:
            errors += 1
            preds.append(None)
    return preds, errors, (time.perf_counter() - t0)


SCORE_TO_LABEL = {1: "LOW", 2: "MEDIUM", 3: "HIGH"}


def evaluate_predictions(preds, primary_gts, gold_sets):
    strict_pairs = [(p, g) for p, g in zip(preds, primary_gts) if p is not None]
    n_valid = len(strict_pairs)
    if not n_valid:
        return {}
    correct = sum(1 for p, g in strict_pairs if p == g)
    per = {}
    for c in CLASSES:
        tp = sum(1 for p, g in strict_pairs if p == c and g == c)
        fp = sum(1 for p, g in strict_pairs if p == c and g != c)
        fn = sum(1 for p, g in strict_pairs if p != c and g == c)
        prec, rec, f1 = prf(tp, fp, fn)
        per[c] = (prec, rec, f1, sum(1 for g in primary_gts if g == c))
    macro_f1 = round(sum(v[2] for v in per.values()) / len(CLASSES), 6)
    lenient_correct = sum(
        1 for p, gs in zip(preds, gold_sets) if p is not None and p in gs
    )
    return {
        "accuracy_strict": round(correct / n_valid, 6),
        "accuracy_lenient_anylabel": round(lenient_correct / len(preds), 6) if preds else "",
        "macro_f1": macro_f1,
        "high_precision": per["HIGH"][0],
        "high_recall": per["HIGH"][1],
        "high_f1": per["HIGH"][2],
        "high_support": per["HIGH"][3],
        "high_to_low_errors": sum(1 for p, g in strict_pairs if g == "HIGH" and p == "LOW"),
        "high_to_medium_errors": sum(1 for p, g in strict_pairs if g == "HIGH" and p == "MEDIUM"),
        "n_cases": len(preds),
        "n_inference_errors": sum(1 for p in preds if p is None),
    }


def main() -> int:
    reg = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    datasets = {d["name"]: d for d in reg["datasets"]}
    trained_model, training_hashes = load_models()
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    rows: list[dict] = []

    # ---- available local external test sets ---------------------------------
    for name in ("ai_triage_benchmark_78vignettes",):
        meta = datasets.get(name)
        if meta is None or meta.get("external_test_allowed") is not True:
            print(f"[skip] {name}: external_test_allowed is not true")
            continue
        path = REPO_ROOT / meta.get("local_copy", "")
        if not path.exists():
            rows.append(_row(name, meta, model="all", status="not_available_locally"))
            continue
        digest = sha256_file(path)
        expected = meta.get("local_sha256")
        if expected and expected != digest:
            print(f"[skip] {name}: sha mismatch vs registry — refusing to use.")
            continue
        seen_in = [ds for ds, h in training_hashes.items() if h.get("sha256") == digest]
        if seen_in:
            print(f"[skip] {name}: SEEN DURING TRAINING ({seen_in}) — excluded.")
            rows.append(_row(name, meta, model="all", status=f"excluded_seen_in_training:{','.join(seen_in)}"))
            continue
        print(f"[load] {name} sha256={digest[:12]}… unseen ✓")

        texts, primary_gts, gold_sets, source_labels = _load_vignettes(meta)
        provenance = {
            "source_url": meta.get("url", ""),
            "license": meta.get("license", ""),
            "sha256": digest,
            "fetched_at_utc": fetched_at,
        }
        base_prov = {"dataset_name": name, "model": "", "status": "ok", **provenance}

        # improved model
        if trained_model is not None:
            preds, _ = run_improved(trained_model, texts)
            m = evaluate_predictions(preds, primary_gts, gold_sets)
            rows.append({**base_prov, "model": "improved_tfidf_logreg",
                         "label_mapping": "A>LOW,B>C>MEDIUM,D>HIGH; strict=most-severe of split label",
                         "source_label_distribution": json.dumps(dict(Counter(source_labels))),
                         **m})
        # baseline engine
        preds, errs, elapsed = run_imci(texts)
        m = evaluate_predictions(preds, primary_gts, gold_sets)
        rows.append({**base_prov, "model": "baseline_imci_engine_via_rule_ner",
                     "label_mapping": "same mapping; engine input from production rule-NER fallback",
                     "source_label_distribution": json.dumps(dict(Counter(source_labels))),
                     "latency_seconds": round(elapsed, 3), **m})

    # ---- approved but not downloaded ----------------------------------------
    handled = {"ai_triage_benchmark_78vignettes"}
    for name, meta in datasets.items():
        if meta.get("external_test_allowed") is True and name not in handled:
            rows.append(_row(name, meta, model="all", status="approved_not_downloaded"))

    # ---- write CSV ------------------------------------------------------------
    OUT_CSV.parent.mkdir(exist_ok=True)
    fieldnames = ["dataset_name", "model", "status", "n_cases", "accuracy_strict",
                  "accuracy_lenient_anylabel", "macro_f1", "high_precision", "high_recall",
                  "high_f1", "high_support", "high_to_low_errors", "high_to_medium_errors",
                  "n_inference_errors", "latency_seconds", "source_url", "license",
                  "sha256", "fetched_at_utc", "label_mapping", "source_label_distribution",
                  "notes"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})

    print(f"\nwrote {OUT_CSV} ({len(rows)} rows)")
    for r in rows:
        print(f"- {r['dataset_name']:<36} {r['model']:<34} acc={r.get('accuracy_strict','')} "
              f"HIGH-rec={r.get('high_recall','')} H->L={r.get('high_to_low_errors','')}")
    return 0


def _row(name, meta, model, status):
    return {"dataset_name": name, "model": model, "status": status,
            "source_url": meta.get("url", ""), "license": meta.get("license", "")}


def _load_vignettes(meta):
    path = REPO_ROOT / meta["local_copy"]
    texts, primary_gts, gold_sets, source_labels = [], [], [], []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            gold = [g.strip() for g in row["gold_triage"].split("/")]
            labels = sorted({LETTER_TO_SWARA[g] for g in gold}, key=lambda x: SEVERITY_ORDER[x])
            texts.append(row["input_prompt"])
            gold_sets.append(set(labels))
            primary_gts.append(labels[-1])          # most severe element
            source_labels.append(row["gold_triage"])
    return texts, primary_gts, gold_sets, source_labels


if __name__ == "__main__":
    raise SystemExit(main())
