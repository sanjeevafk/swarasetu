import { useAppStore, type AppLanguage } from '@/store/useAppStore';
import { Globe } from 'lucide-react';

const LANGUAGES: { key: AppLanguage; label: string; native: string }[] = [
  { key: 'Hindi', label: 'Hindi', native: 'हिन्दी' },
  { key: 'Tamil', label: 'Tamil', native: 'தமிழ்' },
  { key: 'Bengali', label: 'Bengali', native: 'বাংলা' },
];

export function LanguageBadge() {
  const activeLanguage = useAppStore((state) => state.activeLanguage);
  const setLanguage = useAppStore((state) => state.setLanguage);

  return (
    <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800/80 p-1 rounded-full border border-slate-200 dark:border-slate-700 shadow-inner">
      <div className="flex items-center gap-1 px-2 text-slate-500 dark:text-slate-400">
        <Globe className="w-3.5 h-3.5" />
      </div>
      {LANGUAGES.map((lang) => {
        const isActive = activeLanguage === lang.key;
        return (
          <button
            key={lang.key}
            onClick={() => setLanguage(lang.key)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold transition-all duration-200 ${
              isActive
                ? 'bg-emerald-600 text-white shadow-sm scale-105'
                : 'text-slate-600 dark:text-slate-300 hover:text-emerald-600 dark:hover:text-emerald-400 hover:bg-white/60 dark:hover:bg-slate-700/60'
            }`}
            title={`Switch to ${lang.label}`}
          >
            <span>{lang.native}</span>
            <span className="text-[10px] opacity-80 hidden sm:inline">({lang.label})</span>
          </button>
        );
      })}
    </div>
  );
}
