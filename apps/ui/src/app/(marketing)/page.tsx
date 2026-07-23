'use client';

import Image from 'next/image';
import Link from 'next/link';
import { motion } from 'motion/react';
import { ArrowRight, Brain, Shield, Zap, BarChart3, Target, Sparkles } from 'lucide-react';

// ── YU-NA Landing — Light Theme ─────────────────────────────────────────────────
// Clean, modern, Apple-glass aesthetic. Describes the platform. CTA → signup.

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#fafbfc] text-[#1a1a2e] antialiased overflow-x-hidden" style={{ background: '#fafbfc' }}>
      {/* ─── Nav ─────────────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 inset-x-0 z-50 backdrop-blur-xl bg-white/70 border-b border-gray-200/60">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <Image
              src="/brand/01-logo-concept.png"
              alt="YU-NA"
              width={32}
              height={32}
              className="rounded-lg"
            />
            <span className="font-semibold text-lg tracking-tight text-[#1a1a2e]">
              YU-NA
            </span>
          </Link>
          <div className="hidden md:flex items-center gap-8 text-sm text-gray-600">
            <Link href="/budos" className="hover:text-[#1a1a2e] transition-colors">Produkty</Link>
            <Link href="#features" className="hover:text-[#1a1a2e] transition-colors">Funkcje</Link>
            <Link href="#pricing" className="hover:text-[#1a1a2e] transition-colors">Cennik</Link>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm text-gray-600 hover:text-[#1a1a2e] transition-colors px-4 py-2"
            >
              Zaloguj się
            </Link>
            <Link
              href="/signup"
              className="text-sm font-medium bg-[#1a1a2e] text-white px-5 py-2.5 rounded-full hover:bg-[#2a2a3e] transition-colors"
            >
              Rozpocznij
            </Link>
          </div>
        </div>
      </nav>

      {/* ─── Hero ────────────────────────────────────────────────────────────── */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-50 text-emerald-700 text-sm font-medium mb-8 border border-emerald-100">
              <Sparkles className="w-3.5 h-3.5" />
              Platforma Intelligence dla budownictwa
            </div>

            <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.1] text-[#1a1a2e]">
              Decyzje oparte<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 to-teal-500">
                na danych
              </span>
            </h1>

            <p className="mt-6 text-lg md:text-xl text-gray-500 max-w-2xl mx-auto leading-relaxed">
              YU-NA to ekosystem narzędzi AI dla firm budowlanych. Monitoring przetargów, 
              analiza ryzyka, kosztorysy — wszystko w jednym miejscu.
            </p>

            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/signup"
                className="flex items-center gap-2 bg-[#1a1a2e] text-white px-8 py-4 rounded-full text-base font-medium hover:bg-[#2a2a3e] transition-all hover:scale-[1.02] shadow-lg shadow-gray-900/10"
              >
                Załóż konto
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/budos"
                className="flex items-center gap-2 text-gray-600 px-8 py-4 rounded-full text-base font-medium border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all"
              >
                Zobacz Bud.OS
              </Link>
            </div>
          </motion.div>

          {/* Hero visual */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="mt-16 relative"
          >
            <div className="aspect-[16/9] max-w-4xl mx-auto rounded-2xl bg-gradient-to-br from-gray-100 to-gray-50 border border-gray-200 overflow-hidden shadow-2xl shadow-gray-200/50 flex items-center justify-center">
              <div className="text-center p-8">
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-[#1a1a2e] flex items-center justify-center">
                  <Image
                    src="/brand/01-logo-concept.png"
                    alt="YU-NA Platform"
                    width={40}
                    height={40}
                    className="rounded-lg"
                  />
                </div>
                <p className="text-sm text-gray-400 font-medium">YU-NA Intelligence Platform</p>
                <div className="mt-6 grid grid-cols-3 gap-4 max-w-md mx-auto">
                  <div className="h-20 rounded-xl bg-white border border-gray-100 shadow-sm" />
                  <div className="h-20 rounded-xl bg-white border border-gray-100 shadow-sm" />
                  <div className="h-20 rounded-xl bg-white border border-gray-100 shadow-sm" />
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ─── Features ────────────────────────────────────────────────────────── */}
      <section id="features" className="py-24 px-6 bg-white">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-[#1a1a2e]">
              Jeden ekosystem. Wiele narzędzi.
            </h2>
            <p className="mt-4 text-gray-500 text-lg max-w-2xl mx-auto">
              Każdy produkt YU-NA rozwiązuje konkretny problem. Razem tworzą przewagę.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: Target,
                title: 'Bud.OS',
                desc: 'System decyzyjny AI. Monitoring przetargów, scoring GO/NO-GO, kosztorysy KNR/ICB.',
                badge: 'Dostępny',
                badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-100',
              },
              {
                icon: Shield,
                title: 'Infra.OS',
                desc: 'Zarządzanie infrastrukturą budowlaną. Logistyka, zasoby, harmonogramy.',
                badge: 'Wkrótce',
                badgeColor: 'bg-amber-50 text-amber-700 border-amber-100',
              },
              {
                icon: Brain,
                title: 'Dev.OS',
                desc: 'Narzędzia deweloperskie. Analiza rynku nieruchomości, feasibility studies.',
                badge: 'Wkrótce',
                badgeColor: 'bg-blue-50 text-blue-700 border-blue-100',
              },
            ].map((item) => (
              <div
                key={item.title}
                className="group p-8 rounded-2xl border border-gray-100 bg-gray-50/50 hover:bg-white hover:shadow-lg hover:shadow-gray-100/80 transition-all duration-300 hover:border-gray-200"
              >
                <div className="w-12 h-12 rounded-xl bg-[#1a1a2e] flex items-center justify-center mb-5">
                  <item.icon className="w-5 h-5 text-white" />
                </div>
                <div className="flex items-center gap-3 mb-3">
                  <h3 className="text-xl font-semibold text-[#1a1a2e]">{item.title}</h3>
                  <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full border ${item.badgeColor}`}>
                    {item.badge}
                  </span>
                </div>
                <p className="text-gray-500 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Stats band ──────────────────────────────────────────────────────── */}
      <section className="py-16 px-6 border-y border-gray-100">
        <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {[
            { value: '1.4M', label: 'Przetargów w bazie' },
            { value: '67%', label: 'Avg win rate' },
            { value: '<3s', label: 'Czas analizy AI' },
            { value: '24/7', label: 'Monitoring BZP/TED' },
          ].map((s) => (
            <div key={s.label}>
              <div className="text-3xl md:text-4xl font-bold text-[#1a1a2e]">{s.value}</div>
              <div className="mt-1 text-sm text-gray-500">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── How it works ────────────────────────────────────────────────────── */}
      <section className="py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-center text-[#1a1a2e] mb-16">
            Jak to działa
          </h2>
          <div className="grid md:grid-cols-3 gap-12">
            {[
              { step: '01', icon: Zap, title: 'Połącz źródła', desc: 'BZP, TED, e-Zamówienia — automatyczny monitoring 24/7.' },
              { step: '02', icon: BarChart3, title: 'AI analizuje', desc: 'Scoring trafności, analiza ryzyka, sugerowane budżety.' },
              { step: '03', icon: Target, title: 'Podejmij decyzję', desc: 'GO/NO-GO w sekundy zamiast godzin. Pełna dokumentacja ofertowa.' },
            ].map((item) => (
              <div key={item.step} className="text-center">
                <div className="text-xs font-mono text-emerald-600 font-semibold mb-3">{item.step}</div>
                <div className="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-100 flex items-center justify-center mb-4">
                  <item.icon className="w-6 h-6 text-emerald-600" />
                </div>
                <h3 className="text-lg font-semibold text-[#1a1a2e] mb-2">{item.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── CTA ─────────────────────────────────────────────────────────────── */}
      <section className="py-24 px-6 bg-[#1a1a2e]">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
            Gotowy na przewagę?
          </h2>
          <p className="mt-4 text-gray-400 text-lg">
            Dołącz do firm, które wygrywają przetargi dzięki danym.
          </p>
          <Link
            href="/signup"
            className="mt-8 inline-flex items-center gap-2 bg-white text-[#1a1a2e] px-8 py-4 rounded-full text-base font-semibold hover:bg-gray-100 transition-colors"
          >
            Rozpocznij za darmo
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ─── Footer ──────────────────────────────────────────────────────────── */}
      <footer className="py-12 px-6 border-t border-gray-100 bg-white">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Image
              src="/brand/01-logo-concept.png"
              alt="YU-NA"
              width={24}
              height={24}
              className="rounded-md"
            />
            <span className="text-sm text-gray-500">© 2026 YU-NA Intelligence</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-gray-400">
            <Link href="/terms" className="hover:text-gray-600 transition-colors">Regulamin</Link>
            <Link href="/privacy" className="hover:text-gray-600 transition-colors">Prywatność</Link>
            <Link href="/budos" className="hover:text-gray-600 transition-colors">Bud.OS</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
