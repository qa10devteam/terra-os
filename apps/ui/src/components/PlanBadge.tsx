'use client';

import { useEffect, useState } from 'react';

// ── Typy ──────────────────────────────────────────────────────────────────────

type PlanId = 'free' | 'starter' | 'pro' | 'business' | 'enterprise';

const PLAN_CONFIG: Record<PlanId, { label: string; className: string }> = {
  free: {
    label: 'Free',
    className: 'bg-gray-700/60 text-gray-300 border border-gray-600/50',
  },
  starter: {
    label: 'Starter',
    className: 'bg-blue-900/60 text-blue-300 border border-blue-700/50',
  },
  pro: {
    label: 'Pro',
    className: 'bg-purple-900/60 text-purple-300 border border-purple-700/50',
  },
  business: {
    label: 'Business',
    className: 'bg-yellow-900/60 text-yellow-300 border border-yellow-700/50',
  },
  enterprise: {
    label: 'Enterprise',
    className: 'bg-gray-950/80 text-gray-100 border border-gray-700/50',
  },
};

// ── Props ─────────────────────────────────────────────────────────────────────

interface PlanBadgeProps {
  /** Jawnie podany plan — jeśli brak, pobiera z /api/v2/billing/subscription */
  plan?: PlanId;
  /** Rozmiar badge: sm | md (default md) */
  size?: 'sm' | 'md';
  className?: string;
}

// ── Komponent ─────────────────────────────────────────────────────────────────

export function PlanBadge({ plan: planProp, size = 'md', className = '' }: PlanBadgeProps) {
  const [plan, setPlan] = useState<PlanId | null>(planProp ?? null);
  const [loading, setLoading] = useState(!planProp);

  useEffect(() => {
    if (planProp) return; // Użyj podanego planu — nie fetchuj

    let cancelled = false;
    fetch('/api/v2/billing/subscription')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!cancelled && data?.plan) {
          setPlan(data.plan as PlanId);
        }
      })
      .catch(() => {/* cicho ignoruj */})
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [planProp]);

  if (loading) {
    return (
      <span
        className={`inline-block animate-pulse rounded-full px-2 py-0.5 bg-gray-700/50 text-transparent ${
          size === 'sm' ? 'text-xs' : 'text-xs'
        } ${className}`}
      >
        ····
      </span>
    );
  }

  const id = (plan ?? 'free') as PlanId;
  const config = PLAN_CONFIG[id] ?? PLAN_CONFIG.free;

  return (
    <span
      className={`inline-flex items-center rounded-full font-semibold uppercase tracking-wide ${
        size === 'sm' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1'
      } ${config.className} ${className}`}
    >
      {config.label}
    </span>
  );
}

export default PlanBadge;
