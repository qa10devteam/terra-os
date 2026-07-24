'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { motion, useReducedMotion } from 'motion/react';
import { useStore } from '@/store/useStore';
import { useAuthFetch } from '@/lib/api-v2';
import {
  ArrowRight, Bell, LogOut, TrendingUp, Activity, FileText,
  Zap, BarChart3, ChevronRight, Search, Calculator, Brain,
} from 'lucide-react';

// ── YU-NA Hub v4 — Faza 2+3 ──────────────────────────────────────────────────
// Live API metrics · Recent tenders · Quick actions · Mobile responsive · Motion

interface TenderRow {
  id: string;
  title?: string;
  name?: string;
  score?: number;
  match_score?: number;
  value?: number;
  value_pln?: number;
  buyer?: string;
  status?: string;
}

interface DashStats {
  total_tenders?: number;
  new_today?: number;
  new_this_week?: number;
  high_score_count?: number;
}

interface TendersResponse {
  total?: number;
  items?: TenderRow[];
  data?: TenderRow[];
  results?: TenderRow[];
}

// ── Shimmer skeleton helper ───────────────────────────────────────────────────
function Shimmer({ className = '' }: { className?: string }) {
  return (
    <div
      className={`animate-shimmer rounded bg-gradient-to-r from-ink-200 via-ink-100 to-ink-200 ${className}`}
      style={{ backgroundSize: '200% 100%' }}
    />
  );
}

export default function YunaHubPage() {
  const user        = useStore((s) => s.user);
  const accessToken = useStore((s) => s.accessToken);
  const logout      = useStore((s) => s.clearAuth);
  const router      = useRouter();
  const reduce      = useReducedMotion();
  const isAuth      = !!(user && accessToken);
  const authFetch   = useAuthFetch();

  const [hydrated, setHydrated] = useState(() => {
    if (typeof window === 'undefined') return false;
    try {
      const raw = localStorage.getItem('yuna-store');
      if (!raw) return false;
      const parsed = JSON.parse(raw) as { state?: { accessToken?: unknown; user?: unknown } };
      return !!(parsed?.state?.accessToken && parsed?.state?.user);
    } catch { return false; }
  });

  // ── Stats state ─────────────────────────────────────────────────────────────
  const [stats, setStats] = useState({ active: '—', week: '—', mine: '—' });
  const [statsLoaded, setStatsLoaded] = useState(false);

  // ── Recent tenders state ────────────────────────────────────────────────────
  const [recentTenders, setRecentTenders] = useState<TenderRow[]>([]);
  const [tendersLoaded, setTendersLoaded] = useState(false);

  useEffect(() => { setHydrated(true); }, []);
  useEffect(() => {
    if (hydrated && !isAuth) router.replace('/login');
  }, [hydrated, isAuth, router]);

  // ── Fetch stats (total count) ────────────────────────────────────────────────
  useEffect(() => {
    if (!isAuth) return;
    authFetch('/api/v2/dashboard/stats')
      .then((d: any) => {
        if (d) setStats({
          active: String(d.total_tenders ?? '—'),
          week: String(d.new_today ?? '—'),
          mine: String(d.high_score_count ?? '—'),
        });
        setStatsLoaded(true);
      })
      .catch(() => { setStatsLoaded(true); });
  }, [isAuth, authFetch]);

  // ── Fetch recent tenders ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!isAuth) return;
    authFetch('/api/v2/dashboard/recent-tenders')
      .then((d: any) => {
        if (d) {
          const rows = d.items ?? d.data ?? d.results ?? [];
          setRecentTenders(rows.slice(0, 5));
        }
        setTendersLoaded(true);
      })
      .catch(() => { setTendersLoaded(true); });
  }, [isAuth, authFetch]);

  // ── Auth gate ────────────────────────────────────────────────────────────────
  if (!hydrated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-ink-50">
        <div className="w-8 h-8 border-2 border-ink-300 border-t-ink-700 rounded-full animate-spin" />
      </div>
    );
  }
  if (!isAuth) return null;

  const firstName = user?.name?.split(' ')[0] || 'użytkowniku';
  const initials  = user?.name?.slice(0, 2).toUpperCase() || 'U';
  const today     = new Date().toLocaleDateString('pl-PL', { weekday: 'long', day: 'numeric', month: 'long' });

  // ── Score badge helper ───────────────────────────────────────────────────────
  function ScoreBadge({ score }: { score?: number }) {
    if (score === undefined || score === null) {
      return <span className="text-[10.5px] px-2 py-0.5 rounded-full font-semibold bg-ink-100 text-ink-400">—</span>;
    }
    // API returns 0..1 float (e.g. 0.85) — normalize to 0..100
    const pct = score <= 1 ? Math.round(score * 100) : Math.round(score);
    const cls = pct >= 80
      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
      : pct >= 65
        ? 'bg-amber-50 text-amber-700 border border-amber-200'
        : 'bg-ink-100 text-ink-500 border border-ink-200';
    return <span className={`text-[10.5px] px-2 py-0.5 rounded-full font-semibold tabular-nums font-mono ${cls}`}>{pct}</span>;
  }

  return (
    <div
      className="min-h-screen font-display"
      style={{
        background: '#f8f9fb',
        backgroundImage: 'radial-gradient(circle, #d1d5db 1px, transparent 1px)',
        backgroundSize: '22px 22px',
      }}
    >
      {/* ─── Nav ─────────────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-white/90 border-b border-ink-100 shadow-sm">
        <div className="max-w-5xl mx-auto px-6 h-[60px] flex items-center justify-between">
          <Link href="/app" className="flex items-center gap-2.5">
            <Image src="/brand/01-logo-concept.png" alt="YU-NA" width={26} height={26} className="rounded-lg" />
            <span className="font-semibold text-[13.5px] tracking-tight text-ink-900">YU-NA</span>
          </Link>
          <div className="flex items-center gap-1.5">
            <button type="button" className="p-2 rounded-full hover:bg-ink-100 transition-colors" title="Powiadomienia">
              <Bell className="w-4 h-4 text-ink-400" />
            </button>
            <div className="flex items-center gap-2 pl-3 border-l border-ink-200 ml-1">
              <div className="w-7 h-7 rounded-full bg-ink-900 flex items-center justify-center text-white text-[11px] font-semibold shrink-0">
                {initials}
              </div>
              <span className="text-[13px] text-ink-600 font-medium hidden sm:block">{user?.name}</span>
              <button
                type="button"
                onClick={() => { logout(); router.push('/login'); }}
                className="p-2 rounded-full hover:bg-ink-100 transition-colors"
                title="Wyloguj"
              >
                <LogOut className="w-4 h-4 text-ink-400" />
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* ─── Main ────────────────────────────────────────────────────────────── */}
      <main className="max-w-5xl mx-auto px-6 py-12">

        {/* Welcome row — mobile: stack date below name */}
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8 gap-3"
        >
          <div>
            <h1 className="text-2xl font-bold text-ink-900 tracking-tight">
              Witaj, {firstName}.
            </h1>
            <p className="mt-1 text-[13.5px] text-ink-400">
              YU-NA Intelligence Platform
            </p>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center gap-2">
            <span className="text-[12px] text-ink-400 capitalize">{today}</span>
            <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-ink-500 bg-white border border-ink-200 rounded-full px-3 py-1.5 shadow-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
              Wszystkie systemy online
            </div>
          </div>
        </motion.div>

        {/* ─── Bud.OS hero card ──────────────────────────────────────────────── */}
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="mb-4"
        >
          <Link
            href="/app/zwiad"
            className="group relative block rounded-2xl bg-ink-950 overflow-hidden hover:ring-1 hover:ring-white/10 transition-all shadow-2xl shadow-ink-900/30"
          >
            {/* Header row */}
            <div className="relative z-10 flex flex-col sm:flex-row sm:items-center sm:justify-between px-7 pt-6 pb-5 gap-4">
              <div className="flex items-center gap-3.5">
                <Image src="/brand/B01-app-icon-budos.png" alt="Bud.OS" width={40} height={40} className="rounded-xl shrink-0" />
                <div>
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-[10px] font-bold text-emerald-400 tracking-[0.14em] uppercase">Professional</span>
                  </div>
                  <h2 className="text-[18px] font-bold text-white leading-none tracking-tight">Bud.OS</h2>
                </div>
              </div>

              {/* Live Metrics */}
              <div className="flex items-center gap-2 sm:gap-2.5 shrink-0 overflow-x-auto pb-1 sm:pb-0">
                {[
                  { icon: Activity,   value: stats.active, label: 'przetargów',   accent: false },
                  { icon: FileText,   value: stats.week,   label: 'ten tydzień',  accent: false },
                  { icon: TrendingUp, value: stats.mine,   label: 'win rate',     accent: true  },
                ].map((m) => (
                  <div key={m.label} className="flex flex-col items-center px-3 sm:px-4 py-3 rounded-xl bg-white/[0.05] border border-white/[0.07] min-w-[68px] sm:min-w-[76px] shrink-0">
                    <m.icon className={`w-3.5 h-3.5 mb-1.5 ${m.accent ? 'text-emerald-400' : 'text-ink-500'}`} />
                    {!statsLoaded ? (
                      <div className="bg-ink-200/60 animate-pulse h-6 w-10 rounded mb-1" />
                    ) : (
                      <div className={`text-[1.25rem] sm:text-[1.35rem] font-bold leading-none tabular-nums font-mono ${m.accent ? 'text-emerald-400' : 'text-white'}`}>
                        {m.value}
                      </div>
                    )}
                    <div className="text-[9.5px] text-ink-500 mt-1 text-center leading-tight">{m.label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Screenshot */}
            <div className="relative z-10 mx-4 mb-0 rounded-t-xl overflow-hidden border border-white/[0.07] border-b-0">
              {/* Browser chrome */}
              <div className="flex items-center gap-1.5 px-3.5 py-2.5 bg-ink-900/90 border-b border-white/[0.05]">
                <span className="w-2 h-2 rounded-full bg-red-500/50" />
                <span className="w-2 h-2 rounded-full bg-amber-400/50" />
                <span className="w-2 h-2 rounded-full bg-emerald-500/50" />
                <div className="flex-1 mx-2.5 bg-ink-800/70 rounded h-4 flex items-center px-2">
                  <span className="text-[9.5px] text-ink-500 font-mono">app.yu-na.io/zwiad</span>
                </div>
              </div>
              <Image
                src="/brand/live-zwiad.png"
                alt="BudOS Zwiad Przetargowy"
                width={1440}
                height={900}
                className="w-full h-auto block"
                priority
              />
            </div>

            {/* Footer CTA */}
            <div className="relative z-10 px-7 py-4 flex items-center justify-between border-t border-white/[0.05]">
              <p className="text-[12.5px] text-ink-500 max-w-[48ch] hidden sm:block">
                Przetargi z BZP i TED, scoring GO/NO-GO, kosztorysy KNR/ICB, analiza konkurencji.
              </p>
              <div className="flex items-center gap-1.5 text-[13px] font-semibold text-emerald-400 group-hover:gap-2.5 transition-all shrink-0">
                Otwórz Bud.OS <ArrowRight className="w-3.5 h-3.5" />
              </div>
            </div>
          </Link>
        </motion.div>

        {/* ─── Quick Actions ──────────────────────────────────────────────────── */}
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-6 mb-6"
        >
          <Link
            href="/app/zwiad"
            className="col-span-1 flex items-center gap-3 border border-ink-200 rounded-xl p-4 bg-white hover:bg-ink-50 transition-colors shadow-sm"
          >
            <div className="w-8 h-8 rounded-lg bg-ink-100 flex items-center justify-center shrink-0">
              <Search className="w-4 h-4 text-ink-600" />
            </div>
            <div>
              <div className="text-[13.5px] font-semibold text-ink-900">Zwiad</div>
              <div className="text-[11px] text-ink-400">Przetargi</div>
            </div>
          </Link>

          <Link
            href="/app/kosztorys"
            className="col-span-1 flex items-center gap-3 border border-ink-200 rounded-xl p-4 bg-white hover:bg-ink-50 transition-colors shadow-sm"
          >
            <div className="w-8 h-8 rounded-lg bg-ink-100 flex items-center justify-center shrink-0">
              <Calculator className="w-4 h-4 text-ink-600" />
            </div>
            <div>
              <div className="text-[13.5px] font-semibold text-ink-900">Kosztorys</div>
              <div className="text-[11px] text-ink-400">KNR / ICB</div>
            </div>
          </Link>

          {/* Last item spans full width on 2-col mobile, normal on 3-col desktop */}
          <Link
            href="/app/silnik"
            className="col-span-2 sm:col-span-1 flex items-center gap-3 border border-ink-200 rounded-xl p-4 bg-white hover:bg-ink-50 transition-colors shadow-sm"
          >
            <div className="w-8 h-8 rounded-lg bg-ink-100 flex items-center justify-center shrink-0">
              <Brain className="w-4 h-4 text-ink-600" />
            </div>
            <div>
              <div className="text-[13.5px] font-semibold text-ink-900">Silnik AI</div>
              <div className="text-[11px] text-ink-400">Analiza i scoring</div>
            </div>
          </Link>
        </motion.div>

        {/* ─── Recent Tenders ─────────────────────────────────────────────────── */}
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="mb-8"
        >
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[13.5px] font-semibold text-ink-700">Ostatnie przetargi</h3>
            <Link href="/app/zwiad" className="text-[12px] text-ink-400 hover:text-ink-600 transition-colors">
              Zobacz wszystkie →
            </Link>
          </div>

          <div className="bg-white rounded-2xl border border-ink-200 overflow-hidden shadow-sm">
            {!tendersLoaded ? (
              /* Skeleton rows */
              <div className="divide-y divide-ink-100">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="flex items-center gap-4 px-5 py-4">
                    <Shimmer className="h-4 flex-1 max-w-[55%]" />
                    <Shimmer className="h-5 w-10 rounded-full" />
                    <Shimmer className="h-4 w-20 ml-auto" />
                  </div>
                ))}
              </div>
            ) : recentTenders.length === 0 ? (
              /* Empty state */
              <div className="px-6 py-8 flex flex-col items-center text-center gap-3">
                <FileText className="w-8 h-8 text-ink-300" />
                <p className="text-[13.5px] text-ink-500">Brak przetargów w systemie.</p>
                <Link
                  href="/app/zwiad"
                  className="inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-emerald-600 hover:text-emerald-700 transition-colors"
                >
                  Zacznij od zwiadowania rynku <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            ) : (
              /* Data rows — mobile: card layout, desktop: row layout */
              <div className="divide-y divide-ink-100">
                {recentTenders.map((t) => {
                  const title = t.title ?? t.name ?? '(bez tytułu)';
                  const value = t.value_pln ?? t.value;
                  const valueFmt = value != null
                    ? new Intl.NumberFormat('pl-PL', { style: 'currency', currency: 'PLN', maximumFractionDigits: 0 }).format(value)
                    : '—';
                  return (
                    <Link
                      key={t.id}
                      href="/app/zwiad"
                      className="group flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 px-5 py-4 hover:bg-ink-50 transition-colors"
                    >
                      <span className="text-[13px] text-ink-800 font-medium truncate flex-1 min-w-0 group-hover:text-ink-900">
                        {title}
                      </span>
                      <div className="flex items-center gap-3 shrink-0">
                        <ScoreBadge score={t.match_score ?? t.score} />
                        <span className="text-[12px] text-ink-500 font-mono tabular-nums">{valueFmt}</span>
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        </motion.div>

        {/* ─── Infra.OS + Dev.OS — mobile: 1 col, desktop: 2 col ────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            {
              id: 'infra',
              icon: Zap,
              name: 'Infra.OS',
              tagline: 'Zarządzanie infrastrukturą budowy',
              desc: 'Harmonogramy, zasoby, logistyka placu budowy i monitoring postępów — wszystko w jednym miejscu.',
              eta: 'Q3 2026',
              color: 'amber' as const,
              index: 0,
            },
            {
              id: 'dev',
              icon: BarChart3,
              name: 'Dev.OS',
              tagline: 'Analiza rynku nieruchomości',
              desc: 'Feasibility studies, ROI inwestycji, analiza lokalizacji i wyceny rynkowe dla deweloperów.',
              eta: 'Q4 2026',
              color: 'blue' as const,
              index: 1,
            },
          ].map((p) => {
            const colorMap = {
              amber: {
                bg: 'from-amber-500/[0.06] to-orange-500/[0.03]',
                border: 'border-amber-200/60 hover:border-amber-300/80',
                iconBg: 'bg-amber-100',
                iconFg: 'text-amber-600',
                badge: 'text-amber-600 bg-amber-50 border border-amber-200',
                title: 'text-ink-900',
                cta: 'text-amber-600 bg-amber-50 hover:bg-amber-100 border border-amber-200',
              },
              blue: {
                bg: 'from-blue-500/[0.06] to-indigo-500/[0.03]',
                border: 'border-blue-200/60 hover:border-blue-300/80',
                iconBg: 'bg-blue-100',
                iconFg: 'text-blue-600',
                badge: 'text-blue-600 bg-blue-50 border border-blue-200',
                title: 'text-ink-900',
                cta: 'text-blue-600 bg-blue-50 hover:bg-blue-100 border border-blue-200',
              },
            };
            const c = colorMap[p.color];

            return (
              <motion.div
                key={p.id}
                initial={reduce ? false : { opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.1 * p.index + 0.3, ease: [0.16, 1, 0.3, 1] }}
              >
                <div className={`relative h-full p-6 rounded-2xl bg-gradient-to-br ${c.bg} border ${c.border} bg-white transition-all shadow-sm`}>
                  {/* Header */}
                  <div className="flex items-start justify-between mb-5">
                    <div className={`w-10 h-10 rounded-xl ${c.iconBg} flex items-center justify-center shrink-0`}>
                      <p.icon className={`w-5 h-5 ${c.iconFg}`} />
                    </div>
                    <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full ${c.badge}`}>
                      Wkrótce · {p.eta}
                    </span>
                  </div>

                  {/* Name + tagline */}
                  <h3 className={`text-[17px] font-bold ${c.title} leading-tight mb-1`}>{p.name}</h3>
                  <p className="text-[12px] font-medium text-ink-500 mb-3">{p.tagline}</p>
                  <p className="text-[13px] text-ink-500 leading-relaxed mb-6">{p.desc}</p>

                  {/* CTA */}
                  <button
                    type="button"
                    className={`inline-flex items-center gap-1.5 text-[12.5px] font-semibold px-3.5 py-2 rounded-lg transition-colors ${c.cta}`}
                  >
                    Powiadom mnie <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>

      </main>
    </div>
  );
}
