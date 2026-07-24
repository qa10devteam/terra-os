'use client';
import { useCallback, useEffect, useState } from 'react';
import { useAuthFetch } from '@/lib/api-v2';
import { useStore } from '@/store/useStore';
import { GlassCard } from '@/components/ui/GlassCard';
import { PageShell } from '@/components/PageShell';
import { motion, AnimatePresence } from 'motion/react';
import {
  Building2, Star, TrendingUp, Upload, Plus, Save, Trash2,
  ChevronRight, CheckCircle, AlertCircle, Loader2, Brain,
  FileSpreadsheet, Trophy, BarChart2, Users, Sparkles, FileText,
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface CompanyProfile {
  company_name: string;
  nip: string;
  regon: string;
  krs: string;
  adres: string;
  uprawnienia: string[];
  personel_kluczowy: { imie_nazwisko: string; rola: string; uprawnienia: string }[];
  certyfikaty: string[];
  cpv_preferred: string[];
  voivodeships: string[];
  scope_notes: string;
  ai_context_md: string;
  rate_card: { kp_pct?: string; kz_pct?: string; zysk_pct?: string; robocizna_zl_rg?: string };
}

interface CompanyRate {
  id: string;
  symbol: string;
  nazwa: string;
  jednostka: string;
  typ_rms: string;
  cena_netto: number;
  katalog: string;
  source: string;
}

interface CompanyRef {
  id: string;
  nazwa: string;
  inwestor: string;
  lokalizacja: string;
  rok_realizacji: number;
  wartosc_pln: number;
  cpv_codes: string[];
  zakres_md: string;
  certyfikaty: string[];
  ai_summary?: string;
}

interface BidRecord {
  id: string;
  cpv: string;
  region: string;
  our_price: number;
  winning_price: number;
  n_competitors: number;
  won: boolean;
  markup_pct: number;
  margin_pct: number;
  bid_date: string;
}

interface BidStats {
  total: number;
  wins: number;
  win_rate_pct: number;
  avg_markup_pct: number;
  avg_margin_pct: number | null;
  avg_price_ratio: number | null;
}

type Tab = 'profile' | 'rates' | 'references' | 'bids';

// ─── Small helpers ─────────────────────────────────────────────────────────────

const TAB_DEF: { id: Tab; label: string; icon: React.ElementType; desc: string }[] = [
  { id: 'profile',    label: 'Profil firmy',   icon: Building2,   desc: 'NIP, uprawnienia, personel, kontekst AI' },
  { id: 'rates',      label: 'Własne stawki',  icon: FileSpreadsheet, desc: 'R/M/S — import Excel lub ręcznie' },
  { id: 'references', label: 'Referencje',     icon: Star,        desc: 'Zrealizowane projekty' },
  { id: 'bids',       label: 'Historia ofert', icon: TrendingUp,  desc: 'Win-rate, marże, benchmarki' },
];

function PLN(v: number | null | undefined) {
  if (!v) return '—';
  return v.toLocaleString('pl-PL', { style: 'currency', currency: 'PLN', maximumFractionDigits: 0 });
}

function Tag({ label, onRemove }: { label: string; onRemove?: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700">
      {label}
      {onRemove && (
        <button onClick={onRemove} className="text-slate-500 hover:text-red-400 ml-0.5">×</button>
      )}
    </span>
  );
}

function TagInput({
  values, onChange, placeholder,
}: { values: string[]; onChange: (v: string[]) => void; placeholder?: string }) {
  const [draft, setDraft] = useState('');
  const add = () => {
    const t = draft.trim();
    if (t && !values.includes(t)) onChange([...values, t]);
    setDraft('');
  };
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {values.map(v => <Tag key={v} label={v} onRemove={() => onChange(values.filter(x => x !== v))} />)}
      </div>
      <div className="flex gap-2">
        <input
          className="input-dark flex-1 text-sm"
          placeholder={placeholder ?? 'Dodaj…'}
          value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), add())}
        />
        <button onClick={add} type="button" className="btn-outline px-3 py-1.5 text-sm">+</button>
      </div>
    </div>
  );
}

// ─── Tab: Profil firmy ─────────────────────────────────────────────────────────

function ProfileTab({ authFetch }: { authFetch: ReturnType<typeof useAuthFetch> }) {
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [aiCtx, setAiCtx] = useState<string | null>(null);
  const [loadingCtx, setLoadingCtx] = useState(false);

  useEffect(() => {
    authFetch('/api/v2/company/profile').then((d: CompanyProfile) => setProfile(d)).catch(() => {});
  }, [authFetch]);

  if (!profile) return <div className="h-32 flex items-center justify-center text-slate-500"><Loader2 className="animate-spin" size={20} /></div>;

  const set = (key: keyof CompanyProfile, val: unknown) => setProfile(p => p ? { ...p, [key]: val } : p);
  const setRC = (key: string, val: string) => setProfile(p => p ? { ...p, rate_card: { ...p.rate_card, [key]: val } } : p);

  const save = async () => {
    setSaving(true);
    await authFetch('/api/v2/company/profile', { method: 'PUT', body: JSON.stringify(profile) });
    setSaving(false); setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const loadAiCtx = async () => {
    setLoadingCtx(true);
    const r = await authFetch('/api/v2/company/profile/ai-context');
    setAiCtx(r.context);
    setLoadingCtx(false);
  };

  const rc = profile.rate_card || {};

  return (
    <div className="space-y-5">
      {/* Dane firmy */}
      <GlassCard className="p-5 space-y-4">
        <h3 className="text-slate-200 font-semibold flex items-center gap-2"><Building2 size={15} className="text-emerald-400" /> Dane firmy</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {([['company_name','Nazwa firmy'],['nip','NIP'],['regon','REGON'],['krs','KRS'],['adres','Adres']] as [keyof CompanyProfile, string][]).map(([k,lbl]) => (
            <label key={k} className="space-y-1">
              <span className="text-slate-500 text-xs">{lbl}</span>
              <input className="input-dark w-full text-sm" value={(profile[k] as string) || ''} onChange={e => set(k, e.target.value)} />
            </label>
          ))}
        </div>
      </GlassCard>

      {/* Narzuty / rate card */}
      <GlassCard className="p-5 space-y-4">
        <h3 className="text-slate-200 font-semibold flex items-center gap-2"><BarChart2 size={15} className="text-indigo-400" /> Narzuty i robocizna</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {([['kp_pct','KP %'],['kz_pct','KZ %'],['zysk_pct','Zysk %'],['robocizna_zl_rg','Robocizna (PLN/rg)']] as [string,string][]).map(([k,lbl]) => (
            <label key={k} className="space-y-1">
              <span className="text-slate-500 text-xs">{lbl}</span>
              <input className="input-dark w-full text-sm" type="number" step="0.1" value={(rc as Record<string,string>)[k] ?? ''} onChange={e => setRC(k, e.target.value)} />
            </label>
          ))}
        </div>
      </GlassCard>

      {/* Uprawnienia i certyfikaty */}
      <GlassCard className="p-5 space-y-4">
        <h3 className="text-slate-200 font-semibold flex items-center gap-2"><CheckCircle size={15} className="text-emerald-400" /> Uprawnienia i certyfikaty</h3>
        <label className="space-y-1 block">
          <span className="text-slate-500 text-xs">Uprawnienia budowlane</span>
          <TagInput values={profile.uprawnienia || []} onChange={v => set('uprawnienia', v)} placeholder="np. konstrukcyjne bez ograniczeń" />
        </label>
        <label className="space-y-1 block">
          <span className="text-slate-500 text-xs">Certyfikaty (ISO, BHP, etc.)</span>
          <TagInput values={profile.certyfikaty || []} onChange={v => set('certyfikaty', v)} placeholder="np. ISO 9001:2015" />
        </label>
        <label className="space-y-1 block">
          <span className="text-slate-500 text-xs">Preferowane kody CPV</span>
          <TagInput values={profile.cpv_preferred || []} onChange={v => set('cpv_preferred', v)} placeholder="np. 45231000-5" />
        </label>
      </GlassCard>

      {/* Personel kluczowy */}
      <GlassCard className="p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-slate-200 font-semibold flex items-center gap-2"><Users size={15} className="text-indigo-400" /> Personel kluczowy</h3>
          <button type="button" onClick={() => set('personel_kluczowy', [...(profile.personel_kluczowy||[]), {imie_nazwisko:'',rola:'',uprawnienia:''}])}
            className="btn-outline px-3 py-1 text-xs flex items-center gap-1"><Plus size={11} /> Dodaj</button>
        </div>
        {(profile.personel_kluczowy || []).map((p, i) => (
          <div key={i} className="grid grid-cols-3 gap-2 items-center">
            <input className="input-dark text-sm" placeholder="Imię i nazwisko" value={p.imie_nazwisko} onChange={e => {const arr=[...(profile.personel_kluczowy||[])];arr[i]={...arr[i],imie_nazwisko:e.target.value};set('personel_kluczowy',arr);}} />
            <input className="input-dark text-sm" placeholder="Rola" value={p.rola} onChange={e => {const arr=[...(profile.personel_kluczowy||[])];arr[i]={...arr[i],rola:e.target.value};set('personel_kluczowy',arr);}} />
            <div className="flex gap-1">
              <input className="input-dark text-sm flex-1" placeholder="Uprawnienia" value={p.uprawnienia} onChange={e => {const arr=[...(profile.personel_kluczowy||[])];arr[i]={...arr[i],uprawnienia:e.target.value};set('personel_kluczowy',arr);}} />
              <button onClick={() => set('personel_kluczowy',(profile.personel_kluczowy||[]).filter((_,j)=>j!==i))} className="text-slate-600 hover:text-red-400 p-1"><Trash2 size={13} /></button>
            </div>
          </div>
        ))}
      </GlassCard>

      {/* Kontekst AI ręczny */}
      <GlassCard className="p-5 space-y-3">
        <h3 className="text-slate-200 font-semibold flex items-center gap-2"><Brain size={15} className="text-purple-400" /> Ręczny kontekst AI</h3>
        <p className="text-slate-500 text-xs">Dodatkowe informacje, które AI będzie uwzględniać przy generowaniu ofert i kosztorysów. Markdown.</p>
        <textarea className="input-dark w-full text-sm font-mono h-28 resize-none" placeholder="np. Specjalizujemy się w renowacji obiektów zabytkowych. Posiadamy własny park maszynowy…" value={profile.ai_context_md || ''} onChange={e => set('ai_context_md', e.target.value)} />
      </GlassCard>

      {/* Podgląd kontekstu AI */}
      <div className="flex items-center gap-3">
        <button type="button" onClick={loadAiCtx} disabled={loadingCtx}
          className="btn-outline px-4 py-2 text-sm flex items-center gap-2 disabled:opacity-50">
          {loadingCtx ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} className="text-purple-400" />}
          Podgląd kontekstu AI
        </button>
      </div>

      <AnimatePresence>
        {aiCtx && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <GlassCard className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-400 text-xs font-mono">Kontekst wysyłany do AI ({aiCtx.length} znaków)</span>
                <button onClick={() => setAiCtx(null)} className="text-slate-600 hover:text-slate-400 text-xs">zamknij</button>
              </div>
              <pre className="text-slate-300 text-xs whitespace-pre-wrap font-mono bg-slate-900/60 rounded-lg p-3 max-h-64 overflow-y-auto">{aiCtx}</pre>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>

      <button onClick={save} disabled={saving}
        className="btn-primary px-6 py-2.5 flex items-center gap-2 disabled:opacity-50">
        {saving ? <Loader2 size={14} className="animate-spin" /> : saved ? <CheckCircle size={14} /> : <Save size={14} />}
        {saved ? 'Zapisano!' : 'Zapisz profil'}
      </button>
    </div>
  );
}

// ─── Tab: Własne stawki ────────────────────────────────────────────────────────

function RatesTab({ authFetch }: { authFetch: ReturnType<typeof useAuthFetch> }) {
  const accessToken = useStore(s => s.accessToken);
  const [rates, setRates] = useState<CompanyRate[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [importResult, setImportResult] = useState<{ imported: number; errors: string[] } | null>(null);
  const [newRate, setNewRate] = useState<Partial<CompanyRate>>({ typ_rms: 'R', jednostka: 'rg' });
  const [adding, setAdding] = useState(false);

  const reload = useCallback(() => {
    setLoading(true);
    authFetch('/api/v2/company/rates')
      .then((d: { items: CompanyRate[] }) => setRates(d.items))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [authFetch]);

  useEffect(() => { reload(); }, [reload]);

  const handleExcel = async (file: File) => {
    setUploading(true);
    setImportResult(null);
    const fd = new FormData();
    fd.append('file', file);
    const headers: Record<string, string> = {};
    if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`;
    const res = await fetch('/api/v2/company/rates/import-excel', { method: 'POST', body: fd, headers });
    const d = await res.json();
    setImportResult(d);
    setUploading(false);
    reload();
  };

  const addRate = async () => {
    if (!newRate.symbol || !newRate.nazwa || !newRate.cena_netto) return;
    setAdding(true);
    await authFetch('/api/v2/company/rates', { method: 'POST', body: JSON.stringify(newRate) });
    setNewRate({ typ_rms: 'R', jednostka: 'rg' });
    setAdding(false);
    reload();
  };

  const grouped = rates.reduce((acc: Record<string, CompanyRate[]>, r) => {
    const k = r.typ_rms || 'R';
    (acc[k] = acc[k] || []).push(r);
    return acc;
  }, {});

  const TYPE_LABEL: Record<string, string> = { R: 'Robocizna', M: 'Materiały', S: 'Sprzęt' };
  const TYPE_COLOR: Record<string, string> = { R: 'text-blue-400', M: 'text-emerald-400', S: 'text-amber-400' };

  return (
    <div className="space-y-5">
      {/* Import Excel */}
      <GlassCard className="p-5">
        <h3 className="text-slate-200 font-semibold mb-3 flex items-center gap-2"><FileSpreadsheet size={15} className="text-emerald-400" /> Import z Excela</h3>
        <p className="text-slate-500 text-xs mb-3">Format kolumn: <code className="text-emerald-400">symbol | nazwa | jednostka | typ_rms | cena_netto | katalog</code></p>
        <label className="cursor-pointer">
          <span className={`btn-outline px-4 py-2 text-sm inline-flex items-center gap-2 ${uploading ? 'opacity-50' : ''}`}>
            {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
            {uploading ? 'Importuję…' : 'Wgraj plik XLSX'}
          </span>
          <input type="file" accept=".xlsx,.xls" className="hidden" onChange={e => { if (e.target.files?.[0]) handleExcel(e.target.files[0]); }} />
        </label>
        <AnimatePresence>
          {importResult && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-3 p-3 rounded-lg bg-slate-900/60 text-sm">
              <span className="text-emerald-400 font-semibold">+{importResult.imported} pozycji</span>
              {importResult.errors.length > 0 && (
                <div className="mt-1 text-amber-400 text-xs">{importResult.errors.slice(0,3).join(' · ')}</div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </GlassCard>

      {/* Dodaj ręcznie */}
      <GlassCard className="p-5">
        <h3 className="text-slate-200 font-semibold mb-3 flex items-center gap-2"><Plus size={15} className="text-indigo-400" /> Dodaj pozycję ręcznie</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 items-end">
          {([['symbol','Symbol','text'],['nazwa','Nazwa','text'],['jednostka','Jedn.','text'],['cena_netto','Cena (PLN)','number']] as [keyof CompanyRate, string, string][]).map(([k, lbl, type]) => (
            <label key={k} className="space-y-1">
              <span className="text-slate-500 text-xs">{lbl}</span>
              <input type={type} className="input-dark w-full text-sm"
                value={(newRate[k] as string | number) ?? ''}
                onChange={e => setNewRate(p => ({ ...p, [k]: type === 'number' ? parseFloat(e.target.value) : e.target.value }))} />
            </label>
          ))}
          <label className="space-y-1">
            <span className="text-slate-500 text-xs">Typ R/M/S</span>
            <select className="input-dark w-full text-sm" value={newRate.typ_rms || 'R'} onChange={e => setNewRate(p => ({ ...p, typ_rms: e.target.value }))}>
              <option value="R">R — Robocizna</option>
              <option value="M">M — Materiał</option>
              <option value="S">S — Sprzęt</option>
            </select>
          </label>
          <button onClick={addRate} disabled={adding} className="btn-primary px-3 py-2 text-sm flex items-center justify-center gap-1 disabled:opacity-50">
            {adding ? <Loader2 size={13} className="animate-spin" /> : <Plus size={13} />} Dodaj
          </button>
        </div>
      </GlassCard>

      {/* Lista */}
      {loading ? (
        <div className="space-y-2">{[1,2,3].map(i => <div key={i} className="h-10 rounded-lg bg-slate-800/50 animate-pulse" />)}</div>
      ) : rates.length === 0 ? (
        <p className="text-slate-500 text-sm px-1">Brak stawek. Wgraj Excel lub dodaj ręcznie.</p>
      ) : (
        Object.entries(grouped).map(([typ, items]) => (
          <GlassCard key={typ} className="p-4">
            <h4 className={`font-semibold text-sm mb-3 ${TYPE_COLOR[typ] || 'text-slate-300'}`}>{TYPE_LABEL[typ] || typ} ({items.length})</h4>
            <div className="space-y-1">
              {items.map(r => (
                <div key={r.id} className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-800/50 transition-colors">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-slate-500 text-xs font-mono w-24 shrink-0 truncate">{r.symbol}</span>
                    <span className="text-slate-200 text-sm truncate">{r.nazwa}</span>
                    {r.katalog && <span className="text-slate-600 text-xs shrink-0">{r.katalog}</span>}
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-slate-300 text-sm font-medium tabular-nums">{r.cena_netto?.toFixed(2)} <span className="text-slate-500 text-xs">/{r.jednostka}</span></span>
                    {r.source === 'excel_import' && <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400">Excel</span>}
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        ))
      )}
    </div>
  );
}

// ─── Tab: Referencje ──────────────────────────────────────────────────────────

function ReferencesTab({ authFetch }: { authFetch: ReturnType<typeof useAuthFetch> }) {
  const accessToken = useStore(s => s.accessToken);
  const [refs, setRefs] = useState<CompanyRef[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState<Partial<CompanyRef>>({});
  const [saving, setSaving] = useState(false);

  const reload = useCallback(() => {
    setLoading(true);
    authFetch('/api/v2/company/references')
      .then((d: { items: CompanyRef[] }) => setRefs(d.items))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [authFetch]);

  useEffect(() => { reload(); }, [reload]);

  const save = async () => {
    if (!form.nazwa) return;
    setSaving(true);
    await authFetch('/api/v2/company/references', { method: 'POST', body: JSON.stringify(form) });
    setForm({});
    setShowAdd(false);
    setSaving(false);
    reload();
  };

  const del = async (id: string) => {
    await authFetch(`/api/v2/company/references/${id}`, { method: 'DELETE' });
    reload();
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <p className="text-slate-500 text-sm">Zrealizowane projekty — AI używa ich do wypełniania sekcji referencji w ofertach.</p>
        <button onClick={() => setShowAdd(v => !v)} className="btn-primary px-4 py-2 text-sm flex items-center gap-2">
          <Plus size={14} /> Dodaj referencję
        </button>
      </div>

      <AnimatePresence>
        {showAdd && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <GlassCard className="p-5 space-y-4">
              <h3 className="text-slate-200 font-semibold">Nowa referencja</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {([['nazwa','Nazwa projektu *'],['inwestor','Zamawiający'],['lokalizacja','Lokalizacja']] as [keyof CompanyRef, string][]).map(([k,lbl]) => (
                  <label key={k} className="space-y-1">
                    <span className="text-slate-500 text-xs">{lbl}</span>
                    <input className="input-dark w-full text-sm" value={(form[k] as string) ?? ''} onChange={e => setForm(p => ({ ...p, [k]: e.target.value }))} />
                  </label>
                ))}
                <label className="space-y-1">
                  <span className="text-slate-500 text-xs">Rok realizacji</span>
                  <input type="number" className="input-dark w-full text-sm" value={form.rok_realizacji ?? ''} onChange={e => setForm(p => ({ ...p, rok_realizacji: parseInt(e.target.value) }))} />
                </label>
                <label className="space-y-1">
                  <span className="text-slate-500 text-xs">Wartość kontraktu (PLN)</span>
                  <input type="number" className="input-dark w-full text-sm" value={form.wartosc_pln ?? ''} onChange={e => setForm(p => ({ ...p, wartosc_pln: parseFloat(e.target.value) }))} />
                </label>
              </div>
              <label className="space-y-1 block">
                <span className="text-slate-500 text-xs">Opis zakresu (markdown)</span>
                <textarea className="input-dark w-full text-sm h-20 resize-none" value={form.zakres_md ?? ''} onChange={e => setForm(p => ({ ...p, zakres_md: e.target.value }))} placeholder="Zakres robót, technologie, specyfika…" />
              </label>
              <label className="space-y-1 block">
                <span className="text-slate-500 text-xs">Kody CPV</span>
                <TagInput values={form.cpv_codes || []} onChange={v => setForm(p => ({ ...p, cpv_codes: v }))} placeholder="np. 45231000-5" />
              </label>
              <div className="flex gap-2">
                <button onClick={save} disabled={saving} className="btn-primary px-4 py-2 text-sm flex items-center gap-2 disabled:opacity-50">
                  {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />} Zapisz
                </button>
                <button onClick={() => setShowAdd(false)} className="btn-outline px-4 py-2 text-sm">Anuluj</button>
              </div>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>

      {loading ? (
        <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-20 rounded-xl bg-slate-800/50 animate-pulse" />)}</div>
      ) : refs.length === 0 ? (
        <GlassCard className="p-10 text-center">
          <Star size={28} className="text-slate-700 mx-auto mb-2" />
          <p className="text-slate-500 text-sm">Brak referencji. Dodaj projekty aby AI mogło się nimi posługiwać.</p>
        </GlassCard>
      ) : (
        <div className="space-y-3">
          {refs.map(ref => (
            <GlassCard key={ref.id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-slate-100 font-semibold">{ref.nazwa}</span>
                    {ref.rok_realizacji && <span className="text-slate-500 text-xs">{ref.rok_realizacji}</span>}
                    {ref.wartosc_pln && <span className="text-emerald-400 text-xs font-medium">{PLN(ref.wartosc_pln)}</span>}
                  </div>
                  {ref.inwestor && <p className="text-slate-400 text-sm mt-0.5">{ref.inwestor}{ref.lokalizacja ? ` · ${ref.lokalizacja}` : ''}</p>}
                  {ref.zakres_md && <p className="text-slate-500 text-xs mt-1.5 line-clamp-2">{ref.zakres_md}</p>}
                  {ref.cpv_codes?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">{ref.cpv_codes.map(c => <Tag key={c} label={c} />)}</div>
                  )}
                </div>
                <button onClick={() => del(ref.id)} className="text-slate-700 hover:text-red-400 p-1 shrink-0"><Trash2 size={14} /></button>
              </div>
            </GlassCard>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Tab: Historia ofert ───────────────────────────────────────────────────────

function BidsTab({ authFetch }: { authFetch: ReturnType<typeof useAuthFetch> }) {
  const [bids, setBids] = useState<BidRecord[]>([]);
  const [stats, setStats] = useState<BidStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState<Partial<BidRecord>>({ won: false });
  const [saving, setSaving] = useState(false);

  const reload = useCallback(() => {
    setLoading(true);
    Promise.all([
      authFetch('/api/v2/company/bids').then((d: { items: BidRecord[] }) => setBids(d.items)),
      authFetch('/api/v2/company/bids/stats').then((d: BidStats) => setStats(d)),
    ]).catch(() => {}).finally(() => setLoading(false));
  }, [authFetch]);

  useEffect(() => { reload(); }, [reload]);

  const save = async () => {
    if (!form.our_price) return;
    setSaving(true);
    await authFetch('/api/v2/company/bids', { method: 'POST', body: JSON.stringify(form) });
    setForm({ won: false });
    setShowAdd(false);
    setSaving(false);
    reload();
  };

  return (
    <div className="space-y-5">
      {/* Stats strip */}
      {stats && stats.total > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Złożone oferty', value: stats.total, accent: false },
            { label: 'Win-rate', value: `${stats.win_rate_pct.toFixed(1)}%`, accent: stats.win_rate_pct >= 30 },
            { label: 'Śr. narzut', value: `${stats.avg_markup_pct.toFixed(1)}%`, accent: false },
            { label: 'Śr. marża', value: stats.avg_margin_pct ? `${stats.avg_margin_pct.toFixed(1)}%` : '—', accent: false },
          ].map(m => (
            <GlassCard key={m.label} className="p-3 text-center">
              <div className="text-slate-500 text-xs mb-1">{m.label}</div>
              <div className={`font-bold text-lg ${m.accent ? 'text-emerald-400' : 'text-slate-100'}`}>{m.value}</div>
            </GlassCard>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between">
        <p className="text-slate-500 text-sm">Historia złożonych ofert — AI kalibruje marże i prognozy win-rate.</p>
        <button onClick={() => setShowAdd(v => !v)} className="btn-primary px-4 py-2 text-sm flex items-center gap-2">
          <Plus size={14} /> Dodaj wpis
        </button>
      </div>

      <AnimatePresence>
        {showAdd && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <GlassCard className="p-5 space-y-4">
              <h3 className="text-slate-200 font-semibold">Nowy wpis historyczny</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {([['our_price','Nasza cena (PLN)','number'],['winning_price','Cena wygrywająca','number'],['n_competitors','Liczba ofert','number'],['markup_pct','Narzut %','number'],['margin_pct','Marża faktyczna %','number'],['bid_date','Data oferty','date']] as [keyof BidRecord, string, string][]).map(([k,lbl,type]) => (
                  <label key={k} className="space-y-1">
                    <span className="text-slate-500 text-xs">{lbl}</span>
                    <input type={type} className="input-dark w-full text-sm"
                      value={(form[k] as string | number) ?? ''}
                      onChange={e => setForm(p => ({ ...p, [k]: type === 'number' ? parseFloat(e.target.value)||0 : e.target.value }))} />
                  </label>
                ))}
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={!!form.won} onChange={e => setForm(p => ({ ...p, won: e.target.checked }))} className="accent-emerald-500" />
                <span className="text-slate-300 text-sm">Wygraliśmy ten przetarg</span>
              </label>
              <div className="flex gap-2">
                <button onClick={save} disabled={saving} className="btn-primary px-4 py-2 text-sm flex items-center gap-2 disabled:opacity-50">
                  {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />} Zapisz
                </button>
                <button onClick={() => setShowAdd(false)} className="btn-outline px-4 py-2 text-sm">Anuluj</button>
              </div>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>

      {loading ? (
        <div className="space-y-2">{[1,2,3].map(i => <div key={i} className="h-12 rounded-lg bg-slate-800/50 animate-pulse" />)}</div>
      ) : bids.length === 0 ? (
        <GlassCard className="p-10 text-center">
          <Trophy size={28} className="text-slate-700 mx-auto mb-2" />
          <p className="text-slate-500 text-sm">Brak historii. Dodawaj wyniki ofert — AI będzie kalibrować narzuty i win-rate.</p>
        </GlassCard>
      ) : (
        <GlassCard className="p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800/60">
                {['Data','Nasza cena','Wygrywająca','N ofert','Narzut','Wynik'].map(h => (
                  <th key={h} className="text-left text-slate-500 text-xs font-medium px-4 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {bids.map(b => (
                <tr key={b.id} className="border-b border-slate-800/30 hover:bg-slate-800/30 transition-colors">
                  <td className="px-4 py-3 text-slate-400 text-xs tabular-nums">{b.bid_date ? new Date(b.bid_date).toLocaleDateString('pl-PL') : '—'}</td>
                  <td className="px-4 py-3 text-slate-200 font-medium tabular-nums">{PLN(b.our_price)}</td>
                  <td className="px-4 py-3 text-slate-400 tabular-nums">{PLN(b.winning_price)}</td>
                  <td className="px-4 py-3 text-slate-500 tabular-nums text-center">{b.n_competitors ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-400 tabular-nums">{b.markup_pct ? `${b.markup_pct.toFixed(1)}%` : '—'}</td>
                  <td className="px-4 py-3">
                    {b.won
                      ? <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/25">Wygrany</span>
                      : <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-500 border border-slate-700">Przegrany</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </GlassCard>
      )}
    </div>
  );
}

// ─── Main component ────────────────────────────────────────────────────────────

export function FirmKBPage() {
  const authFetch = useAuthFetch();
  const [tab, setTab] = useState<Tab>('profile');

  return (
    <PageShell title="Baza Wiedzy Firmy" subtitle="Profil, stawki, referencje i historia ofert — kontekst AI">
      {/* Tab bar */}
      <div className="flex gap-1 mb-6 overflow-x-auto pb-1">
        {TAB_DEF.map(t => {
          const Icon = t.icon;
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-all duration-150
                ${active
                  ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}
            >
              <Icon size={14} />
              {t.label}
              {active && <ChevronRight size={12} className="text-emerald-500" />}
            </button>
          );
        })}
      </div>

      {/* AI context chip */}
      <div className="mb-5 px-3 py-2 rounded-xl bg-purple-500/5 border border-purple-500/15 flex items-center gap-2.5 text-xs text-purple-300 max-w-xl">
        <Brain size={13} className="text-purple-400 shrink-0" />
        <span>Wszystkie dane z tej sekcji są automatycznie uwzględniane przez AI przy generowaniu kosztorysów i ofert przetargowych.</span>
      </div>

      {/* Tab content */}
      <AnimatePresence mode="wait">
        <motion.div key={tab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
          {tab === 'profile'    && <ProfileTab    authFetch={authFetch} />}
          {tab === 'rates'      && <RatesTab      authFetch={authFetch} />}
          {tab === 'references' && <ReferencesTab authFetch={authFetch} />}
          {tab === 'bids'       && <BidsTab       authFetch={authFetch} />}
        </motion.div>
      </AnimatePresence>
    </PageShell>
  );
}
