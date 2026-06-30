'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  CheckCircle2, XCircle, Loader2, AlertTriangle,
  Calendar, TrendingUp, Info, RefreshCw, ClipboardList,
} from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────────────
interface TenderItem {
  id: string;
  title: string;
  buyer: string;
  value_pln: string | number;
  deadline_at: string;
  status: string;
  match_score: number | null;
}

type Decision = 'decided_go' | 'decided_nogo';

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtPLN(v: string | number | null | undefined) {
  if (v === null || v === undefined) return '—';
  const n = typeof v === 'string' ? parseFloat(v) : v;
  if (isNaN(n)) return '—';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + ' M PLN';
  if (n >= 1_000) return (n / 1_000).toFixed(0) + ' k PLN';
  return n.toFixed(0) + ' PLN';
}
function fmtDate(s: string | null | undefined) {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

// ── Confirm dialog ────────────────────────────────────────────────────────────
function ConfirmDialog({
  tender, decision, onConfirm, onCancel, loading,
}: {
  tender: TenderItem;
  decision: Decision;
  onConfirm: () => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const isGo = decision === 'decided_go';
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-earth-950/80 backdrop-blur-sm p-4"
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="glass-card rounded-2xl p-6 max-w-md w-full shadow-2xl"
      >
        <div className="flex items-center gap-3 mb-4">
          {isGo
            ? <CheckCircle2 className="w-6 h-6 text-accent-primary shrink-0" />
            : <XCircle className="w-6 h-6 text-accent-danger shrink-0" />
          }
          <h3 className="text-earth-100 font-semibold">
            Potwierdzenie decyzji {isGo ? 'GO' : 'NO-GO'}
          </h3>
        </div>
        <p className="text-earth-400 text-sm mb-1">Przetarg:</p>
        <p className="text-earth-200 text-sm font-medium line-clamp-2 mb-4">{tender.title}</p>
        <div className="flex items-center gap-3 p-3 rounded-xl bg-earth-800/40 mb-5">
          <TrendingUp className="w-4 h-4 text-earth-500 shrink-0" />
          <span className="text-earth-400 text-sm">{fmtPLN(tender.value_pln)}</span>
          <span className="w-px h-4 bg-earth-700" />
          <Calendar className="w-4 h-4 text-earth-500 shrink-0" />
          <span className="text-earth-400 text-sm">{fmtDate(tender.deadline_at)}</span>
        </div>
        <p className="text-earth-500 text-xs mb-5">
          {isGo
            ? 'Przetarg zostanie przeniesiony do etapu GO. Oferta zostanie złożona.'
            : 'Przetarg zostanie odrzucony. Decyzja NO-GO jest ostateczna.'}
        </p>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="flex-1 py-2.5 rounded-xl bg-earth-800 text-earth-300 text-sm font-medium hover:bg-earth-700 transition-colors disabled:opacity-50"
          >
            Anuluj
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={`flex-1 py-2.5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-50 ${
              isGo
                ? 'bg-accent-primary text-earth-950 hover:bg-emerald-400'
                : 'bg-accent-danger/15 text-accent-danger border border-accent-danger/30 hover:bg-accent-danger/25'
            }`}
          >
            {loading
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : isGo
                ? <><CheckCircle2 className="w-4 h-4" /> Potwierdź GO</>
                : <><XCircle className="w-4 h-4" /> Odrzuć NO-GO</>
            }
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ── Skeleton row ──────────────────────────────────────────────────────────────
function SkeletonRow() {
  return (
    <div className="glass-card rounded-2xl p-4 animate-pulse">
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <div className="h-4 bg-earth-800 rounded w-3/4 mb-2" />
          <div className="h-3 bg-earth-800 rounded w-1/2 mb-3" />
          <div className="flex gap-4">
            <div className="h-3 bg-earth-800 rounded w-24" />
            <div className="h-3 bg-earth-800 rounded w-20" />
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          <div className="h-9 w-24 bg-earth-800 rounded-xl" />
          <div className="h-9 w-20 bg-earth-800 rounded-xl" />
        </div>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export function RfqPage() {
  const [tenders, setTenders] = useState<TenderItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<{ tender: TenderItem; decision: Decision } | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [justDecided, setJustDecided] = useState<Record<string, Decision>>({});

  const fetchTenders = () => {
    setLoading(true);
    setError(null);
    fetch('/api/v1/tenders?status=analyzing&limit=20')
      .then(r => { if (!r.ok) throw new Error(`Błąd ${r.status}`); return r.json(); })
      .then(data => { setTenders(data.items ?? []); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  };

  useEffect(() => { fetchTenders(); }, []);

  const handleConfirm = async () => {
    if (!confirm) return;
    setConfirming(true);
    try {
      await fetch(`/api/v1/tenders/${confirm.tender.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: confirm.decision }),
      });
      setJustDecided(prev => ({ ...prev, [confirm.tender.id]: confirm.decision }));
      setTimeout(() => {
        setTenders(prev => prev.filter(t => t.id !== confirm.tender.id));
        setJustDecided(prev => { const n = { ...prev }; delete n[confirm.tender.id]; return n; });
      }, 800);
    } catch (e: unknown) {
      console.error(e);
    } finally {
      setConfirming(false);
      setConfirm(null);
    }
  };

  return (
    <>
      {/* Confirm modal */}
      <AnimatePresence>
        {confirm && (
          <ConfirmDialog
            tender={confirm.tender}
            decision={confirm.decision}
            onConfirm={handleConfirm}
            onCancel={() => setConfirm(null)}
            loading={confirming}
          />
        )}
      </AnimatePresence>

      <div className="flex flex-col gap-5 p-6 h-full overflow-y-auto max-w-5xl mx-auto w-full">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-earth-100">Zapytania ofertowe (RFQ)</h2>
            <p className="text-earth-500 text-sm mt-0.5">Przetargi oczekujące na decyzję GO / NO-GO</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="px-3 py-1.5 rounded-full bg-accent-warning/15 text-accent-warning text-sm font-semibold">
              {tenders.length} w analizie
            </span>
            <button
              onClick={fetchTenders}
              disabled={loading}
              className="p-2 rounded-xl bg-earth-800/60 border border-earth-700/40 text-earth-500 hover:text-earth-300 hover:bg-earth-800 transition-colors disabled:opacity-40"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Info bar */}
        <div className="flex items-center gap-2 px-4 py-2.5 bg-accent-info/8 border border-accent-info/20 rounded-xl text-accent-info text-xs">
          <Info className="w-3.5 h-3.5 shrink-0" />
          Przetargi z etapu <span className="font-semibold mx-1">Analiza</span> oczekują na decyzję. Wybierz GO aby złożyć ofertę lub NO-GO aby zrezygnować.
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 p-4 rounded-xl bg-accent-danger/10 border border-accent-danger/20 text-accent-danger text-sm">
            <AlertTriangle className="w-4 h-4 shrink-0" />{error}
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} />)}
          </div>
        ) : tenders.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card rounded-2xl p-14 text-center"
          >
            <ClipboardList className="w-12 h-12 text-earth-700 mx-auto mb-4" />
            <p className="text-earth-300 font-semibold mb-1">Brak przetargów oczekujących na decyzję</p>
            <p className="text-earth-600 text-sm">Wszystkie zapytania zostały już rozpatrzone</p>
          </motion.div>
        ) : (
          <div className="space-y-3">
            <AnimatePresence mode="popLayout">
              {tenders.map((t) => {
                const decided = justDecided[t.id];
                const isGo = decided === 'decided_go';
                const isNogo = decided === 'decided_nogo';
                const score = t.match_score !== null ? Math.round(t.match_score * 100) : null;
                const scoreColor = score === null ? '#71717a'
                  : score >= 70 ? '#10b981'
                  : score >= 40 ? '#F59E0B'
                  : '#EF4444';

                return (
                  <motion.div
                    key={t.id}
                    layout
                    initial={{ opacity: 0, y: 8 }}
                    animate={{
                      opacity: decided ? 0.4 : 1,
                      scale: decided ? 0.98 : 1,
                      y: 0,
                    }}
                    exit={{ opacity: 0, x: isGo ? 60 : -60, scale: 0.95 }}
                    transition={{ duration: 0.3 }}
                    className={`glass-card rounded-2xl p-4 ${decided ? 'pointer-events-none' : ''}`}
                  >
                    <div className="flex items-start gap-4">
                      <div className="flex-1 min-w-0">
                        <p className="text-earth-100 font-medium text-sm line-clamp-2 mb-1">{t.title}</p>
                        <p className="text-earth-500 text-xs mb-3 truncate">{t.buyer}</p>
                        <div className="flex items-center gap-4 flex-wrap">
                          <span className="flex items-center gap-1 text-xs text-earth-400">
                            <TrendingUp className="w-3 h-3" />
                            <span className="font-medium">{fmtPLN(t.value_pln)}</span>
                          </span>
                          <span className="flex items-center gap-1 text-xs text-earth-500">
                            <Calendar className="w-3 h-3" />
                            {fmtDate(t.deadline_at)}
                          </span>
                          {score !== null && (
                            <span
                              className="text-xs font-semibold px-2 py-0.5 rounded"
                              style={{ color: scoreColor, backgroundColor: scoreColor + '20' }}
                            >
                              Dopasowanie {score}%
                            </span>
                          )}
                        </div>
                      </div>

                      {decided ? (
                        <div className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold ${
                          isGo ? 'bg-accent-primary/15 text-accent-primary' : 'bg-accent-danger/15 text-accent-danger'
                        }`}>
                          {isGo ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                          {isGo ? 'GO' : 'NO-GO'}
                        </div>
                      ) : (
                        <div className="flex gap-2 shrink-0">
                          <button
                            onClick={() => setConfirm({ tender: t, decision: 'decided_go' })}
                            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-accent-primary/15 text-accent-primary text-sm font-semibold hover:bg-accent-primary/25 transition-colors border border-accent-primary/20"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            GO
                          </button>
                          <button
                            onClick={() => setConfirm({ tender: t, decision: 'decided_nogo' })}
                            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-accent-danger/10 text-accent-danger text-sm font-semibold hover:bg-accent-danger/20 transition-colors border border-accent-danger/20"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            NO-GO
                          </button>
                        </div>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>
    </>
  );
}
