import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Volume2, MapPin } from 'lucide-react';
import type { RiskLevel } from '@/data/mockSymptoms';

export function TriageResultCard({
  riskScore,
  message,
  onShowMap
}: {
  riskScore: RiskLevel;
  message: string;
  onShowMap: () => void;
}) {
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
        <div className="flex justify-between items-start">
          <CardTitle className="text-sm font-medium text-slate-500 uppercase tracking-wider">AI Triage Result</CardTitle>
          <Badge variant="outline" className={`font-bold ${getBadgeColors(riskScore)}`}>
            Score {riskScore}: {getLabel(riskScore)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-slate-800 dark:text-slate-200 text-lg leading-relaxed font-medium">{message}</p>
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
