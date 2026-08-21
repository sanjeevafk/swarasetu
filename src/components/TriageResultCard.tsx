import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Volume2, MapPin, CloudOff, AlertTriangle, ClipboardList } from 'lucide-react';
import type { RiskLevel, TriageOutcome } from '@/types/api';

interface TriageResultCardProps {
  outcome: TriageOutcome;
  message: string;
  evaluatedOffline?: boolean;
  onShowMap: () => void;
}

export function TriageResultCard({
  outcome,
  message,
  evaluatedOffline = false,
  onShowMap,
}: TriageResultCardProps) {
  const riskScore: RiskLevel =
    outcome.risk_score === 3 ? 3 : outcome.risk_score === 2 ? 2 : 1;

  const getBadgeColors = (score: RiskLevel) => {
    switch (score) {
      case 1:
        return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400 border-emerald-200';
      case 2:
        return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400 border-amber-200';
      case 3:
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 border-red-200';
    }
  };

  const getLabel = (score: RiskLevel) => {
    switch (score) {
      case 1: return 'Self-Care / Home';
      case 2: return 'ASHA Worker Alerted';
      case 3: return 'Urgent Referral';
    }
  };

  return (
    <Card className="w-full border-slate-200 dark:border-slate-800 shadow-sm transition-all duration-300">
      <CardHeader className="pb-3">
        <div className="flex justify-between items-start gap-2">
          <CardTitle className="text-sm font-medium text-slate-500 uppercase tracking-wider">
            IMCI Triage Result
          </CardTitle>
          <div className="flex flex-col items-end gap-1.5">
            <Badge variant="outline" className={`font-bold ${getBadgeColors(riskScore)}`}>
              Score {riskScore}: {getLabel(riskScore)}
            </Badge>
            {evaluatedOffline && (
              <span className="flex items-center gap-1 text-[10px] font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wider">
                <CloudOff className="w-3 h-3" /> On-device
              </span>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-slate-800 dark:text-slate-200 text-base leading-relaxed font-medium">{message}</p>

        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{outcome.rationale_en}</p>

        {outcome.red_flags.length > 0 && (
          <div className="rounded-lg border border-red-100 bg-red-50/60 dark:border-red-900/40 dark:bg-red-950/30 p-2.5">
            <div className="flex items-center gap-1.5 mb-1.5 text-[10px] font-bold uppercase tracking-widest text-red-700 dark:text-red-400">
              <AlertTriangle className="w-3 h-3" /> Red Flags
            </div>
            <ul className="space-y-0.5">
              {outcome.red_flags.map((f) => (
                <li key={f.code} className="text-xs font-medium text-red-700 dark:text-red-300">
                  • {f.description_en}
                </li>
              ))}
            </ul>
          </div>
        )}

        {outcome.actions.length > 0 && (
          <div className="rounded-lg border border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-900 p-2.5">
            <div className="flex items-center gap-1.5 mb-1.5 text-[10px] font-bold uppercase tracking-widest text-slate-500">
              <ClipboardList className="w-3 h-3" /> Field Actions
            </div>
            <ol className="list-decimal list-inside space-y-0.5">
              {outcome.actions.map((a, i) => (
                <li key={i} className="text-xs font-medium text-slate-700 dark:text-slate-300">{a}</li>
              ))}
            </ol>
          </div>
        )}
      </CardContent>
      <CardFooter className="pt-2 flex gap-2">
        <Button variant="secondary" size="sm" className="flex-1 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200">
          <Volume2 className="w-4 h-4 mr-2" /> Play Audio
        </Button>
        {riskScore === 3 && (
          <Button onClick={onShowMap} size="sm" className="flex-1 bg-red-600 hover:bg-red-700 text-white shadow-md">
            <MapPin className="w-4 h-4 mr-2" /> Nearest PHC
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
