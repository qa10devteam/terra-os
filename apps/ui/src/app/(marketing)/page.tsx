'use client';

import Image from 'next/image';
import Link from 'next/link';
import React, { useState } from 'react';
import { ArrowRight, CheckCircle2, TrendingUp, Zap, Shield, Building2 } from 'lucide-react';

// ── Design tokens — YU-NA platform (light institutional)
// Palette: White / Deep Navy / Electric Indigo — Apple/Stripe DNA
const T = {
  // Backgrounds
  bg:        '#FFFFFF',
  bgSub:     '#F5F7FA',
  bgTer:     '#EEF2F7',
  // Brand
  navy:      '#0A1628',
  navyLight: '#1E2D45',
  indigo:    '#4F46E5',
  indigoTint:'#EEF2FF',
  // Signals
  go:        '#00C853',
  goLight:   '#E8F5E9',
  // Text
  ink:       '#0A1628',
  inkMid:    '#334155',
  muted:     '#64748B',
  faint:     '#94A3B8',
  // Borders
  border:    '#E2E8F0',
  borderMid: '#CBD5E1',
  // Fonts
  sans:      'var(--font-space)',
  mono:      'var(--font-jetbrains)',
} as const;

// ── Nav ───────────────────────────────────────────────────────────────────────
function Nav() {
  const [scrolled, setScrolled] = useState(false);

  React.useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <nav style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 50,
      background: scrolled ? 'rgba(255,255,255,0.95)' : 'transparent',
      backdropFilter: scrolled ? 'blur(12px)' : 'none',
      WebkitBackdropFilter: scrolled ? 'blur(12px)' : 'none',
      borderBottom: scrolled ? `1px solid ${T.border}` : '1px solid transparent',
      transition: 'background 200ms ease, border-color 200ms ease, backdrop-filter 200ms ease',
    }}>
      <div style={{
        maxWidth: 1120, margin: '0 auto',
        padding: '0 24px',
        height: 64,
        display: 'flex', alignItems: 'center', gap: 32,
      }}>
        {/* Logo */}
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none', flexShrink: 0 }}>
          <Image
            src="/brand/01-logo-concept.png"
            alt="YU-NA Intelligence"
            width={32}
            height={32}
            style={{ objectFit: 'contain' }}
            priority
          />
          <span style={{
            fontFamily: T.sans, fontWeight: 800, fontSize: 16,
            color: T.navy, letterSpacing: '-0.02em',
          }}>YU-NA</span>
          <span style={{
            fontFamily: T.sans, fontWeight: 500, fontSize: 10,
            color: T.muted, letterSpacing: '0.18em', textTransform: 'uppercase',
            marginTop: 1,
          }}>Intelligence</span>
        </Link>

        <div style={{ flex: 1 }} />

        {/* Nav links */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {[
            { label: 'Produkty', href: '#produkty' },
            { label: 'Jak działa', href: '#jak-dziala' },
            { label: 'Cennik', href: '/budos#cennik' },
          ].map(({ label, href }) => (
            <a key={href} href={href} style={{
              fontFamily: T.sans, fontSize: 13.5, color: T.muted,
              textDecoration: 'none', padding: '6px 12px', borderRadius: 8,
              transition: 'color 120ms ease',
            }}
              onMouseEnter={e => (e.currentTarget.style.color = T.navy)}
              onMouseLeave={e => (e.currentTarget.style.color = T.muted)}
            >{label}</a>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Link href="/login" style={{
            fontFamily: T.sans, fontSize: 13.5, color: T.muted,
            textDecoration: 'none', padding: '7px 16px', borderRadius: 8,
            transition: 'color 120ms ease',
          }}
            onMouseEnter={e => (e.currentTarget.style.color = T.navy)}
            onMouseLeave={e => (e.currentTarget.style.color = T.muted)}
          >
            Zaloguj się
          </Link>
          <Link href="/budos" style={{
            fontFamily: T.sans, fontSize: 13.5, fontWeight: 600,
            color: '#fff',
            background: T.indigo,
            padding: '8px 18px', borderRadius: 8,
            textDecoration: 'none', letterSpacing: '-0.01em',
            transition: 'background 120ms ease',
          }}
            onMouseEnter={e => (e.currentTarget.style.background = '#4338CA')}
            onMouseLeave={e => (e.currentTarget.style.background = T.indigo)}
          >
            Bud.OS →
          </Link>
        </div>
      </div>
    </nav>
  );
}

// ── Hero ──────────────────────────────────────────────────────────────────────
function Hero() {
  return (
    <section style={{
      minHeight: '100vh',
      background: T.bg,
      display: 'flex', alignItems: 'center',
      paddingTop: 64,
    }}>
      <div style={{ maxWidth: 1120, margin: '0 auto', padding: '80px 24px 100px', width: '100%' }}>
        {/* Eyebrow */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          background: T.indigoTint,
          border: `1px solid rgba(79,70,229,0.2)`,
          borderRadius: 9999, padding: '5px 14px',
          marginBottom: 32,
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: T.go, display: 'inline-block',
            boxShadow: `0 0 6px ${T.go}`,
          }} />
          <span style={{
            fontFamily: T.sans, fontSize: 12, fontWeight: 600,
            color: T.indigo, letterSpacing: '0.06em', textTransform: 'uppercase',
          }}>
            Platforma Intelligence dla Budownictwa
          </span>
        </div>

        {/* Headline — two-column layout */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 80, alignItems: 'center' }}>
          {/* Left */}
          <div>
            <h1 style={{
              fontFamily: T.sans, fontWeight: 800,
              fontSize: 'clamp(40px, 5vw, 64px)',
              color: T.navy, letterSpacing: '-0.04em', lineHeight: 1.05,
              margin: '0 0 20px',
            }}>
              Zamówienia<br />
              publiczne.<br />
              <span style={{ color: T.indigo }}>Opanowane.</span>
            </h1>

            <p style={{
              fontFamily: T.sans, fontSize: 17, color: T.muted,
              lineHeight: 1.65, margin: '0 0 36px',
              maxWidth: 440,
            }}>
              YU-NA Intelligence to platforma AI dla firm budowlanych. Jeden ekosystem — zwiad przetargowy, silnik decyzyjny GO/NO-GO, kosztorys automatyczny.
            </p>

            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <Link href="/budos" style={{
                fontFamily: T.sans, fontWeight: 600, fontSize: 15,
                color: '#fff', background: T.indigo,
                padding: '12px 24px', borderRadius: 10,
                textDecoration: 'none', letterSpacing: '-0.01em',
                display: 'inline-flex', alignItems: 'center', gap: 8,
                transition: 'background 120ms ease, transform 80ms ease',
              }}
                onMouseEnter={e => { e.currentTarget.style.background = '#4338CA'; e.currentTarget.style.transform = 'translateY(-1px)'; }}
                onMouseLeave={e => { e.currentTarget.style.background = T.indigo; e.currentTarget.style.transform = 'none'; }}
              >
                Odkryj Bud.OS <ArrowRight size={16} />
              </Link>
              <Link href="/login" style={{
                fontFamily: T.sans, fontWeight: 500, fontSize: 15,
                color: T.inkMid,
                border: `1.5px solid ${T.border}`,
                background: T.bg,
                padding: '12px 24px', borderRadius: 10,
                textDecoration: 'none',
                transition: 'border-color 120ms ease',
              }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = T.borderMid)}
                onMouseLeave={e => (e.currentTarget.style.borderColor = T.border)}
              >
                Zaloguj się
              </Link>
            </div>

            {/* Social proof */}
            <div style={{ marginTop: 40, display: 'flex', gap: 24, alignItems: 'center' }}>
              {[
                { val: '40 000+', label: 'przetargów w bazie' },
                { val: '93%', label: 'dokładność AI' },
                { val: '67%', label: 'avg win rate' },
              ].map(({ val, label }) => (
                <div key={label}>
                  <div style={{ fontFamily: T.mono, fontWeight: 600, fontSize: 20, color: T.navy, letterSpacing: '-0.02em' }}>{val}</div>
                  <div style={{ fontFamily: T.sans, fontSize: 12, color: T.muted, marginTop: 2 }}>{label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Right — product card preview */}
          <div style={{ position: 'relative' }}>
            <ProductCard />
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Product preview card ───────────────────────────────────────────────────────
function ProductCard() {
  return (
    <div style={{
      background: T.bgSub,
      border: `1px solid ${T.border}`,
      borderRadius: 20,
      overflow: 'hidden',
      boxShadow: '0 20px 60px rgba(10,22,40,0.08)',
    }}>
      {/* Card header */}
      <div style={{
        background: T.navy,
        padding: '16px 20px',
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <Image
          src="/brand/B01-app-icon-budos.png"
          alt="Bud.OS"
          width={36}
          height={36}
          style={{ borderRadius: 8 }}
        />
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontFamily: T.sans, fontWeight: 700, fontSize: 14, color: '#fff' }}>Bud.OS</span>
            <span style={{ fontFamily: T.sans, fontSize: 10, color: '#10b981', letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 600 }}>Aktywny</span>
          </div>
          <div style={{ fontFamily: T.sans, fontSize: 11, color: 'rgba(255,255,255,0.45)', marginTop: 1 }}>System Decyzyjny dla Budownictwa</div>
        </div>
        <div style={{ marginLeft: 'auto' }}>
          <span style={{
            background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)',
            borderRadius: 6, padding: '3px 10px',
            fontFamily: T.mono, fontSize: 11, color: '#10b981', fontWeight: 600,
          }}>Professional</span>
        </div>
      </div>

      {/* Tender feed preview */}
      <div style={{ padding: '16px 20px' }}>
        <div style={{ fontFamily: T.sans, fontSize: 11, fontWeight: 600, color: T.faint, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 12 }}>Nowe przetargi · dziś</div>
        {[
          { title: 'Budowa drogi gminnej – Małopolska', val: '2 840 000', go: true, score: 87 },
          { title: 'Remont infrastruktury wod-kan – Śląsk', val: '1 240 000', go: true, score: 74 },
          { title: 'Przebudowa mostu – Opolskie', val: '7 100 000', go: false, score: 38 },
        ].map((t, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '10px 0',
            borderBottom: i < 2 ? `1px solid ${T.border}` : 'none',
          }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontFamily: T.sans, fontSize: 13, color: T.inkMid, fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.title}</div>
              <div style={{ fontFamily: T.mono, fontSize: 11, color: T.muted, marginTop: 2 }}>{t.val} PLN</div>
            </div>
            <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontFamily: T.mono, fontSize: 12, fontWeight: 600, color: '#818cf8' }}>{t.score}</span>
              <span style={{
                background: t.go ? 'rgba(0,200,83,0.1)' : 'rgba(239,68,68,0.1)',
                border: `1px solid ${t.go ? 'rgba(0,200,83,0.25)' : 'rgba(239,68,68,0.25)'}`,
                color: t.go ? T.go : '#ef4444',
                fontFamily: T.mono, fontSize: 10, fontWeight: 700,
                padding: '2px 7px', borderRadius: 4, letterSpacing: '0.08em',
              }}>{t.go ? 'GO' : 'NO-GO'}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Products section ──────────────────────────────────────────────────────────
function ProductsSection() {
  return (
    <section id="produkty" style={{ background: T.bgSub, padding: '100px 24px' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 64 }}>
          <div style={{
            display: 'inline-block',
            fontFamily: T.sans, fontSize: 11, fontWeight: 600,
            color: T.indigo, letterSpacing: '0.12em', textTransform: 'uppercase',
            marginBottom: 16,
          }}>Ekosystem produktów</div>
          <h2 style={{
            fontFamily: T.sans, fontWeight: 800, fontSize: 40,
            color: T.navy, letterSpacing: '-0.03em', lineHeight: 1.1,
            margin: '0 0 16px',
          }}>Jeden login. Pełna przewaga.</h2>
          <p style={{ fontFamily: T.sans, fontSize: 16, color: T.muted, maxWidth: 480, margin: '0 auto' }}>
            Po zalogowaniu do YU-NA masz dostęp do wszystkich produktów w ramach jednego konta.
          </p>
        </div>

        {/* Product grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20 }}>
          {/* BudOS — flagship, large card */}
          <BudOSCard />

          {/* Coming soon cards */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <ComingSoonCard
              name="Infra.OS"
              desc="Platforma dla inwestorów i zamawiających infrastruktury."
              icon="🏗️"
            />
            <ComingSoonCard
              name="Dev.OS"
              desc="Narzędzia deweloperskie dla firm mieszkaniowych."
              icon="🏢"
            />
          </div>
        </div>
      </div>
    </section>
  );
}

function BudOSCard() {
  const [hover, setHover] = useState(false);
  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: '#07070d',
        border: `1px solid ${hover ? 'rgba(16,185,129,0.35)' : 'rgba(255,255,255,0.06)'}`,
        borderRadius: 16,
        padding: '36px 36px 32px',
        transition: 'border-color 200ms ease',
        cursor: 'pointer',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16, marginBottom: 24 }}>
        <Image
          src="/brand/B01-app-icon-budos.png"
          alt="Bud.OS"
          width={52}
          height={52}
          style={{ borderRadius: 12, flexShrink: 0 }}
        />
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <span style={{ fontFamily: T.sans, fontWeight: 800, fontSize: 22, color: '#fff', letterSpacing: '-0.02em' }}>Bud.OS</span>
            <span style={{
              background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)',
              borderRadius: 6, padding: '2px 8px',
              fontFamily: T.mono, fontSize: 10, color: '#10b981', fontWeight: 600, letterSpacing: '0.08em',
            }}>FLAGSHIP</span>
          </div>
          <p style={{ fontFamily: T.sans, fontSize: 14, color: 'rgba(255,255,255,0.5)', margin: 0, lineHeight: 1.5 }}>
            System Decyzyjny AI dla firm budowlanych startujących w przetargach publicznych.
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 28 }}>
        {[
          { name: 'Zwiad', desc: 'BZP + TED real-time' },
          { name: 'Silnik AI', desc: 'GO/NO-GO 30 sekund' },
          { name: 'Kosztorys', desc: 'ATH/PDF/KNR auto' },
        ].map(({ name, desc }) => (
          <div key={name} style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.07)',
            borderRadius: 10, padding: '12px 14px',
          }}>
            <div style={{ fontFamily: T.sans, fontWeight: 600, fontSize: 13, color: '#e2e8f0' }}>{name}</div>
            <div style={{ fontFamily: T.sans, fontSize: 11, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>{desc}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontFamily: T.mono, fontSize: 13, color: 'rgba(255,255,255,0.35)' }}>
          od <span style={{ color: '#fff', fontWeight: 600 }}>499 zł</span> / mies.
        </div>
        <Link href="/budos" style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          fontFamily: T.sans, fontWeight: 600, fontSize: 13,
          color: '#10b981',
          background: 'rgba(16,185,129,0.1)',
          border: '1px solid rgba(16,185,129,0.25)',
          padding: '8px 16px', borderRadius: 8,
          textDecoration: 'none',
          transition: 'background 120ms ease',
        }}
          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(16,185,129,0.18)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'rgba(16,185,129,0.1)')}
        >
          Zobacz produkt <ArrowRight size={14} />
        </Link>
      </div>
    </div>
  );
}

function ComingSoonCard({ name, desc, icon }: { name: string; desc: string; icon: string }) {
  return (
    <div style={{
      background: T.bg,
      border: `1px solid ${T.border}`,
      borderRadius: 16,
      padding: '24px 24px',
      flex: 1,
    }}>
      <div style={{ fontSize: 28, marginBottom: 12 }}>{icon}</div>
      <div style={{ fontFamily: T.sans, fontWeight: 700, fontSize: 16, color: T.navy, marginBottom: 6 }}>{name}</div>
      <div style={{ fontFamily: T.sans, fontSize: 13, color: T.muted, lineHeight: 1.5, marginBottom: 16 }}>{desc}</div>
      <div style={{
        display: 'inline-flex', alignItems: 'center',
        background: T.bgTer, borderRadius: 6, padding: '4px 10px',
        fontFamily: T.sans, fontSize: 11, color: T.faint, fontWeight: 600,
        letterSpacing: '0.08em', textTransform: 'uppercase',
      }}>Wkrótce</div>
    </div>
  );
}

// ── How it works ─────────────────────────────────────────────────────────────
function HowItWorks() {
  const steps = [
    {
      n: '01',
      title: 'Zarejestruj konto YU-NA',
      desc: 'Jeden email. Jeden login. Dostęp do całego ekosystemu produktów dla budownictwa.',
      icon: <Building2 size={20} />,
    },
    {
      n: '02',
      title: 'Uruchom Bud.OS',
      desc: 'Aktywuj produkt i skonfiguruj profil swojej firmy. AI uczy się Twoich branż, regionów i apetytu na ryzyko.',
      icon: <Zap size={20} />,
    },
    {
      n: '03',
      title: 'Wygrywaj przetargi',
      desc: '93% dokładność scoringu. Kosztorys z jednego kliknięcia. Oferty szybciej, win rate wyżej.',
      icon: <TrendingUp size={20} />,
    },
  ];

  return (
    <section id="jak-dziala" style={{ background: T.bg, padding: '100px 24px' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 64 }}>
          <div style={{
            fontFamily: T.sans, fontSize: 11, fontWeight: 600,
            color: T.indigo, letterSpacing: '0.12em', textTransform: 'uppercase',
            marginBottom: 16,
          }}>Jak to działa</div>
          <h2 style={{
            fontFamily: T.sans, fontWeight: 800, fontSize: 40,
            color: T.navy, letterSpacing: '-0.03em', lineHeight: 1.1,
            margin: 0,
          }}>Od rejestracji<br />do pierwszego GO — 15 minut.</h2>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 32 }}>
          {steps.map(({ n, title, desc, icon }) => (
            <div key={n} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{
                  width: 44, height: 44, borderRadius: 12,
                  background: T.indigoTint,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: T.indigo, flexShrink: 0,
                }}>
                  {icon}
                </div>
                <span style={{ fontFamily: T.mono, fontSize: 13, color: T.faint, fontWeight: 600 }}>{n}</span>
              </div>
              <div>
                <h3 style={{ fontFamily: T.sans, fontWeight: 700, fontSize: 18, color: T.navy, letterSpacing: '-0.02em', margin: '0 0 8px' }}>{title}</h3>
                <p style={{ fontFamily: T.sans, fontSize: 14, color: T.muted, lineHeight: 1.65, margin: 0 }}>{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Trust strip ───────────────────────────────────────────────────────────────
function TrustStrip() {
  return (
    <section style={{
      background: T.navy,
      padding: '60px 24px',
    }}>
      <div style={{ maxWidth: 1120, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 32, flexWrap: 'wrap' }}>
        {[
          { icon: <Shield size={18} />, text: 'Dane zgodne z RODO' },
          { icon: <CheckCircle2 size={18} />, text: 'BZP oficjalne źródło' },
          { icon: <TrendingUp size={18} />, text: 'Aktualizacje co 15 minut' },
          { icon: <Zap size={18} />, text: 'Wyniki w 30 sekund' },
        ].map(({ icon, text }) => (
          <div key={text} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ color: T.indigo }}>{icon}</span>
            <span style={{ fontFamily: T.sans, fontSize: 14, color: 'rgba(255,255,255,0.7)', fontWeight: 500 }}>{text}</span>
          </div>
        ))}
        <Link href="/budos" style={{
          fontFamily: T.sans, fontWeight: 600, fontSize: 14,
          color: '#fff', background: T.indigo,
          padding: '10px 22px', borderRadius: 9,
          textDecoration: 'none', flexShrink: 0,
          display: 'inline-flex', alignItems: 'center', gap: 6,
          transition: 'background 120ms ease',
        }}
          onMouseEnter={e => (e.currentTarget.style.background = '#4338CA')}
          onMouseLeave={e => (e.currentTarget.style.background = T.indigo)}
        >
          Zacznij z Bud.OS <ArrowRight size={14} />
        </Link>
      </div>
    </section>
  );
}

// ── Footer ────────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer style={{ background: T.bgSub, borderTop: `1px solid ${T.border}`, padding: '40px 24px' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Image src="/brand/01-logo-concept.png" alt="YU-NA" width={24} height={24} style={{ objectFit: 'contain' }} />
          <span style={{ fontFamily: T.sans, fontWeight: 700, fontSize: 14, color: T.navy }}>YU-NA Intelligence</span>
        </div>
        <div style={{ display: 'flex', gap: 24 }}>
          {['Bud.OS', 'Cennik', 'Zaloguj się'].map(l => (
            <a key={l} href={l === 'Bud.OS' ? '/budos' : l === 'Cennik' ? '/budos#cennik' : '/login'} style={{
              fontFamily: T.sans, fontSize: 13, color: T.muted, textDecoration: 'none',
              transition: 'color 120ms ease',
            }}
              onMouseEnter={e => (e.currentTarget.style.color = T.navy)}
              onMouseLeave={e => (e.currentTarget.style.color = T.muted)}
            >{l}</a>
          ))}
        </div>
        <span style={{ fontFamily: T.sans, fontSize: 12, color: T.faint }}>
          © 2026 YU-NA Intelligence · QA10 sp. z o.o.
        </span>
      </div>
    </footer>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function YuNaLanding() {
  return (
    <main style={{ background: T.bg, minHeight: '100vh' }}>
      <Nav />
      <Hero />
      <ProductsSection />
      <HowItWorks />
      <TrustStrip />
      <Footer />
    </main>
  );
}
