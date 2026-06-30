'use client';

import { useState } from 'react';
import {
  Truck, Users, MapPin, Wrench, CheckCircle, XCircle,
  Phone, BarChart2,
} from 'lucide-react';

const SPRZET = [
  { id: 'e1', name: 'Koparka Komatsu PC210', type: 'Koparka gąsienicowa', capacity: '21 t', availability: true, location: 'Wrocław', status: 'Gotowa' },
  { id: 'e2', name: 'Wywrotka Volvo FH16', type: 'Wywrotka', capacity: '25 t', availability: true, location: 'Legnica', status: 'Gotowa' },
  { id: 'e3', name: 'Walec CAT CS64', type: 'Walec wibracyjny', capacity: '14 t', availability: false, location: 'Wrocław', status: 'Serwis' },
  { id: 'e4', name: 'Koparka Liebherr 934', type: 'Koparka gąsienicowa', capacity: '34 t', availability: true, location: 'Bielawa', status: 'Gotowa' },
  { id: 'e5', name: 'Spychacz CAT D6', type: 'Spycharka gąsienicowa', capacity: '19 t', availability: true, location: 'Wrocław', status: 'Gotowa' },
  { id: 'e6', name: 'Koparko-ładowarka JCB 3CX', type: 'Koparko-ładowarka', capacity: '8 t', availability: false, location: 'Świdnica', status: 'Na budowie S5' },
];

const PRACOWNICY = [
  { id: 'p1', name: 'Marek Kowalski', nameShort: 'MK', competencies: ['Operator koparki', 'Kierowca wywrotki'], available: true, tel: '+48 601 123 456' },
  { id: 'p2', name: 'Piotr Wiśniewski', nameShort: 'PW', competencies: ['Walcowanie', 'Geodezja'], available: false, currentProject: 'S5 Bolków', tel: '+48 602 234 567' },
  { id: 'p3', name: 'Tomasz Nowak', nameShort: 'TN', competencies: ['Operator koparki', 'Spawanie'], available: true, tel: '+48 603 345 678' },
  { id: 'p4', name: 'Adam Zając', nameShort: 'AZ', competencies: ['Kierowca wywrotki', 'Załadunek'], available: true, tel: '+48 604 456 789' },
  { id: 'p5', name: 'Jan Wróblewski', nameShort: 'JW', competencies: ['Operator walca', 'Kierowca TIR'], available: false, currentProject: 'A1 Częstochowa', tel: '+48 605 567 890' },
];

const IKONA_SPRZETU: Record<string, string> = {
  'Koparka gąsienicowa': '🏗️',
  'Wywrotka': '🚛',
  'Walec wibracyjny': '⚙️',
  'Spycharka gąsienicowa': '🚜',
  'Koparko-ładowarka': '🔧',
};

type TabType = 'sprzet' | 'pracownicy' | 'podsumowanie';

export function LogistykaPage() {
  const [tab, setTab] = useState<TabType>('sprzet');

  const availableSprzet = SPRZET.filter(s => s.availability).length;
  const availablePrac = PRACOWNICY.filter(p => p.available).length;

  const tabs: { key: TabType; label: string; icon: React.ReactNode }[] = [
    { key: 'sprzet', label: `Sprzęt (${SPRZET.length})`, icon: <Truck className="w-4 h-4" /> },
    { key: 'pracownicy', label: `Pracownicy (${PRACOWNICY.length})`, icon: <Users className="w-4 h-4" /> },
    { key: 'podsumowanie', label: 'Podsumowanie', icon: <BarChart2 className="w-4 h-4" /> },
  ];

  return (
    <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-earth-100">Logistyka</h2>
        <p className="text-earth-500 text-sm mt-0.5">Sprzęt i zasoby ludzkie</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-earth-900/60 p-1 rounded-xl w-fit border border-earth-800/40">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t.key
                ? 'bg-earth-800 text-earth-100 shadow-sm'
                : 'text-earth-500 hover:text-earth-300'
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* Sprzęt tab */}
      {tab === 'sprzet' && (
        <div className="grid grid-cols-2 gap-4">
          {SPRZET.map(s => (
            <div key={s.id} className="glass-card card-hover rounded-xl p-4 flex gap-4 items-start">
              <div className="w-12 h-12 rounded-xl bg-earth-800 flex items-center justify-center text-2xl shrink-0 border border-earth-700/40">
                {IKONA_SPRZETU[s.type] ?? '🚧'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <p className="text-earth-100 font-medium text-sm leading-snug">{s.name}</p>
                  <span className={`text-xs px-2 py-0.5 rounded-full whitespace-nowrap shrink-0 font-medium ${
                    s.availability
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
                      : 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20'
                  }`}>
                    {s.availability ? '● Dostępna' : '● ' + s.status}
                  </span>
                </div>
                <p className="text-earth-500 text-xs">{s.type} · {s.capacity}</p>
                <div className="flex items-center gap-1.5 mt-2">
                  <MapPin className="w-3 h-3 text-earth-600" />
                  <span className="text-earth-500 text-xs">{s.location}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pracownicy tab */}
      {tab === 'pracownicy' && (
        <div className="glass-card rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-earth-800/60">
                <th className="text-left px-5 py-3 text-earth-500 text-xs font-medium">Pracownik</th>
                <th className="text-left px-5 py-3 text-earth-500 text-xs font-medium">Kompetencje</th>
                <th className="text-left px-5 py-3 text-earth-500 text-xs font-medium">Lokalizacja</th>
                <th className="text-left px-4 py-3 text-earth-500 text-xs font-medium">Kontakt</th>
                <th className="text-right px-5 py-3 text-earth-500 text-xs font-medium">Dostępność</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-earth-800/40">
              {PRACOWNICY.map(p => (
                <tr key={p.id} className="hover:bg-earth-800/20 transition-colors">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <div className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                        p.available ? 'bg-accent-primary/20 text-accent-primary' : 'bg-earth-700 text-earth-400'
                      }`}>
                        {p.nameShort}
                      </div>
                      <p className="text-earth-200 text-sm font-medium">{p.name}</p>
                    </div>
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex flex-wrap gap-1">
                      {p.competencies.map(c => (
                        <span key={c} className="text-xs px-2 py-0.5 rounded-full bg-earth-800 text-earth-400 border border-earth-700/30">{c}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-5 py-3 text-earth-500 text-sm">
                    <div className="flex items-center gap-1.5">
                      <MapPin className="w-3 h-3 text-earth-600" />
                      {p.available ? 'Baza Wrocław' : (p as any).currentProject ?? '—'}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-earth-500 text-xs">
                    <div className="flex items-center gap-1.5">
                      <Phone className="w-3 h-3 text-earth-600" />
                      {p.tel}
                    </div>
                  </td>
                  <td className="px-5 py-3 text-right">
                    {p.available
                      ? <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full">
                          <CheckCircle className="w-3 h-3" /> Dostępny
                        </span>
                      : <span className="inline-flex items-center gap-1.5 text-xs font-medium text-yellow-400 bg-yellow-500/10 px-2.5 py-1 rounded-full">
                          <XCircle className="w-3 h-3" /> Na budowie
                        </span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Podsumowanie tab */}
      {tab === 'podsumowanie' && (
        <div className="space-y-6">
          {/* Stat cards */}
          <div className="grid grid-cols-2 gap-5">
            <div className="glass-card rounded-2xl p-6 border border-emerald-500/20 bg-emerald-500/5">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                  <Truck className="w-5 h-5 text-emerald-400" />
                </div>
                <p className="text-earth-400 text-sm font-medium">Dostępny sprzęt</p>
              </div>
              <p className="text-5xl font-black text-emerald-400">
                {availableSprzet}<span className="text-earth-500 text-2xl font-medium">/{SPRZET.length}</span>
              </p>
              <div className="mt-3 h-2 bg-earth-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 rounded-full transition-all"
                  style={{ width: `${(availableSprzet / SPRZET.length) * 100}%` }}
                />
              </div>
              <p className="text-earth-500 text-xs mt-2">
                {((availableSprzet / SPRZET.length) * 100).toFixed(0)}% floty gotowe do pracy
              </p>
            </div>

            <div className="glass-card rounded-2xl p-6 border border-accent-primary/20 bg-accent-primary/5">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-accent-primary/20 flex items-center justify-center">
                  <Users className="w-5 h-5 text-accent-primary" />
                </div>
                <p className="text-earth-400 text-sm font-medium">Dostępni pracownicy</p>
              </div>
              <p className="text-5xl font-black text-accent-primary">
                {availablePrac}<span className="text-earth-500 text-2xl font-medium">/{PRACOWNICY.length}</span>
              </p>
              <div className="mt-3 h-2 bg-earth-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent-primary rounded-full transition-all"
                  style={{ width: `${(availablePrac / PRACOWNICY.length) * 100}%` }}
                />
              </div>
              <p className="text-earth-500 text-xs mt-2">
                {((availablePrac / PRACOWNICY.length) * 100).toFixed(0)}% zespołu dostępne
              </p>
            </div>
          </div>

          {/* Detailed breakdown */}
          <div className="grid grid-cols-2 gap-4">
            <div className="glass-card rounded-xl p-4">
              <p className="text-earth-400 text-sm font-medium mb-3 flex items-center gap-2">
                <Wrench className="w-4 h-4 text-yellow-400" /> W serwisie
              </p>
              <div className="space-y-2">
                {SPRZET.filter(s => !s.availability).map(s => (
                  <div key={s.id} className="flex items-center justify-between text-xs">
                    <span className="text-earth-300">{s.name}</span>
                    <span className="text-yellow-400 bg-yellow-500/10 px-2 py-0.5 rounded-full">{s.status}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="glass-card rounded-xl p-4">
              <p className="text-earth-400 text-sm font-medium mb-3 flex items-center gap-2">
                <MapPin className="w-4 h-4 text-blue-400" /> Na budowach
              </p>
              <div className="space-y-2">
                {PRACOWNICY.filter(p => !p.available).map(p => (
                  <div key={p.id} className="flex items-center justify-between text-xs">
                    <span className="text-earth-300">{p.name}</span>
                    <span className="text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full">{(p as any).currentProject}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
