'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { motion } from 'motion/react';
import { useStore } from '@/store/useStore';
import { ArrowRight, Bell, LogOut, Package, Lock } from 'lucide-react';

// ── YU-NA Hub — Light theme ─────────────────────────────────────────────────────
// Marketplace of purchased products. Entry point after login.

export default function YunaHubPage() {
  const user        = useStore((s) => s.user);
  const accessToken = useStore((s) => s.accessToken);
  const logout      = useStore((s) => s.clearAuth);
  const router      = useRouter();
  const isAuth      = !!(user && accessToken);

  const [hydrated, setHydrated] = useState(false);
  useEffect(() => { setHydrated(true); }, []);
  useEffect(() => {
    if (hydrated && !isAuth) router.replace('/login');
  }, [hydrated, isAuth, router]);

  if (!hydrated || !isAuth) return null;

  const products = [
    {
      id: 'budos',
      name: 'Bud.OS',
      subtitle: 'System Decyzyjny AI',
      plan: 'Professional',
      logo: '/brand/B01-app-icon-budos.png',
      href: '/app/zwiad',
      stats: { tenders: 14, active: 3, winRate: 67 },
      active: true,
    },
    {
      id: 'infra',
      name: 'Infra.OS',
      subtitle: 'Zarządzanie infrastrukturą',
      plan: null,
      logo: '/brand/01-logo-concept.png',
      href: '#',
      stats: null,
      active: false,
    },
    {
      id: 'dev',
      name: 'Dev.OS',
      subtitle: 'Analiza rynku nieruchomości',
      plan: null,
      logo: '/brand/01-logo-concept.png',
      href: '#',
      stats: null,
      active: false,
    },
  ];

  return (
    <div className="min-h-screen bg-[#fafbfc]" style={{ background: '#fafbfc' }}>
      {/* ─── Top nav ───────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-gray-200/60">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/app" className="flex items-center gap-3">
            <Image
              src="/brand/01-logo-concept.png"
              alt="YU-NA"
              width={30}
              height={30}
              className="rounded-lg"
            />
            <span className="font-semibold text-base tracking-tight text-[#1a1a2e]">
              YU-NA
            </span>
            <span className="text-xs text-gray-400 font-medium ml-1">Intelligence</span>
          </Link>
          <div className="flex items-center gap-4">
            <button className="relative p-2 rounded-full hover:bg-gray-100 transition-colors">
              <Bell className="w-4.5 h-4.5 text-gray-500" />
            </button>
            <div className="flex items-center gap-3 pl-3 border-l border-gray-200">
              <div className="w-8 h-8 rounded-full bg-[#1a1a2e] flex items-center justify-center text-white text-xs font-semibold">
                {user?.name?.slice(0, 2).toUpperCase() || 'U'}
              </div>
              <span className="text-sm text-gray-700 font-medium hidden sm:block">{user?.name}</span>
              <button
                onClick={() => { logout(); router.push('/login'); }}
                className="p-2 rounded-full hover:bg-gray-100 transition-colors"
                title="Wyloguj"
              >
                <LogOut className="w-4 h-4 text-gray-400" />
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* ─── Main content ──────────────────────────────────────────────────── */}
      <main className="max-w-6xl mx-auto px-6 py-12">
        {/* Welcome */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <h1 className="text-2xl md:text-3xl font-bold text-[#1a1a2e] tracking-tight">
            Witaj, {user?.name?.split(' ')[0] || 'użytkowniku'}.
          </h1>
          <p className="mt-2 text-gray-500">
            Twoje produkty YU-NA Intelligence.
          </p>
        </motion.div>

        {/* ─── Product cards ─────────────────────────────────────────────────── */}
        <section className="mt-10">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-5 flex items-center gap-2">
            <Package className="w-4 h-4" />
            Moje produkty
          </h2>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {products.map((p, i) => (
              <motion.div
                key={p.id}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
              >
                {p.active ? (
                  <Link
                    href={p.href}
                    className="group block p-6 rounded-2xl border border-gray-200 bg-white hover:shadow-xl hover:shadow-gray-100/80 hover:border-gray-300 transition-all duration-300"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <Image
                        src={p.logo}
                        alt={p.name}
                        width={44}
                        height={44}
                        className="rounded-xl"
                      />
                      <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-100">
                        {p.plan}
                      </span>
                    </div>
                    <h3 className="text-lg font-semibold text-[#1a1a2e] group-hover:text-emerald-700 transition-colors">
                      {p.name}
                    </h3>
                    <p className="text-sm text-gray-500 mt-0.5">{p.subtitle}</p>

                    {p.stats && (
                      <div className="mt-5 grid grid-cols-3 gap-3 pt-4 border-t border-gray-100">
                        <div>
                          <div className="text-lg font-bold text-[#1a1a2e]">{p.stats.tenders}</div>
                          <div className="text-xs text-gray-400">nowe</div>
                        </div>
                        <div>
                          <div className="text-lg font-bold text-[#1a1a2e]">{p.stats.active}</div>
                          <div className="text-xs text-gray-400">aktywne</div>
                        </div>
                        <div>
                          <div className="text-lg font-bold text-emerald-600">{p.stats.winRate}%</div>
                          <div className="text-xs text-gray-400">win rate</div>
                        </div>
                      </div>
                    )}

                    <div className="mt-5 flex items-center gap-1.5 text-sm font-medium text-emerald-600 group-hover:gap-2.5 transition-all">
                      Otwórz {p.name}
                      <ArrowRight className="w-3.5 h-3.5" />
                    </div>
                  </Link>
                ) : (
                  <div className="relative p-6 rounded-2xl border border-gray-100 bg-gray-50/50 opacity-75">
                    <div className="flex items-start justify-between mb-4">
                      <div className="w-11 h-11 rounded-xl bg-gray-200 flex items-center justify-center">
                        <Lock className="w-4 h-4 text-gray-400" />
                      </div>
                      <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-gray-100 text-gray-500 border border-gray-200">
                        Wkrótce
                      </span>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-600">{p.name}</h3>
                    <p className="text-sm text-gray-400 mt-0.5">{p.subtitle}</p>
                    <div className="mt-5 text-sm text-gray-400">
                      Powiadom mnie o premierze →
                    </div>
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </section>

        {/* ─── Upcoming ──────────────────────────────────────────────────────── */}
        <section className="mt-16 p-8 rounded-2xl bg-gradient-to-br from-[#1a1a2e] to-[#2a2a4e] text-white">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold">Infra.OS i Dev.OS — w przygotowaniu</h3>
              <p className="text-gray-400 text-sm mt-1">Dowiedz się pierwszy. Dołącz do listy oczekujących.</p>
            </div>
            <button className="flex items-center gap-2 bg-white/10 hover:bg-white/20 border border-white/10 text-white px-5 py-2.5 rounded-full text-sm font-medium transition-colors">
              <Bell className="w-3.5 h-3.5" />
              Powiadom mnie
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}
