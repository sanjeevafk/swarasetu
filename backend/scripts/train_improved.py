#!/usr/bin/env python3
"""Trainer for the improved SwaraSetu triage experiment.

Policy enforcement:
  - every dataset in config `training_data` must exist in data/dataset_registry.yaml
    with training_allowed: true, otherwise training aborts;
  - datasets listed under `forbidden_at_training_time` are never loaded;
  - fixed seed everywhere; liblinear solver is deterministic;
  - the held-out benchmark (triage_protocols_structured.json) is never touched here.
"""

from __future__ import annotations

import hashlib
import json
import pickle
import sys
import time
from pathlib import Path

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs" / "experiment_improved.yaml"
REGISTRY_PATH = REPO_ROOT / "data" / "dataset_registry.yaml"


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def load_registry() -> dict[str, dict]:
    reg = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {d["name"]: d for d in reg["datasets"]}


def main() -> int:
    t0 = time.perf_counter()
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    seed = int(cfg["experiment"]["seed"])
    registry = load_registry()

    # ---- policy gate -------------------------------------------------------
    for entry in cfg["training_data"]:
        meta = registry.get(entry["dataset"])
        if meta is None:
            print(f"FATAL: '{entry['dataset']}' not in registry — refusing to train.")
            return 2
        if meta.get("training_allowed") is not True:
            print(f"FATAL: '{entry['dataset']}' training_allowed={meta.get('training_allowed')!r} — refusing to train.")
            return 2
    forbidden = set(cfg.get("forbidden_at_training_time", []))
    overlap = forbidden & {e["dataset"] for e in cfg["training_data"]}
    if overlap:
        print(f"FATAL: forbidden datasets listed as training data: {overlap}")
        return 2
    print(f"[policy] OK: {[e['dataset'] for e in cfg['training_data']]} are registry-approved for training")

    # ---- load training data --------------------------------------------------
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import FeatureUnion, Pipeline

    frames: list[pd.DataFrame] = []
    hashes: dict[str, dict] = {}
    label_map = cfg["labels"]["source_to_swara"]
    classes = cfg["labels"]["classes"]

    for entry in cfg["training_data"]:
        path = REPO_ROOT / entry["path"]
        if not path.exists():
            print(f"FATAL: missing local copy for approved dataset: {path}")
            return 2
        digest = sha256_file(path)
        hashes[entry["dataset"]] = {
            "path": str(entry["path"]), "sha256": digest,
            "size_bytes": path.stat().st_size,
            "registry_training_allowed": True,
        }
        df = pd.read_csv(path, usecols=[entry["text_field"], entry["label_field"]], dtype=str)
        df = df.dropna(subset=[entry["text_field"], entry["label_field"]])
        df = df.rename(columns={entry["text_field"]: "text", entry["label_field"]: "source_label"})
        df["text"] = df["text"].str.strip()
        df["label"] = df["source_label"].str.strip().map(label_map)
        bad = int(df["label"].isna().sum())
        df = df.dropna(subset=["label"])
        print(f"[data] {entry['dataset']}: {len(df):,} usable rows (dropped {bad} unmapped labels) sha256={digest[:12]}…")
        frames.append(df[["text", "source_label", "label"]])

    data = pd.concat(frames, ignore_index=True).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    dist = data["label"].value_counts().to_dict()
    print(f"[data] total rows: {len(data):,} | class distribution: {dist}")
    if set(dist.keys()) != set(classes):
        print(f"FATAL: expected classes {classes}, found {sorted(dist)}")
        return 2

    # ---- internal stratified holdout (sanity only; NOT the benchmark) --------
    val_frac = float(cfg["validation"]["internal_holdout_fraction"])
    tr_x, va_x, tr_y, va_y = train_test_split(
        data["text"], data["label"], test_size=val_frac,
        random_state=seed, stratify=data["label"],
    )

    # ---- model -----------------------------------------------------------------
    feats = cfg["model"]["features"]
    clf_cfg = cfg["model"]["classifier"]

    def make_clf() -> LogisticRegression:
        return LogisticRegression(
            C=clf_cfg["C"], max_iter=clf_cfg["max_iter"],
            class_weight=clf_cfg["class_weight"], solver=clf_cfg["solver"],
            random_state=seed,
        )

    full_pipeline = Pipeline([
        ("features", FeatureUnion([
            ("word", TfidfVectorizer(
                ngram_range=tuple(feats["word_ngrams"]), analyzer="word",
                min_df=feats["min_df"], max_features=feats["max_features"],
                sublinear_tf=feats["sublinear_tf"])),
            ("char_wb", TfidfVectorizer(
                ngram_range=tuple(feats["char_wb_ngrams"]), analyzer="char_wb",
                min_df=feats["min_df"], max_features=feats["max_features"],
                sublinear_tf=feats["sublinear_tf"])),
        ])),
        ("clf", make_clf()),
    ])

    fit_t0 = time.perf_counter()
    full_pipeline.fit(tr_x, tr_y)
    fit_s = time.perf_counter() - fit_t0

    val_acc = float(full_pipeline.score(va_x, va_y))
    vocab_sizes = {
        name: len(vec.vocabulary_)
        for name, vec in full_pipeline.named_steps["features"].transformer_list
    }
    print(f"[fit] fitted in {fit_s:.1f}s | vocab sizes: {vocab_sizes} | internal holdout accuracy: {val_acc:.4f}")

    # ---- persist run artifacts ---------------------------------------------------
    out = cfg["outputs"]
    run_dir = REPO_ROOT / out["run_dir"]
    run_dir.mkdir(parents=True, exist_ok=True)

    with open(REPO_ROOT / out["checkpoint"], "wb") as f:
        pickle.dump({
            "pipeline": full_pipeline,
            "classes": classes,
            "config_name": cfg["experiment"]["name"],
            "version": cfg["experiment"]["version"],
            "seed": seed,
        }, f)

    preprocessing_info = {
        "normalization": "sklearn TfidfVectorizer defaults (lowercase + accent stripping)",
        "feature_union": {
            "word": {"ngram_range": feats["word_ngrams"], "min_df": feats["min_df"],
                      "max_features": feats["max_features"], "sublinear_tf": feats["sublinear_tf"],
                      "vocabulary_size": vocab_sizes.get("word")},
            "char_wb": {"ngram_range": feats["char_wb_ngrams"], "min_df": feats["min_df"],
                         "max_features": feats["max_features"], "sublinear_tf": feats["sublinear_tf"],
                         "vocabulary_size": vocab_sizes.get("char_wb")},
        },
        "n_train_documents": int(len(tr_x)),
        "n_val_documents": int(len(va_x)),
        "label_mapping_source_to_swara": label_map,
    }
    (REPO_ROOT / out["preprocessing"]).write_text(json.dumps(preprocessing_info, indent=2), encoding="utf-8")

    training_meta = {
        "experiment": cfg["experiment"],
        "model": cfg["model"],
        "labels": cfg["labels"],
        "training_datasets": hashes,
        "forbidden_at_training_time": sorted(forbidden),
        "class_distribution": dist,
        "internal_holdout": {"fraction": val_frac, "accuracy": round(val_acc, 6)},
        "sklearn_version": __import__("sklearn").__version__,
        "python_version": sys.version.split()[0],
        "fit_seconds": round(fit_s, 2),
        "trained_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (REPO_ROOT / out["training_config"]).write_text(json.dumps(training_meta, indent=2), encoding="utf-8")
    (REPO_ROOT / out["dataset_hashes"]).write_text(json.dumps(hashes, indent=2), encoding="utf-8")

    print(f"[save] checkpoint -> {out['checkpoint']}")
    print(f"[save] config/hashes/preprocessing -> {run_dir}")
    print(f"done in {time.perf_counter() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
