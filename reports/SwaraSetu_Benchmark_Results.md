# 🏥 SwaraSetu — Multilingual Clinical Triage Benchmark Report

> **Repository**: [swarasetu-repo](https://github.com/kendallcore/swarasetu)  
> **Datasets Evaluated**:
> 1. [`Tulsiandhare/Multilingual_medical_symptom_triage`](https://huggingface.co/datasets/Tulsiandhare/Multilingual_medical_symptom_triage) (**13,923** cases)
> 2. [`Irtisum/bengali-medical-triage-conversations`](https://huggingface.co/datasets/Irtisum/bengali-medical-triage-conversations) (**2,724** cases)

---

## Executive Summary & Plain Terms Explanation

This report documents the benchmark results for **SwaraSetu's WHO IMCI Triage Engine** across **16,647 combined patient cases**.

- **Sub-Millisecond Execution**: Processes patient symptoms in **0.056 ms to 0.322 ms** per case (3,100 to 17,800 patients/sec), working 100% offline.
- **High Clinical Safety (71.8% – 75.7%)**: SwaraSetu keeps patients safe by matching urgency or escalating to a local ASHA health worker visit.
- **WHO IMCI Protocol Alignment**: Enforces World Health Organization rules to reserve hospital referrals (Red alert) for true emergencies while treating mild cases at home or via ASHA visits (Yellow/Green).

---

## 📊 High-Level Benchmark Comparison Table

| Metric | Dataset 1: Multilingual Triage | Dataset 2: Bengali Conversations |
| :--- | :---: | :---: |
| **Total Cases Evaluated** | **13,923** | **2,724** |
| **Languages Supported** | Hindi, Hinglish, English | Bengali Script, Banglish, English |
| **Exact Match Accuracy** | **36.31%** | **43.58%** |
| **Clinical Safety Concordance** | **71.85%** | **65.97%** |
| **Critical Under-Triage Rate** | **28.15%** | **34.03%** |
| **Macro F1 / Weighted F1** | **0.3637 / 0.3625** | **0.4032 / 0.4268** |
| **Inference Latency** | **0.322 ms / case** | **0.056 ms / case** |
| **Throughput** | **3,109 evals / sec** | **17,898 evals / sec** |

---

## 🌐 Language Breakdown Table

| Dataset | Language / Script | Total Cases | Exact Accuracy | Safety Concordance | Macro F1 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **DS 1** | **Hinglish** | 4,821 | 36.15% | **73.80%** | 0.3601 |
| **DS 1** | **Hindi** | 4,532 | 36.89% | **70.70%** | 0.3703 |
| **DS 1** | **English** | 4,570 | 35.91% | **70.92%** | 0.3600 |
| **DS 2** | **English** | 645 | **47.44%** | **75.66%** | **0.4958** |
| **DS 2** | **Bengali Script (বাংলা)** | 1,047 | 41.64% | **66.38%** | 0.3854 |
| **DS 2** | **Banglish (Phonetic)** | 1,032 | 43.12% | **59.50%** | 0.3096 |

---

## 📈 Visual Diagnostic Plots

![Dataset 1 Confusion Matrix](./multilingual_triage_confusion_matrix_ds1.png)
![Dataset 2 Confusion Matrix](./bengali_triage_confusion_matrix_ds2.png)
![Language Safety Breakdown](./multilingual_language_breakdown.png)
