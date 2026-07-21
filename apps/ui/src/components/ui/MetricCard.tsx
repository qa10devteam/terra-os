'use client';

import { GlassCard } from './GlassCard';
import type { LucideIcon } from 'lucide-react';
import { TrendingUp, TrendingDown } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────

interface MetricCardProps {
  icon:         LucideIcon;
  label:        string;
  value:        string | number;
  /** Number — positive = emerald, negative = red */
  trend?:       number;
  trendLabel?:  string;
  /** Tailwind class for icon colour */
  iconColor?:   string;
  /** Suffix shown after value in smaller mono text (e.g. "PLN", "%") */
  suffix?:      string;
  className?:   string;
  loading?:     boolean;
}

// ── Component — Brand Bible BudOS ─────────────────────────────────────────────
// PRECYZJA: wszystkie wartości w font-mono (JetBrains Mono)
// PRZEWAGA: pozytywny trend = emerald, negatywny = red

export function MetricCard({
  icon:       Icon,
  label,
  value,
  trend,
  trendLabel  = 'w tym tygodniu',
  iconColor   = 'text-em',
  suffix,
  className   = '',
  loading     = false,
}: MetricCardProps) {
  const hasTrend      = trend !== undefined;
  const trendPositive = hasTrend && trend >= 0;

  if (loading) {
    return (
      <GlassCard className={`p-4 flex flex-col gap-3 ${className}`}>
        <div className="flex items-center justify-between">
          <div className="h-2.5 w-24 rounded bg-ink-700 animate-shimmer" />
          <div className="w-8 h-8 rounded-lg bg-ink-700 animate-shimmer" />
        </div>
        <div className="h-7 w-20 rounded bg-ink-700 animate-shimmer" />
        <div className="h-2.5 w-28 rounded bg-ink-700 animate-shimmer" />
      </GlassCard>
    );
  }

  return (
    <GlassCard
      className={`p-4 flex flex-col gap-3 ${className}`}
    >
      {/* Header row */}
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-slate-500 font-medium tracking-wide uppercase">
          {label}
        </span>
        <div
          className={`w-8 h-8 rounded-lg bg-ink-800 border border-ink-line flex items-center justify-center ${iconColor}`}
        >
          <Icon className="w-4 h-4" />
        </div>
      </div>

      {/* Value — PRECYZJA: mono font */}
      <div>
        <p className="flex items-baseline gap-1 leading-none">
          <span className="text-2xl font-mono font-semibold text-slate-100 tabular-nums">
            {value}
          </span>
          {suffix && (
            <span className="text-sm font-mono text-slate-500">{suffix}</span>
          )}
        </p>

        {/* Trend */}
        {hasTrend && (
          <div
            className={`flex items-center gap-1 mt-1.5 text-xs font-mono font-medium ${
              trendPositive ? 'text-go' : 'text-nogo'
            }`}
          >
            {trendPositive
              ? <TrendingUp  className="w-3 h-3" />
              : <TrendingDown className="w-3 h-3" />}
            <span>
              {trendPositive ? '+' : ''}{trend} {trendLabel}
            </span>
          </div>
        )}
      </div>
    </GlassCard>
  );
}
