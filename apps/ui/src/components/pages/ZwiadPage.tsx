'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useStore } from '@/store/useStore';
import {
  Search, Filter, ChevronUp, ChevronDown, X, Download,
  AlertTriangle, CheckCircle, ArrowRight, Calculator, Brain,
  MapPin, Calendar, Tag, Building2, Loader2, FileText, TrendingUp,
} from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────
interface TenderItem {
  id: string;
  title: string;
  buyer: string;
  cpv: string[];
  voivodeship: string;
  value_pln: string | number;
  deadline_at: string;
  published_at?: string;
  status: string;
  match_score: number | null;
  match_reason?: string;
  source?: string;
  external_id?: string;
  url?: string;
}

interface AnalysisResult {
  summary_md: string;
  red_flags: { severity: string; category: string; message: string; confidence: number }[];
  key_facts: Record<string, unknown>;
  przedmiar_items: { position_no: string; description: string; unit: string; quantity: number; knr_code?: string }[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const STATUS_LABELS: Record<string, string> = {
  new: 'Nowy', matched: 'Dopasowany', analyzing: 'Analiza',
  estimated: 'Wyceniony', decided_go: 'GO ✓', decided_nogo: 'NO-GO',
  archived: 'Archiwum',
};
const STATUS_COLORS: Record<string, string> = {
  new: 'bg-blue-500/15 text-blue-400',
  matched: 'bg-purple-500/15 text-purple-400',
  analyzing: 'bg-yellow-500/15 text-yellow-400',
  estimated: 'bg-emerald-500/15 text-emerald-400',
  decided_go: 'bg-emerald-600/20 text-emerald-300',
  decided_nogo: 'bg-red-500/15 text-red-400',
  archived: 'bg-earth-700/40 text-earth-500',
};
const SEVERITY_COLORS: Record<string, string> = {
  high: 'bg-red-500/10 text-red-400 border-red-500/20',
  medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  low: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  block: 'bg-red-500/10 text-red-400 border-red-500/20',
  warn: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
};

function fmtPLN(v: string | number | null | undefined) {
  if (v === null || v === undefined) return '—';
  const n = typeof v === 'string' ? parseFloat(v) : v;
  if (isNaN(n)) return '—';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + ' M PLN';
  if (n >= 1_000) return (n / 1_000).toFixed(0) + ' k PLN';
  return n.toFixed(0) + ' PLN';
}
function fmtDate(s?: string) {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

// ── Component ─────────────────────────────────────────────────────────────────
export function ZwiadPage() {
  const { setSelectedTender, setCurrentModule } = useStore();

  // List state
  const [tenders, setTenders] = useState<TenderItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [sortBy, setSortBy] = useState<'deadline_at' | 'value_pln' | 'match_score'>('match_score');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(0);
  const PER_PAGE = 12;

  // Detail panel state
  const [selected, setSelected] = useState<TenderItem | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Fetch list
  useEffect(() => {
    setLoadingList(true);
    setListError(null);
    const params = new URLSearchParams({ limit: '50' });
    if (statusFilter) params.set('status', statusFilter);
    fetch(`/api/v1/tenders?${params}`)
      .then(r => { if (!r.ok) throw new Error(`Błąd ${r.status}`); return r.json(); })
      .then(data => { setTenders(data.items ?? []); setTotal(data.total ?? 0); setLoadingList(false); })
      .catch(e => { setListError(e.message); setLoadingList(false); });
  }, [statusFilter]);

  // Auto-fetch existing analysis when panel opens
  useEffect(() => {
    if (!selected) return;
    setAnalysisResult(null);
    setAnalysisError(null);
    fetch(`/api/v1/tenders/${selected.id}/analysis`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setAnalysisResult(data); })
      .catch(() => {});
  }, [selected?.id]);

  const handleSort = (col: typeof sortBy) => {
    if (sortBy === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortBy(col); setSortDir('desc'); }
  };

  const filtered = tenders.filter(t =>
    !search || t.title.toLowerCase().includes(search.toLowerCase()) ||
    t.buyer.toLowerCase().includes(search.toLowerCase())
  );

  const sorted = [...filtered].sort((a, b) => {
    let va: number, vb: number;
    if (sortBy === 'match_score') { va = a.match_score ?? 0; vb = b.match_score ?? 0; }
    else if (sortBy === 'value_pln') { va = parseFloat(String(a.value_pln)) || 0; vb = parseFloat(String(b.value_pln)) || 0; }
    else { va = new Date(a.deadline_at).getTime(); vb = new Date(b.deadline_at).getTime(); }
    return sortDir === 'asc' ? va - vb : vb - va;
  });

  const paged = sorted.slice(page * PER_PAGE, (page + 1) * PER_PAGE);
  const totalPages = Math.ceil(sorted.length / PER_PAGE);

  const SortIcon = ({ col }: { col: typeof sortBy }) =>
    sortBy === col
      ? (sortDir === 'desc' ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />)
      : <ChevronDown className="w-3 h-3 opacity-30" />;

  const fetchAnalysis = () => {
    if (!selected) return;
    setAnalysisLoading(true);
    setAnalysisError(null);
    fetch(`/api/v1/tenders/${selected.id}/analyze`, { method: 'POST' })
      .then(r => { if (!r.ok) throw new Error(`Błąd ${r.status}`); return r.json(); })
      .then(() => fetch(`/api/v1/tenders/${selected.id}/analysis`))
      .then(r => r.json())
      .then(data => { setAnalysisResult(data); setAnalysisLoading(false); })
      .catch(e => { setAnalysisError(e.message); setAnalysisLoading(false); });
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* ── LEFT: tender list ─────────────────────────────────── */}
      <div className={`flex flex-col transition-all duration-300 ${selected ? 'w-[58%]' : 'w-full'} overflow-hidden border-r border-earth-800/60`}>
        {/* Toolbar */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-earth-800/60">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-earth-600" />
            <input
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(0); }}
              placeholder="Szukaj po nazwie lub zamawiającym…"
              className="w-full pl-9 pr-3 py-2 rounded-lg bg-earth-800 border border-earth-700 text-sm text-earth-100 placeholder:text-earth-600 focus:outline-none focus:border-accent-primary/50"
            />
          </div>
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-earth-600 pointer-events-none" />
            <select
              value={statusFilter}
              onChange={e => { setStatusFilter(e.target.value); setPage(0); }}
              className="pl-9 pr-8 py-2 rounded-lg bg-earth-800 border border-earth-700 text-sm text-earth-300 focus:outline-none focus:border-accent-primary/50 appearance-none"
            >
              <option value="">Wszystkie statusy</option>
              {Object.entries(STATUS_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <span className="text-earth-600 text-xs whitespace-nowrap">{filtered.length} z {total}</span>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto">
          {loadingList ? (
            <div className="flex items-center justify-center h-32 gap-2 text-earth-500">
              <Loader2 className="w-4 h-4 animate-spin" /> Ładowanie przetargów…
            </div>
          ) : listError ? (
            <div className="flex items-center gap-2 m-5 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              <AlertTriangle className="w-4 h-4 shrink-0" />{listError}
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-earth-950 z-10">
                <tr className="border-b border-earth-800/60">
                  <th className="text-left px-5 py-3 text-earth-500 font-medium">Przetarg</th>
                  <th
                    className="text-right px-3 py-3 text-earth-500 font-medium cursor-pointer hover:text-earth-300 whitespace-nowrap"
                    onClick={() => handleSort('value_pln')}
                  >
                    <span className="flex items-center justify-end gap-1">Wartość <SortIcon col="value_pln" /></span>
                  </th>
                  <th
                    className="text-right px-3 py-3 text-earth-500 font-medium cursor-pointer hover:text-earth-300 whitespace-nowrap"
                    onClick={() => handleSort('match_score')}
                  >
                    <span className="flex items-center justify-end gap-1">Dopas. <SortIcon col="match_score" /></span>
                  </th>
                  <th
                    className="text-right px-5 py-3 text-earth-500 font-medium cursor-pointer hover:text-earth-300 whitespace-nowrap"
                    onClick={() => handleSort('deadline_at')}
                  >
                    <span className="flex items-center justify-end gap-1">Termin <SortIcon col="deadline_at" /></span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-earth-800/40">
                {paged.map(t => (
                  <tr
                    key={t.id}
                    onClick={() => setSelected(t)}
                    className={`cursor-pointer transition-colors hover:bg-earth-800/30 ${selected?.id === t.id ? 'bg-earth-800/50 border-l-2 border-l-accent-primary' : ''}`}
                  >
                    <td className="px-5 py-3">
                      <p className="text-earth-200 font-medium line-clamp-1 text-sm">{t.title}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${STATUS_COLORS[t.status] ?? 'bg-earth-700 text-earth-400'}`}>
                          {STATUS_LABELS[t.status] ?? t.status}
                        </span>
                        <span className="text-earth-600 text-xs truncate">{t.buyer}</span>
                      </div>
                    </td>
                    <td className="px-3 py-3 text-right text-earth-300 whitespace-nowrap">{fmtPLN(t.value_pln)}</td>
                    <td className="px-3 py-3">
                      {t.match_score !== null ? (
                        <div className="flex items-center gap-1.5 justify-end">
                          <div className="w-16 h-1.5 bg-earth-800 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${(t.match_score * 100).toFixed(0)}%`,
                                backgroundColor: t.match_score > 0.7 ? '#10b981' : t.match_score > 0.4 ? '#f59e0b' : '#ef4444',
                              }}
                            />
                          </div>
                          <span className="text-earth-400 text-xs w-7 text-right">{(t.match_score * 100).toFixed(0)}%</span>
                        </div>
                      ) : <span className="text-earth-700 text-xs text-right block">—</span>}
                    </td>
                    <td className="px-5 py-3 text-right text-earth-500 text-xs whitespace-nowrap">{fmtDate(t.deadline_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-earth-800/60">
            <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
              className="text-xs text-earth-500 hover:text-earth-300 disabled:opacity-30">← Poprzednia</button>
            <span className="text-xs text-earth-600">{page + 1} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
              className="text-xs text-earth-500 hover:text-earth-300 disabled:opacity-30">Następna →</button>
          </div>
        )}
      </div>

      {/* ── RIGHT: detail panel ───────────────────────────────── */}
      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
            className="w-[42%] flex flex-col overflow-hidden bg-earth-950"
          >
            {/* Panel header */}
            <div className="flex items-start gap-3 px-5 py-4 border-b border-earth-800/60">
              <div className="flex-1 min-w-0">
                <p className="text-earth-100 font-semibold text-sm leading-snug line-clamp-2">{selected.title}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${STATUS_COLORS[selected.status] ?? ''}`}>
                    {STATUS_LABELS[selected.status] ?? selected.status}
                  </span>
                  {selected.source && <span className="text-earth-600 text-xs uppercase">{selected.source}</span>}
                </div>
              </div>
              <button onClick={() => setSelected(null)} className="p-1.5 hover:bg-earth-800 rounded-lg transition-colors mt-0.5">
                <X className="w-4 h-4 text-earth-500" />
              </button>
            </div>

            {/* Panel body */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              {/* Key facts */}
              <div className="grid grid-cols-2 gap-3">
                <div className="glass-card rounded-xl p-3">
                  <div className="flex items-center gap-1.5 text-earth-500 text-xs mb-1"><TrendingUp className="w-3 h-3" /> Wartość</div>
                  <p className="text-earth-100 font-semibold">{fmtPLN(selected.value_pln)}</p>
                </div>
                <div className="glass-card rounded-xl p-3">
                  <div className="flex items-center gap-1.5 text-earth-500 text-xs mb-1"><Calendar className="w-3 h-3" /> Termin</div>
                  <p className="text-earth-100 font-semibold">{fmtDate(selected.deadline_at)}</p>
                </div>
                <div className="glass-card rounded-xl p-3">
                  <div className="flex items-center gap-1.5 text-earth-500 text-xs mb-1"><MapPin className="w-3 h-3" /> Województwo</div>
                  <p className="text-earth-200 text-sm capitalize">{selected.voivodeship || '—'}</p>
                </div>
                <div className="glass-card rounded-xl p-3">
                  <div className="flex items-center gap-1.5 text-earth-500 text-xs mb-1"><Building2 className="w-3 h-3" /> Zamawiający</div>
                  <p className="text-earth-200 text-xs line-clamp-2">{selected.buyer}</p>
                </div>
              </div>

              {/* Match score */}
              {selected.match_score !== null && (
                <div className="glass-card rounded-xl p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-earth-500 text-xs">Dopasowanie profilu</span>
                    <span className="text-earth-200 font-semibold">{(selected.match_score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="h-2 bg-earth-800 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all"
                      style={{
                        width: `${(selected.match_score * 100).toFixed(0)}%`,
                        backgroundColor: selected.match_score > 0.7 ? '#10b981' : selected.match_score > 0.4 ? '#f59e0b' : '#ef4444',
                      }}
                    />
                  </div>
                  {selected.match_reason && <p className="text-earth-600 text-xs mt-1.5">{selected.match_reason}</p>}
                </div>
              )}

              {/* CPV codes */}
              {selected.cpv?.length > 0 && (
                <div className="glass-card rounded-xl p-3">
                  <div className="flex items-center gap-1.5 text-earth-500 text-xs mb-2"><Tag className="w-3 h-3" /> Kody CPV</div>
                  <div className="flex flex-wrap gap-1.5">
                    {selected.cpv.map((c, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-earth-800 text-earth-400 font-mono">{c}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Analyze button */}
              <button
                onClick={fetchAnalysis}
                disabled={analysisLoading}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-earth-800 border border-earth-700 text-earth-200 text-sm font-medium hover:bg-earth-700 transition-colors disabled:opacity-50"
              >
                {analysisLoading
                  ? <><Loader2 className="w-4 h-4 animate-spin" /> Analizuję dokumentację…</>
                  : <><Download className="w-4 h-4" /> {analysisResult ? 'Odśwież dokumentację' : 'Pobierz dokumentację'}</>}
              </button>

              {analysisError && (
                <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                  <AlertTriangle className="w-4 h-4 shrink-0" />{analysisError}
                </div>
              )}

              {/* Analysis results */}
              {analysisResult && (
                <div className="space-y-3">
                  {/* Summary */}
                  {analysisResult.summary_md && (
                    <div className="glass-card rounded-xl p-3">
                      <div className="flex items-center gap-1.5 text-earth-500 text-xs mb-2"><FileText className="w-3 h-3" /> Podsumowanie</div>
                      <p className="text-earth-300 text-xs leading-relaxed whitespace-pre-line">{analysisResult.summary_md.replace(/^#+\s/gm, '')}</p>
                    </div>
                  )}

                  {/* Red flags */}
                  {analysisResult.red_flags?.length > 0 && (
                    <div className="glass-card rounded-xl overflow-hidden">
                      <div className="flex items-center gap-1.5 px-3 py-2 border-b border-earth-800/60">
                        <AlertTriangle className="w-3 h-3 text-yellow-400" />
                        <span className="text-earth-400 text-xs font-medium">Red flags ({analysisResult.red_flags.length})</span>
                      </div>
                      <div className="divide-y divide-earth-800/40">
                        {analysisResult.red_flags.map((f, i) => (
                          <div key={i} className="px-3 py-2 flex items-start gap-2">
                            <span className={`text-xs px-1.5 py-0.5 rounded border font-medium shrink-0 ${SEVERITY_COLORS[f.severity] ?? SEVERITY_COLORS.low}`}>
                              {f.severity.toUpperCase()}
                            </span>
                            <p className="text-earth-300 text-xs leading-relaxed">{f.message}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Przedmiar */}
                  {analysisResult.przedmiar_items?.length > 0 && (
                    <div className="glass-card rounded-xl overflow-hidden">
                      <div className="flex items-center gap-1.5 px-3 py-2 border-b border-earth-800/60">
                        <CheckCircle className="w-3 h-3 text-emerald-400" />
                        <span className="text-earth-400 text-xs font-medium">Przedmiar ({analysisResult.przedmiar_items.length} poz.)</span>
                      </div>
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b border-earth-800/40">
                            <th className="px-3 py-1.5 text-left text-earth-600 font-normal">Poz.</th>
                            <th className="px-3 py-1.5 text-left text-earth-600 font-normal">Opis</th>
                            <th className="px-3 py-1.5 text-right text-earth-600 font-normal">Ilość</th>
                            <th className="px-3 py-1.5 text-right text-earth-600 font-normal pr-3">KNR</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-earth-800/30">
                          {analysisResult.przedmiar_items.map((item, i) => (
                            <tr key={i} className="hover:bg-earth-800/20">
                              <td className="px-3 py-1.5 text-earth-500 font-mono">{item.position_no}</td>
                              <td className="px-3 py-1.5 text-earth-300">{item.description}</td>
                              <td className="px-3 py-1.5 text-right text-earth-400">{item.quantity} {item.unit}</td>
                              <td className="px-3 py-1.5 text-right text-earth-600 font-mono text-xs pr-3">{item.knr_code ?? '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Action buttons */}
            <div className="flex gap-2 px-5 py-4 border-t border-earth-800/60">
              <button
                onClick={() => { setSelectedTender(selected as any); setCurrentModule('kosztorys'); }}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-accent-primary text-earth-950 font-semibold text-sm hover:bg-emerald-400 transition-colors"
              >
                <Calculator className="w-4 h-4" /> Kosztorys
              </button>
              <button
                onClick={() => { setSelectedTender(selected as any); setCurrentModule('silnik'); }}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-earth-800 text-earth-200 font-semibold text-sm hover:bg-earth-700 transition-colors border border-earth-700"
              >
                <Brain className="w-4 h-4" /> Silnik <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
