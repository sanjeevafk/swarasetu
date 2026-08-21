#!/usr/bin/env python3
"""Build reports/SwaraSetu_Benchmark_Report.pdf from existing artifacts.

Every number is read live from reports/*.json|csv and data/dataset_registry.yaml.
Nothing is hard-coded except section structure and limitation text.
"""

from __future__ import annotations

import base64
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (HRFlowable, Image, KeepTogether, PageBreak,
                                Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "reports"
OUT_PDF = REPORTS / "SwaraSetu_Benchmark_Report.pdf"

DARK = colors.HexColor("#0f172a")
BLUE = colors.HexColor("#0369a1")
GREEN = colors.HexColor("#166534")
RED = colors.HexColor("#b91c1c")
GREY = colors.HexColor("#64748b")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=20, textColor=DARK, spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], alignment=1, textColor=GREY, fontSize=9)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=13, textColor=BLUE,
                    spaceBefore=10, spaceAfter=4)
WARN = ParagraphStyle("WARN", parent=ss["Normal"], fontSize=10, leading=13,
                      textColor=colors.HexColor("#7f1d1d"))
BODY = ParagraphStyle("BODY", parent=ss["Normal"], fontSize=9, leading=12)
SMALL = ParagraphStyle("SMALL", parent=ss["Normal"], fontSize=8, leading=10, textColor=GREY)


def table(data, widths=None, header=True, fs=8, align_right_cols=()):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), fs),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), DARK),
                  ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    for c in align_right_cols:
        style.append(("ALIGN", (c, 1), (c, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


def fmt(v):
    try:
        f = float(v)
        return f"{f:.4f}" if abs(f) <= 1 else f"{int(f):,}"
    except (TypeError, ValueError):
        return str(v or "-")


def confusion_table(cm, title):
    order = ["HIGH", "MEDIUM", "LOW"]
    head = [title, "pred HIGH", "pred MED", "pred LOW", "Σ"]
    rows = [head]
    for t in order:
        r = cm[t]
        rows.append([f"true {t}", r[order[0]], r[order[1]], r[order[2]],
                     sum(r.values())])
    rows.append(["Σ predicted", sum(cm[t]["HIGH"] for t in order),
                 sum(cm[t]["MEDIUM"] for t in order),
                 sum(cm[t]["LOW"] for t in order),
                 sum(sum(cm[t].values()) for t in order)])
    tbl = table(rows, widths=[78, 58, 58, 58, 44], fs=7.5,
                align_right_cols=(1, 2, 3, 4))
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (1, 1), (3, 3), colors.HexColor("#e0f2fe")),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (4, 1), (4, 4), colors.HexColor("#e2e8f0")),
        ("TEXTCOLOR", (0, 4), (-1, 4), colors.black),
    ]))
    return tbl


def build():
    base = json.loads((REPORTS / "baseline_metrics.json").read_text())
    impr = json.loads((REPORTS / "improved_metrics.json").read_text())
    ba_rows = list(csv.DictReader(open(REPORTS / "before_after.csv")))
    lang_rows = list(csv.DictReader(open(REPORTS / "language_benchmark.csv")))
    ext_rows = list(csv.DictReader(open(REPORTS / "external_validation.csv")))
    reg = yaml.safe_load((REPO_ROOT / "data/dataset_registry.yaml").read_text())["datasets"]
    png_ba = REPORTS / "before_after.png"
    png_cm = REPORTS / "baseline_confusion_matrix.png"

    story = []
    story.append(Paragraph("SwaraSetu — Benchmark Report", H1))
    story.append(Paragraph(
        f"deterministic WHO IMCI engine vs trained TF-IDF+LogReg · generated "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · "
        f"commit {__import__('subprocess').check_output(['git','-C',str(REPO_ROOT),'rev-parse','--short','HEAD']).decode().strip()}",
        SUB))
    story.append(Spacer(1, 6))
    warn = Table([[Paragraph(
        "<b>NOT CLINICALLY VALIDATED.</b> Research prototype benchmarked on a synthetic/internal "
        "English case set and one public physician-labeled vignette corpus. Nothing here is evidence "
        "of clinical safety or effectiveness. Do not use for patient care.", WARN)]],
        colWidths=[170 * mm])
    warn.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fee2e2")),
                              ("BOX", (0, 0), (-1, -1), 1, RED),
                              ("LEFTPADDING", (0, 0), (-1, -1), 8),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                              ("TOPPADDING", (0, 0), (-1, -1), 6),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(warn)

    # ---- 1/2 headline metrics -------------------------------------------------
    def perf_block(m, name):
        pc = m["per_class"]
        data = [["Metric", "Value"], ["Accuracy", fmt(m["accuracy"])],
                ["Macro Precision", fmt(m["macro_precision"])],
                ["Macro Recall", fmt(m["macro_recall"])],
                ["Macro F1", fmt(m["macro_f1"])],
                ["Weighted F1", fmt(m["weighted_f1"])],
                ["HIGH precision", fmt(pc["HIGH"]["precision"])],
                ["HIGH recall", fmt(pc["HIGH"]["recall"])],
                ["HIGH F1", fmt(pc["HIGH"]["f1_score"])],
                ["HIGH→LOW errors", fmt(m["high_to_low_errors"])],
                ["HIGH→MEDIUM errors", fmt(m["high_to_medium_errors"])]]
        return KeepTogether([Paragraph(name, H2),
                             table(data, widths=[110, 70], align_right_cols=(1,)),
                             Spacer(1, 3),
                             Paragraph(f"Held-out set: {m['metadata']['dataset']} "
                                       f"({m['metadata']['num_cases']} cases). Model: {m['metadata']['model']}",
                                       SMALL)])

    story.append(perf_block(base, "1. Baseline performance (original pipeline, untouched)"))
    story.append(PageBreak())
    story.append(perf_block(impr, "2. Improved performance (experiment_improved v1)"))

    # ---- 3 before/after --------------------------------------------------------
    story.append(Paragraph("3. Before vs After — identical held-out set", H2))
    data = [["Metric", "Baseline", "Improved", "Δ", "Verdict"]]
    for r in ba_rows:
        data.append([r["metric"], fmt(r["baseline"]), fmt(r["improved"]),
                     fmt(r["delta_improved_minus_baseline"]), r["verdict"]])
    t = table(data, widths=[95, 55, 55, 55, 60], align_right_cols=(1, 2, 3))
    st = [("ALIGN", (4, 1), (4, -1), "CENTER")]
    for ri, r in enumerate(ba_rows, start=1):
        c = GREEN if r["verdict"] == "improved" else (RED if r["verdict"] == "regressed" else GREY)
        st.append(("TEXTCOLOR", (4, ri), (4, ri), c))
        st.append(("FONTNAME", (4, ri), (4, ri), "Helvetica-Bold"))
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Paragraph("Error-count rows: lower is better (see notes column in CSV). "
                           "Two honest regressions: HIGH precision ↓ and HIGH→MEDIUM errors ↑.", SMALL))
    story.append(Spacer(1, 4))
    if png_ba.exists():
        from PIL import Image as PILImage
        w, h = PILImage.open(png_ba).size
        story.append(Image(str(png_ba), width=175 * mm, height=175 * mm * h / w))

    # ---- 4 confusion matrices ----------------------------------------------------
    story.append(Paragraph("4. Confusion matrices (rows = ground truth, columns = predicted)", H2))
    story.append(confusion_table(base["confusion_matrix"]["matrix"],
                                 "Baseline (IMCI engine)"))
    story.append(Spacer(1, 6))
    story.append(confusion_table(impr["confusion_matrix"]["matrix"],
                                 "Improved (TF-IDF + LogReg)"))

    # ---- 5/6 callouts ----------------------------------------------------------------
    story.append(Paragraph("5 & 6. Safety-critical indicators (internal held-out benchmark)", H2))
    hb, hi_, hl = base["per_class"]["HIGH"], impr["per_class"]["HIGH"], None
    call = [["Indicator", "Baseline", "Improved", "Interpretation"],
            ["HIGH-risk recall", f"{hb['recall']*100:.2f}%", f"{hi_['recall']*100:.2f}%",
             "both clinically inadequate (<20%)"],
            ["HIGH→LOW errors", fmt(base["high_to_low_errors"]), fmt(impr["high_to_low_errors"]),
             "missed emergencies triaged to self-care"],
            ["HIGH→MEDIUM errors", fmt(base["high_to_medium_errors"]), fmt(impr["high_to_medium_errors"]),
             "improved model shifts misses upward but still misses"]]
    story.append(table(call, widths=[90, 45, 45, 130]))
    story.append(PageBreak())

    # ---- 7 language -----------------------------------------------------------------
    story.append(Paragraph("7. Language performance (reports/language_benchmark.csv)", H2))
    data = [["Subset", "Eval type", "Model", "n", "Acc", "Macro F1", "HI rec", "H→L err"]]
    for r in lang_rows:
        data.append([r["language_subset"], r["evaluation_type"] or "-",
                     (r["model"] or "-").replace("_via_rule_ner", "*"),
                     str(r.get("n_cases") or "-"), fmt(r.get("accuracy"))[:7],
                     fmt(r.get("macro_f1"))[:7], fmt(r.get("high_recall"))[:7],
                     str(r.get("high_to_low_errors") or "-")])
    story.append(table(data, widths=[62, 52, 118, 30, 40, 42, 40, 38], fs=7))
    story.append(Paragraph("* baseline engine consumes raw text through the production rule-NER "
                           "fallback. Rows marked in_sample were part of improved-model training "
                           "(SYNTHETIC public data) — they are NOT validation results. N/A = no "
                           "labelled data available; nothing fabricated.", SMALL))

    # ---- 8 external validation ---------------------------------------------------------
    story.append(Paragraph("8. External validation (unseen during training)", H2))
    data = [["Dataset", "Model", "n", "Acc(strict)", "Acc(lenient)", "Macro F1", "HI rec", "H→L", "H→M"]]
    for r in ext_rows:
        data.append([r["dataset_name"].replace("_", " ")[:26], r["model"].replace("_", " ")[:24] or "-",
                     str(r.get("n_cases") or "-"), fmt(r.get("accuracy_strict"))[:7],
                     fmt(r.get("accuracy_lenient_anylabel"))[:7], fmt(r.get("macro_f1"))[:7],
                     fmt(r.get("high_recall"))[:7], str(r.get("high_to_low_errors") or "-"),
                     str(r.get("high_to_medium_errors") or "-")])
    story.append(table(data, widths=[100, 105, 22, 40, 42, 38, 36, 25, 25], fs=7))
    story.append(Paragraph("Only ai_triage_benchmark_78vignettes (public GitHub; physician-labeled A–D scale, "
                           "sha256 dd0d6aec…) qualifies as truly unseen external test data today. Mapping: "
                           "A→LOW, B/C→MEDIUM, D→HIGH (documented; source labels preserved). Strict accuracy uses "
                           "the most severe element of split labels; lenient credits any valid label. Other approved "
                           "sets await credentialed/manual access.", SMALL))

    # ---- 9/10 datasets ---------------------------------------------------------------------
    story.append(Paragraph("9 & 10. Dataset sizes and sources (data/dataset_registry.yaml)", H2))

    def badge(d):
        if d["name"] == "swarasetu_triage_protocols_2251":
            return "INTERNAL-BENCHMARK"
        if d["name"].startswith("local_bengali"):
            return "QUARANTINED"
        if "tulsiandhare" in d["name"]:
            return "SYNTHETIC-PUBLIC"
        if d.get("download_policy") == "manual" or d.get("access_requirements") not in (None, "none"):
            return "PUBLIC-CREDENTIALED"
        return "PUBLIC"

    data = [["Dataset", "Badge", "Languages", "Size", "License", "Train/Test/ExtTest"]]
    for d in reg:
        data.append([d["name"].replace("_", " ")[:30], badge(d),
                     ", ".join(d.get("languages", []))[:28] or "-", str(d.get("size", "-"))[:26],
                     str(d.get("license", "-"))[:38],
                     f"{str(bool(d.get('training_allowed')))[0]}/"
                     f"{str(bool(d.get('testing_allowed')))[0]}/"
                     f"{str(bool(d.get('external_test_allowed')))[0]}"])
    story.append(table(data, widths=[104, 66, 92, 82, 128, 56], fs=6.6))
    story.append(Paragraph("Clinical reference material used to BUILD the engine: WHO IMCI protocol "
                           "(published guidelines) — it is not a dataset and confers no validation. "
                           "T/F flags: training/testing/external-test allowed per registry policy.", SMALL))
    story.append(PageBreak())

    # ---- 11 limitations -----------------------------------------------------------------------
    story.append(Paragraph("11. Limitations (read before citing any number above)", H2))
    lims = [
        "<b>No clinical validation.</b> No clinician reviewed outputs; IMCI implementation is untested against real patients.",
        "Internal benchmark provenance is undocumented; legacy GT mapping maps BLACK (deceased) to LOW.",
        "Baseline keyword adapter loses most signal — 91.74% under-triage internally; engine predicts LOW for ~92% of inputs.",
        "Improved model trained ONLY on synthetic multilingual data; its Tulsiandhare numbers are in-sample and optimistic.",
        "External validation covers 78 English vignettes; strict accuracy 32% (improved) / 15% (baseline via rule-NER) — far below deployment thresholds.",
        "Language coverage gap: labelled triage data exists for en/hi/code-mixed only; ta/te/kn/ml/mr/bn/transliteration are N/A, not zero.",
        "Frontend offline engine has drifted from backend (missing snake-bite/trauma rules added in 68bf3b1).",
        "Known latent bug: extract_symptoms_rule_fallback can raise TypeError on pregnant+headache transcripts (invalid field name).",
        "Approved credentialed corpora (MIETIC, MIMIC-IV-ED, Yale ETD, NHAMCS, DISPLACE-M) not yet ingested.",
        "Edge ASR falls back to canned fixture transcripts without ONNX weights; latency figures exclude real decoding.",
    ]
    for i, l in enumerate(lims, 1):
        story.append(Paragraph(f"{i}. {l}", BODY))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.6, color=GREY))
    story.append(Paragraph(
        "Reproduce: see README.md §Benchmarks — eval_baseline.py · train_improved.py · eval_improved.py · "
        "compare_before_after.py · eval_multilingual.py · run_external_validation.py · build_report_pdf.py",
        SMALL))

    doc = SimpleDocTemplate(str(OUT_PDF), pagesize=A4,
                            leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm,
                            title="SwaraSetu Benchmark Report",
                            author="SwaraSetu research")
    doc.build(story)
    print(f"wrote {OUT_PDF}")


if __name__ == "__main__":
    build()
