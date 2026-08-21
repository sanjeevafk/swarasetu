import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
import { triageVolumeByDistrict as fallbackDistricts, escalationTrend as fallbackTrend } from '@/data/mockDashboardData';
import { Badge } from '@/components/ui/badge';
import { CloudOff } from 'lucide-react';
import type { AnalyticsSummary } from '@/types/api';
import { useAppStore } from '@/store/useAppStore';

import { api } from '@/lib/api';

const CLUSTER_COLORS: Record<string, string> = {
  fever: '#10b981',
  respiratory: '#f97316',
  diarrhoea: '#3b82f6',
  maternal: '#a855f7',
};

export function SupervisorDashboard() {
  const isOfflineMode = useAppStore((s) => s.isOfflineMode);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      if (isOfflineMode) return;
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
    // Poll every 15 s so new cases appear live.
    const t = setInterval(load, 15000);
    return () => {
      cancelled = true;
      clearInterval(t);
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
          { name: 'Fever', value: 45, fill: '#10b981' },
          { name: 'Respiratory', value: 30, fill: '#f97316' },
          { name: 'Diarrhoea', value: 15, fill: '#3b82f6' },
          { name: 'Other', value: 10, fill: '#64748b' },
        ];

  const trendData =
    summary && summary.recent_cases.length > 0
      ? buildRollingRedRate(summary)
      : fallbackTrend;

  return (
    <div className="p-4 bg-slate-50 dark:bg-slate-900 min-h-full space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Regional Overview</h2>
        <div className="flex items-center gap-2">
          {summary && (
            <Badge className="bg-slate-900 text-white dark:bg-white dark:text-slate-900 border-0">
              {summary.total_cases} live case{summary.total_cases === 1 ? '' : 's'} ·{' '}
              {summary.risk_distribution.red} red
            </Badge>
          )}
          {(isOfflineMode || loadFailed) && (
            <Badge variant="outline" className="border-amber-300 text-amber-700 dark:text-amber-400 flex items-center gap-1">
              <CloudOff className="w-3 h-3" /> {isOfflineMode ? 'Offline (cached)' : 'Backend unreachable'}
            </Badge>
          )}
          {!isOfflineMode && !loadFailed && (
            <Badge variant="outline" className="border-blue-200 text-blue-700 dark:text-blue-400">Last 7 Days</Badge>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card className="shadow-sm border-slate-200 dark:border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Triage Volume</CardTitle>
          </CardHeader>
          <CardContent className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={districtData} margin={{ top: 0, right: 0, left: -25, bottom: 0 }}>
                <XAxis dataKey="name" tick={{fontSize: 10}} interval={0} angle={-30} textAnchor="end" />
                <YAxis tick={{fontSize: 10}} />
                <Tooltip />
                <Bar dataKey="volume" fill="#10b981" radius={[2,2,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-slate-200 dark:border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Key Symptoms</CardTitle>
          </CardHeader>
          <CardContent className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={symptomData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={20} outerRadius={45}>
                  {symptomData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="col-span-2 shadow-sm border-slate-200 dark:border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Escalation Trends (%)</CardTitle>
          </CardHeader>
          <CardContent className="h-32">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                <XAxis dataKey="day" tick={{fontSize: 10}} />
                <YAxis tick={{fontSize: 10}} />
                <Tooltip />
                <Line type="monotone" dataKey="rate" stroke="#ef4444" strokeWidth={2} dot={{r: 3}} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card className="shadow-sm border-slate-200 dark:border-slate-800">
        <CardHeader className="pb-2">
          <CardTitle className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Recent Cases</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {recentRows(summary).map((c, i) => (
              <div key={`${c.id}-${i}`} className="flex items-center justify-between p-3 px-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                <div>
                  <div className="text-sm font-bold text-slate-800 dark:text-slate-200">{c.id}</div>
                  <div className="text-xs font-medium text-slate-500">{c.district} • {c.script}</div>
                </div>
                <div className="flex flex-col items-end">
                  <Badge className={`font-bold uppercase tracking-wide text-[10px] ${c.risk === 3 ? 'bg-red-100 text-red-700' : c.risk===2 ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`} variant="outline">
                    Score {c.risk}
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

/** Rolling % of red cases per day derived from live case timestamps. */
function buildRollingRedRate(summary: AnalyticsSummary): { day: string; rate: number }[] {
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const buckets = new Map<string, { total: number; red: number }>();
  for (const c of summary.recent_cases) {
    if (!c.created_at) continue;
    const d = new Date(c.created_at);
    const key = days[d.getDay()];
    const b = buckets.get(key) ?? { total: 0, red: 0 };
    b.total += 1;
    if (c.risk_score === 3) b.red += 1;
    buckets.set(key, b);
  }
  if (buckets.size === 0) return fallbackTrend;
  return [...buckets.entries()].map(([day, b]) => ({
    day,
    rate: b.total === 0 ? 0 : Math.round((b.red / b.total) * 100),
  }));
}

function recentRows(
  summary: AnalyticsSummary | null,
): { id: string; district: string; script: string; risk: number; time: string }[] {
  if (!summary || summary.recent_cases.length === 0) {
    return [
      { id: 'C-8921', district: 'Sitamarhi', script: 'Hindi', risk: 3, time: '10 min ago' },
      { id: 'C-8920', district: 'Sheohar', script: 'Bengali', risk: 1, time: '25 min ago' },
      { id: 'C-8919', district: 'Muzaffarpur', script: 'Hindi', risk: 2, time: '1 hr ago' },
      { id: 'C-8918', district: 'Sitamarhi', script: 'Tamil', risk: 1, time: '2 hrs ago' },
      { id: 'C-8917', district: 'Darbhanga', script: 'Hindi', risk: 3, time: '2.5 hrs ago' },
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
      district: c.district ?? 'Unknown',
      script: c.language.toUpperCase(),
      risk: c.risk_score,
      time,
    };
  });
}
