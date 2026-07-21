import type { ReactNode } from 'react';

// ── Types ──────────────────────────────────────────────────────────────────────

interface GlassCardProps {
  children:   ReactNode;
  className?: string;
  /** default = standard card | elevated = stronger surface | flat = minimal */
  variant?:   'default' | 'elevated' | 'flat';
  /** Highlight = emerald border — active/selected state */
  highlight?: boolean;
  /** Forward click handler — renders as <button> when provided */
  onClick?:   () => void;
}

// ── Style map — Brand Bible BudOS ─────────────────────────────────────────────
// Ink backgrounds + subtle borders. NO gradients. NO blur in cards.
// hover: border tightens, surface lifts one level.

const VARIANT_CLS: Record<'default' | 'elevated' | 'flat', string> = {
  default:  'bg-ink-900 border border-ink-line shadow-sm',
  elevated: 'bg-ink-800 border border-ink-line-strong shadow-md',
  flat:     'bg-ink-900 border border-ink-line',
};

const HIGHLIGHT  = 'border-em-brd bg-ink-800';
const INTERACTIVE = 'cursor-pointer hover:border-ink-line-strong hover:bg-ink-800 transition-colors duration-150 text-left w-full';

// ── Component ──────────────────────────────────────────────────────────────────

export function GlassCard({
  children,
  className = '',
  variant   = 'default',
  highlight = false,
  onClick,
}: GlassCardProps) {
  const base = [
    'rounded-xl',
    highlight ? HIGHLIGHT : VARIANT_CLS[variant],
    onClick ? INTERACTIVE : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={base}>
        {children}
      </button>
    );
  }

  return (
    <div className={base}>
      {children}
    </div>
  );
}
