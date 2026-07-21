'use client';

// ── Types ──────────────────────────────────────────────────────────────────────

export type BadgeVariant =
  | 'new'
  | 'matched'
  | 'watching'
  | 'analyzing'
  | 'estimated'
  | 'decided_go'
  | 'decided_nogo'
  | 'archived'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'neutral';

interface StatusBadgeProps {
  status:     BadgeVariant | string;
  /** Override display label */
  label?:     string;
  size?:      'xs' | 'sm';
  /** GO/NO-GO badges animate in — disable for list renders */
  animate?:   boolean;
  className?: string;
}

// ── Config — Brand Bible BudOS: PRECYZJA · ZWIAD · PRZEWAGA ───────────────────
// Emerald = TYLKO sygnały decyzji (GO, active states)
// Indigo = score, analysis
// Slate = neutral states

const STATUS_MAP: Record<string, { label: string; cls: string; mono?: boolean }> = {
  // ── Decision signals (primary) ────────────────────────────────────────
  decided_go:   {
    label: 'GO',
    cls: 'bg-go-bg border-go-brd text-go',
    mono: true,
  },
  decided_nogo: {
    label: 'NO-GO',
    cls: 'bg-nogo-bg border-nogo-brd text-nogo',
    mono: true,
  },

  // ── Pipeline states ───────────────────────────────────────────────────
  new:          { label: 'Nowy',         cls: 'bg-ink-700 border-ink-line text-slate-300' },
  matched:      { label: 'Dopasowany',   cls: 'bg-score/10 border-score/20 text-score' },
  watching:     { label: 'Obserwowany',  cls: 'bg-sky-500/10 border-sky-500/20 text-sky-400' },
  analyzing:    { label: 'W analizie',   cls: 'bg-warn-bg border-warn/20 text-warn' },
  estimated:    { label: 'Wyceniony',    cls: 'bg-em-bg border-em-brd text-em' },
  archived:     { label: 'Archiwum',     cls: 'bg-ink-700 border-ink-line text-slate-500' },

  // ── Semantic ──────────────────────────────────────────────────────────
  success:      { label: 'OK',           cls: 'bg-go-bg border-go-brd text-go', mono: true },
  warning:      { label: 'Uwaga',        cls: 'bg-warn-bg border-warn/20 text-warn' },
  danger:       { label: 'Blad',         cls: 'bg-nogo-bg border-nogo-brd text-nogo', mono: true },
  info:         { label: 'Info',         cls: 'bg-score/10 border-score/20 text-score' },
  neutral:      { label: 'Neutralny',    cls: 'bg-ink-700 border-ink-line text-slate-500' },
};

// ── Component ──────────────────────────────────────────────────────────────────

export function StatusBadge({
  status,
  label,
  size      = 'sm',
  animate   = false,
  className = '',
}: StatusBadgeProps) {
  const cfg = STATUS_MAP[status] ?? {
    label: status,
    cls: 'bg-ink-700 border-ink-line text-slate-400',
    mono: false,
  };

  const displayLabel = label ?? cfg.label;

  const sizeClass = size === 'xs'
    ? 'px-1.5 py-0.5 text-[10px] tracking-wider'
    : 'px-2.5 py-1 text-xs tracking-wider';

  // GO/NO-GO animate in — spring pop (Brand Bible: go-pop 500ms)
  const animClass = animate && (status === 'decided_go' || status === 'decided_nogo')
    ? 'animate-go-pop'
    : '';

  return (
    <span
      className={[
        'inline-flex items-center rounded-md border font-semibold whitespace-nowrap uppercase',
        cfg.mono ? 'font-mono' : '',
        sizeClass,
        animClass,
        cfg.cls,
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {displayLabel}
    </span>
  );
}
