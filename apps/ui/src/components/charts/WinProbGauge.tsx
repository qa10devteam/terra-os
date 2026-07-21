import { PieChart, Pie, Cell } from 'recharts';

// ── Colour constants ───────────────────────────────────────────────────────────
const PRIMARY = '#10b981';
const WARNING = '#f59e0b';
const DANGER  = '#ef4444';

// Neutral track colour (ink-800 equivalent)
const TRACK = 'var(--color-ink-800)';

interface WinProbGaugeProps {
  probability: number; // 0.0 – 1.0
}

export function WinProbGauge({ probability }: WinProbGaugeProps) {
  const pct   = Math.round(probability * 100);
  const color = pct >= 60 ? PRIMARY : pct >= 40 ? WARNING : DANGER;

  return (
    <div className="flex flex-col items-center rounded-xl bg-ink-900 border border-ink-800 p-4">
      <p className="section-label mb-2">Prawdopodobieństwo wygranej</p>
      <PieChart width={120} height={70}>
        <Pie
          data={[{ v: pct }, { v: 100 - pct }]}
          cx={55}
          cy={60}
          startAngle={180}
          endAngle={0}
          innerRadius={40}
          outerRadius={55}
          dataKey="v"
        >
          <Cell fill={color} />
          <Cell fill={TRACK} />
        </Pie>
      </PieChart>
      <div className="-mt-6 text-2xl font-bold tabular-nums" style={{ color }}>
        {pct}%
      </div>
      <div className="text-xs text-slate-500 mt-1">Szanse wygranej</div>
    </div>
  );
}
