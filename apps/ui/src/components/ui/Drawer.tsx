'use client';

import { useEffect, useCallback, ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'motion/react';
import { X } from 'lucide-react';

type DrawerSide = 'right' | 'left';

interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  side?: DrawerSide;
  width?: string;
}

export function Drawer({
  isOpen,
  onClose,
  title,
  children,
  side = 'right',
  width = '420px',
}: DrawerProps) {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
  }, [onClose]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, handleKeyDown]);

  if (typeof document === 'undefined') return null;

  const initialX = side === 'right' ? '100%' : '-100%';
  const borderSide = side === 'right' ? 'border-l' : 'border-r';
  const positionCls = side === 'right' ? 'right-0' : 'left-0';

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 bg-earth-950/60 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            initial={{ x: initialX }}
            animate={{ x: 0 }}
            exit={{ x: initialX }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
            style={{ width }}
            className={[
              'absolute top-0 bottom-0',
              positionCls,
              'z-10 flex flex-col',
              'bg-earth-900',
              borderSide,
              'border-earth-700',
              'shadow-token-lg',
            ].join(' ')}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-earth-700/50 shrink-0">
              {title ? (
                <span className="section-label">{title}</span>
              ) : (
                <span />
              )}
              <button
                onClick={onClose}
                className="btn-ghost w-7 h-7 flex items-center justify-center p-0 rounded-token"
                aria-label="Zamknij"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Body — scrollable */}
            <div className="overflow-y-auto flex-1 px-5 py-4">
              {children}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}

export default Drawer;
