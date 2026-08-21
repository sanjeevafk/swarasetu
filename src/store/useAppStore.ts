import { create } from 'zustand';
import { defaultScenarios, type SymptomScenario } from '@/data/mockSymptoms';

export type UserRole = 'Patient' | 'CHW' | 'Supervisor';
export type AppLanguage = 'Hindi' | 'Tamil' | 'Bengali';

interface AppState {
  isDemoActive: boolean;
  activeRole: UserRole;
  activeLanguage: AppLanguage;
  currentScenario: SymptomScenario;
  demoProgress: number; // 0: Start, 1: Audio, 2: STT, 3: NER, 4: IMCI, 5: Map
  isOfflineMode: boolean;
  
  startDemo: (role: UserRole) => void;
  setLanguage: (lang: AppLanguage) => void;
  setDemoProgress: (step: number) => void;
  toggleOfflineMode: () => void;
  resetDemo: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  isDemoActive: false,
  activeRole: 'Patient',
  activeLanguage: 'Hindi',
  currentScenario: defaultScenarios['Hindi'],
  demoProgress: 0,
  isOfflineMode: true,

  startDemo: (role) => set({ isDemoActive: true, activeRole: role, demoProgress: 0 }),
  setLanguage: (lang) => set({ activeLanguage: lang, currentScenario: defaultScenarios[lang], demoProgress: 0 }),
  setDemoProgress: (step) => set({ demoProgress: step }),
  toggleOfflineMode: () => set((state) => ({ isOfflineMode: !state.isOfflineMode })),
  resetDemo: () => set({ isDemoActive: false, demoProgress: 0 })
}));
