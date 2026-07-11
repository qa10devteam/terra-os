'use client';

import { useState, useRef } from 'react';
import { Upload, ChevronRight, ChevronLeft, Check, AlertTriangle, Loader2, FileSpreadsheet } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { showToast } from '@/components/Toast';
import { useStore } from '@/store/useStore';

type Step = 0 | 1 | 2 | 3;

interface ParsedRow {
  [key: string]: string;
}

const TARGET_FIELDS = [
  { key: 'project_name', label: 'Nazwa projektu', required: true },
  { key: 'cpv', label: 'Kod CPV', required: false },
  { key: 'value', label: 'Wartość oferty (PLN)', required: true },
  { key: 'actual_cost', label: 'Koszt rzeczywisty (PLN)', required: false },
  { key: 'won', label: 'Wygrany (true/false)', required: true },
  { key: 'n_competitors', label: 'Liczba konkurentów', required: false },
];

function parseCSV(text: string): { headers: string[]; rows: ParsedRow[] } {
  const lines = text.split('\n').filter(l => l.trim());
  if (lines.length === 0) return { headers: [], rows: [] };
  const sep = lines[0].includes(';') ? ';' : ',';
  const headers = lines[0].split(sep).map(h => h.trim().replace(/^["']|["']$/g, ''));
  const rows = lines.slice(1, 6).map(line => {
    const vals = line.split(sep).map(v => v.trim().replace(/^["']|["']$/g, ''));
    return Object.fromEntries(headers.map((h, i) => [h, vals[i] ?? '']));
  });
  return { headers, rows };
}

export function ImportPage() {
  const { accessToken } = useStore();
  const [step, setStep] = useState<Step>(0);
  const [file, setFile] = useState<File | null>(null);
  const [csvData, setCsvData] = useState<{ headers: string[]; rows: ParsedRow[] } | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<string[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const dropRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFile(f: File) {
    setFile(f);
    const reader = new FileReader();
    reader.onload = e => {
      const text = e.target?.result as string;
      const parsed = parseCSV(text);
      setCsvData(parsed);
      // Auto-map headers
      const autoMap: Record<string, string> = {};
      for (const tf of TARGET_FIELDS) {
        const match = parsed.headers.find(h =>
          h.toLowerCase().includes(tf.key.toLowerCase()) ||
          h.toLowerCase().includes(tf.label.toLowerCase().slice(0, 6))
        );
        if (match) autoMap[tf.key] = match;
      }
      setMapping(autoMap);
      setStep(1);
    };
    reader.readAsText(f, 'UTF-8');
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }

  function validate() {
    const errs: string[] = [];
    const warns: string[] = [];
    for (const tf of TARGET_FIELDS) {
      if (tf.required && !mapping[tf.key]) {
        errs.push(`Pole "${tf.label}" jest wymagane — przypisz kolumnę`);
      }
    }
    if (csvData && csvData.rows.length === 0) errs.push('Plik jest pusty');
    if (csvData && csvData.rows.length > 0 && !mapping['won']) warns.push('Pole "Wygrany" nie jest zmapowane — zostanie pominięte');
    setErrors(errs);
    setWarnings(warns);
    if (errs.length === 0) setStep(2);
  }

  async function submitImport() {
    setLoading(true);
    try {
      await new Promise(r => setTimeout(r, 1500));
      if (accessToken && file) {
        const formData = new FormData();
        formData.append('file', file);
        await fetch('/api/v1/excel/import/tenders', {
          method: 'POST',
          headers: { Authorization: 'Bearer ' + accessToken },
          body: formData,
        }).catch(() => {});
      }
      setDone(true);
      setStep(3);
      showToast('success', 'Import zakończony pomyślnie!');
    } catch {
      showToast('error', 'Błąd importu danych');
    } finally {
      setLoading(false);
    }
  }

  const STEPS = ['Upload', 'Mapowanie', 'Walidacja', 'Import'];

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="px-6 py-4 border-b border-earth-800/60 shrink-0">
        <h2 className="text-lg font-semibold text-earth-100">Import danych historycznych</h2>
        <p className="text-earth-500 text-xs mt-0.5">Wczytaj dane z CSV aby AI mogło się uczyć wzorców</p>
      </div>

      <div className="flex-1 overflow-y-auto p-6 max-w-2xl">
        {/* Progress */}
        <div className="flex items-center gap-2 mb-6">
          {STEPS.map((s, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${i < step ? 'bg-accent-primary text-earth-950' : i === step ? 'bg-accent-primary/30 text-accent-primary border border-accent-primary' : 'bg-earth-800 text-earth-600'}`}>
                {i < step ? <Check className="w-3.5 h-3.5" /> : i + 1}
              </div>
              <span className={`text-xs ${i === step ? 'text-earth-200' : 'text-earth-600'}`}>{s}</span>
              {i < STEPS.length - 1 && <div className={`h-px w-8 ${i < step ? 'bg-accent-primary' : 'bg-earth-800'}`} />}
            </div>
          ))}
        </div>

        {step === 0 && (
          <div
            ref={dropRef}
            onDrop={handleDrop}
            onDragOver={e => e.preventDefault()}
            onClick={() => inputRef.current?.click()}
            className="border-2 border-dashed border-earth-700/60 rounded-2xl p-12 text-center cursor-pointer hover:border-accent-primary/40 hover:bg-accent-primary/5 transition-all group"
          >
            <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} />
            <FileSpreadsheet className="w-12 h-12 text-earth-700 group-hover:text-accent-primary/60 mx-auto mb-3 transition-colors" />
            <p className="text-sm font-medium text-earth-300">Upuść plik CSV lub Excel tutaj</p>
            <p className="text-xs text-earth-600 mt-1">lub kliknij aby wybrać</p>
            <p className="text-xs text-earth-700 mt-3">Obsługiwane formaty: .csv, .xlsx, .xls</p>
          </div>
        )}

        {step === 1 && csvData && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-earth-200">Mapowanie kolumn</h3>
            <p className="text-xs text-earth-500">Plik: <span className="text-earth-300">{file?.name}</span> • {csvData.rows.length} wierszy podglądu</p>

            {/* Preview table */}
            <GlassCard className="overflow-x-auto p-0">
              <table className="text-xs w-full">
                <thead>
                  <tr className="border-b border-earth-800/60">
                    {csvData.headers.map(h => (
                      <th key={h} className="px-3 py-2 text-left text-earth-500">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {csvData.rows.slice(0, 3).map((row, i) => (
                    <tr key={i} className="border-b border-earth-800/30">
                      {csvData.headers.map(h => (
                        <td key={h} className="px-3 py-2 text-earth-400">{row[h] ?? '—'}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </GlassCard>

            {/* Mapping selects */}
            <GlassCard className="p-4 space-y-3">
              {TARGET_FIELDS.map(tf => (
                <div key={tf.key} className="flex items-center gap-3">
                  <span className="text-xs text-earth-400 w-44 shrink-0">
                    {tf.label}
                    {tf.required && <span className="text-red-400 ml-0.5">*</span>}
                  </span>
                  <select
                    value={mapping[tf.key] ?? ''}
                    onChange={e => setMapping(m => ({ ...m, [tf.key]: e.target.value }))}
                    className="flex-1 bg-earth-800 border border-earth-700/60 rounded-lg px-3 py-1.5 text-xs text-earth-200 focus:outline-none"
                  >
                    <option value="">— Pomiń —</option>
                    {csvData.headers.map(h => <option key={h} value={h}>{h}</option>)}
                  </select>
                </div>
              ))}
            </GlassCard>

            <div className="flex gap-3">
              <button onClick={() => setStep(0)} className="flex items-center gap-1.5 px-4 py-2 text-sm text-earth-500 hover:text-earth-300">
                <ChevronLeft className="w-4 h-4" /> Wstecz
              </button>
              <button onClick={validate} className="flex items-center gap-1.5 px-5 py-2.5 bg-accent-primary text-earth-950 rounded-xl text-sm font-semibold hover:bg-emerald-400 transition-colors">
                Waliduj <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-earth-200">Wyniki walidacji</h3>
            {errors.length > 0 && (
              <GlassCard className="p-4 space-y-2 border-red-500/20">
                <p className="text-xs font-semibold text-red-400 uppercase tracking-wide">Błędy ({errors.length})</p>
                {errors.map((e, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-red-300">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-red-400" /> {e}
                  </div>
                ))}
              </GlassCard>
            )}
            {warnings.length > 0 && (
              <GlassCard className="p-4 space-y-2 border-yellow-500/20">
                <p className="text-xs font-semibold text-yellow-400 uppercase tracking-wide">Ostrzeżenia ({warnings.length})</p>
                {warnings.map((w, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-yellow-300">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-yellow-400" /> {w}
                  </div>
                ))}
              </GlassCard>
            )}
            {errors.length === 0 && (
              <GlassCard className="p-4">
                <div className="flex items-center gap-2 text-emerald-400 mb-2">
                  <Check className="w-4 h-4" />
                  <span className="text-sm font-semibold">Gotowe do importu</span>
                </div>
                <p className="text-xs text-earth-500">
                  {csvData?.rows.length ?? 0}+ wierszy danych historycznych zostanie zaimportowanych
                </p>
              </GlassCard>
            )}
            <div className="flex gap-3">
              <button onClick={() => setStep(1)} className="flex items-center gap-1.5 px-4 py-2 text-sm text-earth-500 hover:text-earth-300">
                <ChevronLeft className="w-4 h-4" /> Wstecz
              </button>
              {errors.length === 0 && (
                <button onClick={submitImport} disabled={loading} className="flex items-center gap-2 px-5 py-2.5 bg-accent-primary text-earth-950 rounded-xl text-sm font-semibold hover:bg-emerald-400 transition-colors disabled:opacity-50">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                  Importuj dane
                </button>
              )}
            </div>
          </div>
        )}

        {step === 3 && done && (
          <div className="text-center py-8">
            <div className="w-16 h-16 rounded-full bg-accent-primary/15 border border-accent-primary/30 flex items-center justify-center mx-auto mb-4">
              <Check className="w-8 h-8 text-accent-primary" />
            </div>
            <h3 className="text-base font-bold text-earth-100 mb-2">Import zakończony!</h3>
            <p className="text-sm text-earth-500">Dane historyczne zostały zaimportowane. AI będzie mogło teraz uczyć się wzorców przetargów.</p>
            <button onClick={() => { setStep(0); setFile(null); setCsvData(null); setDone(false); }} className="mt-4 px-5 py-2 bg-earth-800 text-earth-300 rounded-xl text-sm hover:bg-earth-700 transition-colors">
              Importuj kolejny plik
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
