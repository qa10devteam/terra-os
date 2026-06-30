'use client';

import { motion } from 'motion/react';
import type { ReactNode } from 'react';

interface PageShellProps {
  /** Page title — rendered as an h1 */
  title: string;
  /** Optional subtitle below the title */
  subtitle?: string;
  /** Optional breadcrumb text or element shown above the title */
  breadcrumb?: ReactNode;
  /** Optional slot for action buttons, aligned to the right */
  actions?: ReactNode;
  children: ReactNode;
}

/**
 * PageShell — consistent wrapper for every module page.
 *
 * Provides entrance animation, standardised header layout (title + subtitle +
 * optional actions) and a max-width container so content never stretches to
 * full viewport width.
 */
export function PageShell({
  title,
  subtitle,
  breadcrumb,
  actions,
  children,
}: PageShellProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="pt-6 px-6 md:px-8 pb-10 max-w-7xl mx-auto w-full"
    >
      {/* ── Breadcrumb ───────────────────────────────────────────────── */}
      {breadcrumb && (
        <div className="mb-2 text-xs text-earth-600 font-medium tracking-wide uppercase">
          {breadcrumb}
        </div>
      )}

      {/* ── Header row ──────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-earth-100 tracking-tight leading-tight">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-1 text-sm text-earth-500">{subtitle}</p>
          )}
        </div>

        {/* Actions slot */}
        {actions && (
          <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>
        )}
      </div>

      {/* ── Page content ────────────────────────────────────────────── */}
      {children}
    </motion.div>
  );
}
