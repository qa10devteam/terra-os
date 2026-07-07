'use client';

import { useState, useEffect, useCallback } from 'react';
import { Search, RefreshCw, Download, Save, SlidersHorizontal, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useStore } from '@/store/useStore';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { SkeletonRow } from '@/components/ui/SkeletonLoader';
import { TenderDetail } from '@/components/TenderDetail';
import { showToast } from '@/components/Toast';

interface TenderItem {
  id: string;
  title: string;
  buyer: string | null;
  cpv: string[];
  voivodeship: string | null;
  value_pln: number | null;
  deadline_at: string | null;
  status: string;
  match_score: number | null;
  match_reason: string | null;
  source: string | null;
}

type SortKey = 'title' | 'buyer' | 'value_pln' | 'deadline_at' | 'match_score' | 'status';

const ALL_STATUSES = ['new', 'matched', 'watching', 'analyzing', 'estimated', 'decided_go', 'decided_nogo', 'archived'];
const STATUS_LABELS: Record<string, string> = {
  new: 'Nowy', matched: 'Dopasowany', watching: 'Obserwowany', analyzing: 'Analiza',
  estimated: 'Wyceniony', decided_go: 'GO', decided_nogo: 'NO-GO', archived: 'Archiwum',
};

function fmtPLN(v: number | null | undefined) {
  if (!v) return '—';
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + ' M';
  if (v >= 1_000) return (v / 1_000).toFixed(0) + ' tys.';
  return v.toFixed(0);
}
function fmtDate(s: string | null | undefined) {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit', year: '2-digit' });
}
function daysUntil(s: string | null) {
  if (!s) return null;
  return Math.ceil((new Date(s).getTime() - Date.now()) / 86400000);
}

function exportCSV(tenders: TenderItem[]) {
  const headers = ['ID', 'Tytuł', 'Zamawiający', 'CPV', 'Region', 'Wartość (PLN)', 'Deadline', 'Status', 'Score'];
  const rows = tenders.map(t => [
    t.id, t.title, t.buyer ?? '', t.cpv.join(';'), t.voivodeship ?? '',
    t.value_pln ?? '', t.deadline_at ?? '', t.status, Math.round((t.match_score ?? 0) * 100),
  ]);
  const csv = [headers, ...rows].map(r => r.map(v => '"' + String(v).replace(/"/g, '""') + '"').join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'przetargi.csv';
  a.click();
  URL.revokeObjectURL(url);
}

export function ZwiadPage() {
  const { accessToken, setSelectedTender, selectedTender } = useStore();
  const [tenders, setTenders] = useState<TenderItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('match_score');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
  const [minValue, setMinValue] = useState('');
  const [maxValue, setMaxValue] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkStatus, setBulkStatus] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [openTender, setOpenTender] = useState<TenderItem | null>(null);

  const fetchTenders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const headers: Record<string, string> = {};
      if (accessToken) headers['Authorization'] = 'Bearer ' + accessToken;
      const res = await fetch('/api/v1/tenders?limit=100', { headers });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const json = await res.json();
      setTenders(json.items ?? []);
      setTotal(json.total ?? 0);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => { fetchTenders(); }, [fetchTenders]);

  // Auto-open TenderDetail when navigated from Dashboard with selectedTender
  useEffect(() => {
    if (selectedTender && !openTender) {
      setOpenTender(selectedTender as unknown as TenderItem);
      setSelectedTender(null);
    }
  }, [selectedTender]);

  async function handleSync() {
    setSyncing(true);
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (accessToken) headers['Authorization'] = 'Bearer ' + accessToken;
      await fetch('/api/v1/ingest/run', { method: 'POST', headers });
      showToast('success', 'Synchronizacja uruchomiona!');
      setTimeout(fetchTenders, 2000);
    } catch {
      showToast('error', 'Błąd synchronizacji');
    } finally {
      setSyncing(false);
    }
  }

  async function handleBulkStatus() {
    if (!bulkStatus || selected.size === 0) return;
    const ids = [...selected];
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (accessToken) headers['Authorization'] = 'Bearer ' + accessToken;
    for (const id of ids) {
      await fetch('/api/v1/tenders/' + id, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ status: bulkStatus }),
      }).catch(() => {});
    }
    showToast('success', 'Status zaktualizowany dla ' + ids.length + ' przetargów');
    setSelected(new Set());
    fetchTenders();
  }

  function saveFilters() {
    const filters = { selectedStatuses, minValue, maxValue, sortKey, sortDir };
    localStorage.setItem('terra-zwiad-filters', JSON.stringify(filters));
    showToast('success', 'Filtry zapisane');
  }

  function loadFilters() {
    try {
      const saved = localStorage.getItem('terra-zwiad-filters');
      if (saved) {
        const f = JSON.parse(saved);
        setSelectedStatuses(f.selectedStatuses ?? []);
        setMinValue(f.minValue ?? '');
        setMaxValue(f.maxValue ?? '');
        setSortKey(f.sortKey ?? 'match_score');
        setSortDir(f.sortDir ?? 'desc');
        showToast('info', 'Filtry załadowane');
      }
    } catch {}
  }

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  }

  function toggleSelect(id: string) {
    setSelected(s => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  // Filter + sort
  const filtered = tenders
    .filter(t => {
      if (query && !t.title.toLowerCase().includes(query.toLowerCase()) &&
          !(t.buyer ?? '').toLowerCase().includes(query.toLowerCase())) return false;
      if (selectedStatuses.length > 0 && !selectedStatuses.includes(t.status)) return false;
      if (minValue && t.value_pln !== null && t.value_pln < Number(minValue)) return false;
      if (maxValue && t.value_pln !== null && t.value_pln > Number(maxValue)) return false;
      return true;
    })
    .sort((a, b) => {
      const av = a[sortKey] ?? (typeof a[sortKey] === 'number' ? 0 : '');
      const bv = b[sortKey] ?? (typeof b[sortKey] === 'number' ? 0 : '');
      const cmp = String(av).localeCompare(String(bv), 'pl', { numeric: true });
      return sortDir === 'asc' ? cmp : -cmp;
    });

  function SortBtn({ col, label, cls }: { col: SortKey; label: string; cls?: string }) {
    return (
      <th
        onClick={() => toggleSort(col)}
        className={"px-3 py-2.5 text-left text-xs font-semibold text-earth-500 uppercase tracking-wide cursor-pointer hover:text-earth-300 select-none " + (cls ?? '')}
      >
        {label}{sortKey === col ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''}
      </th>
    );
  }

  return (
    <>
      <div className="flex flex-col h-full overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-earth-800/60 shrink-0">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-lg font-semibold text-earth-100">Zwiad przetargowy</h2>
              <p className="text-earth-500 text-xs">{total} przetargów w bazie</p>
            </div>
            <div className="flex items-center gap-2">
              {selected.size > 0 && (
                <div className="flex items-center gap-2 bg-earth-800 rounded-xl px-3 py-1.5">
                  <span className="text-xs text-earth-400">{selected.size} zaznaczonych</span>
                  <select
                    value={bulkStatus}
                    onChange={e => setBulkStatus(e.target.value)}
                    className="bg-earth-700 text-xs text-earth-200 rounded-lg px-2 py-1 focus:outline-none"
                  >
                    <option value="">Zmień status...</option>
                    {ALL_STATUSES.map(s => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
                  </select>
                  <button onClick={handleBulkStatus} className="text-xs bg-accent-primary/20 text-accent-primary px-2 py-1 rounded-lg hover:bg-accent-primary/30">
                    <Check className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
              <button onClick={() => exportCSV(filtered)} className="flex items-center gap-1.5 px-3 py-1.5 bg-earth-800 text-earth-400 hover:text-earth-200 rounded-xl text-xs transition-colors">
                <Download className="w-3.5 h-3.5" /> CSV
              </button>
              <button onClick={loadFilters} className="flex items-center gap-1.5 px-3 py-1.5 bg-earth-800 text-earth-400 hover:text-earth-200 rounded-xl text-xs transition-colors">
                Załaduj filtry
              </button>
              <button onClick={saveFilters} className="flex items-center gap-1.5 px-3 py-1.5 bg-earth-800 text-earth-400 hover:text-earth-200 rounded-xl text-xs transition-colors">
                <Save className="w-3.5 h-3.5" /> Zapisz filtry
              </button>
              <button
                onClick={handleSync}
                disabled={syncing}
                className="flex items-center gap-1.5 px-4 py-2 bg-accent-primary text-earth-950 rounded-xl text-xs font-semibold hover:bg-emerald-400 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={"w-3.5 h-3.5 " + (syncing ? "animate-spin" : "")} />
                Synchronizuj
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-earth-600" />
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Szukaj przetargów..."
                className="w-full bg-earth-800/60 border border-earth-700/60 rounded-xl pl-9 pr-4 py-2 text-sm text-earth-100 placeholder-earth-600 focus:outline-none focus:border-accent-primary/60"
              />
            </div>
            <button
              onClick={() => setFiltersOpen(f => !f)}
              className={"flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs transition-colors " + (filtersOpen ? "bg-accent-primary/20 text-accent-primary" : "bg-earth-800 text-earth-400 hover:text-earth-200")}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" /> Filtry
            </button>
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar filters */}
          <AnimatePresence>
            {filtersOpen ? (
              <motion.div
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: 200, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                className="border-r border-earth-800/60 overflow-hidden shrink-0"
              >
                <div className="p-4 w-[200px] space-y-4">
                  <div>
                    <p className="text-xs font-semibold text-earth-500 uppercase tracking-wide mb-2">Status</p>
                    {ALL_STATUSES.map(s => (
                      <label key={s} className="flex items-center gap-2 mb-1.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedStatuses.includes(s)}
                          onChange={() => setSelectedStatuses(arr => arr.includes(s) ? arr.filter(x => x !== s) : [...arr, s])}
                          className="accent-emerald-500"
                        />
                        <span className="text-xs text-earth-300">{STATUS_LABELS[s]}</span>
                      </label>
                    ))}
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-earth-500 uppercase tracking-wide mb-2">Wartość (PLN)</p>
                    <input
                      value={minValue}
                      onChange={e => setMinValue(e.target.value)}
                      placeholder="Min"
                      type="number"
                      className="w-full bg-earth-800 rounded-lg px-2 py-1.5 text-xs text-earth-200 mb-1 focus:outline-none"
                    />
                    <input
                      value={maxValue}
                      onChange={e => setMaxValue(e.target.value)}
                      placeholder="Max"
                      type="number"
                      className="w-full bg-earth-800 rounded-lg px-2 py-1.5 text-xs text-earth-200 focus:outline-none"
                    />
                  </div>
                  <button
                    onClick={() => { setSelectedStatuses([]); setMinValue(''); setMaxValue(''); }}
                    className="text-xs text-earth-600 hover:text-earth-300 transition-colors"
                  >
                    Wyczyść filtry
                  </button>
                </div>
              </motion.div>
            ) : null}
          </AnimatePresence>

          {/* Table */}
          <div className="flex-1 overflow-auto">
            {error ? (
              <div className="m-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                Błąd: {error}
                <button onClick={fetchTenders} className="ml-3 underline">Spróbuj ponownie</button>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-earth-950/95 backdrop-blur-sm z-10">
                  <tr className="border-b border-earth-800/60">
                    <th className="pl-4 pr-2 py-2.5 w-8">
                      <input
                        type="checkbox"
                        checked={selected.size === filtered.length && filtered.length > 0}
                        onChange={e => setSelected(e.target.checked ? new Set(filtered.map(t => t.id)) : new Set())}
                        className="accent-emerald-500"
                      />
                    </th>
                    <th className="px-3 py-2.5 text-left text-xs font-semibold text-earth-500 uppercase tracking-wide">Status</th>
                    <SortBtn col="title" label="Tytuł" cls="min-w-[200px]" />
                    <SortBtn col="buyer" label="Zamawiający" cls="hidden md:table-cell" />
                    <th className="px-3 py-2.5 text-left text-xs font-semibold text-earth-500 uppercase tracking-wide hidden lg:table-cell">CPV</th>
                    <th className="px-3 py-2.5 text-left text-xs font-semibold text-earth-500 uppercase tracking-wide hidden lg:table-cell">Region</th>
                    <SortBtn col="value_pln" label="Wartość" />
                    <SortBtn col="deadline_at" label="Deadline" />
                    <SortBtn col="match_score" label="Score" />
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    Array.from({ length: 8 }).map((_, i) => (
                      <tr key={i}><td colSpan={9}><SkeletonRow cols={8} /></td></tr>
                    ))
                  ) : filtered.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="px-4 py-16 text-center">
                        <div className="max-w-sm mx-auto">
                          <p className="text-earth-500 text-sm mb-1">Brak przetargów</p>
                          {query || selectedStatuses.length > 0
                            ? <p className="text-earth-700 text-xs">Zmień filtry aby zobaczyć wyniki</p>
                            : <p className="text-earth-700 text-xs mb-4">Kliknij Synchronizuj aby pobrać dane z BZP</p>
                          }
                          {!query && selectedStatuses.length === 0 && (
                            <button
                              onClick={handleSync}
                              disabled={syncing}
                              className="px-5 py-2 bg-accent-primary text-earth-950 rounded-xl text-xs font-semibold hover:bg-emerald-400 transition-colors"
                            >
                              Synchronizuj teraz
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ) : filtered.map(t => {
                    const days = daysUntil(t.deadline_at);
                    const urgent = days !== null && days <= 3;
                    const score = t.match_score !== null ? Math.round(t.match_score * 100) : 0;
                    return (
                      <tr
                        key={t.id}
                        onClick={(e) => { if ((e.target as HTMLElement).tagName !== 'INPUT') { setOpenTender(t); setSelectedTender(t as any); } }}
                        className="border-b border-earth-800/30 hover:bg-earth-800/40 transition-colors cursor-pointer"
                      >
                        <td className="pl-4 pr-2 py-2.5" onClick={e => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={selected.has(t.id)}
                            onChange={() => toggleSelect(t.id)}
                            className="accent-emerald-500"
                          />
                        </td>
                        <td className="px-3 py-2.5"><StatusBadge status={t.status} /></td>
                        <td className="px-3 py-2.5 max-w-xs">
                          <p className="text-xs text-earth-200 line-clamp-2 font-medium">{t.title}</p>
                        </td>
                        <td className="px-3 py-2.5 hidden md:table-cell">
                          <p className="text-xs text-earth-500 truncate max-w-[120px]">{t.buyer ?? '—'}</p>
                        </td>
                        <td className="px-3 py-2.5 hidden lg:table-cell">
                          <p className="text-xs font-mono text-earth-600">{t.cpv[0] ?? '—'}</p>
                        </td>
                        <td className="px-3 py-2.5 hidden lg:table-cell">
                          <p className="text-xs text-earth-500">{t.voivodeship ?? '—'}</p>
                        </td>
                        <td className="px-3 py-2.5">
                          <p className="text-xs font-mono text-earth-300">{fmtPLN(t.value_pln)}</p>
                        </td>
                        <td className="px-3 py-2.5">
                          <p className={"text-xs font-mono " + (urgent ? "text-red-400" : "text-earth-400")}>{fmtDate(t.deadline_at)}</p>
                          {days !== null && days <= 7 && (
                            <p className={"text-[10px] " + (urgent ? "text-red-500" : "text-yellow-600")}>{days}d</p>
                          )}
                        </td>
                        <td className="px-3 py-2.5">
                          <span
                            className="text-xs font-bold px-2 py-0.5 rounded-full"
                            style={{
                              color: score >= 80 ? '#10b981' : score >= 60 ? '#F59E0B' : '#EF4444',
                              backgroundColor: (score >= 80 ? '#10b981' : score >= 60 ? '#F59E0B' : '#EF4444') + '20',
                            }}
                          >
                            {score}%
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      <TenderDetail tender={openTender} onClose={() => setOpenTender(null)} />
    </>
  );
}
