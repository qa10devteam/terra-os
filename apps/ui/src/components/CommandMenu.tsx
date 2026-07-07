'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Search, LayoutDashboard, Radar, GitBranch, Calculator, Settings, Upload, X } from 'lucide-react';
import { useStore } from '@/store/useStore';
import type { ModuleName } from '@/store/useStore';

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: React.ReactNode;
  action: () => void;
}

interface CommandMenuProps {
  open: boolean;
  onClose: () => void;
}

export function CommandMenu({ open, onClose }: CommandMenuProps) {
  const { setCurrentModule } = useStore();
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  function navigate(module: ModuleName) {
    setCurrentModule(module);
    onClose();
  }

  const items: CommandItem[] = [
    { id: 'dashboard', label: 'Dashboard', description: 'Panel główny', icon: <LayoutDashboard className="w-4 h-4" />, action: () => navigate('dashboard') },
    { id: 'zwiad', label: 'Zwiad przetargowy', description: 'Lista przetargów z BZP', icon: <Radar className="w-4 h-4" />, action: () => navigate('zwiad') },
    { id: 'pipeline', label: 'Pipeline', description: 'Kanban przetargów', icon: <GitBranch className="w-4 h-4" />, action: () => navigate('pipeline') },
    { id: 'kosztorys', label: 'Kosztorys', description: 'Wycena i kosztorysy', icon: <Calculator className="w-4 h-4" />, action: () => navigate('kosztorys') },
    { id: 'system', label: 'Ustawienia', description: 'Konfiguracja systemu', icon: <Settings className="w-4 h-4" />, action: () => navigate('system') },
    { id: 'import', label: 'Import danych', description: 'Importuj dane historyczne CSV', icon: <Upload className="w-4 h-4" />, action: () => navigate('system') },
  ];

  const filtered = query
    ? items.filter(i => i.label.toLowerCase().includes(query.toLowerCase()) || i.description?.toLowerCase().includes(query.toLowerCase()))
    : items;

  useEffect(() => {
    if (open) {
      setQuery('');
      setSelected(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    setSelected(0);
  }, [query]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { onClose(); return; }
      if (e.key === 'ArrowDown') { e.preventDefault(); setSelected(s => Math.min(s + 1, filtered.length - 1)); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); setSelected(s => Math.max(s - 1, 0)); return; }
      if (e.key === 'Enter') { e.preventDefault(); filtered[selected]?.action(); return; }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, filtered, selected, onClose]);

  return (
    <AnimatePresence>
      {open ? (
        <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] px-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-earth-950/70 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -8 }}
            transition={{ duration: 0.15, ease: [0.4, 0, 0.2, 1] }}
            className="relative w-full max-w-lg bg-earth-900 border border-earth-700/60 rounded-2xl shadow-2xl shadow-black/60 overflow-hidden"
          >
            {/* Search input */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-earth-800/60">
              <Search className="w-4 h-4 text-earth-500 shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Szukaj modułu lub akcji..."
                className="flex-1 bg-transparent text-earth-100 placeholder-earth-600 text-sm outline-none"
              />
              <button onClick={onClose} className="text-earth-600 hover:text-earth-300 transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Results */}
            <div className="py-2 max-h-80 overflow-y-auto">
              {filtered.length === 0 ? (
                <p className="px-4 py-6 text-center text-earth-600 text-sm">Brak wyników dla &quot;{query}&quot;</p>
              ) : filtered.map((item, idx) => (
                <button
                  key={item.id}
                  onClick={item.action}
                  onMouseEnter={() => setSelected(idx)}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${idx === selected ? 'bg-accent-primary/10 text-accent-primary' : 'text-earth-300 hover:bg-earth-800/60'}`}
                >
                  <span className={idx === selected ? 'text-accent-primary' : 'text-earth-500'}>{item.icon}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{item.label}</p>
                    {item.description && <p className="text-xs text-earth-600">{item.description}</p>}
                  </div>
                </button>
              ))}
            </div>

            {/* Footer hint */}
            <div className="px-4 py-2 border-t border-earth-800/60 flex items-center gap-3 text-xs text-earth-700">
              <span>↑↓ nawigacja</span>
              <span>↵ wybierz</span>
              <span>Esc zamknij</span>
            </div>
          </motion.div>
        </div>
      ) : null}
    </AnimatePresence>
  );
}
