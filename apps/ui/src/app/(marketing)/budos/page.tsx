'use client';

import { useRef } from 'react';
import Link from 'next/link';
import { motion, useScroll, useTransform } from 'motion/react';
import {
  ArrowLeft, ArrowRight, ChevronRight, CheckCircle2,
  RefreshCw, Brain, Calculator, GitBranch,
  BarChart3, Shield, FileText, Target,
  Clock, TrendingUp, Award, Zap,
  Hexagon,
} from 'lucide-react';

// ── Data ───────────────────────────────────────────────────────────────────────

const HERO_FEATURES = [
  { icon: Brain,      label: 'Silnik GO/NO-GO' },
  { icon: RefreshCw,  label: 'BZP / TED Sync' },
  { icon: Calculator, label: 'Kosztorysy KNR/ICB' },
  { icon: GitBranch,  label: 'Pipeline Kanban' },
];

const STATS = [
  { icon: Clock,      value: '< 3 min', label: 'analiza SWZ' },
  { icon: TrendingUp, value: '94%',     label: 'trafność GO/NO-GO' },
  { icon: Award,      value: '+23%',    label: 'skuteczność ofert' },
  { icon: RefreshCw,  value: '2 137',   label: 'przetargów live' },
];

const FEATURES = [
  {
    icon: RefreshCw,
    title: 'Automatyczny BZP/TED Sync',
    desc: 'Nowe przetargi trafiają do systemu co godzinę. Zero ręcznego przeszukiwania. Filtry CPV, region, wartość.',
    tag: 'Monitorowanie',
  },
  {
    icon: Brain,
    title: 'Silnik GO/NO-GO',
    desc: 'AI czyta pełne dokumenty SWZ i ocenia opłacalność w 3 minuty. Scoring AHP, analiza ryzyka, rekomendacja.',
    tag: 'Analiza AI',
  },
  {
    icon: Calculator,
    title: 'Kosztorysy KNR/ICB',
    desc: 'Automatyczne wyceny z bazy InterCenBud. Eksport do Excel. Symulacja Monte Carlo dla marży.',
    tag: 'Wyceny',
  },
  {
    icon: GitBranch,
    title: 'Pipeline Kanban',
    desc: 'Prowadź każdy przetarg przez cały cykl życia. Drag & drop, deadliny, wartość kontraktu.',
    tag: 'Zarządzanie',
  },
  {
    icon: BarChart3,
    title: 'Raporty Win/Loss',
    desc: 'Analiza skuteczności, porównanie z konkurencją, rekomendacje poprawy marży i strategii.',
    tag: 'Analityka',
  },
  {
    icon: FileText,
    title: 'Generator Ofert',
    desc: 'Formularz ofertowy wypełniony danymi z systemu. PDF/DOCX gotowy do podpisu kwalifikowanego.',
    tag: 'Generowanie',
  },
  {
    icon: Target,
    title: 'Analiza Konkurencji',
    desc: 'Baza historycznych wyników z BZP. Kto startuje w Twoich przetargach i za ile.',
    tag: 'Wywiad',
  },
  {
    icon: Shield,
    title: 'Alerty i Powiadomienia',
    desc: 'Push/email gdy zbliża się deadline, pojawia nowy przetarg lub zmiana warunków.',
    tag: 'Alerty',
  },
];

const PRICING = [
  {
    name: 'Starter',
    price: '299',
    period: 'zł/mies.',
    desc: 'Dla pojedynczego estimatora',
    features: [
      'Do 50 przetargów/mies.',
      'Silnik GO/NO-GO',
      'BZP Sync',
      'Alerty email',
      '1 użytkownik',
    ],
    cta: 'Zacznij za darmo',
    highlight: false,
    badge: null,
  },
  {
    name: 'Pro',
    price: '799',
    period: 'zł/mies.',
    desc: 'Dla zespołu ofertowego',
    features: [
      'Nieograniczone przetargi',
      'Kosztorysy KNR/ICB',
      'Pipeline Kanban',
      'Raporty Win/Loss',
      'Generator ofert',
      'Do 5 użytkowników',
      'Priorytetowy support',
    ],
    cta: 'Wybierz Pro',
    highlight: true,
    badge: 'Najczęściej wybierany',
  },
  {
    name: 'Enterprise',
    price: 'Kontakt',
    period: '',
    desc: 'Dla firm z dużym portfolio',
    features: [
      'Wszystko z Pro',
      'Nielimitowani użytkownicy',
      'API dostęp',
      'Dedykowane wdrożenie',
      'SLA 99.9%',
      'Analiza konkurencji premium',
    ],
    cta: 'Porozmawiajmy',
    highlight: false,
    badge: null,
  },
];

const FLOW_STEPS = [
  { step: '01', title: 'Sync przetargów', desc: 'BZP i TED co godzinę. Filtry CPV, region, wartość.' },
  { step: '02', title: 'Analiza AI', desc: 'Silnik czyta SWZ, liczy scoring, rekomenduje GO lub NO-GO.' },
  { step: '03', title: 'Wycena', desc: 'Kosztorys KNR/ICB w 10 minut. Monte Carlo dla marży.' },
  { step: '04', title: 'Oferta', desc: 'Generator tworzy gotowy dokument. Podpisujesz i wysyłasz.' },
];

// ── Navbar ─────────────────────────────────────────────────────────────────────

function Navbar() {
  return (
    <nav className="fixed top-0 inset-x-0 z-50 glass-2 border-b border-ink-800/60 py-3">
      <div className="max-w-5xl mx-auto px-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center gap-1.5 text-slate-500 hover:text-slate-300 transition-colors text-xs">
            <ArrowLeft className="w-3.5 h-3.5" /> YU-NA
          </Link>
          <span className="text-slate-700">|</span>
          <div className="flex items-center gap-1.5">
            <div className="w-5 h-5 rounded-lg bg-em/10 border border-em/20 flex items-center justify-center">
              <span className="text-[9px] font-bold text-em" style={{ fontFamily: 'var(--font-space)' }}>b</span>
            </div>
            <span className="text-sm font-bold text-slate-200" style={{ fontFamily: 'var(--font-space)' }}>BudOS</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <a href="#pricing" className="text-xs text-slate-500 hover:text-slate-300 transition-colors px-3 py-2">Cennik</a>
          <Link href="/signup" className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-em text-ink-950 text-xs font-bold hover:bg-em/90 transition-all glow-em-xs">
            Zacznij za darmo <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </nav>
  );
}

// ── Hero ───────────────────────────────────────────────────────────────────────

function Hero() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] });
  const y = useTransform(scrollYProgress, [0, 1], [0, 80]);

  return (
    <section ref={ref} className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden px-6 pt-20">
      {/* Glow background */}
      <div className="absolute inset-0 pointer-events-none">
        <div
          className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px]"
          style={{ background: 'radial-gradient(ellipse at center top, rgba(16,185,129,0.10) 0%, transparent 65%)' }}
        />
      </div>

      {/* Grid lines subtle */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.025]"
        style={{
          backgroundImage: 'linear-gradient(rgba(16,185,129,0.8) 1px, transparent 1px), linear-gradient(90deg, rgba(16,185,129,0.8) 1px, transparent 1px)',
          backgroundSize: '60px 60px',
        }}
      />

      <motion.div style={{ y }} className="relative z-10 text-center max-w-3xl">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-em/20 bg-em/5 text-em text-[11px] font-medium mb-8"
        >
          <Zap className="w-3 h-3" />
          Produkt YU-NA — Dostępny teraz
        </motion.div>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="text-5xl md:text-6xl font-bold tracking-tight leading-[1.08]"
          style={{ fontFamily: 'var(--font-space)' }}
        >
          <span className="text-gradient-white">Przetargi budowlane.</span>
          <br />
          <span className="text-gradient-em">Opanowane.</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.25 }}
          className="mt-6 text-base text-slate-500 max-w-lg mx-auto leading-relaxed"
        >
          System AI który monitoruje BZP/TED, analizuje SWZ w 3 minuty,
          generuje kosztorysy i prowadzi Cię od znalezienia przetargu
          do podpisanej umowy.
        </motion.p>

        {/* Feature chips */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="flex flex-wrap items-center justify-center gap-2 mt-8"
        >
          {HERO_FEATURES.map((f, i) => (
            <span key={i} className="flex items-center gap-1.5 px-3 py-1 rounded-full border border-ink-700 bg-ink-900/50 text-xs text-slate-400">
              <f.icon className="w-3 h-3 text-em" />
              {f.label}
            </span>
          ))}
        </motion.div>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-10"
        >
          <Link
            href="/signup"
            className="group flex items-center gap-2 px-8 py-3.5 rounded-xl bg-em text-ink-950 font-bold text-sm hover:bg-em/90 transition-all glow-em shadow-lg shadow-em/20"
          >
            Zacznij za darmo
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
          <a
            href="#pricing"
            className="flex items-center gap-1.5 px-6 py-3.5 rounded-xl border border-ink-700 text-slate-300 font-medium text-sm hover:border-em/30 hover:bg-ink-900/40 transition-all"
          >
            Cennik <ChevronRight className="w-4 h-4 text-slate-500" />
          </a>
        </motion.div>

        {/* Trust */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.65 }}
          className="text-[11px] text-slate-700 mt-6"
        >
          14 dni za darmo · Bez karty kredytowej · Anuluj kiedy chcesz
        </motion.p>
      </motion.div>

      {/* Scroll nudge */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
        className="absolute bottom-10 left-1/2 -translate-x-1/2"
      >
        <motion.div
          animate={{ y: [0, 6, 0] }}
          transition={{ repeat: Infinity, duration: 1.5 }}
          className="w-px h-8 bg-gradient-to-b from-em/40 to-transparent mx-auto"
        />
      </motion.div>
    </section>
  );
}

// ── Stats ──────────────────────────────────────────────────────────────────────

function StatsSection() {
  return (
    <section className="border-y border-ink-800/50">
      <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4">
        {STATS.map((s, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.07 }}
            className={['flex flex-col items-center py-10', i < 3 ? 'border-r border-ink-800/50' : ''].join(' ')}
          >
            <s.icon className="w-4 h-4 text-em mb-3" />
            <span className="text-2xl md:text-3xl font-bold text-slate-100 font-mono tabular-nums">{s.value}</span>
            <span className="text-[11px] text-slate-600 mt-1">{s.label}</span>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

// ── How it works ───────────────────────────────────────────────────────────────

function HowItWorksSection() {
  return (
    <section className="px-6 py-28">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <span className="text-[11px] text-em font-medium uppercase tracking-[0.15em]">Jak to działa</span>
          <h2 className="text-3xl md:text-4xl font-bold text-slate-100 mt-3" style={{ fontFamily: 'var(--font-space)' }}>
            Od przetargu do umowy
          </h2>
          <p className="text-sm text-slate-500 mt-3">Cztery kroki. Jeden system.</p>
        </motion.div>

        {/* Flow */}
        <div className="relative">
          {/* Connecting line */}
          <div className="hidden md:block absolute top-8 left-[12.5%] right-[12.5%] h-px bg-gradient-to-r from-transparent via-em/20 to-transparent" />

          <div className="grid md:grid-cols-4 gap-6">
            {FLOW_STEPS.map((step, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="flex flex-col items-center text-center"
              >
                <div className="relative w-16 h-16 rounded-2xl bg-ink-900 border border-ink-700 flex items-center justify-center mb-4 glow-em-xs">
                  <span className="text-2xl font-bold text-em/20 font-mono absolute">{step.step}</span>
                  <span className="text-xs font-bold text-em relative z-10 font-mono">{step.step}</span>
                </div>
                <h3 className="text-sm font-semibold text-slate-200 mb-1" style={{ fontFamily: 'var(--font-space)' }}>
                  {step.title}
                </h3>
                <p className="text-xs text-slate-600 leading-relaxed">{step.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Features ───────────────────────────────────────────────────────────────────

function FeaturesSection() {
  return (
    <section className="px-6 py-24 bg-ink-900/15">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <span className="text-[11px] text-em font-medium uppercase tracking-[0.15em]">Funkcje</span>
          <h2 className="text-3xl md:text-4xl font-bold text-slate-100 mt-3" style={{ fontFamily: 'var(--font-space)' }}>
            Kompletny arsenał
          </h2>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-3">
          {FEATURES.map((f, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: (i % 2) * 0.08 }}
              className="flex gap-4 p-5 rounded-xl bg-ink-900/40 border border-ink-800/50 hover:border-ink-700/70 transition-colors card-hover"
            >
              <div className="w-9 h-9 rounded-lg bg-em/8 border border-em/12 flex items-center justify-center shrink-0">
                <f.icon className="w-4 h-4 text-em" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-sm font-semibold text-slate-200">{f.title}</h3>
                  <span className="text-[9px] font-medium text-em/60 bg-em/6 border border-em/12 px-1.5 py-0.5 rounded-full">
                    {f.tag}
                  </span>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">{f.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Pricing ────────────────────────────────────────────────────────────────────

function PricingSection() {
  return (
    <section id="pricing" className="px-6 py-28 scroll-mt-16">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <span className="text-[11px] text-em font-medium uppercase tracking-[0.15em]">Cennik</span>
          <h2 className="text-3xl md:text-4xl font-bold text-slate-100 mt-3" style={{ fontFamily: 'var(--font-space)' }}>
            Prosty i transparentny
          </h2>
          <p className="text-sm text-slate-500 mt-3">Bez ukrytych opłat. Anuluj kiedy chcesz.</p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-4">
          {PRICING.map((plan, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className={[
                'relative p-6 rounded-2xl border flex flex-col',
                plan.highlight
                  ? 'bg-ink-900/70 border-em/30 ring-1 ring-em/10 animate-glow-pulse'
                  : 'bg-ink-900/30 border-ink-800/50',
              ].join(' ')}
            >
              {plan.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="text-[10px] font-bold text-ink-950 bg-em px-3 py-1 rounded-full whitespace-nowrap">
                    {plan.badge}
                  </span>
                </div>
              )}

              <h3 className="text-lg font-bold text-slate-100 mb-0.5" style={{ fontFamily: 'var(--font-space)' }}>
                {plan.name}
              </h3>
              <p className="text-xs text-slate-600 mb-5">{plan.desc}</p>

              <div className="mb-6">
                <span className="text-4xl font-bold text-slate-100 font-mono">{plan.price}</span>
                {plan.period && <span className="text-sm text-slate-500 ml-1">{plan.period}</span>}
              </div>

              <ul className="space-y-2.5 mb-8 flex-1">
                {plan.features.map((f, fi) => (
                  <li key={fi} className="flex items-start gap-2 text-xs text-slate-400">
                    <CheckCircle2 className="w-3.5 h-3.5 text-em shrink-0 mt-0.5" />
                    {f}
                  </li>
                ))}
              </ul>

              <Link
                href="/signup"
                className={[
                  'w-full text-center py-3 rounded-xl text-sm font-bold transition-all',
                  plan.highlight
                    ? 'bg-em text-ink-950 hover:bg-em/90 shadow-lg shadow-em/20'
                    : 'border border-ink-700 text-slate-300 hover:border-em/25 hover:bg-ink-900/50',
                ].join(' ')}
              >
                {plan.cta}
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── CTA ────────────────────────────────────────────────────────────────────────

function CTASection() {
  return (
    <section className="px-6 py-20 border-t border-ink-800/40">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="max-w-2xl mx-auto text-center"
      >
        <h2 className="text-3xl font-bold text-slate-100 mb-4" style={{ fontFamily: 'var(--font-space)' }}>
          Wygrywaj więcej przetargów.
        </h2>
        <p className="text-sm text-slate-500 mb-8">
          14 dni za darmo. Bez karty kredytowej.
        </p>
        <Link
          href="/signup"
          className="group inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-em text-ink-950 font-bold text-sm hover:bg-em/90 transition-all glow-em shadow-xl shadow-em/25"
        >
          Zacznij za darmo
          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </Link>
      </motion.div>
    </section>
  );
}

// ── Footer ─────────────────────────────────────────────────────────────────────

function Footer() {
  return (
    <footer className="border-t border-ink-800/40 px-6 py-8">
      <div className="max-w-5xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Hexagon className="w-4 h-4 text-em/60" strokeWidth={1.5} />
          <span className="text-xs text-slate-600" style={{ fontFamily: 'var(--font-space)' }}>
            YU-NA / <span className="text-slate-500">BudOS</span>
          </span>
        </div>
        <div className="flex gap-5 text-[11px] text-slate-700">
          <Link href="/"        className="hover:text-slate-400 transition-colors">Platforma</Link>
          <Link href="/terms"   className="hover:text-slate-400 transition-colors">Regulamin</Link>
          <Link href="/privacy" className="hover:text-slate-400 transition-colors">Prywatność</Link>
        </div>
      </div>
    </footer>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function BudosProductPage() {
  return (
    <main className="min-h-screen bg-ink-950 overflow-x-hidden">
      <Navbar />
      <Hero />
      <StatsSection />
      <HowItWorksSection />
      <FeaturesSection />
      <PricingSection />
      <CTASection />
      <Footer />
    </main>
  );
}
