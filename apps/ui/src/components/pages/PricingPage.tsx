'use client';

import { useState } from 'react';
import Link from 'next/link';
import { PageShell } from '@/components/PageShell';
import { Check, Loader2 } from 'lucide-react';

// ── Plan definitions (fallback; matches API /api/v2/billing/plans) ─────────────
const PLANS = [
  {
    id: 'free',
    name: 'Free',
    price: '0 PLN',
    period: 'bezpłatny',
    popular: false,
    highlight: false,
    features: [
      'Podgląd 5 przetargów/miesiąc',
      'Filtry CPV i region',
      'Profil firmy',
    ],
    locked: [
      'AI analiza SWZ',
      'Kosztorys i kalkulator',
      'Alerty BZP',
      'Eksport',
    ],
  },
  {
    id: 'starter',
    name: 'Starter',
    price: '199 PLN',
    period: '/miesiąc',
    popular: false,
    highlight: false,
    features: [
      'Do 15 przetargów',
      'AI analiza ryzyka SWZ (10 analiz/mies.)',
      'Automatyczne alerty BZP',
      'Kalkulator kosztorysu',
      'Pogoda dla placu budowy',
      'Zarządzanie pracownikami i sprzętem',
      'Eksport Excel',
      '2 osoby w zespole',
    ],
    locked: [],
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '499 PLN',
    period: '/miesiąc',
    popular: true,
    highlight: true,
    features: [
      'Do 50 przetargów',
      'AI analiza SWZ bez limitu',
      'AI Bid Writing — gotowa oferta w 5 sekcjach',
      'TED EU — przetargi unijne',
      'Sygnały pre-przetargowe (4–8 tyg. przed ogłoszeniem)',
      'Harmonogram Gantt',
      'Śledzenie konkurencji',
      'AI scoring oferty',
      '5 osób w zespole',
      'Eksport Excel + PDF',
    ],
    locked: [],
  },
  {
    id: 'business',
    name: 'Business',
    price: '1 499 PLN',
    period: '/miesiąc',
    popular: false,
    highlight: false,
    features: [
      'Nielimitowane przetargi',
      'GUS Market Intelligence AI',
      'Advanced Analytics i raporty',
      'Dostęp API + integracje ERP',
      'Nieograniczony zespół',
      'Priorytetowe wsparcie (SLA <4h)',
      'Zaawansowane raporty i OLAP',
      'Masowy eksport danych',
    ],
    locked: [],
  },
];

// ── PlanCard ──────────────────────────────────────────────────────────────────

interface PlanCardProps {
  id: string;
  name: string;
  price: string;
  period: string;
  popular: boolean;
  highlight: boolean;
  features: string[];
}

function PlanCard({ id, name, price, period, popular, highlight, features }: PlanCardProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSelectPlan() {
    if (id === 'free') {
      window.location.href = '/register';
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch('/api/v2/billing/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan_id: id,
          success_url: '/billing?success=1',
          cancel_url: '/pricing',
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.detail || 'Błąd podczas tworzenia sesji płatności');
      }

      const data = await res.json();
      if (data.redirect_url && data.redirect_url !== '#stripe-not-configured') {
        window.location.href = data.redirect_url;
      } else {
        setError(data.message || 'Stripe nie jest jeszcze skonfigurowany. Skontaktuj się z nami.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nieoczekiwany błąd');
    } finally {
      setLoading(false);
    }
  }

  const ctaLabel = id === 'free' ? 'Zacznij za darmo' : `Wybierz ${name}`;

  return (
    <div
      className={`relative rounded-2xl border flex flex-col p-6 transition-all ${
        highlight
          ? 'border-em bg-ink-900/80 shadow-glow'
          : 'border-ink-800/60 bg-ink-900/40 card-hover'
      }`}
    >
      {/* Popularne badge */}
      {popular && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10">
          <span className="bg-em text-ink-950 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wide">
            Popularne
          </span>
        </div>
      )}

      {/* Nazwa planu */}
      <h2 className={`text-xl font-bold mb-1 ${highlight ? 'text-em' : 'text-slate-100'}`}>
        {name}
      </h2>

      {/* Cena */}
      <div className="mb-6">
        <span className="text-3xl font-extrabold text-slate-100">{price}</span>
        <span className="text-slate-500 text-sm ml-1">{period}</span>
      </div>

      {/* Lista features */}
      <ul className="space-y-2 flex-1 mb-8">
        {features.map((feature) => (
          <li key={feature} className="flex items-start gap-2 text-sm text-slate-300">
            <Check size={14} className="text-success mt-0.5 shrink-0" />
            {feature}
          </li>
        ))}
      </ul>

      {/* Błąd */}
      {error && (
        <p className="text-xs text-nogo mb-3 text-center">{error}</p>
      )}

      {/* CTA */}
      <button
        onClick={handleSelectPlan}
        disabled={loading}
        className={`flex items-center justify-center gap-2 rounded-xl py-3 px-4 font-semibold text-sm transition-all disabled:opacity-60 disabled:cursor-not-allowed ${
          highlight ? 'btn-primary' : 'btn-secondary'
        }`}
      >
        {loading && <Loader2 size={14} className="animate-spin" />}
        {ctaLabel}
      </button>
    </div>
  );
}

// ── PricingPage ───────────────────────────────────────────────────────────────

export function PricingPage() {
  return (
    <PageShell title="Cennik" subtitle="Wybierz plan dla swojego zespołu">
      {/* Intro */}
      <div className="text-center mb-10">
        <p className="text-slate-400 text-base max-w-2xl mx-auto">
          Zacznij bezpłatnie, skaluj w miarę wzrostu. Bez ukrytych kosztów. Rezygnacja w dowolnym momencie.
        </p>
      </div>

      {/* Karty planów */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        {PLANS.map((plan) => (
          <PlanCard key={plan.id} {...plan} />
        ))}
      </div>

      {/* Enterprise link */}
      <div className="mt-12 text-center rounded-2xl border border-ink-800/60 bg-ink-900/40 p-8">
        <h3 className="text-lg font-bold text-slate-100 mb-2">Enterprise</h3>
        <p className="text-slate-400 text-sm mb-4 max-w-lg mx-auto">
          On-premise, SSO/SAML, SLA 99.9%, dedykowany opiekun, własne integracje i audyt bezpieczeństwa.
          Wycena indywidualna.
        </p>
        <Link
          href="mailto:sales@terra.os"
          className="inline-flex items-center gap-2 btn-secondary rounded-xl py-2.5 px-6 font-semibold text-sm"
        >
          Skontaktuj się z nami
        </Link>
      </div>

      {/* Przypis */}
      <p className="text-center text-slate-500 text-sm mt-8">
        Wszystkie plany zawierają 14-dniowy bezpłatny okres próbny. Rezygnacja w dowolnym momencie.
      </p>
    </PageShell>
  );
}
