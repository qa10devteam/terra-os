'use client';

import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { Loader2, AlertTriangle, TrendingUp } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────
interface TenderItem {
  id: string;
  title: string;
  buyer: string | null;
  value_pln: number | string | null;
  match_score: number | null;
  status: string;
}

// ── Config ────────────────────────────────────────────────────────────────────
const PIPELINE_STAGES = [
  { key: 'new',          label: 'Nowy',        desc: 'Świeżo z BZP',          color: '#60a5fa', borderColor: 'border-blue-500/30',   bg: 'bg-blue-500/8',    headerBg: 'bg-blue-500/15' },
  { key: 'matched',      label: 'Dopasowany',  desc: 'Pasuje do profilu',      color: '#a78bfa', borderColor: 'border-purple-500/30', bg: 'bg-purple-500/8',  headerBg: 'bg-purple-500/15' },
  { key: 'analyzing',    label: 'Analiza',     desc: 'Dokumentacja pobrana',   color: '#fbbf24', borderColor: 'border-yellow-500/30', bg: 'bg-yellow-500/8',  headerBg: 'bg-yellow-500/15' },
  { key: 'estimated',    label: 'Wyceniony',   desc: 'Kosztorys gotowy',       color: '#34d399', borderColor: 'border-emerald-500/30',bg: 'bg-emerald-500/8', headerBg: 'bg-emerald-500/15' },
  { key: 'decided_go',   label: 'GO ✓',        desc: 'Oferta złożona',         color: '#10b981', borderColor: 'border-emerald-600/40',bg: 'bg-emerald-600/8', headerBg: 'bg-emerald-600/20' },
  { key: 'decided_nogo', label: 'NO-GO',       desc: 'Rezygnacja',             color: '#f87171', borderColor: 'border-red-500/30',    bg: 'bg-red-500/8',     headerBg: 'bg-red-500/15' },
];

function fmtPLN(v: number | string | null | undefined) {
  if (v === null || v === undefined) return '—';
  const n = typeof v === 'string' ? parseFloat(v) : v;
  if (isNaN(n)) return '—';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + ' M';
  if (n >= 1_000) return (n / 1_000).toFixed(0) + ' k';
  return n.toFixed(0);
}

// ── Tender card ───────────────────────────────────────────────────────────────
function TenderCard({ tender, color }: { tender: TenderItem; color: string }) {
  const score = tender.match_score !== null ? Math.round(tender.match_score * 100) : null;
  const scoreColor = score === null ? '#71717a'
    : score >= 70 ? '#10b981'
    : score >= 40 ? '#F59E0B'
    : '#EF4444';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-3 rounded-xl bg-earth-900/60 border border-earth-800/50 hover:border-earth-700/70 hover:bg-earth-900 transition-all duration-200 cursor-pointer group"
    >
      <p className="text-earth-200 text-xs font-medium line-clamp-2 leading-snug group-hover:text-earth-100 transition-colors">
        {tender.title}
      </p>
      <p className="text-earth-600 text-xs mt-1.5 truncate">{tender.buyer ?? '—'}</p>
      <div className="flex items-center justify-between mt-2">
        <span className="text-earth-400 text-xs font-mono">
          {fmtPLN(tender.value_pln)} PLN
        </span>
        {score !== null && (
          <span
            className="text-xs font-bold px-1.5 py-0.5 rounded"
            style={{ color: scoreColor, backgroundColor: scoreColor + '20' }}
          >
            {score}%
          </span>
        )}
      </div>
    </motion.div>
  );
}

// ── Skeleton card ─────────────────────────────────────────────────────────────
function SkeletonCard() {
  return (
    <div className="p-3 rounded-xl bg-earth-900/60 border border-earth-800/50 animate-pulse">
      <div className="h-3 bg-earth-800 rounded w-full mb-1.5" />
      <div className="h-3 bg-earth-800 rounded w-3/4 mb-3" />
      <div className="h-2.5 bg-earth-800 rounded w-1/2" />
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export function PipelinePage() {
  const [tendersByStage, setTendersByStage] = useState<Record<string, TenderItem[]>>({});
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetch('/api/v1/tenders?limit=200')
      .then(r => { if (!r.ok) throw new Error(`Błąd ${r.status}`); return r.json(); })
      .then(data => {
        const items: TenderItem[] = data.items ?? [];
        const byStage: Record<string, TenderItem[]> = {};
        const c: Record<string, number> = {};
        for (const st of PIPELINE_STAGES) { byStage[st.key] = []; c[st.key] = 0; }
        for (const t of items) {
          if (byStage[t.status] !== undefined) {
            byStage[t.status].push(t);
            c[t.status]++;
          }
        }
        setTendersByStage(byStage);
        setCounts(c);
        setTotal(data.total ?? items.length);
        setLoading(false);
      })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  const goCount = counts['decided_go'] ?? 0;
  const activeTotal = Object.entries(counts)
    .filter(([k]) => k !== 'archived')
    .reduce((s, [, v]) => s + v, 0);
  const conversionRate = activeTotal > 0 ? ((goCount / activeTotal) * 100).toFixed(0) : '0';

  if (error) return (
    <div className="m-6 p-4 rounded-xl bg-accent-danger/10 border border-accent-danger/20 text-accent-danger text-sm flex gap-2">
      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />{error}
    </div>
  );

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-earth-800/60 flex items-center justify-between shrink-0">
        <div>
          <h2 className="text-lg font-semibold text-earth-100">Pipeline przetargów</h2>
          <p className="text-earth-500 text-xs mt-0.5">Przepływ przetargów przez etapy decyzyjne</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-center">
            <p className="text-xl font-bold text-earth-100 tabular-nums">{total}</p>
            <p className="text-earth-600 text-xs">Łącznie</p>
          </div>
          <div className="w-px h-8 bg-earth-800" />
          <div className="text-center">
            <p className="text-xl font-bold text-accent-primary tabular-nums">{goCount}</p>
            <p className="text-earth-600 text-xs">GO</p>
          </div>
          <div className="w-px h-8 bg-earth-800" />
          <div className="text-center">
            <p className="text-xl font-bold text-accent-info tabular-nums">{conversionRate}%</p>
            <p className="text-earth-600 text-xs">Konwersja</p>
          </div>
        </div>
      </div>

      {/* Kanban board */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden">
        <div className="flex gap-3 p-4 h-full min-w-max">
          {PIPELINE_STAGES.map((stage) => {
            const stageTenders = tendersByStage[stage.key] ?? [];
            const count = counts[stage.key] ?? 0;
            return (
              <div
                key={stage.key}
                className={`flex flex-col w-64 rounded-2xl border ${stage.borderColor} ${stage.bg} overflow-hidden`}
              >
                {/* Column header */}
                <div className={`px-3 py-2.5 ${stage.headerBg} border-b ${stage.borderColor} shrink-0`}>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold" style={{ color: stage.color }}>
                      {stage.label}
                    </span>
                    <span
                      className="text-xs font-bold px-2 py-0.5 rounded-full"
                      style={{ color: stage.color, backgroundColor: stage.color + '25' }}
                    >
                      {count}
                    </span>
                  </div>
                  <p className="text-earth-600 text-xs mt-0.5">{stage.desc}</p>
                </div>

                {/* Cards list — scrollable */}
                <div className="flex-1 overflow-y-auto p-2 space-y-2">
                  {loading
                    ? Array.from({ length: 2 }).map((_, i) => <SkeletonCard key={i} />)
                    : stageTenders.length === 0
                      ? (
                        <div className="py-6 text-center">
                          <TrendingUp className="w-5 h-5 text-earth-800 mx-auto mb-1" />
                          <p className="text-earth-700 text-xs">Brak przetargów</p>
                        </div>
                      )
                      : stageTenders.map(t => (
                        <TenderCard key={t.id} tender={t} color={stage.color} />
                      ))
                  }
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
