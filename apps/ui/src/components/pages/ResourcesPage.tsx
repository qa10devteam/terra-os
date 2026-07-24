'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Users, Truck, Calendar, Plus, Search, UserCheck, UserX, X } from 'lucide-react';
import { PageShell } from '@/components/PageShell';
import { useAuthFetch } from '@/lib/api-v2';
import { showToast } from '@/components/Toast';

interface Resource {
  id: string;
  type: 'person' | 'equipment';
  name: string;
  role?: string;
  status: 'available' | 'assigned' | 'on_leave' | 'unavailable';
  project?: string;
  rate_pln?: number;
}

// Fetched from API — no demo data

const STATUS_META: Record<string, { label: string; dot: string; bg: string }> = {
  available:   { label: 'Dostępny',    dot: 'bg-success',     bg: 'bg-success/10 text-success' },
  assigned:    { label: 'Zajęty',      dot: 'bg-warning',     bg: 'bg-warning/10 text-warning' },
  on_leave:    { label: 'Urlop',       dot: 'bg-info',        bg: 'bg-info/10 text-info' },
  unavailable: { label: 'Niedostępny', dot: 'bg-ink-600',   bg: 'bg-ink-700/30 text-slate-500' },
};

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
};
const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

export function ResourcesPage() {
  const [filter, setFilter] = useState<'all' | 'person' | 'equipment'>('all');
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [allResources, setAllResources] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ type: 'person', name: '', role: '', phone: '' });
  const authFetch = useAuthFetch();

  const fetchResources = useCallback(() => {
    Promise.all([
      authFetch('/api/v1/resources/employees').catch(() => ({ items: [] })),
      authFetch('/api/v1/resources/equipment').catch(() => ({ items: [] })),
    ]).then(([empData, eqData]: any[]) => {
      const emps: Resource[] = (empData.items ?? empData ?? []).map((e: any) => ({
        id: e.id, type: 'person' as const, name: e.name ?? '—',
        role: e.role ?? '', status: e.active ? 'available' : 'unavailable',
      }));
      const equip: Resource[] = (eqData.items ?? eqData ?? []).map((e: any) => ({
        id: e.id, type: 'equipment' as const, name: e.model ?? e.type ?? '—',
        role: e.type ?? '', status: e.active ? 'available' : 'unavailable',
      }));
      setAllResources([...emps, ...equip]);
    }).finally(() => setLoading(false));
  }, [authFetch]);

  useEffect(() => { fetchResources(); }, [fetchResources]);

  const handleCreate = useCallback(async () => {
    if (!form.name.trim()) { showToast('error', 'Nazwa jest wymagana'); return; }
    setSaving(true);
    try {
      if (form.type === 'person') {
        await authFetch('/api/v1/resources/employees', {
          method: 'POST',
          body: JSON.stringify({ name: form.name, role: form.role || 'pracownik', phone: form.phone || undefined }),
        });
      } else {
        await authFetch('/api/v1/resources/equipment', {
          method: 'POST',
          body: JSON.stringify({ name: form.name, category: form.role || 'maszyna' }),
        });
      }
      showToast('success', 'Zasób dodany');
      setShowModal(false);
      setForm({ type: 'person', name: '', role: '', phone: '' });
      fetchResources();
    } catch (e) {
      showToast('error', (e as Error).message || 'Błąd dodawania zasobu');
    } finally {
      setSaving(false);
    }
  }, [authFetch, form, fetchResources]);

  const resources = allResources.filter(r => {
    if (filter !== 'all' && r.type !== filter) return false;
    if (search && !r.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const counts = {
    total:     allResources.length,
    available: allResources.filter(r => r.status === 'available').length,
    assigned:  allResources.filter(r => r.status === 'assigned').length,
    onLeave:   allResources.filter(r => r.status === 'on_leave').length,
  };

  const selected = allResources.find(r => r.id === selectedId);

  const actions = (
    <button type="button" onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
      <Plus className="w-4 h-4" /> Dodaj zasób
    </button>
  );

  return (
    <PageShell title="Zasoby" subtitle="Zarządzanie zasobami budowlanymi" actions={actions}>
      <motion.div className="flex flex-col gap-6" variants={container} initial="hidden" animate="show">

        {/* Stat Cards */}
        <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Łącznie',   value: counts.total,     icon: Users,     color: 'text-slate-200' },
            { label: 'Dostępni',  value: counts.available, icon: UserCheck, color: 'text-success' },
            { label: 'Zajęci',    value: counts.assigned,  icon: UserX,     color: 'text-warning' },
            { label: 'Urlopy',    value: counts.onLeave,   icon: Calendar,  color: 'text-info' },
          ].map(s => (
            <div key={s.label} className="card rounded-xl p-4 shadow-md-sm">
              <div className="flex items-center gap-2 text-slate-500 text-xs mb-2">
                <s.icon className="w-3.5 h-3.5" />
                {s.label}
              </div>
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </motion.div>

        {/* Filters */}
        <motion.div variants={item} className="flex items-center gap-3">
          <div className="flex gap-1 p-1 rounded-xl bg-ink-900 border border-ink-800/60">
            {([['all', 'Wszystkie'], ['person', 'Pracownicy'], ['equipment', 'Sprzęt']] as const).map(([key, label]) => (
              <button type="button"
                key={key}
                onClick={() => setFilter(key)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-[color,background-color,border-color,opacity,transform,box-shadow] ${
                  filter === key ? 'bg-ink-800 text-slate-100' : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-600" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Szukaj zasobów..."
              className="input-base pl-9"
            />
          </div>
        </motion.div>

        {/* Content: List + Detail */}
        <motion.div variants={item} className="flex gap-4 min-h-[480px]">
          {/* Resource List */}
          <div className="w-[380px] shrink-0 card rounded-xl overflow-y-auto shadow-md-sm">
            <div className="divide-y divide-ink-800/30">
              {resources.map(r => {
                const meta = STATUS_META[r.status];
                return (
                  <button type="button"
                    key={r.id}
                    onClick={() => setSelectedId(r.id)}
                    className={`w-full text-left px-4 py-3 hover:bg-ink-800/30 transition-colors ${
                      selectedId === r.id ? 'bg-ink-800/40' : ''
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-ink-800 flex items-center justify-center border border-ink-700/40">
                        {r.type === 'person'
                          ? <Users className="w-4 h-4 text-slate-500" />
                          : <Truck className="w-4 h-4 text-slate-500" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-slate-200 font-medium truncate">{r.name}</p>
                        <p className="text-xs text-slate-500 truncate">{r.role}</p>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${meta.bg}`}>
                        {meta.label}
                      </span>
                    </div>
                    {r.project && (
                      <p className="text-xs text-slate-600 mt-1 ml-12 truncate">📍 {r.project}</p>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Detail / Calendar Panel */}
          <div className="flex-1 card rounded-xl p-6 shadow-md-sm">
            {selected ? (
              <div className="space-y-5">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-ink-800 flex items-center justify-center border border-ink-700/40">
                    {selected.type === 'person'
                      ? <Users className="w-7 h-7 text-slate-400" />
                      : <Truck className="w-7 h-7 text-slate-400" />}
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-slate-100">{selected.name}</h3>
                    <p className="text-sm text-slate-500">{selected.role}</p>
                  </div>
                  <span className={`ml-auto text-xs px-3 py-1 rounded-full font-medium ${STATUS_META[selected.status].bg}`}>
                    {STATUS_META[selected.status].label}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-xl bg-ink-900/60 border border-ink-800/40">
                    <p className="text-xs text-slate-500 mb-1">Stawka dzienna</p>
                    <p className="text-lg font-bold text-slate-200 font-mono">{selected.rate_pln?.toLocaleString()} PLN</p>
                  </div>
                  <div className="p-3 rounded-xl bg-ink-900/60 border border-ink-800/40">
                    <p className="text-xs text-slate-500 mb-1">Projekt</p>
                    <p className="text-sm text-slate-200">{selected.project || 'Brak przypisania'}</p>
                  </div>
                </div>

                {/* Calendar placeholder */}
                <div className="mt-4">
                  <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                    <Calendar className="w-4 h-4" /> Dostępność — Lipiec 2026
                  </h4>
                  <div className="grid grid-cols-4 sm:grid-cols-7 gap-1">
                    {['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'Sb', 'Nd'].map(d => (
                      <div key={d} className="text-center text-xs text-slate-600 py-1">{d}</div>
                    ))}
                    {Array.from({ length: 31 }, (_, i) => {
                      const busy  = selected.status === 'assigned' && i < 15;
                      const leave = selected.status === 'on_leave' && i >= 10 && i <= 20;
                      return (
                        <div
                          key={i}
                          className={`text-center text-xs py-2 rounded-md ${
                            leave ? 'bg-info/20 text-info' :
                            busy  ? 'bg-warning/15 text-warning' :
                            'bg-ink-900/40 text-slate-500 hover:bg-ink-800/60'
                          }`}
                        >
                          {i + 1}
                        </div>
                      );
                    })}
                  </div>
                  <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-warning/30" /> Zajęty</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-info/30" /> Urlop</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-ink-900/60" /> Dostępny</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
                <Calendar className="w-12 h-12 text-slate-600" />
                <div>
                  <p className="text-slate-300 font-medium">Wybierz zasób</p>
                  <p className="text-slate-500 text-sm mt-1">Kliknij na pracownika lub sprzęt, aby zobaczyć kalendarz dostępności</p>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>

      {/* Add Resource Modal */}
      <AnimatePresence>
        {showModal && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            onClick={(e) => { if (e.target === e.currentTarget) setShowModal(false); }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }}
              className="glass-card w-full max-w-md mx-4 p-6 flex flex-col gap-4"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-slate-100">Dodaj zasób</h3>
                <button type="button" onClick={() => setShowModal(false)} className="p-1 rounded-md hover:bg-ink-700/60 text-slate-500 hover:text-slate-300 transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="flex flex-col gap-3">
                {/* Type toggle */}
                <div className="flex rounded-lg overflow-hidden border border-ink-700/60">
                  {(['person', 'equipment'] as const).map(t => (
                    <button key={t} type="button"
                      onClick={() => setForm(f => ({ ...f, type: t }))}
                      className={`flex-1 py-2 text-xs font-medium transition-colors ${form.type === t ? 'bg-em/20 text-em' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                      {t === 'person' ? '👤 Pracownik' : '🚛 Sprzęt'}
                    </button>
                  ))}
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">{form.type === 'person' ? 'Imię i nazwisko' : 'Nazwa / model'} *</label>
                  <input type="text" value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    placeholder={form.type === 'person' ? 'Jan Kowalski' : 'Koparka CAT 320'}
                    className="w-full bg-ink-800/60 border border-ink-700/60 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-em/50"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">{form.type === 'person' ? 'Stanowisko' : 'Kategoria'}</label>
                  <input type="text" value={form.role}
                    onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                    placeholder={form.type === 'person' ? 'Kierownik budowy' : 'maszyna'}
                    className="w-full bg-ink-800/60 border border-ink-700/60 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-em/50"
                  />
                </div>
                {form.type === 'person' && (
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Telefon</label>
                    <input type="tel" value={form.phone}
                      onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                      placeholder="+48 600 000 000"
                      className="w-full bg-ink-800/60 border border-ink-700/60 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-em/50"
                    />
                  </div>
                )}
              </div>
              <div className="flex gap-2 pt-1">
                <button type="button" onClick={() => setShowModal(false)} className="btn-ghost flex-1 justify-center">Anuluj</button>
                <button type="button" onClick={handleCreate} disabled={saving} className="btn-primary flex-1 justify-center disabled:opacity-60">
                  {saving ? 'Dodaję...' : 'Dodaj zasób'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </PageShell>
  );
}
