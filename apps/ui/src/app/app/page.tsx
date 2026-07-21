'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'motion/react';
import {
  Hexagon, Settings, LogOut,
  ChevronRight, Lock, ArrowUpRight,
  Zap,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { useRouter } from 'next/navigation';

// ── Products config ────────────────────────────────────────────────────────────

const OWNED_PRODUCTS = [
  {
    id: 'budos',
    name: 'BudOS',
    subtitle: 'Przetargi budowlane · AI',
    href: '/app/budos',
    icon: 'b',
    status: 'active' as const,
    metrics: ['2 137 przetargów', '94% trafność', 'Ostatnia sync: 2 min temu'],
    color: '#10b981',
  },
];

const AVAILABLE_PRODUCTS = [
  {
    id: 'coming-1',
    name: 'Produkt #2',
    subtitle: 'Wkrótce · Q3 2026',
    href: '#',
    icon: '?',
    status: 'locked' as const,
    teaser: 'Nowe narzędzie AI dla branży budowlanej.',
    badge: 'Q3 2026',
  },
  {
    id: 'coming-2',
    name: 'Produkt #3',
    subtitle: 'Wkrótce · Q4 2026',
    href: '#',
    icon: '?',
    status: 'locked' as const,
    teaser: 'Nowe narzędzie AI dla branży budowlanej.',
    badge: 'Q4 2026',
  },
];

// ── Page ───────────────────────────────────────────────────────────────────────

export default function AppDashboard() {
  const user      = useStore((s) => s.user);
  const accessToken = useStore((s) => s.accessToken);
  const clearAuth = useStore((s) => s.clearAuth);
  const router    = useRouter();
  const isAuth    = !!(user && accessToken);

  useEffect(() => {
    if (!isAuth) router.replace('/login');
  }, [isAuth, router]);

  if (!isAuth) return null;

  const greeting = (() => {
    const h = new Date().getHours();
    if (h < 12) return 'Dzień dobry';
    if (h < 18) return 'Cześć';
    return 'Dobry wieczór';
  })();

  return (
    <main className="min-h-screen bg-ink-950">

      {/* ── Top bar ── */}
      <header className="border-b border-ink-800/60 glass-2 sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          {/* Brand */}
          <div className="flex items-center gap-2.5">
            <div className="relative w-7 h-7">
              <Hexagon className="w-7 h-7 text-em" strokeWidth={1.5} />
              <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-em">YN</span>
            </div>
            <span className="text-sm font-bold text-slate-200" style={{ fontFamily: 'var(--font-space)' }}>YU-NA</span>
          </div>

          {/* User actions */}
          <div className="flex items-center gap-1">
            <span className="text-xs text-slate-600 mr-2 hidden sm:block">{user?.email}</span>
            <Link
              href="/app/settings"
              className="p-2 rounded-lg text-slate-600 hover:text-slate-300 hover:bg-ink-900 transition-all"
            >
              <Settings className="w-4 h-4" />
            </Link>
            <button
              onClick={() => { clearAuth(); router.push('/'); }}
              className="p-2 rounded-lg text-slate-600 hover:text-nogo hover:bg-ink-900 transition-all"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* ── Content ── */}
      <div className="max-w-4xl mx-auto px-6 py-12">

        {/* Welcome */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <h1 className="text-2xl font-bold text-slate-100" style={{ fontFamily: 'var(--font-space)' }}>
            {greeting}, {user?.name?.split(' ')[0] ?? 'Witaj'}.
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Twoje narzędzia YU-NA. Wybierz produkt.
          </p>
        </motion.div>

        {/* ── Active products ── */}
        <div className="mb-3">
          <p className="text-[11px] font-semibold text-slate-600 uppercase tracking-[0.12em] mb-4">
            Twoje produkty
          </p>
          <div className="space-y-3">
            {OWNED_PRODUCTS.map((product, i) => (
              <motion.div
                key={product.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06 }}
              >
                <Link
                  href={product.href}
                  className="group flex items-center gap-5 p-5 rounded-2xl bg-ink-900/50 border border-ink-700/60 hover:border-em/30 hover:bg-ink-900/80 transition-all card-hover"
                >
                  {/* Icon */}
                  <div className="w-14 h-14 rounded-2xl bg-em/10 border border-em/20 flex items-center justify-center shrink-0 glow-em-xs group-hover:glow-em-sm transition-all">
                    <span
                      className="text-2xl font-bold text-em"
                      style={{ fontFamily: 'var(--font-space)' }}
                    >
                      {product.icon}
                    </span>
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <h3 className="text-base font-bold text-slate-100" style={{ fontFamily: 'var(--font-space)' }}>
                        {product.name}
                      </h3>
                      <span className="flex items-center gap-1 text-[10px] font-bold text-go bg-go/10 border border-go/20 px-2 py-0.5 rounded-full">
                        <span className="w-1.5 h-1.5 rounded-full bg-go animate-pulse" />
                        Aktywny
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mb-3">{product.subtitle}</p>

                    {/* Metrics row */}
                    <div className="flex flex-wrap gap-2">
                      {product.metrics.map((m, mi) => (
                        <span
                          key={mi}
                          className="text-[10px] text-slate-600 bg-ink-800 border border-ink-700 px-2 py-0.5 rounded-full font-mono"
                        >
                          {m}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Arrow */}
                  <ArrowUpRight className="w-5 h-5 text-slate-600 group-hover:text-em transition-colors shrink-0" />
                </Link>
              </motion.div>
            ))}
          </div>
        </div>

        {/* ── Marketplace ── */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mt-10"
        >
          <div className="flex items-center justify-between mb-4">
            <p className="text-[11px] font-semibold text-slate-600 uppercase tracking-[0.12em]">
              Wkrótce w YU-NA
            </p>
            <span className="flex items-center gap-1.5 text-[10px] text-em/60 font-medium">
              <Zap className="w-3 h-3" /> Premiera 2026
            </span>
          </div>

          <div className="grid md:grid-cols-2 gap-3">
            {AVAILABLE_PRODUCTS.map((product, i) => (
              <motion.div
                key={product.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + i * 0.06 }}
                className="flex items-center gap-4 p-4 rounded-xl bg-ink-900/20 border border-ink-800/40 opacity-50"
              >
                <div className="w-10 h-10 rounded-xl bg-ink-800 border border-ink-700 flex items-center justify-center shrink-0">
                  <Lock className="w-4 h-4 text-slate-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-slate-500">{product.name}</h3>
                  <p className="text-xs text-slate-700 mt-0.5">{product.teaser}</p>
                </div>
                <span className="text-[10px] text-slate-700 bg-ink-800 border border-ink-700/50 px-2 py-0.5 rounded-full font-mono shrink-0">
                  {product.badge}
                </span>
              </motion.div>
            ))}
          </div>
        </motion.div>

      </div>

      {/* ── Footer ── */}
      <footer className="border-t border-ink-800/40 mt-16 py-6 px-6">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <p className="text-[11px] text-slate-700 font-mono">
            PRECYZJA · ZWIAD · PRZEWAGA
          </p>
          <Link href="/" className="text-[11px] text-slate-700 hover:text-slate-400 transition-colors">
            yu-na.io
          </Link>
        </div>
      </footer>
    </main>
  );
}
