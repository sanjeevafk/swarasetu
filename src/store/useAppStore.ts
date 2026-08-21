import { create } from 'zustand';
import { defaultScenarios, type SymptomScenario } from '@/data/mockSymptoms';
import type {
  LanguageCode,
  RiskLevel,
  SymptomPayload,
  TriageOutcome,
  TriageEvaluateResponse,
} from '@/types/api';
import { emptyPayload } from '@/types/api';
import { api, ApiUnreachableError } from '@/lib/api';
import { evaluateLocal } from '@/lib/triageLocal';
import { countQueued, enqueue, flushOutbox } from '@/lib/outbox';

export type UserRole = 'Patient' | 'CHW' | 'Supervisor';
export type AppLanguage = 'Hindi' | 'Tamil' | 'Bengali';

const LANGUAGE_CODE: Record<AppLanguage, LanguageCode> = {
  Hindi: 'hi',
  Tamil: 'ta',
  Bengali: 'bn',
};

export interface ActiveEvaluation {
  outcome: TriageOutcome;
  directive: TriageEvaluateResponse['directive'] | null;
  nearest_phc: TriageEvaluateResponse['nearest_phc'];
  evaluatedOffline: boolean;
}

interface AppState {
  isDemoActive: boolean;
  activeRole: UserRole;
  activeLanguage: AppLanguage;
  currentScenario: SymptomScenario;
  demoProgress: number; // 0: Start, 1: Audio, 2: STT, 3: NER, 4: IMCI, 5: Map
  isOfflineMode: boolean;

  // Live evaluation state
  isEvaluating: boolean;
  activeEvaluation: ActiveEvaluation | null;
  backendOnline: boolean | null; // null = unknown / not probed yet
  pendingSyncCount: number;

  startDemo: (role: UserRole) => void;
  setLanguage: (lang: AppLanguage) => void;
  setDemoProgress: (step: number) => void;
  toggleOfflineMode: () => void;
  resetDemo: () => void;

  /** Evaluate the active demo scenario through the API (or locally offline). */
  evaluateCurrentScenario: (scenario?: SymptomScenario) => Promise<ActiveEvaluation>;
  refreshPendingSyncCount: () => Promise<void>;
  syncNow: () => Promise<boolean>;

  /** Build the canonical payload for a scenario's NER extraction. */
  buildPayloadFromScenario: (scenario: SymptomScenario) => SymptomPayload;
}

function uuid(): string {
  if ('crypto' in globalThis && 'randomUUID' in crypto) return crypto.randomUUID();
  return `sw-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

/** Map a demo scenario's NER extraction to the canonical symptom payload.
 *  Deterministic heuristics keyed off the mock fixture fields. */
function buildPayload(scenario: SymptomScenario): SymptomPayload {
  const p = emptyPayload(LANGUAGE_CODE[scenario.language] ?? 'en');
  const symptoms = scenario.nerExtraction.symptoms.map((s) => s.toLowerCase());
  const flags = scenario.nerExtraction.redFlags ?? [];
  const age = (scenario.nerExtraction.patientAge ?? 'child').toLowerCase();

  p.age_group = age.includes('adult') ? 'adult' : 'child';
  p.language = LANGUAGE_CODE[scenario.language] ?? 'en';

  const has = (...keys: string[]) =>
    symptoms.some((s) => keys.some((k) => s.includes(k))) ||
    flags.some((f) => keys.some((k) => f.toLowerCase().includes(k)));

  if (has('fever')) {
    p.has_fever = true;
    p.fever_days = parseDays(scenario.nerExtraction.duration) ?? 1;
  }
  if (has('cough')) {
    p.cough_days = parseDays(scenario.nerExtraction.duration) ?? 2;
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

  return p;
}

function parseDays(duration: string | undefined): number | null {
  if (!duration) return null;
  const m = duration.match(/(\d+)\s*day/i);
  return m ? parseInt(m[1], 10) : null;
}

export const useAppStore = create<AppState>((set, get) => ({
  isDemoActive: false,
  activeRole: 'Patient',
  activeLanguage: 'Hindi',
  currentScenario: defaultScenarios['Hindi'],
  demoProgress: 0,
  isOfflineMode: true,

  isEvaluating: false,
  activeEvaluation: null,
  backendOnline: null,
  pendingSyncCount: 0,

  startDemo: (role) => set({ isDemoActive: true, activeRole: role, demoProgress: 0 }),
  setLanguage: (lang) =>
    set({
      activeLanguage: lang,
      currentScenario: defaultScenarios[lang],
      demoProgress: 0,
      activeEvaluation: null,
    }),
  setDemoProgress: (step) => set({ demoProgress: step }),
  toggleOfflineMode: () => {
    const next = !get().isOfflineMode;
    set({ isOfflineMode: next });
    if (!next) {
      // Coming back online: flush queued outbox records in background.
      void get().syncNow();
    }
  },
  resetDemo: () => set({ isDemoActive: false, demoProgress: 0 }),

  buildPayloadFromScenario: (scenario) => buildPayload(scenario),

  evaluateCurrentScenario: async (scenarioOverride) => {
    const scenario = scenarioOverride ?? get().currentScenario;
    const payload = buildPayload(scenario);
    const client_uuid = uuid();
    set({ isEvaluating: true, activeEvaluation: null });

    let evaluation: ActiveEvaluation;

    if (get().isOfflineMode) {
      // Explicit offline mode: deterministic local engine + outbox queue.
      const outcome = evaluateLocal(payload);
      await enqueue({ client_uuid, payload, created_at: new Date().toISOString(), client_risk_score: outcome.risk_score });
      evaluation = { outcome, directive: null, nearest_phc: null, evaluatedOffline: true };
    } else {
      try {
        const res = await api.evaluateTriage({ payload, client_uuid });
        evaluation = {
          outcome: res.outcome,
          directive: res.directive,
          nearest_phc: res.nearest_phc,
          evaluatedOffline: false,
        };
        set({ backendOnline: true });
      } catch (err) {
        // Backend unreachable: graceful degradation to local engine + queue.
        const offline = err instanceof ApiUnreachableError || !(err instanceof Error && err.message.startsWith('API '));
        if (offline) set({ backendOnline: false });
        const outcome = evaluateLocal(payload);
        await enqueue({ client_uuid, payload, created_at: new Date().toISOString(), client_risk_score: outcome.risk_score });
        evaluation = { outcome, directive: null, nearest_phc: null, evaluatedOffline: true };
      }
    }

    const count = await countQueued();
    set({ isEvaluating: false, activeEvaluation: evaluation, pendingSyncCount: count });
    return evaluation;
  },

  refreshPendingSyncCount: async () => {
    try {
      const count = await countQueued();
      set({ pendingSyncCount: count });
    } catch {
      // IndexedDB unavailable (private mode): leave count untouched.
    }
  },

  syncNow: async () => {
    const res = await flushOutbox((items) => api.syncCases(items));
    if (res.ok) {
      const count = await countQueued();
      set({ backendOnline: true, pendingSyncCount: count });
    }
    return res.ok;
  },
}));

// Keep risk level typing narrow for consumers of the store outcome.
export type { RiskLevel };
