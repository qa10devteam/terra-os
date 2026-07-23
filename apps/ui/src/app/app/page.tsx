'use client';

import Link from 'next/link';
import Image from 'next/image';
import { ArrowRight, ExternalLink, Activity, TrendingUp, Clock } from 'lucide-react';
import { useStore } from '@/store/useStore';

// YU-NA hub palette (light)
const T = {
  bg:       '#F5F7FA',
  card:     '#FFFFFF',
  navy:     '#0A1628',
  indigo:   '#4F46E5',
  border:   '#E2E8F0',
  muted:    '#64748B',
  faint:    '#94A3B8',
  go:       '#00C853',
  sans:     'var(--font-space)',
  mono:     'var(--font-jetbrains)',
} as const;

function YuNaHubHeader() {
  const user = useStore((s) => s.user);
  const firstName = (user?.name ?? 'Użytkowniku').split(' ')[0];

  return (
    <div style={{
      background: T.navy,
      padding: '40px 40px 48px',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Subtle grid pattern */}
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: 'linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)',
        backgroundSize: '40px 40px',
        pointerEvents: 'none',
      }} />

      <div style={{ position: 'relative', maxWidth: 960, margin: '0 auto' }}>
        {/* YU-NA Platform label */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
          <Image
            src="/brand/01-logo-concept.png"
            alt="YU-NA"
            width={28}
            height={28}
            style={{ objectFit: 'contain', filter: 'brightness(0) invert(1)' }}
          />
          <span style={{ fontFamily: T.sans, fontWeight: 700, fontSize: 14, color: '#fff', letterSpacing: '-0.01em' }}>YU-NA Intelligence</span>
          <span style={{ fontFamily: T.sans, fontSize: 10, color: 'rgba(255,255,255,0.35)', letterSpacing: '0.15em', textTransform: 'uppercase' }}>Platform</span>
        </div>

        <h1 style={{
          fontFamily: T.sans, fontWeight: 800, fontSize: 32,
          color: '#fff', letterSpacing: '-0.03em', lineHeight: 1.1,
          margin: '0 0 8px',
        }}>
          Witaj, {firstName}.
        </h1>
        <p style={{ fontFamily: T.sans, fontSize: 15, color: 'rgba(255,255,255,0.5)', margin: 0 }}>
          Twoje produkty YU-NA Intelligence.
        </p>
      </div>
    </div>
  );
}

function ProductGrid() {
  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '40px 40px' }}>
      <div style={{
        fontFamily: T.sans, fontSize: 11, fontWeight: 600,
        color: T.faint, letterSpacing: '0.12em', textTransform: 'uppercase',
        marginBottom: 20,
      }}>Moje produkty</div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* BudOS — active */}
        <BudOSActiveCard />

        {/* More products coming */}
        <div style={{
          background: T.card,
          border: `1.5px dashed ${T.border}`,
          borderRadius: 16,
          padding: '28px',
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          gap: 10, minHeight: 200, textAlign: 'center',
        }}>
          <div style={{ fontFamily: T.sans, fontSize: 15, fontWeight: 600, color: T.navy }}>Więcej produktów</div>
          <div style={{ fontFamily: T.sans, fontSize: 13, color: T.muted, maxWidth: 220, lineHeight: 1.5 }}>
            Infra.OS i Dev.OS — w przygotowaniu. Dowiedz się pierwszy.
          </div>
          <button style={{
            fontFamily: T.sans, fontSize: 12, fontWeight: 600,
            color: T.indigo, background: 'transparent',
            border: `1px solid rgba(79,70,229,0.3)`,
            borderRadius: 7, padding: '7px 16px', cursor: 'pointer',
            marginTop: 4,
          }}>
            Powiadom mnie
          </button>
        </div>
      </div>

      {/* Quick stats */}
      <QuickStats />
    </div>
  );
}

function BudOSActiveCard() {
  return (
    <div style={{
      background: '#07070d',
      border: '1px solid rgba(16,185,129,0.2)',
      borderRadius: 16,
      padding: '28px',
      display: 'flex', flexDirection: 'column', gap: 20,
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
        <Image
          src="/brand/B01-app-icon-budos.png"
          alt="Bud.OS"
          width={44}
          height={44}
          style={{ borderRadius: 10, flexShrink: 0 }}
        />
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ fontFamily: T.sans, fontWeight: 800, fontSize: 18, color: '#fff', letterSpacing: '-0.02em' }}>Bud.OS</span>
            <span style={{
              background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)',
              borderRadius: 5, padding: '2px 8px',
              fontFamily: T.mono, fontSize: 10, color: '#10b981', fontWeight: 600,
            }}>Aktywny</span>
          </div>
          <p style={{ fontFamily: T.sans, fontSize: 12, color: 'rgba(255,255,255,0.4)', margin: 0 }}>
            System Decyzyjny AI · Professional
          </p>
        </div>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 4,
          background: 'rgba(16,185,129,0.08)',
          borderRadius: 7, padding: '5px 8px',
        }}>
          <Activity size={12} color="#10b981" />
          <span style={{ fontFamily: T.mono, fontSize: 11, color: '#10b981', fontWeight: 600 }}>LIVE</span>
        </div>
      </div>

      {/* Mini stats */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
        {[
          { label: 'Nowych dziś', val: '14', icon: <Clock size={11} /> },
          { label: 'GO aktywnych', val: '3', icon: <TrendingUp size={11} /> },
          { label: 'Win rate', val: '67%', icon: <Activity size={11} /> },
        ].map(({ label, val, icon }) => (
          <div key={label} style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.07)',
            borderRadius: 9, padding: '10px 12px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 5, color: 'rgba(255,255,255,0.35)' }}>
              {icon}
              <span style={{ fontFamily: T.sans, fontSize: 10, color: 'rgba(255,255,255,0.35)' }}>{label}</span>
            </div>
            <div style={{ fontFamily: T.mono, fontWeight: 600, fontSize: 18, color: '#fff', letterSpacing: '-0.02em' }}>{val}</div>
          </div>
        ))}
      </div>

      {/* CTA */}
      <Link href="/app/zwiad" style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'rgba(16,185,129,0.1)',
        border: '1px solid rgba(16,185,129,0.25)',
        borderRadius: 10, padding: '12px 16px',
        textDecoration: 'none',
        transition: 'background 120ms ease',
      }}
        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(16,185,129,0.18)')}
        onMouseLeave={e => (e.currentTarget.style.background = 'rgba(16,185,129,0.1)')}
      >
        <span style={{ fontFamily: T.sans, fontWeight: 600, fontSize: 13, color: '#10b981' }}>
          Otwórz Bud.OS
        </span>
        <ArrowRight size={14} color="#10b981" />
      </Link>
    </div>
  );
}

function QuickStats() {
  return (
    <div style={{ marginTop: 32 }}>
      <div style={{
        fontFamily: T.sans, fontSize: 11, fontWeight: 600,
        color: T.faint, letterSpacing: '0.12em', textTransform: 'uppercase',
        marginBottom: 16,
      }}>Szybki dostęp</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {[
          { label: 'Przetargi', href: '/app/zwiad', emoji: '📡' },
          { label: 'Silnik AI', href: '/app/silnik', emoji: '🧠' },
          { label: 'Kosztorys', href: '/app/kosztorys', emoji: '📐' },
          { label: 'Pipeline', href: '/app/pipeline', emoji: '🎯' },
        ].map(({ label, href, emoji }) => (
          <Link key={href} href={href} style={{
            background: T.card,
            border: `1px solid ${T.border}`,
            borderRadius: 12, padding: '16px',
            textDecoration: 'none',
            display: 'flex', flexDirection: 'column', gap: 8,
            transition: 'border-color 120ms ease, box-shadow 120ms ease',
          }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLElement).style.borderColor = T.indigo + '66';
              (e.currentTarget as HTMLElement).style.boxShadow = `0 4px 20px rgba(79,70,229,0.08)`;
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLElement).style.borderColor = T.border;
              (e.currentTarget as HTMLElement).style.boxShadow = 'none';
            }}
          >
            <span style={{ fontSize: 22 }}>{emoji}</span>
            <span style={{ fontFamily: T.sans, fontWeight: 600, fontSize: 13, color: T.navy }}>{label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default function AppHub() {
  return (
    <div style={{ background: T.bg, minHeight: '100vh' }}>
      <YuNaHubHeader />
      <ProductGrid />
    </div>
  );
}
