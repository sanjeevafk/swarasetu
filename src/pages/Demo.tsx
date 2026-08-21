import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAppStore } from '@/store/useAppStore';
import { DemoChat } from '@/components/DemoChat';
import { CHWTablet } from '@/components/CHWTablet';
import { SupervisorDashboard } from '@/components/SupervisorDashboard';
import { LanguageBadge } from '@/components/LanguageBadge';
import { PHCMap } from '@/components/PHCMap';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Stethoscope, Tablet, BarChart3, X } from 'lucide-react';

export function Demo() {
  const { activeRole, isDemoActive, resetDemo } = useAppStore();
  const [showMap, setShowMap] = useState(false);
  const [activeTab, setActiveTab] = useState(activeRole.toString().toLowerCase());

  useEffect(() => {
    setActiveTab(activeRole.toString().toLowerCase());
  }, [activeRole]);

  if (!isDemoActive) return null;

  return (
    <div className="fixed inset-0 bg-slate-900 z-50 flex flex-col sm:p-4 md:p-8 font-sans">
      <div className="bg-slate-100 dark:bg-slate-950 w-full h-full max-w-6xl mx-auto rounded-none sm:rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-slate-200 dark:border-slate-800">
        
        {/* Top Navigation */}
        <div className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 p-3 md:p-4 flex items-center justify-between z-20">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={resetDemo} className="hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 rounded-full">
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h2 className="font-bold text-lg md:text-xl text-slate-800 dark:text-slate-100 flex items-center gap-2 tracking-tight">
                SwaraSetu 
                <span className="hidden sm:inline text-sm font-normal text-slate-500">Live Prototype</span>
              </h2>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <LanguageBadge />
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 bg-slate-50 dark:bg-slate-950/50 relative overflow-hidden">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col w-full">
            <div className="px-4 pt-3 flex justify-center bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
              <TabsList className="bg-slate-100 dark:bg-slate-800/50 p-1 rounded-t-xl rounded-b-none border-b-0 h-auto">
                <TabsTrigger value="patient" className="px-6 py-2.5 rounded-t-lg rounded-b-none data-[state=active]:bg-white dark:data-[state=active]:bg-slate-700 data-[state=active]:shadow-sm text-sm font-semibold">
                  <Stethoscope className="w-4 h-4 mr-2" /> Patient View
                </TabsTrigger>
                <TabsTrigger value="chw" className="px-6 py-2.5 rounded-t-lg rounded-b-none data-[state=active]:bg-white dark:data-[state=active]:bg-slate-700 data-[state=active]:shadow-sm text-sm font-semibold">
                  <Tablet className="w-4 h-4 mr-2" /> ASHA Tablet
                </TabsTrigger>
                <TabsTrigger value="supervisor" className="px-6 py-2.5 rounded-t-lg rounded-b-none data-[state=active]:bg-white dark:data-[state=active]:bg-slate-700 data-[state=active]:shadow-sm text-sm font-semibold">
                  <BarChart3 className="w-4 h-4 mr-2" /> Supervisor
                </TabsTrigger>
              </TabsList>
            </div>

            <div className="flex-1 relative overflow-hidden">
              <AnimatePresence mode="wait">
                <TabsContent value="patient" className="h-full m-0 data-[state=inactive]:hidden flex justify-center items-center bg-[url('https://images.unsplash.com/photo-1532375810565-ffa8fb18092a?q=80&w=2600')] bg-cover bg-center relative">
                   <div className="absolute inset-0 bg-black/50 backdrop-blur-[2px] z-0" />
                   <motion.div 
                     initial={{ opacity: 0, y: 20 }}
                     animate={{ opacity: 1, y: 0 }}
                     exit={{ opacity: 0, y: -20 }}
                     className="w-full h-full sm:h-[750px] sm:max-h-[90vh] sm:w-[400px] sm:rounded-[2.5rem] bg-white dark:bg-black shadow-2xl overflow-hidden border-[8px] border-slate-800 relative z-10"
                   >
                     {/* iPhone Notch */}
                     <div className="absolute top-0 inset-x-0 h-6 bg-slate-800 rounded-b-3xl w-40 mx-auto z-50 flex justify-center items-end pb-1">
                        <div className="w-16 h-1.5 bg-black/50 rounded-full" />
                     </div>
                     <DemoChat onShowMap={() => setShowMap(true)} />
                   </motion.div>
                </TabsContent>

                <TabsContent value="chw" className="h-full m-0 data-[state=inactive]:hidden p-0 sm:p-6 lg:p-12 relative bg-slate-50 dark:bg-slate-900">
                   <motion.div
                     initial={{ opacity: 0, scale: 0.95 }}
                     animate={{ opacity: 1, scale: 1 }}
                     exit={{ opacity: 0, scale: 0.95 }}
                     className="w-full h-full max-w-5xl mx-auto rounded-none sm:rounded-3xl shadow-2xl overflow-hidden border-[12px] border-slate-300 dark:border-slate-800 bg-white relative z-10"
                   >
                     {/* Tablet Bezel Elements */}
                     <div className="absolute left-0 top-1/2 -translate-y-1/2 w-3 h-16 bg-slate-400 dark:bg-slate-700 -ml-3 rounded-l-md hidden sm:block" />
                     <div className="absolute top-0 left-1/2 -translate-x-1/2 w-4 h-4 rounded-full bg-slate-900 dark:bg-black mt-2 hidden sm:block shadow-inner ring-1 ring-white/10" />
                     
                     <CHWTablet onShowMap={() => setShowMap(true)} />
                   </motion.div>
                </TabsContent>

                <TabsContent value="supervisor" className="h-full m-0 data-[state=inactive]:hidden p-0 sm:p-4 md:p-6 overflow-y-auto bg-slate-100 dark:bg-slate-950">
                   <motion.div
                     initial={{ opacity: 0 }}
                     animate={{ opacity: 1 }}
                     exit={{ opacity: 0 }}
                     className="w-full max-w-6xl mx-auto"
                   >
                     <SupervisorDashboard />
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
              className="absolute inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 sm:p-8"
            >
              <motion.div 
                initial={{ scale: 0.9, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.9, y: 20 }}
                className="w-full max-w-4xl h-[80vh] bg-white dark:bg-slate-900 rounded-2xl shadow-2xl overflow-hidden flex flex-col relative"
              >
                <div className="absolute top-4 right-4 z-50">
                  <Button variant="secondary" size="icon" onClick={() => setShowMap(false)} className="rounded-full shadow-lg h-10 w-10 bg-white hover:bg-slate-100 text-slate-800 border border-slate-200">
                    <X className="w-5 h-5" />
                  </Button>
                </div>
                <PHCMap />
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
