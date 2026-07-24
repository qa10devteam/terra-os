'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Search, Loader2, ChevronRight, Play, CheckCircle2, Circle,
  Clock, XCircle, Trophy, FileText, Calculator, GitBranch,
  Send, Workflow, AlertTriangle, RefreshCw, Plus, ArrowRight,
} from 'lucide-react';
import { GlassCard }   from '@/components/ui/GlassCard';
import { PageShell }   from '@/components/PageShell';
import { useAuthFetch } from '@/lib/api-v2';
import { showToast }   from '@/components/Toast';

// ─── Types ────────────────────────────────────────────────────────────────────

interface BudosStep {
  id: string;
  label: string;
  description: string;
  icon: string;
  color: string;
  transitions: string[];
  is_terminal: boolean;
}

interface WorkflowInstance {
  id: string;
  tender_id: string;
  current_step: string;
  current_step_label: string;
  current_step_icon: string;
  current_step_color: string;
  status: string;
  outcome: string | null;
  progress_pct: number;
  transitions: string[];
  started_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
  steps?: (BudosStep & { state: 'completed' | 'active' | 'pending' })[];
  log?: { id: string; from_step: string | null; to_step: string; note: string | null; created_at: string | null }[];
}

interface Tender {
  id: string;
  title: string | null;
  buyer: string | null;
  deadline_at: string | null;
  value_pln: number | null;
  go_score: number | null;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const STEP_ICONS: Record<string, React.ElementType> = {
  Search: Search, Calculator: Calculator, GitBranch: GitBranch,
  FileText: FileText, Send: Send, Trophy: Trophy, XCircle: XCircle,
};

const COLOR_CLS: Record<string, { bg: string; border: string; text: string; ring: string }> = {
  indigo: { bg: 'bg-indigo/10', border: 'border-indigo/30', text: 'text-indigo-300', ring: 'ring-indigo/40' },
  violet: { bg: 'bg-violet-500/10', border: 'border-violet-500/30', text: 'text-violet-300', ring: 'ring-violet-500/40' },
  warn:   { bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-300', ring: 'ring-amber-500/40' },
  em:     { bg: 'bg-em/10', border: 'border-em/30', text: 'text-em', ring: 'ring-em/40' },
  go:     { bg: 'bg-go/10', border: 'border-go/30', text: 'text-go', ring: 'ring-go/40' },
  nogo:   { bg: 'bg-nogo/10', border: 'border-nogo/30', text: 'text-nogo', ring: 'ring-nogo/40' },
  slate:  { bg: 'bg-ink-800/40', border: 'border-ink-700/30', text: 'text-slate-500', ring: 'ring-ink-700/40' },
};

function fmtDate(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('pl-PL', { day: '2-digit', month: 'short' });
}

function fmtPLN(v: number | null) {
  if (v == null) return '—';
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + ' mln';
  return v.toLocaleString('pl-PL') + ' zł';
}

function stepIcon(iconName: string, cls?: string) {
  const Icon = STEP_ICONS[iconName] ?? Circle;
  return <Icon className={cls ?? 'w-4 h-4'} />;
}

const OUTCOME_LABEL: Record<string, string> = {
  won: 'Wygrany', lost: 'Przegrany', cancelled: 'Anulowany', completed: 'Zakończony',
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function StepBadge({ step, size = 'sm' }: { step: BudosStep & { state: string }; size?: 'sm' | 'md' }) {
  const c = COLOR_CLS[step.color] ?? COLOR_CLS.slate;
  const dim = size === 'md' ? 'w-9 h-9' : 'w-7 h-7';
  const iconDim = size === 'md' ? 'w-4 h-4' : 'w-3.5 h-3.5';

  if (step.state === 'completed') {
    return (
      <div className={`${dim} rounded-full bg-go/15 border border-go/30 flex items-center justify-center shrink-0`}>
        <CheckCircle2 className={`${iconDim} text-go`} />
      </div>
    );
  }
  if (step.state === 'active') {
    return (
      <div className={`${dim} rounded-full ${c.bg} border ${c.border} flex items-center justify-center shrink-0 ring-2 ${c.ring} ring-offset-1 ring-offset-ink-900`}>
        {stepIcon(step.icon, `${iconDim} ${c.text}`)}
      </div>
    );
  }
  return (
    <div className={`${dim} rounded-full bg-ink-800/30 border border-ink-700/20 flex items-center justify-center shrink-0`}>
      {stepIcon(step.icon, `${iconDim} text-slate-700`)}
    </div>
  );
}

function ProgressRail({ instance }: { instance: WorkflowInstance }) {
  const steps = (instance.steps ?? []).filter(s => s.id !== 'rezygnacja');
  if (steps.length === 0) return null;

  return (
    <div className="flex items-center gap-0 w-full">
      {steps.map((step, i) => {
        const c = COLOR_CLS[step.color] ?? COLOR_CLS.slate;
        return (
          <div key={step.id} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center gap-1 shrink-0">
              <StepBadge step={step} />
              <span className={`text-[9px] font-medium leading-tight max-w-[48px] text-center ${
                step.state === 'active' ? c.text : step.state === 'completed' ? 'text-go/70' : 'text-slate-700'
              }`}>
                {step.label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className={`h-px flex-1 mx-1 transition-colors ${
                step.state === 'completed' ? 'bg-go/30' : 'bg-ink-700/30'
              }`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function WorkflowPage() {
  const authFetch = useAuthFetch();

  // BudOS definition
  const [budosSteps, setBudosSteps] = useState<BudosStep[]>([]);

  // Tenders list
  const [tenders, setTenders]           = useState<Tender[]>([]);
  const [tendersLoading, setTendersLoading] = useState(false);
  const [tenderSearch, setTenderSearch] = useState('');

  // Instances map tender_id → instance
  const [instances, setInstances] = useState<Record<string, WorkflowInstance>>({});
  const [instLoading, setInstLoading] = useState(false);

  // Selected tender for detail panel
  const [selected, setSelected]       = useState<Tender | null>(null);
  const [selInst, setSelInst]         = useState<WorkflowInstance | null>(null);
  const [selInstLoading, setSelInstLoading] = useState(false);

  // Transition panel
  const [transLoading, setTransLoading] = useState(false);
  const [transNote, setTransNote]       = useState('');

  // ── Load BudOS definition ───────────────────────────────────────────────────
  useEffect(() => {
    authFetch('/api/v2/workflows/budos')
      .then((d: { steps?: BudosStep[] }) => setBudosSteps(d.steps ?? []))
      .catch(() => {});
  }, []);

  // ── Load tenders ────────────────────────────────────────────────────────────
  const loadTenders = useCallback(async () => {
    setTendersLoading(true);
    try {
      const d = await authFetch('/api/v2/tenders?limit=50&sort=updated_at_desc') as {
        items?: Tender[]; results?: Tender[];
      };
      setTenders((d.items ?? d.results ?? []) as Tender[]);
    } catch {
      showToast('error', 'Błąd ładowania przetargów');
    } finally {
      setTendersLoading(false);
    }
  }, [authFetch]);

  // ── Load all instances (for status indicators) ──────────────────────────────
  const loadInstances = useCallback(async () => {
    setInstLoading(true);
    try {
      const d = await authFetch('/api/v2/workflow-instances') as { items?: WorkflowInstance[] };
      const map: Record<string, WorkflowInstance> = {};
      for (const it of (d.items ?? [])) {
        map[it.tender_id] = it;
      }
      setInstances(map);
    } catch {
      // silent
    } finally {
      setInstLoading(false);
    }
  }, [authFetch]);

  useEffect(() => {
    loadTenders();
    loadInstances();
  }, [loadTenders, loadInstances]);

  // ── Load detail for selected tender ────────────────────────────────────────
  const loadDetail = useCallback(async (tender: Tender) => {
    setSelInstLoading(true);
    setSelInst(null);
    try {
      const d = await authFetch(`/api/v2/workflow-instances?tender_id=${tender.id}`) as {
        items?: WorkflowInstance[];
      };
      const inst = (d.items ?? [])[0] ?? null;
      if (inst) {
        const detail = await authFetch(`/api/v2/workflow-instances/${inst.id}`) as WorkflowInstance;
        setSelInst(detail);
      } else {
        setSelInst(null);
      }
    } catch {
      setSelInst(null);
    } finally {
      setSelInstLoading(false);
    }
  }, [authFetch]);

  const selectTender = useCallback((t: Tender) => {
    setSelected(t);
    setTransNote('');
    loadDetail(t);
  }, [loadDetail]);

  // ── Start workflow ──────────────────────────────────────────────────────────
  const startWorkflow = useCallback(async () => {
    if (!selected) return;
    setTransLoading(true);
    try {
      const res = await authFetch('/api/v2/workflow-instances', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tender_id: String(selected.id) }),
      }) as WorkflowInstance & { created?: boolean };

      if (!res.created) {
        showToast('info', 'Przepływ już istnieje — wczytano istniejący');
      } else {
        showToast('success', 'Przepływ BudOS uruchomiony');
      }
      await loadDetail(selected);
      await loadInstances();
    } catch {
      showToast('error', 'Błąd startu przepływu');
    } finally {
      setTransLoading(false);
    }
  }, [selected, authFetch, loadDetail, loadInstances]);

  // ── Transition ──────────────────────────────────────────────────────────────
  const doTransition = useCallback(async (toStep: string) => {
    if (!selInst) return;
    setTransLoading(true);
    try {
      const res = await authFetch(`/api/v2/workflow-instances/${selInst.id}/transition`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ to_step: toStep, note: transNote || null }),
      }) as { current_step_label?: string };

      showToast('success', `→ ${res.current_step_label ?? toStep}`);
      setTransNote('');
      await loadDetail(selected!);
      await loadInstances();
    } catch (err: unknown) {
      const msg = (err as { message?: string })?.message ?? 'Błąd przejścia';
      showToast('error', msg);
    } finally {
      setTransLoading(false);
    }
  }, [selInst, transNote, selected, authFetch, loadDetail, loadInstances]);

  // ── Complete ────────────────────────────────────────────────────────────────
  const completeInstance = useCallback(async (outcome: string) => {
    if (!selInst) return;
    setTransLoading(true);
    try {
      await authFetch(`/api/v2/workflow-instances/${selInst.id}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ outcome, note: transNote || null }),
      });
      showToast('success', `Przepływ zamknięty: ${OUTCOME_LABEL[outcome] ?? outcome}`);
      setTransNote('');
      await loadDetail(selected!);
      await loadInstances();
    } catch {
      showToast('error', 'Błąd zamknięcia');
    } finally {
      setTransLoading(false);
    }
  }, [selInst, transNote, selected, authFetch, loadDetail, loadInstances]);

  // ── Filter ──────────────────────────────────────────────────────────────────
  const filtered = tenders.filter(t =>
    !tenderSearch || (t.title ?? '').toLowerCase().includes(tenderSearch.toLowerCase())
  );

  // ─── Render ─────────────────────────────────────────────────────────────────
  return (
    <PageShell title="Workflow BudOS">
      <div className="flex gap-3 h-full overflow-hidden">

        {/* ── LEFT: Tender list ─────────────────────────────────────────────── */}
        <div className="w-80 shrink-0 flex flex-col gap-3 overflow-hidden">
          {/* Search */}
          <GlassCard className="p-2.5 shrink-0">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-600" />
              <input
                value={tenderSearch}
                onChange={e => setTenderSearch(e.target.value)}
                placeholder="Szukaj przetargu…"
                className="w-full pl-8 pr-3 py-1.5 rounded-md bg-ink-800/60 border border-ink-700/50 text-slate-200 placeholder-ink-600 text-xs focus:outline-none focus:border-em/50 transition-colors"
              />
            </div>
          </GlassCard>

          {/* List */}
          <GlassCard className="flex-1 overflow-y-auto p-1.5 flex flex-col gap-1">
            {tendersLoading ? (
              <div className="flex-1 flex items-center justify-center">
                <Loader2 className="w-5 h-5 text-slate-600 animate-spin" />
              </div>
            ) : filtered.length === 0 ? (
              <p className="text-slate-600 text-xs text-center py-8">Brak przetargów</p>
            ) : (
              filtered.map(t => {
                const inst = instances[String(t.id)];
                const isActive = selected?.id === t.id;
                const c = inst ? (COLOR_CLS[inst.current_step_color ?? 'slate'] ?? COLOR_CLS.slate) : null;
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => selectTender(t)}
                    className={`w-full text-left rounded-lg px-3 py-2.5 transition-all border ${
                      isActive
                        ? 'bg-ink-700/60 border-ink-600/60'
                        : 'bg-transparent border-transparent hover:bg-ink-800/40 hover:border-ink-700/30'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-slate-200 text-xs font-medium leading-snug truncate">{t.title ?? '—'}</p>
                        <p className="text-slate-600 text-[10px] mt-0.5 truncate">{t.buyer ?? '—'}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-slate-600 text-[10px]">{fmtPLN(t.value_pln)}</span>
                          {t.deadline_at && (
                            <span className="text-slate-600 text-[10px] flex items-center gap-0.5">
                              <Clock className="w-2.5 h-2.5" />{fmtDate(t.deadline_at)}
                            </span>
                          )}
                        </div>
                      </div>
                      {inst ? (
                        <span className={`shrink-0 px-1.5 py-0.5 rounded text-[9px] font-semibold border ${c!.bg} ${c!.border} ${c!.text}`}>
                          {inst.current_step_label}
                        </span>
                      ) : (
                        <span className="shrink-0 px-1.5 py-0.5 rounded text-[9px] font-semibold border border-ink-700/30 text-slate-700 bg-ink-800/20">
                          brak
                        </span>
                      )}
                    </div>
                  </button>
                );
              })
            )}
          </GlassCard>
        </div>

        {/* ── RIGHT: Detail panel ───────────────────────────────────────────── */}
        <div className="flex-1 min-w-0 flex flex-col gap-3 overflow-hidden">
          {!selected ? (
            <GlassCard className="flex-1 flex flex-col items-center justify-center gap-3">
              <Workflow className="w-10 h-10 text-slate-700" />
              <p className="text-slate-600 text-sm">Wybierz przetarg z listy aby zarządzać przepływem BudOS</p>
            </GlassCard>
          ) : selInstLoading ? (
            <GlassCard className="flex-1 flex items-center justify-center">
              <Loader2 className="w-5 h-5 text-slate-600 animate-spin" />
            </GlassCard>
          ) : (
            <>
              {/* Header */}
              <GlassCard className="p-4 shrink-0">
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <h2 className="text-slate-100 font-semibold text-sm leading-snug truncate">
                      {selected.title ?? '—'}
                    </h2>
                    <p className="text-slate-500 text-xs mt-0.5 truncate">{selected.buyer ?? '—'}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {selInst ? (
                      <span className="text-slate-500 text-[10px] font-mono">#{selInst.id.slice(0, 8)}</span>
                    ) : (
                      <button
                        type="button"
                        onClick={startWorkflow}
                        disabled={transLoading}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-em/10 border border-em/30 text-em text-xs font-semibold hover:bg-em/20 transition-colors disabled:opacity-50"
                      >
                        {transLoading
                          ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          : <Play className="w-3.5 h-3.5" />}
                        Uruchom przepływ
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => loadDetail(selected)}
                      className="p-1.5 rounded-md text-slate-600 hover:text-slate-400 hover:bg-ink-800/40 transition-colors"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Progress bar */}
                {selInst && (
                  <div className="mt-3">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-slate-500 text-[10px]">Postęp</span>
                      <span className="text-slate-400 text-[10px] font-semibold">{selInst.progress_pct}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-ink-800/60 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-indigo/60 to-em/60 transition-all"
                        style={{ width: `${selInst.progress_pct}%` }}
                      />
                    </div>
                  </div>
                )}
              </GlassCard>

              {selInst ? (
                <>
                  {/* Step rail */}
                  <GlassCard className="p-4 shrink-0">
                    <div className="flex items-center justify-between mb-4">
                      <span className="section-label">Kroki przepływu</span>
                      {selInst.status !== 'active' && (
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                          selInst.outcome === 'won' ? 'bg-go/10 border-go/30 text-go'
                          : selInst.outcome === 'lost' ? 'bg-nogo/10 border-nogo/30 text-nogo'
                          : 'bg-ink-800/40 border-ink-700/30 text-slate-500'
                        }`}>
                          {OUTCOME_LABEL[selInst.outcome ?? ''] ?? selInst.status}
                        </span>
                      )}
                    </div>
                    <ProgressRail instance={selInst} />
                  </GlassCard>

                  {/* Transition panel — only when active */}
                  {selInst.status === 'active' && selInst.transitions.length > 0 && (
                    <GlassCard className="p-4 shrink-0">
                      <div className="flex items-center gap-2 mb-3">
                        <ArrowRight className="w-3.5 h-3.5 text-em" />
                        <span className="section-label">Przejście do następnego kroku</span>
                      </div>
                      <div className="flex flex-col gap-2">
                        <textarea
                          value={transNote}
                          onChange={e => setTransNote(e.target.value)}
                          placeholder="Notatka (opcjonalna)…"
                          rows={2}
                          className="w-full px-3 py-2 rounded-md bg-ink-800/60 border border-ink-700/50 text-slate-200 placeholder-ink-600 text-xs focus:outline-none focus:border-em/50 transition-colors resize-none"
                        />
                        <div className="flex flex-wrap gap-2">
                          {selInst.transitions.map(toStep => {
                            const stepDef = budosSteps.find(s => s.id === toStep);
                            const c = COLOR_CLS[stepDef?.color ?? 'slate'] ?? COLOR_CLS.slate;
                            return (
                              <button
                                key={toStep}
                                type="button"
                                onClick={() => doTransition(toStep)}
                                disabled={transLoading}
                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all disabled:opacity-50 ${c.bg} ${c.border} ${c.text} hover:brightness-110`}
                              >
                                {transLoading
                                  ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                  : <ChevronRight className="w-3.5 h-3.5" />}
                                {stepDef?.label ?? toStep}
                              </button>
                            );
                          })}
                          {/* Rezygnacja always available */}
                          {selInst.current_step !== 'wynik' && selInst.current_step !== 'rezygnacja' && (
                            <button
                              type="button"
                              onClick={() => doTransition('rezygnacja')}
                              disabled={transLoading}
                              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border border-nogo/30 text-nogo bg-nogo/10 hover:bg-nogo/20 transition-all disabled:opacity-50"
                            >
                              <XCircle className="w-3.5 h-3.5" />
                              Rezygnacja
                            </button>
                          )}
                        </div>
                        {/* Final outcomes for terminal steps */}
                        {selInst.transitions.length === 0 && selInst.current_step === 'wynik' && (
                          <div className="flex gap-2 mt-1">
                            {(['won', 'lost'] as const).map(outcome => (
                              <button
                                key={outcome}
                                type="button"
                                onClick={() => completeInstance(outcome)}
                                disabled={transLoading}
                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all disabled:opacity-50 ${
                                  outcome === 'won'
                                    ? 'bg-go/10 border-go/30 text-go hover:bg-go/20'
                                    : 'bg-nogo/10 border-nogo/30 text-nogo hover:bg-nogo/20'
                                }`}
                              >
                                {outcome === 'won' ? <Trophy className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                                {OUTCOME_LABEL[outcome]}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </GlassCard>
                  )}

                  {/* Step log */}
                  {(selInst.log ?? []).length > 0 && (
                    <GlassCard className="flex-1 overflow-y-auto p-4">
                      <span className="section-label block mb-3">Historia kroków</span>
                      <div className="flex flex-col gap-2">
                        {[...(selInst.log ?? [])].reverse().map(lg => (
                          <div key={lg.id} className="flex items-start gap-2.5 py-2 border-b border-ink-800/30 last:border-0">
                            <div className="w-5 h-5 rounded-full bg-ink-800/60 border border-ink-700/30 flex items-center justify-center shrink-0 mt-0.5">
                              <CheckCircle2 className="w-3 h-3 text-go/60" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-1.5 flex-wrap">
                                {lg.from_step && (
                                  <>
                                    <span className="text-slate-500 text-[10px]">{lg.from_step}</span>
                                    <ChevronRight className="w-2.5 h-2.5 text-slate-700" />
                                  </>
                                )}
                                <span className="text-slate-300 text-[10px] font-medium">{lg.to_step}</span>
                              </div>
                              {lg.note && <p className="text-slate-600 text-[10px] mt-0.5">{lg.note}</p>}
                            </div>
                            <span className="text-slate-700 text-[10px] shrink-0">{fmtDate(lg.created_at)}</span>
                          </div>
                        ))}
                      </div>
                    </GlassCard>
                  )}
                </>
              ) : (
                /* No instance yet */
                <GlassCard className="flex-1 flex flex-col items-center justify-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-em/10 border border-em/20 flex items-center justify-center">
                    <Workflow className="w-5 h-5 text-em/60" />
                  </div>
                  <div className="text-center">
                    <p className="text-slate-400 text-sm font-medium">Brak aktywnego przepływu</p>
                    <p className="text-slate-600 text-xs mt-1">Uruchom przepływ BudOS dla tego przetargu</p>
                  </div>
                  <button
                    type="button"
                    onClick={startWorkflow}
                    disabled={transLoading}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-em/10 border border-em/30 text-em text-sm font-semibold hover:bg-em/20 transition-colors disabled:opacity-50"
                  >
                    {transLoading
                      ? <Loader2 className="w-4 h-4 animate-spin" />
                      : <Plus className="w-4 h-4" />}
                    Uruchom przepływ
                  </button>
                </GlassCard>
              )}
            </>
          )}
        </div>

        {/* ── FAR RIGHT: BudOS steps legend ────────────────────────────────── */}
        <div className="w-52 shrink-0 flex flex-col gap-3 overflow-hidden">
          <GlassCard className="p-3 flex-1 overflow-y-auto">
            <p className="section-label mb-3">Przepływ BudOS</p>
            <div className="flex flex-col">
              {budosSteps.filter(s => s.id !== 'rezygnacja').map((s, i) => {
                const c = COLOR_CLS[s.color] ?? COLOR_CLS.slate;
                return (
                  <div key={s.id} className="flex items-start gap-2.5 pb-3 last:pb-0 relative">
                    {/* Connector line */}
                    {i < budosSteps.filter(x => x.id !== 'rezygnacja').length - 1 && (
                      <div className="absolute left-[13px] top-6 bottom-0 w-px bg-ink-700/30" />
                    )}
                    <div className={`w-7 h-7 rounded-full ${c.bg} border ${c.border} flex items-center justify-center shrink-0 z-10`}>
                      {stepIcon(s.icon, `w-3.5 h-3.5 ${c.text}`)}
                    </div>
                    <div className="flex-1 min-w-0 pt-0.5">
                      <p className={`text-xs font-semibold leading-tight ${c.text}`}>{s.label}</p>
                      <p className="text-slate-600 text-[10px] mt-0.5 leading-snug">{s.description}</p>
                    </div>
                  </div>
                );
              })}
              {/* Rezygnacja — shown separately */}
              {budosSteps.filter(s => s.id === 'rezygnacja').map(s => {
                const c = COLOR_CLS.nogo;
                return (
                  <div key={s.id} className="flex items-start gap-2.5 pt-3 border-t border-ink-800/40 mt-1">
                    <div className={`w-7 h-7 rounded-full ${c.bg} border ${c.border} flex items-center justify-center shrink-0`}>
                      {stepIcon(s.icon, `w-3.5 h-3.5 ${c.text}`)}
                    </div>
                    <div className="flex-1 min-w-0 pt-0.5">
                      <p className={`text-xs font-semibold leading-tight ${c.text}`}>{s.label}</p>
                      <p className="text-slate-600 text-[10px] mt-0.5 leading-snug">{s.description}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </GlassCard>
        </div>

      </div>
    </PageShell>
  );
}
