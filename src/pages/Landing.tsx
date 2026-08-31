import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Activity, Globe2, ShieldCheck, HeartPulse, MapPin, ChevronRight, Stethoscope, Tablet, BarChart3 } from 'lucide-react';
import { useAppStore, type UserRole } from '@/store/useAppStore';

export function Landing() {
  const startDemo = useAppStore((state) => state.startDemo);

  const roles: { role: UserRole; icon: React.ReactNode; label: string; desc: string }[] = [
    { role: 'CHW', icon: <Tablet className="w-5 h-5" />, label: 'ASHA Worker Portal', desc: 'Zero-literacy touch-to-hear triage tablet' },
    { role: 'Patient', icon: <Stethoscope className="w-5 h-5" />, label: 'Patient Voice Intake', desc: 'Multilingual speech symptom reporting' },
    { role: 'Supervisor', icon: <BarChart3 className="w-5 h-5" />, label: 'Supervisor Dashboard', desc: 'District PHC surveillance & caseload' },
  ];

  return (
    <div className="min-h-screen bg-[#f8fafc] flex flex-col items-center justify-center p-4 sm:p-6 relative overflow-hidden font-sans text-slate-900">
      {/* Background ambient accents */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] bg-emerald-500/5 rounded-full blur-[100px] -z-10" />

      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-lg flex flex-col items-center text-center z-10"
      >
        {/* Pulse Logo Badge */}
        <div className="h-16 w-16 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center justify-center mb-4 shadow-sm text-emerald-700">
          <Activity className="w-8 h-8 stroke-[2.4]" />
        </div>

        <h1 className="text-3xl md:text-4xl font-extrabold text-slate-900 mb-2 tracking-tight">
          Swara<span className="text-emerald-700">Setu</span>
          <span className="block text-xl font-medium text-amber-700 mt-1 font-serif">
            स्वर सेतु · Sitamarhi Frontline Healthcare
          </span>
        </h1>

        <p className="text-sm md:text-base text-slate-600 font-medium mb-6 max-w-md">
          Offline-first multilingual clinical triage for rural communities and ASHA frontline workers.
        </p>

        {/* Feature Highlights Grid Card */}
        <Card className="w-full bg-white border border-slate-200 shadow-sm mb-6 rounded-2xl overflow-hidden">
          <CardContent className="p-0">
            <div className="grid grid-cols-2 divide-x divide-y divide-slate-100 border-b border-slate-100">
              <div className="p-3.5 flex flex-col items-center text-center">
                <Globe2 className="w-5 h-5 text-amber-600 mb-1.5" />
                <span className="text-xs font-bold text-slate-900">100% Offline Edge</span>
                <span className="text-[11px] text-slate-500">Auto-syncs on reconnect</span>
              </div>
              <div className="p-3.5 flex flex-col items-center text-center">
                <HeartPulse className="w-5 h-5 text-emerald-600 mb-1.5" />
                <span className="text-xs font-bold text-slate-900">Touch-to-Hear</span>
                <span className="text-[11px] text-slate-500">Zero-literacy visual cards</span>
              </div>
              <div className="p-3.5 flex flex-col items-center text-center">
                <ShieldCheck className="w-5 h-5 text-blue-600 mb-1.5" />
                <span className="text-xs font-bold text-slate-900">WHO IMCI Protocols</span>
                <span className="text-[11px] text-slate-500">Clinical grade risk triage</span>
              </div>
              <div className="p-3.5 flex flex-col items-center text-center">
                <MapPin className="w-5 h-5 text-rose-600 mb-1.5" />
                <span className="text-xs font-bold text-slate-900">PHC Geo-Routing</span>
                <span className="text-[11px] text-slate-500">Nearest facility dispatch</span>
              </div>
            </div>

            <div className="bg-slate-50/80 p-3 text-xs text-slate-600 text-center font-medium">
              Designed for 1M+ ASHA workers across rural primary healthcare sub-centers.
            </div>
          </CardContent>
        </Card>

        {/* Role Demo Triggers */}
        <div className="w-full space-y-2.5">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1 text-left">
            Launch Prototype View
          </p>

          {roles.map(({ role, icon, label, desc }) => (
            <motion.div key={role} whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
              <Button
                onClick={() => startDemo(role)}
                className="w-full h-auto py-3.5 px-4 justify-between text-left bg-white hover:bg-slate-50 border border-slate-200 hover:border-slate-300 text-slate-900 shadow-sm transition-all rounded-xl"
                variant="outline"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`p-2.5 rounded-lg ${
                      role === 'CHW'
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : role === 'Patient'
                        ? 'bg-blue-50 text-blue-800 border border-blue-200'
                        : 'bg-amber-50 text-amber-800 border border-amber-200'
                    }`}
                  >
                    {icon}
                  </div>
                  <div>
                    <div className="font-bold text-sm text-slate-900">{label}</div>
                    <div className="font-medium text-xs text-slate-500 mt-0.5">{desc}</div>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-400" />
              </Button>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
