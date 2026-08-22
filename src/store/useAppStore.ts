import { create } from 'zustand';
import { defaultScenarios, type SymptomScenario } from '@/data/mockSymptoms';
import type {
  AgeGroup,
  LanguageCode,
  RiskLevel,
  SymptomPayload,
  TriageOutcome,
  TriageEvaluateResponse,
} from '@/types/api';
import { emptyPayload, sanitizePayload } from '@/types/api';

import { api, ApiUnreachableError } from '@/lib/api';
import { evaluateLocal, buildDirective, buildEmergencyDispatch } from '@/lib/triageLocal';
import { normalizeTranscript } from '@/lib/edge/sttRunner';
import { countQueued, enqueue, flushOutbox } from '@/lib/outbox';
import { mockPHCs } from '@/data/mockPHCs';

export type UserRole = 'Patient' | 'CHW' | 'Supervisor';
export type AppLanguage = 'Hindi' | 'Tamil' | 'Bengali';

export const LANGUAGE_CODE: Record<AppLanguage, LanguageCode> = {
  Hindi: 'hi',
  Tamil: 'ta',
  Bengali: 'bn',
};

export interface ChatMessage {
  id?: string;
  type: 'bot' | 'user_text' | 'audio' | 'stt';
  text?: string;
  duration?: number;
  script?: string;
  english?: string;
  timestamp?: string;
}

export interface ActiveEvaluation {
  outcome: TriageOutcome;
  directive: TriageEvaluateResponse['directive'] | null;
  nearest_phc: TriageEvaluateResponse['nearest_phc'];
  emergency_dispatch?: TriageEvaluateResponse['emergency_dispatch'];
  evaluatedOffline: boolean;
}

export interface PatientCaseRecord {
  id: string;
  patientName: string;
  age: string;
  village: string;
  lastUpdated: string;
  symptomSummary: string;
  riskScore: RiskLevel;
  primaryCluster: string;
  status: 'needs_visit' | 'visited' | 'emergency_dispatched' | 'monitoring';
  isCurrentActive: boolean;
}

interface AppState {
  isDemoActive: boolean;
  activeRole: UserRole;
  activeLanguage: AppLanguage;
  currentScenario: SymptomScenario;
  demoProgress: number; // 0: Start, 1: Audio, 2: STT, 3: NER, 4: IMCI, 5: Map
  isOfflineMode: boolean;

  // Shared synchronized conversation
  messages: ChatMessage[];
  inputText: string;
  setInputText: (text: string) => void;
  addMessage: (msg: ChatMessage) => void;
  setMessages: (msgs: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => void;
  resetChat: () => void;

  // Live evaluation state
  isEvaluating: boolean;
  isSyncing: boolean;
  activeEvaluation: ActiveEvaluation | null;
  backendOnline: boolean | null; // null = unknown / not probed yet
  pendingSyncCount: number;

  // ASHA Case Synchronization
  patientCases: PatientCaseRecord[];
  activePatientId: string;
  setActivePatientId: (id: string) => void;
  markCaseStatus: (id: string, status: PatientCaseRecord['status']) => void;

  startDemo: (role: UserRole) => void;
  setLanguage: (lang: AppLanguage) => void;
  setDemoProgress: (step: number) => void;
  toggleOfflineMode: () => void;
  resetDemo: () => void;

  /** Evaluate the active demo scenario through the API (or locally offline). */
  evaluateCurrentScenario: (scenario?: SymptomScenario) => Promise<ActiveEvaluation>;
  evaluateCustomText: (text: string) => Promise<ActiveEvaluation>;
  evaluateCustomPayload: (payload: SymptomPayload, summaryLabel?: string) => Promise<ActiveEvaluation>;
  refreshPendingSyncCount: () => Promise<void>;
  syncNow: () => Promise<boolean>;

  /** Build the canonical payload for a scenario's NER extraction. */
  buildPayloadFromScenario: (scenario: SymptomScenario) => SymptomPayload;
}

let evaluationSequence = 0;

function uuid(): string {
  if ('crypto' in globalThis && 'randomUUID' in crypto) return crypto.randomUUID();
  return `sw-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function getInitialGreeting(lang: AppLanguage): string {
  return lang === 'Tamil'
    ? 'வணக்கம்! உங்கள் நோயாளிக்கு என்ன பிரச்சனை என்று வாய்ஸ் நோட் மூலம் அல்லது டைப் செய்து சொல்லுங்கள்.'
    : lang === 'Bengali'
    ? 'নমস্কার! আপনার রোগীর কী সমস্যা হচ্ছে তা ভয়েস নোট বা লিখে জানান।'
    : 'नमस्ते! कृपया बताएं कि आपके मरीज को क्या तकलीफ है — बोलकर या लिखकर संदेश भेजें।';
}

/** Map a demo scenario's NER extraction to the canonical symptom payload. */
function buildPayload(scenario: SymptomScenario): SymptomPayload {
  const p = emptyPayload(LANGUAGE_CODE[scenario.language] ?? 'en');
  const symptoms = scenario.nerExtraction.symptoms.map((s) => s.toLowerCase());
  const flags = scenario.nerExtraction.redFlags ?? [];
  const ageRaw = (scenario.nerExtraction.patientAge ?? 'child').toLowerCase();

  let ageGroup: AgeGroup = 'child';
  if (ageRaw.includes('neonate') || ageRaw.includes('newborn') || ageRaw.includes('day')) {
    ageGroup = 'neonate';
  } else if (ageRaw.includes('infant') || ageRaw.includes('month')) {
    ageGroup = 'infant';
  } else if (ageRaw.includes('adult') || ageRaw.includes('year-old male') || ageRaw.includes('year-old female')) {
    ageGroup = 'adult';
  }
  p.age_group = ageGroup;
  p.language = LANGUAGE_CODE[scenario.language] ?? 'en';

  const has = (...keys: string[]) =>
    symptoms.some((s) => keys.some((k) => s.includes(k))) ||
    flags.some((f) => keys.some((k) => f.toLowerCase().includes(k)));

  if (has('fever')) {
    p.has_fever = true;
    p.fever_days = parseDays(scenario.nerExtraction.duration) ?? 1;
  }
  if (has('cough')) {
    p.cough_days = parseDays(scenario.nerExtraction.duration) ?? 1;
  }
  if (has('breathing difficulty', 'difficulty breathing', 'shortness of breath')) {
    p.difficulty_breathing = true;
  }
  if (has('chest pain')) {
    p.chest_pain_severe = true;
  }
  if (has('vomiting blood')) {
    p.vomiting_blood = true;
  }

  // Duration "Immediate" implies an acute emergency presentation.
  const duration = (scenario.nerExtraction.duration ?? '').toLowerCase();
  if (duration === 'immediate' && !p.chest_pain_severe && !p.vomiting_blood) {
    p.unable_to_drink_or_breastfeed = true;
  }

  return sanitizePayload(p);
}

function parseDays(duration: string | undefined): number | null {
  if (!duration) return null;
  const m = duration.match(/(\d+)\s*day/i);
  return m ? parseInt(m[1], 10) : null;
}

const INITIAL_PATIENT_CASES: PatientCaseRecord[] = [
  {
    id: 'C-812',
    patientName: 'Aarav Kumar (Child, 2y)',
    age: '2 yrs',
    village: 'Belsand Tola (1.2 km)',
    lastUpdated: 'Live Session',
    symptomSummary: 'Awaiting triage intake…',
    riskScore: 2,
    primaryCluster: 'respiratory',
    status: 'needs_visit',
    isCurrentActive: true,
  },
  {
    id: 'C-813',
    patientName: 'Pooja Devi (Maternal, 24y)',
    age: '24 yrs',
    village: 'Runnisaidpur Ward 4 (3.4 km)',
    lastUpdated: '1 hour ago',
    symptomSummary: 'Mild fever, safe prenatal routine check',
    riskScore: 1,
    primaryCluster: 'maternal',
    status: 'monitoring',
    isCurrentActive: false,
  },
  {
    id: 'C-814',
    patientName: 'Rameshwar Roy (Adult, 58y)',
    age: '58 yrs',
    village: 'Dumra East (4.8 km)',
    lastUpdated: '3 hours ago',
    symptomSummary: 'Persistent cough (4 days) without fever',
    riskScore: 2,
    primaryCluster: 'respiratory',
    status: 'visited',
    isCurrentActive: false,
  },
  {
    id: 'C-815',
    patientName: 'Sita Kumari (Infant, 8mo)',
    age: '8 mo',
    village: 'Pupri South (6.1 km)',
    lastUpdated: 'Yesterday',
    symptomSummary: 'Mild diarrhoea, ORS replenishment visit',
    riskScore: 1,
    primaryCluster: 'diarrhoea',
    status: 'visited',
    isCurrentActive: false,
  },
];

export const useAppStore = create<AppState>((set, get) => ({
  isDemoActive: false,
  activeRole: 'Patient',
  activeLanguage: 'Hindi',
  currentScenario: defaultScenarios['Hindi'],
  demoProgress: 0,
  isOfflineMode: true,

  messages: [{ type: 'bot', text: getInitialGreeting('Hindi') }],
  inputText: '',
  setInputText: (text) => set({ inputText: text }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setMessages: (msgs) =>
    set((s) => ({
      messages: typeof msgs === 'function' ? msgs(s.messages) : msgs,
    })),
  resetChat: () =>
    set((s) => ({
      messages: [{ type: 'bot', text: getInitialGreeting(s.activeLanguage) }],
      demoProgress: 0,
      activeEvaluation: null,
      inputText: '',
    })),

  isEvaluating: false,
  isSyncing: false,
  activeEvaluation: null,
  backendOnline: null,
  pendingSyncCount: 0,

  patientCases: INITIAL_PATIENT_CASES,
  activePatientId: 'C-812',
  setActivePatientId: (id) => set({ activePatientId: id }),
  markCaseStatus: (id, status) =>
    set((s) => ({
      patientCases: s.patientCases.map((c) => (c.id === id ? { ...c, status } : c)),
    })),

  startDemo: (role) => set({ isDemoActive: true, activeRole: role, demoProgress: 0 }),
  
  setLanguage: (lang) => {
    const scenario = defaultScenarios[lang];
    set({
      activeLanguage: lang,
      currentScenario: scenario,
      demoProgress: 0,
      activeEvaluation: null,
      inputText: '',
      messages: [{ type: 'bot', text: getInitialGreeting(lang) }],
    });
  },

  setDemoProgress: (step) => set({ demoProgress: step }),

  toggleOfflineMode: () => {
    const next = !get().isOfflineMode;
    set({ isOfflineMode: next });
    if (!next) {
      void get().syncNow();
    }
  },

  resetDemo: () =>
    set((s) => ({
      isDemoActive: false,
      demoProgress: 0,
      activeEvaluation: null,
      inputText: '',
      messages: [{ type: 'bot', text: getInitialGreeting(s.activeLanguage) }],
    })),

  buildPayloadFromScenario: (scenario) => buildPayload(scenario),

  evaluateCurrentScenario: async (scenarioOverride) => {
    const currentSeq = ++evaluationSequence;
    const scenario = scenarioOverride ?? get().currentScenario;
    const payload = buildPayload(scenario);
    const client_uuid = uuid();
    const langCode = LANGUAGE_CODE[get().activeLanguage] ?? 'hi';

    set({ isEvaluating: true });

    let evaluation: ActiveEvaluation;

    if (get().isOfflineMode) {
      const outcome = evaluateLocal(payload);
      await enqueue({
        client_uuid,
        payload,
        created_at: new Date().toISOString(),
        client_risk_score: outcome.risk_score,
      });

      const directiveInfo = buildDirective(outcome.risk_score, outcome.primary_cluster, langCode);
      const emergency_dispatch = buildEmergencyDispatch(outcome, langCode);
      const defaultPhc = mockPHCs[0]
        ? {
            id: 1,
            name: mockPHCs[0].name,
            district: 'Sitamarhi',
            facility_type: 'PHC',
            phone: '+91 94318 00001',
            distance_km: mockPHCs[0].distance,
            hours: mockPHCs[0].hours,
            is_24x7: true,
            doctor_available: mockPHCs[0].doctorAvailable,
            latitude: mockPHCs[0].coordinates[0],
            longitude: mockPHCs[0].coordinates[1],
          }
        : null;

      evaluation = {
        outcome,
        directive: {
          type: directiveInfo.type,
          message_en: directiveInfo.message_local,
        },
        nearest_phc: defaultPhc,
        emergency_dispatch: emergency_dispatch ?? undefined,
        evaluatedOffline: true,
      };
    } else {
      try {
        const res = await api.evaluateTriage({ payload, client_uuid, district: 'Sitamarhi' });
        evaluation = {
          outcome: res.outcome,
          directive: res.directive,
          nearest_phc: res.nearest_phc,
          emergency_dispatch: res.emergency_dispatch ?? undefined,
          evaluatedOffline: false,
        };
        set({ backendOnline: true });
      } catch (err) {
        const isNetworkUnreachable = err instanceof ApiUnreachableError;
        if (isNetworkUnreachable) {
          set({ backendOnline: false });
        }
        const outcome = evaluateLocal(payload);
        await enqueue({
          client_uuid,
          payload,
          created_at: new Date().toISOString(),
          client_risk_score: outcome.risk_score,
        });
        const directiveInfo = buildDirective(outcome.risk_score, outcome.primary_cluster, langCode);
        const emergency_dispatch = buildEmergencyDispatch(outcome, langCode);
        evaluation = {
          outcome,
          directive: {
            type: directiveInfo.type,
            message_en: directiveInfo.message_local,
          },
          nearest_phc: null,
          emergency_dispatch: emergency_dispatch ?? undefined,
          evaluatedOffline: true,
        };
      }
    }

    if (currentSeq === evaluationSequence) {
      const count = await countQueued();
      // Synchronize Patient C-812 case card in ASHA tablet
      const updatedScore = evaluation.outcome.risk_score;
      const status = updatedScore === 3 ? 'emergency_dispatched' : updatedScore === 2 ? 'needs_visit' : 'monitoring';
      
      set((s) => ({
        isEvaluating: false,
        activeEvaluation: evaluation,
        pendingSyncCount: count,
        patientCases: s.patientCases.map((c) =>
          c.id === 'C-812'
            ? {
                ...c,
                riskScore: updatedScore,
                primaryCluster: evaluation.outcome.primary_cluster,
                symptomSummary: scenario.nerExtraction.symptoms.join(', ') || 'Voice Triage Intake',
                status,
                lastUpdated: 'Just now (Synced)',
              }
            : c
        ),
      }));
    }
    return evaluation;
  },

  evaluateCustomText: async (text: string) => {
    const currentSeq = ++evaluationSequence;
    const langCode = LANGUAGE_CODE[get().activeLanguage] ?? 'hi';
    const payload = normalizeTranscript(text, langCode);
    const client_uuid = uuid();

    set({ isEvaluating: true });

    let evaluation: ActiveEvaluation;

    if (get().isOfflineMode) {
      const outcome = evaluateLocal(payload);
      await enqueue({
        client_uuid,
        payload,
        created_at: new Date().toISOString(),
        client_risk_score: outcome.risk_score,
      });
      const directiveInfo = buildDirective(outcome.risk_score, outcome.primary_cluster, langCode);
      const emergency_dispatch = buildEmergencyDispatch(outcome, langCode);
      const defaultPhc = mockPHCs[0]
        ? {
            id: 1,
            name: mockPHCs[0].name,
            district: 'Sitamarhi',
            facility_type: 'PHC',
            phone: '+91 94318 00001',
            distance_km: mockPHCs[0].distance,
            hours: mockPHCs[0].hours,
            is_24x7: true,
            doctor_available: mockPHCs[0].doctorAvailable,
            latitude: mockPHCs[0].coordinates[0],
            longitude: mockPHCs[0].coordinates[1],
          }
        : null;

      evaluation = {
        outcome,
        directive: {
          type: directiveInfo.type,
          message_en: directiveInfo.message_local,
        },
        nearest_phc: defaultPhc,
        emergency_dispatch: emergency_dispatch ?? undefined,
        evaluatedOffline: true,
      };
    } else {
      try {
        const res = await api.evaluateTriage({ payload, client_uuid, district: 'Sitamarhi' });
        evaluation = {
          outcome: res.outcome,
          directive: res.directive,
          nearest_phc: res.nearest_phc,
          emergency_dispatch: res.emergency_dispatch ?? undefined,
          evaluatedOffline: false,
        };
        set({ backendOnline: true });
      } catch {
        const outcome = evaluateLocal(payload);
        await enqueue({
          client_uuid,
          payload,
          created_at: new Date().toISOString(),
          client_risk_score: outcome.risk_score,
        });
        const directiveInfo = buildDirective(outcome.risk_score, outcome.primary_cluster, langCode);
        const emergency_dispatch = buildEmergencyDispatch(outcome, langCode);
        evaluation = {
          outcome,
          directive: {
            type: directiveInfo.type,
            message_en: directiveInfo.message_local,
          },
          nearest_phc: null,
          emergency_dispatch: emergency_dispatch ?? undefined,
          evaluatedOffline: true,
        };
      }
    }

    if (currentSeq === evaluationSequence) {
      const count = await countQueued();
      const updatedScore = evaluation.outcome.risk_score;
      const status = updatedScore === 3 ? 'emergency_dispatched' : updatedScore === 2 ? 'needs_visit' : 'monitoring';

      set((s) => ({
        isEvaluating: false,
        activeEvaluation: evaluation,
        pendingSyncCount: count,
        patientCases: s.patientCases.map((c) =>
          c.id === 'C-812'
            ? {
                ...c,
                riskScore: updatedScore,
                primaryCluster: evaluation.outcome.primary_cluster,
                symptomSummary: text.length > 40 ? text.slice(0, 40) + '…' : text,
                status,
                lastUpdated: 'Just now (Synced)',
              }
            : c
        ),
      }));
    }
    return evaluation;
  },

  evaluateCustomPayload: async (payload: SymptomPayload, summaryLabel?: string) => {
    const currentSeq = ++evaluationSequence;
    const langCode = LANGUAGE_CODE[get().activeLanguage] ?? 'hi';
    const client_uuid = uuid();

    set({ isEvaluating: true });

    const outcome = evaluateLocal(payload);
    await enqueue({
      client_uuid,
      payload,
      created_at: new Date().toISOString(),
      client_risk_score: outcome.risk_score,
    });

    const directiveInfo = buildDirective(outcome.risk_score, outcome.primary_cluster, langCode);
    const emergency_dispatch = buildEmergencyDispatch(outcome, langCode);
    const defaultPhc = mockPHCs[0]
      ? {
          id: 1,
          name: mockPHCs[0].name,
          district: 'Sitamarhi',
          facility_type: 'PHC',
          phone: '+91 94318 00001',
          distance_km: mockPHCs[0].distance,
          hours: mockPHCs[0].hours,
          is_24x7: true,
          doctor_available: mockPHCs[0].doctorAvailable,
          latitude: mockPHCs[0].coordinates[0],
          longitude: mockPHCs[0].coordinates[1],
        }
      : null;

    const evaluation: ActiveEvaluation = {
      outcome,
      directive: {
        type: directiveInfo.type,
        message_en: directiveInfo.message_local,
      },
      nearest_phc: defaultPhc,
      emergency_dispatch: emergency_dispatch ?? undefined,
      evaluatedOffline: true,
    };

    if (currentSeq === evaluationSequence) {
      const count = await countQueued();
      const updatedScore = evaluation.outcome.risk_score;
      const status = updatedScore === 3 ? 'emergency_dispatched' : updatedScore === 2 ? 'needs_visit' : 'monitoring';

      set((s) => ({
        isEvaluating: false,
        activeEvaluation: evaluation,
        pendingSyncCount: count,
        demoProgress: 5,
        patientCases: s.patientCases.map((c) =>
          c.id === 'C-812'
            ? {
                ...c,
                riskScore: updatedScore,
                primaryCluster: evaluation.outcome.primary_cluster,
                symptomSummary: summaryLabel || `Touch-to-Hear Check (${outcome.primary_cluster})`,
                status,
                lastUpdated: 'Just now (Synced)',
              }
            : c
        ),
      }));
    }
    return evaluation;
  },

  refreshPendingSyncCount: async () => {
    try {
      const count = await countQueued();
      set({ pendingSyncCount: count });
    } catch {
      // IndexedDB unavailable: leave count untouched.
    }
  },

  syncNow: async () => {
    set({ isSyncing: true });
    try {
      const res = await flushOutbox((items) => api.syncCases(items));
      if (res.ok) {
        const count = await countQueued();
        set({ backendOnline: true, pendingSyncCount: count });
      }
      return res.ok;
    } finally {
      set({ isSyncing: false });
    }
  },
}));

// Setup auto-reconnect listener in browser
if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    void useAppStore.getState().syncNow();
  });
}

export type { RiskLevel };

