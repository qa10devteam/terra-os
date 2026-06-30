'use client';

import { useStore } from '@/store/useStore';
import {
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  Radar,
  Calculator,
  Brain,
  Scale,
  Truck,
  ShieldCheck,
  GitBranch,
  Settings,
  CloudSun,
} from 'lucide-react';

const modules = [
  { id: 'dashboard' as const, icon: LayoutDashboard, name: 'Dashboard',  desc: 'Panel główny' },
  { id: 'zwiad'     as const, icon: Radar,           name: 'Zwiad',      desc: 'Zwiad przetargowy' },
  { id: 'kosztorys' as const, icon: Calculator,      name: 'Kosztorys',  desc: 'Kosztorys 2 warianty' },
  { id: 'silnik'    as const, icon: Brain,           name: 'Silnik',     desc: 'Silnik decyzyjny' },
  { id: 'decyzja'   as const, icon: Scale,           name: 'Decyzja',    desc: 'Rekomendacje' },
  { id: 'logistyka' as const, icon: Truck,           name: 'Logistyka',  desc: 'Zasoby' },
  { id: 'rfq'       as const, icon: ShieldCheck,     name: 'RFQ',        desc: 'Zatwierdzenia' },
  { id: 'pipeline'  as const, icon: GitBranch,       name: 'Pipeline',   desc: 'Supervisor' },
  { id: 'pogoda'    as const, icon: CloudSun,        name: 'Pogoda',     desc: 'Prognoza 14 dni' },
  { id: 'system'    as const, icon: Settings,        name: 'System',     desc: 'Backup & Config' },
];

export function Sidebar() {
  const { currentModule, setCurrentModule, isMenuOpen, toggleMenu } = useStore();

  return (
    <div
      className={`relative flex flex-col bg-earth-900/50 border-r border-earth-800/80 backdrop-blur-xl transition-all duration-300 ease-in-out ${
        isMenuOpen ? 'w-60' : 'w-[68px]'
      }`}
    >
      {/* ── Logo / Header ───────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-3 h-16 border-b border-earth-800/60">
        {/* Logo when expanded */}
        {isMenuOpen ? (
          <span className="text-base font-bold text-earth-100 tracking-tight select-none">
            Terra<span className="text-accent-primary">.OS</span>
          </span>
        ) : (
          /* "T" badge when collapsed */
          <div className="w-8 h-8 rounded-full bg-accent-primary/10 border border-accent-primary/30 flex items-center justify-center mx-auto">
            <span className="text-accent-primary text-sm font-bold leading-none select-none">T</span>
          </div>
        )}

        <button
          onClick={toggleMenu}
          aria-label={isMenuOpen ? 'Zwiń menu' : 'Rozwiń menu'}
          className="p-1.5 rounded-md hover:bg-earth-800 text-earth-500 hover:text-earth-200 transition-colors duration-200 ml-auto flex-shrink-0"
        >
          {isMenuOpen ? (
            <ChevronLeft className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* ── Navigation ──────────────────────────────────────────────── */}
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        {modules.map(({ id, icon: Icon, name, desc }) => {
          const isActive = currentModule === id;
          return (
            <div key={id} className="relative group/item">
              <button
                onClick={() => setCurrentModule(id)}
                className={`relative w-full flex items-center gap-3 rounded-lg px-3 py-2.5 transition-all duration-200 ${
                  isActive
                    ? 'bg-accent-primary/10 text-accent-primary border-l-2 border-accent-primary/60'
                    : 'text-earth-400 hover:text-earth-200 hover:bg-earth-800/60 border-l-2 border-transparent'
                }`}
              >
                <Icon
                  className={`w-[18px] h-[18px] flex-shrink-0 transition-colors duration-200 ${
                    isActive
                      ? 'text-accent-primary'
                      : 'text-earth-500 group-hover/item:text-earth-300'
                  }`}
                />
                {isMenuOpen && (
                  <span
                    className={`text-sm font-medium truncate transition-colors duration-200 ${
                      isActive
                        ? 'text-accent-primary'
                        : 'text-earth-300 group-hover/item:text-earth-100'
                    }`}
                  >
                    {name}
                  </span>
                )}
              </button>

              {/* Tooltip — only when collapsed */}
              {!isMenuOpen && (
                <div
                  className="
                    pointer-events-none
                    absolute left-full top-1/2 -translate-y-1/2 ml-3 z-50
                    px-3 py-2
                    bg-earth-800 border border-earth-700/50
                    rounded-lg shadow-xl shadow-black/40
                    whitespace-nowrap
                    opacity-0 scale-95
                    group-hover/item:opacity-100 group-hover/item:scale-100
                    transition-all duration-150 ease-out
                  "
                >
                  <div className="text-sm font-semibold text-earth-100">{name}</div>
                  <div className="text-xs text-earth-400 mt-0.5">{desc}</div>
                  {/* Arrow */}
                  <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-earth-700/50" />
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <div className="p-3 border-t border-earth-800/60 space-y-2">
        {/* User row */}
        {isMenuOpen ? (
          <div className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-earth-800/40 transition-colors cursor-pointer">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent-primary/30 to-accent-primary/10 border border-accent-primary/20 flex items-center justify-center text-xs font-bold text-accent-primary flex-shrink-0">
              MK
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-earth-200 truncate">Maciek K.</div>
              <div className="text-xs text-earth-500">Operator</div>
            </div>
          </div>
        ) : (
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent-primary/30 to-accent-primary/10 border border-accent-primary/20 flex items-center justify-center text-xs font-bold text-accent-primary mx-auto">
            MK
          </div>
        )}

        {/* Version + API status */}
        {isMenuOpen ? (
          <div className="flex items-center justify-between px-2 py-1">
            <span className="text-[10px] text-earth-600 font-mono tracking-wide">v1.0.0</span>
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-accent-primary animate-pulse" />
              <span className="text-[10px] text-earth-600">API</span>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <div className="w-1.5 h-1.5 rounded-full bg-accent-primary animate-pulse" />
          </div>
        )}
      </div>
    </div>
  );
}
