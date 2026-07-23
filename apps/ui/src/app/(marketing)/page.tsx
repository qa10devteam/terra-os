'use client';
/* YU-NA Landing v5 — Faza 2+3: Mobile Responsiveness, Scroll Reveals, Micro-interactions
 * Hero: 58/42 split with live DataPanel
 * Products: BudOS (featured), + "Stay Tuned" upcoming
 * Tone: szeroki, ambicja, market edge
 */

import Link from 'next/link';
import Image from 'next/image';
import { motion, useReducedMotion } from 'motion/react';
import { useState, useEffect, useRef } from 'react';

// ── TOKEN SYSTEM ──────────────────────────────────────────────────────────────
const T = {
  bg0:        '#f7f9fc',
  bg1:        '#ffffff',
  bg2:        '#f0f3f8',
  bg3:        '#e8ecf3',
  edge0:      '#dde3ec',
  edge1:      '#c8d0dd',
  ink:        '#0c1524',
  muted:      '#5a6d84',
  faint:      '#8fa0b4',
  accent:     '#16c984',
  accentDim:  '#0d7a4f',
  accentSub:  'rgba(22,201,132,0.08)',
  accentBrd:  'rgba(22,201,132,0.25)',
  data:       '#2c3e52',
  amber:      '#f59e0b',
  blue:       '#60a5fa',
  serif:      'var(--font-dm-serif)',
  sans:       'var(--font-space)',
  mono:       'var(--font-jetbrains)',
} as const;

// ── FROZEN MOCK DATA ──────────────────────────────────────────────────────────
const TENDER_MOCK = [
  { id: 'WR/2026/0041', title: 'Rozbudowa drogi gminnej nr 104', budget: '2.4M', score: 87, go: true,  cat: 'Drogi'      },
  { id: 'GD/2026/0289', title: 'Budowa przedszkola Gdańsk',      budget: '8.1M', score: 72, go: true,  cat: 'Kubatura'   },
  { id: 'KR/2026/1102', title: 'Remont siedziby ZUS Kraków',     budget: '1.2M', score: 51, go: false, cat: 'Remonty'    },
  { id: 'WA/2026/0773', title: 'Modernizacja sieci wod-kan',     budget: '5.7M', score: 91, go: true,  cat: 'Instalacje' },
  { id: 'PO/2026/0156', title: 'Hala sportowa MOSiR Poznań',     budget: '12.3M',score: 65, go: true,  cat: 'Kubatura'   },
  { id: 'LU/2026/0387', title: 'Termomodernizacja SP nr 3',      budget: '3.1M', score: 78, go: true,  cat: 'Remonty'    },
] as const;

// ── ANIMATED COUNTER ──────────────────────────────────────────────────────────
function Counter({ to, suffix = '', fast }: { to: number; suffix?: string; fast?: boolean }) {
  const [val, setVal] = useState(0);
  const started = useRef(false);
  const ref = useRef<HTMLSpanElement>(null);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting && !started.current) {
        started.current = true;
        if (reduceMotion) { setVal(to); return; }
        const dur = fast ? 800 : 1400;
        const startTime = performance.now();
        const tick = (now: number) => {
          const t = Math.min((now - startTime) / dur, 1);
          const ease = 1 - Math.pow(1 - t, 3);
          setVal(Math.round(ease * to));
          if (t < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      }
    }, { threshold: 0.3 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [to, fast, reduceMotion]);

  return <span ref={ref}>{val.toLocaleString('pl-PL')}{suffix}</span>;
}

// ── SCORE BADGE ───────────────────────────────────────────────────────────────
function ScoreBadge({ score, go }: { score: number; go: boolean }) {
  const color  = go ? T.accent : T.amber;
  const bg     = go ? T.accentSub : 'rgba(245,158,11,0.08)';
  const border = go ? T.accentBrd : 'rgba(245,158,11,0.2)';
  return (
    <span
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        background: bg, border: `1px solid ${border}`,
        borderRadius: 8, padding: '3px 8px',
        fontFamily: T.mono, fontSize: 11, fontWeight: 700, color,
        transition: 'transform 0.15s',
        cursor: 'default',
        flexShrink: 0,
      }}
      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(1.08)'; }}
      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = ''; }}
    >
      {score}
      <span style={{ fontSize: 9, opacity: 0.7 }}>{go ? '↑GO' : 'NO'}</span>
    </span>
  );
}

// ── DATA PANEL ────────────────────────────────────────────────────────────────
function DataPanel() {
  return (
    <div style={{
      background: T.bg1,
      border: `1px solid ${T.edge0}`,
      borderRadius: 20,
      overflow: 'hidden',
      boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 4px 16px rgba(0,0,0,0.06), 0 16px 48px rgba(0,0,0,0.08)',
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 18px',
        borderBottom: `1px solid ${T.edge0}`,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: T.bg0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            width: 7, height: 7, borderRadius: '50%',
            background: T.accent,
            display: 'block',
            animation: 'blink 1.5s infinite',
          }} />
          <span style={{ fontFamily: T.mono, fontSize: 10, fontWeight: 700, color: T.ink, letterSpacing: '0.08em' }}>
            AKTYWNE PRZETARGI
          </span>
        </div>
        <span style={{ fontFamily: T.mono, fontSize: 10, color: T.faint }}>
          {TENDER_MOCK.length} wyników
        </span>
      </div>

      {/* Tender rows */}
      <div className="data-panel-scroll">
        {TENDER_MOCK.map((t) => (
          <div
            key={t.id}
            style={{
              padding: '11px 18px',
              borderBottom: `1px solid ${T.edge0}`,
              display: 'flex', alignItems: 'flex-start', gap: 10,
              transition: 'background 0.15s, transform 0.15s',
              cursor: 'pointer',
            }}
            onMouseEnter={e => {
              const el = e.currentTarget as HTMLElement;
              el.style.background = T.bg2;
              el.style.transform = 'translateX(4px)';
            }}
            onMouseLeave={e => {
              const el = e.currentTarget as HTMLElement;
              el.style.background = '';
              el.style.transform = '';
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontFamily: T.mono, fontSize: 10, color: T.faint, marginBottom: 3 }}>{t.id}</div>
              <div style={{
                fontFamily: T.sans, fontSize: 12, fontWeight: 600, color: T.ink,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>{t.title}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                <span style={{ fontFamily: T.mono, fontSize: 11, color: T.muted }}>{t.budget} PLN</span>
                <span style={{
                  fontFamily: T.sans, fontSize: 9, color: T.faint,
                  background: T.bg2, borderRadius: 4, padding: '1px 5px',
                }}>{t.cat}</span>
              </div>
            </div>
            <ScoreBadge score={t.score} go={t.go} />
          </div>
        ))}
      </div>

      {/* Footer */}
      <div style={{
        padding: '10px 18px',
        background: T.bg0,
        display: 'flex', alignItems: 'center', gap: 6,
      }}>
        <span style={{
          width: 5, height: 5, borderRadius: '50%',
          background: T.accent, display: 'block',
          animation: 'blink 1.5s infinite',
        }} />
        <span style={{ fontFamily: T.mono, fontSize: 10, color: T.faint }}>
          Dane aktualne · BZP/TED · odświeżane co 15 min
        </span>
      </div>
    </div>
  );
}

// ── NAV ───────────────────────────────────────────────────────────────────────
function Nav() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const h = () => setScrolled(window.scrollY > 24);
    window.addEventListener('scroll', h, { passive: true });
    return () => window.removeEventListener('scroll', h);
  }, []);

  return (
    <nav className="nav-pill" style={{
      position: 'fixed', top: 20, left: '50%', transform: 'translateX(-50%)',
      zIndex: 100, display: 'flex', alignItems: 'center',
      gap: 0,
      background: scrolled ? 'rgba(255,255,255,0.92)' : 'rgba(255,255,255,0.80)',
      backdropFilter: 'blur(20px)',
      border: `1px solid ${scrolled ? T.edge0 : 'rgba(221,227,236,0.6)'}`,
      borderRadius: 999, padding: '8px 10px 8px 20px',
      boxShadow: scrolled ? '0 4px 24px rgba(12,21,36,0.09)' : '0 2px 12px rgba(12,21,36,0.05)',
      transition: 'all 0.3s ease',
      whiteSpace: 'nowrap',
    }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 32 }}>
        <Image src="/brand/01-logo-concept.png" alt="YU-NA" width={22} height={22} style={{ borderRadius: 6 }} />
        <span style={{ fontFamily: T.sans, fontWeight: 700, fontSize: 14, color: T.ink, letterSpacing: '-0.02em' }}>
          YU-NA
        </span>
      </div>

      {/* Links — hidden on mobile via CSS */}
      <div className="nav-links">
        {[
          { label: 'BudOS', href: '/budos' },
          { label: 'O platformie', href: '#platforma' },
        ].map(l => (
          <Link key={l.label} href={l.href} style={{
            fontFamily: T.sans, fontSize: 13, color: T.muted, fontWeight: 500,
            padding: '6px 14px', borderRadius: 999,
            transition: 'color 0.15s',
            textDecoration: 'none',
          }}
            onMouseEnter={e => (e.currentTarget.style.color = T.ink)}
            onMouseLeave={e => (e.currentTarget.style.color = T.muted)}
          >
            {l.label}
          </Link>
        ))}
      </div>

      {/* CTA */}
      <Link href="/signup" style={{
        marginLeft: 8,
        display: 'inline-flex', alignItems: 'center', gap: 6,
        background: T.ink, color: '#fff',
        fontFamily: T.sans, fontSize: 13, fontWeight: 700,
        padding: '9px 20px', borderRadius: 999,
        textDecoration: 'none',
        transition: 'background 0.2s',
      }}
        onMouseEnter={e => (e.currentTarget.style.background = '#1a2d47')}
        onMouseLeave={e => (e.currentTarget.style.background = T.ink)}
      >
        Zacznij
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M2 6h8M7 3l3 3-3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </Link>
    </nav>
  );
}

// ── HERO ──────────────────────────────────────────────────────────────────────
function Hero({ reduce }: { reduce: boolean | null }) {
  return (
    <section style={{
      minHeight: '100vh',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      padding: '120px 24px 80px',
      position: 'relative',
    }}>
      {/* Subtle radial bg */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: 'radial-gradient(ellipse 70% 50% at 50% 20%, rgba(22,201,132,0.055) 0%, transparent 70%)',
      }} />

      {/* 58/42 split */}
      <div className="hero-grid" style={{
        display: 'flex', flexDirection: 'row', gap: 48,
        maxWidth: 1100, width: '100%', position: 'relative',
        alignItems: 'center',
      }}>
        {/* Left — 58% */}
        <div className="hero-left" style={{ flex: '0 0 58%', maxWidth: '58%' }}>
          {/* Eyebrow */}
          <motion.div
            initial={reduce ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              background: T.accentSub,
              border: `1px solid ${T.accentBrd}`,
              borderRadius: 999, padding: '5px 14px',
              marginBottom: 32,
            }}
          >
            <span style={{
              width: 6, height: 6, borderRadius: '50%',
              background: T.accent,
              boxShadow: `0 0 8px ${T.accent}`,
              display: 'block',
              animation: 'pulse 2s ease-in-out infinite',
            }} />
            <span style={{ fontFamily: T.mono, fontSize: 11, fontWeight: 600, color: T.accent, letterSpacing: '0.1em' }}>
              MARKET INTELLIGENCE PLATFORM
            </span>
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={reduce ? false : { opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.08, ease: [0.16, 1, 0.3, 1] }}
            style={{
              fontFamily: T.serif,
              fontSize: 'clamp(36px, 4.5vw, 56px)',
              fontWeight: 400,
              color: T.ink,
              lineHeight: 1.08,
              letterSpacing: '-0.02em',
              maxWidth: 560,
              marginBottom: 24,
            }}
          >
            Dane, które dają<br />
            <em style={{ fontStyle: 'italic', color: T.accent }}>przewagę.</em>
          </motion.h1>

          {/* Subline */}
          <motion.p
            initial={reduce ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.2 }}
            style={{
              fontFamily: T.sans, fontSize: 17, color: T.muted,
              maxWidth: 480, lineHeight: 1.65,
              marginBottom: 40,
            }}
          >
            YU-NA to platforma intelligence, która zamienia surowe dane rynkowe
            w konkretne decyzje biznesowe — szybciej niż konkurencja.
          </motion.p>

          {/* CTAs */}
          <motion.div
            initial={reduce ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.32 }}
            style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}
          >
            <Link href="/budos" style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              background: T.accent, color: T.bg1,
              fontFamily: T.sans, fontSize: 15, fontWeight: 700,
              padding: '14px 32px', borderRadius: 999,
              textDecoration: 'none',
              boxShadow: `0 4px 24px rgba(22,201,132,0.28)`,
              transition: 'all 0.2s',
            }}
              onMouseEnter={e => {
                e.currentTarget.style.transform = 'scale(1.02)';
                e.currentTarget.style.boxShadow = `0 8px 32px rgba(22,201,132,0.36)`;
              }}
              onMouseLeave={e => {
                e.currentTarget.style.transform = '';
                e.currentTarget.style.boxShadow = `0 4px 24px rgba(22,201,132,0.28)`;
              }}
            >
              Odkryj BudOS
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </Link>
            <Link href="/budos" style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              border: `1.5px solid ${T.edge1}`, color: T.muted,
              fontFamily: T.sans, fontSize: 15, fontWeight: 500,
              padding: '13px 28px', borderRadius: 999,
              textDecoration: 'none', background: T.bg1,
              transition: 'all 0.2s',
            }}
              onMouseEnter={e => {
                e.currentTarget.style.background = T.accentSub;
                e.currentTarget.style.borderColor = T.accentBrd;
                e.currentTarget.style.color = T.ink;
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = T.bg1;
                e.currentTarget.style.borderColor = T.edge1;
                e.currentTarget.style.color = T.muted;
              }}
            >
              Poznaj Bud.OS
            </Link>
          </motion.div>
        </div>

        {/* Right — 42% DataPanel */}
        <motion.div
          className="hero-right"
          initial={reduce ? false : { opacity: 0, x: 24 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.7, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          style={{ flex: '0 0 42%', maxWidth: '42%' }}
        >
          <DataPanel />
        </motion.div>
      </div>
    </section>
  );
}

// ── STAT STRIP SECTION ────────────────────────────────────────────────────────
function StatStripSection({ reduce }: { reduce: boolean | null }) {
  return (
    <section style={{ padding: '0 24px 64px', background: T.bg0 }}>
      <motion.div
        initial={reduce ? false : { opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.2 }}
        transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="stat-strip-grid" style={{
          maxWidth: 1100, margin: '0 auto',
          display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
          background: T.bg1, border: `1px solid ${T.edge0}`,
          borderRadius: 20, overflow: 'hidden',
          boxShadow: '0 2px 16px rgba(12,21,36,0.05)',
        }}>
          {[
            { value: 1626,    suffix: '',   label: 'nowych przetargów w tygodniu', fast: true  },
            { value: 9913,    suffix: '',   label: 'zamawiających w bazie',        fast: true  },
            { value: 1400000, suffix: '+',  label: 'ogłoszeń przeanalizowanych',   fast: false },
            { value: 30,      suffix: 's',  label: 'czas analizy SWZ',             fast: false },
          ].map((s, i) => (
            <div key={i} style={{
              padding: '24px 32px',
              borderRight: i < 3 ? `1px solid ${T.edge0}` : undefined,
              textAlign: 'center',
            }}>
              <div style={{ fontFamily: T.mono, fontSize: 28, fontWeight: 700, color: T.ink, letterSpacing: '-0.03em' }}>
                <Counter to={s.value} suffix={s.suffix} fast={s.fast} />
              </div>
              <div style={{ fontFamily: T.sans, fontSize: 11, color: T.faint, marginTop: 4, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </motion.div>
    </section>
  );
}

// ── PLATFORM SECTION ──────────────────────────────────────────────────────────
function PlatformSection({ reduce }: { reduce: boolean | null }) {
  return (
    <section id="platforma" style={{
      padding: 'clamp(40px, 5vw, 64px) 24px',
      borderTop: `1px solid ${T.edge0}`,
      background: T.bg1,
    }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>

        {/* Header */}
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
          style={{ textAlign: 'center', marginBottom: 60 }}
        >
          <p style={{ fontFamily: T.mono, fontSize: 11, letterSpacing: '0.12em', color: T.accent, fontWeight: 600, textTransform: 'uppercase', marginBottom: 20 }}>
            Jak działa YU-NA
          </p>
          <h2 style={{ fontFamily: T.serif, fontSize: 'clamp(28px, 3vw, 40px)', color: T.ink, lineHeight: 1.1, letterSpacing: '-0.02em', marginBottom: 20 }}>
            Dane rynkowe → decyzja<br />w minutach, nie tygodniach.
          </h2>
          <p style={{ fontFamily: T.sans, fontSize: 17, color: T.muted, maxWidth: 520, margin: '0 auto', lineHeight: 1.65 }}>
            Zbieramy, filtrujemy i analizujemy dane z setek źródeł. Dostarczamy gotową inteligencję — dopasowaną do konkretnej branży i konkretnej decyzji.
          </p>
        </motion.div>

        {/* 3-column steps */}
        <div className="steps-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}>
          {[
            {
              icon: (
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
                </svg>
              ),
              title: 'Zbieranie danych',
              desc: 'Automatyczny monitoring dziesiątek źródeł — przetargi, ogłoszenia, raporty rynkowe, dane rejestrowe. Zero ręcznej pracy.',
            },
            {
              icon: (
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 20V10M18 20V4M6 20v-4"/>
                </svg>
              ),
              title: 'Analiza AI',
              desc: 'Modele wyuczone na specyfice branży. Scoring, klasyfikacja, ekstrakcja sygnałów — kontekst którego generyczne LLM nie rozumieją.',
            },
            {
              icon: (
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>
                </svg>
              ),
              title: 'Gotowa decyzja',
              desc: 'Nie "dashboard z wykresami" — konkretna rekomendacja. GO/NO-GO, wycena, profil ryzyka. Działaj, nie analizuj.',
            },
          ].map((f, i) => (
            <motion.div
              key={i}
              initial={reduce ? false : { opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.45, delay: i * 0.1, ease: [0.16, 1, 0.3, 1] }}
              style={{
                background: T.bg0,
                border: `1px solid ${T.edge0}`,
                borderRadius: 20, padding: '36px 32px',
              }}
            >
              <div style={{
                width: 48, height: 48, borderRadius: 14,
                background: T.accentSub, border: `1px solid ${T.accentBrd}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: T.accent, marginBottom: 24,
              }}>
                {f.icon}
              </div>
              <h3 style={{ fontFamily: T.sans, fontSize: 17, fontWeight: 700, color: T.ink, marginBottom: 12, letterSpacing: '-0.015em' }}>
                {f.title}
              </h3>
              <p style={{ fontFamily: T.sans, fontSize: 14, color: T.muted, lineHeight: 1.7 }}>
                {f.desc}
              </p>
            </motion.div>
          ))}
        </div>

      </div>
    </section>
  );
}

// ── DLA KOGO? ─────────────────────────────────────────────────────────────────
function DlaKogoSection({ reduce }: { reduce: boolean | null }) {
  return (
    <section style={{
      padding: 'clamp(40px, 5vw, 64px) 24px',
      borderTop: `1px solid ${T.edge0}`,
      background: T.bg0,
    }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        >
          <h2 style={{
            fontFamily: T.serif,
            fontSize: 'clamp(28px, 3vw, 40px)',
            color: T.ink, lineHeight: 1.1,
            letterSpacing: '-0.02em',
            marginBottom: 32, textAlign: 'center',
          }}>
            Dla kogo?
          </h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, justifyContent: 'center' }}>
            {[
              {
                icon: (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/><path d="M2 12h20"/>
                  </svg>
                ),
                label: 'Właściciel firmy budowlanej',
              },
              {
                icon: (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-5 0v-15A2.5 2.5 0 0 1 9.5 2z"/><path d="M14.5 8A2.5 2.5 0 0 1 17 10.5v9a2.5 2.5 0 0 1-5 0v-9A2.5 2.5 0 0 1 14.5 8z"/>
                  </svg>
                ),
                label: 'Dyrektor przetargów',
              },
              {
                icon: (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="4" y="2" width="16" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><line x1="8" y1="10" x2="16" y2="10"/><line x1="8" y1="14" x2="12" y2="14"/>
                  </svg>
                ),
                label: 'Kosztorysant',
              },
            ].map((p) => (
              <div key={p.label} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                border: `1px solid ${T.edge0}`,
                borderRadius: 999,
                paddingTop: 12, paddingBottom: 12,
                paddingLeft: 24, paddingRight: 24,
                background: T.bg1,
                fontFamily: T.sans, fontSize: 14, fontWeight: 500, color: T.ink,
                cursor: 'default',
              }}>
                <span style={{ color: T.accent, display: 'flex' }}>{p.icon}</span>
                {p.label}
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// ── PRODUCTS SECTION ──────────────────────────────────────────────────────────
function ProductsSection({ reduce }: { reduce: boolean | null }) {
  return (
    <section style={{ padding: 'clamp(40px, 5vw, 64px) 24px', borderTop: `1px solid ${T.edge0}` }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>

        <motion.div
          initial={reduce ? false : { opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
          style={{ marginBottom: 48 }}
        >
          <p style={{ fontFamily: T.mono, fontSize: 11, letterSpacing: '0.12em', color: T.accent, fontWeight: 600, textTransform: 'uppercase', marginBottom: 16 }}>
            Produkty
          </p>
          <h2 style={{ fontFamily: T.serif, fontSize: 'clamp(28px, 3vw, 40px)', color: T.ink, lineHeight: 1.1, letterSpacing: '-0.02em' }}>
            Jeden ekosystem.<br />Wiele rynków.
          </h2>
        </motion.div>

        {/* BudOS — featured, full width */}
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          style={{ marginBottom: 20 }}
        >
          <Link href="/budos" className="budos-card" style={{
            display: 'grid', gridTemplateColumns: '1fr 1fr',
            background: T.ink, borderRadius: 24, overflow: 'hidden',
            textDecoration: 'none', position: 'relative',
            boxShadow: '0 8px 48px rgba(12,21,36,0.14)',
            transition: 'box-shadow 0.3s',
          }}
            onMouseEnter={e => (e.currentTarget.style.boxShadow = '0 16px 64px rgba(12,21,36,0.22)')}
            onMouseLeave={e => (e.currentTarget.style.boxShadow = '0 8px 48px rgba(12,21,36,0.14)')}
          >
            {/* Left — copy */}
            <div style={{ padding: '56px 56px 56px 56px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                {/* Badge */}
                <div style={{
                  display: 'inline-flex', alignItems: 'center', gap: 8,
                  background: T.accentSub, border: `1px solid ${T.accentBrd}`,
                  borderRadius: 999, padding: '5px 14px', marginBottom: 32,
                }}>
                  <span style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: T.accent, display: 'block',
                    animation: 'blink 1.5s infinite',
                  }} />
                  <span style={{ fontFamily: T.mono, fontSize: 10, fontWeight: 700, color: T.accent, letterSpacing: '0.12em' }}>PRODUKT #1 · LIVE</span>
                </div>

                <h3 style={{ fontFamily: T.serif, fontSize: 'clamp(36px, 3.5vw, 52px)', color: '#ffffff', lineHeight: 1.08, letterSpacing: '-0.025em', marginBottom: 20 }}>
                  BudOS
                </h3>
                <p style={{ fontFamily: T.sans, fontSize: 16, color: 'rgba(255,255,255,0.5)', lineHeight: 1.7, maxWidth: '38ch', marginBottom: 40 }}>
                  Intelligence dla rynku zamówień publicznych. Monitoring BZP/TED, analiza SWZ, scoring GO/NO-GO, kosztorys AI — od ogłoszenia do oferty.
                </p>

                {/* Key stats */}
                <div style={{ display: 'flex', gap: 32 }}>
                  {[
                    { v: '1.4M', l: 'ogłoszeń' },
                    { v: '30s', l: 'analiza SWZ' },
                    { v: 'KNR/ICB', l: 'kosztorys' },
                  ].map((s, i) => (
                    <div key={i}>
                      <div style={{ fontFamily: T.mono, fontSize: 22, fontWeight: 700, color: '#fff', letterSpacing: '-0.02em' }}>{s.v}</div>
                      <div style={{ fontFamily: T.sans, fontSize: 11, color: 'rgba(255,255,255,0.3)', marginTop: 3, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{s.l}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* CTA */}
              <div style={{
                marginTop: 48,
                display: 'inline-flex', alignItems: 'center', gap: 8,
                color: T.accent, fontFamily: T.sans, fontSize: 14, fontWeight: 700,
                letterSpacing: '-0.01em',
              }}>
                Odkryj BudOS
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
            </div>

            {/* Right — screenshot with hover scale */}
            <div className="budos-screenshot" style={{ position: 'relative', overflow: 'hidden', transition: 'transform 0.3s ease' }}>
              {/* Ambient glow */}
              <div style={{
                position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, pointerEvents: 'none',
                background: 'radial-gradient(ellipse at 30% 20%, rgba(22,201,132,0.12) 0%, transparent 60%)',
              }} />
              {/* Browser bar */}
              <div style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '12px 16px',
                background: 'rgba(255,255,255,0.04)',
                borderBottom: '1px solid rgba(255,255,255,0.07)',
              }}>
                <span style={{ width: 9, height: 9, borderRadius: '50%', background: 'rgba(255,59,48,0.45)', display: 'block' }} />
                <span style={{ width: 9, height: 9, borderRadius: '50%', background: 'rgba(255,159,10,0.45)', display: 'block' }} />
                <span style={{ width: 9, height: 9, borderRadius: '50%', background: 'rgba(40,205,65,0.45)', display: 'block' }} />
                <div style={{
                  flex: 1, marginLeft: 8, height: 18, borderRadius: 4,
                  background: 'rgba(255,255,255,0.06)',
                  display: 'flex', alignItems: 'center', paddingLeft: 10,
                }}>
                  <span style={{ fontFamily: T.mono, fontSize: 10, color: 'rgba(255,255,255,0.25)' }}>app.yu-na.io/zwiad</span>
                </div>
              </div>
              <Image
                src="/brand/live-dashboard.png"
                alt="BudOS dashboard"
                width={720}
                height={480}
                style={{ width: '100%', height: 'auto', display: 'block' }}
              />
            </div>
          </Link>
        </motion.div>

        {/* Coming soon grid — 2 teaser cards */}
        <div className="bento-coming" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          {[
            {
              label: 'Wkrótce',
              title: 'Projekt #2',
              desc: 'Nowy rynek. Nowe dane. Ta sama przewaga.',
              accent: T.amber,
              accentSub: 'rgba(245,158,11,0.07)',
              accentBrd: 'rgba(245,158,11,0.2)',
            },
            {
              label: 'Wkrótce',
              title: 'Projekt #3',
              desc: 'Stay tuned.',
              accent: T.blue,
              accentSub: 'rgba(96,165,250,0.07)',
              accentBrd: 'rgba(96,165,250,0.2)',
            },
          ].map((p, i) => (
            <motion.div
              key={i}
              initial={reduce ? false : { opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.45, delay: i * 0.1, ease: [0.16, 1, 0.3, 1] }}
              style={{
                background: T.bg0,
                border: `1.5px solid ${T.edge0}`,
                borderRadius: 20, padding: '40px 36px',
                display: 'flex', flexDirection: 'column', gap: 16,
                position: 'relative', overflow: 'hidden',
                transition: 'border-color 0.2s',
                cursor: 'default',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = T.accent; }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = T.edge0; }}
            >
              {/* Subtle glow */}
              <div style={{
                position: 'absolute', top: -40, right: -40,
                width: 160, height: 160, borderRadius: '50%',
                background: `radial-gradient(circle, ${p.accentSub.replace('0.07', '0.18')} 0%, transparent 70%)`,
                pointerEvents: 'none',
              }} />

              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                background: p.accentSub,
                border: `1px solid ${p.accentBrd}`,
                borderRadius: 999, padding: '4px 12px',
                fontFamily: T.mono, fontSize: 10, fontWeight: 700,
                color: p.accent, letterSpacing: '0.1em',
                alignSelf: 'flex-start',
              }}>
                {p.label}
              </span>

              <h3 style={{ fontFamily: T.serif, fontSize: 32, color: T.ink, letterSpacing: '-0.02em', lineHeight: 1.1 }}>
                {p.title}
              </h3>
              <p style={{ fontFamily: T.sans, fontSize: 14, color: T.muted, lineHeight: 1.65 }}>
                {p.desc}
              </p>

              {/* Notify CTA */}
              <div style={{ marginTop: 8 }}>
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  fontFamily: T.sans, fontSize: 13, fontWeight: 600, color: T.faint,
                  border: `1px solid ${T.edge0}`, borderRadius: 999,
                  padding: '8px 18px', cursor: 'default',
                }}>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0"/>
                  </svg>
                  Powiadom mnie
                </span>
              </div>
            </motion.div>
          ))}
        </div>

      </div>
    </section>
  );
}

// ── FINAL CTA ─────────────────────────────────────────────────────────────────
function FinalCTA({ reduce }: { reduce: boolean | null }) {
  return (
    <section style={{
      padding: 'clamp(80px, 10vw, 120px) 24px',
      borderTop: `1px solid ${T.edge0}`,
      background: T.bg1,
      textAlign: 'center',
    }}>
      <motion.div
        initial={reduce ? false : { opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.2 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        style={{ maxWidth: 640, margin: '0 auto' }}
      >
        <p style={{ fontFamily: T.mono, fontSize: 11, letterSpacing: '0.12em', color: T.accent, fontWeight: 600, textTransform: 'uppercase', marginBottom: 24 }}>
          Zacznij teraz
        </p>
        <h2 style={{ fontFamily: T.serif, fontSize: 'clamp(40px, 5vw, 68px)', color: T.ink, lineHeight: 1.08, letterSpacing: '-0.02em', marginBottom: 24 }}>
          Gotowy na przewagę?
        </h2>
        <p style={{ fontFamily: T.sans, fontSize: 17, color: T.muted, lineHeight: 1.65, marginBottom: 40 }}>
          Dołącz do firm które już działają szybciej dzięki YU-NA.
        </p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link href="/budos" style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            background: T.accent, color: T.bg1,
            fontFamily: T.sans, fontSize: 15, fontWeight: 700,
            padding: '15px 36px', borderRadius: 999,
            textDecoration: 'none',
            boxShadow: `0 4px 24px rgba(22,201,132,0.28)`,
            transition: 'all 0.2s',
          }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = 'scale(1.02)';
              e.currentTarget.style.boxShadow = `0 8px 32px rgba(22,201,132,0.36)`;
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = '';
              e.currentTarget.style.boxShadow = `0 4px 24px rgba(22,201,132,0.28)`;
            }}
          >
            Odkryj BudOS
          </Link>
          <Link href="/budos" style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            border: `1.5px solid ${T.edge1}`, color: T.muted,
            fontFamily: T.sans, fontSize: 15, fontWeight: 500,
            padding: '14px 28px', borderRadius: 999,
            textDecoration: 'none', background: T.bg1,
            transition: 'all 0.2s',
          }}
            onMouseEnter={e => {
              e.currentTarget.style.background = T.accentSub;
              e.currentTarget.style.borderColor = T.accentBrd;
              e.currentTarget.style.color = T.ink;
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = T.bg1;
              e.currentTarget.style.borderColor = T.edge1;
              e.currentTarget.style.color = T.muted;
            }}
          >
            Poznaj Bud.OS
          </Link>
        </div>
        {/* Social proof */}
        <p style={{
          fontFamily: T.sans, fontSize: 12,
          color: T.muted, marginTop: 20, opacity: 0.8,
        }}>
          Bez karty kredytowej · 14 dni za darmo · Anuluj kiedy chcesz
        </p>
      </motion.div>
    </section>
  );
}

// ── FOOTER Ft5 ────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer style={{
      borderTop: `1px solid ${T.edge0}`,
      padding: '32px 24px',
      background: T.bg0,
    }}>
      <div style={{
        maxWidth: 1100, margin: '0 auto',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: 16,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Image src="/brand/01-logo-concept.png" alt="YU-NA" width={20} height={20} style={{ borderRadius: 5, opacity: 0.7 }} />
          <span style={{ fontFamily: T.sans, fontSize: 13, color: T.faint }}>
            © YU-NA Intelligence 2026
          </span>
        </div>
        <div style={{ display: 'flex', gap: 24 }}>
          {[
            { l: 'Regulamin', h: '/terms'   },
            { l: 'Prywatność', h: '/privacy' },
            { l: 'RODO',      h: '/rodo'    },
          ].map(item => (
            <Link key={item.l} href={item.h} style={{
              fontFamily: T.sans, fontSize: 12, color: T.faint,
              textDecoration: 'none',
              transition: 'color 0.2s',
            }}
              onMouseEnter={e => (e.currentTarget.style.color = T.muted)}
              onMouseLeave={e => (e.currentTarget.style.color = T.faint)}
            >
              {item.l}
            </Link>
          ))}
        </div>
      </div>
    </footer>
  );
}

// ── PAGE ──────────────────────────────────────────────────────────────────────
export default function YunaLandingPage() {
  const reduce = useReducedMotion();

  return (
    <div style={{ background: T.bg0, minHeight: '100vh' }}>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.6; transform: scale(0.85); }
        }
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.3; }
        }

        /* Nav pill: cap width on mobile */
        .nav-pill {
          max-width: calc(100% - 2rem);
        }

        /* BudOS screenshot scale on card hover */
        .budos-card:hover .budos-screenshot {
          transform: scale(1.02);
        }

        /* ── MOBILE BREAKPOINT ── */
        @media (max-width: 767px) {
          /* Hero: stack vertically */
          .hero-grid {
            flex-direction: column !important;
          }
          .hero-left {
            flex: 0 0 100% !important;
            max-width: 100% !important;
          }
          .hero-right {
            flex: 0 0 100% !important;
            max-width: 100% !important;
          }

          /* DataPanel: constrained height, scrollable */
          .data-panel-scroll {
            max-height: 18rem;
            overflow-y: auto;
          }

          /* Nav links: hide on mobile */
          .nav-links {
            display: none !important;
          }

          /* Steps: single column */
          .steps-row {
            grid-template-columns: 1fr !important;
            gap: 2rem !important;
          }

          /* Bento coming-soon: single column */
          .bento-coming {
            grid-template-columns: 1fr !important;
          }

          /* Stat strip: 2 columns */
          .stat-strip-grid {
            grid-template-columns: repeat(2, 1fr) !important;
          }

          /* BudOS card: stack vertically */
          .budos-card {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>

      <Nav />
      <Hero reduce={reduce} />
      <StatStripSection reduce={reduce} />
      <PlatformSection reduce={reduce} />
      <DlaKogoSection reduce={reduce} />
      <ProductsSection reduce={reduce} />
      <FinalCTA reduce={reduce} />
      <Footer />
    </div>
  );
}
