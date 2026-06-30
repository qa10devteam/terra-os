'use client';

import { useState, useEffect } from 'react';
import { useStore } from '@/store/useStore';
import {
  Calculator, ChevronDown, ChevronUp, AlertCircle,
  ArrowRight, TrendingUp, TrendingDown, ChevronRight,
} from 'lucide-react';

interface EstimateLine {
  position_no: string;
  description: string;
  unit: string;
  quantity: string;
  unit_price: string;
  line_total_pln: string;
  knr_code?: string | null;
  chapter?: string | null;
}

interface Estimate {
  id: string;
  variant: 'doc' | 'owner';
  total_net_pln: string;
  lines: EstimateLine[];
  params: Record<string, unknown>;
}

function fmt(val: string | number | null | undefined) {
  if (val === null || val === undefined) return '—';
  const n = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(n)) return '—';
  return n.toLocaleString('pl-PL', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + ' PLN';
}

function groupByChapter(lines: EstimateLine[]) {
  const chapters: Record<string, EstimateLine[]> = {};
  for (const l of lines) {
    const ch = l.chapter || 'Pozostałe';
    if (!chapters[ch]) chapters[ch] = [];
    chapters[ch].push(l);
  }
  return chapters;
}

function SkeletonCard() {
  return (
    <div className="glass-card rounded-xl p-4 animate-pulse">
      <div className="h-3 w-24 bg-earth-700 rounded mb-2" />
      <div className="h-6 w-36 bg-earth-700 rounded mb-1" />
      <div className="h-2.5 w-20 bg-earth-800 rounded" />
    </div>
  );
}

function SkeletonTable() {
  return (
    <div className="glass-card rounded-xl overflow-hidden animate-pulse">
      <div className="px-4 py-3 border-b border-earth-800/60 flex justify-between">
        <div className="h-4 w-32 bg-earth-700 rounded" />
        <div className="h-4 w-24 bg-earth-700 rounded" />
      </div>
      {[1, 2, 3, 4].map(i => (
        <div key={i} className="px-4 py-3 border-b border-earth-800/30 flex justify-between">
          <div className="h-3 w-48 bg-earth-800 rounded" />
          <div className="h-3 w-20 bg-earth-800 rounded" />
        </div>
      ))}
    </div>
  );
}

export function KosztorysPage() {
  const { selectedTender, setCurrentModule } = useStore();
  const tender = selectedTender as any;

  const [estimates, setEstimates] = useState<Estimate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedChapters, setExpandedChapters] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (!tender?.id) return;
    setLoading(true);
    setError(null);
    fetch(`/api/v1/tenders/${tender.id}/estimates`)
      .then(r => {
        if (!r.ok) throw new Error(r.status === 404 ? 'Brak kosztorysów dla tego przetargu' : `Błąd ${r.status}`);
        return r.json();
      })
      .then((data: Estimate[]) => { setEstimates(data); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [tender?.id]);

  if (!tender) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
        <div className="w-20 h-20 rounded-2xl bg-earth-800 flex items-center justify-center border border-earth-700/40">
          <Calculator className="w-10 h-10 text-earth-500" />
        </div>
        <div>
          <p className="text-earth-200 font-semibold text-xl">Brak wybranego przetargu</p>
          <p className="text-earth-500 text-sm mt-2 max-w-xs mx-auto leading-relaxed">
            Wybierz przetarg ze Zwiadu aby zobaczyć kosztorys
          </p>
        </div>
        <button
          onClick={() => setCurrentModule('zwiad')}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent-primary/10 text-accent-primary hover:bg-accent-primary/20 transition-colors text-sm font-medium border border-accent-primary/20"
        >
          Przejdź do Zwiadu <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    );
  }

  const doc = estimates.find(e => e.variant === 'doc');
  const owner = estimates.find(e => e.variant === 'owner');
  const docTotal = doc ? parseFloat(doc.total_net_pln) : 0;
  const ownerTotal = owner ? parseFloat(owner.total_net_pln) : 0;
  const delta = ownerTotal - docTotal;
  const deltaPct = docTotal > 0 ? ((delta / docTotal) * 100) : 0;
  const isFavorable = delta <= 0;

  const toggleChapter = (ch: string) =>
    setExpandedChapters(prev => ({ ...prev, [ch]: !prev[ch] }));

  return (
    <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto">
      {/* Breadcrumb + Header */}
      <div>
        <div className="flex items-center gap-1.5 text-xs text-earth-600 mb-1.5">
          <span className="hover:text-earth-400 cursor-pointer" onClick={() => setCurrentModule('zwiad')}>Zwiad</span>
          <ChevronRight className="w-3 h-3" />
          <span className="text-earth-400">Kosztorys</span>
        </div>
        <h2 className="text-xl font-semibold text-earth-100">Kosztorys</h2>
        <p className="text-earth-500 text-sm mt-0.5 line-clamp-1">{tender.title}</p>
      </div>

      {/* Skeleton */}
      {loading && (
        <>
          <div className="grid grid-cols-3 gap-4">
            <SkeletonCard /><SkeletonCard /><SkeletonCard />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <SkeletonTable /><SkeletonTable />
          </div>
        </>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {!loading && !error && estimates.length > 0 && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-3 gap-4">
            <div className="glass-card rounded-xl p-4">
              <p className="text-earth-500 text-xs mb-1">Dokumentacja (A)</p>
              <p className="text-earth-100 font-semibold text-lg font-mono tabular-nums">{fmt(docTotal)}</p>
              <p className="text-earth-600 text-xs mt-0.5">wariant docs</p>
            </div>
            <div className="glass-card rounded-xl p-4">
              <p className="text-earth-500 text-xs mb-1">Inwestorski (B)</p>
              <p className="text-earth-100 font-semibold text-lg font-mono tabular-nums">{fmt(ownerTotal)}</p>
              <p className="text-earth-600 text-xs mt-0.5">wariant owner</p>
            </div>
            {/* Delta card */}
            <div className={`glass-card rounded-xl p-4 border ${isFavorable ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
              <p className="text-earth-500 text-xs mb-1">Delta (B − A)</p>
              <div className="flex items-center gap-1.5">
                {isFavorable
                  ? <TrendingDown className="w-4 h-4 text-emerald-400" />
                  : <TrendingUp className="w-4 h-4 text-red-400" />}
                <p className={`font-semibold text-lg font-mono tabular-nums ${isFavorable ? 'text-emerald-400' : 'text-red-400'}`}>
                  {delta > 0 ? '+' : ''}{fmt(delta)}
                </p>
              </div>
              <p className={`text-xs mt-0.5 font-mono ${isFavorable ? 'text-emerald-600' : 'text-red-500'}`}>
                {deltaPct > 0 ? '+' : ''}{deltaPct.toFixed(1)}% vs dokumentacja
              </p>
            </div>
          </div>

          {/* Side-by-side tables */}
          <div className="grid grid-cols-2 gap-4">
            {[doc, owner].map((est) => {
              if (!est) return null;
              const label = est.variant === 'doc' ? 'Dokumentacja (A)' : 'Inwestorski (B)';
              const chapters = groupByChapter(est.lines);
              return (
                <div key={est.id} className="glass-card rounded-xl overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-earth-800/60">
                    <span className="text-sm font-medium text-earth-200">{label}</span>
                    <span className="text-xs text-accent-primary font-mono tabular-nums">{fmt(est.total_net_pln)}</span>
                  </div>
                  <div className="divide-y divide-earth-800/40">
                    {Object.entries(chapters).map(([ch, lines]) => {
                      const chKey = `${est.variant}-${ch}`;
                      const expanded = expandedChapters[chKey] !== false;
                      const chTotal = lines.reduce((s, l) => s + parseFloat(l.line_total_pln || '0'), 0);
                      return (
                        <div key={chKey}>
                          <button
                            onClick={() => toggleChapter(chKey)}
                            className="w-full flex items-center justify-between px-4 py-2 hover:bg-earth-800/30 transition-colors text-left"
                          >
                            <span className="text-xs font-medium text-earth-300">{ch}</span>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-earth-500 font-mono tabular-nums">{fmt(chTotal)}</span>
                              {expanded
                                ? <ChevronUp className="w-3 h-3 text-earth-600" />
                                : <ChevronDown className="w-3 h-3 text-earth-600" />}
                            </div>
                          </button>
                          {expanded && (
                            <table className="w-full text-xs">
                              <tbody>
                                {lines.map((line, i) => (
                                  <tr key={i} className="hover:bg-earth-800/20 border-t border-earth-800/30">
                                    <td className="pl-6 pr-2 py-1.5 text-earth-600 w-8">{line.position_no}</td>
                                    <td className="px-2 py-1.5 text-earth-300">{line.description}</td>
                                    <td className="px-2 py-1.5 text-earth-500 text-right whitespace-nowrap">{line.quantity} {line.unit}</td>
                                    <td className="pl-2 pr-4 py-1.5 text-earth-400 text-right whitespace-nowrap font-mono tabular-nums">
                                      {parseFloat(line.line_total_pln || '0').toLocaleString('pl-PL', { maximumFractionDigits: 0 })}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          )}
                        </div>
                      );
                    })}
                  </div>
                  {/* Chapter delta row */}
                  <div className={`flex items-center justify-between px-4 py-2.5 border-t-2 ${isFavorable ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-red-500/20 bg-red-500/5'}`}>
                    <span className="text-xs font-semibold text-earth-300">RAZEM NETTO</span>
                    <span className="text-sm font-bold font-mono tabular-nums text-earth-100">{fmt(est.total_net_pln)}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Delta summary row */}
          <div className={`glass-card rounded-xl p-4 flex items-center justify-between border ${isFavorable ? 'border-emerald-500/30' : 'border-red-500/30'}`}>
            <div className="flex items-center gap-3">
              {isFavorable
                ? <TrendingDown className="w-5 h-5 text-emerald-400" />
                : <TrendingUp className="w-5 h-5 text-red-400" />}
              <div>
                <p className="text-earth-400 text-xs">Różnica kosztorysów (B minus A)</p>
                <p className={`text-sm font-medium ${isFavorable ? 'text-emerald-300' : 'text-red-300'}`}>
                  {isFavorable ? 'Wariant inwestorski jest korzystniejszy' : 'Wariant inwestorski jest droższy'}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className={`text-2xl font-bold font-mono tabular-nums ${isFavorable ? 'text-emerald-400' : 'text-red-400'}`}>
                {delta > 0 ? '+' : ''}{fmt(delta)}
              </p>
              <p className={`text-xs font-mono ${isFavorable ? 'text-emerald-600' : 'text-red-500'}`}>
                {deltaPct > 0 ? '+' : ''}{deltaPct.toFixed(2)}%
              </p>
            </div>
          </div>
        </>
      )}

      {!loading && !error && estimates.length === 0 && (
        <div className="flex flex-col items-center justify-center flex-1 gap-4 text-center py-16">
          <div className="w-14 h-14 rounded-2xl bg-earth-800 flex items-center justify-center border border-earth-700/40">
            <Calculator className="w-7 h-7 text-earth-500" />
          </div>
          <div>
            <p className="text-earth-300 font-medium">Brak kosztorysów</p>
            <p className="text-earth-500 text-sm mt-1">Uruchom wycenę przez Silnik decyzyjny</p>
          </div>
        </div>
      )}
    </div>
  );
}
