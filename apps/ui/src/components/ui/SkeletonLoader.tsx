export function SkeletonRow({ cols = 5 }: { cols?: number }) {
  return (
    <div className="flex gap-3 p-3">
      {Array(cols).fill(0).map((_, i) => (
        <div key={i} className="h-4 bg-earth-800/60 rounded animate-pulse flex-1" />
      ))}
    </div>
  );
}

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="p-4 rounded-xl bg-earth-900/60 border border-earth-800/50 animate-pulse space-y-2">
      {Array(lines).fill(0).map((_, i) => (
        <div key={i} className={`h-3 bg-earth-800/60 rounded ${i === lines - 1 ? 'w-1/2' : i === 0 ? 'w-3/4' : 'w-full'}`} />
      ))}
    </div>
  );
}

export function SkeletonBlock({ className = 'h-24' }: { className?: string }) {
  return <div className={`bg-earth-800/40 rounded-xl animate-pulse ${className}`} />;
}
