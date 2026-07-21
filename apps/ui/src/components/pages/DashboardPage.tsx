'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuthFetch } from '@/lib/api-v2';
import type { Tender } from '@/types';
import { useStore } from '@/store/useStore';
import { GlassCard } from '@/components/ui/GlassCard';
import { MetricCard } from '@/components/ui/MetricCard';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { SkeletonKPI, SkeletonCard, SkeletonTextBlock } from '@/components/ui/SkeletonLoader';
import { PageShell } from '@/components/PageShell';
import { showToast } from '@/components/Toast';
import { motion, AnimatePresence } from 'motion/react';
import {
  Activity,
  TrendingUp,
  Target,
  Zap,
  Bell,
  ArrowRight,
  RefreshCw,
  Search,
} from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface DashboardKPI {
  active_tenders: number;
  pipeline_value: number;
  win_rate_mtd: number;
  avg_deal_size: number;
  new_today: number;
  total_value?: number;
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

function formatPLN(value: number | null | undefined): string {
  return (value ?? 0).toLocaleString('pl-PL', {
    style: 'currency',
    currency: 'PLN',
    maximumFractionDigits: 0,
  });
}

function truncate(text: string, max: number): string {
  return text.length <= max ? text : text.slice(0, max) + '…';
}

function daysUntil(dateStr: string): number {
  const diff = new Date(dateStr).getTime() - Date.now();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

function deadlineBadgeVariant(days: number): 'danger' | 'warning' | 'success' {
  if (days < 7) return 'danger';
  if (days < 14) return 'warning';
  return 'success';
}

function relativeTime(dateStr: string): string {
  const diffMs  = Date.now() - new Date(dateStr).getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const diffH   = Math.floor(diffMin / 60);
  const diffD   = Math.floor(diffH / 24);

  if (diffMin < 1)  return 'teraz';
  if (diffMin < 60) return `${diffMin}m temu`;
  if (diffH < 24)   return `${diffH}h temu`;
  if (diffD === 1)  return 'wczoraj';
  if (diffD < 7)    return `${diffD}d temu`;
  return new Date(dateStr).toLocaleDateString('pl-PL');
}

function renderSimpleMarkdown(content: string): React.ReactNode[] {
  return content.split('\n').map((line, i) => {
    if (line.startsWith('## ')) {
      return (
        <h2 key={i} className="text-lg font-semibold text-slate-100 mt-4 mb-2">
          {line.slice(3)}
        </h2>
      );
    }
    if (line.startsWith('# ')) {
      return (
        <h1 key={i} className="text-xl font-bold text-slate-100 mt-4 mb-2">
          {line.slice(2)}
        </h1>
      );
    }
    const parts = line.split(/\*\*(.*?)\*\*/g);
    const rendered = parts.map((part, j) =>
      j % 2 === 1 ? (
        <strong key={j} className="font-semibold text-slate-100">
          {part}
        </strong>
      ) : (
        <span key={j}>{part}</span>
      ),
    );
    return (
      <p key={i} className="text-slate-300 text-sm leading-relaxed">
        {rendered}
      </p>
    );
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Animated Counter Hook
// ─────────────────────────────────────────────────────────────────────────────

function useAnimatedCounter(target: number, duration = 1200): number {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    if (target === 0) {
      setCurrent(0);
      return;
    }
    const startTime = Date.now();

    const tick = () => {
      const elapsed  = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased    = 1 - Math.pow(1 - progress, 3);
      setCurrent(Math.round(target * eased));
      if (progress < 1) requestAnimationFrame(tick);
    };

    requestAnimationFrame(tick);
  }, [target, duration]);

  return current;
}

// ─────────────────────────────────────────────────────────────────────────────
// TenderCard — najgorętsze przetargi
// ─────────────────────────────────────────────────────────────────────────────

interface TenderCardProps {
  tender: DashboardTender;
  index: number;
  onClick: () => void;
}

function TenderCard({ tender, index, onClick }: TenderCardProps) {
  const days    = daysUntil(tender.deadline);
  const variant = deadlineBadgeVariant(days);

  // Match-score gradient — kolor końcowy zależy od poziomu dopasowania
  const scoreEndColor =
    tender.match_score > 80
      ? 'var(--color-go)'
      : tender.match_score > 60
        ? 'var(--color-warn)'
        : 'var(--color-nogo)';

  return (
    <motion.div
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08 }}
      onClick={onClick}
      className={[
        'group p-4 rounded-xl',
        'bg-ink-900/40 border border-ink-800/50',
        'hover:border-em/40 hover:bg-ink-900/60',
        'cursor-pointer transition-all duration-300',
      ].join(' ')}
    >
      {/* Wiersz: tytuł + badge terminu */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-slate-100 group-hover:text-em transition-colors truncate">
            {truncate(tender.title, 60)}
          </h4>
          <p className="text-xs text-slate-400 mt-1">{tender.buyer}</p>
        </div>
        <StatusBadge
          status={variant}
          label={`${days}d`}
          size="xs"
          className="shrink-0"
        />
      </div>

      {/* Pasek dopasowania */}
      <div className="mt-3">
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span className="text-slate-400">Dopasowanie</span>
          <span className="text-slate-200 font-medium">{tender.match_score}%</span>
        </div>
        <div className="h-1.5 bg-ink-800 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${tender.match_score}%` }}
            transition={{ duration: 0.8, delay: index * 0.1 + 0.3 }}
            className="h-full rounded-full"
            style={{
              background: `linear-gradient(90deg, var(--color-indigo), ${scoreEndColor})`,
            }}
          />
        </div>
      </div>

      {/* Wartość + strzałka */}
      <div className="mt-2 flex items-center justify-between">
        <span className="text-xs text-slate-300">{formatPLN(tender.value)}</span>
        <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-em transition-colors" />
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ActivityIcon — ikona w osi czasu aktywności
// ─────────────────────────────────────────────────────────────────────────────

function ActivityIcon({ type }: { type: string }) {
  const cls = 'w-3.5 h-3.5';
  switch (type) {
    case 'create':
      return (
        <svg className={`${cls} text-em`} viewBox="0 0 16 16" fill="none">
          <path
            d="M8 3v10M3 8h10"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      );
    case 'update':
      return (
        <svg className={`${cls} text-warn`} viewBox="0 0 16 16" fill="none">
          <path
            d="M11.5 1.5l3 3-9 9H2.5v-3l9-9z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case 'delete':
      return (
        <svg className={`${cls} text-nogo`} viewBox="0 0 16 16" fill="none">
          <path
            d="M2 4h12M5.33 4V2.67a1.33 1.33 0 011.34-1.34h2.66a1.33 1.33 0 011.34 1.34V4m2 0v9.33a1.33 1.33 0 01-1.34 1.34H4.67a1.33 1.33 0 01-1.34-1.34V4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    case 'login':
      return (
        <svg className={`${cls} text-indigo`} viewBox="0 0 16 16" fill="none">
          <path
            d="M10 2h2.67A1.33 1.33 0 0114 3.33v9.34A1.33 1.33 0 0112.67 14H10M6.67 11.33L10 8 6.67 4.67M10 8H2"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    default:
      return <Activity className={`${cls} text-slate-400`} />;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// ActivityItem — pojedynczy wpis w osi czasu
// ─────────────────────────────────────────────────────────────────────────────

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
      {/* Oś czasu */}
      <div className="flex flex-col items-center">
        <div className="w-7 h-7 rounded-full bg-ink-800/80 border border-ink-700 flex items-center justify-center shrink-0">
          <ActivityIcon type={entry.action_type} />
        </div>
        {!isLast && <div className="w-px flex-1 bg-ink-800 mt-1" />}
      </div>

      {/* Treść wpisu */}
      <div className="pb-4 flex-1 min-w-0">
        <p className="text-xs text-slate-200 leading-relaxed">
          <span className="font-medium text-slate-100">
            {(entry.user_email ?? 'system').split('@')[0]}
          </span>{' '}
          <span className="text-slate-400">{entry.action}</span>
        </p>
        <p className="text-[11px] text-slate-500 mt-0.5">
          {relativeTime(entry.created_at)}
        </p>
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// DigestSkeleton — loading state digestu AI
// ─────────────────────────────────────────────────────────────────────────────

function DigestSkeleton() {
  return <SkeletonTextBlock lines={5} />;
}

// ─────────────────────────────────────────────────────────────────────────────
// TenderListSkeleton — loading state listy przetargów
// ─────────────────────────────────────────────────────────────────────────────

function TenderListSkeleton() {
  return (
    <div className="space-y-3">
      {[...Array(4)].map((_, i) => (
        <SkeletonCard key={i} lines={2} />
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main — DashboardPage
// ─────────────────────────────────────────────────────────────────────────────

export function DashboardPage() {
  const authFetch = useAuthFetch();
  const { setCurrentModule, setSelectedTender } = useStore();

  // ── State ──────────────────────────────────────────────────────────────────

  const [kpi,             setKpi]             = useState<DashboardKPI | null>(null);
  const [tenders,         setTenders]         = useState<DashboardTender[]>([]);
  const [auditLog,        setAuditLog]        = useState<AuditEntry[]>([]);
  const [auditError,      setAuditError]      = useState(false);
  const [digest,          setDigest]          = useState<string | null>(null);
  const [digestError,     setDigestError]     = useState(false);
  const [digestLoading,   setDigestLoading]   = useState(false);
  const [loading,         setLoading]         = useState(true);
  const [refreshingAudit, setRefreshingAudit] = useState(false);

  // ── Animated counters ──────────────────────────────────────────────────────

  // Pipeline: animujemy wartość w dziesiątkach tysięcy → wyświetlamy M PLN
  const animActiveTenders = useAnimatedCounter(kpi?.active_tenders ?? 0);
  const animPipelineTenths = useAnimatedCounter(
    kpi?.pipeline_value ? Math.round((kpi.pipeline_value / 1_000_000) * 10) : 0,
  );
  const animWinRate  = useAnimatedCounter(kpi?.win_rate_mtd ?? 0);
  const animNewToday = useAnimatedCounter(kpi?.new_today ?? 0);

  // ── Formatted KPI values ───────────────────────────────────────────────────

  const pipelineLabel = `${(animPipelineTenths / 10).toLocaleString('pl-PL', {
    minimumFractionDigits: 1,
  })} M PLN`;

  const winRateTrend = kpi?.win_rate_mtd
    ? kpi.win_rate_mtd > 50 ? 5 : -3
    : 0;

  // ── Data Fetching ──────────────────────────────────────────────────────────

  const fetchDashboard = useCallback(async () => {
    try {
      const data = await authFetch('/api/v2/dashboard/stats') as DashboardKPI;
      setKpi(data);
    } catch (err) {
      // Fallback to tenders/stats endpoint when dashboard/stats returns 404
      try {
        const fallback = await authFetch('/api/v2/tenders/stats') as DashboardKPI;
        setKpi(fallback);
      } catch {
        console.error('Dashboard KPI fetch failed:', err);
        showToast('error', 'Nie udało się pobrać KPI');
      }
    }
  }, [authFetch]);

  const fetchTenders = useCallback(async () => {
    try {
      const data = await authFetch(
        '/api/v2/tenders?sort=match_score&limit=5&deadline_days=14',
      ) as DashboardTender[];
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
      if (data?.content) {
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
      await authFetch('/api/v2/dashboard/digest/generate', { method: 'POST' });
      showToast('success', 'Digest jest generowany…');
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

  // ── Auto-refresh audit co 60 s ─────────────────────────────────────────────

  useEffect(() => {
    const id = setInterval(fetchAuditLog, 60_000);
    return () => clearInterval(id);
  }, [fetchAuditLog]);

  // ── Render helpers ─────────────────────────────────────────────────────────

  const handleRefreshAll = () => {
    fetchDashboard();
    fetchTenders();
    fetchAuditLog();
    fetchDigest();
    showToast('info', 'Odświeżam dane…');
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <PageShell
      title="Dashboard"
      subtitle="Przegląd aktywności przetargowej"
      actions={
        <Button
          variant="secondary"
          size="sm"
          iconLeft={<RefreshCw className="w-3.5 h-3.5" />}
          onClick={handleRefreshAll}
        >
          Odśwież
        </Button>
      }
    >
      {/* ════════════════════════════════════════════════════════════════════
          ROW 1 — 4 kluczowe KPI
          ════════════════════════════════════════════════════════════════════ */}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {loading ? (
          <>
            {[...Array(4)].map((_, i) => (
              <SkeletonKPI key={i} />
            ))}
          </>
        ) : (
          <>
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0 }}
            >
              <MetricCard
                icon={Activity}
                label="Aktywne przetargi"
                value={animActiveTenders.toLocaleString('pl-PL')}
                trend={12}
                trendLabel="vs. poprzedni tydzień"
                iconColor="text-indigo"
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              <MetricCard
                icon={TrendingUp}
                label="Pipeline"
                value={pipelineLabel}
                trend={8}
                trendLabel="wzrost wartości"
                iconColor="text-em"
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <MetricCard
                icon={Target}
                label="Win Rate MTD"
                value={`${animWinRate}%`}
                trend={winRateTrend}
                trendLabel="wobec celu"
                iconColor="text-violet"
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <MetricCard
                icon={Bell}
                label="Nowe dziś"
                value={animNewToday.toLocaleString('pl-PL')}
                iconColor="text-nogo"
              />
            </motion.div>
          </>
        )}
      </div>

      {/* ════════════════════════════════════════════════════════════════════
          ROW 2 — Najgorętsze przetargi (hero) + AI Digest
          ════════════════════════════════════════════════════════════════════ */}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-8">
        {/* Najgorętsze przetargi — hero section */}
        <div className="lg:col-span-3">
          <GlassCard className="p-6 h-full">
            {/* Nagłówek sekcji */}
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-em animate-pulse-soft" />
                <h2 className="text-base font-semibold text-slate-100">
                  Najgorętsze dziś
                </h2>
              </div>
              <button
                onClick={() => setCurrentModule('zwiad')}
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-em transition-colors"
              >
                Wszystkie <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            {/* Zawartość */}
            {loading ? (
              <TenderListSkeleton />
            ) : tenders.length === 0 ? (
              <EmptyState
                icon={<Search className="w-6 h-6" />}
                title="Brak gorących przetargów"
                description="Nowe przetargi pojawią się po następnym skanie rynku."
                compact
              />
            ) : (
              <div className="space-y-3">
                {tenders.slice(0, 5).map((tender, i) => (
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

        {/* AI Digest — compact */}
        <div className="lg:col-span-2">
          <GlassCard className="p-6 h-full flex flex-col">
            {/* Nagłówek digestu */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-gradient-to-br from-em/20 to-violet/20">
                  <Zap className="w-4 h-4 text-em" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-slate-100">AI Digest</h2>
                  <p className="text-[11px] text-slate-500 leading-tight">
                    Inteligencja rynkowa YU-NA
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                iconLeft={
                  <RefreshCw
                    className={`w-3.5 h-3.5 ${digestLoading ? 'animate-spin' : ''}`}
                  />
                }
                loading={digestLoading}
                onClick={generateDigest}
              >
                Odśwież
              </Button>
            </div>

            {/* Zawartość digestu */}
            <div className="flex-1 overflow-y-auto">
              {digestLoading ? (
                <DigestSkeleton />
              ) : digestError || !digest ? (
                <EmptyState
                  icon={<Zap className="w-5 h-5" />}
                  title="Digest zostanie wygenerowany dziś o 8:00"
                  description='Kliknij „Odśwież" aby wygenerować teraz.'
                  compact
                />
              ) : (
                <div className="prose prose-invert prose-sm max-w-none">
                  {renderSimpleMarkdown(digest)}
                </div>
              )}
            </div>
          </GlassCard>
        </div>
      </div>

      {/* ════════════════════════════════════════════════════════════════════
          ROW 3 — Feed aktywności (collapsible, secondary)
          ════════════════════════════════════════════════════════════════════ */}

      {!auditError && auditLog.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
        >
          <GlassCard className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-slate-100">Ostatnia aktywność</h2>
              <div className="flex items-center gap-2">
                {refreshingAudit && (
                  <RefreshCw className="w-3.5 h-3.5 text-slate-500 animate-spin" />
                )}
                <span className="text-[11px] text-slate-500 tabular-nums">
                  auto 60 s
                </span>
              </div>
            </div>

            <div className="max-h-48 overflow-y-auto pr-2 scrollbar-thin scrollbar-track-ink-900 scrollbar-thumb-ink-700">
              <AnimatePresence mode="popLayout">
                {auditLog.slice(0, 8).map((entry, i) => (
                  <ActivityItem
                    key={entry.id}
                    entry={entry}
                    index={i}
                    isLast={i === Math.min(auditLog.length, 8) - 1}
                  />
                ))}
              </AnimatePresence>
            </div>
          </GlassCard>
        </motion.div>
      )}

      {/* Spacer dolny */}
      <div className="h-8" />
    </PageShell>
  );
}
