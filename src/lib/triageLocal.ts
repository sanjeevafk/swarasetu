/**
 * Client-side mirror of the deterministic WHO IMCI triage engine
 * (backend/app/triage). Used when the backend is unreachable or the device is
 * in explicit offline mode. Logic must stay 1:1 with the Python engine so
 * offline and online outcomes can never diverge.
 */

import type { RiskLevel, SymptomPayload, TriageOutcome, LanguageCode } from '@/types/api';

const FAST_BREATHING_THRESHOLDS: Record<string, number> = {
  neonate: 60,
  infant: 50,
  child: 40,
  adolescent: 30,
  adult: 24,
};

const COUGH_URI_DAYS_MAX = 14;
const STOOL_HEAVY_PER_DAY = 8;

interface ClusterFinding {
  cluster: string;
  risk_score: 1 | 2 | 3;
  rationale_keys: string[];
  red_flag_codes: string[];
  matched: boolean;
}

function evaluateGeneralDangerSigns(p: SymptomPayload): ClusterFinding {
  const checks: [boolean, string][] = [
    [p.convulsions, 'convulsions'],
    [p.unconscious, 'unconscious'],
    [p.unable_to_drink_or_breastfeed, 'unable_to_drink'],
    [p.vomiting_everything, 'vomiting_everything'],
    [p.chest_pain_severe, 'severe_chest_pain'],
    [p.vomiting_blood, 'vomiting_blood'],
    [p.acute_poisoning_or_bite, 'acute_poisoning_or_bite'],
    [p.severe_trauma, 'severe_trauma'],
  ];
  const codes = checks.filter(([present]) => present).map(([, code]) => code);

  if (codes.length === 0) {
    return { cluster: 'general', risk_score: 1, rationale_keys: [], red_flag_codes: [], matched: false };
  }
  const keys = ['general_danger_sign'];
  if (codes.includes('severe_chest_pain') || codes.includes('vomiting_blood')) {
    keys.push('severe_chest_pain');
  }
  if (codes.includes('acute_poisoning_or_bite')) {
    keys.push('snake_bite_emergency');
  }
  if (codes.includes('severe_trauma')) {
    keys.push('severe_trauma_burn');
  }
  return { cluster: 'general', risk_score: 3, rationale_keys: keys, red_flag_codes: codes, matched: true };
}


function evaluateFever(p: SymptomPayload): ClusterFinding {
  const measured = p.temperature_c !== null && p.temperature_c >= 37.5;
  if (!p.has_fever && !measured) {
    return { cluster: 'fever', risk_score: 1, rationale_keys: [], red_flag_codes: [], matched: false };
  }

  if (p.age_group === 'neonate') {
    return {
      cluster: 'fever',
      risk_score: 3,
      rationale_keys: ['neonatal_fever'],
      red_flag_codes: ['neonatal_fever'],
      matched: true,
    };
  }
  if (p.neck_stiffness) {
    return {
      cluster: 'fever',
      risk_score: 3,
      rationale_keys: ['fever_neck_stiffness_meningitis'],
      red_flag_codes: ['neck_stiffness_meningitis'],
      matched: true,
    };
  }
  if (p.convulsions) {
    return {
      cluster: 'fever',
      risk_score: 3,
      rationale_keys: ['fever_convulsions'],
      red_flag_codes: ['febrile_convulsions'],
      matched: true,
    };
  }

  const redFlags: string[] = [];
  const keys: string[] = [];
  if (p.rash_with_fever) {
    redFlags.push('fever_with_rash');
    keys.push('fever_rash_urgent');
  }
  const highOrProlonged =
    (p.temperature_c !== null && p.temperature_c >= 39.0) ||
    (p.fever_days !== null && p.fever_days > 7);

  if (!redFlags.length && !highOrProlonged && !p.malaria_risk_area) {
    return { cluster: 'fever', risk_score: 1, rationale_keys: ['fever_self_care'], red_flag_codes: [], matched: true };
  }

  if (highOrProlonged) keys.push('fever_high_or_prolonged');
  if (p.malaria_risk_area) keys.push('malaria_risk_fever');

  return { cluster: 'fever', risk_score: 2, rationale_keys: keys, red_flag_codes: redFlags, matched: true };
}

function evaluateRespiratory(p: SymptomPayload): ClusterFinding {
  const present =
    p.cough_days !== null ||
    p.difficulty_breathing ||
    p.breathing_rate_per_min !== null ||
    p.chest_indrawing ||
    p.stridor ||
    p.wheezing;
  if (!present) {
    return { cluster: 'respiratory', risk_score: 1, rationale_keys: [], red_flag_codes: [], matched: false };
  }

  if (p.stridor) {
    return {
      cluster: 'respiratory',
      risk_score: 3,
      rationale_keys: ['resp_severe_distress'],
      red_flag_codes: ['stridor'],
      matched: true,
    };
  }
  if (p.chest_indrawing) {
    return {
      cluster: 'respiratory',
      risk_score: 3,
      rationale_keys: ['resp_severe_distress'],
      red_flag_codes: ['chest_indrawing'],
      matched: true,
    };
  }

  const threshold = FAST_BREATHING_THRESHOLDS[p.age_group] ?? FAST_BREATHING_THRESHOLDS.child;
  const fastBreathing = p.breathing_rate_per_min !== null && p.breathing_rate_per_min >= threshold;
  if (fastBreathing) {
    return {
      cluster: 'respiratory',
      risk_score: 2,
      rationale_keys: ['resp_fast_breathing_pneumonia'],
      red_flag_codes: ['fast_breathing'],
      matched: true,
    };
  }

  if (p.difficulty_breathing) {
    return {
      cluster: 'respiratory',
      risk_score: 2,
      rationale_keys: ['resp_fast_breathing_pneumonia'],
      red_flag_codes: ['breathing_difficulty_reported'],
      matched: true,
    };
  }

  if (p.cough_days !== null) {
    if (p.cough_days <= COUGH_URI_DAYS_MAX) {
      return { cluster: 'respiratory', risk_score: 1, rationale_keys: ['resp_uri_self_care'], red_flag_codes: [], matched: true };
    }
    return {
      cluster: 'respiratory',
      risk_score: 2,
      rationale_keys: ['resp_fast_breathing_pneumonia'],
      red_flag_codes: ['prolonged_cough'],
      matched: true,
    };
  }

  return { cluster: 'respiratory', risk_score: 1, rationale_keys: ['resp_uri_self_care'], red_flag_codes: [], matched: true };
}

function evaluateDiarrhoea(p: SymptomPayload): ClusterFinding {
  if (!p.diarrhoea && p.stool_frequency_per_day === null) {
    return { cluster: 'diarrhoea', risk_score: 1, rationale_keys: [], red_flag_codes: [], matched: false };
  }

  const severeSigns = (p.sunken_eyes ? 1 : 0) + (p.skin_pinch_slow ? 1 : 0);
  if (severeSigns === 2) {
    return {
      cluster: 'diarrhoea',
      risk_score: 3,
      rationale_keys: ['diarrhoea_severe_dehydration'],
      red_flag_codes: ['severe_dehydration'],
      matched: true,
    };
  }

  const dysentery = p.blood_in_stool;
  const heavyFrequency = p.stool_frequency_per_day !== null && p.stool_frequency_per_day >= STOOL_HEAVY_PER_DAY;
  const someDehydration = p.restless_irritable || severeSigns === 1 || p.unable_to_drink_or_breastfeed;

  if (someDehydration || dysentery || heavyFrequency) {
    const codes: string[] = [];
    if (dysentery) codes.push('blood_in_stool_dysentery');
    if (someDehydration) codes.push('some_dehydration');
    if (heavyFrequency) codes.push('frequent_stools');
    return {
      cluster: 'diarrhoea',
      risk_score: 2,
      rationale_keys: ['diarrhoea_some_dehydration_or_dysentery'],
      red_flag_codes: codes,
      matched: true,
    };
  }

  return { cluster: 'diarrhoea', risk_score: 1, rationale_keys: ['diarrhoea_no_dehydration'], red_flag_codes: [], matched: true };
}

function evaluateMaternal(p: SymptomPayload): ClusterFinding {
  if (!p.pregnant) {
    return { cluster: 'maternal', risk_score: 1, rationale_keys: [], red_flag_codes: [], matched: false };
  }

  if (p.severe_headache && p.blurred_vision) {
    return { cluster: 'maternal', risk_score: 3, rationale_keys: ['maternal_emergency'], red_flag_codes: ['pre_eclampsia'], matched: true };
  }
  if (p.severe_headache || p.blurred_vision) {
    return { cluster: 'maternal', risk_score: 2, rationale_keys: ['maternal_emergency'], red_flag_codes: ['maternal_headache_or_visual'], matched: true };
  }
  if (p.vaginal_bleeding) {
    return { cluster: 'maternal', risk_score: 3, rationale_keys: ['maternal_emergency'], red_flag_codes: ['vaginal_bleeding'], matched: true };
  }
  if (p.reduced_fetal_movement) {
    return { cluster: 'maternal', risk_score: 3, rationale_keys: ['maternal_emergency'], red_flag_codes: ['reduced_fetal_movement'], matched: true };
  }
  if (p.convulsions) {
    return { cluster: 'maternal', risk_score: 3, rationale_keys: ['maternal_emergency'], red_flag_codes: ['eclampsia_convulsions'], matched: true };
  }
  return { cluster: 'maternal', risk_score: 1, rationale_keys: [], red_flag_codes: [], matched: true };
}

/** English action templates mirroring messages.ACTIONS['en'] in the backend. */
const ACTION_TEXT: Record<string, string> = {
  act_refer_phc_now: 'Go to the nearest PHC/hospital immediately; share coordinates and contact number.',
  act_call_ambulance: 'Call the 108 ambulance service right away.',
  act_notify_asha: 'ASHA worker alerted for a visit within 24 hours.',
  act_paracetamol_home_care:
    'Give paracetamol as per weight, plenty of fluids, and monitor temperature twice daily.',
  act_return_if_worse:
    'Return immediately if breathing worsens, fever rises, or new danger signs appear.',
  act_ors_fluids: 'Start ORS solution and continue frequent small feeds/breastfeeding.',
  act_monitor_home: 'Monitor at home; no referral needed at this time.',
  act_zinc_supplement: 'Give zinc supplement for 14 days as advised by the health worker.',
};

const RATIONALE_TEXT: Record<string, string> = {
  general_danger_sign: 'A general danger sign was detected. This needs emergency care now.',
  severe_chest_pain: 'Severe chest pain with vomiting blood can indicate a medical emergency.',
  snake_bite_emergency: 'Snake bite or acute envenomation is a critical life-threatening emergency. Immediate anti-venom at nearest PHC is required.',
  severe_trauma_burn: 'Severe injury, major burn, or trauma requires immediate emergency medical care and hospital stabilization.',
  fever_neck_stiffness_meningitis:
    'Fever with neck stiffness suggests possible meningitis and must be referred immediately.',
  fever_convulsions: 'Convulsions with fever are a danger sign requiring immediate referral.',
  fever_rash_urgent:
    'Fever with rash may signal dengue or another urgent infection needing assessment.',
  neonatal_fever: 'Fever in a baby under 2 months is always treated as serious; refer now.',
  fever_high_or_prolonged: 'High or prolonged fever needs assessment within 24 hours by a health worker.',
  malaria_risk_fever: 'In a malaria-prone area this fever needs testing and ASHA follow-up today.',
  fever_self_care: 'Mild fever without danger signs can be managed safely at home.',
  resp_severe_distress:
    'Chest indrawing or noisy breathing (stridor) means severe respiratory distress — refer immediately.',
  resp_fast_breathing_pneumonia:
    'Fast breathing indicates possible pneumonia; an ASHA worker should assess within 24 hours.',
  resp_uri_self_care: 'Short cough without fast breathing looks like a common cold; home care suffices.',
  diarrhoea_severe_dehydration: 'Signs of severe dehydration from diarrhoea detected — immediate referral needed.',
  diarrhoea_some_dehydration_or_dysentery:
    'Some dehydration or blood in stool detected; ASHA assessment needed within 24 hours with ORS guidance.',
  diarrhoea_no_dehydration: 'Diarrhoea without dehydration signs; continue ORS and feeding at home.',
  maternal_emergency:
    'Maternal danger sign detected — this is an obstetric emergency requiring immediate referral.',
  no_symptoms_matched:
    'No concerning symptoms matched the IMCI protocol; monitor at home and return if things worsen.',
};

const RED_FLAG_DESCRIPTIONS: Record<string, string> = {
  convulsions: 'Convulsions / fits',
  unconscious: 'Unconsciousness or lethargy',
  unable_to_drink: 'Unable to drink or breastfeed',
  vomiting_everything: 'Vomiting everything',
  severe_chest_pain: 'Severe chest pain',
  vomiting_blood: 'Vomiting blood (haematemesis)',
  acute_poisoning_or_bite: 'Snake bite / acute envenomation / poisoning',
  severe_trauma: 'Severe trauma, fracture, or major burn injury',
  neonatal_fever: 'Fever in baby under 2 months',
  neck_stiffness_meningitis: 'Fever with neck stiffness (suspected meningitis)',
  febrile_convulsions: 'Fever with convulsions',
  fever_with_rash: 'Fever with rash (possible dengue/measles)',
  stridor: 'Stridor — noisy breathing on inspiration',
  chest_indrawing: 'Lower chest wall indrawing',
  fast_breathing: 'Fast breathing for age (possible pneumonia)',
  breathing_difficulty_reported: 'Reported difficulty breathing',
  prolonged_cough: 'Cough lasting more than 14 days',
  severe_dehydration: 'Severe dehydration (sunken eyes + slow skin pinch)',
  some_dehydration: 'Some dehydration signs',
  blood_in_stool_dysentery: 'Blood in stool (dysentery)',
  frequent_stools: 'Very frequent stools (>=8/day)',
  pre_eclampsia: 'Severe headache with blurred vision (pre-eclampsia)',
  maternal_headache_or_visual: 'Headache or visual disturbance in pregnancy',
  vaginal_bleeding: 'Vaginal bleeding in pregnancy',
  reduced_fetal_movement: 'Reduced fetal movement',
  eclampsia_convulsions: 'Convulsions in pregnancy (possible eclampsia)',
};


function actionsFor(risk: 1 | 2 | 3, primaryCluster: string): string[] {
  let keys: string[];
  if (risk === 1) {
    keys =
      primaryCluster === 'diarrhoea'
        ? ['act_ors_fluids', 'act_zinc_supplement', 'act_monitor_home', 'act_return_if_worse']
        : primaryCluster === 'fever'
          ? ['act_paracetamol_home_care', 'act_monitor_home', 'act_return_if_worse']
          : ['act_monitor_home', 'act_return_if_worse'];
  } else if (risk === 2) {
    keys = ['act_notify_asha', 'act_return_if_worse'];
  } else {
    keys = ['act_refer_phc_now', 'act_call_ambulance'];
  }
  return keys.map((k) => ACTION_TEXT[k]);
}

/**
 * Deterministic local evaluation — mirrors backend evaluate().
 */
export function evaluateLocal(payload: SymptomPayload): TriageOutcome {
  const findings: ClusterFinding[] = [
    evaluateGeneralDangerSigns(payload),
    evaluateFever(payload),
    evaluateRespiratory(payload),
    evaluateDiarrhoea(payload),
    evaluateMaternal(payload),
  ];

  const maxRisk = Math.max(...findings.map((f) => f.risk_score)) as 1 | 2 | 3;
  const matched = findings.filter((f) => f.matched);
  const ordered: ClusterFinding[] = [];
  for (const tier of [3, 2, 1] as const) {
    for (const f of matched) {
      if (f.risk_score === tier) ordered.push(f);
    }
  }
  const primary = matched.find((f) => f.risk_score === maxRisk);

  const rationaleKeys: string[] = [];
  const redFlagCodes: string[] = [];
  for (const f of ordered) {
    for (const k of f.rationale_keys) {
      if (!rationaleKeys.includes(k)) rationaleKeys.push(k);
    }
    for (const c of f.red_flag_codes) {
      if (!redFlagCodes.includes(c)) redFlagCodes.push(c);
    }
  }

  return {
    risk_score: maxRisk as RiskLevel,
    rationale_keys: rationaleKeys.length ? rationaleKeys : ['no_symptoms_matched'],
    rationale_en:
      (rationaleKeys.length ? rationaleKeys : ['no_symptoms_matched'])
        .map((k) => RATIONALE_TEXT[k])
        .filter(Boolean)
        .join(' ') || RATIONALE_TEXT.no_symptoms_matched,
    actions: actionsFor(maxRisk, primary?.cluster ?? 'none'),
    red_flags: redFlagCodes.map((code) => ({
      code,
      description_en: RED_FLAG_DESCRIPTIONS[code] ?? code.replace(/_/g, ' '),
    })),
    primary_cluster: primary?.cluster ?? 'none',
  };
}

/**
 * Localized clinical directives matching the score and cluster.
 */
export function buildDirective(risk: RiskLevel, primaryCluster: string, lang: LanguageCode = 'hi'): { type: 'self_care' | 'asha_dispatch' | 'phc_referral'; message_en: string; message_local: string } {
  if (risk === 3) {
    const msgs: Record<LanguageCode, string> = {
      hi: 'अति आवश्यक आपातकाल! तुरंत नजदीकी प्राथमिक स्वास्थ्य केंद्र (PHC) या अस्पताल जाएं। 108 एम्बुलेंस को अलर्ट कर दिया गया है।',
      ta: 'அவசரநிலை! உடனடியாக அருகிலுள்ள ஆரம்ப சுகாதார நிலையத்திற்கு (PHC) செல்லவும். 108 ஆம்புலன்ஸ் எச்சரிக்கை அனுப்பப்பட்டது.',
      bn: 'মারাত্মক জরুরি অবস্থা! অবিলম্বে নিকটস্থ স্বাস্থ্যকেন্দ্রে (PHC) যান। ১০৮ অ্যাম্বুলেন্সকে জানানো হয়েছে।',
      en: 'CRITICAL EMERGENCY: Immediate referral to nearest PHC / Hospital. 108 Emergency Ambulance pre-alerted.',
    };
    return {
      type: 'phc_referral',
      message_en: 'CRITICAL EMERGENCY: Immediate referral to nearest PHC / Hospital. 108 Emergency Ambulance pre-alerted.',
      message_local: msgs[lang] || msgs.hi,
    };
  }

  if (risk === 2) {
    const msgs: Record<LanguageCode, string> = {
      hi: 'आशा स्वास्थ्य कार्यकर्ता को अलर्ट भेजा गया! आशा दीदी (सुनीता देवी) 24 घंटे के भीतर घर आकर जांच करेंगी।',
      ta: 'ஆஷா சுகாதாரப் பணியாளருக்கு தகவல் அனுப்பப்பட்டது! 24 மணி நேரத்திற்குள் வீட்டுப் பரிசோதனை மேற்கொள்ளப்படும்.',
      bn: 'আশা স্বাস্থ্য কর্মীকে সতর্কবার্তা পাঠানো হয়েছে! ২৪ ঘণ্টার মধ্যে বাড়িতে এসে স্বাস্থ্য পরীক্ষা করা হবে।',
      en: 'ASHA Health Worker Alerted for home assessment within 24 hours. Keep patient resting and hydrated.',
    };
    return {
      type: 'asha_dispatch',
      message_en: 'ASHA Health Worker Alerted for home assessment within 24 hours. Keep patient resting and hydrated.',
      message_local: msgs[lang] || msgs.hi,
    };
  }

  // Score 1 (Self-Care)
  const detailHi = primaryCluster === 'fever'
    ? 'हल्का बुखार: घरेलू देखभाल और आराम की सलाह। पैरासिटामोल दें और पर्याप्त पानी पिलाएं।'
    : primaryCluster === 'diarrhoea'
    ? 'दस्त: ओआरएस (ORS) घोल दें और तरल पदार्थ पिलाते रहें। स्वच्छता का ध्यान रखें।'
    : 'घरेलू देखभाल और निगरानी की सलाह। यदि लक्षण 3 दिन से ज्यादा रहें या बढ़ें तो स्वास्थ्य केंद्र जाएं।';

  const detailTa = primaryCluster === 'fever'
    ? 'லேசான காய்ச்சல்: வீட்டுப் பராமரிப்பு, ஓய்வு மற்றும் பாராசிட்டமால் கொடுக்கவும்.'
    : 'வீட்டுப் பராமரிப்பு மற்றும் ஓய்வு அறிவுறுத்தப்படுகிறது. அறிகுறிகள் தீவிரமடைந்தால் PHC செல்லவும்.';

  const detailBn = primaryCluster === 'fever'
    ? 'হালকা জ্বর: বাড়িতে বিশ্রাম ও প্রচুর তরল খাবার দিন। প্রয়োজনে প্যারাসিটামল দিন।'
    : 'বাড়িতে যত্ন ও পর্যবেক্ষণ করুন। লক্ষণ বাড়লে স্বাস্থ্যকেন্দ্রে যোগাযোগ করুন।';

  const detailEn = primaryCluster === 'fever'
    ? 'Mild fever: Safe home management with rest, hydration, and paracetamol.'
    : 'Self-Care & Home Monitoring advised. Rest and oral fluids. Visit PHC if symptoms worsen.';

  const msgs: Record<LanguageCode, string> = {
    hi: detailHi,
    ta: detailTa,
    bn: detailBn,
    en: detailEn,
  };

  return {
    type: 'self_care',
    message_en: detailEn,
    message_local: msgs[lang] || msgs.hi,
  };
}

/**
 * 4-Pillar Emergency Dispatch generator for Score 3 critical cases.
 */
export function buildEmergencyDispatch(outcome: TriageOutcome, lang: LanguageCode = 'hi') {
  if (outcome.risk_score !== 3) return null;

  const hasKey = (...k: string[]) => outcome.rationale_keys.some((rk) => k.includes(rk));
  const hasFlag = (...c: string[]) => outcome.red_flags.some((f) => c.includes(f.code));

  let protocol_key = 'general_emergency';
  let title = 'Emergency Clinical Protocol';
  let cad_priority = 'CRITICAL_P1';
  let ambulance_type = '108 Emergency ALS Unit';
  let phc_readiness = 'Pre-alerted Duty Medical Officer & Resuscitation Bay';
  let steps: string[] = [];

  if (hasKey('snake_bite_emergency') || hasFlag('acute_poisoning_or_bite')) {
    protocol_key = 'snake_bite_emergency';
    title = 'Snake Bite & Acute Envenomation Protocol';
    ambulance_type = '108 ALS Emergency Ambulance';
    phc_readiness = 'Prepare Anti-Snake Venom (ASV) & Oxygen Support';
    const stepsMap: Record<LanguageCode, string[]> = {
      hi: [
        '🚑 108 एम्बुलेंस: स्वचालित CAD SOS डिस्पैच टिकट जनरेट किया गया।',
        '👩‍⚕️ PHC अलर्ट: स्थानीय प्राथमिक स्वास्थ्य केंद्र पर एंटी-वेनम (ASV) तैयार रखने का अलर्ट भेजा गया।',
        '🩹 मरीज को स्थिर रखें: मरीज को शांत और लेटाकर रखें। हिलने-डुलने से जहर तेजी से फैलता है।',
        '🚫 क्या न करें: काटे गए स्थान को चीरें, चूसें या बर्फ न लगाएं। टाइट पट्टी न बांधें।',
        '🛡️ अंग को स्थिर रखें: प्रभावित अंग को दिल के स्तर से नीचे सहारा देकर रखें।',
      ],
      ta: [
        '🚑 108 ஆம்புலன்ஸ்: தானியங்கி SOS அவசர டிக்கெட் உருவாக்கப்பட்டது.',
        '👩‍⚕️ PHC எச்சரிக்கை: ஆன்டி-வெனம் (ASV) மருந்து தயார் செய்ய தகவல் அனுப்பப்பட்டது.',
        '🩹 அமைதியாக படுக்க வைக்கவும்: அசைந்தால் விஷம் உடலில் வேகமாக பரவும்.',
        '🚫 செய்யக்கூடாதவை: கடித்த இடத்தில் கீறவோ, உறிஞ்சவோ, ஐஸ் வைக்கவோ கூடாது.',
        '🛡️ உறுப்பை இதய மட்டத்திற்கு கீழே அசைவின்றி வைக்கவும்.',
      ],
      bn: [
        '🚑 ১০৮ অ্যাম্বুলেন্স: স্বয়ংক্রিয় জরুরি ডিসপ্যাচ টিকিট তৈরি হয়েছে।',
        '👩‍⚕️ PHC সতর্কতা: অ্যান্টি-ভেনম প্রস্তুত রাখতে বার্তা পাঠানো হয়েছে।',
        '🩹 রোগীকে স্থির রাখুন: রোগীকে শুইয়ে শান্ত রাখুন। নড়াচড়া করলে বিষ দ্রুত ছড়ায়।',
        '🚫 নিষেধ: ক্ষতস্থান কাটবেন না, চুষবেন না বা বরফ দেবেন না।',
        '🛡️ আক্রান্ত অঙ্গ হৃদপিন্ডের নিচে স্থির রাখুন।',
      ],
      en: [
        '🚑 108 CAD Ambulance: Automated SOS emergency dispatch ticket logged.',
        '👩‍⚕️ PHC Pre-Alert: Alerted duty physician to prepare Anti-Snake Venom (ASV).',
        '🩹 Keep Patient Still: Keep patient lying flat and calm; movement accelerates venom absorption.',
        '🚫 Strict Don\'ts: Do NOT cut, suck, ice, or tightly tourniquet the wound.',
        '🛡️ Immobilize: Keep bitten limb immobilized below heart level.',
      ],
    };
    steps = stepsMap[lang] || stepsMap.hi;
  } else if (hasKey('severe_chest_pain') || hasFlag('severe_chest_pain', 'vomiting_blood')) {
    protocol_key = 'severe_chest_pain';
    title = 'Acute Coronary & Severe Distress Protocol';
    ambulance_type = '108 Cardiac ICU Ambulance';
    phc_readiness = 'Prepare ECG Bay, Oxygen & Sublingual Sorbitrate';
    const stepsMap: Record<LanguageCode, string[]> = {
      hi: [
        '🚑 108 एम्बुलेंस: आपातकालीन कार्डियक लाइफ-सपोर्ट यूनिट रवाना।',
        '👩‍⚕️ PHC अलर्ट: ड्यूटी डॉक्टर को ECG वार्ड तैयार रखने की सूचना दी गई।',
        '🩹 स्थिति: मरीज को आराम से बैठाकर रखें और तंग कपड़े ढीले करें।',
        '💊 प्राथमिक उपचार: यदि उपलब्ध हो और एलर्जी न हो, तो 300mg एस्पिरिन चबाने को दें।',
        '🚫 मरीज को चलना-फिरना या कोई शारीरिक श्रम बिल्कुल न करने दें।',
      ],
      ta: [
        '🚑 108 ஆம்புலன்ஸ்: தீவிர இதய சிகிச்சை ஆம்புலன்ஸ் அனுப்பப்பட்டது.',
        '👩‍⚕️ PHC எச்சரிக்கை: அவசர பிரிவு மருத்துவர் ECG தயார் செய்ய எச்சரிக்கப்பட்டார்.',
        '🩹 நிலை: நோயாளியை சாய்ந்த நிலையில் அமர வைக்கவும். ஆடைகளை தளர்த்தவும்.',
        '💊 முதலுதவி: ஒவ்வாமை இல்லையெனில் 300mg ஆஸ்பிரின் மெல்ல கொடுக்கவும்.',
        '🚫 நோயாளியை நடக்கவோ சிரமப்படவோ விடாதீர்கள்.',
      ],
      bn: [
        '🚑 ১০৮ অ্যাম্বুলেন্স: কার্ডিয়াক আইসিইউ অ্যাম্বুলেন্স রওনা হয়েছে।',
        '👩‍⚕️ PHC সতর্কতা: জরুরি ডাক্তারকে ইসিজি বে প্রস্তুত রাখতে বলা হয়েছে।',
        '🩹 রোগীকে হেলান দিয়ে বসিয়ে রাখুন এবং জামাকাপড় ঢিলে করুন।',
        '💊 অ্যালার্জি না থাকলে ৩০০ মিলিগ্রাম অ্যাসপিরিন চিবিয়ে খেতে দিন।',
        '🚫 রোগীকে কোনোরকম শারীরিক পরিশ্রম বা হাঁটাহাঁটি করতে দেবেন না।',
      ],
      en: [
        '🚑 108 Ambulance: Emergency Cardiac CAD ticket initiated.',
        '👩‍⚕️ PHC Pre-Alert: Alerted emergency duty doctor to prepare ECG bay.',
        '🩹 Position: Keep patient seated upright in comfortable leaning position. Loosen tight clothing.',
        '💊 First Aid: Administer 300mg chewable Aspirin if available and not allergic.',
        '🚫 Strict Don\'ts: Do NOT allow patient to walk, stand, or perform physical exertion.',
      ],
    };
    steps = stepsMap[lang] || stepsMap.hi;
  } else if (hasKey('resp_severe_distress') || hasFlag('stridor', 'chest_indrawing')) {
    protocol_key = 'respiratory_emergency';
    title = 'Severe Respiratory Distress Protocol';
    ambulance_type = '108 Oxygen Support Ambulance';
    phc_readiness = 'Prepare Nebulizer, Oxygen Hood & Pediatric Resuscitation';
    const stepsMap: Record<LanguageCode, string[]> = {
      hi: [
        '🚑 108 एम्बुलेंस: ऑक्सीजन युक्त आपातकालीन एम्बुलेंस डिस्पैच।',
        '👩‍⚕️ PHC अलर्ट: बाल चिकित्सा एवं ऑक्सीजन वार्ड को तुरंत सक्रिय किया गया।',
        '🩹 स्थिति: बच्चे को गोद में सीधा बैठाकर रखें, वायुमार्ग खुला रखें।',
        '🚫 जबरन खाना या ठोस आहार न खिलाएं।',
        '🛡️ तुरंत निकटतम स्वास्थ्य केंद्र पहुंचें।',
      ],
      ta: [
        '🚑 108 ஆம்புலன்ஸ்: ஆக்ஸிஜன் வசதியுடன் கூடிய ஆம்புலன்ஸ் அனுப்பப்பட்டது.',
        '👩‍⚕️ PHC எச்சரிக்கை: தீவிர ஆக்ஸிஜன் சிகிச்சை தயார் செய்யப்பட்டுள்ளது.',
        '🩹 நிலை: குழந்தையை நேராக அமர வைக்கவும், மூச்சுக்குழாயை சீராக வைக்கவும்.',
        '🚫 திட உணவுகளை கொடுக்க வேண்டாம்.',
        '🛡️ உடனடியாக அருகில் உள்ள மருத்துவமனைக்கு செல்லவும்.',
      ],
      bn: [
        '🚑 ১০৮ অ্যাম্বুলেন্স: অক্সিজেন সমৃদ্ধ অ্যাম্বুলেন্স পাঠানো হয়েছে।',
        '👩‍⚕️ PHC সতর্কতা: পেডিয়াট্রিক ও অক্সিজেন ইউনিট প্রস্তুত রাখা হয়েছে।',
        '🩹 শিশুকে সোজা করে কোলে বসিয়ে রাখুন, শ্বাসনালী খোলা রাখুন।',
        '🚫 কোনো শক্ত খাবার খাওয়াবেন না।',
        '🛡️ দ্রুত নিকটস্থ স্বাস্থ্যকেন্দ্রে নিয়ে যান।',
      ],
      en: [
        '🚑 108 Ambulance: Oxygen-equipped emergency unit dispatched.',
        '👩‍⚕️ PHC Pre-Alert: Pediatric oxygen and nebulization bay prepared.',
        '🩹 Position: Keep child seated upright in lap; ensure airway remains clear.',
        '🚫 Do NOT force-feed or give solid foods.',
        '🛡️ Proceed immediately to the nearest PHC / Hospital.',
      ],
    };
    steps = stepsMap[lang] || stepsMap.hi;
  } else {
    // General emergency / convulsions / trauma
    const stepsMap: Record<LanguageCode, string[]> = {
      hi: [
        '🚑 108 एम्बुलेंस: आपातकालीन जीवन रक्षक वाहन डिस्पैच।',
        '👩‍⚕️ PHC अलर्ट: आपातकालीन ड्यूटी डॉक्टर को तैयार रहने की सूचना दी गई।',
        '🩹 मरीज को सुरक्षित स्थिति में रखें और वायुमार्ग खुला रखें।',
        '🚫 मरीज के मुंह में कोई चम्मच या कपड़ा न डालें।',
        '🛡️ तुरंत नजदीकी अस्पताल के लिए प्रस्थान करें।',
      ],
      ta: [
        '🚑 108 ஆம்புலன்ஸ்: அவசர உயிர் காக்கும் வாகனம் அனுப்பப்பட்டது.',
        '👩‍⚕️ PHC எச்சரிக்கை: அவசர மருத்துவர் தயார் நிலையில் உள்ளார்.',
        '🩹 நோயாளியை பாதுகாப்பான நிலையில் வைக்கவும்.',
        '🚫 வாயில் எந்த பொருளையும் திணிக்க வேண்டாம்.',
        '🛡️ உடனடியாக மருத்துவமனைக்கு புறப்படவும்.',
      ],
      bn: [
        '🚑 ১০৮ অ্যাম্বুলেন্স: জরুরি জীবনরক্ষাকারী অ্যাম্বুলেন্স পাঠানো হয়েছে।',
        '👩‍⚕️ PHC সতর্কতা: জরুরি ডাক্তারকে প্রস্তুত থাকতে বলা হয়েছে।',
        '🩹 রোগীকে নিরাপদ স্থানে রাখুন ও শ্বাসনালী পরিষ্কার রাখুন।',
        '🚫 মুখে কোনো বস্তু বা চামচ দেবেন না।',
        '🛡️ অবিলম্বে হাসপাতালের দিকে রওনা দিন।',
      ],
      en: [
        '🚑 108 Ambulance: Emergency Life Support CAD ticket dispatched.',
        '👩‍⚕️ PHC Pre-Alert: Emergency medical officer on standby.',
        '🩹 Keep patient safe, on side (recovery position) with clear airway.',
        '🚫 Do NOT insert any objects into mouth.',
        '🛡️ Proceed to the nearest hospital facility immediately.',
      ],
    };
    steps = stepsMap[lang] || stepsMap.hi;
  }

  const randomTicket = Math.floor(1000 + Math.random() * 9000);

  return {
    is_emergency: true,
    protocol_key,
    title,
    ticket_id: `108-CAD-${randomTicket}`,
    cad_priority,
    ambulance_type,
    phc_readiness,
    steps,
    map_url: 'https://maps.google.com/?q=26.4468,85.3402',
  };
}
