/**
 * API contract types mirroring backend/app/schemas (Pydantic v2).
 * Keep in sync with the backend — single source of truth for both layers.
 */

export type AgeGroup = 'neonate' | 'infant' | 'child' | 'adolescent' | 'adult';
export type LanguageCode = 'en' | 'hi' | 'ta' | 'bn';
export type RiskLevel = 1 | 2 | 3;

/** Canonical structured symptom payload (NER output contract). */
export interface SymptomPayload {
  age_group: AgeGroup;
  pregnant: boolean;
  convulsions: boolean;
  unconscious: boolean;
  unable_to_drink_or_breastfeed: boolean;
  vomiting_everything: boolean;
  has_fever: boolean;
  temperature_c: number | null;
  fever_days: number | null;
  neck_stiffness: boolean;
  rash_with_fever: boolean;
  malaria_risk_area: boolean;
  cough_days: number | null;
  difficulty_breathing: boolean;
  breathing_rate_per_min: number | null;
  chest_indrawing: boolean;
  stridor: boolean;
  wheezing: boolean;
  chest_pain_severe: boolean;
  vomiting_blood: boolean;
  diarrhoea: boolean;
  stool_frequency_per_day: number | null;
  blood_in_stool: boolean;
  sunken_eyes: boolean;
  skin_pinch_slow: boolean;
  restless_irritable: boolean;
  severe_headache: boolean;
  blurred_vision: boolean;
  vaginal_bleeding: boolean;
  reduced_fetal_movement: boolean;
  language: LanguageCode;
}

export function emptyPayload(language: LanguageCode = 'en'): SymptomPayload {
  return {
    age_group: 'child',
    pregnant: false,
    convulsions: false,
    unconscious: false,
    unable_to_drink_or_breastfeed: false,
    vomiting_everything: false,
    has_fever: false,
    temperature_c: null,
    fever_days: null,
    neck_stiffness: false,
    rash_with_fever: false,
    malaria_risk_area: false,
    cough_days: null,
    difficulty_breathing: false,
    breathing_rate_per_min: null,
    chest_indrawing: false,
    stridor: false,
    wheezing: false,
    chest_pain_severe: false,
    vomiting_blood: false,
    diarrhoea: false,
    stool_frequency_per_day: null,
    blood_in_stool: false,
    sunken_eyes: false,
    skin_pinch_slow: false,
    restless_irritable: false,
    severe_headache: false,
    blurred_vision: false,
    vaginal_bleeding: false,
    reduced_fetal_movement: false,
    language,
  };
}

export interface RedFlag {
  code: string;
  description_en: string;
}

export interface TriageOutcome {
  risk_score: RiskLevel;
  rationale_keys: string[];
  rationale_en: string;
  actions: string[];
  red_flags: RedFlag[];
  primary_cluster: string;
}

export type DirectiveType = 'self_care' | 'asha_dispatch' | 'phc_referral';

export interface Directive {
  type: DirectiveType;
  message_en: string;
}

export interface PHCNearby {
  id: number;
  name: string;
  district: string;
  facility_type: string;
  phone: string;
  distance_km: number;
  hours: string;
  is_24x7: boolean;
  doctor_available: boolean;
  latitude: number;
  longitude: number;
}

export interface TriageEvaluateRequest {
  payload: SymptomPayload;
  client_uuid: string;
  district?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export interface TriageEvaluateResponse {
  case_id: number | null;
  client_uuid: string;
  outcome: TriageOutcome;
  directive: Directive;
  nearest_phc: PHCNearby | null;
}

export interface SyncCaseItem {
  client_uuid: string;
  payload: SymptomPayload;
  district?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  created_at?: string | null;
  client_risk_score?: RiskLevel | null;
}

export interface SyncResponse {
  accepted: number;
  duplicates: number;
  total: number;
}

export interface AnalyticsSummary {
  total_cases: number;
  risk_distribution: { green: number; yellow: number; red: number };
  symptom_breakdown: { cluster: string; count: number }[];
  districts: {
    district: string;
    volume: number;
    red_cases: number;
    fever: number;
    respiratory: number;
    diarrhoea: number;
    maternal: number;
    other: number;
  }[];
  recent_cases: {
    id: number;
    client_uuid: string;
    created_at: string | null;
    age_group: string;
    language: string;
    district: string | null;
    risk_score: number;
    primary_cluster: string;
    source: string;
  }[];
}
