import type { LucideIcon } from 'lucide-react';
import { GlassCard } from './GlassCard';

interface MetricCardProps {
  icon: LucideIcon;
  label: string;
  value: string | number;
  trend?: number;
  trendLabel?: string;
  iconColor?: string;
}

export function MetricCard({ icon: Icon, label, value, trend, trendLabel = 'w tym tygodniu', iconColor = 'text-accent-primary' }: MetricCardProps) {
  const trendPositive = trend !== undefined && trend >= 0;
  return (
    <GlassCard className="p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs text-earth-500 font-medium uppercase tracking-wide">{label}</span>
        <div className={`w-8 h-8 rounded-lg bg-earth-800/80 flex items-center justify-center ${iconColor}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div>
        <p className="text-2xl font-bold text-earth-100 tabular-nums">{value}</p>
        {trend !== undefined && (
          <p className={`text-xs mt-1 font-medium ${trendPositive ? 'text-emerald-400' : 'text-red-400'}`}>
            {trendPositive ? '+' : ''}{trend} {trendLabel}
          </p>
        )}
      </div>
    </GlassCard>
  );
}
