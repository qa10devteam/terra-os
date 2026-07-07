export function GlassCard({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`backdrop-blur-sm bg-earth-900/60 border border-earth-800/60 rounded-2xl ${className}`}>
      {children}
    </div>
  );
}
