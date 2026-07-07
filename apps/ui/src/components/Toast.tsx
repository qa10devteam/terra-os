'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { CheckCircle, AlertTriangle, XCircle, Info, X } from 'lucide-react';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  createdAt: number;
}

const TOAST_DURATION = 4000;
const MAX_TOASTS = 3;

// Global state via module-level subscribers pattern
const listeners = new Set<(toasts: ToastItem[]) => void>();
let globalToasts: ToastItem[] = [];
let counter = 0;

function notifyListeners() {
  listeners.forEach(fn => fn([...globalToasts]));
}

export function showToast(type: ToastType, message: string) {
  const id = String(++counter);
  const toast: ToastItem = { id, type, message, createdAt: Date.now() };

  // Keep max 3
  if (globalToasts.length >= MAX_TOASTS) {
    globalToasts = globalToasts.slice(globalToasts.length - MAX_TOASTS + 1);
  }
  globalToasts = [...globalToasts, toast];
  notifyListeners();

  setTimeout(() => {
    globalToasts = globalToasts.filter(t => t.id !== id);
    notifyListeners();
  }, TOAST_DURATION);
}

const TOAST_CONFIG: Record<ToastType, {
  Icon: typeof CheckCircle;
  iconClass: string;
  borderClass: string;
  bgClass: string;
  textClass: string;
  barClass: string;
}> = {
  success: {
    Icon: CheckCircle,
    iconClass: 'text-emerald-400',
    borderClass: 'border-emerald-500/30',
    bgClass: 'bg-emerald-500/10',
    textClass: 'text-emerald-100',
    barClass: 'bg-emerald-500',
  },
  error: {
    Icon: XCircle,
    iconClass: 'text-red-400',
    borderClass: 'border-red-500/30',
    bgClass: 'bg-red-500/10',
    textClass: 'text-red-100',
    barClass: 'bg-red-500',
  },
  warning: {
    Icon: AlertTriangle,
    iconClass: 'text-yellow-400',
    borderClass: 'border-yellow-500/30',
    bgClass: 'bg-yellow-500/10',
    textClass: 'text-yellow-100',
    barClass: 'bg-yellow-500',
  },
  info: {
    Icon: Info,
    iconClass: 'text-blue-400',
    borderClass: 'border-blue-500/30',
    bgClass: 'bg-blue-500/10',
    textClass: 'text-blue-100',
    barClass: 'bg-blue-500',
  },
};

function ToastProgress({ duration, barClass }: { duration: number; barClass: string }) {
  const [width, setWidth] = useState(100);
  const startRef = useRef(Date.now());
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    startRef.current = Date.now();
    const tick = () => {
      const elapsed = Date.now() - startRef.current;
      const pct = Math.max(0, 100 - (elapsed / duration) * 100);
      setWidth(pct);
      if (pct > 0) {
        rafRef.current = requestAnimationFrame(tick);
      }
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [duration]);

  return (
    <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-earth-800/60">
      <div
        className={`h-full ${barClass} transition-none rounded-full`}
        style={{ width: `${width}%` }}
      />
    </div>
  );
}

function SingleToast({ toast, onDismiss }: { toast: ToastItem; onDismiss: (id: string) => void }) {
  const config = TOAST_CONFIG[toast.type];
  const Icon = config.Icon;
  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 80, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 80, scale: 0.9, transition: { duration: 0.18 } }}
      transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
      className={`relative flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg border overflow-hidden min-w-[280px] max-w-[380px] ${config.bgClass} ${config.borderClass}`}
      style={{ backdropFilter: 'blur(12px)' }}
    >
      <Icon className={`w-5 h-5 shrink-0 ${config.iconClass}`} />
      <span className={`text-sm font-medium flex-1 ${config.textClass}`}>{toast.message}</span>
      <button
        onClick={() => onDismiss(toast.id)}
        aria-label="Zamknij"
        className="w-5 h-5 rounded flex items-center justify-center text-earth-500 hover:text-earth-300 transition-colors shrink-0"
      >
        <X className="w-3.5 h-3.5" />
      </button>
      <ToastProgress duration={TOAST_DURATION} barClass={config.barClass} />
    </motion.div>
  );
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  useEffect(() => {
    const handler = (updated: ToastItem[]) => setToasts(updated);
    listeners.add(handler);
    return () => { listeners.delete(handler); };
  }, []);

  const dismiss = useCallback((id: string) => {
    globalToasts = globalToasts.filter(t => t.id !== id);
    notifyListeners();
  }, []);

  return (
    <div className="fixed bottom-24 right-6 z-[60] flex flex-col-reverse gap-2 items-end pointer-events-none">
      <AnimatePresence mode="popLayout">
        {toasts.map(toast => (
          <div key={toast.id} className="pointer-events-auto">
            <SingleToast toast={toast} onDismiss={dismiss} />
          </div>
        ))}
      </AnimatePresence>
    </div>
  );
}
