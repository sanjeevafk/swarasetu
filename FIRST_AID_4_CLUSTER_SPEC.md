# SwaraSetu 4-Cluster Triage & First-Aid Specification
**Version:** 2.0 (Agent-Ready Clinical Decision Support Spec)  
**Target:** Rural Healthcare & Edge AI Engine (`backend/app/triage/`, `ml/edge_runner.py`)  
**Standard:** Aligned with WHO IMCI, Indian MoHFW Guidelines, and Kaggle First-Aid Intents adaptation

---

## 1. Executive Overview

This specification maps and standardizes conversational first-aid and symptom data into **4 Deterministic Clinical Clusters** designed for zero-internet rural healthcare environments.

```
                               ┌─────────────────────────────────────────┐
                               │  Spoken Patient Audio / Text Intake     │
                               │  (Hindi, Tamil, Bengali, English)       │
                               └────────────────────┬────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │  Keyword NER & Entity Normalizer        │
                               │  (`normalize_symptoms` / Lexicon)       │
                               └────────────────────┬────────────────────┘
                                                    │
             ┌──────────────────────┬───────────────┴──────────────┬──────────────────────┐
             ▼                      ▼                              ▼                      ▼
    ┌─────────────────┐    ┌─────────────────┐            ┌─────────────────┐    ┌─────────────────┐
    │  Cluster 1      │    │  Cluster 2      │            │  Cluster 3      │    │  Cluster 4      │
    │  Respiratory &  │    │  Febrile,       │            │  Trauma, Bites  │    │  GI, Poison &   │
    │  Airway         │    │  Infection &    │            │  & Surface      │    │  Environmental  │
    │  Distress       │    │  Meningitis     │            │  Injuries       │    │  Emergencies    │
    └────────┬────────┘    └────────┬────────┘            └────────┬────────┘    └────────┬────────┘
             │                      │                              │                      │
             └──────────────────────┴───────────────┬──────────────┴──────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │  3-Tier Severity & Escalation Ladder    │
                               ├─────────────────────────────────────────┤
                               │  Score 1: Self-Care & First-Aid         │
                               │  Score 2: ASHA Worker Visit (24h)       │
                               │  Score 3: Emergency PHC / 108 Route     │
                               └─────────────────────────────────────────┘
```

---

## 2. The 4 Clinical Clusters & Severity Ladders

### Cluster 1: Respiratory & Airway Distress (`respiratory`)
*Derived from dataset intents: `Cough`, `Choking`, `Asthma / Breathing Difficulties` + WHO IMCI ARI.*

| Severity Rung | Clinical Indicator | Risk Score | Immediate Action |
|---|---|---|---|
| **Emergency (Red)** | Stridor, Chest indrawing, Complete airway obstruction/choking, Cyanosis (blue lips) | **Score 3** | Immediate Heimlich / clear airway, oxygen dispatch, emergency PHC referral |
| **Urgent (Yellow)** | Fast breathing (age-dependent), cough $>14$ days, persistent wheezing, moderate breathlessness | **Score 2** | ASHA worker pulse oximetry & respiratory rate check within 24h |
| **Self-Care (Green)** | Mild cough $\le 14$ days, clear nasal discharge, normal breathing rate | **Score 1** | Warm fluids, steam inhalation, home rest, red-flag monitoring |

---

### Cluster 2: Febrile, Sepsis & Systemic Infections (`fever`)
*Derived from dataset intents: `Fever`, `Meningitis Signs`, `Seizures / Fits`, `Malaria / Dengue Suspicion`.*

| Severity Rung | Clinical Indicator | Risk Score | Immediate Action |
|---|---|---|---|
| **Emergency (Red)** | Neonate fever ($<2$ months), Stiff neck (meningitis), Febrile convulsions/fits, Temperature $\ge 39.5^\circ\text{C}$ with lethargy | **Score 3** | Urgent antibiotic/antipyretic protocol at nearest PHC/CHC |
| **Urgent (Yellow)** | Fever $>7$ days, Fever with petechial rash (dengue suspect), Fever in malaria-endemic region | **Score 2** | ASHA worker RDT (Rapid Diagnostic Test) for malaria + fever charting |
| **Self-Care (Green)** | Mild fever $<7$ days, alert child, drinking fluids well | **Score 1** | Tepid sponging, Paracetamol syrup (weight-based), ORS/hydration |

---

### Cluster 3: Trauma, Envenomation & Surface Injuries (`trauma_firstaid`)
*Derived from dataset intents: `Snake Bite`, `Animal / Dog Bite`, `Severe Burns`, `Heavy Bleeding`, `Fractures`, `Sprains / Cuts`.*

| Severity Rung | Clinical Indicator | Risk Score | Immediate Action |
|---|---|---|---|
| **Emergency (Red)** | Snake bite (venomous suspect), Arterial spurting / uncontrolled bleeding, 2nd/3rd degree burns $>10\%$ body area, Open compound fracture | **Score 3** | Immobilize limb, pressure bandage (for bleeding), zero tourniquet (for snake bite), direct 108/PHC anti-venom dispatch |
| **Urgent (Yellow)** | Stray dog/animal bite (Rabies risk Category II/III), deep laceration needing sutures, suspected closed bone fracture | **Score 2** | Wash with soap & running water 15 min; ASHA facilitates PHC Rabies vaccine & Tetanus shot |
| **Self-Care (Green)** | Minor abrasion, superficial cut, mild 1st-degree burn (sunburn/erythema), minor sprain | **Score 1** | Wash with clean water, antiseptic dressing, R.I.C.E protocol (Rest, Ice, Compression, Elevation) |

---

### Cluster 4: Gastrointestinal, Toxins & Environmental Emergencies (`gi_environmental`)
*Derived from dataset intents: `Diarrhea / Dehydration`, `Poisoning / Chemical Ingestion`, `Heatstroke`, `Severe Vomiting`.*

| Severity Rung | Clinical Indicator | Risk Score | Immediate Action |
|---|---|---|---|
| **Emergency (Red)** | Severe dehydration (sunken eyes + skin pinch $>2$s), Ingestion of pesticide/chemical/poison, Heatstroke (high temp + no sweating + confusion), Vomiting blood | **Score 3** | Do NOT induce vomiting for corrosive poisons; position recovery, IV fluids at PHC |
| **Urgent (Yellow)** | Dysentery (blood in stool), $>6$ watery stools/day, heat exhaustion (cramps, heavy sweating), mild dehydration | **Score 2** | ASHA supplies Zinc tablets + ORS packets, hydration tracking |
| **Self-Care (Green)** | Watery diarrhoea $<5$ times/day with good fluid intake, mild nausea, mild heat fatigue | **Score 1** | WHO-Standard ORS preparation at home, continuous breastfeeding/fluids |

---

## 3. Multilingual Keyword Lexicon (`LEXICON`)

For integration into `backend/app/triage/` and `ml/edge_runner.py`:

```python
FIRST_AID_LEXICON: dict[str, dict[str, tuple[str, ...]]] = {
    # --- Cluster 1: Respiratory & Airway ---
    "choking": {
        "en": ("choking", "food stuck in throat", "cannot breathe", "gasping"),
        "hi": ("गले में कुछ अटक गया", "दम घुट रहा है", "सांस रुक गई"),
        "ta": ("தொண்டையில் அடைப்பு", "மூச்சு அடைக்கிறது"),
        "bn": ("গলায় কিছু আটকেছে", "দম বন্ধ হয়ে আসছে"),
    },
    "asthma_difficulty_breathing": {
        "en": ("asthma attack", "heavy breathing", "chest indrawing", "shortness of breath"),
        "hi": ("सांस फूलना", "दमा", "पसली चलना", "सांस लेने में भारी तकलीफ"),
        "ta": ("ஆஸ்துமா", "மூச்சுத் திணறல்", "நெஞ்சு கூடு இறங்குதல்"),
        "bn": ("হাঁপানি", "শ্বাসকষ্ট", "বুকের খাঁচা ডেবে যাওয়া"),
    },

    # --- Cluster 2: Fever & Sepsis ---
    "fever_convulsions": {
        "en": ("fever fit", "febrile seizure", "fever shaking"),
        "hi": ("बुखार में झटके", "बुखार का दौरा", "आंखें उलट जाना"),
        "ta": ("காய்ச்சல் வலிப்பு", "ஜுர வலிப்பு"),
        "bn": ("জ্বরের খিঁচুনি", "জ্বরে কাঁপুনি"),
    },
    "stiff_neck": {
        "en": ("stiff neck", "neck pain with fever", "cannot bend neck"),
        "hi": ("गर्दन में अकड़न", "गर्दन नहीं मुड़ रही"),
        "ta": ("கழுத்து விறைப்பு", "கழுத்து திருப்ப முடியவில்லை"),
        "bn": ("ঘাড় শক্ত হয়ে যাওয়া",),
    },

    # --- Cluster 3: Trauma, Envenomation & Surface ---
    "snake_bite": {
        "en": ("snake bite", "snake venom", "bitten by snake"),
        "hi": ("सांप ने काटा", "सर्पदंश", "सांप का जहर"),
        "ta": ("பாம்பு கடி", "பாம்பு தீண்டியது"),
        "bn": ("সাপের কামড়", "সাপে কেটেছে"),
    },
    "animal_bite": {
        "en": ("dog bite", "monkey bite", "rabies risk", "animal scratch"),
        "hi": ("कुत्ते ने काटा", "बंदर ने काटा", "पागल कुत्ता"),
        "ta": ("நாய் கடி", "விலங்கு கடி"),
        "bn": ("কুকুরের কামড়", "পাগলা কুকুর"),
    },
    "severe_burn": {
        "en": ("hot oil burn", "fire burn", "boiling water burn", "skin blister"),
        "hi": ("आग से जला", "गर्म तेल से जलना", "उबलते पानी से जला", "छाले पड़ गए"),
        "ta": ("தீக்காயம்", "சுடுநீர் காயம்"),
        "bn": ("আগুনে পোড়া", "গরম তেলের পোড়া"),
    },
    "heavy_bleeding": {
        "en": ("bleeding heavily", "blood not stopping", "deep cut"),
        "hi": ("खून बहना बंद नहीं हो रहा", "गहरा घाव", "खून की धार"),
        "ta": ("ரத்தம் நிற்கவில்லை", "ஆழமான வெட்டு"),
        "bn": ("রক্ত বন্ধ হচ্ছে না", "গভীর ক্ষত"),
    },

    # --- Cluster 4: GI, Poisoning & Environmental ---
    "poison_ingestion": {
        "en": ("swallowed poison", "drank pesticide", "kerosene ingestion", "chemical drink"),
        "hi": ("कीटनाशक पी लिया", "जहर खा लिया", "मिट्टी का तेल पी लिया", "दवाई ज्यादा खा ली"),
        "ta": ("விஷம் குடித்துவிட்டார்", "பூச்சிக்கொல்லி மருந்து", "மண்ணெண்ணெய்"),
        "bn": ("বিষ খেয়েছে", "কীটনাশক খেয়েছে", "কেরোসিন খেয়েছে"),
    },
    "heat_stroke": {
        "en": ("heat stroke", "sun stroke", "fainted in hot sun", "high fever no sweat"),
        "hi": ("लू लग गई", "धूप में बेहोश", "लू लगना"),
        "ta": ("சூரிய வெப்ப பக்கவாதம்", "வெயில் மயக்கம்"),
        "bn": ("সানস্ট্রোক", "লু লাগা", "রোদে অজ্ঞান"),
    },
    "severe_diarrhoea_dehydration": {
        "en": ("sunken eyes", "loose motion 10 times", "no urine 8 hours", "skin pinch slow"),
        "hi": ("आंखें धंस गई", "पानी जैसे पतले दस्त", "पेशाब नहीं हुआ", "चमड़ी ढीली"),
        "ta": ("கண்கள் குழிவிழுந்தது", "நீர் கழிச்சல்", "சிறுநீர் போகவில்லை"),
        "bn": ("চোখ বসে গেছে", "ঘন ঘন পাতলা পায়খানা", "প্রস্রাব বন্ধ"),
    },
}
```

---

## 4. Canonical Python Data Contract (`types.py`)

```python
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class RiskScore(IntEnum):
    SELF_CARE = 1          # Green: Home care & first-aid
    ASHA_DISPATCH = 2      # Yellow: CHW/ASHA visit within 24h
    EMERGENCY_REFERRAL = 3  # Red: Immediate PHC / 108 referral


@dataclass(frozen=True)
class FirstAidSymptomPayload:
    # Cluster 1: Respiratory & Airway
    choking: bool = False
    stridor_or_indrawing: bool = False
    fast_breathing: bool = False
    cough_days: Optional[int] = None

    # Cluster 2: Fever & Sepsis
    has_fever: bool = False
    fever_days: Optional[int] = None
    temperature_c: Optional[float] = None
    febrile_convulsion: bool = False
    neck_stiffness: bool = False
    petechial_rash: bool = False

    # Cluster 3: Trauma, Bites & Surface Injuries
    snake_bite: bool = False
    animal_bite: bool = False
    severe_burn_or_scald: bool = False
    uncontrolled_bleeding: bool = False
    suspected_fracture: bool = False
    minor_cut_or_burn: bool = False

    # Cluster 4: GI, Poisoning & Environmental
    poison_ingestion: bool = False
    heat_stroke: bool = False
    watery_diarrhoea: bool = False
    stool_frequency: Optional[int] = None
    blood_in_stool: bool = False
    severe_dehydration_signs: bool = False

    # Provenance
    age_group: str = "child"
    language: str = "hi"
```

---

## 5. Ground-Truth Test Benchmarks (JSON)

Use these test cases in `backend/conftest.py` and `ml/edge_runner.py` to evaluate pipeline accuracy:

```json
[
  {
    "scenario_id": "FA_C3_001",
    "cluster": "trauma_firstaid",
    "language": "hi",
    "spoken_query": "खेत में काम करते समय सांप ने पैर में काट लिया है तुरंत मदद चाहिए",
    "extracted_payload": {
      "snake_bite": true,
      "age_group": "adult"
    },
    "expected_risk_score": 3,
    "expected_action": "PHC_ANTIVENOM_EMERGENCY_DISPATCH",
    "first_aid_guidance_en": "Immobilize limb. Keep bitten area below heart level. Do not apply tourniquet or cut wound. Proceed immediately to nearest PHC with Anti-Snake Venom (ASV)."
  },
  {
    "scenario_id": "FA_C3_002",
    "cluster": "trauma_firstaid",
    "language": "bn",
    "spoken_query": "পাড়ার একটি কুকুর হাতে কামড়ে রক্ত বের করে দিয়েছে",
    "extracted_payload": {
      "animal_bite": true,
      "age_group": "child"
    },
    "expected_risk_score": 2,
    "expected_action": "ASHA_RABIES_VACCINE_REFERRAL",
    "first_aid_guidance_en": "Wash wound immediately with soap and running water for 15 minutes. ASHA notified for PHC Rabies post-exposure prophylaxis."
  },
  {
    "scenario_id": "FA_C4_003",
    "cluster": "gi_environmental",
    "language": "hi",
    "spoken_query": "बच्चे ने गलती से कीटनाशक की दवा पी ली है और बेहोश हो रहा है",
    "extracted_payload": {
      "poison_ingestion": true,
      "age_group": "child"
    },
    "expected_risk_score": 3,
    "expected_action": "EMERGENCY_TOXICOLOGY_108",
    "first_aid_guidance_en": "Do NOT induce vomiting. Place in recovery position on side. Emergency transport to CHC/District Hospital immediately."
  },
  {
    "scenario_id": "FA_C1_004",
    "cluster": "respiratory",
    "language": "ta",
    "spoken_query": "குழந்தைக்கு சாப்பிடும் போது தொண்டையில் முள்ளு மாட்டி மூச்சு அடைக்குது",
    "extracted_payload": {
      "choking": true,
      "age_group": "child"
    },
    "expected_risk_score": 3,
    "expected_action": "EMERGENCY_AIRWAY_REFERRAL",
    "first_aid_guidance_en": "Perform 5 back blows followed by 5 chest thrusts. Call emergency services immediately."
  }
]
```

---

## 6. Coding Agent Handoff Checklist

When implementing this variant into the SwaraSetu repository:

1. **Step 1:** Extend [`backend/app/triage/types.py`](file:///home/lildosa/Project/swarasetu/backend/app/triage/types.py) with the trauma and poison danger-sign attributes.
2. **Step 2:** Add `evaluate_trauma()` and `evaluate_gi_environmental()` into [`backend/app/triage/clusters.py`](file:///home/lildosa/Project/swarasetu/backend/app/triage/clusters.py).
3. **Step 3:** Append multilingual first-aid audio strings and rationale keys into [`backend/app/triage/messages.py`](file:///home/lildosa/Project/swarasetu/backend/app/triage/messages.py).
4. **Step 4:** Integrate `FIRST_AID_LEXICON` into [`ml/edge_runner.py`](file:///home/lildosa/Project/swarasetu/ml/edge_runner.py) to enable on-device offline first-aid normalization.
5. **Step 5:** Run `pytest backend/` and `python ml/edge_runner.py --benchmark 50` to verify zero latency regression.
