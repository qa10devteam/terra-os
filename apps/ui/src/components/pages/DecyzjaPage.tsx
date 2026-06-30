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

function fmt(val: string | number | null | undefined) {
  if (val === null || val === undefined) return '—';
  const n = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(n)) return '—';
  return n.toLocaleString('pl-PL', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + ' PLN';
}

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
        setToast({
          type: 'success',
          message: status === 'decided_go' ? '✅ Decyzja GO — oferta będzie złożona' : '❌ Przetarg odrzucony',
        });
      })
      .catch((e) => {
        setActionStatus('error');
        setToast({ type: 'error', message: `Błąd: ${e.message}` });
      });
  };

  if (!tender) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
        <div className="w-20 h-20 rounded-2xl bg-earth-800 flex items-center justify-center border border-earth-700/40">
          <Scale className="w-10 h-10 text-earth-500" />
        </div>
        <div>
          <p className="text-earth-200 font-semibold text-xl">Nie wybrano przetargu</p>
          <p className="text-earth-500 text-sm mt-2 max-w-xs mx-auto leading-relaxed">
            Przejdź do Zwiadu i wybierz przetarg, aby podjąć decyzję
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
      icon: <CheckCircle className="w-9 h-9 text-emerald-400" />,
      subtitle: 'Złóż ofertę — warunki sprzyjające',
    },
    'NO-GO': {
      bg: 'bg-red-500/10 border-red-500/40',
      textColor: 'text-red-400',
      iconBg: 'bg-red-500/20',
      icon: <XCircle className="w-9 h-9 text-red-400" />,
      subtitle: 'Odrzuć przetarg — zbyt wysokie ryzyko',
    },
    'NEGOCJUJ': {
      bg: 'bg-yellow-500/10 border-yellow-500/40',
      textColor: 'text-yellow-400',
      iconBg: 'bg-yellow-500/20',
      icon: <AlertCircle className="w-9 h-9 text-yellow-400" />,
      subtitle: 'Warunki graniczne — rozważ negocjacje',
    },
  };
  const rec = recConfig[recommendation];

  const delta = compare ? parseFloat(compare.delta_pln) : 0;
  const headroom = compare ? parseFloat(compare.margin_headroom_pct) : null;

  return (
    <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-earth-100">Decyzja</h2>
        <p className="text-earth-500 text-sm mt-0.5 line-clamp-1">{tender.title}</p>
      </div>

      {loading && (
        <div className="flex items-center gap-3 text-earth-500">
          <div className="w-4 h-4 border-2 border-earth-700 border-t-accent-primary rounded-full animate-spin" />
          Ładowanie danych…
        </div>
      )}

      {/* Toast notification */}
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
          {/* Verdict card */}
          <div className={`rounded-2xl p-6 flex items-center gap-5 border-2 ${rec.bg}`}>
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center shrink-0 ${rec.iconBg}`}>
              {rec.icon}
            </div>
            <div className="flex-1">
              <p className="text-earth-500 text-xs font-medium uppercase tracking-wider mb-0.5">Rekomendacja systemu</p>
              <p className={`text-4xl font-black tracking-tight ${rec.textColor}`}>{recommendation}</p>
              <p className="text-earth-400 text-sm mt-1">{rec.subtitle}</p>
            </div>
          </div>

          {/* Three metrics side by side */}
          <div className="grid grid-cols-3 gap-4">
            {/* Delta kosztorys */}
            <div className="glass-card rounded-xl p-4">
              <p className="text-earth-500 text-xs mb-3">Delta kosztorys (B − A)</p>
              {compare ? (
                <div>
                  <div className="flex items-center gap-2">
                    {delta > 0
                      ? <TrendingUp className="w-4 h-4 text-red-400" />
                      : <TrendingDown className="w-4 h-4 text-emerald-400" />}
                    <span className={`text-xl font-bold font-mono tabular-nums ${delta > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                      {delta > 0 ? '+' : ''}{fmt(delta)}
                    </span>
                  </div>
                  {headroom !== null && (
                    <p className="text-earth-500 text-xs mt-1.5">
                      Headroom: <span className={headroom < 0 ? 'text-red-400' : 'text-emerald-400'}>{headroom.toFixed(2)}%</span>
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-earth-600 text-sm">Brak kosztorysów</p>
              )}
            </div>

            {/* Marża P50 */}
            <div className="glass-card rounded-xl p-4">
              <p className="text-earth-500 text-xs mb-3">Marża P50 (mediana)</p>
              {engine?.risk ? (
                <div>
                  <p className="text-yellow-400 font-black text-3xl">
                    {(engine.risk.margin_p50 * 100).toFixed(1)}%
                  </p>
                  <div className="flex gap-3 mt-2">
                    <span className="text-xs text-earth-600">P10: <span className="text-red-400">{(engine.risk.margin_p10 * 100).toFixed(1)}%</span></span>
                    <span className="text-xs text-earth-600">P90: <span className="text-emerald-400">{(engine.risk.margin_p90 * 100).toFixed(1)}%</span></span>
                  </div>
                </div>
              ) : (
                <p className="text-earth-600 text-sm">Brak danych — uruchom Silnik</p>
              )}
            </div>

            {/* Violations count */}
            <div className="glass-card rounded-xl p-4">
              <p className="text-earth-500 text-xs mb-3">Naruszenia reguł</p>
              {engine ? (
                <div>
                  <p className={`font-black text-3xl ${blockCount > 0 ? 'text-red-400' : warnCount > 0 ? 'text-yellow-400' : 'text-emerald-400'}`}>
                    {engine.violations?.length ?? 0}
                  </p>
                  <div className="flex gap-3 mt-2">
                    <span className="text-xs text-earth-600">Blok: <span className="text-red-400">{blockCount}</span></span>
                    <span className="text-xs text-earth-600">Warn: <span className="text-yellow-400">{warnCount}</span></span>
                  </div>
                </div>
              ) : (
                <p className="text-earth-600 text-sm">Brak danych silnika</p>
              )}
            </div>
          </div>

          {/* Key drivers */}
          {engine?.risk && engine.risk.drivers.length > 0 && (
            <div className="glass-card rounded-xl p-4">
              <p className="text-earth-500 text-xs mb-3">Kluczowe czynniki ryzyka</p>
              <div className="flex flex-wrap gap-2">
                {engine.risk.drivers.slice(0, 5).map((d, i) => (
                  <span key={i} className="text-xs px-2.5 py-1 rounded-full bg-earth-800 text-earth-300 border border-earth-700/40">
                    {d.factor} <span className="text-earth-500">({(d.ST * 100).toFixed(0)}%)</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Action buttons */}
          {actionStatus === 'decided_go' ? (
            <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              <CheckCircle className="w-5 h-5" />
              <span className="font-medium">Decyzja GO — status przetargu zaktualizowany</span>
            </div>
          ) : actionStatus === 'decided_nogo' ? (
            <div className="flex items-center gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400">
              <XCircle className="w-5 h-5" />
              <span className="font-medium">Przetarg odrzucony — status zaktualizowany</span>
            </div>
          ) : (
            <div className="flex gap-4 mt-2">
              <button
                onClick={() => takeAction('decided_go')}
                disabled={actionStatus === 'loading'}
                className="flex-1 flex items-center justify-center gap-2 py-3.5 rounded-xl bg-emerald-500 text-white font-bold text-sm hover:bg-emerald-400 transition-colors disabled:opacity-50 shadow-lg shadow-emerald-500/20"
              >
                {actionStatus === 'loading'
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <ThumbsUp className="w-5 h-5" />}
                POTWIERDŹ GO
              </button>
              <button
                onClick={() => takeAction('decided_nogo')}
                disabled={actionStatus === 'loading'}
                className="flex-1 flex items-center justify-center gap-2 py-3.5 rounded-xl bg-earth-800 text-earth-300 font-bold text-sm hover:bg-earth-700 transition-colors disabled:opacity-50 border border-earth-700"
              >
                {actionStatus === 'loading'
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <ThumbsDown className="w-5 h-5" />}
                ODRZUĆ
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
