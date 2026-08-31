import { useState, lazy, Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAppStore } from '@/store/useAppStore';
import { DemoChat } from '@/components/DemoChat';
import { CHWTablet } from '@/components/CHWTablet';
import { LanguageBadge } from '@/components/LanguageBadge';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Stethoscope, Tablet, BarChart3, X, Activity, Loader2 } from 'lucide-react';

// Lazy load heavy chart and mapping components for sub-second initial bundle load
const SupervisorDashboard = lazy(() =>
  import('@/components/SupervisorDashboard').then((m) => ({ default: m.SupervisorDashboard }))
);
const PHCMap = lazy(() =>
  import('@/components/PHCMap').then((m) => ({ default: m.PHCMap }))
);

function ComponentFallback() {
  return (
    <div className="h-full min-h-[300px] w-full flex flex-col items-center justify-center text-slate-400 gap-2 font-sans">
      <Loader2 className="w-6 h-6 animate-spin text-emerald-700" />
      <span className="text-xs font-semibold text-slate-600">Loading module…</span>
    </div>
  );
}

export function Demo() {
  const activeRole = useAppStore((s) => s.activeRole);
  const isDemoActive = useAppStore((s) => s.isDemoActive);
  const resetDemo = useAppStore((s) => s.resetDemo);
  const startDemo = useAppStore((s) => s.startDemo);

  const [showMap, setShowMap] = useState(false);

  if (!isDemoActive) return null;

  const currentTab = activeRole.toLowerCase();

  const handleTabChange = (val: string) => {
    if (val === 'patient') startDemo('Patient');
    else if (val === 'chw') startDemo('CHW');
    else if (val === 'supervisor') startDemo('Supervisor');
  };

  return (
    <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-md z-50 flex flex-col sm:p-3 md:p-5 font-sans">
      <div className="bg-white w-full h-full max-w-7xl mx-auto rounded-none sm:rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-slate-200">
        {/* Top Navigation */}
        <div className="bg-white border-b border-slate-200 px-4 py-2.5 flex items-center justify-between z-20 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="icon"
              onClick={resetDemo}
              className="h-8 w-8 rounded-lg border-slate-200 hover:bg-slate-50 text-slate-700 shadow-xs"
              title="Return to Home"
            >
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-700">
                <Activity className="w-4 h-4 stroke-[2.5]" />
              </div>
              <h1 className="font-bold text-base text-slate-900 flex items-center gap-2 tracking-tight">
                SwaraSetu
                <span className="hidden sm:inline-block text-xs font-semibold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                  Live Prototype
                </span>
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <LanguageBadge />
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 bg-[#f8fafc] relative overflow-hidden flex flex-col">
          <Tabs value={currentTab} onValueChange={handleTabChange} className="h-full flex flex-col w-full">
            {/* View Selector Tabs */}
            <div className="px-4 pt-2 pb-2 flex justify-center bg-white border-b border-slate-200">
              <TabsList className="bg-slate-100 p-1 rounded-xl h-auto border border-slate-200/80 shadow-inner flex gap-1">
                <TabsTrigger
                  value="patient"
                  className="px-4 py-1.5 rounded-lg data-[state=active]:bg-[#0f4c42] data-[state=active]:text-white data-[state=active]:shadow-xs text-xs font-bold text-slate-600 transition-all cursor-pointer"
                >
                  <Stethoscope className="w-3.5 h-3.5 mr-1.5" /> Patient Voice View
                </TabsTrigger>
                <TabsTrigger
                  value="chw"
                  className="px-4 py-1.5 rounded-lg data-[state=active]:bg-[#0f4c42] data-[state=active]:text-white data-[state=active]:shadow-xs text-xs font-bold text-slate-600 transition-all cursor-pointer"
                >
                  <Tablet className="w-3.5 h-3.5 mr-1.5" /> ASHA Portal Tablet
                </TabsTrigger>
                <TabsTrigger
                  value="supervisor"
                  className="px-4 py-1.5 rounded-lg data-[state=active]:bg-[#0f4c42] data-[state=active]:text-white data-[state=active]:shadow-xs text-xs font-bold text-slate-600 transition-all cursor-pointer"
                >
                  <BarChart3 className="w-3.5 h-3.5 mr-1.5" /> Supervisor Dashboard
                </TabsTrigger>
              </TabsList>
            </div>

            <div className="flex-1 relative overflow-hidden">
              <AnimatePresence mode="wait">
                <TabsContent
                  value="patient"
                  className="h-full m-0 data-[state=inactive]:hidden flex justify-center items-center p-3 sm:p-4 bg-slate-100 relative overflow-hidden"
                >
                  <motion.div
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -15 }}
                    className="w-full h-full max-h-[620px] sm:w-[390px] rounded-2xl bg-white shadow-xl overflow-hidden border border-slate-300 relative z-10 flex flex-col"
                  >
                    <DemoChat onShowMap={() => setShowMap(true)} />
                  </motion.div>
                </TabsContent>

                <TabsContent
                  value="chw"
                  className="h-full m-0 data-[state=inactive]:hidden p-0 relative bg-[#f8fafc]"
                >
                  <motion.div
                    initial={{ opacity: 0, scale: 0.99 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.99 }}
                    className="w-full h-full mx-auto shadow-none overflow-hidden bg-[#f8fafc] relative z-10"
                  >
                    <CHWTablet onShowMap={() => setShowMap(true)} />
                  </motion.div>
                </TabsContent>

                <TabsContent
                  value="supervisor"
                  className="h-full m-0 data-[state=inactive]:hidden p-0 sm:p-3 overflow-y-auto bg-[#f8fafc]"
                >
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="w-full max-w-6xl mx-auto"
                  >
                    <Suspense fallback={<ComponentFallback />}>
                      <SupervisorDashboard />
                    </Suspense>
                  </motion.div>
                </TabsContent>
              </AnimatePresence>
            </div>
          </Tabs>
        </div>

        {/* Map Modal Overlay */}
        <AnimatePresence>
          {showMap && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 sm:p-8"
            >
              <motion.div
                initial={{ scale: 0.94, y: 15 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.94, y: 15 }}
                className="w-full max-w-4xl h-[80vh] bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col relative border border-slate-200"
              >
                <div className="absolute top-4 right-4 z-50">
                  <Button
                    variant="secondary"
                    size="icon"
                    onClick={() => setShowMap(false)}
                    className="rounded-full shadow-md h-9 w-9 bg-white hover:bg-slate-100 text-slate-800 border border-slate-200"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
                <Suspense fallback={<ComponentFallback />}>
                  <PHCMap />
                </Suspense>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
