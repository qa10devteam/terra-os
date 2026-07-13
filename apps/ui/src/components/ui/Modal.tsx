'use client';

import { useEffect, useCallback, ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'motion/react';
import { X } from 'lucide-react';

type ModalSize = 'sm' | 'md' | 'lg' | 'xl';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  size?: ModalSize;
}

const SIZE_CLS: Record<ModalSize, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
};

export function Modal({ isOpen, onClose, title, children, size = 'md' }: ModalProps) {
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

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 bg-earth-950/80 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className={[
              'relative w-full z-10',
              'bg-earth-900 border border-earth-700 rounded-token-xl shadow-token-glow',
              'flex flex-col max-h-[90vh]',
              SIZE_CLS[size],
            ].join(' ')}
          >
            {/* Header */}
            {(title !== undefined) && (
              <div className="flex items-center justify-between px-5 py-4 border-b border-earth-700/50 shrink-0">
                <span className="section-label">{title}</span>
                <button
                  onClick={onClose}
                  className="btn-ghost w-7 h-7 flex items-center justify-center p-0 rounded-token"
                  aria-label="Zamknij"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
            {title === undefined && (
              <button
                onClick={onClose}
                className="btn-ghost absolute top-3 right-3 w-7 h-7 flex items-center justify-center p-0 rounded-token z-10"
                aria-label="Zamknij"
              >
                <X className="w-4 h-4" />
              </button>
            )}

            {/* Body — scrollable */}
            <div className="overflow-y-auto px-5 py-4 flex-1">
              {children}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}

export default Modal;
