import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
import { triageVolumeByDistrict, symptomDistribution, escalationTrend, recentCases } from '@/data/mockDashboardData';
import { Badge } from '@/components/ui/badge';

export function SupervisorDashboard() {
  return (
    <div className="p-4 bg-slate-50 dark:bg-slate-900 min-h-full space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Regional Overview</h2>
        <Badge variant="outline" className="border-blue-200 text-blue-700 dark:text-blue-400">Last 7 Days</Badge>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card className="shadow-sm border-slate-200 dark:border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Triage Volume</CardTitle>
          </CardHeader>
          <CardContent className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={triageVolumeByDistrict} margin={{ top: 0, right: 0, left: -25, bottom: 0 }}>
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
                <Pie data={symptomDistribution} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={20} outerRadius={45}>
                  {symptomDistribution.map((entry, index) => (
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
              <LineChart data={escalationTrend} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
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
            {recentCases.map((c, i) => (
              <div key={i} className="flex items-center justify-between p-3 px-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
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
