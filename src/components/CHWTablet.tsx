import { useEffect, useState } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import {
  Activity,
  CheckCircle2,
  CloudOff,
  RefreshCw,
  Volume2,
  MessageSquare,
  PhoneCall,
  MapPin,
  Check,
  ShieldAlert,
  AlertTriangle,
  ClipboardCheck,
} from 'lucide-react';
import { DemoChat } from './DemoChat';
import { TouchToHearPanel } from './TouchToHearPanel';

export function CHWTablet({ onShowMap }: { onShowMap: () => void }) {
  const {
    isOfflineMode,
    toggleOfflineMode,
    currentScenario,
    activeEvaluation,
    isSyncing,
    pendingSyncCount,
    refreshPendingSyncCount,
    activeLanguage,
    patientCases,
    activePatientId,
    setActivePatientId,
    markCaseStatus,
  } = useAppStore();

  const [tabMode, setTabMode] = useState<'chat' | 'visual'>('chat');
  const [visitedChecked, setVisitedChecked] = useState(false);

  useEffect(() => {
    void refreshPendingSyncCount();
  }, [refreshPendingSyncCount]);

  const activePatient = patientCases.find((c) => c.id === activePatientId) || patientCases[0];
  const activeRisk = activeEvaluation?.outcome.risk_score ?? activePatient.riskScore ?? currentScenario.riskScore;

  const getScoreBadge = (score: number) => {
    if (score === 3) return 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300 border-red-300';
    if (score === 2) return 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 border-amber-300';
    return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 border-emerald-300';
  };

  return (
    <div className="flex flex-col h-full bg-slate-100 dark:bg-slate-900 overflow-hidden font-sans">
      {/* Tablet Header / Status Bar */}
      <div className="bg-emerald-700 dark:bg-emerald-900 text-white p-3 flex justify-between items-center shadow-md z-10">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5" />
          <span className="font-bold text-base md:text-lg tracking-tight">Swara ASHA Portal — Sitamarhi District</span>
          <Badge variant="outline" className="bg-white/10 text-white border-white/30 text-[10px] hidden md:inline-flex">
            Worker: Smt. Sunita Devi (ID: AS-8821)
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          {/* Mode Tab Switcher */}
          <div className="flex items-center bg-black/20 rounded-lg p-0.5 gap-0.5">
            <button
              onClick={() => setTabMode('chat')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                tabMode === 'chat' ? 'bg-white text-emerald-900 shadow-sm' : 'text-emerald-100 hover:text-white'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              Patient Sync
            </button>
            <button
              onClick={() => setTabMode('visual')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                tabMode === 'visual' ? 'bg-white text-emerald-900 shadow-sm' : 'text-emerald-100 hover:text-white'
              }`}
            >
              <Volume2 className="w-3.5 h-3.5" />
              Touch-to-Hear
            </button>
          </div>

          {/* Offline Toggle */}
          <div className="flex items-center space-x-1.5 bg-black/20 px-2 py-1 rounded-md">
            <Switch id="offline-mode" checked={isOfflineMode} onCheckedChange={toggleOfflineMode} />
            <Label htmlFor="offline-mode" className="text-[11px] font-semibold uppercase tracking-wider cursor-pointer">
              {isOfflineMode ? (
                <span className="flex items-center text-amber-300">
                  <CloudOff className="w-3 h-3 mr-1" /> Offline
                </span>
              ) : (
                <span className="flex items-center text-emerald-300">
                  <CheckCircle2 className="w-3 h-3 mr-1" /> Online
                </span>
              )}
            </Label>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-hidden p-2 md:p-3 pb-2 flex gap-3">
        {/* Sidebar - Case List */}
        <div className="w-80 min-w-[240px] flex flex-col gap-2.5 h-full overflow-y-auto hidden sm:flex">
          <Card className="border-0 shadow-sm flex-1 bg-white dark:bg-slate-950 flex flex-col overflow-hidden">
            <CardHeader className="p-3 pb-2 border-b border-slate-100 dark:border-slate-800 flex flex-row items-center justify-between">
              <CardTitle className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                <ClipboardCheck className="w-3.5 h-3.5 text-emerald-600" /> Assigned Visits ({patientCases.length})
              </CardTitle>
              <span className="text-[10px] bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300 font-bold px-1.5 py-0.5 rounded">
                Live Synced
              </span>
            </CardHeader>
            <CardContent className="p-0 overflow-y-auto flex-1">
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {patientCases.map((pCase) => {
                  const isSelected = pCase.id === activePatientId;
                  return (
                    <div
                      key={pCase.id}
                      onClick={() => setActivePatientId(pCase.id)}
                      className={`p-2.5 cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-emerald-50/80 dark:bg-emerald-900/25 border-l-4 border-emerald-500'
                          : 'hover:bg-slate-50 dark:hover:bg-slate-800/40'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-0.5">
                        <div className="flex items-center gap-1">
                          <span className="font-bold text-xs text-slate-900 dark:text-slate-100">
                            {pCase.id} · {pCase.patientName.split(' ')[0]}
                          </span>
                          {pCase.id === 'C-812' && (
                            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" title="Active demo session" />
                          )}
                        </div>
                        <Badge variant="outline" className={`text-[9px] h-4 px-1 leading-3 uppercase font-bold ${getScoreBadge(pCase.riskScore)}`}>
                          Score {pCase.riskScore}
                        </Badge>
                      </div>

                      <div className="text-[11px] font-medium text-slate-600 dark:text-slate-300 line-clamp-1">
                        {pCase.symptomSummary}
                      </div>

                      <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                        <span className="flex items-center gap-0.5">
                          <MapPin className="w-2.5 h-2.5" /> {pCase.village.split(' ')[0]}
                        </span>
                        <span className="font-semibold text-[9px]">{pCase.lastUpdated}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Action Callout for ASHA */}
          <div className="bg-white dark:bg-slate-950 p-2.5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1">
                {activeRisk === 3 ? (
                  <span className="text-red-600 flex items-center gap-1">
                    <ShieldAlert className="w-3.5 h-3.5" /> Emergency Dispatch
                  </span>
                ) : activeRisk === 2 ? (
                  <span className="text-amber-600 flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" /> Home Visit Needed
                  </span>
                ) : (
                  <span className="text-emerald-600 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Home Monitoring
                  </span>
                )}
              </span>
              <span className="text-[10px] text-slate-500 font-mono">Patient C-812</span>
            </div>

            <div className="flex gap-1.5">
              <Button
                size="sm"
                variant="outline"
                className="flex-1 text-[10px] h-7 px-1.5 text-slate-700 dark:text-slate-300"
                onClick={() => alert('Dialing Patient C-812 Guardian: +91 98350 12345')}
              >
                <PhoneCall className="w-3 h-3 mr-1 text-emerald-600" /> Call
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="flex-1 text-[10px] h-7 px-1.5 text-slate-700 dark:text-slate-300"
                onClick={onShowMap}
              >
                <MapPin className="w-3 h-3 mr-1 text-red-500" /> PHC Route
              </Button>
            </div>

            <Button
              size="sm"
              onClick={() => {
                setVisitedChecked(!visitedChecked);
                markCaseStatus('C-812', visitedChecked ? 'needs_visit' : 'visited');
              }}
              className={`w-full text-[10px] h-7 font-bold transition-all ${
                visitedChecked
                  ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                  : 'bg-slate-100 hover:bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-200'
              }`}
            >
              <Check className="w-3 h-3 mr-1" />
              {visitedChecked ? 'Visit Marked Completed ✓' : 'Mark Visit Complete'}
            </Button>
          </div>

          {isOfflineMode && (
            <div className="bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 p-2.5 rounded-xl flex items-start gap-2 text-xs shadow-sm border border-amber-200 dark:border-amber-800">
              <RefreshCw className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-600" />
              <div>
                <div className="font-bold">
                  Edge Mode Active{pendingSyncCount > 0 ? ` · ${pendingSyncCount} queued` : ''}
                </div>
                <div className="text-[10px] text-amber-700/80 dark:text-amber-400">
                  Data will automatically sync on reconnect.
                </div>
              </div>
            </div>
          )}

          {!isOfflineMode && isSyncing && (
            <div className="bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400 p-2.5 rounded-xl flex items-start gap-2 text-xs shadow-sm border border-blue-200 dark:border-blue-800">
              <RefreshCw className="w-4 h-4 flex-shrink-0 mt-0.5 animate-spin" />
              <div>
                <div className="font-bold">Syncing {pendingSyncCount > 0 ? `${pendingSyncCount} ` : ''}records…</div>
              </div>
            </div>
          )}
        </div>

        {/* Main Content - Triage Frame */}
        <div className="flex-1 h-full pb-1">
          <div className="bg-white dark:bg-slate-950 h-full rounded-2xl shadow-lg border-[6px] border-slate-200 dark:border-slate-800 overflow-hidden relative">
            {/* Tablet Camera Notch simulation */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-3.5 bg-slate-200 dark:bg-slate-800 rounded-b-xl z-20 flex justify-center items-end pb-0.5">
              <div className="w-1.5 h-1.5 rounded-full bg-slate-400 dark:bg-slate-700" />
            </div>

            {tabMode === 'chat' ? (
              <DemoChat onShowMap={onShowMap} titleOverride="SwaraSetu — Patient C-812 Live Intake" />
            ) : (
              <TouchToHearPanel language={activeLanguage} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

