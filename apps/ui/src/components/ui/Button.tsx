'use client';

import { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
type ButtonSize    = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:   ButtonVariant;
  size?:      ButtonSize;
  loading?:   boolean;
  /** Renders a full-width block button */
  fullWidth?: boolean;
  /** Icon to render before label */
  iconLeft?:  React.ReactNode;
  /** Icon to render after label */
  iconRight?: React.ReactNode;
}

// ── Style maps — Brand Bible BudOS ────────────────────────────────────────────
// primary = emerald (GO signal) — highest CTAs only
// secondary = ink surface — standard actions
// ghost = no bg — nav, inline
// danger = red signal — destructive

const VARIANT: Record<ButtonVariant, string> = {
  primary:
    'bg-em text-ink-950 font-semibold ' +
    'hover:bg-em-light ' +
    'border border-transparent',
  secondary:
    'bg-ink-800 text-slate-200 font-medium ' +
    'border border-ink-line ' +
    'hover:bg-ink-700 hover:border-ink-line-strong hover:text-slate-100',
  ghost:
    'text-slate-400 font-medium ' +
    'border border-transparent ' +
    'hover:bg-ink-800 hover:text-slate-200',
  danger:
    'bg-nogo-bg text-nogo font-medium ' +
    'border border-nogo-brd ' +
    'hover:bg-nogo/15 hover:border-red-500/35',
};

const SIZE: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs rounded-md gap-1.5 h-7',
  md: 'px-4 py-2 text-sm rounded-md gap-2 h-9',
  lg: 'px-5 py-2.5 text-base rounded-lg gap-2.5 h-11',
};

// ── Component ──────────────────────────────────────────────────────────────────

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant   = 'primary',
    size      = 'md',
    loading   = false,
    fullWidth = false,
    iconLeft,
    iconRight,
    children,
    disabled,
    className = '',
    ...rest
  },
  ref,
) {
  const isDisabled = disabled || loading;
  return (
    <button
      ref={ref}
      disabled={isDisabled}
      className={[
        'inline-flex items-center justify-center',
        'transition-all duration-150',
        'active:scale-[0.97]',
        'disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-em/60 focus-visible:ring-offset-1 focus-visible:ring-offset-ink-950',
        VARIANT[variant],
        SIZE[size],
        fullWidth ? 'w-full' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      {...rest}
    >
      {loading ? (
        <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
      ) : (
        iconLeft && <span className="shrink-0">{iconLeft}</span>
      )}
      {children && <span className="truncate">{children}</span>}
      {!loading && iconRight && <span className="shrink-0">{iconRight}</span>}
    </button>
  );
});

Button.displayName = 'Button';
