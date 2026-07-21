'use client';

interface SkeletonCardProps {
  /** Number of content lines to render (default: 3) */
  lines?: number;
  /** Extra Tailwind classes for the outer wrapper */
  className?: string;
  /** Show a header placeholder above the lines */
  showHeader?: boolean;
}

/**
 * SkeletonCard — shimmering placeholder for stat cards and content sections.
 *
 * Uses the `.skeleton` class defined in globals.css which applies the
 * horizontal sweep animation backed by `@keyframes shimmer`.
 */
export function SkeletonCard({
  lines = 3,
  className = '',
  showHeader = true,
}: SkeletonCardProps) {
  return (
    <div
      className={`rounded-xl border border-ink-800/60 bg-ink-900/60 p-4 space-y-3 ${className}`}
    >
      {/* Header placeholder */}
      {showHeader && (
        <div className="flex items-center justify-between mb-1">
          <div className="skeleton h-3.5 w-28 rounded" />
          <div className="skeleton h-4 w-4 rounded-full" />
        </div>
      )}

      {/* Line placeholders — each row varies in width for realism */}
      {Array.from({ length: lines }).map((_, i) => {
        const widths = ['w-full', 'w-4/5', 'w-3/5', 'w-2/3', 'w-full', 'w-1/2'];
        const w = widths[i % widths.length];
        return (
          <div key={i} className={`skeleton h-3 rounded ${w}`} />
        );
      })}

      {/* Bottom action stub */}
      <div className="pt-1 flex justify-end">
        <div className="skeleton h-7 w-20 rounded-md" />
      </div>
    </div>
  );
}
