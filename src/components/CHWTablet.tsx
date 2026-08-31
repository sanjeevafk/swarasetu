import { useEffect, useState } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Activity,
  CheckCircle2,
  CloudOff,
  RefreshCw,
  Volume2,
  Phone,
  MapPin,
  Check,
  ShieldAlert,
  AlertTriangle,
  ClipboardList,
  RotateCw,
  Wifi,
} from 'lucide-react';
import { DemoChat } from './DemoChat';
import { TouchToHearPanel } from './TouchToHearPanel';

export function CHWTablet({ onShowMap }: { onShowMap: () => void }) {
  const isOfflineMode = useAppStore((s) => s.isOfflineMode);
  const toggleOfflineMode = useAppStore((s) => s.toggleOfflineMode);
  const currentScenario = useAppStore((s) => s.currentScenario);
  const activeEvaluation = useAppStore((s) => s.activeEvaluation);
  const pendingSyncCount = useAppStore((s) => s.pendingSyncCount);
  const refreshPendingSyncCount = useAppStore((s) => s.refreshPendingSyncCount);
  const activeLanguage = useAppStore((s) => s.activeLanguage);
  const patientCases = useAppStore((s) => s.patientCases);
  const activePatientId = useAppStore((s) => s.activePatientId);
  const setActivePatientId = useAppStore((s) => s.setActivePatientId);
  const markCaseStatus = useAppStore((s) => s.markCaseStatus);

  const [tabMode, setTabMode] = useState<'visual' | 'chat'>('visual');
  const [visitedChecked, setVisitedChecked] = useState(false);

  useEffect(() => {
    void refreshPendingSyncCount();
  }, [refreshPendingSyncCount]);

  const activePatient = patientCases.find((c) => c.id === activePatientId) || patientCases[0];
  const activeRisk = activeEvaluation?.outcome.risk_score ?? activePatient.riskScore ?? currentScenario.riskScore;

  const getScoreBadge = (score: number) => {
    if (score === 3) {
      return 'bg-red-50 text-red-700 border-red-200';
    }
    if (score === 2) {
      return 'bg-amber-50 text-amber-700 border-amber-200';
    }
    return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  };

  return (
    <div className="flex flex-col h-full bg-[#f8fafc] overflow-hidden font-sans text-slate-900">
      {/* Top Header / Portal Navigation matching screenshot */}
      <div className="bg-white border-b border-slate-200 px-4 py-3 flex flex-wrap justify-between items-center gap-3 z-10 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        {/* Left: Pulse Icon & Title */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-700">
            <Activity className="w-5 h-5 stroke-[2.4]" />
          </div>
          <span className="font-bold text-base sm:text-lg text-slate-900 tracking-tight">
            Swara ASHA Portal – Sitamarhi District
          </span>
        </div>

        {/* Right: Worker Pill, Sync Tab, Touch-to-Hear Tab, Offline Badge */}
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Worker Pill */}
          <div className="hidden lg:flex items-center px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs text-slate-700 font-medium shadow-sm">
            Worker: Smt. Sunita Devi (ID: AS-8821)
          </div>

          {/* Patient Sync Button */}
          <button
            onClick={() => setTabMode('chat')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold border transition-all shadow-sm ${
              tabMode === 'chat'
                ? 'bg-[#0f4c42] text-white border-[#0f4c42]'
                : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-200'
            }`}
          >
            <RotateCw className={`w-3.5 h-3.5 ${tabMode === 'chat' ? 'text-white' : 'text-emerald-600'}`} />
            Patient Sync
          </button>

          {/* Touch-to-Hear Button */}
          <button
            onClick={() => setTabMode('visual')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold border transition-all shadow-sm ${
              tabMode === 'visual'
                ? 'bg-[#0f4c42] text-white border-[#0f4c42]'
                : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-200'
            }`}
          >
            <Volume2 className="w-3.5 h-3.5" />
            Touch-to-Hear
          </button>

          {/* Offline / Online Pill Toggle */}
          <button
            onClick={toggleOfflineMode}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider border transition-all shadow-sm ${
              isOfflineMode
                ? 'border-amber-300 bg-amber-50 text-amber-700 hover:bg-amber-100'
                : 'border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
            }`}
            title="Click to toggle Online/Offline Edge mode"
          >
            {isOfflineMode ? (
              <>
                <CloudOff className="w-3.5 h-3.5 text-amber-600" />
                OFFLINE
              </>
            ) : (
              <>
                <Wifi className="w-3.5 h-3.5 text-emerald-600" />
                ONLINE
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Workspace Body */}
      <div className="flex-1 overflow-hidden p-3 md:p-4 flex gap-4">
        {/* Left Column Sidebar matching screenshot */}
        <div className="w-80 min-w-[300px] flex flex-col gap-3 h-full overflow-y-auto hidden sm:flex">
          {/* Card 1: Assigned Visits */}
          <Card className="border border-slate-200 shadow-sm flex-1 bg-white flex flex-col overflow-hidden rounded-xl">
            <CardHeader className="p-3.5 pb-2.5 border-b border-slate-100 flex flex-row items-center justify-between">
              <CardTitle className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                <ClipboardList className="w-4 h-4 text-slate-700" /> Assigned Visits ({patientCases.length})
              </CardTitle>
              <span className="text-[11px] bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold px-2 py-0.5 rounded-md">
                Live Synced
              </span>
            </CardHeader>

            <CardContent className="p-2.5 overflow-y-auto flex-1 space-y-2">
              {patientCases.map((pCase) => {
                const isSelected = pCase.id === activePatientId;
                const isC812 = pCase.id === 'C-812';
                const nameDisplay = isC812 ? 'C-812 • Aarav' : `${pCase.id} • ${pCase.patientName.split(' ')[0]}`;
                const locationDisplay = isC812 ? 'Betsland' : pCase.village.split(' ')[0];

                return (
                  <div
                    key={pCase.id}
                    onClick={() => setActivePatientId(pCase.id)}
                    className={`p-3 rounded-xl cursor-pointer transition-all ${
                      isSelected
                        ? 'border-2 border-emerald-600 bg-emerald-50/25 shadow-sm'
                        : 'border border-slate-200/90 bg-white hover:border-slate-300 hover:bg-slate-50/50 shadow-sm'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span className="font-bold text-xs text-slate-900">
                        {nameDisplay}
                      </span>
                      <Badge
                        variant="outline"
                        className={`text-[10px] h-4 px-1.5 uppercase font-bold tracking-wider rounded border ${getScoreBadge(
                          pCase.riskScore
                        )}`}
                      >
                        SCORE {pCase.riskScore}
                      </Badge>
                    </div>

                    <div className="text-xs text-slate-500 line-clamp-1 mb-2">
                      {pCase.symptomSummary}
                    </div>

                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span className="flex items-center gap-1 text-slate-500">
                        <MapPin className="w-3 h-3 text-slate-400" /> {locationDisplay}
                      </span>
                      <span className={isC812 ? 'text-emerald-700 font-semibold' : 'text-slate-400 font-medium'}>
                        {pCase.lastUpdated}
                      </span>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* Card 2: Action Callout Card matching screenshot */}
          <div className="bg-amber-50/40 p-3.5 rounded-xl border border-amber-200/90 shadow-sm space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold flex items-center gap-1.5">
                {activeRisk === 3 ? (
                  <span className="text-red-700 flex items-center gap-1.5">
                    <ShieldAlert className="w-4 h-4 text-red-600" /> Emergency Dispatch
                  </span>
                ) : activeRisk === 2 ? (
                  <span className="text-amber-800 flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4 text-amber-600" /> Home Visit Needed
                  </span>
                ) : (
                  <span className="text-emerald-800 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Home Monitoring
                  </span>
                )}
              </span>
              <span className="text-xs text-slate-500 font-medium">Patient C-812</span>
            </div>

            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                className="flex-1 text-xs h-8 bg-white hover:bg-slate-50 text-slate-800 border-slate-200 font-semibold shadow-sm rounded-lg"
                onClick={() => alert('Dialing Patient C-812 Guardian: +91 98350 12345')}
              >
                <Phone className="w-3.5 h-3.5 mr-1.5 text-slate-600" /> Call
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="flex-1 text-xs h-8 bg-white hover:bg-slate-50 text-slate-800 border-slate-200 font-semibold shadow-sm rounded-lg"
                onClick={onShowMap}
              >
                <MapPin className="w-3.5 h-3.5 mr-1.5 text-rose-500" /> PHC Route
              </Button>
            </div>

            <Button
              size="sm"
              onClick={() => {
                setVisitedChecked(!visitedChecked);
                markCaseStatus('C-812', visitedChecked ? 'needs_visit' : 'visited');
              }}
              className={`w-full text-xs h-8 font-bold border transition-all rounded-lg shadow-sm ${
                visitedChecked
                  ? 'bg-emerald-600 text-white border-emerald-600 hover:bg-emerald-700'
                  : 'bg-white hover:bg-slate-50 text-slate-800 border-slate-200'
              }`}
            >
              <Check className="w-3.5 h-3.5 mr-1.5 text-slate-700" />
              {visitedChecked ? 'Marked Complete ✓' : 'Mark Visit Complete'}
            </Button>
          </div>

          {/* Card 3: Edge Mode Card matching screenshot */}
          {isOfflineMode ? (
            <div className="bg-amber-50/40 text-amber-900 p-3.5 rounded-xl flex items-start gap-2.5 text-xs shadow-sm border border-amber-200/90">
              <RefreshCw className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-600" />
              <div>
                <div className="font-bold text-amber-800">
                  Edge Mode Active{pendingSyncCount > 0 ? ` • ${pendingSyncCount} queued` : ' • 4 queued'}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  Data will automatically sync on reconnect.
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-emerald-50/40 text-emerald-900 p-3.5 rounded-xl flex items-start gap-2.5 text-xs shadow-sm border border-emerald-200/90">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5 text-emerald-600" />
              <div>
                <div className="font-bold text-emerald-800">Cloud Sync Active</div>
                <div className="text-xs text-slate-500 mt-0.5">
                  Connected to District Health Information Server.
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Main Content Area */}
        <div className="flex-1 h-full overflow-hidden">
          <div className="bg-white h-full rounded-2xl shadow-sm border border-slate-200 overflow-hidden relative">
            {tabMode === 'chat' ? (
              <DemoChat onShowMap={onShowMap} titleOverride="SwaraSetu — Patient C-812 Intake" />
            ) : (
              <TouchToHearPanel language={activeLanguage} onShowMap={onShowMap} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
