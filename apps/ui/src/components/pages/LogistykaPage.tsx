'use client';

import { useState } from 'react';
import {
  Truck, Users, MapPin, Wrench, CheckCircle, XCircle,
  Phone, BarChart2, PackageX, UserX, LayoutList,
} from 'lucide-react';

const SPRZET = [
  { id: 'e1', name: 'Koparka Komatsu PC210',    type: 'Koparka gąsienicowa',   capacity: '21 t', status: 'Dostępny',  location: 'Wrocław' },
  { id: 'e2', name: 'Wywrotka Volvo FH16',       type: 'Wywrotka',              capacity: '25 t', status: 'Dostępny',  location: 'Legnica' },
  { id: 'e3', name: 'Walec CAT CS64',            type: 'Walec wibracyjny',      capacity: '14 t', status: 'Serwis',    location: 'Wrocław' },
  { id: 'e4', name: 'Koparka Liebherr 934',      type: 'Koparka gąsienicowa',   capacity: '34 t', status: 'Dostępny',  location: 'Bielawa' },
  { id: 'e5', name: 'Spychacz CAT D6',           type: 'Spycharka gąsienicowa', capacity: '19 t', status: 'Dostępny',  location: 'Wrocław' },
  { id: 'e6', name: 'Koparko-ładowarka JCB 3CX', type: 'Koparko-ładowarka',    capacity: '8 t',  status: 'Zajęty',    location: 'Świdnica' },
];

const PRACOWNICY = [
  { id: 'p1', name: 'Marek Kowalski',   nameShort: 'MK', role: 'Operator maszyn',  competencies: ['Operator koparki', 'Kierowca wywrotki'], available: true,  tel: '+48 601 123 456' },
  { id: 'p2', name: 'Piotr Wiśniewski', nameShort: 'PW', role: 'Geodeta',          competencies: ['Walcowanie', 'Geodezja'],                 available: false, tel: '+48 602 234 567', currentProject: 'S5 Bolków' },
  { id: 'p3', name: 'Tomasz Nowak',     nameShort: 'TN', role: 'Operator / Spawacz', competencies: ['Operator koparki', 'Spawanie'],         available: true,  tel: '+48 603 345 678' },
  { id: 'p4', name: 'Adam Zając',       nameShort: 'AZ', role: 'Kierowca',         competencies: ['Kierowca wywrotki', 'Załadunek'],         available: true,  tel: '+48 604 456 789' },
  { id: 'p5', name: 'Jan Wróblewski',   nameShort: 'JW', role: 'Kierowca TIR',     competencies: ['Operator walca', 'Kierowca TIR'],        available: false, tel: '+48 605 567 890', currentProject: 'A1 Częstochowa' },
];

const IKONA_SPRZETU: Record<string, string> = {
  'Koparka gąsienicowa':   '🏗️',
  'Wywrotka':              '🚛',
  'Walec wibracyjny':      '⚙️',
  'Spycharka gąsienicowa': '🚜',
  'Koparko-ładowarka':     '🔧',
};

function statusBadge(status: string) {
  if (status === 'Dostępny') {
    return 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20';
  }
  if (status === 'Serwis') {
    return 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/20';
  }
  // Zajęty
  return 'bg-blue-500/15 text-blue-400 border border-blue-500/20';
}

type TabType = 'sprzet' | 'pracownicy' | 'podsumowanie';

export function LogistykaPage() {
  const [tab, setTab] = useState<TabType>('sprzet');

  const dostepnySprzet  = SPRZET.filter(s => s.status === 'Dostępny').length;
  const wSerwisie       = SPRZET.filter(s => s.status === 'Serwis').length;
  const zajetySprzet    = SPRZET.filter(s => s.status === 'Zajęty').length;
  const dostepniPrac    = PRACOWNICY.filter(p => p.available).length;

  const tabs: { key: TabType; label: string; icon: React.ReactNode }[] = [
    { key: 'sprzet',       label: `Sprzęt (${SPRZET.length})`,      icon: <Truck    className="w-4 h-4" /> },
    { key: 'pracownicy',   label: `Pracownicy (${PRACOWNICY.length})`, icon: <Users  className="w-4 h-4" /> },
    { key: 'podsumowanie', label: 'Podsumowanie',                    icon: <BarChart2 className="w-4 h-4" /> },
  ];

  return (
    <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto">
      {/* Nagłówek */}
      <div>
        <h2 className="text-xl font-semibold text-earth-100">Logistyka</h2>
        <p className="text-earth-500 text-sm mt-0.5">Sprzęt i zasoby ludzkie</p>
      </div>

      {/* Taby */}
      <div className="flex gap-1 bg-earth-900/60 p-1 rounded-xl w-fit border border-earth-800/40">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t.key
                ? 'bg-earth-800 text-earth-100 shadow-sm border border-earth-700/40'
                : 'text-earth-500 hover:text-earth-300'
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Tab: Sprzęt ─────────────────────────────────────────── */}
      {tab === 'sprzet' && (
        <>
          {SPRZET.length === 0 ? (
            <div className="glass-card rounded-2xl p-14 text-center">
              <PackageX className="w-12 h-12 text-earth-700 mx-auto mb-4" />
              <p className="text-earth-300 font-semibold mb-1">Brak sprzętu w bazie</p>
              <p className="text-earth-600 text-sm">Dodaj maszyny, aby zarządzać flotą</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {SPRZET.map(s => (
                <div key={s.id} className="glass-card card-hover rounded-xl p-4 flex gap-4 items-start">
                  <div className="w-12 h-12 rounded-xl bg-earth-800 flex items-center justify-center text-2xl shrink-0 border border-earth-700/40">
                    {IKONA_SPRZETU[s.type] ?? '🚧'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <p className="text-earth-100 font-medium text-sm leading-snug">{s.name}</p>
                      <span className={`text-xs px-2 py-0.5 rounded-full whitespace-nowrap shrink-0 font-medium ${statusBadge(s.status)}`}>
                        ● {s.status}
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
        </>
      )}

      {/* ── Tab: Pracownicy ──────────────────────────────────────── */}
      {tab === 'pracownicy' && (
        <>
          {PRACOWNICY.length === 0 ? (
            <div className="glass-card rounded-2xl p-14 text-center">
              <UserX className="w-12 h-12 text-earth-700 mx-auto mb-4" />
              <p className="text-earth-300 font-semibold mb-1">Brak pracowników w bazie</p>
              <p className="text-earth-600 text-sm">Dodaj pracowników, aby zarządzać zespołem</p>
            </div>
          ) : (
            <div className="glass-card rounded-xl overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-earth-800/60">
                    <th className="text-left px-5 py-3 text-earth-500 text-xs font-medium uppercase tracking-wide">Pracownik</th>
                    <th className="text-left px-5 py-3 text-earth-500 text-xs font-medium uppercase tracking-wide">Rola</th>
                    <th className="text-left px-5 py-3 text-earth-500 text-xs font-medium uppercase tracking-wide">Kompetencje</th>
                    <th className="text-left px-4 py-3 text-earth-500 text-xs font-medium uppercase tracking-wide">Kontakt</th>
                    <th className="text-right px-5 py-3 text-earth-500 text-xs font-medium uppercase tracking-wide">Dostępność</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-earth-800/40">
                  {PRACOWNICY.map(p => (
                    <tr key={p.id} className="hover:bg-earth-800/20 transition-colors">
                      {/* Imię i nazwisko */}
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                          <div className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                            p.available ? 'bg-accent-primary/20 text-accent-primary' : 'bg-earth-700 text-earth-400'
                          }`}>
                            {p.nameShort}
                          </div>
                          <div>
                            <p className="text-earth-200 text-sm font-medium">{p.name}</p>
                            {!p.available && (p as any).currentProject && (
                              <p className="text-earth-600 text-xs flex items-center gap-1 mt-0.5">
                                <MapPin className="w-3 h-3" /> {(p as any).currentProject}
                              </p>
                            )}
                          </div>
                        </div>
                      </td>
                      {/* Rola */}
                      <td className="px-5 py-3">
                        <span className="text-earth-400 text-xs px-2 py-0.5 rounded-full bg-earth-800/60 border border-earth-700/30">
                          {p.role}
                        </span>
                      </td>
                      {/* Kompetencje */}
                      <td className="px-5 py-3">
                        <div className="flex flex-wrap gap-1">
                          {p.competencies.map(c => (
                            <span key={c} className="text-xs px-2 py-0.5 rounded-full bg-earth-800 text-earth-400 border border-earth-700/30">{c}</span>
                          ))}
                        </div>
                      </td>
                      {/* Kontakt */}
                      <td className="px-4 py-3 text-earth-500 text-xs">
                        <div className="flex items-center gap-1.5">
                          <Phone className="w-3 h-3 text-earth-600" />
                          {p.tel}
                        </div>
                      </td>
                      {/* Dostępność */}
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
        </>
      )}

      {/* ── Tab: Podsumowanie ────────────────────────────────────── */}
      {tab === 'podsumowanie' && (
        <>
          {SPRZET.length === 0 && PRACOWNICY.length === 0 ? (
            <div className="glass-card rounded-2xl p-14 text-center">
              <LayoutList className="w-12 h-12 text-earth-700 mx-auto mb-4" />
              <p className="text-earth-300 font-semibold mb-1">Brak danych do podsumowania</p>
              <p className="text-earth-600 text-sm">Dodaj sprzęt i pracowników, aby zobaczyć statystyki</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Stat cards */}
              <div className="grid grid-cols-2 gap-5">
                {/* Sprzęt */}
                <div className="glass-card rounded-2xl p-6 border border-emerald-500/20 bg-emerald-500/5">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                      <Truck className="w-5 h-5 text-emerald-400" />
                    </div>
                    <div>
                      <p className="text-earth-400 text-sm font-medium">Dostępny sprzęt</p>
                      <p className="text-earth-600 text-xs">Maszyny gotowe do pracy</p>
                    </div>
                  </div>
                  <p className="text-5xl font-black text-emerald-400">
                    {dostepnySprzet}<span className="text-earth-500 text-2xl font-medium">/{SPRZET.length}</span>
                  </p>
                  <div className="mt-3">
                    <div className="flex justify-between text-xs text-earth-500 mb-1">
                      <span>Dostępność floty</span>
                      <span>{((dostepnySprzet / SPRZET.length) * 100).toFixed(0)}%</span>
                    </div>
                    <div className="h-2 bg-earth-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full transition-all"
                        style={{ width: `${(dostepnySprzet / SPRZET.length) * 100}%` }}
                      />
                    </div>
                  </div>
                  <div className="mt-3 flex gap-3 text-xs">
                    <span className="text-yellow-400">⚙ {wSerwisie} w serwisie</span>
                    <span className="text-blue-400">🔒 {zajetySprzet} zajęty</span>
                  </div>
                </div>

                {/* Pracownicy */}
                <div className="glass-card rounded-2xl p-6 border border-accent-primary/20 bg-accent-primary/5">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-xl bg-accent-primary/20 flex items-center justify-center">
                      <Users className="w-5 h-5 text-accent-primary" />
                    </div>
                    <div>
                      <p className="text-earth-400 text-sm font-medium">Dostępni pracownicy</p>
                      <p className="text-earth-600 text-xs">Gotowi do nowego zlecenia</p>
                    </div>
                  </div>
                  <p className="text-5xl font-black text-accent-primary">
                    {dostepniPrac}<span className="text-earth-500 text-2xl font-medium">/{PRACOWNICY.length}</span>
                  </p>
                  <div className="mt-3">
                    <div className="flex justify-between text-xs text-earth-500 mb-1">
                      <span>Dostępność zespołu</span>
                      <span>{((dostepniPrac / PRACOWNICY.length) * 100).toFixed(0)}%</span>
                    </div>
                    <div className="h-2 bg-earth-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-accent-primary rounded-full transition-all"
                        style={{ width: `${(dostepniPrac / PRACOWNICY.length) * 100}%` }}
                      />
                    </div>
                  </div>
                  <div className="mt-3 text-xs text-yellow-400">
                    ⏳ {PRACOWNICY.length - dostepniPrac} na budowach
                  </div>
                </div>
              </div>

              {/* Szczegóły */}
              <div className="grid grid-cols-2 gap-4">
                <div className="glass-card rounded-xl p-4">
                  <p className="text-earth-400 text-sm font-medium mb-3 flex items-center gap-2">
                    <Wrench className="w-4 h-4 text-yellow-400" /> Sprzęt w serwisie / zajęty
                  </p>
                  {SPRZET.filter(s => s.status !== 'Dostępny').length === 0 ? (
                    <p className="text-earth-600 text-xs">Cały sprzęt jest dostępny</p>
                  ) : (
                    <div className="space-y-2">
                      {SPRZET.filter(s => s.status !== 'Dostępny').map(s => (
                        <div key={s.id} className="flex items-center justify-between text-xs">
                          <span className="text-earth-300">{s.name}</span>
                          <span className={`px-2 py-0.5 rounded-full ${statusBadge(s.status)}`}>{s.status}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="glass-card rounded-xl p-4">
                  <p className="text-earth-400 text-sm font-medium mb-3 flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-blue-400" /> Pracownicy na budowach
                  </p>
                  {PRACOWNICY.filter(p => !p.available).length === 0 ? (
                    <p className="text-earth-600 text-xs">Wszyscy pracownicy są w bazie</p>
                  ) : (
                    <div className="space-y-2">
                      {PRACOWNICY.filter(p => !p.available).map(p => (
                        <div key={p.id} className="flex items-center justify-between text-xs">
                          <span className="text-earth-300">{p.name}</span>
                          <span className="text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full">{(p as any).currentProject}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
