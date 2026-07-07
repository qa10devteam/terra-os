'use client';

import { useState, useEffect } from 'react';
import { X, ChevronRight, ChevronLeft, Sparkles } from 'lucide-react';

const TOUR_STEPS = [
  {
    title: 'Panel główny',
    description: 'Przegląd aktywnych przetargów, wartość pipeline, scoring dopasowania i szybkie akcje.',
    module: 'dashboard',
  },
  {
    title: 'Zwiad przetargowy',
    description: 'Lista przetargów z BZP z filtrami, sortowaniem i eksportem CSV. Kliknij wiersz aby zobaczyć szczegóły.',
    module: 'zwiad',
  },
  {
    title: 'Silnik AI',
    description: 'Analiza feasibility — weryfikacja zgodności z PZP, identyfikacja ryzyk i rekomendacja GO/NO-GO.',
    module: 'silnik',
  },
  {
    title: 'Pipeline',
    description: 'Kanban z etapami przetargu. Przeciągaj karty między kolumnami: Nowy → Analiza → Wyceniony → GO.',
    module: 'pipeline',
  },
  {
    title: 'Pogoda budowy',
    description: '14-dniowa prognoza z ryzykiem budowlanym (opady, mróz, wiatr). Dane z Open-Meteo dla dowolnego miasta.',
    module: 'pogoda',
  },
];

export function DemoTour() {
  const [visible, setVisible] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    const seen = localStorage.getItem('terra_tour_seen');
    if (!seen) {
      const timer = setTimeout(() => setVisible(true), 2000);
      return () => clearTimeout(timer);
    }
  }, []);

  function dismiss() {
    setVisible(false);
    localStorage.setItem('terra_tour_seen', '1');
  }

  function next() {
    if (step < TOUR_STEPS.length - 1) setStep(s => s + 1);
    else dismiss();
  }

  function prev() {
    if (step > 0) setStep(s => s - 1);
  }

  if (!visible) return null;

  const current = TOUR_STEPS[step];

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-earth-950/60 backdrop-blur-sm" onClick={dismiss} />
      <div className="relative z-10 w-full max-w-md bg-earth-900 border border-earth-700/60 rounded-2xl shadow-2xl p-6">
        <button onClick={dismiss} className="absolute top-4 right-4 text-earth-500 hover:text-earth-200">
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="w-5 h-5 text-accent-primary" />
          <span className="text-xs text-earth-500 font-medium">TOUR {step + 1}/{TOUR_STEPS.length}</span>
        </div>

        <h3 className="text-lg font-bold text-earth-100 mb-2">{current.title}</h3>
        <p className="text-sm text-earth-400 leading-relaxed mb-6">{current.description}</p>

        <div className="flex items-center justify-between">
          <div className="flex gap-1.5">
            {TOUR_STEPS.map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full transition-colors ${i === step ? 'bg-accent-primary' : 'bg-earth-700'}`}
              />
            ))}
          </div>
          <div className="flex gap-2">
            {step > 0 && (
              <button onClick={prev} className="flex items-center gap-1 px-3 py-1.5 text-sm text-earth-400 hover:text-earth-200">
                <ChevronLeft className="w-4 h-4" /> Wstecz
              </button>
            )}
            <button
              onClick={next}
              className="flex items-center gap-1 px-4 py-1.5 bg-accent-primary text-earth-950 text-sm font-semibold rounded-lg hover:bg-accent-primary/90"
            >
              {step === TOUR_STEPS.length - 1 ? 'Rozpocznij' : 'Dalej'} <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
