import { Badge } from '@/components/ui/badge';
import { useAppStore } from '@/store/useAppStore';

export function LanguageBadge() {
  const activeLanguage = useAppStore((state) => state.activeLanguage);

  return (
    <div className="flex items-center space-x-2 bg-slate-900/5 dark:bg-slate-100/10 px-3 py-1.5 rounded-full backdrop-blur-sm">
      <span className="text-lg leading-none" role="img" aria-label="India flag">
        🇮🇳
      </span>
      <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
        {activeLanguage}
      </span>
      <Badge variant="outline" className="border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-[10px] px-1.5 py-0 h-4">
        Live
      </Badge>
    </div>
  );
}
