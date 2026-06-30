'use client';

import { useState, useEffect } from 'react';
import { useStore } from '@/store/useStore';
import {
  Brain, AlertTriangle, CheckCircle, XCircle, Play, ArrowRight,
  BarChart2, Zap, ShieldAlert, Info,
} from 'lucide-react';

interface Violation {
  axiom_code: string;
  severity: string;
  message: string;
  provenance: Record<string, unknown>;
}

interface Driver {
  factor: string;
  S1: number;
  ST: number;
}

interface RiskData {
  margin_p10: number;
  margin_p50: number;
  margin_p90: number;
  drivers: Driver[];
  n_samples_used: number;
}

interface EngineResult {
  feasible: boolean;
  violations: Violation[];
  risk: RiskData | null;
  explanation_md: string;
}

const SEVERITY_ORDER = ['block', 'warn', 'info'];

const SEVERITY_META: Record<string, { label: string; classes: string; icon: React.ReactNode }> = {
  block: {
    label: 'BLOKADA',
    classes: 'text-red-400 bg-red-500/10 border-red-500/30',
    icon: <XCircle className="w-4 h-4 text-red-400 shrink-0" />,
  },
  warn: {
    label: 'OSTRZEŻENIE',
    classes: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
    icon: <AlertTriangle className="w-4 h-4 text-yellow-400 shrink-0" />,
  },
  info: {
    label: 'INFO',
    classes: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
    icon: <Info className="w-4 h-4 text-blue-400 shrink-0" />,
  },
};

function pct(v: number) { return (v * 100).toFixed(1) + '%'; }

export function SilnikPage() {
  const { selectedTender, setCurrentModule } = useStore();
  const tender = selectedTender as any;

  const [result, setResult] = useState<EngineResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchResult = (id: string) => {
    setLoading(true);
    setError(null);
    fetch(`/api/v1/tenders/${id}/engine`)
      .then(r => {
        if (r.status === 404) return null;
        if (!r.ok) throw new Error(`Błąd ${r.status}`);
        return r.json();
      })
      .then(data => { setResult(data); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  };

  useEffect(() => {
    if (tender?.id) fetchResult(tender.id);
  }, [tender?.id]);

  const runEngine = () => {
    if (!tender?.id) return;
    setRunning(true);
    setError(null);
    fetch(`/api/v1/tenders/${tender.id}/engine/run`, { method: 'POST' })
      .then(r => { if (!r.ok) throw new Error(`Błąd ${r.status}`); return r.json(); })
      .then(data => { setResult(data); setRunning(false); })
      .catch(e => { setError(e.message); setRunning(false); });
  };

  if (!tender) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
        <div className="w-20 h-20 rounded-2xl bg-earth-800 flex items-center justify-center border border-earth-700/40">
          <Brain className="w-10 h-10 text-earth-500" />
        </div>
        <div>
          <p className="text-earth-200 font-semibold text-xl">Nie wybrano przetargu</p>
          <p className="text-earth-500 text-sm mt-2 max-w-xs mx-auto leading-relaxed">
            Wejdź do Zwiadu i wybierz przetarg, aby uruchomić analizę
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

  // Group violations by severity
  const violationsBySeverity: Record<string, Violation[]> = {};
  if (result?.violations) {
    for (const v of result.violations) {
      if (!violationsBySeverity[v.severity]) violationsBySeverity[v.severity] = [];
      violationsBySeverity[v.severity].push(v);
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-earth-100">Silnik decyzyjny</h2>
          <p className="text-earth-500 text-sm mt-0.5 line-clamp-1">{tender.title}</p>
        </div>
        <button
          onClick={runEngine}
          disabled={running || loading}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-primary text-earth-950 font-semibold text-sm hover:bg-emerald-400 transition-colors disabled:opacity-50 shrink-0"
        >
          {running
            ? <><div className="w-4 h-4 border-2 border-earth-900 border-t-transparent rounded-full animate-spin" /> Analizuję…</>
            : <><Play className="w-4 h-4" /> {result ? 'Przelicz ponownie' : 'Uruchom analizę'}</>}
        </button>
      </div>

      {loading && (
        <div className="flex items-center gap-3 text-earth-500">
          <div className="w-4 h-4 border-2 border-earth-700 border-t-accent-primary rounded-full animate-spin" />
          Ładowanie wyników…
        </div>
      )}

      {error && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {!loading && result && (
        <>
          {/* Verdict Banner — GO / NO-GO */}
          <div className={`rounded-2xl p-6 flex items-center gap-5 border-2 ${
            result.feasible
              ? 'bg-emerald-500/10 border-emerald-500/40'
              : 'bg-red-500/10 border-red-500/40'
          }`}>
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center shrink-0 ${
              result.feasible ? 'bg-emerald-500/20' : 'bg-red-500/20'
            }`}>
              {result.feasible
                ? <CheckCircle className="w-9 h-9 text-emerald-400" />
                : <XCircle className="w-9 h-9 text-red-400" />}
            </div>
            <div className="flex-1">
              <p className="text-earth-500 text-xs font-medium uppercase tracking-wider mb-0.5">Werdykt silnika</p>
              <p className={`text-4xl font-black tracking-tight ${result.feasible ? 'text-emerald-400' : 'text-red-400'}`}>
                {result.feasible ? 'GO' : 'NO-GO'}
              </p>
              <p className="text-earth-400 text-sm mt-1">
                {result.feasible
                  ? 'Przetarg WYKONALNY — kwalifikuje się do wyceny'
                  : 'Przetarg NIEWYKONALNY — wykryto blokady'}
              </p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-earth-500 text-xs">Naruszenia</p>
              <p className={`text-3xl font-bold ${(result.violations?.length ?? 0) > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                {result.violations?.length ?? 0}
              </p>
            </div>
          </div>

          {/* Risk Gauges: P10/P50/P90 */}
          {result.risk && (
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: 'Marża P10', sublabel: 'pesymistyczna', val: result.risk.margin_p10, bg: 'bg-red-500/10 border-red-500/30', text: 'text-red-400', bar: 'bg-red-400' },
                { label: 'Marża P50', sublabel: 'mediana', val: result.risk.margin_p50, bg: 'bg-yellow-500/10 border-yellow-500/30', text: 'text-yellow-400', bar: 'bg-yellow-400' },
                { label: 'Marża P90', sublabel: 'optymistyczna', val: result.risk.margin_p90, bg: 'bg-emerald-500/10 border-emerald-500/30', text: 'text-emerald-400', bar: 'bg-emerald-400' },
              ].map(({ label, sublabel, val, bg, text, bar }) => (
                <div key={label} className={`glass-card rounded-xl p-5 border ${bg}`}>
                  <p className="text-earth-500 text-xs mb-0.5">{label}</p>
                  <p className="text-earth-600 text-xs mb-3">{sublabel}</p>
                  <p className={`text-3xl font-black ${text}`}>{pct(val)}</p>
                  <div className="mt-3 h-1.5 bg-earth-800 rounded-full overflow-hidden">
                    <div className={`h-full ${bar} rounded-full transition-all`} style={{ width: `${Math.min(Math.max(val * 100, 0), 100)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Violations grouped by severity */}
          {result.violations.length > 0 && (
            <div className="glass-card rounded-xl overflow-hidden">
              <div className="px-4 py-3 border-b border-earth-800/60 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-red-400" />
                <span className="text-sm font-medium text-earth-200">Naruszenia reguł</span>
                <span className="ml-auto text-xs text-earth-500">{result.violations.length} łącznie</span>
              </div>
              <div>
                {SEVERITY_ORDER.filter(sev => violationsBySeverity[sev]?.length).map(sev => {
                  const meta = SEVERITY_META[sev] || SEVERITY_META.info;
                  return (
                    <div key={sev}>
                      <div className={`px-4 py-2 flex items-center gap-2 text-xs font-semibold border-b border-earth-800/40 ${meta.classes}`}>
                        {meta.icon}
                        <span>{meta.label} ({violationsBySeverity[sev].length})</span>
                      </div>
                      <div className="divide-y divide-earth-800/30">
                        {violationsBySeverity[sev].map((v, i) => (
                          <div key={i} className="px-4 py-3 flex items-start gap-3 hover:bg-earth-800/15">
                            <div className="flex-1 min-w-0">
                              <p className="text-earth-200 text-sm">{v.message}</p>
                              <p className="text-earth-600 text-xs mt-0.5 font-mono">{v.axiom_code}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Drivers table with mini bar chart */}
          {result.risk && result.risk.drivers.length > 0 && (
            <div className="glass-card rounded-xl overflow-hidden">
              <div className="px-4 py-3 border-b border-earth-800/60 flex items-center gap-2">
                <Zap className="w-4 h-4 text-accent-primary" />
                <span className="text-sm font-medium text-earth-200">Czynniki ryzyka</span>
                <span className="text-earth-600 text-xs ml-auto">{result.risk.n_samples_used.toLocaleString()} próbek Monte Carlo</span>
              </div>
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-earth-800/40">
                    <th className="text-left px-4 py-2 text-earth-500 font-medium">Czynnik</th>
                    <th className="text-right px-3 py-2 text-earth-500 font-medium w-16">S1</th>
                    <th className="text-right px-3 py-2 text-earth-500 font-medium w-16">ST</th>
                    <th className="px-4 py-2 text-earth-500 font-medium w-40">Udział ST</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-earth-800/30">
                  {result.risk.drivers.slice(0, 10).map((d, i) => (
                    <tr key={i} className="hover:bg-earth-800/20">
                      <td className="px-4 py-2.5 text-earth-300">{d.factor}</td>
                      <td className="px-3 py-2.5 text-earth-500 text-right font-mono">{pct(d.S1)}</td>
                      <td className="px-3 py-2.5 text-earth-400 text-right font-mono font-semibold">{pct(d.ST)}</td>
                      <td className="px-4 py-2.5">
                        <div className="h-1.5 bg-earth-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-accent-primary rounded-full"
                            style={{ width: `${Math.min(d.ST * 100, 100)}%` }}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* No risk data */}
          {!result.risk && (
            <div className="glass-card rounded-xl p-6 flex items-center gap-4 text-earth-500 border border-earth-800/40">
              <BarChart2 className="w-8 h-8 shrink-0" />
              <div>
                <p className="text-earth-300 text-sm font-medium">Brak danych ryzyka</p>
                <p className="text-xs mt-0.5">Uruchom analizę ponownie aby wygenerować scenariusze Monte Carlo</p>
              </div>
            </div>
          )}
        </>
      )}

      {!loading && !result && !error && (
        <div className="flex flex-col items-center justify-center flex-1 gap-5 text-center py-16">
          <div className="w-16 h-16 rounded-2xl bg-earth-800 flex items-center justify-center border border-earth-700/40">
            <Brain className="w-8 h-8 text-earth-600" />
          </div>
          <div>
            <p className="text-earth-300 font-medium">Gotowy do analizy</p>
            <p className="text-earth-500 text-sm mt-1">
              Kliknij <strong className="text-earth-200">Uruchom analizę</strong> aby sprawdzić wykonalność
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
