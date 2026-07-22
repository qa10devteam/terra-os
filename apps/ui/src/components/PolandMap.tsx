'use client';
/**
 * PolandMap — interaktywna SVG mapa Polski z koloryzacją wg liczby tenderów.
 * Kliknięcie województwa ustawia filtr; `selected` podświetla aktywne.
 */

import { useMemo } from 'react';

interface Props {
  /** Liczba tenderów per nazwa województwa (lowercase, z DB) */
  counts: Record<string, number>;
  selected: string;   // 'Wszystkie' | nazwa z WOJEWODZTWA
  onSelect: (woj: string) => void;
}

// Normalise name z DB (lowercase, warianty) → display label
const NORM: Record<string, string> = {
  'dolnośląskie':       'Dolnośląskie',
  'kujawsko-pomorskie': 'Kujawsko-Pomorskie',
  'lubelskie':          'Lubelskie',
  'lubuskie':           'Lubuskie',
  'łódzkie':            'Łódzkie',
  'małopolskie':        'Małopolskie',
  'mazowieckie':        'Mazowieckie',
  'opolskie':           'Opolskie',
  'podkarpackie':       'Podkarpackie',
  'podlaskie':          'Podlaskie',
  'pomorskie':          'Pomorskie',
  'śląskie':            'Śląskie',
  'slaskie':            'Śląskie',
  'świętokrzyskie':     'Świętokrzyskie',
  'warmińsko-mazurskie':'Warmińsko-Mazurskie',
  'wielkopolskie':      'Wielkopolskie',
  'zachodniopomorskie': 'Zachodniopomorskie',
};

// Simplified SVG paths per voivodeship (scaled 0-800 × 0-900)
// Paths approximated from official boundaries — good enough for a filter UI
const PATHS: { id: string; label: string; d: string; cx: number; cy: number }[] = [
  {
    id: 'Zachodniopomorskie', label: 'Zachodniopomorskie',
    cx: 120, cy: 120,
    d: 'M60,40 L220,40 L240,80 L230,160 L200,200 L150,210 L100,200 L70,160 L55,110 Z',
  },
  {
    id: 'Pomorskie', label: 'Pomorskie',
    cx: 310, cy: 105,
    d: 'M230,40 L410,40 L430,80 L420,150 L380,160 L310,165 L240,160 L230,110 Z',
  },
  {
    id: 'Warmińsko-Mazurskie', label: 'Warmińsko-Mazurskie',
    cx: 490, cy: 120,
    d: 'M420,40 L590,40 L610,80 L600,180 L550,190 L470,185 L420,170 L415,100 Z',
  },
  {
    id: 'Podlaskie', label: 'Podlaskie',
    cx: 620, cy: 190,
    d: 'M590,80 L700,80 L720,130 L710,260 L660,280 L590,270 L565,210 L580,150 Z',
  },
  {
    id: 'Kujawsko-Pomorskie', label: 'Kujawsko-Pomorskie',
    cx: 290, cy: 240,
    d: 'M215,165 L380,162 L390,240 L360,295 L280,300 L215,290 L200,240 Z',
  },
  {
    id: 'Lubuskie', label: 'Lubuskie',
    cx: 100, cy: 280,
    d: 'M55,200 L170,205 L180,290 L165,360 L110,375 L55,360 L40,290 Z',
  },
  {
    id: 'Wielkopolskie', label: 'Wielkopolskie',
    cx: 260, cy: 335,
    d: 'M170,205 L380,200 L400,295 L390,400 L330,420 L200,415 L165,360 L178,290 Z',
  },
  {
    id: 'Mazowieckie', label: 'Mazowieckie',
    cx: 510, cy: 290,
    d: 'M390,200 L580,195 L600,270 L590,390 L520,410 L430,405 L400,340 L395,255 Z',
  },
  {
    id: 'Łódzkie', label: 'Łódzkie',
    cx: 370, cy: 415,
    d: 'M300,300 L450,298 L460,380 L430,440 L350,450 L290,440 L280,365 Z',
  },
  {
    id: 'Dolnośląskie', label: 'Dolnośląskie',
    cx: 160, cy: 460,
    d: 'M100,380 L265,375 L280,460 L265,540 L180,555 L95,540 L80,460 Z',
  },
  {
    id: 'Opolskie', label: 'Opolskie',
    cx: 305, cy: 470,
    d: 'M265,375 L380,372 L395,455 L370,520 L290,525 L265,455 Z',
  },
  {
    id: 'Śląskie', label: 'Śląskie',
    cx: 400, cy: 500,
    d: 'M375,375 L480,372 L500,450 L490,540 L400,550 L365,525 L370,455 Z',
  },
  {
    id: 'Świętokrzyskie', label: 'Świętokrzyskie',
    cx: 490, cy: 430,
    d: 'M450,360 L570,358 L580,420 L565,480 L480,490 L450,470 L445,420 Z',
  },
  {
    id: 'Lubelskie', label: 'Lubelskie',
    cx: 610, cy: 395,
    d: 'M575,270 L710,268 L730,330 L720,490 L640,510 L570,500 L555,435 L560,320 Z',
  },
  {
    id: 'Podkarpackie', label: 'Podkarpackie',
    cx: 590, cy: 530,
    d: 'M480,460 L660,455 L680,510 L660,590 L580,605 L490,595 L470,540 Z',
  },
  {
    id: 'Małopolskie', label: 'Małopolskie',
    cx: 430, cy: 565,
    d: 'M355,460 L500,458 L510,530 L480,600 L390,610 L345,590 L340,530 Z',
  },
];

function heat(count: number, max: number): string {
  if (count === 0 || max === 0) return 'rgba(255,255,255,0.04)';
  const t = Math.sqrt(count / max); // sqrt → better visual spread
  // dark navy → emerald glow
  const r = Math.round(20  + t * 10);
  const g = Math.round(30  + t * 150);
  const b = Math.round(50  + t * 80);
  return `rgba(${r},${g},${b},${0.25 + t * 0.55})`;
}

export function PolandMap({ counts, selected, onSelect }: Props) {
  // Normalise counts keys → display labels
  const normCounts = useMemo(() => {
    const out: Record<string, number> = {};
    for (const [k, v] of Object.entries(counts)) {
      const label = NORM[k.toLowerCase()] ?? k;
      out[label] = (out[label] ?? 0) + v;
    }
    return out;
  }, [counts]);

  const max = useMemo(() => Math.max(1, ...Object.values(normCounts)), [normCounts]);

  return (
    <div className="relative w-full" style={{ aspectRatio: '9/10', maxWidth: 280 }}>
      <svg
        viewBox="0 0 800 900"
        className="w-full h-full"
        style={{ overflow: 'visible' }}
      >
        {PATHS.map((p) => {
          const count = normCounts[p.id] ?? 0;
          const isSelected = selected === p.id;
          const fill = isSelected
            ? 'rgba(52,211,153,0.55)'
            : heat(count, max);

          return (
            <g key={p.id} className="cursor-pointer group" onClick={() => onSelect(isSelected ? 'Wszystkie' : p.id)}>
              <path
                d={p.d}
                fill={fill}
                stroke={isSelected ? 'rgba(52,211,153,0.9)' : 'rgba(255,255,255,0.12)'}
                strokeWidth={isSelected ? 2.5 : 1}
                className="transition-all duration-200 group-hover:brightness-125"
              />
              {/* Label */}
              {count > 0 && (
                <text
                  x={p.cx}
                  y={p.cy + 4}
                  textAnchor="middle"
                  fontSize={18}
                  fontWeight={isSelected ? '700' : '500'}
                  fill={isSelected ? '#34d399' : 'rgba(255,255,255,0.7)'}
                  className="pointer-events-none select-none"
                  style={{ fontFamily: 'system-ui, sans-serif' }}
                >
                  {count}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      {/* Legend */}
      <div className="absolute bottom-0 left-0 right-0 flex justify-between text-[10px] text-slate-500 px-1">
        <span>0</span>
        <span className="text-emerald-400/60">więcej przetargów</span>
        <span>{max}</span>
      </div>
    </div>
  );
}
