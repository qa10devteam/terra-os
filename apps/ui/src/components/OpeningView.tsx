'use client';

import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { ArrowRight } from 'lucide-react';

type Phase = 'intro' | 'shovel' | 'ready';

interface OpeningViewProps {
  onStart: () => void;
}

export function OpeningView({ onStart }: OpeningViewProps) {
  const [phase, setPhase] = useState<Phase>('intro');

  useEffect(() => {
    const t1 = setTimeout(() => setPhase('shovel'), 800);
    const t2 = setTimeout(() => setPhase('ready'), 2200);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="min-h-[100dvh] w-full flex flex-col items-center justify-center bg-earth-950 text-earth-100 overflow-hidden relative"
    >
      {/* Background image */}
      <div className="absolute inset-0 z-0 opacity-35">
        <img
          src="/assets/illustrations/shovel-hero.png"
          alt=""
          aria-hidden="true"
          className="w-full h-full object-cover"
        />
      </div>
      <div className="absolute inset-0 z-0 bg-gradient-to-t from-earth-950 via-earth-950/75 to-transparent" />
      {/* Grid texture */}
      <div
        className="absolute inset-0 z-0 opacity-[0.03]"
        style={{
          backgroundImage:
            'repeating-linear-gradient(0deg,#fff 0px,#fff 1px,transparent 1px,transparent 60px),repeating-linear-gradient(90deg,#fff 0px,#fff 1px,transparent 1px,transparent 60px)',
        }}
      />

      {/* Logo — visible in 'shovel' phase */}
      {phase !== 'intro' && (
        <motion.div
          key="logo"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="z-10 mb-8"
        >
          <img
            src="/assets/logo/logo.svg"
            alt="Terra.OS"
            className="w-56 h-auto mx-auto drop-shadow-2xl"
          />
        </motion.div>
      )}

      {/* Title — visible from 'shovel' onward */}
      {phase !== 'intro' && (
        <motion.div
          key="title"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="text-center z-10 px-6"
        >
          <h1 className="text-6xl md:text-7xl font-bold mb-3 tracking-tighter leading-none">
            Terra<span className="text-accent-primary">.OS</span>
          </h1>
          <p className="text-xl text-earth-400 mb-2 font-light">
            System Zarządzania Przetargami i&nbsp;Budową
          </p>
          <p className="text-sm text-earth-600 mb-12 font-mono tracking-wide">
            v2.1 — Dzierżoniów, Dolnośląskie
          </p>
        </motion.div>
      )}

      {/* Module hints — only in shovel phase */}
      {phase === 'shovel' && (
        <motion.div
          key="hints"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="absolute bottom-28 flex items-center gap-4 text-earth-600 text-xs z-10 tracking-widest uppercase"
        >
          <span>Zwiad</span>
          <span className="text-earth-800">•</span>
          <span>Kosztorys</span>
          <span className="text-earth-800">•</span>
          <span>Silnik</span>
          <span className="text-earth-800">•</span>
          <span>Decyzja</span>
        </motion.div>
      )}

      {/* CTA Button — visible in 'ready' phase */}
      {phase === 'ready' && (
        <motion.button
          key="cta"
          initial={{ opacity: 0, scale: 0.88, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          whileHover={{ scale: 1.04, y: -2 }}
          whileTap={{ scale: 0.97 }}
          transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
          onClick={onStart}
          className="group relative flex items-center gap-3 px-9 py-4 bg-accent-primary text-earth-950 rounded-xl font-bold text-lg shadow-xl shadow-accent-primary/25 hover:shadow-accent-primary/40 transition-shadow z-10 cursor-pointer"
        >
          <span className="absolute inset-0 rounded-xl bg-accent-primary/20 blur-xl -z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          Wejdź do systemu
          <ArrowRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform duration-200" />
        </motion.button>
      )}

      {/* Footer */}
      {phase === 'ready' && (
        <motion.div
          key="footer"
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.5 }}
          transition={{ delay: 0.5 }}
          className="absolute bottom-6 text-earth-700 text-xs z-10"
        >
          QA10 Labs © 2026
        </motion.div>
      )}
    </motion.div>
  );
}
