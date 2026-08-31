import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
import { triageVolumeByDistrict as fallbackDistricts, escalationTrend as fallbackTrend } from '@/data/mockDashboardData';
import { Badge } from '@/components/ui/badge';
import { CloudOff, Activity, Users, CheckCircle2 } from 'lucide-react';
import type { AnalyticsSummary } from '@/types/api';
import { useAppStore } from '@/store/useAppStore';
import { api } from '@/lib/api';

const CLUSTER_COLORS: Record<string, string> = {
  fever: '#059669',
  respiratory: '#f97316',
  diarrhoea: '#0284c7',
  maternal: '#7c3aed',
};

export function SupervisorDashboard() {
  const isOfflineMode = useAppStore((s) => s.isOfflineMode);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      if (isOfflineMode || document.visibilityState !== 'visible') return;
      try {
        const data = await api.analyticsSummary();
        if (!cancelled) {
          setSummary(data);
          setLoadFailed(false);
        }
      } catch {
        if (!cancelled) setLoadFailed(true);
      }
    };

    void load();

    // Poll every 15s only while component is mounted and tab is visible
    const t = setInterval(() => {
      if (document.visibilityState === 'visible') {
        void load();
      }
    }, 15000);

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        void load();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      cancelled = true;
      clearInterval(t);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isOfflineMode]);

  const districtData =
    summary && summary.districts.length > 0
      ? summary.districts.map((d) => ({ name: d.district, volume: d.volume }))
      : fallbackDistricts;

  const symptomData =
    summary && summary.symptom_breakdown.length > 0
      ? summary.symptom_breakdown.map((s) => ({
          name: s.cluster.charAt(0).toUpperCase() + s.cluster.slice(1),
          value: s.count,
          fill: CLUSTER_COLORS[s.cluster] ?? '#64748b',
        }))
      : [
          { name: 'Fever', value: 45, fill: '#059669' },
          { name: 'Respiratory', value: 30, fill: '#f97316' },
          { name: 'Diarrhoea', value: 15, fill: '#0284c7' },
          { name: 'Other', value: 10, fill: '#64748b' },
        ];

  const trendData =
    summary && summary.recent_cases.length > 0
      ? buildRollingRedRate(summary)
      : fallbackTrend;

  return (
    <div className="p-4 md:p-6 bg-[#f8fafc] min-h-full space-y-4 font-sans text-slate-900">
      {/* Top Title Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-200">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-700" />
            Regional Overview – Sitamarhi District
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time IMCI triage surveillance and ASHA frontline dispatch monitoring
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {summary && (
            <Badge className="bg-[#0f4c42] text-white border-0 font-semibold px-3 py-1 text-xs">
              {summary.total_cases} live case{summary.total_cases === 1 ? '' : 's'} ·{' '}
              {summary.risk_distribution.red} red emergency
            </Badge>
          )}
          {(isOfflineMode || loadFailed) && (
            <Badge variant="outline" className="border-amber-300 bg-amber-50 text-amber-800 flex items-center gap-1 text-xs font-semibold">
              <CloudOff className="w-3.5 h-3.5 text-amber-600" /> {isOfflineMode ? 'Offline (Edge Synced)' : 'Backend unreachable'}
            </Badge>
          )}
          {!isOfflineMode && !loadFailed && (
            <Badge variant="outline" className="border-emerald-200 bg-emerald-50 text-emerald-800 text-xs font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mr-1" /> Live Sync Connected
            </Badge>
          )}
        </div>
      </div>

      {/* Analytics Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* District Triage Volume */}
        <Card className="shadow-sm border-slate-200 bg-white rounded-xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Triage Volume by Sub-District
            </CardTitle>
          </CardHeader>
          <CardContent className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={districtData} margin={{ top: 5, right: 10, left: -20, bottom: 15 }}>
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} interval={0} angle={-25} textAnchor="end" />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '0.5rem', fontSize: '12px' }}
                />
                <Bar dataKey="volume" fill="#0f4c42" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Key Symptoms Cluster Pie Chart */}
        <Card className="shadow-sm border-slate-200 bg-white rounded-xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Syndromic Cluster Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent className="h-44 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={symptomData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={30} outerRadius={55} paddingAngle={2}>
                  {symptomData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '0.5rem', fontSize: '12px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Escalation Rate Trend */}
        <Card className="col-span-1 md:col-span-2 shadow-sm border-slate-200 bg-white rounded-xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              High Risk Escalation Trend (%)
            </CardTitle>
          </CardHeader>
          <CardContent className="h-36">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{ top: 5, right: 15, left: -20, bottom: 0 }}>
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '0.5rem', fontSize: '12px' }}
                />
                <Line type="monotone" dataKey="rate" stroke="#ef4444" strokeWidth={2.5} dot={{ r: 4, fill: '#ef4444' }} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Recent Cases Table */}
      <Card className="shadow-sm border-slate-200 bg-white rounded-xl overflow-hidden">
        <CardHeader className="p-3.5 pb-2.5 border-b border-slate-100 flex flex-row items-center justify-between">
          <CardTitle className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
            <Users className="w-4 h-4 text-emerald-700" /> Recent Frontline Intakes
          </CardTitle>
          <span className="text-xs text-slate-500 font-medium">Sitamarhi Block</span>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y divide-slate-100">
            {recentRows(summary).map((c, i) => (
              <div
                key={`${c.id}-${i}`}
                className="flex items-center justify-between p-3.5 hover:bg-slate-50 transition-colors"
              >
                <div>
                  <div className="text-xs font-bold text-slate-900">{c.id}</div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {c.district} • <span className="font-semibold text-slate-700">{c.script}</span>
                  </div>
                </div>
                <div className="flex flex-col items-end">
                  <Badge
                    className={`font-bold uppercase tracking-wider text-[10px] px-2 py-0.5 rounded border ${
                      c.risk === 3
                        ? 'bg-red-50 text-red-700 border-red-200'
                        : c.risk === 2
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    }`}
                    variant="outline"
                  >
                    SCORE {c.risk}
                  </Badge>
                  <span className="text-[10px] font-medium text-slate-400 mt-1">{c.time}</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function buildRollingRedRate(summary: AnalyticsSummary): { day: string; rate: number }[] {
  const buckets = new Map<string, { total: number; red: number; timestamp: number }>();
  for (const c of summary.recent_cases) {
    if (!c.created_at) continue;
    const d = new Date(c.created_at);
    if (isNaN(d.getTime())) continue;
    const key = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    const dayTimestamp = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
    const b = buckets.get(key) ?? { total: 0, red: 0, timestamp: dayTimestamp };
    b.total += 1;
    if (c.risk_score === 3) b.red += 1;
    buckets.set(key, b);
  }
  if (buckets.size === 0) return fallbackTrend;
  return [...buckets.entries()]
    .sort((a, b) => a[1].timestamp - b[1].timestamp)
    .slice(-7)
    .map(([day, b]) => ({
      day,
      rate: b.total === 0 ? 0 : Math.round((b.red / b.total) * 100),
    }));
}

function recentRows(
  summary: AnalyticsSummary | null
): { id: string; district: string; script: string; risk: number; time: string }[] {
  if (!summary || summary.recent_cases.length === 0) {
    return [
      { id: 'C-8921', district: 'Sitamarhi', script: 'HINDI', risk: 3, time: '10 min ago' },
      { id: 'C-8920', district: 'Sheohar', script: 'BENGALI', risk: 1, time: '25 min ago' },
      { id: 'C-8919', district: 'Muzaffarpur', script: 'HINDI', risk: 2, time: '1 hr ago' },
      { id: 'C-8918', district: 'Sitamarhi', script: 'TAMIL', risk: 1, time: '2 hrs ago' },
      { id: 'C-8917', district: 'Darbhanga', script: 'HINDI', risk: 3, time: '2.5 hrs ago' },
    ];
  }
  return summary.recent_cases.map((c) => {
    const created = c.created_at ? new Date(c.created_at) : null;
    const mins = created ? Math.max(0, Math.round((Date.now() - created.getTime()) / 60000)) : null;
    const time =
      mins === null
        ? ''
        : mins < 60
        ? `${mins} min ago`
        : `${Math.round(mins / 60)} hr${Math.round(mins / 60) === 1 ? '' : 's'} ago`;
    return {
      id: `C-${String(c.id).padStart(4, '0')}`,
      district: c.district ?? 'Sitamarhi',
      script: c.language.toUpperCase(),
      risk: c.risk_score,
      time,
    };
  });
}
