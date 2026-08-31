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
    <div className="flex items-center gap-1 bg-white p-1 rounded-lg border border-slate-200 shadow-xs">
      <div className="flex items-center gap-1 px-1.5 text-slate-400">
        <Globe className="w-3.5 h-3.5" />
      </div>
      {LANGUAGES.map((lang) => {
        const isActive = activeLanguage === lang.key;
        return (
          <button
            key={lang.key}
            onClick={() => setLanguage(lang.key)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold transition-all ${
              isActive
                ? 'bg-[#0f4c42] text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
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
