#!/usr/bin/env python3
"""Train compact zero-dependency Tanglish N-gram weights for offline edge inference."""

from __future__ import annotations

import collections
import csv
import json
import math
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_CSV = REPO_ROOT / "ml/data_tanglish_triage.csv"
OUTPUT_JSON = REPO_ROOT / "ml/data/tanglish_weights.json"
OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

TIER_TO_LEVEL = {"ER_NOW": 3, "CALL_ASHA": 2, "CLINIC_24H": 2, "HOME_CARE": 1}


def tokenize(text: str) -> list[str]:
    text = text.lower()
    words = re.findall(r"[a-zA-Z\u0B80-\u0BFF]+", text)
    tokens = list(words)
    # Word bigrams
    for i in range(len(words) - 1):
        tokens.append(f"{words[i]}_{words[i+1]}")
    # Word trigrams
    for i in range(len(words) - 2):
        tokens.append(f"{words[i]}_{words[i+1]}_{words[i+2]}")
    # Character trigrams and 4-grams for subword root morphology
    for w in words:
        if len(w) >= 3:
            for j in range(len(w) - 2):
                tokens.append(f"#3{w[j:j+3]}")
        if len(w) >= 4:
            for j in range(len(w) - 3):
                tokens.append(f"#4{w[j:j+4]}")
    return tokens


def main():
    rows = []
    with open(DATASET_CSV, "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            t = (r.get("symptom_text") or "").strip()
            tier = (r.get("risk_tier") or "").strip()
            if t and tier in TIER_TO_LEVEL:
                rows.append((t, TIER_TO_LEVEL[tier]))

    counts = collections.Counter()
    for t, _ in rows:
        for tok in tokenize(t):
            counts[tok] += 1

    vocab = {tok for tok, c in counts.items() if c >= 1}

    class_counts = collections.Counter(y for _, y in rows)
    word_counts = {1: collections.Counter(), 2: collections.Counter(), 3: collections.Counter()}
    total_words = {1: 0, 2: 0, 3: 0}

    for text, y in rows:
        for tok in tokenize(text):
            if tok in vocab:
                word_counts[y][tok] += 1
                total_words[y] += 1

    v_size = len(vocab)
    alpha = 0.01
    log_priors = [
        math.log(class_counts[1] / len(rows)),
        math.log(class_counts[2] / len(rows)),
        math.log(class_counts[3] / len(rows)),
    ]

    weights = {}
    for tok in vocab:
        weights[tok] = [
            round(math.log((word_counts[c][tok] + alpha) / (total_words[c] + alpha * v_size)), 4)
            for c in (1, 2, 3)
        ]

    model_data = {"priors": log_priors, "weights": weights}
    OUTPUT_JSON.write_text(json.dumps(model_data, separators=(",", ":")), encoding="utf-8")
    print(f"✓ Saved {len(weights)} features to {OUTPUT_JSON} ({OUTPUT_JSON.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()

