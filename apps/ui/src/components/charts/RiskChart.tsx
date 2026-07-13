// Violin-like p10/p50/p90 chart dla Engine L2 wyników
import {
  ComposedChart,
  Bar,
  ErrorBar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

// ── Colour constants ───────────────────────────────────────────────────────────
const PRIMARY = '#10b981';
const DANGER  = '#ef4444';
const WARNING = '#f59e0b';

interface RiskChartProps {
  p10: number;
  p50: number;
  p90: number;
  current_price?: number;
  currency?: string;
}

export function RiskChart({ p10, p50, p90, current_price, currency = 'PLN' }: RiskChartProps) {
  const fmt = (v: number) =>
    new Intl.NumberFormat('pl-PL', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(v);

  const data = [{ name: 'Ryzyko', center: p50, error: [[p50 - p10], [p90 - p50]] }];

  return (
    <div className="w-full h-48 rounded-token-lg bg-earth-900 border border-earth-800 p-3">
      <div className="flex justify-between text-sm mb-2">
        <span className="text-accent-danger font-medium">P10: {fmt(p10)}</span>
        <span className="font-semibold text-earth-100">P50: {fmt(p50)}</span>
        <span className="text-accent-warning font-medium">P90: {fmt(p90)}</span>
      </div>
      <ResponsiveContainer width="100%" height={120}>
        <ComposedChart data={data} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
          <XAxis dataKey="name" tick={{ fill: 'var(--color-earth-400)', fontSize: 11 }} />
          <YAxis
            domain={[p10 * 0.95, p90 * 1.05]}
            tickFormatter={(v) =>
              new Intl.NumberFormat('pl-PL', { notation: 'compact' }).format(v)
            }
            tick={{ fill: 'var(--color-earth-400)', fontSize: 11 }}
          />
          <Tooltip
            formatter={(v: number) => fmt(v)}
            contentStyle={{
              background: 'var(--color-earth-800)',
              border: '1px solid var(--color-earth-700)',
              borderRadius: 8,
              color: 'var(--color-earth-100)',
            }}
          />
          <Bar dataKey="center" fill={PRIMARY} barSize={40}>
            <ErrorBar dataKey="error" width={4} strokeWidth={2} stroke={WARNING} />
            <Cell fill={PRIMARY} />
          </Bar>
        </ComposedChart>
      </ResponsiveContainer>
      {current_price && (
        <div className="text-xs text-center text-earth-500 mt-1">
          Twoja cena: {fmt(current_price)} —{' '}
          {current_price < p50 ? (
            <span className="text-accent-warning">⚠️ Poniżej mediany ryzyka</span>
          ) : (
            <span className="text-accent-primary">✅ Powyżej mediany</span>
          )}
        </div>
      )}
    </div>
  );
}
