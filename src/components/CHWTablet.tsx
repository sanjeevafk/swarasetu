import { useAppStore } from '@/store/useAppStore';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { User, Activity, CheckCircle2, CloudOff, RefreshCw } from 'lucide-react';
import { DemoChat } from './DemoChat';

export function CHWTablet({ onShowMap }: { onShowMap: () => void }) {
  const { isOfflineMode, toggleOfflineMode, currentScenario } = useAppStore();

  return (
    <div className="flex flex-col h-full bg-slate-100 dark:bg-slate-900 overflow-hidden font-sans">
      {/* Tablet Header / Status Bar */}
      <div className="bg-emerald-700 dark:bg-emerald-900 text-white p-3 flex justify-between items-center shadow-md z-10">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5" />
          <span className="font-bold text-lg tracking-tight">Swara ASHA Portal</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center space-x-2 bg-black/20 px-2 py-1 rounded-md">
            <Switch id="offline-mode" checked={isOfflineMode} onCheckedChange={toggleOfflineMode} />
            <Label htmlFor="offline-mode" className="text-xs font-semibold uppercase tracking-wider cursor-pointer">
              {isOfflineMode ? <span className="flex items-center text-amber-300"><CloudOff className="w-3 h-3 mr-1" /> Offline</span> : <span className="flex items-center text-emerald-300"><CheckCircle2 className="w-3 h-3 mr-1" /> Online</span>}
            </Label>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-hidden p-2 md:p-4 pb-0 flex gap-4">
        {/* Sidebar - Case List */}
        <div className="w-1/3 min-w-[200px] flex-col gap-3 h-full overflow-y-auto hidden sm:flex">
           <Card className="border-0 shadow-sm flex-1 bg-white/50 dark:bg-slate-950/50">
             <CardHeader className="p-4 pb-2 border-b border-slate-100 dark:border-slate-800">
               <CardTitle className="text-sm font-bold text-slate-800 dark:text-slate-200">Pending Visits (4)</CardTitle>
             </CardHeader>
             <CardContent className="p-0">
               <div className="divide-y divide-slate-100 dark:divide-slate-800">
                 <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 border-l-4 border-emerald-500 cursor-pointer">
                   <div className="flex justify-between items-start mb-1">
                     <span className="font-semibold text-sm">Patient C-812</span>
                     <Badge variant="outline" className="text-[10px] h-4 leading-3 uppercase bg-white dark:bg-black">Score {currentScenario.riskScore}</Badge>
                   </div>
                   <div className="text-xs text-slate-500 flex items-center"><User className="w-3 h-3 mr-1" /> Currently Active</div>
                 </div>
                 {[1,2,3].map(i => (
                   <div key={i} className="p-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50">
                     <div className="flex justify-between items-start mb-1">
                       <span className="font-semibold text-sm text-slate-700 dark:text-slate-300">Patient C-81{i+2}</span>
                     </div>
                     <div className="text-xs text-slate-400">Not assessed</div>
                   </div>
                 ))}
               </div>
             </CardContent>
           </Card>
           
           {isOfflineMode && (
             <div className="bg-amber-100 dark:bg-amber-900/50 text-amber-800 dark:text-amber-400 p-3 rounded-xl flex items-start gap-2 text-sm shadow-sm border border-amber-200 dark:border-amber-800">
               <RefreshCw className="w-5 h-5 flex-shrink-0 mt-0.5" />
               <div>
                  <div className="font-bold mb-0.5">Offline Mode Active</div>
                  <div className="text-xs font-medium">Data will sync when connected. Triage engine running on-device.</div>
               </div>
             </div>
           )}
        </div>

        {/* Main Content - Triage Frame */}
        <div className="flex-1 h-full pb-4">
           <div className="bg-white dark:bg-slate-950 h-full rounded-2xl shadow-lg border-[6px] border-slate-200 dark:border-slate-800 overflow-hidden relative">
              {/* Camera Notch simulation */}
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-4 bg-slate-200 dark:bg-slate-800 rounded-b-xl z-20 flex justify-center items-end pb-1">
                <div className="w-2 h-2 rounded-full bg-slate-400 dark:bg-slate-700" />
              </div>
              <DemoChat onShowMap={onShowMap} />
           </div>
        </div>
      </div>
    </div>
  );
}
