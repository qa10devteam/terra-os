'use client';

import { useState, useEffect } from 'react';
import { useStore } from '@/store/useStore';
import {
  Scale, CheckCircle, XCircle, AlertCircle, ArrowRight,
  TrendingUp, TrendingDown, ThumbsUp, ThumbsDown, Loader2,
} from 'lucide-react';

interface EngineResult {
  feasible: boolean;
  violations: { severity: string; message: string }[];
  risk: {
    margin_p10: number;
    margin_p50: number;
    margin_p90: number;
    drivers: { factor: string; ST: number }[];
  } | null;
}

interface CompareResult {
  doc_total: string;
  owner_total: string;
  delta_pln: string;
  margin_headroom_pct: string;
}

function fmtPLN(val: string | number | null | undefined) {
  if (val === null || val === undefined) return '—';
  const n = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(n)) return '—';
  return n.toLocaleString('pl-PL', { style: 'currency', currency: 'PLN', maximumFractionDigits: 0 });
}

// Status → polska etykieta
const STATUS_LABELS: Record<string, string> = {
  decided_go: 'GO ✓',
  decided_nogo: 'NO-GO ✗',
};

type ToastState = { type: 'success' | 'error'; message: string } | null;

export function DecyzjaPage() {
  const { selectedTender, setCurrentModule } = useStore();
  const tender = selectedTender as any;

  const [engine, setEngine] = useState<EngineResult | null>(null);
  const [compare, setCompare] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionStatus, setActionStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastState>(null);

  useEffect(() => {
    if (!tender?.id) return;
    setLoading(true);
    setError(null);
    Promise.all([
      fetch(`/api/v1/tenders/${tender.id}/engine`).then(r => r.ok ? r.json() : null).catch(() => null),
      fetch(`/api/v1/tenders/${tender.id}/estimate/compare`).then(r => r.ok ? r.json() : null).catch(() => null),
    ]).then(([eng, cmp]) => {
      setEngine(eng);
      setCompare(cmp);
      setLoading(false);
    });
  }, [tender?.id]);

  // Toast auto-dismiss
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(t);
  }, [toast]);

  const takeAction = (status: 'decided_go' | 'decided_nogo') => {
    if (!tender?.id) return;
    setActionStatus('loading');
    fetch(`/api/v1/tenders/${tender.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
      .then(r => { if (!r.ok) throw new Error(`Błąd ${r.status}`); return r.json(); })
      .then(() => {
        setActionStatus(status);
        const statusLabel = STATUS_LABELS[status] ?? status;
        setToast({
          type: 'success',
          message: `Decyzja zapisana — przetarg przesunięty do statusu: ${statusLabel}`,
        });
      })
      .catch((e) => {
        setActionStatus('error');
        setToast({ type: 'error', message: `Błąd zapisu decyzji: ${e.message}` });
      });
  };

  // ── Empty state — nie wybrano przetargu ─────────────────────────────────────
  if (!tender) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
        <div className="w-20 h-20 rounded-2xl bg-earth-800 flex items-center justify-center border border-earth-700/40">
          <Scale className="w-10 h-10 text-earth-500" />
        </div>
        <div>
          <p className="text-earth-200 font-semibold text-xl">Wybierz przetarg z wyceną</p>
          <p className="text-earth-500 text-sm mt-2 max-w-xs mx-auto leading-relaxed">
            Wybierz przetarg z wyceną do podjęcia decyzji — GO (złóż ofertę) lub NO-GO (odrzuć)
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

  // Determine recommendation
  const blockCount = engine?.violations?.filter(v => v.severity === 'block').length ?? 0;
  const warnCount = engine?.violations?.filter(v => v.severity === 'warn').length ?? 0;
  const margin = engine?.risk?.margin_p50 ?? null;
  let recommendation: 'GO' | 'NO-GO' | 'NEGOCJUJ' = 'NEGOCJUJ';
  if (!engine) recommendation = 'NEGOCJUJ';
  else if (!engine.feasible || blockCount > 0) recommendation = 'NO-GO';
  else if (margin !== null && margin > 0.08) recommendation = 'GO';
  else if (margin !== null && margin < 0.03) recommendation = 'NO-GO';
  else recommendation = 'NEGOCJUJ';

  const recConfig = {
    'GO': {
      bg: 'bg-emerald-500/10 border-emerald-500/40',
      textColor: 'text-emerald-400',
      iconBg: 'bg-emerald-500/20',
      icon: <CheckCircle className="w-10 h-10 text-emerald-400" />,
      subtitle: 'Złóż ofertę — warunki sprzyjające, marża akceptowalna',
      explanation: 'System rekomenduje złożenie oferty. Ostateczna decyzja należy do kierownika budowy.',
    },
    'NO-GO': {
      bg: 'bg-red-500/10 border-red-500/40',
      textColor: 'text-red-400',
      iconBg: 'bg-red-500/20',
      icon: <XCircle className="w-10 h-10 text-red-400" />,
      subtitle: 'Odrzuć przetarg — zbyt wysokie ryzyko lub blokady systemowe',
      explanation: 'System rekomenduje rezygnację. Sprawdź naruszenia reguł w module Silnik.',
    },
    'NEGOCJUJ': {
      bg: 'bg-yellow-500/10 border-yellow-500/40',
      textColor: 'text-yellow-400',
      iconBg: 'bg-yellow-500/20',
      icon: <AlertCircle className="w-10 h-10 text-yellow-400" />,
      subtitle: 'Warunki graniczne — rozważ negocjacje przed złożeniem oferty',
      explanation: 'Marża jest na granicy akceptowalności. Zalecane negocjacje warunków umowy.',
    },
  };
  const rec = recConfig[recommendation];

  const delta = compare ? parseFloat(compare.delta_pln) : 0;
  const headroom = compare ? parseFloat(compare.margin_headroom_pct) : null;

  return (
    <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-earth-100">Decyzja — GO / NO-GO</h2>
        <p className="text-earth-500 text-sm mt-0.5">Zatwierdź lub odrzuć udział w przetargu</p>
        <p className="text-earth-600 text-xs mt-1 line-clamp-1">{tender.title}</p>
      </div>

      {loading && (
        <div className="flex items-center gap-3 text-earth-500">
          <div className="w-4 h-4 border-2 border-earth-700 border-t-accent-primary rounded-full animate-spin" />
          Ładowanie danych analizy…
        </div>
      )}

      {/* Toast — potwierdzenie decyzji */}
      {toast && (
        <div className={`flex items-center gap-3 p-4 rounded-xl border text-sm font-medium ${
          toast.type === 'success'
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
            : 'bg-red-500/10 border-red-500/30 text-red-300'
        }`}>
          {toast.type === 'success' ? <CheckCircle className="w-5 h-5 shrink-0" /> : <XCircle className="w-5 h-5 shrink-0" />}
          {toast.message}
        </div>
      )}

      {!loading && (
        <>
          {/* Verdict banner — DUŻY, z pełnym wyjaśnieniem */}
          <div className={`rounded-2xl p-6 border-2 ${rec.bg}`}>
            <div className="flex items-start gap-5">
              <div className={`w-18 h-18 rounded-2xl flex items-center justify-center shrink-0 p-3 ${rec.iconBg}`}>
                {rec.icon}
              </div>
              <div className="flex-1">
                <p className="text-earth-500 text-xs font-medium uppercase tracking-wider mb-1">
                  Rekomendacja systemu
                </p>
                <p className={`text-5xl font-black tracking-tight leading-none ${rec.textColor}`}>
                  {recommendation}
                </p>
                <p className={`text-base font-semibold mt-2 ${rec.textColor}`}>
                  {rec.subtitle}
                </p>
                <p className="text-earth-400 text-sm mt-1 leading-relaxed">
                  {rec.explanation}
                </p>
              </div>
            </div>
          </div>

          {/* Trzy metryki — polskie etykiety, PLN sformatowane */}
          <div className="grid grid-cols-3 gap-4">
            {/* Różnica kosztorysów */}
            <div className="glass-card rounded-xl p-4">
              <p className="text-earth-500 text-xs mb-0.5">Różnica kosztorysów (B − A)</p>
              <p className="text-earth-600 text-xs mb-3">Wycena własna minus dokumentacja</p>
              {compare ? (
                <div>
                  <div className="flex items-center gap-2">
                    {delta > 0
                      ? <TrendingUp className="w-4 h-4 text-red-400" />
                      : <TrendingDown className="w-4 h-4 text-emerald-400" />}
                    <span className={`text-xl font-bold font-mono tabular-nums ${delta > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                      {delta > 0 ? '+' : ''}{fmtPLN(delta)}
                    </span>
                  </div>
                  {headroom !== null && (
                    <p className="text-earth-500 text-xs mt-1.5">
                      Przestrzeń marżowa:{' '}
                      <span className={headroom < 0 ? 'text-red-400' : 'text-emerald-400'}>
                        {headroom.toFixed(2)}%
                      </span>
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-earth-600 text-sm">Brak kosztorysów — uruchom wycenę</p>
              )}
            </div>

            {/* Marża P50 */}
            <div className="glass-card rounded-xl p-4">
              <p className="text-earth-500 text-xs mb-0.5">Marża P50 — najbardziej prawdopodobna</p>
              <p className="text-earth-600 text-xs mb-3">Wynik symulacji Monte Carlo</p>
              {engine?.risk ? (
                <div>
                  <p className="text-yellow-400 font-black text-3xl">
                    {(engine.risk.margin_p50 * 100).toFixed(1)}%
                  </p>
                  <div className="flex gap-3 mt-2">
                    <span className="text-xs text-earth-600">
                      P10 (pesym.): <span className="text-red-400">{(engine.risk.margin_p10 * 100).toFixed(1)}%</span>
                    </span>
                    <span className="text-xs text-earth-600">
                      P90 (optym.): <span className="text-emerald-400">{(engine.risk.margin_p90 * 100).toFixed(1)}%</span>
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-earth-600 text-sm">Brak danych — uruchom Silnik decyzyjny</p>
              )}
            </div>

            {/* Naruszenia reguł */}
            <div className="glass-card rounded-xl p-4">
              <p className="text-earth-500 text-xs mb-0.5">Naruszenia reguł</p>
              <p className="text-earth-600 text-xs mb-3">Wykryte przez silnik decyzyjny</p>
              {engine ? (
                <div>
                  <p className={`font-black text-3xl ${blockCount > 0 ? 'text-red-400' : warnCount > 0 ? 'text-yellow-400' : 'text-emerald-400'}`}>
                    {engine.violations?.length ?? 0}
                  </p>
                  <div className="flex gap-3 mt-2">
                    <span className="text-xs text-earth-600">
                      Blokady: <span className="text-red-400">{blockCount}</span>
                    </span>
                    <span className="text-xs text-earth-600">
                      Ostrzeżenia: <span className="text-yellow-400">{warnCount}</span>
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-earth-600 text-sm">Brak danych silnika</p>
              )}
            </div>
          </div>

          {/* Kluczowe czynniki ryzyka */}
          {engine?.risk && engine.risk.drivers.length > 0 && (
            <div className="glass-card rounded-xl p-4">
              <p className="text-earth-500 text-xs mb-1">Kluczowe czynniki ryzyka (top 5)</p>
              <p className="text-earth-600 text-xs mb-3">Czynniki o największym wpływie na marżę — z analizy Monte Carlo</p>
              <div className="flex flex-wrap gap-2">
                {engine.risk.drivers.slice(0, 5).map((d, i) => (
                  <span key={i} className="text-xs px-2.5 py-1 rounded-full bg-earth-800 text-earth-300 border border-earth-700/40">
                    {d.factor}{' '}
                    <span className="text-earth-500">({(d.ST * 100).toFixed(0)}% wpływu)</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Przyciski decyzji */}
          {actionStatus === 'decided_go' ? (
            <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              <CheckCircle className="w-5 h-5 shrink-0" />
              <div>
                <p className="font-semibold">Decyzja GO zapisana</p>
                <p className="text-xs text-emerald-600 mt-0.5">Przetarg przesunięty do statusu: GO ✓ — prześlij do realizacji</p>
              </div>
            </div>
          ) : actionStatus === 'decided_nogo' ? (
            <div className="flex items-center gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400">
              <XCircle className="w-5 h-5 shrink-0" />
              <div>
                <p className="font-semibold">Decyzja NO-GO zapisana</p>
                <p className="text-xs text-red-600 mt-0.5">Przetarg przesunięty do statusu: NO-GO ✗ — oznaczony jako odrzucony</p>
              </div>
            </div>
          ) : (
            <div className="flex gap-4 mt-2">
              <button
                onClick={() => takeAction('decided_go')}
                disabled={actionStatus === 'loading'}
                className="flex-1 flex items-center justify-center gap-2 py-4 rounded-xl bg-emerald-500 text-white font-bold text-sm hover:bg-emerald-400 transition-colors disabled:opacity-50 shadow-lg shadow-emerald-500/20"
              >
                {actionStatus === 'loading'
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <ThumbsUp className="w-5 h-5" />}
                Zatwierdź GO — prześlij do realizacji
              </button>
              <button
                onClick={() => takeAction('decided_nogo')}
                disabled={actionStatus === 'loading'}
                className="flex-1 flex items-center justify-center gap-2 py-4 rounded-xl bg-earth-800 text-earth-300 font-bold text-sm hover:bg-earth-700 transition-colors disabled:opacity-50 border border-earth-700"
              >
                {actionStatus === 'loading'
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <ThumbsDown className="w-5 h-5" />}
                Odrzuć — oznacz jako NO-GO
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
