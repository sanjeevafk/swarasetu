/**
 * Client-side mirror of the deterministic WHO IMCI triage engine
 * (backend/app/triage). Used when the backend is unreachable or the device is
 * in explicit offline mode. Logic must stay 1:1 with the Python engine so
 * offline and online outcomes can never diverge.
 */

import type { RiskLevel, SymptomPayload, TriageOutcome } from '@/types/api';

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
  ];
  const codes = checks.filter(([present]) => present).map(([, code]) => code);

  if (codes.length === 0) {
    return { cluster: 'general', risk_score: 1, rationale_keys: [], red_flag_codes: [], matched: false };
  }
  const keys = ['general_danger_sign'];
  if (codes.includes('severe_chest_pain') || codes.includes('vomiting_blood')) {
    keys.push('severe_chest_pain');
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
