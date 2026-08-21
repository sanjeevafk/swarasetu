import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Radio, Activity, Users, Globe2, ShieldCheck, HeartPulse, MapPin } from 'lucide-react';
import { useAppStore, type UserRole } from '@/store/useAppStore';

export function Landing() {
  const startDemo = useAppStore(state => state.startDemo);

  const roles: { role: UserRole; icon: React.ReactNode; label: string; desc: string }[] = [
    { role: 'Patient', icon: <Activity className="w-5 h-5" />, label: 'As Patient', desc: 'Voice-first symptom reporting' },
    { role: 'CHW', icon: <HeartPulse className="w-5 h-5" />, label: 'As ASHA Worker', desc: 'Offline triage tablet' },
    { role: 'Supervisor', icon: <Users className="w-5 h-5" />, label: 'As Supervisor', desc: 'PHC Dashboard analytics' }
  ];

  return (
    <div className="min-h-screen bg-[#fffaf0] dark:bg-[#0f172a] flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Decorative pulse background */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-emerald-500/5 dark:bg-emerald-500/10 rounded-full blur-[100px] -z-10" />
      <div className="absolute top-1/3 left-1/3 w-[400px] h-[400px] bg-sky-500/5 dark:bg-sky-500/10 rounded-full blur-[80px] -z-10" />

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md flex flex-col items-center text-center z-10"
      >
        <div className="h-16 w-16 bg-emerald-100 dark:bg-emerald-900/50 rounded-2xl flex items-center justify-center mb-6 shadow-sm border border-emerald-200 dark:border-emerald-800">
          <Radio className="w-8 h-8 text-emerald-600 dark:text-emerald-400" />
        </div>
        
        <h1 className="text-4xl md:text-5xl font-extrabold text-slate-900 dark:text-white mb-4 tracking-tight">
          Swara<span className="text-emerald-600 dark:text-emerald-400">Setu</span>
          <span className="block text-2xl font-serif text-amber-600 dark:text-amber-500 mt-2">स्वर सेतु</span>
        </h1>
        
        <p className="text-xl text-slate-600 dark:text-slate-300 font-medium mb-8">
          Your voice, your village, your first doctor.
        </p>

        <Card className="w-full bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-slate-200 dark:border-slate-800 shadow-xl mb-10 overflow-hidden">
          <CardContent className="p-0">
            <div className="grid grid-cols-2 divide-x divide-y divide-slate-100 dark:divide-slate-800/60 border-b border-slate-100 dark:border-slate-800/60">
              <div className="p-4 flex flex-col items-center text-center">
                <Globe2 className="w-5 h-5 text-amber-500 mb-2" />
                <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Offline-First</span>
                <span className="text-xs text-slate-500">No internet required</span>
              </div>
              <div className="p-4 flex flex-col items-center text-center">
                <Activity className="w-5 h-5 text-emerald-500 mb-2" />
                <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Voice AI</span>
                <span className="text-xs text-slate-500">Language agnostic</span>
              </div>
              <div className="p-4 flex flex-col items-center text-center">
                <ShieldCheck className="w-5 h-5 text-blue-500 mb-2" />
                <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">IMCI Protocol</span>
                <span className="text-xs text-slate-500">WHO standards</span>
              </div>
              <div className="p-4 flex flex-col items-center text-center">
                <MapPin className="w-5 h-5 text-red-500 mb-2" />
                <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Auto-Routing</span>
                <span className="text-xs text-slate-500">Nearest PHC mapping</span>
              </div>
            </div>
            <div className="bg-slate-50 dark:bg-slate-950/50 p-4 text-sm text-slate-600 dark:text-slate-400 text-center">
              <p className="font-semibold text-slate-800 dark:text-slate-200 mb-1">Impact Potential</p>
              Bridging the gap for 800M rural Indians with only 0.7 doctors per 1,000 people.
            </div>
          </CardContent>
        </Card>

        <div className="w-full space-y-3">
          <p className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest mb-3">Try the 90-second Demo</p>
          {roles.map(({ role, icon, label, desc }) => (
            <motion.div key={role} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
              <Button 
                onClick={() => startDemo(role)}
                className="w-full h-auto py-4 px-5 justify-start text-left bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 text-slate-800 dark:text-slate-100 shadow-sm transition-all rounded-xl"
                variant="outline"
              >
                <div className="flex items-center gap-4">
                  <div className={`p-2.5 rounded-lg ${role === 'Patient' ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/50 dark:text-emerald-400' : role === 'CHW' ? 'bg-amber-100 text-amber-600 dark:bg-amber-900/50 dark:text-amber-400' : 'bg-blue-100 text-blue-600 dark:bg-blue-900/50 dark:text-blue-400'}`}>
                    {icon}
                  </div>
                  <div>
                    <div className="font-bold text-base text-slate-900 dark:text-slate-100">{label}</div>
                    <div className="font-medium text-[13px] text-slate-500 dark:text-slate-400 mt-0.5">{desc}</div>
                  </div>
                </div>
              </Button>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
