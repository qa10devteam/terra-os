import type { ReactNode } from 'react';

/**
 * Marketing layout — no sidebar, no auth required.
 * Covers: /, /budos, /pricing, /signup, /login, /terms, /privacy
 */
export default function MarketingLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
