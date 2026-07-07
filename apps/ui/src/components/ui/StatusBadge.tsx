const STATUS_MAP: Record<string, { label: string; cls: string }> = {
  new:          { label: 'Nowy',        cls: 'bg-blue-500/15 text-blue-400' },
  matched:      { label: 'Dopasowany',  cls: 'bg-purple-500/15 text-purple-400' },
  watching:     { label: 'Obserwowany', cls: 'bg-sky-500/15 text-sky-400' },
  analyzing:    { label: 'Analiza',     cls: 'bg-yellow-500/15 text-yellow-400' },
  estimated:    { label: 'Wyceniony',   cls: 'bg-emerald-500/15 text-emerald-400' },
  decided_go:   { label: 'GO ✓',        cls: 'bg-green-500/20 text-green-400' },
  decided_nogo: { label: 'NO-GO',       cls: 'bg-red-500/15 text-red-400' },
  archived:     { label: 'Archiwum',    cls: 'bg-earth-700/40 text-earth-500' },
};

export function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_MAP[status] ?? { label: status, cls: 'bg-earth-700/40 text-earth-400' };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${cfg.cls}`}>
      {cfg.label}
    </span>
  );
}
