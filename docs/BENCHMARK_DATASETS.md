# SwaraSetu — Benchmark & Training Dataset Catalog

Curated open datasets to strengthen SwaraSetu's evaluation (triage accuracy, ASR WER,
NER F1, under-triage safety) across every pipeline layer. Organized by the benchmark
each dataset improves, with access links and licensing caveats.

---

## 1. Triage / Clinical Decision Benchmarks (IMCI Engine)

| Dataset | Size | Languages | Why it helps | Access |
|---|---|---|---|---|
| **Multilingual Medical Symptom Triage** (Tulsiandhare, HF) | 9,064 cases | Hindi, English, Hinglish | Patient queries → severity/urgency/recommended_action labels + comorbidities, outcomes. Direct eval set for risk-score 1–3 mapping (Home Care / Consult / Emergency ≈ Score 1/2/3). | [HF](https://huggingface.co/datasets/Tulsiandhare/Multilingual_medical_symptom_triage) — open |
| **BODHI-S / BODHI** (Eka Care) | 779 conditions · 4,037 symptom nodes · 13,204 relations | EN (SNOMED-linked) | India-validated symptom→condition graph with per-node triage levels (`emergency`/`worrisome`/`opd_managed`) and Indian demographic likelihoods. Gold grounding for NER normalization + IMCI red-flag logic; GraphRAG-ready. CC BY-NC 4.0. | [HF](https://huggingface.co/datasets/ekacare/BODHI-S) · [GitHub](https://github.com/eka-care/BODHI) |
| **MIETIC** (MIMIC-IV-Ext Triage Corpus) | 9,629 ESI-aligned cases | EN | Instruction-tuning corpus for LLM triage with chief complaints, vitals, history. Map ESI 1–5 → Score 3–1 to cross-validate the deterministic tree against an international standard. PhysioNet credentialed access. | [PhysioNet](https://www.physionet.org/content/mietic/1.0.0/) |
| **Indian Rural Triage Data** (jadhavmanasi70, HF) | 15,091 prompt–completion pairs | Multilingual Indic + dialects | Rural CHW-style scenarios with severity classes and safety-bounded guidance — closest match to ASHA tablet workflow. | [HF](https://huggingface.co/datasets/jadhavmanasi70/indian-rural-triage-data) |
| **Med-Triage Router** (fhai50032, HF) | 2,000 verified tool-calls | EN + Hinglish | Structured JSON triage-router samples (urgency: emergency→routine). Benchmark for the NER→canonical-JSON extraction contract (`{symptom, duration, severity, red_flags}`). | [HF](https://huggingface.co/datasets/fhai50032/latentsig-med-triage-router) |
| **AI Triage Benchmark** (sreerammarimuthu) | 78 physician-labeled vignettes (19 domains) | EN | Publishes the exact metrics SwaraSetu should adopt: **Under-Triage Rate, Over-Triage Rate, Calibration, Faithfulness**. Includes ChatGPT Health baseline from Ramaswamy et al. (Nature Medicine 2026). | [GitHub](https://github.com/sreerammarimuthu/AI-triage-benchmark) |
| **ER-Reason** | 3,984 encounters · 25k notes · 194 SCT cases | EN | Longitudinal ER reasoning benchmark (triage intake → disposition). For advanced disposition-planning evals. Credentialed. | [PhysioNet](https://physionet.org/content/er-reason/1.0.0/) |

**Suggested protocol:** report Accuracy + Under-Triage Rate (=0% target already claimed)
on BODHI-S triage levels, MIETIC ESI mapping, and the 78-vignette set; keep Hinglish
rows of datasets 1 & 5 as a held-out code-mix slice.

## 2. Voice / ASR Benchmarks (Edge `indic-seamless` Tier)

| Dataset | Size | Coverage | Why it helps | Access |
|---|---|---|---|---|
| **IndicVoices** (AI4Bharat) | 23.7K hrs, 11.2K transcribed · 51K speakers · 400+ districts | 22 languages | Natural/spontaneous speech (76% extempore, 15% conversational) — matches IVRS/WhatsApp voice notes far better than read speech. Per-language test splits for WER tables in all 22 languages. | [HF](https://huggingface.co/datasets/ai4bharat/IndicVoices) · [Site](https://ai4bharat.iitm.ac.in/datasets/indicvoices) |
| **Kathbath** | 1,684 hrs · 1,218 speakers · 203 districts | 12 languages | Human-labeled clean ASR benchmark (+ Hard/noisy split) — the de-facto Indic WER yardstick used by Vistaar leaderboard. | [HF](https://huggingface.co/datasets/ai4bharat/Kathbath) |
| **Vistaar** | 59 benchmarks / training sets · 10,700+ hrs | 12 languages | Domain-diverse benchmarks (news, education, GramVaani telephony…) with published IndicWhisper WER baselines to compare quantized on-device models against cloud STT. | [GitHub](https://github.com/ai4bharat/vistaar) |
| **DISPLACE-M** ⭐ | ~35 hrs real consultations (25 train + 10.13 eval) | Hinglish (code-switched), rural India | **Highest-relevance dataset found**: de-identified ASHA↔patient primary-care recordings from rural India — noisy, overlapped, code-mixed. Comes with a challenge task (diarization + SA-ASR + medical-condition extraction, tcpWER metric). Perfect end-to-end benchmark of Voice→NER stage. | [Paper](https://arxiv.org/html/2603.06373) (challenge/CodaBench access) |
| **Shrutilipi** | 6,457 hrs mined audio-text pairs | 12 languages | Large augmentation pool for fine-tuning before quantization. | via AI4Bharat |
| **GramVaani / MUCS 2022** | ~1,000 hrs telephony | hi, bn (+ ta/te in MUCS) | 8 kHz telephone-channel speech = exact IVRS/USSD acoustic conditions (low bandwidth, noise). | [MUCS](https://mucs.aiiit.ac.in/) · Vistaar mirrors |
| **Svarah / Lahaja** (AI4Bharat) | 10 hrs accented EN / dialect benchmarks | EN-Indian + 8 langs | Accent & dialect robustness slices for Tier-2 device testing. | [GitHub](https://github.com/AI4Bharat/Svarah) |

## 3. NLU / NER Benchmarks (Symptom Normalization)

| Dataset | Size | Languages | Why it helps | Access |
|---|---|---|---|---|
| **IHQID-WebMD / IHQID-1mg** | FAQ queries + real Indian hospital queries | en, hi, bn, ta, te, gu, mr | Intent detection + BIO entity tags (drug/disease/treatment) annotated by native speakers; includes *real hospital query* test set. Standard zero-shot vs translate-test protocol for the Sarvam-NER fallback comparison. | [ACL paper](https://aclanthology.org/2023.findings-eacl.140.pdf) · data linked from [arXiv:2302.09685](https://arxiv.org/abs/2302.09685) |
| **IndicMedDialog** | Multi-turn parallel consultations (extends MDDial) | EN + 9 Indic languages | Symptom-elicitation dialogue eval incl. documented failure tiers for ta/te tokenizer gaps — informs the 2-followup-question clarification loop design. | [BioNLP 2026](https://aclanthology.org/2026.bionlp-1.84/) |
| **Indic-Bert-NER-BIO** | ~70K sentences BIO (CTRI/JSL sources) | Hindi + mixed | Medical/pharma entity spans (drug, dosage, route, adverse-event) for augmenting NER training. | [HF](https://huggingface.co/datasets/sharkdodo/Indic-Bert-NER-BIO-Dataset) |
| **DocMate NER Conversations** | 1,954 annotated conversations (SYMPTOM/DIAGNOSIS/MEDICATION/FAMILY_HISTORY) | EN | Character-level clinical-dialogue NER benchmark. | [IEEE DataPort](https://ieee-dataport.org/documents/docmate-annotated-medical-conversations-keyword-extraction-medical-ner-dataset) |

## 4. Epidemiological Priors (Risk-Score Calibration)

| Source | What it gives | Access |
|---|---|---|
| **HMIS item-wise monthly reports** (MoHFW) | District×month counts of fever, diarrhoea, ARI, malaria etc. → prevalence priors so IMCI thresholds reflect local endemicity; also powers the supervisor dashboard's "endemic symptom distribution" claims. Free API/CSV. | [data.gov.in](https://www.data.gov.in/catalog/item-wise-hmis-report-all-states-and-districts-across-months) |
| **NFHS-5 microdata (2019–21)** | 707-district child/maternal health indicators (immunization, anaemia, stunting, CHW contact rates) for demographic risk-vector weighting. Registration required (DHS Program). | [Microdata](https://microdata.worldbank.org/index.php/catalog/4482) · [Factsheets](https://www.data.gov.in/resource/all-india-and-stateut-wise-factsheets-national-family-health-survey-nfhs-5-2019-2021) |
| **WHO GHO IMNCI indicator** | Facility assessment-of-sick-child coverage benchmark to cite in SIH defense docs. | [WHO GHO](https://www.who.int/data/gho/indicator-metadata-registry/imr-details/assessment-for-the-sick-children---5-years-old-based-on-the-integrated-management-of-newborn-and-childhood-illness-criteria) |

## 5. Priority Actions

1. **Adopt the DISPLACE-M task** as the flagship voice-pipeline benchmark (ASHA↔patient Hinglish, tcpWER + condition-extraction F1) — nothing else is closer to production reality.
2. **Report Under-/Over-Triage Rate** (AI-triage-benchmark definitions) alongside existing 0%-under-triage claim, on MIETESI-mapped MIETIC + BODHI-S slices.
3. **Add a Hinglish/code-mix slice** from datasets 1 & 5 (Section 1) to every table in EVALUATION.md.
4. **Calibrate IMCI priors with HMIS district data** and document methodology (defensible vs judges).
5. License check before redistribution: BODHI (CC BY-NC), PhysioNet (credentialed), NFHS (DHS terms) — evaluate, don't re-host.
