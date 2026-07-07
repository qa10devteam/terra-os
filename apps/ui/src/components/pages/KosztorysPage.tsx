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

function fmtPLN(val: string | number | null | undefined) {
  if (val === null || val === undefined) return '—';
  const n = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(n)) return '—';
  return n.toLocaleString('pl-PL', { style: 'currency', currency: 'PLN', maximumFractionDigits: 0 });
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

  // ── Empty state — brak wybranego przetargu ──────────────────────────────────
  if (!tender) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
        <div className="w-20 h-20 rounded-2xl bg-earth-800 flex items-center justify-center border border-earth-700/40">
          <Calculator className="w-10 h-10 text-earth-500" />
        </div>
        <div>
          <p className="text-earth-200 font-semibold text-xl">Brak wybranego przetargu</p>
          <p className="text-earth-500 text-sm mt-2 max-w-xs mx-auto leading-relaxed">
            Wybierz przetarg z modułu Zwiad, aby zobaczyć kosztorys
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
      {/* Breadcrumb — Zwiad → Kosztorys */}
      <div>
        <div className="flex items-center gap-1.5 text-xs text-earth-600 mb-1.5">
          <span
            className="hover:text-earth-400 cursor-pointer transition-colors"
            onClick={() => setCurrentModule('zwiad')}
          >
            Zwiad
          </span>
          <ChevronRight className="w-3 h-3" />
          <span className="text-earth-400 font-medium">Kosztorys</span>
        </div>
        <h2 className="text-xl font-semibold text-earth-100">Kosztorys przetargu</h2>
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
          {/* Karty podsumowujące */}
          <div className="grid grid-cols-3 gap-4">
            {/* A — Dokumentacja projektowa */}
            <div className="glass-card rounded-xl p-4">
              <p className="text-earth-500 text-xs mb-0.5">Kosztorys A — Dokumentacja</p>
              <p className="text-earth-600 text-xs mb-2">Wycena wg dokumentacji przetargowej</p>
              <p className="text-earth-100 font-bold text-2xl font-mono tabular-nums">{fmtPLN(docTotal)}</p>
            </div>
            {/* B — Wycena własna */}
            <div className="glass-card rounded-xl p-4">
              <p className="text-earth-500 text-xs mb-0.5">Kosztorys B — Wycena własna</p>
              <p className="text-earth-600 text-xs mb-2">Wycena inwestorska firmy</p>
              <p className="text-earth-100 font-bold text-2xl font-mono tabular-nums">{fmtPLN(ownerTotal)}</p>
            </div>
            {/* Delta */}
            <div className={`glass-card rounded-xl p-4 border ${isFavorable ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
              <p className="text-earth-500 text-xs mb-0.5">Różnica (B − A)</p>
              <p className="text-earth-600 text-xs mb-2">
                {isFavorable ? 'Wycena własna niższa — korzystne' : 'Wycena własna wyższa — ryzyko marży'}
              </p>
              <div className="flex items-center gap-1.5">
                {isFavorable
                  ? <TrendingDown className="w-4 h-4 text-emerald-400" />
                  : <TrendingUp className="w-4 h-4 text-red-400" />}
                <p className={`font-bold text-2xl font-mono tabular-nums ${isFavorable ? 'text-emerald-400' : 'text-red-400'}`}>
                  {delta > 0 ? '+' : ''}{fmtPLN(delta)}
                </p>
              </div>
              <p className={`text-xs mt-1 font-mono ${isFavorable ? 'text-emerald-600' : 'text-red-500'}`}>
                {deltaPct > 0 ? '+' : ''}{deltaPct.toFixed(1)}% względem dokumentacji
              </p>
            </div>
          </div>

          {/* Tabele kosztorysowe — obok siebie */}
          <div className="grid grid-cols-2 gap-4">
            {[doc, owner].map((est) => {
              if (!est) return null;
              const label = est.variant === 'doc'
                ? 'Kosztorys A — Dokumentacja projektowa'
                : 'Kosztorys B — Wycena własna (inwestorska)';
              const chapters = groupByChapter(est.lines);
              return (
                <div key={est.id} className="glass-card rounded-xl overflow-hidden">
                  {/* Nagłówek tabeli */}
                  <div className="flex items-center justify-between px-4 py-3 border-b border-earth-800/60">
                    <span className="text-sm font-medium text-earth-200">{label}</span>
                    <span className="text-xs text-accent-primary font-mono tabular-nums font-bold">{fmtPLN(est.total_net_pln)}</span>
                  </div>

                  {/* Nagłówki kolumn tabeli */}
                  <div className="grid grid-cols-[2rem_1fr_3rem_4rem_5rem_5rem] px-4 py-2 border-b border-earth-800/40 bg-earth-900/40">
                    <span className="text-earth-600 text-xs font-semibold">Lp.</span>
                    <span className="text-earth-600 text-xs font-semibold">Opis</span>
                    <span className="text-earth-600 text-xs font-semibold text-center">Jedn.</span>
                    <span className="text-earth-600 text-xs font-semibold text-right">Ilość</span>
                    <span className="text-earth-600 text-xs font-semibold text-right">C.jedn.</span>
                    <span className="text-earth-600 text-xs font-semibold text-right">Wartość</span>
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
                              <span className="text-xs text-earth-500 font-mono tabular-nums">{fmtPLN(chTotal)}</span>
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
                                    <td className="px-2 py-1.5 text-earth-500 text-center whitespace-nowrap">{line.unit}</td>
                                    <td className="px-2 py-1.5 text-earth-400 text-right whitespace-nowrap font-mono tabular-nums">{parseFloat(line.quantity || '0').toLocaleString('pl-PL', { maximumFractionDigits: 2 })}</td>
                                    <td className="px-2 py-1.5 text-earth-500 text-right whitespace-nowrap font-mono tabular-nums">{parseFloat(line.unit_price || '0').toLocaleString('pl-PL', { maximumFractionDigits: 2 })}</td>
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

                  {/* Suma netto — duża, czytelna */}
                  <div className={`flex items-center justify-between px-4 py-3 border-t-2 ${isFavorable ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-red-500/20 bg-red-500/5'}`}>
                    <div>
                      <span className="text-xs font-semibold text-earth-300 uppercase tracking-wide">Razem netto</span>
                      <p className="text-earth-600 text-xs mt-0.5">Suma wszystkich pozycji bez VAT</p>
                    </div>
                    <span className="text-xl font-bold font-mono tabular-nums text-earth-100">{fmtPLN(est.total_net_pln)}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Wiersz delta — wyraźne podsumowanie różnicy */}
          <div className={`glass-card rounded-xl p-5 flex items-center justify-between border-2 ${isFavorable ? 'border-emerald-500/30' : 'border-red-500/30'}`}>
            <div className="flex items-center gap-4">
              {isFavorable
                ? <TrendingDown className="w-6 h-6 text-emerald-400 shrink-0" />
                : <TrendingUp className="w-6 h-6 text-red-400 shrink-0" />}
              <div>
                <p className="text-earth-300 text-sm font-semibold">
                  {isFavorable
                    ? '✓ Wycena własna jest niższa od dokumentacji'
                    : '⚠ Wycena własna jest wyższa od dokumentacji'}
                </p>
                <p className="text-earth-500 text-xs mt-0.5">
                  {isFavorable
                    ? 'Różnica (B − A): firma wyceniła taniej — korzystna marża'
                    : 'Różnica (B − A): firma wyceniła drożej — sprawdź ryzyko marży przed złożeniem oferty'}
                </p>
              </div>
            </div>
            <div className="text-right shrink-0 ml-4">
              <p className={`text-3xl font-bold font-mono tabular-nums ${isFavorable ? 'text-emerald-400' : 'text-red-400'}`}>
                {delta > 0 ? '+' : ''}{fmtPLN(delta)}
              </p>
              <p className={`text-xs font-mono mt-0.5 ${isFavorable ? 'text-emerald-600' : 'text-red-500'}`}>
                {deltaPct > 0 ? '+' : ''}{deltaPct.toFixed(2)}% względem dokumentacji
              </p>
            </div>
          </div>
        </>
      )}

      {/* Empty state — przetarg wybrany, ale brak kosztorysów */}
      {!loading && !error && estimates.length === 0 && (
        <div className="flex flex-col items-center justify-center flex-1 gap-4 text-center py-16">
          <div className="w-14 h-14 rounded-2xl bg-earth-800 flex items-center justify-center border border-earth-700/40">
            <Calculator className="w-7 h-7 text-earth-500" />
          </div>
          <div>
            <p className="text-earth-300 font-medium text-lg">Brak kosztorysów dla tego przetargu</p>
            <p className="text-earth-500 text-sm mt-1 max-w-xs mx-auto leading-relaxed">
              Uruchom wycenę w module Silnik, aby wygenerować kosztorys
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
