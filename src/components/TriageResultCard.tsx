import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Volume2, MapPin, CloudOff, AlertTriangle, ClipboardList, Siren, ShieldAlert, HeartPulse } from 'lucide-react';
import type { RiskLevel, TriageOutcome, EmergencyDispatch } from '@/types/api';

interface TriageResultCardProps {
  outcome: TriageOutcome;
  message: string;
  evaluatedOffline?: boolean;
  emergencyDispatch?: EmergencyDispatch | null;
  onShowMap: () => void;
}

export function TriageResultCard({
  outcome,
  message,
  evaluatedOffline = false,
  emergencyDispatch,
  onShowMap,
}: TriageResultCardProps) {
  const riskScore: RiskLevel =
    outcome.risk_score === 3 ? 3 : outcome.risk_score === 2 ? 2 : 1;

  const getBadgeColors = (score: RiskLevel) => {
    switch (score) {
      case 1:
        return 'bg-emerald-50 text-emerald-800 border-emerald-200';
      case 2:
        return 'bg-amber-50 text-amber-800 border-amber-200';
      case 3:
        return 'bg-rose-50 text-rose-800 border-rose-200';
    }
  };

  const getLabel = (score: RiskLevel) => {
    switch (score) {
      case 1:
        return 'Self-Care / Home';
      case 2:
        return 'ASHA Worker Alerted';
      case 3:
        return 'Critical Emergency';
    }
  };

  return (
    <Card className="w-full border-slate-200 bg-white shadow-sm transition-all duration-200 rounded-xl overflow-hidden font-sans">
      <CardHeader className="pb-2.5 p-4 border-b border-slate-100">
        <div className="flex justify-between items-start gap-2">
          <CardTitle className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            WHO IMCI Triage Assessment
          </CardTitle>
          <div className="flex flex-col items-end gap-1">
            <Badge variant="outline" className={`font-bold text-xs uppercase px-2.5 py-0.5 rounded-md border ${getBadgeColors(riskScore)}`}>
              Score {riskScore}: {getLabel(riskScore)}
            </Badge>
            {evaluatedOffline && (
              <span className="flex items-center gap-1 text-[10px] font-bold text-amber-700 uppercase tracking-wider">
                <CloudOff className="w-3 h-3 text-amber-600" /> On-Device (Offline)
              </span>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-4 space-y-3">
        <p className="text-slate-900 text-sm md:text-base leading-relaxed font-semibold">
          {message}
        </p>

        <p className="text-xs text-slate-500 leading-relaxed">
          {outcome.rationale_en}
        </p>

        {/* 4-Pillar Emergency Response for Score 3 */}
        {riskScore === 3 && emergencyDispatch?.is_emergency && (
          <div className="rounded-xl border border-rose-200 bg-rose-50/60 p-3.5 space-y-2.5 shadow-sm">
            <div className="flex items-center justify-between border-b border-rose-200 pb-2">
              <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-rose-800">
                <Siren className="w-4 h-4 text-rose-600 animate-pulse" /> 4-Pillar Emergency Dispatch
              </div>
              <Badge variant="destructive" className="text-[10px] font-mono bg-rose-600">
                {emergencyDispatch.ticket_id || '108-EMRI-SOS'}
              </Badge>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              <div className="flex items-center gap-2 bg-white p-2.5 rounded-lg border border-rose-100 shadow-xs">
                <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
                <div>
                  <span className="font-bold text-slate-900">108 Ambulance: </span>
                  <span className="text-slate-600">{emergencyDispatch.ambulance_type || '108 ALS Unit Dispatched'}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 bg-white p-2.5 rounded-lg border border-rose-100 shadow-xs">
                <HeartPulse className="w-4 h-4 text-rose-600 shrink-0" />
                <div>
                  <span className="font-bold text-slate-900">PHC Readiness: </span>
                  <span className="text-slate-600">{emergencyDispatch.phc_readiness || 'Pre-alerted Duty Doctor'}</span>
                </div>
              </div>
            </div>

            {emergencyDispatch.steps.length > 0 && (
              <div className="bg-white rounded-lg p-3 border border-rose-100 space-y-1.5 shadow-xs">
                <span className="text-[11px] font-bold text-rose-800 uppercase tracking-wider block">
                  Immediate Life-Saving Directives
                </span>
                <ul className="space-y-1">
                  {emergencyDispatch.steps.map((step, idx) => (
                    <li key={idx} className="text-xs text-slate-700 leading-snug font-medium">
                      • {step}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {outcome.red_flags.length > 0 && (!emergencyDispatch || !emergencyDispatch.is_emergency) && (
          <div className="rounded-xl border border-rose-200 bg-rose-50/60 p-3">
            <div className="flex items-center gap-1.5 mb-1.5 text-[10px] font-bold uppercase tracking-wider text-rose-800">
              <AlertTriangle className="w-3.5 h-3.5 text-rose-600" /> Clinical Danger Signs (Red Flags)
            </div>
            <ul className="space-y-0.5">
              {outcome.red_flags.map((f) => (
                <li key={f.code} className="text-xs font-semibold text-rose-800">
                  • {f.description_en}
                </li>
              ))}
            </ul>
          </div>
        )}

        {outcome.actions.length > 0 && (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center gap-1.5 mb-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-600">
              <ClipboardList className="w-3.5 h-3.5 text-slate-600" /> ASHA Action Checklist
            </div>
            <ol className="list-decimal list-inside space-y-1">
              {outcome.actions.map((a, i) => (
                <li key={i} className="text-xs font-medium text-slate-800">{a}</li>
              ))}
            </ol>
          </div>
        )}
      </CardContent>

      <CardFooter className="p-4 pt-1 flex gap-2">
        <Button
          variant="outline"
          size="sm"
          className="flex-1 bg-white hover:bg-slate-50 border-slate-200 text-slate-800 font-semibold shadow-sm text-xs h-9 rounded-lg"
          onClick={() => {
            if ('speechSynthesis' in window) {
              const u = new SpeechSynthesisUtterance(message);
              u.rate = 0.9;
              window.speechSynthesis.speak(u);
            }
          }}
        >
          <Volume2 className="w-3.5 h-3.5 mr-1.5 text-emerald-700" /> Play Audio
        </Button>
        {riskScore === 3 && (
          <Button
            onClick={onShowMap}
            size="sm"
            className="flex-1 bg-rose-600 hover:bg-rose-700 text-white font-bold shadow-sm text-xs h-9 rounded-lg"
          >
            <MapPin className="w-3.5 h-3.5 mr-1.5" /> Nearest PHC Route
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
