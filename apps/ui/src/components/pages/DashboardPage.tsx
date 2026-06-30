'use client';

import { motion } from 'motion/react';
import { useStore } from '@/store/useStore';
import { useDashboardStats, useTenders } from '@/lib/api';
import {
  TrendingUp,
  FileText,
  AlertTriangle,
  Target,
  Zap,
  ArrowRight,
  Clock,
  Radar,
  Calculator,
  Brain,
  BarChart3,
} from 'lucide-react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';

// ── Spark data ────────────────────────────────────────────────────────────────
const sparkData = [
  { v: 3 }, { v: 5 }, { v: 4 }, { v: 7 }, { v: 6 }, { v: 8 }, { v: 9 },
];

// ── Animation variants ────────────────────────────────────────────────────────
const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.07 } },
};
const item = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.38, ease: [0, 0, 0.2, 1] as const } },
};

// ── Pipeline stages config ────────────────────────────────────────────────────
const pipelineStages = [
  { key: 'new',          label: 'Nowy',       color: '#3B82F6' },
  { key: 'matched',      label: 'Dopasowany', color: '#8B5CF6' },
  { key: 'analyzing',    label: 'Analiza',    color: '#F59E0B' },
  { key: 'estimated',    label: 'Wyceniony',  color: '#10b981' },
  { key: 'decided_go',   label: 'GO',         color: '#22C55E' },
  { key: 'decided_nogo', label: 'NO-GO',      color: '#EF4444' },
];

// ── Status badge config ───────────────────────────────────────────────────────
const STATUS_COLORS: Record<string, string> = {
  new:          'bg-accent-info/15 text-accent-info',
  matched:      'bg-accent-violet/15 text-accent-violet',
  analyzing:    'bg-accent-warning/15 text-accent-warning',
  estimated:    'bg-accent-primary/15 text-accent-primary',
  decided_go:   'bg-accent-primary/20 text-accent-primary',
  decided_nogo: 'bg-accent-danger/15 text-accent-danger',
  archived:     'bg-earth-700/40 text-earth-500',
};
const STATUS_LABELS: Record<string, string> = {
  new: 'Nowy', matched: 'Dopasowany', analyzing: 'Analiza',
  estimated: 'Wyceniony', decided_go: 'GO ✓', decided_nogo: 'NO-GO',
  archived: 'Archiwum',
};

function fmtPLN(v: number | null | undefined) {
  if (v === null || v === undefined) return '—';
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + ' M';
  if (v >= 1_000) return (v / 1_000).toFixed(0) + ' k';
  return v.toFixed(0);
}

function fmtDate(s: string | null | undefined) {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

// ── Skeleton cards ────────────────────────────────────────────────────────────
function SkeletonStatCard() {
  return (
    <div className="glass-card p-5 animate-pulse">
      <div className="flex items-center justify-between mb-4">
        <div className="h-3 bg-earth-700 rounded w-24" />
        <div className="w-4 h-4 bg-earth-700 rounded" />
      </div>
      <div className="flex items-end justify-between gap-4">
        <div className="h-8 bg-earth-700 rounded w-16" />
        <div className="w-16 h-8 bg-earth-800 rounded" />
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export function DashboardPage() {
  const { setCurrentModule, setSelectedTender } = useStore();
  const { data: stats, isLoading } = useDashboardStats();
  const { data: tenders } = useTenders();

  const pipelineCounts = stats?.pipelineCounts || {};
  const totalPipeline = Object.values(pipelineCounts).reduce((s, v) => s + v, 0) || 1;

  const statCards = [
    {
      label: 'Aktywne przetargi',
      value: stats?.activeTenders ?? 0,
      icon: FileText,
      color: 'text-accent-primary',
      sparkColor: '#10b981',
      trend: '+3 tym tygodniu',
    },
    {
      label: 'Wartość pipeline',
      value: `${fmtPLN(stats?.totalValue ?? 0)} PLN`,
      icon: TrendingUp,
      color: 'text-accent-warning',
      sparkColor: '#F59E0B',
      trend: 'łączna wartość',
    },
    {
      label: 'Średni score',
      value: `${stats?.avgScore ?? 0}%`,
      icon: Target,
      color: 'text-accent-info',
      sparkColor: '#3B82F6',
      trend: 'dopasowanie profilu',
    },
    {
      label: 'Czerwone flagi',
      value: stats?.redFlags ?? 0,
      icon: AlertTriangle,
      color: 'text-accent-danger',
      sparkColor: '#EF4444',
      trend: 'decyzje NO-GO',
    },
  ];

  const quickActions = [
    { label: 'Skanuj BZP',    icon: Radar,      module: 'zwiad'    as const },
    { label: 'Nowy kosztorys', icon: Calculator, module: 'kosztorys' as const },
    { label: 'Analiza ryzyka', icon: Brain,      module: 'silnik'   as const },
  ];

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="p-6 md:p-8 max-w-7xl mx-auto space-y-6"
    >
      {/* ── Header ─────────────────────────────────────────────── */}
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-earth-50 tracking-tight">Dashboard</h1>
          <p className="text-sm text-earth-500 mt-0.5">Podsumowanie aktywności pipeline przetargowego</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-earth-800/60 border border-earth-700/40">
          <BarChart3 className="w-3.5 h-3.5 text-accent-primary" />
          <span className="text-xs text-earth-400">{stats?.activeTenders ?? 0} aktywnych</span>
        </div>
      </motion.div>

      {/* ── Stat Cards ─────────────────────────────────────────── */}
      <motion.div variants={item} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading
          ? Array.from({ length: 4 }).map((_, i) => <SkeletonStatCard key={i} />)
          : statCards.map((stat) => (
            <div key={stat.label} className="glass-card card-hover p-5 group">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-medium text-earth-500 uppercase tracking-wider">
                  {stat.label}
                </span>
                <stat.icon className={`w-4 h-4 ${stat.color} opacity-60 group-hover:opacity-100 transition-opacity`} />
              </div>
              <div className="flex items-end justify-between gap-4">
                <div>
                  <p className="text-2xl font-bold text-earth-50 tabular-nums">{stat.value}</p>
                  <p className="text-xs text-earth-600 mt-0.5">{stat.trend}</p>
                </div>
                <div className="w-16 h-10 shrink-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={sparkData}>
                      <Line
                        type="monotone"
                        dataKey="v"
                        stroke={stat.sparkColor}
                        strokeWidth={1.5}
                        dot={false}
                        strokeOpacity={0.7}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          ))}
      </motion.div>

      {/* ── Pipeline Bar ───────────────────────────────────────── */}
      <motion.div variants={item} className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs font-semibold text-earth-400 uppercase tracking-wider">
            Pipeline przetargów
          </h3>
          <span className="text-xs text-earth-600">{totalPipeline} łącznie</span>
        </div>
        <div className="flex items-stretch h-10 rounded-xl overflow-hidden bg-earth-800/40 gap-px">
          {pipelineStages.map((stage) => {
            const count = pipelineCounts[stage.key] || 0;
            const pct = (count / totalPipeline) * 100;
            if (pct < 1 && count === 0) return null;
            return (
              <div
                key={stage.key}
                className="h-full flex items-center justify-center text-xs font-semibold transition-all duration-700 cursor-default"
                style={{
                  width: `${Math.max(pct, count > 0 ? 6 : 0)}%`,
                  backgroundColor: stage.color + '28',
                  borderTop: `2px solid ${stage.color}`,
                  color: stage.color,
                }}
                title={`${stage.label}: ${count} (${pct.toFixed(0)}%)`}
              >
                {count > 0 && count}
              </div>
            );
          })}
        </div>
        <div className="flex items-center gap-4 mt-3 flex-wrap">
          {pipelineStages.map((stage) => (
            <div key={stage.key} className="flex items-center gap-1.5 text-xs text-earth-500">
              <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: stage.color }} />
              <span>{stage.label}</span>
              <span className="text-earth-700">({pipelineCounts[stage.key] || 0})</span>
            </div>
          ))}
        </div>
      </motion.div>

      {/* ── Bottom grid ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* ── Recent tenders table ─── */}
        <motion.div variants={item} className="lg:col-span-2 glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-semibold text-earth-400 uppercase tracking-wider">
              Ostatnie przetargi
            </h3>
            <Clock className="w-3.5 h-3.5 text-earth-600" />
          </div>
          <div className="overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-earth-800/60">
                  <th className="text-left pb-2 text-xs text-earth-600 font-medium">Przetarg</th>
                  <th className="text-right pb-2 text-xs text-earth-600 font-medium pr-2">Wartość</th>
                  <th className="text-right pb-2 text-xs text-earth-600 font-medium pr-2">Status</th>
                  <th className="text-right pb-2 text-xs text-earth-600 font-medium">Termin</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-earth-800/30">
                {(stats?.recentTenders || []).slice(0, 5).map((t, i) => (
                  <tr
                    key={t.id || i}
                    onClick={() => {
                      setSelectedTender(t as unknown as Parameters<typeof setSelectedTender>[0]);
                      setCurrentModule('zwiad');
                    }}
                    className="group cursor-pointer hover:bg-earth-800/30 transition-colors duration-150"
                  >
                    <td className="py-2.5 pr-3">
                      <p className="text-earth-200 text-xs font-medium line-clamp-1 group-hover:text-earth-100 transition-colors">
                        {t.title}
                      </p>
                      <p className="text-earth-600 text-xs mt-0.5 truncate">{t.buyer}</p>
                    </td>
                    <td className="py-2.5 pr-2 text-right text-earth-400 text-xs whitespace-nowrap">
                      {fmtPLN((t as { value_pln?: number }).value_pln)}
                    </td>
                    <td className="py-2.5 pr-2 text-right">
                      <span className={`inline-block text-xs px-1.5 py-0.5 rounded font-medium ${STATUS_COLORS[t.status] ?? 'bg-earth-700 text-earth-400'}`}>
                        {STATUS_LABELS[t.status] ?? t.status}
                      </span>
                    </td>
                    <td className="py-2.5 text-right text-earth-600 text-xs whitespace-nowrap">
                      {fmtDate((t as { deadline_at?: string }).deadline_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(!stats?.recentTenders || stats.recentTenders.length === 0) && (
              <div className="py-8 text-center text-earth-600 text-sm">
                Brak danych — zeskanuj przetargi w module Zwiad
              </div>
            )}
          </div>
        </motion.div>

        {/* ── Right column ─── */}
        <motion.div variants={item} className="flex flex-col gap-4">

          {/* Quick actions */}
          <div className="glass-card p-5">
            <h3 className="text-xs font-semibold text-earth-400 uppercase tracking-wider mb-3">
              Szybkie akcje
            </h3>
            <div className="space-y-2">
              {quickActions.map((action) => (
                <button
                  key={action.label}
                  onClick={() => setCurrentModule(action.module)}
                  className="w-full flex items-center gap-3 p-2.5 rounded-lg bg-earth-800/30 border border-earth-700/30 hover:border-accent-primary/40 hover:bg-earth-800/60 transition-all duration-200 group"
                >
                  <div className="w-7 h-7 rounded-lg bg-earth-700/50 flex items-center justify-center group-hover:bg-accent-primary/15 transition-colors">
                    <action.icon className="w-3.5 h-3.5 text-earth-400 group-hover:text-accent-primary transition-colors" />
                  </div>
                  <span className="text-sm text-earth-300 group-hover:text-earth-100 transition-colors flex-1 text-left">
                    {action.label}
                  </span>
                  <ArrowRight className="w-3 h-3 text-earth-600 group-hover:text-accent-primary group-hover:translate-x-0.5 transition-all" />
                </button>
              ))}
            </div>
          </div>

          {/* Latest tenders preview */}
          <div className="glass-card p-5 flex-1">
            <h3 className="text-xs font-semibold text-earth-400 uppercase tracking-wider mb-3">
              Top przetargi
            </h3>
            <div className="space-y-2.5">
              {tenders.slice(0, 4).map((t) => (
                <div
                  key={t.id}
                  onClick={() => {
                    setSelectedTender(t as unknown as Parameters<typeof setSelectedTender>[0]);
                    setCurrentModule('zwiad');
                  }}
                  className="flex items-start gap-2 cursor-pointer group"
                >
                  <Zap className="w-3 h-3 mt-0.5 text-accent-primary shrink-0" />
                  <span className="text-xs text-earth-400 line-clamp-2 flex-1 group-hover:text-earth-200 transition-colors">
                    {t.title}
                  </span>
                  <span
                    className="text-xs font-semibold shrink-0 tabular-nums"
                    style={{
                      color: t.match_score > 0.7 ? '#10b981' : t.match_score > 0.4 ? '#F59E0B' : '#EF4444',
                    }}
                  >
                    {Math.round(t.match_score * 100)}%
                  </span>
                </div>
              ))}
              {tenders.length === 0 && (
                <p className="text-xs text-earth-600 text-center py-4">Brak przetargów</p>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}
