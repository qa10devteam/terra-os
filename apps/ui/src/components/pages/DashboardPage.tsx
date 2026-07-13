'use client';
import { useEffect, useState, useCallback } from 'react';
import { useAuthFetch } from '@/lib/api-v2';
import type { Tender } from '@/types';
import { useStore } from '@/store/useStore';
import { GlassCard } from '@/components/ui/GlassCard';
import { showToast } from '@/components/Toast';
import { motion, AnimatePresence } from 'motion/react';
import { Activity, TrendingUp, Target, Zap, Bell, ArrowRight, RefreshCw, BarChart3, Search, Package } from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface DashboardKPI {
  active_tenders: number;
  pipeline_value: number;
  win_rate_mtd: number;
  avg_deal_size: number;
  new_today: number;
}

interface DashboardTender {
  id: string;
  title: string;
  buyer: string;
  deadline: string;
  match_score: number;
  value: number;
}

interface AuditEntry {
  id: string;
  action_type: 'create' | 'update' | 'delete' | 'login';
  user_email: string;
  action: string;
  created_at: string;
}

interface DigestData {
  content: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function formatPLN(value: number): string {
  return value.toLocaleString('pl-PL', { style: 'currency', currency: 'PLN', maximumFractionDigits: 0 });
}

function formatPLNMillions(value: number): string {
  const millions = value / 1_000_000;
  return millions.toLocaleString('pl-PL', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' M PLN';
}

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max) + '…';
}

function daysUntil(dateStr: string): number {
  const now = new Date();
  const target = new Date(dateStr);
  const diff = target.getTime() - now.getTime();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

function deadlineBadgeColor(days: number): string {
  if (days < 7) return 'bg-red-500/20 text-red-400 border-red-500/30';
  if (days < 14) return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
  return 'bg-green-500/20 text-green-400 border-green-500/30';
}

function relativeTime(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffH = Math.floor(diffMin / 60);
  const diffD = Math.floor(diffH / 24);

  if (diffMin < 1) return 'teraz';
  if (diffMin < 60) return `${diffMin}m temu`;
  if (diffH < 24) return `${diffH}h temu`;
  if (diffD === 1) return 'wczoraj';
  if (diffD < 7) return `${diffD}d temu`;
  return date.toLocaleDateString('pl-PL');
}

function renderSimpleMarkdown(content: string): React.ReactNode[] {
  const lines = content.split('\n');
  return lines.map((line, i) => {
    if (line.startsWith('## ')) {
      return (
        <h2 key={i} className="text-lg font-semibold text-earth-100 mt-4 mb-2">
          {line.slice(3)}
        </h2>
      );
    }
    if (line.startsWith('# ')) {
      return (
        <h1 key={i} className="text-xl font-bold text-earth-100 mt-4 mb-2">
          {line.slice(2)}
        </h1>
      );
    }
    // Handle **bold**
    const parts = line.split(/\*\*(.*?)\*\*/g);
    const rendered = parts.map((part, j) =>
      j % 2 === 1 ? (
        <strong key={j} className="font-semibold text-earth-100">{part}</strong>
      ) : (
        <span key={j}>{part}</span>
      )
    );
    return (
      <p key={i} className="text-earth-300 text-sm leading-relaxed">
        {rendered}
      </p>
    );
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Animated Counter Hook
// ─────────────────────────────────────────────────────────────────────────────

function useAnimatedCounter(target: number, duration: number = 1200): number {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    if (target === 0) {
      setCurrent(0);
      return;
    }
    const startTime = Date.now();
    const startValue = 0;

    const tick = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = Math.round(startValue + (target - startValue) * eased);
      setCurrent(value);
      if (progress < 1) {
        requestAnimationFrame(tick);
      }
    };

    requestAnimationFrame(tick);
  }, [target, duration]);

  return current;
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI Card Component
// ─────────────────────────────────────────────────────────────────────────────

interface KPICardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  rawValue: number;
  trend?: number;
  delay: number;
  color: string;
}

function KPICard({ icon, label, value, trend, delay, color }: KPICardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: delay * 0.1 }}
    >
      <GlassCard className="p-5 hover:border-[#3B82F6]/30 transition-all duration-300">
        <div className="flex items-start justify-between">
          <div className={`p-2.5 rounded-xl ${color}`}>
            {icon}
          </div>
          {trend !== undefined && (
            <div className={`flex items-center gap-1 text-xs font-medium ${
              trend >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              <svg
                width="12"
                height="12"
                viewBox="0 0 12 12"
                fill="none"
                className={trend < 0 ? 'rotate-180' : ''}
              >
                <path
                  d="M6 2L10 7H2L6 2Z"
                  fill="currentColor"
                />
              </svg>
              <span>{Math.abs(trend)}%</span>
            </div>
          )}
        </div>
        <div className="mt-4">
          <p className="text-2xl font-bold text-earth-100 tracking-tight">
            {value}
          </p>
          <p className="text-sm text-earth-400 mt-1">{label}</p>
        </div>
      </GlassCard>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Tender Card Component
// ─────────────────────────────────────────────────────────────────────────────

interface TenderCardProps {
  tender: DashboardTender;
  index: number;
  onClick: () => void;
}

function TenderCard({ tender, index, onClick }: TenderCardProps) {
  const days = daysUntil(tender.deadline);
  const badgeColor = deadlineBadgeColor(days);

  return (
    <motion.div
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08 }}
      onClick={onClick}
      className="group p-4 rounded-xl bg-earth-900/40 border border-earth-800/50 hover:border-[#3B82F6]/40 cursor-pointer transition-all duration-300 hover:bg-earth-900/60"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-earth-100 group-hover:text-[#3B82F6] transition-colors truncate">
            {truncate(tender.title, 60)}
          </h4>
          <p className="text-xs text-earth-400 mt-1">{tender.buyer}</p>
        </div>
        <span className={`shrink-0 px-2 py-0.5 text-xs font-medium rounded-full border ${badgeColor}`}>
          {days}d
        </span>
      </div>

      {/* Match score bar */}
      <div className="mt-3">
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span className="text-earth-400">Dopasowanie</span>
          <span className="text-earth-200 font-medium">{tender.match_score}%</span>
        </div>
        <div className="h-1.5 bg-earth-800 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${tender.match_score}%` }}
            transition={{ duration: 0.8, delay: index * 0.1 + 0.3 }}
            className="h-full rounded-full"
            style={{
              background: `linear-gradient(90deg, #3B82F6, ${
                tender.match_score > 80 ? '#10B981' : tender.match_score > 60 ? '#F59E0B' : '#EF4444'
              })`,
            }}
          />
        </div>
      </div>

      {/* Value */}
      <div className="mt-2 flex items-center justify-between">
        <span className="text-xs text-earth-300">
          {formatPLN(tender.value)}
        </span>
        <ArrowRight className="w-3.5 h-3.5 text-earth-500 group-hover:text-[#3B82F6] transition-colors" />
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Activity Feed Item
// ─────────────────────────────────────────────────────────────────────────────

function ActivityIcon({ type }: { type: string }) {
  const baseClass = 'w-3.5 h-3.5';
  switch (type) {
    case 'create':
      return (
        <svg className={baseClass} viewBox="0 0 16 16" fill="none">
          <path d="M8 3v10M3 8h10" stroke="#10B981" strokeWidth="2" strokeLinecap="round" />
        </svg>
      );
    case 'update':
      return (
        <svg className={baseClass} viewBox="0 0 16 16" fill="none">
          <path d="M11.5 1.5l3 3-9 9H2.5v-3l9-9z" stroke="#F59E0B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case 'delete':
      return (
        <svg className={baseClass} viewBox="0 0 16 16" fill="none">
          <path d="M2 4h12M5.33 4V2.67a1.33 1.33 0 011.34-1.34h2.66a1.33 1.33 0 011.34 1.34V4m2 0v9.33a1.33 1.33 0 01-1.34 1.34H4.67a1.33 1.33 0 01-1.34-1.34V4" stroke="#EF4444" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case 'login':
      return (
        <svg className={baseClass} viewBox="0 0 16 16" fill="none">
          <path d="M10 2h2.67A1.33 1.33 0 0114 3.33v9.34A1.33 1.33 0 0112.67 14H10M6.67 11.33L10 8 6.67 4.67M10 8H2" stroke="#3B82F6" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    default:
      return <Activity className={`${baseClass} text-earth-400`} />;
  }
}

interface ActivityItemProps {
  entry: AuditEntry;
  index: number;
  isLast: boolean;
}

function ActivityItem({ entry, index, isLast }: ActivityItemProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className="flex gap-3 relative"
    >
      {/* Timeline */}
      <div className="flex flex-col items-center">
        <div className="w-7 h-7 rounded-full bg-earth-800/80 border border-earth-700 flex items-center justify-center shrink-0">
          <ActivityIcon type={entry.action_type} />
        </div>
        {!isLast && (
          <div className="w-px flex-1 bg-earth-800 mt-1" />
        )}
      </div>

      {/* Content */}
      <div className="pb-4 flex-1 min-w-0">
        <p className="text-xs text-earth-200 leading-relaxed">
          <span className="font-medium text-earth-100">
            {entry.user_email.split('@')[0]}
          </span>
          {' '}
          <span className="text-earth-400">{entry.action}</span>
        </p>
        <p className="text-[11px] text-earth-500 mt-0.5">
          {relativeTime(entry.created_at)}
        </p>
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Quick Action Card
// ─────────────────────────────────────────────────────────────────────────────

interface QuickActionProps {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  delay: number;
}

function QuickActionCard({ icon, label, onClick, delay }: QuickActionProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, delay }}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      className="group relative cursor-pointer"
    >
      {/* Gradient border on hover */}
      <div className="absolute -inset-[1px] rounded-xl bg-gradient-to-br from-[#3B82F6]/0 via-[#3B82F6]/0 to-[#3B82F6]/0 group-hover:from-[#3B82F6]/50 group-hover:via-[#3B82F6]/20 group-hover:to-[#3B82F6]/50 transition-all duration-500 rounded-xl" />
      <div className="relative p-6 rounded-xl bg-earth-900/60 border border-earth-800 group-hover:border-transparent transition-all duration-300">
        <div className="flex flex-col items-center gap-3">
          <div className="p-3 rounded-xl bg-earth-800/60 group-hover:bg-[#3B82F6]/10 transition-colors duration-300">
            {icon}
          </div>
          <span className="text-sm font-medium text-earth-200 group-hover:text-earth-100 transition-colors">
            {label}
          </span>
        </div>
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Sparkline SVG Component
// ─────────────────────────────────────────────────────────────────────────────

function SparklineSVG({ data, color }: { data: number[]; color: string }) {
  if (data.length < 2) return null;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 80;
  const h = 28;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x},${y}`;
  });
  const pathD = `M${points.join(' L')}`;

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="opacity-60">
      <path d={pathD} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Loading Skeleton
// ─────────────────────────────────────────────────────────────────────────────

function KPISkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="p-5 rounded-xl bg-earth-900/60 border border-earth-800 animate-pulse">
          <div className="w-10 h-10 rounded-xl bg-earth-800" />
          <div className="mt-4 h-7 w-20 bg-earth-800 rounded" />
          <div className="mt-2 h-4 w-24 bg-earth-800/60 rounded" />
        </div>
      ))}
    </div>
  );
}

function TenderSkeleton() {
  return (
    <div className="space-y-3">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="p-4 rounded-xl bg-earth-900/40 border border-earth-800/50 animate-pulse">
          <div className="h-4 w-3/4 bg-earth-800 rounded" />
          <div className="mt-2 h-3 w-1/2 bg-earth-800/60 rounded" />
          <div className="mt-3 h-1.5 w-full bg-earth-800 rounded-full" />
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Dashboard Component
// ─────────────────────────────────────────────────────────────────────────────

export function DashboardPage() {
  const authFetch = useAuthFetch();
  const { setCurrentModule, setSelectedTender } = useStore();

  // ── State ──────────────────────────────────────────────────────────────────
  const [kpi, setKpi] = useState<DashboardKPI | null>(null);
  const [tenders, setTenders] = useState<DashboardTender[]>([]);
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([]);
  const [auditError, setAuditError] = useState(false);
  const [digest, setDigest] = useState<string | null>(null);
  const [digestError, setDigestError] = useState(false);
  const [digestLoading, setDigestLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshingAudit, setRefreshingAudit] = useState(false);

  // Animated counters
  const animActiveTenders = useAnimatedCounter(kpi?.active_tenders ?? 0);
  const animPipelineValue = useAnimatedCounter(kpi?.pipeline_value ? Math.round(kpi.pipeline_value / 1_000_000 * 10) : 0);
  const animWinRate = useAnimatedCounter(kpi?.win_rate_mtd ?? 0);
  const animAvgDeal = useAnimatedCounter(kpi?.avg_deal_size ?? 0);
  const animNewToday = useAnimatedCounter(kpi?.new_today ?? 0);

  // ── Data Fetching ──────────────────────────────────────────────────────────

  const fetchDashboard = useCallback(async () => {
    try {
      const data = await authFetch('/api/v2/dashboard') as DashboardKPI;
      setKpi(data);
    } catch (err) {
      console.error('Dashboard KPI fetch failed:', err);
      showToast('error', 'Nie udało się pobrać KPI');
    }
  }, [authFetch]);

  const fetchTenders = useCallback(async () => {
    try {
      const data = await authFetch('/api/v2/tenders?sort=match_score&limit=5&deadline_days=14') as DashboardTender[];
      setTenders(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Tenders fetch failed:', err);
    }
  }, [authFetch]);

  const fetchAuditLog = useCallback(async () => {
    try {
      setRefreshingAudit(true);
      const data = await authFetch('/api/v2/audit/recent?limit=15') as AuditEntry[];
      setAuditLog(Array.isArray(data) ? data : []);
      setAuditError(false);
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 404) {
        setAuditError(true);
      } else {
        console.error('Audit fetch failed:', err);
        setAuditError(true);
      }
    } finally {
      setRefreshingAudit(false);
    }
  }, [authFetch]);

  const fetchDigest = useCallback(async () => {
    try {
      const data = await authFetch('/api/v2/dashboard/digest') as DigestData;
      if (data && data.content) {
        setDigest(data.content);
        setDigestError(false);
      } else {
        setDigestError(true);
      }
    } catch {
      setDigestError(true);
    }
  }, [authFetch]);

  const generateDigest = useCallback(async () => {
    setDigestLoading(true);
    try {
      await authFetch('/api/v2/dashboard/digest/generate', {
        method: 'POST',
      });
      showToast('success', 'Digest generowany...');
      // Re-fetch after a short delay
      setTimeout(() => {
        fetchDigest();
        setDigestLoading(false);
      }, 2000);
    } catch {
      showToast('error', 'Nie udało się wygenerować digestu');
      setDigestLoading(false);
    }
  }, [authFetch, fetchDigest]);

  // ── Initial Load ───────────────────────────────────────────────────────────

  useEffect(() => {
    async function loadAll() {
      setLoading(true);
      await Promise.all([
        fetchDashboard(),
        fetchTenders(),
        fetchAuditLog(),
        fetchDigest(),
      ]);
      setLoading(false);
    }
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Auto-refresh audit every 60s ──────────────────────────────────────────

  useEffect(() => {
    const interval = setInterval(() => {
      fetchAuditLog();
    }, 60_000);
    return () => clearInterval(interval);
  }, [fetchAuditLog]);

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-earth-950 p-6 lg:p-8 space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-earth-100">
            Centrum Dowodzenia
          </h1>
          <p className="text-sm text-earth-400 mt-1">
            Przegląd aktywności i inteligencji rynkowej
          </p>
        </div>
        <button
          onClick={() => {
            fetchDashboard();
            fetchTenders();
            fetchAuditLog();
            fetchDigest();
            showToast('info', 'Odświeżam dane...');
          }}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-earth-900/60 border border-earth-800 text-earth-300 hover:text-earth-100 hover:border-[#3B82F6]/40 transition-all duration-300"
        >
          <RefreshCw className="w-4 h-4" />
          <span className="text-sm">Odśwież</span>
        </button>
      </motion.div>

      {/* ═══════════════════════════════════════════════════════════════════════
          ROW 1 — KPI Cards
          ═══════════════════════════════════════════════════════════════════════ */}

      {loading ? (
        <KPISkeleton />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <KPICard
            icon={<Activity className="w-5 h-5 text-[#3B82F6]" />}
            label="Aktywne przetargi"
            value={animActiveTenders.toLocaleString('pl-PL')}
            rawValue={kpi?.active_tenders ?? 0}
            trend={12}
            delay={0}
            color="bg-[#3B82F6]/10"
          />
          <KPICard
            icon={<TrendingUp className="w-5 h-5 text-emerald-400" />}
            label="Pipeline"
            value={`${(animPipelineValue / 10).toLocaleString('pl-PL', { minimumFractionDigits: 1 })} M PLN`}
            rawValue={kpi?.pipeline_value ?? 0}
            trend={8}
            delay={1}
            color="bg-emerald-500/10"
          />
          <KPICard
            icon={<Target className="w-5 h-5 text-violet-400" />}
            label="Win Rate MTD"
            value={`${animWinRate}%`}
            rawValue={kpi?.win_rate_mtd ?? 0}
            trend={kpi?.win_rate_mtd ? (kpi.win_rate_mtd > 50 ? 5 : -3) : 0}
            delay={2}
            color="bg-violet-500/10"
          />
          <KPICard
            icon={<Zap className="w-5 h-5 text-amber-400" />}
            label="Śr. wartość oferty"
            value={formatPLN(animAvgDeal)}
            rawValue={kpi?.avg_deal_size ?? 0}
            trend={3}
            delay={3}
            color="bg-amber-500/10"
          />
          <KPICard
            icon={<Bell className="w-5 h-5 text-rose-400" />}
            label="Nowe dziś"
            value={animNewToday.toLocaleString('pl-PL')}
            rawValue={kpi?.new_today ?? 0}
            trend={undefined}
            delay={4}
            color="bg-rose-500/10"
          />
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════
          ROW 2 — Tenders + Activity Feed (60/40)
          ═══════════════════════════════════════════════════════════════════════ */}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left Column — Hot Tenders (3/5 = 60%) */}
        <div className="lg:col-span-3">
          <GlassCard className="p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-[#3B82F6] animate-pulse" />
                <h2 className="text-lg font-semibold text-earth-100">
                  Najgorętsze dziś
                </h2>
              </div>
              <button
                onClick={() => setCurrentModule('zwiad')}
                className="text-xs text-earth-400 hover:text-[#3B82F6] transition-colors flex items-center gap-1"
              >
                Wszystkie <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            {loading ? (
              <TenderSkeleton />
            ) : tenders.length === 0 ? (
              <div className="text-center py-12 text-earth-400">
                <Target className="w-10 h-10 mx-auto mb-3 opacity-40" />
                <p className="text-sm">Brak gorących przetargów</p>
              </div>
            ) : (
              <div className="space-y-3">
                {tenders.map((tender, i) => (
                  <TenderCard
                    key={tender.id}
                    tender={tender}
                    index={i}
                    onClick={() => {
                      setSelectedTender(tender as unknown as Tender);
                      setCurrentModule('decyzja');
                    }}
                  />
                ))}
              </div>
            )}
          </GlassCard>
        </div>

        {/* Right Column — Activity Feed (2/5 = 40%) */}
        <div className="lg:col-span-2">
          <GlassCard className="p-6 h-full">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-earth-100">
                Aktywność
              </h2>
              <div className="flex items-center gap-2">
                {refreshingAudit && (
                  <RefreshCw className="w-3.5 h-3.5 text-earth-500 animate-spin" />
                )}
                <span className="text-[11px] text-earth-500">auto 60s</span>
              </div>
            </div>

            {auditError ? (
              <div className="flex flex-col items-center justify-center py-12 text-earth-400">
                <Activity className="w-10 h-10 mb-3 opacity-30" />
                <p className="text-sm">Feed aktywności niedostępny</p>
                <p className="text-xs text-earth-500 mt-1">Dane pojawią się wkrótce</p>
              </div>
            ) : auditLog.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-earth-400">
                <Activity className="w-10 h-10 mb-3 opacity-30" />
                <p className="text-sm">Brak ostatniej aktywności</p>
              </div>
            ) : (
              <div className="max-h-[420px] overflow-y-auto pr-2 scrollbar-thin scrollbar-track-earth-900 scrollbar-thumb-earth-700">
                <AnimatePresence mode="popLayout">
                  {auditLog.map((entry, i) => (
                    <ActivityItem
                      key={entry.id}
                      entry={entry}
                      index={i}
                      isLast={i === auditLog.length - 1}
                    />
                  ))}
                </AnimatePresence>
              </div>
            )}
          </GlassCard>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          ROW 3 — Quick Actions
          ═══════════════════════════════════════════════════════════════════════ */}

      <div>
        <motion.h2
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="text-lg font-semibold text-earth-100 mb-4"
        >
          Szybkie akcje
        </motion.h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <QuickActionCard
            icon={<Bell className="w-6 h-6 text-[#3B82F6] group-hover:text-[#60A5FA] transition-colors" />}
            label="Nowy Alert"
            onClick={() => setCurrentModule('notifications')}
            delay={0.7}
          />
          <QuickActionCard
            icon={<BarChart3 className="w-6 h-6 text-emerald-400 group-hover:text-emerald-300 transition-colors" />}
            label="Pipeline"
            onClick={() => setCurrentModule('pipeline')}
            delay={0.8}
          />
          <QuickActionCard
            icon={<Search className="w-6 h-6 text-violet-400 group-hover:text-violet-300 transition-colors" />}
            label="Zwiad AI"
            onClick={() => setCurrentModule('zwiad')}
            delay={0.9}
          />
          <QuickActionCard
            icon={<Package className="w-6 h-6 text-amber-400 group-hover:text-amber-300 transition-colors" />}
            label="InterCenBud"
            onClick={() => setCurrentModule('icb')}
            delay={1.0}
          />
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          ROW 4 — AI Digest
          ═══════════════════════════════════════════════════════════════════════ */}

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 1.0 }}
      >
        <GlassCard className="p-6">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-gradient-to-br from-[#3B82F6]/20 to-violet-500/20">
                <Zap className="w-5 h-5 text-[#3B82F6]" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-earth-100">
                  AI Digest
                </h2>
                <p className="text-xs text-earth-400">
                  Podsumowanie inteligencji rynkowej
                </p>
              </div>
            </div>
            <button
              onClick={generateDigest}
              disabled={digestLoading}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#3B82F6]/10 border border-[#3B82F6]/30 text-[#3B82F6] hover:bg-[#3B82F6]/20 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${digestLoading ? 'animate-spin' : ''}`} />
              <span className="text-xs font-medium">Odśwież</span>
            </button>
          </div>

          {digestLoading ? (
            <div className="space-y-3 animate-pulse">
              <div className="h-4 w-3/4 bg-earth-800 rounded" />
              <div className="h-4 w-full bg-earth-800/60 rounded" />
              <div className="h-4 w-5/6 bg-earth-800/40 rounded" />
              <div className="h-4 w-2/3 bg-earth-800/30 rounded" />
            </div>
          ) : digestError || !digest ? (
            <div className="flex flex-col items-center justify-center py-10 text-earth-400">
              <div className="p-4 rounded-full bg-earth-800/40 mb-4">
                <Zap className="w-8 h-8 opacity-40" />
              </div>
              <p className="text-sm font-medium text-earth-300">
                Digest wygeneruje się dziś o 8:00
              </p>
              <p className="text-xs text-earth-500 mt-1">
                Kliknij &quot;Odśwież&quot; aby wygenerować teraz
              </p>
            </div>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none">
              {renderSimpleMarkdown(digest)}
            </div>
          )}
        </GlassCard>
      </motion.div>

      {/* ═══════════════════════════════════════════════════════════════════════
          Footer Spacer
          ═══════════════════════════════════════════════════════════════════════ */}
      <div className="h-8" />
    </div>
  );
}
