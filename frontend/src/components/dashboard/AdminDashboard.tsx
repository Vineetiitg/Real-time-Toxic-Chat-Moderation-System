import React, { useEffect, useState } from 'react';
import { API_BASE_URL } from '../../config/env';
import {
  ShieldCheck,
  Server,
  Activity,
  Cpu,
  BarChart2,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  MessageSquare,
  Zap,
  Globe,
  TrendingUp,
  Clock,
  Shield,
  Brain,
  Layers,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  AreaChart,
  Area,
  CartesianGrid,
} from 'recharts';

export default function AdminDashboard() {
  const [healthData, setHealthData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const fetchHealth = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/health`);
      if (res.ok) {
        const data = await res.json();
        setHealthData(data);
      }
    } catch (e) {
      console.error('Failed to fetch health status:', e);
    }
    setIsLoading(false);
    setLastRefreshed(new Date());
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  // Demo data
  const severityDistribution = [
    { name: 'SAFE', value: 82, color: '#10b981' },
    { name: 'LOW', value: 9, color: '#3b82f6' },
    { name: 'MEDIUM', value: 6, color: '#f59e0b' },
    { name: 'HIGH', value: 3, color: '#ef4444' },
  ];

  const languageStats = [
    { language: 'English', count: 1240, fill: '#6366f1' },
    { language: 'Hinglish', count: 860, fill: '#8b5cf6' },
    { language: 'Hindi', count: 420, fill: '#a78bfa' },
  ];

  const timelineData = [
    { time: '00:00', safe: 45, flagged: 3, blocked: 1 },
    { time: '04:00', safe: 22, flagged: 1, blocked: 0 },
    { time: '08:00', safe: 78, flagged: 8, blocked: 2 },
    { time: '12:00', safe: 95, flagged: 12, blocked: 4 },
    { time: '16:00', safe: 110, flagged: 15, blocked: 5 },
    { time: '20:00', safe: 88, flagged: 9, blocked: 3 },
    { time: '23:59', safe: 52, flagged: 4, blocked: 1 },
  ];

  const recentActions = [
    { text: 'tu bewakoof hai kya...', severity: 'HIGH', lang: 'Hinglish', action: 'BLOCKED', time: '2m ago' },
    { text: 'shut up nobody cares', severity: 'MEDIUM', lang: 'English', action: 'FLAGGED', time: '5m ago' },
    { text: 'idhar aa tujhe dikhata hu', severity: 'MEDIUM', lang: 'Hinglish', action: 'REWRITTEN', time: '8m ago' },
    { text: 'Great work on the project!', severity: 'SAFE', lang: 'English', action: 'DELIVERED', time: '10m ago' },
    { text: 'kya bakwaas hai yeh', severity: 'MEDIUM', lang: 'Hinglish', action: 'REWRITTEN', time: '12m ago' },
  ];

  const actionColors: Record<string, string> = {
    BLOCKED: 'text-rose-600 bg-rose-50 border-rose-200',
    FLAGGED: 'text-amber-600 bg-amber-50 border-amber-200',
    REWRITTEN: 'text-indigo-600 bg-indigo-50 border-indigo-200',
    DELIVERED: 'text-emerald-600 bg-emerald-50 border-emerald-200',
  };

  const StatusIcon = ({ ok }: { ok: boolean }) =>
    ok ? <CheckCircle className="w-4 h-4 text-emerald-500" /> : <AlertTriangle className="w-4 h-4 text-amber-500" />;

  return (
    <div className="flex-1 h-full overflow-y-auto bg-slate-50/50 p-5 md:p-6">
      <div className="max-w-6xl mx-auto space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-extrabold text-slate-800 flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-indigo-600" />
              Admin Dashboard
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Infrastructure telemetry, model benchmarks & moderation analytics
            </p>
          </div>
          <button
            onClick={fetchHealth}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-2 bg-white border border-slate-200 hover:bg-slate-50 rounded-xl text-xs font-semibold text-slate-600 shadow-card transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-indigo-600' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="stat-card">
            <div className="flex items-center justify-between mb-3">
              <div className="w-9 h-9 rounded-xl bg-indigo-50 flex items-center justify-center">
                <MessageSquare className="w-5 h-5 text-indigo-500" />
              </div>
              <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded-md flex items-center gap-0.5">
                <TrendingUp className="w-2.5 h-2.5" /> +12%
              </span>
            </div>
            <p className="text-2xl font-extrabold text-slate-800">2,520</p>
            <p className="text-[11px] text-slate-400 mt-0.5">Total Messages</p>
          </div>

          <div className="stat-card">
            <div className="flex items-center justify-between mb-3">
              <div className="w-9 h-9 rounded-xl bg-rose-50 flex items-center justify-center">
                <Shield className="w-5 h-5 text-rose-500" />
              </div>
              <span className="text-[10px] font-bold text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded-md">9.1%</span>
            </div>
            <p className="text-2xl font-extrabold text-slate-800">229</p>
            <p className="text-[11px] text-slate-400 mt-0.5">Toxic Detected</p>
          </div>

          <div className="stat-card">
            <div className="flex items-center justify-between mb-3">
              <div className="w-9 h-9 rounded-xl bg-purple-50 flex items-center justify-center">
                <Globe className="w-5 h-5 text-purple-500" />
              </div>
              <span className="text-[10px] font-bold text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded-md">Polyglot</span>
            </div>
            <p className="text-2xl font-extrabold text-slate-800">3</p>
            <p className="text-[11px] text-slate-400 mt-0.5">Languages Active</p>
          </div>

          <div className="stat-card">
            <div className="flex items-center justify-between mb-3">
              <div className="w-9 h-9 rounded-xl bg-emerald-50 flex items-center justify-center">
                <Zap className="w-5 h-5 text-emerald-500" />
              </div>
              <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded-md flex items-center gap-0.5">
                <Clock className="w-2.5 h-2.5" /> Fast
              </span>
            </div>
            <p className="text-2xl font-extrabold text-slate-800">42ms</p>
            <p className="text-[11px] text-slate-400 mt-0.5">Avg Inference</p>
          </div>
        </div>

        {/* Infrastructure Status */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { name: 'PostgreSQL', key: 'postgresql', sub: 'Users & Channels', icon: Server, fallback: 'Standby' },
            { name: 'Redis', key: 'redis', sub: 'Rate Limiting', icon: Activity, fallback: 'In-Memory Mode' },
            { name: 'MongoDB', key: 'mongodb', sub: 'Chat & Feedback', icon: Layers, fallback: 'Local Memory' },
            { name: 'ML Engine', key: null, sub: 'Hing-RoBERTa + Gemini', icon: Brain, fallback: null },
          ].map((svc) => {
            const isOk = svc.key ? healthData?.engines?.[svc.key] === 'ok' : true;
            return (
              <div key={svc.name} className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-card">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{svc.name}</span>
                  <svc.icon className="w-4 h-4 text-slate-300" />
                </div>
                <div className="text-sm font-semibold text-slate-800 flex items-center gap-1.5">
                  <StatusIcon ok={isOk} />
                  {isOk ? 'Connected' : (svc.fallback || 'Offline')}
                </div>
                <p className="text-[10px] text-slate-400 mt-1">{svc.sub}</p>
              </div>
            );
          })}
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Severity Distribution */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-card">
            <h3 className="text-sm font-bold text-slate-800 mb-1 flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-indigo-500" />
              Severity Distribution
            </h3>
            <p className="text-[11px] text-slate-400 mb-4">Across all evaluated messages</p>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={severityDistribution}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={48}
                    outerRadius={78}
                    strokeWidth={2}
                    stroke="#fff"
                    label={({ name, value }) => `${name} ${value}%`}
                  >
                    {severityDistribution.map((entry, i) => (
                      <Cell key={`cell-${i}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Language Breakdown */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-card">
            <h3 className="text-sm font-bold text-slate-800 mb-1 flex items-center gap-2">
              <Globe className="w-4 h-4 text-indigo-500" />
              Language Breakdown
            </h3>
            <p className="text-[11px] text-slate-400 mb-4">Script-detected multilingual distribution</p>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={languageStats} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="language" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                    {languageStats.map((entry, i) => (
                      <Cell key={`bar-${i}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Moderation Timeline */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-card">
          <h3 className="text-sm font-bold text-slate-800 mb-1 flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-500" />
            24h Moderation Timeline
          </h3>
          <p className="text-[11px] text-slate-400 mb-4">Message volume by safety outcome over time</p>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timelineData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="time" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Area type="monotone" dataKey="safe" stackId="1" stroke="#10b981" fill="#10b981" fillOpacity={0.15} />
                <Area type="monotone" dataKey="flagged" stackId="1" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.3} />
                <Area type="monotone" dataKey="blocked" stackId="1" stroke="#ef4444" fill="#ef4444" fillOpacity={0.3} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recent Moderation Actions */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-card">
          <h3 className="text-sm font-bold text-slate-800 mb-4 flex items-center gap-2">
            <Shield className="w-4 h-4 text-indigo-500" />
            Recent Moderation Actions
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="text-left py-2.5 px-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Message</th>
                  <th className="text-center py-2.5 px-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Severity</th>
                  <th className="text-center py-2.5 px-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Language</th>
                  <th className="text-center py-2.5 px-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Action</th>
                  <th className="text-right py-2.5 px-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Time</th>
                </tr>
              </thead>
              <tbody>
                {recentActions.map((a, i) => (
                  <tr key={i} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                    <td className="py-2.5 px-3 text-xs text-slate-700 font-mono truncate max-w-[200px]">{a.text}</td>
                    <td className="py-2.5 px-3 text-center">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                        a.severity === 'HIGH' ? 'text-rose-700 bg-rose-50 border-rose-200' :
                        a.severity === 'MEDIUM' ? 'text-amber-700 bg-amber-50 border-amber-200' :
                        'text-emerald-700 bg-emerald-50 border-emerald-200'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          a.severity === 'HIGH' ? 'bg-rose-500' :
                          a.severity === 'MEDIUM' ? 'bg-amber-500' : 'bg-emerald-500'
                        }`} />
                        {a.severity}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-center text-[11px] text-slate-500">{a.lang}</td>
                    <td className="py-2.5 px-3 text-center">
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${actionColors[a.action] || ''}`}>
                        {a.action}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right text-[11px] text-slate-400">{a.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Architecture Card */}
        <div className="bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white p-6 rounded-2xl shadow-lg">
          <h3 className="text-xs font-bold uppercase tracking-[0.15em] text-indigo-300 mb-4">
            Production Architecture
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 text-[13px]">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <Brain className="w-4 h-4 text-indigo-400" />
                <span className="font-bold text-white">Toxicity Classifier</span>
              </div>
              <p className="text-slate-400 text-xs leading-relaxed">
                Fine-Tuned Hing-RoBERTa with LoRA (r=32) on 37K multi-label real dataset.
                WeightedFocalLoss with per-class PR-curve threshold optimization.
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <Zap className="w-4 h-4 text-emerald-400" />
                <span className="font-bold text-white">Detoxification</span>
              </div>
              <p className="text-slate-400 text-xs leading-relaxed">
                Gemini 2.5 Flash API for intent-preserving style transfer with async streaming.
                Multilingual regex scrubber fallback with LRU+TTL cache.
              </p>
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <Layers className="w-4 h-4 text-purple-400" />
                <span className="font-bold text-white">Infrastructure</span>
              </div>
              <p className="text-slate-400 text-xs leading-relaxed">
                FastAPI async gateway + WebSocket real-time pipeline.
                PostgreSQL, Redis, MongoDB polyglot persistence with offline fallbacks.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
