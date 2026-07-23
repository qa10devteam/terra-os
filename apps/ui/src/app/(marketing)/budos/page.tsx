'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import {
  ArrowLeft, ArrowRight, CheckCircle2,
  Satellite, Brain, Calculator,
  Plus, Minus, Zap, Shield, TrendingUp,
} from 'lucide-react';

// ── BudOS Design tokens — dark precision tool ─────────────────────────────────
const B = {
  bg0:       '#05070c',   // deepest — true black-navy
  bg1:       '#080c14',   // primary surface
  bg2:       '#0c1220',   // elevated panel
  bg3:       '#101929',   // card
  edge0:     '#141e30',   // hairline
  edge1:     '#1c2a3e',   // border
  ink:       '#e8edf5',   // primary text
  muted:     '#6b7f9c',   // secondary
  faint:     '#344560',   // tertiary
  em:        '#10b981',   // emerald signal
  emDim:     '#065f46',
  emSub:     'rgba(16,185,129,0.07)',
  emBrd:     'rgba(16,185,129,0.2)',
  red:       '#ef4444',
  redSub:    'rgba(239,68,68,0.07)',
  sans:      'var(--font-space)',
  mono:      'var(--font-jetbrains)',
} as const;

// ── Data ─────────────────────────────────────────────────────────────────────
const PRICING = [
  {
    name: 'Starter',
    price: 'Bezpłatny',
    period: '14 dni próby',
    desc: 'Dla pojedynczego estimatora',
    features: ['5 przetargów miesięcznie', 'Podstawowa analiza AI', 'Alerty email', 'BZP Sync', '1 użytkownik'],
    cta: 'Zacznij za darmo',
    href: '/signup',
    highlight: false,
  },
  {
    name: 'Professional',
    price: '499 zł',
    period: '/mies.',
    desc: 'Dla aktywnego zespołu ofertowego',
    features: [
      'Nielimitowane przetargi',
      'Pełny Silnik Decyzyjny AI',
      'Kosztorys AI (ATH/PDF/KNR)',
      'Alerty push i email',
      'Do 5 użytkowników',
      'Priorytetowy support',
    ],
    cta: 'Wybierz Professional',
    href: '/signup',
    highlight: true,
    badge: 'Najczęściej wybierany',
  },
  {
    name: 'Enterprise',
    price: 'Wycena',
    period: 'indywidualna',
    desc: 'Dla firm z dużym portfolio',
    features: [
      'Wszystko z Professional',
      'Nielimitowani użytkownicy',
      'Dedykowany model AI',
      'SLA 99,9%',
      'Wdrożenie i integracje',
      'Analiza konkurencji premium',
    ],
    cta: 'Porozmawiajmy',
    href: '/contact',
    highlight: false,
  },
];

const FAQ = [
  {
    q: 'Jak działa dopasowanie AI?',
    a: 'Silnik porównuje pełną treść ogłoszenia z profilem Twojej firmy — branżą, kodami CPV, historią wygranych i kompetencjami. Wynik 0–100 jest generowany automatycznie i można go dostosować własną wagą kryteriów.',
  },
  {
    q: 'Czy można eksportować kosztorys do ATH?',
    a: 'Tak. BudOS obsługuje natywny eksport do ATH (Norma Pro / Zuzia), PDF i XLSX. Wszystkie pozycje zgodne z KNR i aktualnymi bazami cenowymi.',
  },
  {
    q: 'Jakie bazy przetargów są monitorowane?',
    a: 'BZP, TED/eTendering oraz e-zamówienia.gov.pl. Synchronizacja co 15 minut.',
  },
  {
    q: 'Czy jest integracja z innymi systemami?',
    a: 'Professional i Enterprise obsługują eksport Excel/PDF/DOCX. Enterprise zawiera pełne REST API do integracji z ERP, CRM i narzędziami biurowymi.',
  },
  {
    q: 'Ile kosztuje Enterprise?',
    a: 'Wyceniamy indywidualnie na podstawie liczby użytkowników, wolumenu i wymagań integracji. Odpowiadamy w ciągu 24h roboczych.',
  },
];

// ── Navbar ───────────────────────────────────────────────────────────────────
function Navbar() {
  return (
    <nav style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 50,
      background: 'rgba(8,12,20,0.90)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      borderBottom: `1px solid ${B.edge1}`,
    }}>
      <div style={{
        maxWidth: 1120, margin: '0 auto',
        padding: '0 24px',
        height: 60,
        display: 'flex', alignItems: 'center', gap: 16,
      }}>
        {/* Back to YU-NA */}
        <Link href="/" style={{
          display: 'flex', alignItems: 'center', gap: 6,
          fontFamily: B.sans, fontSize: 12, color: B.muted,
          textDecoration: 'none',
          transition: 'color 120ms ease',
        }}
          onMouseEnter={e => (e.currentTarget.style.color = B.ink)}
          onMouseLeave={e => (e.currentTarget.style.color = B.muted)}
        >
          <ArrowLeft size={13} />
          YU-NA
        </Link>

        <span style={{ color: B.edge1, fontSize: 16 }}>|</span>

        {/* BudOS brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <Image
            src="/brand/B01-app-icon-budos.png"
            alt="Bud.OS"
            width={26}
            height={26}
            style={{ borderRadius: 6 }}
          />
          <span style={{ fontFamily: B.sans, fontWeight: 700, fontSize: 15, color: B.ink, letterSpacing: '-0.01em' }}>
            Bud.OS
          </span>
        </div>

        <div style={{ flex: 1 }} />

        {/* Nav links */}
        <div style={{ display: 'none' }}>
          {/* hidden on smallest, shown via media — inline styles can't do media queries, use className fallback */}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {[
            { label: 'Zwiad', href: '#zwiad' },
            { label: 'Silnik AI', href: '#silnik' },
            { label: 'Kosztorys', href: '#kosztorys' },
            { label: 'Cennik', href: '#cennik' },
          ].map(({ label, href }) => (
            <a key={href} href={href} style={{
              fontFamily: B.sans, fontSize: 12.5, color: B.muted,
              textDecoration: 'none', padding: '5px 10px',
              transition: 'color 120ms ease',
            }}
              onMouseEnter={e => (e.currentTarget.style.color = B.ink)}
              onMouseLeave={e => (e.currentTarget.style.color = B.muted)}
            >{label}</a>
          ))}
        </div>

        <Link href="/signup" style={{
          fontFamily: B.sans, fontWeight: 600, fontSize: 13,
          color: B.bg0, background: B.em,
          padding: '8px 16px', borderRadius: 8,
          textDecoration: 'none',
          display: 'inline-flex', alignItems: 'center', gap: 5,
          transition: 'background 120ms ease',
        }}
          onMouseEnter={e => (e.currentTarget.style.background = '#059669')}
          onMouseLeave={e => (e.currentTarget.style.background = B.em)}
        >
          Zacznij za darmo <ArrowRight size={13} />
        </Link>
      </div>
    </nav>
  );
}

// ── Hero ──────────────────────────────────────────────────────────────────────
function Hero() {
  return (
    <section style={{
      minHeight: '100vh',
      background: B.bg0,
      display: 'flex', alignItems: 'center',
      paddingTop: 60,
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background grid */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        backgroundImage: [
          'radial-gradient(ellipse 80% 50% at 50% 0%, rgba(16,185,129,0.09) 0%, transparent 60%)',
          `linear-gradient(${B.emBrd.replace('0.2', '0.03')} 1px, transparent 1px)`,
          `linear-gradient(90deg, ${B.emBrd.replace('0.2', '0.03')} 1px, transparent 1px)`,
        ].join(', '),
        backgroundSize: 'auto, 56px 56px, 56px 56px',
      }} />

      <div style={{ maxWidth: 1120, margin: '0 auto', padding: '80px 24px', width: '100%', position: 'relative' }}>
        {/* Eyebrow */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          background: B.emSub,
          border: `1px solid ${B.emBrd}`,
          borderRadius: 9999, padding: '5px 14px',
          marginBottom: 28,
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: B.em, display: 'inline-block',
            boxShadow: `0 0 8px ${B.em}`,
          }} />
          <span style={{
            fontFamily: B.sans, fontSize: 11.5, fontWeight: 600,
            color: B.em, letterSpacing: '0.08em', textTransform: 'uppercase',
          }}>System Decyzyjny AI · Zamówienia Publiczne</span>
        </div>

        {/* Headline + right column */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 80, alignItems: 'center' }}>
          <div>
            <h1 style={{
              fontFamily: B.sans, fontWeight: 800,
              fontSize: 'clamp(38px, 5vw, 62px)',
              color: B.ink, letterSpacing: '-0.04em', lineHeight: 1.04,
              margin: '0 0 20px',
            }}>
              Wygrywaj<br />
              przetargi.<br />
              <span style={{ color: B.em }}>Szybciej.</span>
            </h1>

            <p style={{
              fontFamily: B.sans, fontSize: 16, color: B.muted,
              lineHeight: 1.65, margin: '0 0 36px',
              maxWidth: 420,
            }}>
              BudOS to AI dla firm budowlanych startujących w zamówieniach publicznych. Zwiad BZP/TED, GO/NO-GO w 30 sekund, kosztorys ATH z jednego kliknięcia.
            </p>

            <div style={{ display: 'flex', gap: 12 }}>
              <Link href="/signup" style={{
                fontFamily: B.sans, fontWeight: 600, fontSize: 14,
                color: B.bg0, background: B.em,
                padding: '12px 24px', borderRadius: 10,
                textDecoration: 'none',
                display: 'inline-flex', alignItems: 'center', gap: 7,
                transition: 'background 120ms ease, transform 80ms ease',
              }}
                onMouseEnter={e => { e.currentTarget.style.background = '#059669'; e.currentTarget.style.transform = 'translateY(-1px)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = B.em; e.currentTarget.style.transform = 'none'; }}
              >
                Zacznij za darmo <ArrowRight size={15} />
              </Link>
              <a href="#cennik" style={{
                fontFamily: B.sans, fontWeight: 500, fontSize: 14,
                color: B.muted, background: 'transparent',
                border: `1.5px solid ${B.edge1}`,
                padding: '12px 22px', borderRadius: 10,
                textDecoration: 'none',
                transition: 'border-color 120ms ease, color 120ms ease',
              }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = B.edge1; e.currentTarget.style.color = B.ink; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = B.edge1; e.currentTarget.style.color = B.muted; }}
              >
                Zobacz cennik
              </a>
            </div>

            {/* Stats row */}
            <div style={{ display: 'flex', gap: 32, marginTop: 44 }}>
              {[
                { val: '40 000+', label: 'przetargów / mies.' },
                { val: '30s', label: 'analiza GO/NO-GO' },
                { val: '67%', label: 'avg win rate' },
              ].map(({ val, label }) => (
                <div key={label}>
                  <div style={{ fontFamily: B.mono, fontWeight: 700, fontSize: 22, color: B.em, letterSpacing: '-0.02em' }}>{val}</div>
                  <div style={{ fontFamily: B.sans, fontSize: 11, color: B.muted, marginTop: 3 }}>{label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Right — GO/NO-GO mock */}
          <GonogoDeck />
        </div>
      </div>
    </section>
  );
}

function GonogoDeck() {
  return (
    <div style={{
      background: B.bg2,
      border: `1px solid ${B.edge1}`,
      borderRadius: 18,
      overflow: 'hidden',
      boxShadow: '0 24px 64px rgba(0,0,0,0.4)',
    }}>
      {/* Header bar */}
      <div style={{
        background: B.bg3,
        borderBottom: `1px solid ${B.edge1}`,
        padding: '14px 20px',
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <Image src="/brand/B01-app-icon-budos.png" alt="BudOS" width={28} height={28} style={{ borderRadius: 6 }} />
        <div>
          <div style={{ fontFamily: B.sans, fontWeight: 700, fontSize: 12.5, color: B.ink }}>Silnik Decyzyjny AI</div>
          <div style={{ fontFamily: B.sans, fontSize: 10.5, color: B.muted, marginTop: 1 }}>Analiza SWZ — wynik natychmiastowy</div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: B.em, boxShadow: `0 0 6px ${B.em}`, display: 'inline-block' }} />
          <span style={{ fontFamily: B.mono, fontSize: 10, color: B.em, fontWeight: 600 }}>LIVE</span>
        </div>
      </div>

      {/* Decision block */}
      <div style={{ padding: '20px' }}>
        <div style={{
          background: B.emSub,
          border: `1px solid ${B.emBrd}`,
          borderRadius: 12, padding: '16px 18px',
          marginBottom: 16,
          display: 'flex', alignItems: 'center', gap: 14,
        }}>
          <div style={{
            width: 48, height: 48, borderRadius: 10,
            background: B.em,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: B.mono, fontWeight: 900, fontSize: 14,
            color: B.bg0, letterSpacing: '0.04em', flexShrink: 0,
          }}>GO</div>
          <div>
            <div style={{ fontFamily: B.sans, fontWeight: 700, fontSize: 13.5, color: B.ink, marginBottom: 3 }}>
              Budowa drogi gminnej – Małopolska
            </div>
            <div style={{ fontFamily: B.sans, fontSize: 11.5, color: B.muted }}>2 840 000 PLN · BZP 2026/S-04-0044231</div>
          </div>
          <div style={{ marginLeft: 'auto', textAlign: 'right', flexShrink: 0 }}>
            <div style={{ fontFamily: B.mono, fontWeight: 700, fontSize: 22, color: B.em }}>87</div>
            <div style={{ fontFamily: B.sans, fontSize: 10, color: B.muted }}>score</div>
          </div>
        </div>

        {/* Risk chips */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontFamily: B.sans, fontSize: 10.5, color: B.faint, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>
            Ryzyka kontraktowe
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {['Warunki płatności 60 dni', 'Kara umowna 15%', 'Wymagany potencjał tech.'].map((r, i) => (
              <span key={r} style={{
                fontFamily: B.sans, fontSize: 11, color: i === 0 ? '#f59e0b' : B.muted,
                background: i === 0 ? 'rgba(245,158,11,0.08)' : B.bg3,
                border: `1px solid ${i === 0 ? 'rgba(245,158,11,0.2)' : B.edge0}`,
                borderRadius: 6, padding: '3px 9px',
              }}>{r}</span>
            ))}
          </div>
        </div>

        {/* Second tender — NO-GO */}
        <div style={{
          background: B.redSub,
          border: '1px solid rgba(239,68,68,0.18)',
          borderRadius: 10, padding: '12px 14px',
          display: 'flex', alignItems: 'center', gap: 12, opacity: 0.8,
        }}>
          <div style={{
            width: 40, height: 40, borderRadius: 8,
            background: B.redSub,
            border: '1px solid rgba(239,68,68,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: B.mono, fontWeight: 800, fontSize: 11,
            color: B.red, letterSpacing: '0.04em', flexShrink: 0,
          }}>NO-GO</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontFamily: B.sans, fontSize: 12.5, color: B.muted, fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              Przebudowa mostu – Opolskie
            </div>
            <div style={{ fontFamily: B.sans, fontSize: 10.5, color: B.faint, marginTop: 2 }}>7 100 000 PLN</div>
          </div>
          <div style={{ fontFamily: B.mono, fontWeight: 700, fontSize: 18, color: B.red, flexShrink: 0 }}>38</div>
        </div>
      </div>
    </div>
  );
}

// ── Features ─────────────────────────────────────────────────────────────────
function FeaturesSection() {
  const pillars = [
    {
      id: 'zwiad',
      icon: <Satellite size={22} />,
      title: 'Zwiad Przetargowy',
      headline: 'BZP + TED w jednym miejscu.',
      desc: 'AI monitoruje bazę 24/7 i dopasowuje ogłoszenia do profilu Twojej firmy. Alerty push i email — wiesz o przetargu zanim zrobi to konkurencja.',
      features: [
        'BZP + TED w jednym miejscu',
        'Matching AI z profilem firmy',
        'Alerty push i email',
        'Historia wszystkich ogłoszeń',
        'Filtrowanie branż i kwot',
      ],
    },
    {
      id: 'silnik',
      icon: <Brain size={22} />,
      title: 'Silnik Decyzyjny AI',
      headline: 'GO / NO-GO w 30 sekund.',
      desc: 'Pełna analiza SWZ: ryzyka kontraktowe, wymagania techniczne, ocena dopasowania 0–100. Historyczne decyzje tworzą profil Twoich wygranych.',
      features: [
        'Analiza ryzyk kontraktowych',
        'Wymagania techniczne SWZ',
        'Ocena dopasowania 0–100',
        'Historia decyzji GO/NO-GO',
        'Raport PDF jednym kliknięciem',
      ],
    },
    {
      id: 'kosztorys',
      icon: <Calculator size={22} />,
      title: 'Kosztorys AI',
      headline: 'ATH/PDF/KNR z jednego kliknięcia.',
      desc: 'Automatyczna wycena z dokumentacji SWZ. Baza materiałów zawsze aktualna, wersjonowanie kosztorysów, eksport kompatybilny z Norma Pro i Zuzia.',
      features: [
        'Generowanie z dokumentacji SWZ',
        'Format ATH / PDF gotowy do złożenia',
        'Baza materiałów zawsze aktualna',
        'Wersjonowanie kosztorysów',
        'Eksport KNR i ICB',
      ],
    },
  ];

  return (
    <div>
      {pillars.map((p, i) => (
        <section
          key={p.id}
          id={p.id}
          style={{
            background: i % 2 === 0 ? B.bg1 : B.bg0,
            padding: '100px 24px',
          }}
        >
          <div style={{
            maxWidth: 1120, margin: '0 auto',
            display: 'grid', gridTemplateColumns: '1fr 1fr',
            gap: 80, alignItems: 'center',
            ...(i % 2 !== 0 ? { direction: 'rtl' } : {}),
          }}>
            <div style={{ direction: 'ltr' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
                <div style={{
                  width: 44, height: 44, borderRadius: 12,
                  background: B.emSub, border: `1px solid ${B.emBrd}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: B.em,
                }}>
                  {p.icon}
                </div>
                <span style={{ fontFamily: B.sans, fontSize: 12, fontWeight: 600, color: B.em, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                  {p.title}
                </span>
              </div>
              <h2 style={{
                fontFamily: B.sans, fontWeight: 800, fontSize: 36,
                color: B.ink, letterSpacing: '-0.03em', lineHeight: 1.1,
                margin: '0 0 16px',
              }}>{p.headline}</h2>
              <p style={{ fontFamily: B.sans, fontSize: 15, color: B.muted, lineHeight: 1.65, margin: '0 0 28px' }}>{p.desc}</p>
              <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
                {p.features.map(f => (
                  <li key={f} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <CheckCircle2 size={15} color={B.em} style={{ flexShrink: 0 }} />
                    <span style={{ fontFamily: B.sans, fontSize: 14, color: B.ink }}>{f}</span>
                  </li>
                ))}
              </ul>
            </div>
            {/* Right side placeholder — dark card */}
            <div style={{ direction: 'ltr' }}>
              <FeatureCard pillar={p.id} />
            </div>
          </div>
        </section>
      ))}
    </div>
  );
}

function FeatureCard({ pillar }: { pillar: string }) {
  if (pillar === 'zwiad') {
    return (
      <div style={{
        background: B.bg2, border: `1px solid ${B.edge1}`,
        borderRadius: 16, padding: '24px', boxShadow: '0 16px 48px rgba(0,0,0,0.3)',
      }}>
        <div style={{ fontFamily: B.sans, fontSize: 10.5, fontWeight: 600, color: B.faint, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 14 }}>
          Nowe przetargi · aktualizacja co 15 min
        </div>
        {[
          { title: 'Remont infrastruktury wod-kan – Śląsk', val: '1 240 000', score: 81 },
          { title: 'Budowa chodnika ul. Różana – Kraków', val: '380 000', score: 74 },
          { title: 'Kanalizacja deszczowa – Gdańsk', val: '2 100 000', score: 69 },
          { title: 'Modernizacja dróg powiatowych', val: '4 600 000', score: 58 },
        ].map((t, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '11px 0',
            borderBottom: i < 3 ? `1px solid ${B.edge0}` : 'none',
          }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontFamily: B.sans, fontSize: 12.5, color: B.ink, fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.title}</div>
              <div style={{ fontFamily: B.mono, fontSize: 11, color: B.muted, marginTop: 2 }}>{t.val} PLN</div>
            </div>
            <div style={{
              background: B.emSub, border: `1px solid ${B.emBrd}`,
              borderRadius: 6, padding: '3px 9px',
              fontFamily: B.mono, fontSize: 12, fontWeight: 700, color: B.em,
              flexShrink: 0,
            }}>{t.score}</div>
          </div>
        ))}
      </div>
    );
  }

  if (pillar === 'silnik') {
    return (
      <div style={{
        background: B.bg2, border: `1px solid ${B.edge1}`,
        borderRadius: 16, padding: '24px', boxShadow: '0 16px 48px rgba(0,0,0,0.3)',
      }}>
        <div style={{ fontFamily: B.sans, fontSize: 10.5, fontWeight: 600, color: B.faint, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 14 }}>
          Analiza SWZ · wynik
        </div>
        <div style={{
          background: B.emSub, border: `1px solid ${B.emBrd}`,
          borderRadius: 12, padding: '16px 18px', marginBottom: 16,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <span style={{ fontFamily: B.mono, fontWeight: 900, fontSize: 32, color: B.em }}>87</span>
            <span style={{
              background: B.em, color: B.bg0,
              fontFamily: B.mono, fontWeight: 800, fontSize: 13,
              padding: '5px 14px', borderRadius: 8,
            }}>GO</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {[
              { k: 'CPV match', v: '94%', ok: true },
              { k: 'Budżet', v: 'OK', ok: true },
              { k: 'Termin', v: '45 dni', ok: true },
              { k: 'Kara umowna', v: '15%', ok: false },
            ].map(({ k, v, ok }) => (
              <div key={k} style={{
                background: B.bg3, border: `1px solid ${B.edge0}`,
                borderRadius: 7, padding: '8px 10px',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}>
                <span style={{ fontFamily: B.sans, fontSize: 11, color: B.muted }}>{k}</span>
                <span style={{ fontFamily: B.mono, fontSize: 11, fontWeight: 600, color: ok ? B.em : '#f59e0b' }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // kosztorys
  return (
    <div style={{
      background: B.bg2, border: `1px solid ${B.edge1}`,
      borderRadius: 16, padding: '24px', boxShadow: '0 16px 48px rgba(0,0,0,0.3)',
    }}>
      <div style={{ fontFamily: B.sans, fontSize: 10.5, fontWeight: 600, color: B.faint, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 14 }}>
        Kosztorys · pozycje KNR
      </div>
      {[
        { nr: 'KNR 2-01 0106-01', name: 'Roboty ziemne', jm: 'm³', ile: 420, cena: 38.5 },
        { nr: 'KNR 2-01 0201-04', name: 'Podbudowa z kruszywa', jm: 'm²', ile: 1200, cena: 62.0 },
        { nr: 'KNR 2-05 0102-01', name: 'Nawierzchnia bitumiczna', jm: 'm²', ile: 1100, cena: 145.0 },
        { nr: 'KNR 2-01 1001-02', name: 'Krawężnik betonowy', jm: 'm.b.', ile: 640, cena: 28.0 },
      ].map((row, i) => (
        <div key={i} style={{
          display: 'grid', gridTemplateColumns: '1fr auto',
          gap: 8, padding: '9px 0',
          borderBottom: i < 3 ? `1px solid ${B.edge0}` : 'none',
          alignItems: 'start',
        }}>
          <div>
            <div style={{ fontFamily: B.mono, fontSize: 10, color: B.faint, marginBottom: 2 }}>{row.nr}</div>
            <div style={{ fontFamily: B.sans, fontSize: 12.5, color: B.ink }}>{row.name}</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontFamily: B.mono, fontSize: 12, fontWeight: 600, color: B.em }}>
              {(row.ile * row.cena).toLocaleString('pl-PL')} zł
            </div>
            <div style={{ fontFamily: B.mono, fontSize: 10, color: B.faint }}>
              {row.ile} {row.jm}
            </div>
          </div>
        </div>
      ))}
      <div style={{
        marginTop: 12, paddingTop: 12, borderTop: `1px solid ${B.edge1}`,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <span style={{ fontFamily: B.sans, fontSize: 12, color: B.muted, fontWeight: 600 }}>Łącznie netto</span>
        <span style={{ fontFamily: B.mono, fontSize: 16, fontWeight: 700, color: B.em }}>263 060 zł</span>
      </div>
    </div>
  );
}

// ── Pricing ───────────────────────────────────────────────────────────────────
function Pricing() {
  return (
    <section id="cennik" style={{ background: B.bg1, padding: '100px 24px' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 64 }}>
          <div style={{
            fontFamily: B.sans, fontSize: 11, fontWeight: 600,
            color: B.em, letterSpacing: '0.12em', textTransform: 'uppercase',
            marginBottom: 14,
          }}>Cennik</div>
          <h2 style={{
            fontFamily: B.sans, fontWeight: 800, fontSize: 40,
            color: B.ink, letterSpacing: '-0.03em', lineHeight: 1.1, margin: 0,
          }}>Prosty model. Bez niespodzianek.</h2>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
          {PRICING.map(plan => (
            <div key={plan.name} style={{
              background: plan.highlight ? B.bg3 : B.bg2,
              border: plan.highlight ? `1px solid ${B.emBrd}` : `1px solid ${B.edge1}`,
              borderRadius: 18,
              padding: '32px 28px',
              position: 'relative',
              display: 'flex', flexDirection: 'column',
              boxShadow: plan.highlight ? `0 0 0 1px ${B.emBrd}, 0 20px 48px rgba(16,185,129,0.08)` : 'none',
            }}>
              {plan.highlight && plan.badge && (
                <div style={{
                  position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
                  background: B.em, color: B.bg0,
                  fontFamily: B.mono, fontSize: 10.5, fontWeight: 700,
                  letterSpacing: '0.08em', padding: '4px 14px', borderRadius: 9999,
                  whiteSpace: 'nowrap',
                }}>{plan.badge}</div>
              )}

              <div style={{ marginBottom: 24 }}>
                <div style={{ fontFamily: B.sans, fontWeight: 700, fontSize: 16, color: B.ink, marginBottom: 4 }}>{plan.name}</div>
                <div style={{ fontFamily: B.sans, fontSize: 13, color: B.muted, marginBottom: 16 }}>{plan.desc}</div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
                  <span style={{ fontFamily: B.mono, fontWeight: 800, fontSize: plan.price === 'Wycena' ? 24 : 32, color: plan.highlight ? B.em : B.ink, letterSpacing: '-0.02em' }}>
                    {plan.price}
                  </span>
                  <span style={{ fontFamily: B.sans, fontSize: 13, color: B.muted }}>{plan.period}</span>
                </div>
              </div>

              <ul style={{ listStyle: 'none', margin: '0 0 28px', padding: 0, display: 'flex', flexDirection: 'column', gap: 10, flex: 1 }}>
                {plan.features.map(f => (
                  <li key={f} style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                    <CheckCircle2 size={13} color={plan.highlight ? B.em : B.muted} style={{ flexShrink: 0 }} />
                    <span style={{ fontFamily: B.sans, fontSize: 13, color: plan.highlight ? B.ink : B.muted }}>{f}</span>
                  </li>
                ))}
              </ul>

              <Link href={plan.href} style={{
                fontFamily: B.sans, fontWeight: 600, fontSize: 14,
                color: plan.highlight ? B.bg0 : B.muted,
                background: plan.highlight ? B.em : 'transparent',
                border: plan.highlight ? 'none' : `1.5px solid ${B.edge1}`,
                padding: '11px 0', borderRadius: 10,
                textDecoration: 'none', textAlign: 'center',
                display: 'block',
                transition: 'background 120ms ease, color 120ms ease',
              }}
                onMouseEnter={e => {
                  if (plan.highlight) e.currentTarget.style.background = '#059669';
                  else { e.currentTarget.style.color = B.ink; e.currentTarget.style.borderColor = B.em; }
                }}
                onMouseLeave={e => {
                  if (plan.highlight) e.currentTarget.style.background = B.em;
                  else { e.currentTarget.style.color = B.muted; e.currentTarget.style.borderColor = B.edge1; }
                }}
              >{plan.cta}</Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Trust ─────────────────────────────────────────────────────────────────────
function TrustRow() {
  return (
    <section style={{ background: B.bg2, borderTop: `1px solid ${B.edge1}`, borderBottom: `1px solid ${B.edge1}`, padding: '32px 24px' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-around', flexWrap: 'wrap', gap: 24 }}>
        {[
          { icon: <Shield size={16} />, label: 'RODO compliant' },
          { icon: <Zap size={16} />, label: 'Update co 15 min' },
          { icon: <TrendingUp size={16} />, label: '93% dokładność AI' },
          { icon: <CheckCircle2 size={16} />, label: 'BZP oficjalne źródło' },
        ].map(({ icon, label }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: B.em }}>{icon}</span>
            <span style={{ fontFamily: B.sans, fontSize: 13, color: B.muted, fontWeight: 500 }}>{label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

// ── FAQ ───────────────────────────────────────────────────────────────────────
function FAQSection() {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <section style={{ background: B.bg0, padding: '100px 24px' }}>
      <div style={{ maxWidth: 720, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 56 }}>
          <h2 style={{
            fontFamily: B.sans, fontWeight: 800, fontSize: 36,
            color: B.ink, letterSpacing: '-0.03em', margin: 0,
          }}>Często zadawane pytania</h2>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {FAQ.map((item, i) => (
            <div key={i} style={{
              background: B.bg2,
              border: `1px solid ${open === i ? B.emBrd : B.edge1}`,
              borderRadius: 12,
              overflow: 'hidden',
              transition: 'border-color 120ms ease',
            }}>
              <button
                type="button"
                onClick={() => setOpen(open === i ? null : i)}
                style={{
                  width: '100%', textAlign: 'left',
                  padding: '18px 20px',
                  background: 'none', border: 'none', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16,
                }}
              >
                <span style={{ fontFamily: B.sans, fontWeight: 600, fontSize: 14.5, color: B.ink }}>{item.q}</span>
                {open === i
                  ? <Minus size={16} color={B.em} style={{ flexShrink: 0 }} />
                  : <Plus size={16} color={B.muted} style={{ flexShrink: 0 }} />
                }
              </button>
              {open === i && (
                <div style={{ padding: '0 20px 18px' }}>
                  <p style={{ fontFamily: B.sans, fontSize: 13.5, color: B.muted, lineHeight: 1.7, margin: 0 }}>{item.a}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── CTA bottom ────────────────────────────────────────────────────────────────
function CTABottom() {
  return (
    <section style={{
      background: B.bg1,
      borderTop: `1px solid ${B.edge1}`,
      padding: '80px 24px',
      textAlign: 'center',
    }}>
      <div style={{ maxWidth: 560, margin: '0 auto' }}>
        <Image src="/brand/B01-app-icon-budos.png" alt="BudOS" width={52} height={52} style={{ borderRadius: 12, margin: '0 auto 24px' }} />
        <h2 style={{
          fontFamily: B.sans, fontWeight: 800, fontSize: 36,
          color: B.ink, letterSpacing: '-0.03em', lineHeight: 1.1,
          margin: '0 0 16px',
        }}>Gotowy na pierwszego GO?</h2>
        <p style={{ fontFamily: B.sans, fontSize: 15, color: B.muted, lineHeight: 1.6, margin: '0 0 32px' }}>
          14 dni za darmo. Żadnej karty kredytowej. Konto aktywne w 2 minuty.
        </p>
        <Link href="/signup" style={{
          fontFamily: B.sans, fontWeight: 700, fontSize: 15,
          color: B.bg0, background: B.em,
          padding: '14px 32px', borderRadius: 12,
          textDecoration: 'none',
          display: 'inline-flex', alignItems: 'center', gap: 8,
          transition: 'background 120ms ease, transform 80ms ease',
        }}
          onMouseEnter={e => { e.currentTarget.style.background = '#059669'; e.currentTarget.style.transform = 'translateY(-2px)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = B.em; e.currentTarget.style.transform = 'none'; }}
        >
          Zacznij za darmo <ArrowRight size={16} />
        </Link>
      </div>
    </section>
  );
}

// ── Footer ────────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer style={{ background: B.bg0, borderTop: `1px solid ${B.edge1}`, padding: '32px 24px' }}>
      <div style={{
        maxWidth: 1120, margin: '0 auto',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: 16,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Image src="/brand/B01-app-icon-budos.png" alt="BudOS" width={22} height={22} style={{ borderRadius: 5 }} />
          <span style={{ fontFamily: B.sans, fontWeight: 700, fontSize: 13, color: B.ink }}>Bud.OS</span>
          <span style={{ fontFamily: B.sans, fontSize: 12, color: B.faint }}>produkt</span>
          <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 5, textDecoration: 'none', marginLeft: 8 }}>
            <Image src="/brand/01-logo-concept.png" alt="YU-NA" width={16} height={16} style={{ objectFit: 'contain', filter: 'brightness(0) invert(0.5)' }} />
            <span style={{ fontFamily: B.sans, fontSize: 12, color: B.faint }}>YU-NA Intelligence</span>
          </Link>
        </div>
        <span style={{ fontFamily: B.sans, fontSize: 11, color: B.faint }}>© 2026 QA10 sp. z o.o.</span>
      </div>
    </footer>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function BudOSPage() {
  return (
    <main style={{ background: B.bg0 }}>
      <Navbar />
      <Hero />
      <TrustRow />
      <FeaturesSection />
      <Pricing />
      <FAQSection />
      <CTABottom />
      <Footer />
    </main>
  );
}
