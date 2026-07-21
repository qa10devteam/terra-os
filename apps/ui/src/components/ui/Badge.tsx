'use client';

import type { ReactNode } from 'react';

// ── Types ──────────────────────────────────────────────────────────────────────

type BadgeColor = 'em' | 'go' | 'nogo' | 'warn' | 'indigo' | 'violet' | 'neutral';

interface BadgeProps {
  color?:    BadgeColor;
  children:  ReactNode;
  dot?:      boolean;
  className?: string;
}

// ── Color map ──────────────────────────────────────────────────────────────────

const BADGE_STYLES: Record<BadgeColor, string> = {
  em:      'bg-em/15 text-em border-em/25',
  go:      'bg-go/15 text-go border-go/25',
  nogo:    'bg-nogo/15 text-nogo border-nogo/25',
  warn:    'bg-warn/15 text-warn border-warn/25',
  indigo:  'bg-indigo/15 text-indigo-400 border-indigo/25',
  violet:  'bg-violet/15 text-violet-400 border-violet/25',
  neutral: 'bg-ink-800 text-slate-400 border-ink-700',
};

const DOT_COLORS: Record<BadgeColor, string> = {
  em:     'bg-em',
  go:     'bg-go',
  nogo:   'bg-nogo',
  warn:   'bg-warn',
  indigo: 'bg-indigo',
  violet: 'bg-violet-400',
  neutral:'bg-slate-500',
};

// ── Component ──────────────────────────────────────────────────────────────────

export function Badge({ color = 'neutral', children, dot = false, className = '' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium border ${BADGE_STYLES[color]} ${className}`}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${DOT_COLORS[color]}`} />}
      {children}
    </span>
  );
}
