'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { motion, useScroll, useTransform, AnimatePresence } from 'motion/react';
import {
  Hexagon, ArrowRight, ChevronRight,
  Zap, Shield, BarChart3, Brain,
  Building2, Cpu, Globe, TrendingUp,
  Star, Quote, CheckCircle2,
} from 'lucide-react';

// ── Constants ──────────────────────────────────────────────────────────────────

const PRODUCTS = [
  {
    id: 'budos',
    name: 'BudOS',
    subtitle: 'Przetargi budowlane',
    status: 'available' as const,
    tagline: 'AI analizuje SWZ w 3 minuty. Scoring GO/NO-GO. Kosztorysy KNR/ICB. Pipeline ofertowy.',
    icon: 'b',
    href: '/budos',
    metrics: ['2 137 przetargów', '< 3 min analiza', '94% trafność'],
    badge: 'Dostępny teraz',
  },
  {
    id: 'next-1',
    name: '???',
    subtitle: 'Wkrótce',
    status: 'locked' as const,
    tagline: 'Nowy produkt YU-NA w przygotowaniu.',
    icon: '?',
    href: '#',
    metrics: [],
    badge: 'Q3 2026',
  },
  {
    id: 'next-2',
    name: '???',
    subtitle: 'Wkrótce',
    status: 'locked' as const,
    tagline: 'Nowy produkt YU-NA w przygotowaniu.',
    icon: '?',
    href: '#',
    metrics: [],
    badge: 'Q4 2026',
  },
];

const STATS = [
  { value: '2 137', label: 'przetargów monitorowanych' },
  { value: '< 3 min', label: 'analiza dokumentów SWZ' },
  { value: '94%', label: 'trafność decyzji GO/NO-GO' },
  { value: '23%', label: 'wyższa skuteczność ofert' },
];

const SOCIAL_PROOF = [
  { name: 'Marek W.', role: 'Dyrektor ds. Ofert, firma budowlana', quote: 'BudOS skrócił czas analizy przetargu z 2 dni do 3 godzin. Wygrywamy więcej.' },
  { name: 'Anna K.', role: 'Estimator, generalny wykonawca', quote: 'Silnik GO/NO-GO jest dokładny. Przestałam tracić czas na przetargi, które i tak przegramy.' },
  { name: 'Tomasz P.', role: 'Prezes, firma infrastrukturalna', quote: 'Kosztorysy KNR/ICB generowane automatycznie — to był game-changer dla naszego zespołu.' },
];

const LOGOS = ['BUDIMEX', 'STRABAG', 'SKANSKA', 'HOCHTIEF', 'PORR', 'ERBUD', 'UNIBEP', 'MIRBUD'];

// ── Canvas Particles ───────────────────────────────────────────────────────────

function ParticleCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    const particles: Array<{ x: number; y: number; vx: number; vy: number; size: number; alpha: number; decay: number }> = [];

    const resize = () => {
      canvas.width  = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    // spawn
    for (let i = 0; i < 60; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        size: Math.random() * 1.5 + 0.5,
        alpha: Math.random() * 0.5 + 0.1,
        decay: 0,
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // connections
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 120) {
            ctx.beginPath();
            ctx.strokeStyle = `rgba(16,185,129,${0.08 * (1 - dist / 120)})`;
            ctx.lineWidth = 0.5;
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();
          }
        }
      }

      // dots
      particles.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(16,185,129,${p.alpha})`;
        ctx.fill();
      });

      animId = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={ref}
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ opacity: 0.6 }}
    />
  );
}

// ── Navbar ─────────────────────────────────────────────────────────────────────

function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', fn, { passive: true });
    return () => window.removeEventListener('scroll', fn);
  }, []);

  return (
    <motion.nav
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={[
        'fixed top-0 inset-x-0 z-50 transition-all duration-300',
        scrolled
          ? 'glass-2 border-b border-ink-800/70 py-3'
          : 'py-5',
      ].join(' ')}
    >
      <div className="max-w-6xl mx-auto px-6 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-2.5">
          <div className="relative w-7 h-7">
            <Hexagon className="w-7 h-7 text-em" strokeWidth={1.5} />
            <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-em">
              YN
            </span>
          </div>
          <span
            className="text-sm font-bold tracking-wide text-slate-200"
            style={{ fontFamily: 'var(--font-space)' }}
          >
            YU-NA
          </span>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
          >
            Logowanie
          </Link>
          <Link
            href="/signup"
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-em text-ink-950 text-xs font-bold hover:bg-em/90 transition-all glow-em-xs"
          >
            Zacznij za darmo <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </motion.nav>
  );
}

// ── Hero ───────────────────────────────────────────────────────────────────────

function Hero() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] });
  const y = useTransform(scrollYProgress, [0, 1], [0, 120]);
  const opacity = useTransform(scrollYProgress, [0, 0.7], [1, 0]);

  return (
    <section ref={ref} className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden">
      {/* Particles */}
      <ParticleCanvas />

      {/* Radial glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[600px] rounded-full"
          style={{ background: 'radial-gradient(ellipse at center, rgba(16,185,129,0.06) 0%, transparent 65%)' }}
        />
      </div>

      <motion.div
        style={{ y, opacity }}
        className="relative z-10 text-center max-w-4xl px-6 pt-24"
      >
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-em/20 bg-em/5 text-em text-[11px] font-medium mb-8"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-em animate-pulse" />
          Platforma AI dla firm budowlanych — Premiera 2026
        </motion.div>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="text-5xl md:text-7xl font-bold tracking-tight leading-none mb-4"
          style={{ fontFamily: 'var(--font-space)' }}
        >
          <span className="text-gradient-white">Przyszłość</span>
          <br />
          <span className="text-gradient-em">biznesu budowlanego</span>
          <br />
          <span className="text-gradient-white">jest tutaj.</span>
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="text-base md:text-lg text-slate-500 max-w-xl mx-auto mt-6 leading-relaxed"
        >
          YU-NA to platforma narzędzi AI które zmieniają sposób w jaki firmy
          budowlane wygrywają przetargi, liczą koszty i zarządzają projektami.
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.35 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-10"
        >
          <Link
            href="/signup"
            className="group flex items-center gap-2 px-7 py-3.5 rounded-xl bg-em text-ink-950 font-bold text-sm hover:bg-em/90 transition-all glow-em shadow-lg shadow-em/20"
          >
            Zacznij za darmo
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
          <Link
            href="/budos"
            className="flex items-center gap-2 px-7 py-3.5 rounded-xl border border-ink-700 text-slate-300 font-medium text-sm hover:border-em/30 hover:bg-ink-900/50 transition-all"
          >
            Poznaj BudOS <ChevronRight className="w-4 h-4 text-slate-500" />
          </Link>
        </motion.div>

        {/* Social proof mini */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="flex items-center justify-center gap-2 mt-8 text-[11px] text-slate-600"
        >
          <div className="flex -space-x-1.5">
            {['M', 'A', 'T', 'P'].map((l, i) => (
              <div key={i} className="w-5 h-5 rounded-full bg-ink-700 border border-ink-600 flex items-center justify-center text-[8px] text-slate-400 font-medium">
                {l}
              </div>
            ))}
          </div>
          <span>Dołącz do 200+ firm budowlanych</span>
        </motion.div>
      </motion.div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2 }}
        className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1.5"
      >
        <span className="text-[10px] text-slate-600 tracking-wider uppercase">Przewiń</span>
        <motion.div
          animate={{ y: [0, 6, 0] }}
          transition={{ repeat: Infinity, duration: 1.5, ease: 'easeInOut' }}
          className="w-px h-6 bg-gradient-to-b from-em/40 to-transparent"
        />
      </motion.div>
    </section>
  );
}

// ── Stats bar ──────────────────────────────────────────────────────────────────

function StatsBar() {
  return (
    <section className="border-y border-ink-800/60 bg-ink-900/30">
      <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4">
        {STATS.map((s, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.08 }}
            className={[
              'flex flex-col items-center py-8 px-4',
              i < STATS.length - 1 ? 'border-r border-ink-800/60' : '',
            ].join(' ')}
          >
            <span className="text-2xl md:text-3xl font-bold font-mono text-slate-100 tabular-nums">
              {s.value}
            </span>
            <span className="text-[11px] text-slate-600 mt-1 text-center">{s.label}</span>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

// ── Products showcase ──────────────────────────────────────────────────────────

function ProductsSection() {
  return (
    <section className="px-6 py-28">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <span className="text-[11px] text-em font-medium uppercase tracking-[0.15em]">
            Ekosystem produktów
          </span>
          <h2
            className="text-3xl md:text-4xl font-bold text-slate-100 mt-3"
            style={{ fontFamily: 'var(--font-space)' }}
          >
            Narzędzia które wygrywają
          </h2>
          <p className="text-sm text-slate-500 mt-3 max-w-lg mx-auto">
            Kupujesz dostęp tylko do produktów które potrzebujesz.
            Każdy działa samodzielnie — razem tworzą przewagę konkurencyjną.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-4">
          {PRODUCTS.map((product, i) => (
            <motion.div
              key={product.id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
            >
              {product.status === 'available' ? (
                <Link
                  href={product.href}
                  className={[
                    'group block p-6 rounded-2xl border transition-all duration-300 h-full',
                    'bg-ink-900/50 border-em/20 hover:border-em/40 hover:bg-ink-900/70',
                    'card-hover',
                  ].join(' ')}
                >
                  <ProductCard product={product} />
                </Link>
              ) : (
                <div className="block p-6 rounded-2xl border border-ink-800/50 bg-ink-900/20 h-full opacity-40 cursor-not-allowed">
                  <ProductCard product={product} locked />
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ProductCard({ product, locked }: { product: typeof PRODUCTS[0]; locked?: boolean }) {
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div className="w-12 h-12 rounded-xl bg-em/10 border border-em/15 flex items-center justify-center">
          <span
            className={['text-xl font-bold', locked ? 'text-slate-600' : 'text-em'].join(' ')}
            style={{ fontFamily: 'var(--font-space)' }}
          >
            {product.icon}
          </span>
        </div>
        <span className={[
          'text-[10px] font-bold px-2 py-0.5 rounded-full border',
          product.status === 'available'
            ? 'text-go bg-go/10 border-go/25'
            : 'text-slate-600 bg-ink-800 border-ink-700',
        ].join(' ')}>
          {product.badge}
        </span>
      </div>

      {/* Name */}
      <h3
        className={['text-lg font-bold mb-0.5', locked ? 'text-slate-600' : 'text-slate-100'].join(' ')}
        style={{ fontFamily: 'var(--font-space)' }}
      >
        {product.name}
      </h3>
      <p className={['text-xs mb-3', locked ? 'text-slate-700' : 'text-em'].join(' ')}>
        {product.subtitle}
      </p>
      <p className={['text-xs leading-relaxed flex-1', locked ? 'text-slate-700' : 'text-slate-500'].join(' ')}>
        {product.tagline}
      </p>

      {/* Metrics */}
      {product.metrics.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-4">
          {product.metrics.map((m, mi) => (
            <span key={mi} className="text-[10px] text-slate-500 bg-ink-800 border border-ink-700 px-2 py-0.5 rounded-full font-mono">
              {m}
            </span>
          ))}
        </div>
      )}

      {/* CTA arrow */}
      {product.status === 'available' && (
        <div className="flex items-center gap-1 mt-5 text-xs text-em font-medium group-hover:gap-2 transition-all">
          Dowiedz się więcej <ArrowRight className="w-3 h-3" />
        </div>
      )}
    </div>
  );
}

// ── Why YU-NA ──────────────────────────────────────────────────────────────────

const WHY_ITEMS = [
  {
    icon: Brain,
    title: 'Decyzje na podstawie danych',
    desc: 'Koniec z intuicją i arkuszami Excel. AI analizuje przetarg kompleksowo — SWZ, konkurencję, ryzyko, marżę.',
  },
  {
    icon: Zap,
    title: 'Szybkość jako przewaga',
    desc: 'Twoi konkurenci wciąż analizują ręcznie. Ty masz decyzję w 3 minuty. W przetargach czas to pieniądz.',
  },
  {
    icon: Shield,
    title: 'Jedno źródło prawdy',
    desc: 'Wszystkie przetargi, wyceny, oferty i wyniki w jednym miejscu. Zero silosów, zero zgubionych plików.',
  },
  {
    icon: TrendingUp,
    title: 'Uczysz się z każdej oferty',
    desc: 'System analizuje Twoje wygrane i przegrane. Z czasem scoring staje się coraz dokładniejszy.',
  },
  {
    icon: Globe,
    title: 'BZP i TED — cały rynek',
    desc: 'Monitorujemy BZP (Polska) i TED (Europa). Żaden przetarg w Twojej niszy Cię nie ominie.',
  },
  {
    icon: Building2,
    title: 'Zbudowane dla budownictwa',
    desc: 'Kody CPV, KNR, ICB, kosztorysy budowlane — to nasz język. Nie adapetacja ogólnego narzędzia.',
  },
];

function WhySection() {
  return (
    <section className="px-6 py-24 bg-ink-900/20">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <span className="text-[11px] text-em font-medium uppercase tracking-[0.15em]">
            Dlaczego YU-NA
          </span>
          <h2
            className="text-3xl md:text-4xl font-bold text-slate-100 mt-3"
            style={{ fontFamily: 'var(--font-space)' }}
          >
            Zbudowane dla wygrywania
          </h2>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-4">
          {WHY_ITEMS.map((item, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: Math.floor(i / 3) * 0.1 + (i % 3) * 0.08 }}
              className="p-5 rounded-xl bg-ink-900/40 border border-ink-800/50 hover:border-ink-700/70 transition-colors"
            >
              <div className="w-8 h-8 rounded-lg bg-em/8 border border-em/12 flex items-center justify-center mb-4">
                <item.icon className="w-4 h-4 text-em" />
              </div>
              <h3 className="text-sm font-semibold text-slate-200 mb-1.5">{item.title}</h3>
              <p className="text-xs text-slate-500 leading-relaxed">{item.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Social proof ───────────────────────────────────────────────────────────────

function SocialProofSection() {
  return (
    <section className="px-6 py-24">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-14"
        >
          <div className="flex justify-center gap-0.5 mb-4">
            {[...Array(5)].map((_, i) => (
              <Star key={i} className="w-4 h-4 text-warn fill-warn" />
            ))}
          </div>
          <h2
            className="text-3xl font-bold text-slate-100"
            style={{ fontFamily: 'var(--font-space)' }}
          >
            Co mówią nasi klienci
          </h2>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-4">
          {SOCIAL_PROOF.map((item, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="p-6 rounded-2xl bg-ink-900/40 border border-ink-800/50"
            >
              <Quote className="w-5 h-5 text-em/40 mb-4" />
              <p className="text-sm text-slate-400 leading-relaxed mb-5 italic">
                &ldquo;{item.quote}&rdquo;
              </p>
              <div>
                <p className="text-xs font-semibold text-slate-200">{item.name}</p>
                <p className="text-[11px] text-slate-600 mt-0.5">{item.role}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Logos marquee ──────────────────────────────────────────────────────────────

function LogosSection() {
  const doubled = [...LOGOS, ...LOGOS];
  return (
    <section className="py-16 border-y border-ink-800/40 overflow-hidden">
      <p className="text-center text-[11px] text-slate-600 uppercase tracking-widest mb-8">
        Używany przez firmy takie jak
      </p>
      <div className="relative">
        <div className="flex gap-12 animate-marquee">
          {doubled.map((logo, i) => (
            <span
              key={i}
              className="text-slate-700 font-bold text-sm tracking-wider whitespace-nowrap hover:text-slate-500 transition-colors"
              style={{ fontFamily: 'var(--font-space)' }}
            >
              {logo}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── CTA ────────────────────────────────────────────────────────────────────────

function CTASection() {
  return (
    <section className="px-6 py-28">
      <div className="max-w-2xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="relative p-10 rounded-3xl border border-em/20 bg-ink-900/50 overflow-hidden animate-border-pulse"
        >
          {/* Glow */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{ background: 'radial-gradient(ellipse at 50% -20%, rgba(16,185,129,0.08) 0%, transparent 60%)' }}
          />

          <span className="text-[11px] text-em font-medium uppercase tracking-[0.15em]">
            Zacznij dziś
          </span>
          <h2
            className="text-3xl md:text-4xl font-bold text-slate-100 mt-4 mb-4"
            style={{ fontFamily: 'var(--font-space)' }}
          >
            Gotowy na przewagę?
          </h2>
          <p className="text-sm text-slate-500 mb-8 leading-relaxed">
            14 dni za darmo. Bez karty kredytowej. Anuluj w dowolnej chwili.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/signup"
              className="group flex items-center gap-2 px-8 py-3.5 rounded-xl bg-em text-ink-950 font-bold text-sm hover:bg-em/90 transition-all glow-em shadow-xl shadow-em/25"
            >
              Zacznij za darmo
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link
              href="/budos"
              className="flex items-center gap-1.5 px-6 py-3.5 rounded-xl text-sm text-slate-400 hover:text-slate-200 transition-colors"
            >
              Poznaj BudOS <ChevronRight className="w-4 h-4" />
            </Link>
          </div>

          <div className="flex items-center justify-center gap-5 mt-8">
            {['Bez zobowiązań', 'Darmowe 14 dni', 'Wsparcie PL'].map((item, i) => (
              <div key={i} className="flex items-center gap-1.5 text-[11px] text-slate-600">
                <CheckCircle2 className="w-3 h-3 text-em" />
                {item}
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// ── Footer ─────────────────────────────────────────────────────────────────────

function Footer() {
  return (
    <footer className="border-t border-ink-800/50 px-6 py-10">
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-col md:flex-row items-start justify-between gap-8">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Hexagon className="w-5 h-5 text-em" strokeWidth={1.5} />
              <span className="text-sm font-bold text-slate-300" style={{ fontFamily: 'var(--font-space)' }}>
                YU-NA
              </span>
            </div>
            <p className="text-xs text-slate-600 max-w-xs leading-relaxed">
              Platforma AI narzędzi dla firm budowlanych. Premiera 2026.
            </p>
          </div>

          {/* Links */}
          <div className="flex gap-10">
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-3">Produkty</p>
              <div className="space-y-2">
                <Link href="/budos" className="block text-xs text-slate-600 hover:text-slate-300 transition-colors">BudOS</Link>
                <span className="block text-xs text-slate-700">Wkrótce...</span>
              </div>
            </div>
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-3">Firma</p>
              <div className="space-y-2">
                <Link href="/signup" className="block text-xs text-slate-600 hover:text-slate-300 transition-colors">Rejestracja</Link>
                <Link href="/login"  className="block text-xs text-slate-600 hover:text-slate-300 transition-colors">Logowanie</Link>
              </div>
            </div>
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-3">Prawne</p>
              <div className="space-y-2">
                <Link href="/terms"   className="block text-xs text-slate-600 hover:text-slate-300 transition-colors">Regulamin</Link>
                <Link href="/privacy" className="block text-xs text-slate-600 hover:text-slate-300 transition-colors">Prywatność</Link>
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-ink-800/40 mt-8 pt-6 flex items-center justify-between">
          <p className="text-[11px] text-slate-700">
            © 2026 YU-NA. Wszelkie prawa zastrzeżone.
          </p>
          <p className="text-[11px] text-slate-700 font-mono">
            PRECYZJA · ZWIAD · PRZEWAGA
          </p>
        </div>
      </div>
    </footer>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-ink-950 overflow-x-hidden">
      <Navbar />
      <Hero />
      <StatsBar />
      <ProductsSection />
      <WhySection />
      <SocialProofSection />
      <LogosSection />
      <CTASection />
      <Footer />
    </main>
  );
}
