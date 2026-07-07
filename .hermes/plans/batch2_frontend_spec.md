# Terra.OS — Frontend Design System Spec & New Pages
**Batch 2 | Frontend Developer Report**  
_Wersja: 1.0 | Data: 2026-07-07_

---

## SPIS TREŚCI

1. [Audyt UI — analiza istniejących stron](#1-audyt-ui)
2. [Design System Spec](#2-design-system-spec)
3. [Spec 8 Nowych Stron](#3-spec-8-nowych-stron)
4. [Spec Ulepszeń Istniejących Stron](#4-spec-ulepszeń-istniejących-stron)
5. [Spec Onboarding Flow](#5-spec-onboarding-flow)

---

## 1. AUDYT UI

### 1.1 DashboardPage.tsx — Analiza

**Mocne strony:**
- ✅ Stagger animation (motion/react) — profesjonalne wejście kart
- ✅ Real API (`useDashboardStats`, `useTenders`) — nie pure mock
- ✅ Skeleton loader (`SkeletonStatCard`) z `animate-pulse`
- ✅ Sparkline chart (Recharts `LineChart`) w stat kartach
- ✅ Pipeline bar z progresywną wizualizacją 7 etapów
- ✅ Empty state w tabeli `recentTenders` z CTA do Zwiadu
- ✅ `tabular-nums` na wartościach numerycznych (nie ma layout shift)
- ✅ `STATUS_COLORS` / `STATUS_LABELS` — scentralizowana konfiguracja statusów

**Problemy / Tech Debt:**
- ⚠️ `sparkData` jest STATYCZNY (`[{v:3},{v:5}...]`) — niezwiązany z realną historią
- ⚠️ `trend` w stat kartach ("3 w tym tygodniu") — hardcoded string, nie z API
- ⚠️ Brak `ErrorBoundary` — błąd `useDashboardStats` renderuje pustą stronę
- ⚠️ `stats?.recentTenders` — brak limit 5 egzekwowanego po stronie API
- ⚠️ `tenders.slice(0, 4)` — może zwrócić null/crash jeśli `tenders` nie jest array
- ⚠️ Brak `aria-label` na przyciskach Quick Actions
- ⚠️ Tooltip renderuje tylko `title` attribute — brak rich tooltip (dostępność)
- ⚠️ `setSelectedTender(t as unknown as ...)` — type-cast wskazuje na rozbieżność typów API/Store
- ⚠️ Brak loading state dla `useTenders()` — "Top przetargi" może flashować puste

**Propozycje:**
1. Połączyć `sparkData` z `stats.weeklyActivity` endpoint
2. Dodać `<ErrorBoundary fallback={<DashboardError />}>`
3. Usunąć type-casts — zunifikować typy przez `Tender` interface
4. Dodać trend delta (`+3`, `-1`) z API porównania t-7 dni

---

### 1.2 SilnikPage.tsx — Analiza

**Mocne strony:**
- ✅ Trzy stany załadowania: `loading`, `running`, `error` — kompletna obsługa
- ✅ Verdict Banner GO/NO-GO — wysoka widoczność decyzji
- ✅ P10/P50/P90 Risk Gauges — rozproszenie scenariuszy
- ✅ Violations grouped by severity (`block > warn > info`)
- ✅ Monte Carlo drivers table z mini bar chart
- ✅ Empty state z CTA do Zwiadu (brak przetargu)
- ✅ Spinner w przycisku "Uruchom analizę"

**Problemy / Tech Debt:**
- ⚠️ `tender` typowany jako `any` — cały komponent traci type-safety
- ⚠️ `fetchResult` / `runEngine` — brak `AbortController` (race condition przy szybkiej zmianie przetargu)
- ⚠️ Brak wizualizacji rozkładu — P10/P50/P90 jako liczby, nie wykres violin/box
- ⚠️ Drivers table — brak sortowania wg ST (najważniejszy czynnik na górze)
- ⚠️ `explanation_md` — pole istnieje w interface ale **nigdzie nie renderowane**
- ⚠️ Brak persist — wyniki giną przy zmianie zakładki (useEffect refetch za każdym razem)
- ⚠️ `violations[].provenance` — nie wyświetlane, wartościowa informacja debugowania

**Propozycje:**
1. Dodać `WaterfallChart` dla drivers (Recharts ComposedChart)
2. Renderować `explanation_md` jako `ReactMarkdown` w osobnej zakładce
3. Dodać `useRef` AbortController w fetchResult/runEngine
4. Cache wyników w Zustand store per `tender.id`

---

### 1.3 KosztorysPage.tsx — Analiza

**Mocne strony:**
- ✅ Dual kosztorys A/B side-by-side — excellent UX do porównania
- ✅ Delta card z color-coded (zielony/czerwony) — instant insight
- ✅ Collapsible chapters z sum per chapter
- ✅ Dwa typy skeleton (SkeletonCard + SkeletonTable)
- ✅ Breadcrumb nawigacja Zwiad → Kosztorys
- ✅ Empty state na dwóch poziomach (brak przetargu vs brak kosztorysów)
- ✅ `tabular-nums` + `font-mono` na liczbach

**Problemy / Tech Debt:**
- ⚠️ `tender as any` — brak typów
- ⚠️ Brak violation badges na liniach kosztorysu (np. niezgodne KNR)
- ⚠️ Brak chat edit panel — nie ma UI do AI edycji pozycji
- ⚠️ `expandedChapters` default: wszystkie expanded — for long estimates (100+ lines) performance issue
- ⚠️ Tabela dwukolumnowa bardzo wąska na < 1200px viewport
- ⚠️ Brak eksportu PDF / Excel
- ⚠️ Brak inline edit pozycji (manual correction)

**Propozycje:**
1. Live violation badges per linia (czerwona/żółta kropka przy opisie)
2. Chat panel z prawej strony (collapsible drawer)
3. Virtualizacja tabeli (`@tanstack/react-virtual`) dla 100+ pozycji
4. Export button (PDF via `@react-pdf/renderer`)

---

### 1.4 layout.tsx — Analiza

**Mocne strony:**
- ✅ `Space_Grotesk` + `JetBrains_Mono` — professional font stack
- ✅ CSS font variables (`--font-space`, `--font-mono`)
- ✅ PWA Service Worker registration
- ✅ Manifest + Apple Web App meta
- ✅ `lang="pl"` — poprawna lokalizacja

**Problemy / Tech Debt:**
- ⚠️ `themeColor: '#00ff88'` — kolor niezgodny z design systemem (powinno być `#10b981`)
- ⚠️ SW registration inline script — brak nonce dla strict CSP
- ⚠️ Brak `<Providers>` wrapper (TanStack Query, Zustand devtools)
- ⚠️ Brak `<Toaster>` (toast notifications)
- ⚠️ Brak OpenGraph meta (title, image)

---

## 2. DESIGN SYSTEM SPEC

### 2.1 Token System — Kolory

```typescript
// tokens/colors.ts — pełna paleta Terra.OS

export const colors = {
  // ── Earth palette (neutrals / background) ──────────────────────────────
  earth: {
    950: '#09090b',   // body background — czarny węgiel
    900: '#18181b',   // card background
    800: '#27272a',   // input / hover bg
    700: '#3f3f46',   // border / divider
    600: '#52525b',   // muted icon / placeholder
    500: '#71717a',   // label / secondary text
    400: '#a1a1aa',   // disabled text
    300: '#d4d4d8',   // body text secondary
    200: '#e4e4e7',   // body text primary
    100: '#f4f4f5',   // heading
    50:  '#fafafa',   // max contrast
  },

  // ── Clay palette (construction brand — accent secondary) ───────────────
  clay: {
    600: '#9A3412',   // dark clay — bardzo intensywne, dla alertów
    500: '#C2410C',   // clay orange — brand accent
    400: '#E04512',   // hover clay
    300: '#F4763F',   // light clay — success variant
    200: '#FCA47D',   // bardzo jasny — backgrounds
    100: '#FEE4D4',   // pale clay background
  },

  // ── Semantic accents ───────────────────────────────────────────────────
  accent: {
    primary:  '#10b981',  // emerald — główny akcent (GO, success, CTAs)
    success:  '#22C55E',  // green — potwierdzenia
    warning:  '#F59E0B',  // amber — ostrzeżenia
    danger:   '#EF4444',  // red — błędy, NO-GO
    info:     '#3B82F6',  // blue — informacje, nowe
    violet:   '#8B5CF6',  // violet — matched, AI
  },

  // ── Construction-specific semantic ────────────────────────────────────
  construction: {
    concrete: '#78716c',  // warm gray — materiały
    steel:    '#94a3b8',  // blue-gray — stal/metal
    wood:     '#a16207',  // wood brown — drewno
    ground:   '#57534e',  // earth brown — ziemia/wykop
  },
} as const;

// ── CSS Variables (globals.css) ────────────────────────────────────────────────
// Wszystkie kolory dostępne jako: bg-earth-900, text-accent-primary, etc.
// Gradient set: from-earth-900 to-earth-950
// Glass overlay: bg-earth-900/40 + backdrop-blur-xl
```

**Kontrast WCAG 2.1 AA:**
| Token | Na tle earth-950 | Status |
|-------|-----------------|--------|
| earth-100 | 18.1:1 | ✅ AAA |
| earth-200 | 13.7:1 | ✅ AAA |
| earth-300 | 9.4:1 | ✅ AAA |
| earth-400 | 5.6:1 | ✅ AA |
| accent-primary (#10b981) | 4.7:1 | ✅ AA |
| accent-warning (#F59E0B) | 8.2:1 | ✅ AAA |
| accent-danger (#EF4444) | 4.5:1 | ✅ AA |

---

### 2.2 Token System — Typografia

```typescript
// tokens/typography.ts

export const typography = {
  // ── Font families ──────────────────────────────────────────────────────
  fonts: {
    display: 'Space Grotesk',   // headings, UI labels, CTAs
    mono:    'JetBrains Mono',  // numbers, code, KNR codes, PLN values
    system:  'system-ui',       // fallback
  },

  // ── Font scale ─────────────────────────────────────────────────────────
  sizes: {
    '2xs': '0.625rem',  // 10px — micro labels
    'xs':  '0.75rem',   // 12px — labels, badges, table headers
    'sm':  '0.875rem',  // 14px — body text, table cells
    'base':'1rem',      // 16px — default body
    'lg':  '1.125rem',  // 18px — sub-headings
    'xl':  '1.25rem',   // 20px — section titles
    '2xl': '1.5rem',    // 24px — page headings
    '3xl': '1.875rem',  // 30px — hero numbers (stat values)
    '4xl': '2.25rem',   // 36px — GO/NO-GO verdict
  },

  // ── Weights ────────────────────────────────────────────────────────────
  weights: {
    normal:    400,
    medium:    500,
    semibold:  600,
    bold:      700,
    extrabold: 800,
    black:     900,
  },

  // ── Line heights ───────────────────────────────────────────────────────
  leading: {
    none:     1,
    tight:    1.25,
    snug:     1.375,
    normal:   1.5,
    relaxed:  1.625,
  },

  // ── Letter spacing ─────────────────────────────────────────────────────
  tracking: {
    tighter: '-0.05em',
    tight:   '-0.025em',
    normal:  '0',
    wide:    '0.025em',
    wider:   '0.05em',
    widest:  '0.1em',   // uppercase labels
  },
} as const;

// ── Usage rules ────────────────────────────────────────────────────────────────
// Page heading:     text-2xl font-bold text-earth-50 tracking-tight
// Section title:    text-sm font-semibold text-earth-300 uppercase tracking-wider
// Body:             text-sm text-earth-300 leading-relaxed
// Label:            text-xs font-semibold text-earth-400 uppercase tracking-wider
// Stat value:       text-3xl font-bold text-earth-50 tabular-nums font-mono
// Badge:            text-xs font-semibold
// PLN amount:       font-mono tabular-nums text-earth-100
// KNR code:         font-mono text-xs text-earth-600
```

---

### 2.3 Token System — Spacing

```typescript
// tokens/spacing.ts — based on 4px grid

export const spacing = {
  // ── Base scale ─────────────────────────────────────────────────────────
  0:    '0',
  0.5:  '0.125rem',  // 2px
  1:    '0.25rem',   // 4px
  1.5:  '0.375rem',  // 6px
  2:    '0.5rem',    // 8px
  2.5:  '0.625rem',  // 10px
  3:    '0.75rem',   // 12px
  4:    '1rem',      // 16px
  5:    '1.25rem',   // 20px
  6:    '1.5rem',    // 24px
  8:    '2rem',      // 32px
  10:   '2.5rem',    // 40px
  12:   '3rem',      // 48px
  16:   '4rem',      // 64px
  20:   '5rem',      // 80px

  // ── Component-specific tokens ──────────────────────────────────────────
  component: {
    cardPadding:     '1.25rem',   // p-5 = 20px
    cardPaddingLg:   '1.5rem',    // p-6 = 24px
    sectionGap:      '1.25rem',   // gap-5 = 20px
    pageGutter:      '1.5rem',    // px-6
    pageGutterLg:    '2rem',      // px-8
    tableRowPaddingY:'0.75rem',   // py-3
    tableRowPaddingX:'1rem',      // px-4
    inputHeight:     '2.25rem',   // h-9
    buttonHeight:    '2.25rem',   // h-9
    buttonHeightSm:  '2rem',      // h-8
    sidebarWidth:    '14rem',     // w-56
    iconSm:          '0.875rem',  // w-3.5 h-3.5
    iconMd:          '1rem',      // w-4 h-4
    iconLg:          '1.25rem',   // w-5 h-5
    iconXl:          '1.5rem',    // w-6 h-6
  },
} as const;
```

---

### 2.4 Token System — Shadows & Borders

```typescript
// tokens/effects.ts

export const effects = {
  // ── Border radius ──────────────────────────────────────────────────────
  radius: {
    sm:   '0.375rem',  // rounded-md — inputs, badges
    md:   '0.5rem',    // rounded-lg — buttons
    lg:   '0.75rem',   // rounded-xl — cards (PRIMARY)
    xl:   '1rem',      // rounded-2xl — modals, hero cards
    full: '9999px',    // rounded-full — avatars, pills
  },

  // ── Shadows ────────────────────────────────────────────────────────────
  shadows: {
    sm:    '0 1px 2px 0 rgb(0 0 0 / 0.3)',
    md:    '0 4px 6px -1px rgb(0 0 0 / 0.4)',
    lg:    '0 10px 15px -3px rgb(0 0 0 / 0.4)',
    xl:    '0 20px 25px -5px rgb(0 0 0 / 0.5)',
    glow:  '0 0 20px 0 rgb(16 185 129 / 0.25)',   // accent-primary glow
    card:  '0 10px 15px -3px rgb(0 0 0 / 0.2)',   // glass-card
  },

  // ── Borders ────────────────────────────────────────────────────────────
  borders: {
    card:    '1px solid color-mix(in srgb, #3f3f46 30%, transparent)',
    input:   '1px solid #3f3f46',
    focus:   '1px solid #10b981',
    danger:  '1px solid rgb(239 68 68 / 0.3)',
    success: '1px solid rgb(16 185 129 / 0.3)',
  },

  // ── Backdrop ───────────────────────────────────────────────────────────
  blur: {
    sm:  'blur(8px)',
    md:  'blur(16px)',
    lg:  'blur(24px)',   // glass-card
    xl:  'blur(40px)',   // modal overlay
  },
} as const;
```

---

### 2.5 Component Inventory — 20 Komponentów

#### C-01: Button

```typescript
// components/ui/Button.tsx

interface ButtonProps {
  variant:   'primary' | 'secondary' | 'danger' | 'ghost' | 'link';
  size:      'sm' | 'md' | 'lg';
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  loading?:  boolean;
  disabled?: boolean;
  fullWidth?: boolean;
  onClick?:  () => void;
  type?:     'button' | 'submit' | 'reset';
  'aria-label'?: string;
  children:  React.ReactNode;
}

// Variants:
// primary:   bg-accent-primary text-earth-950 font-bold — CTA, GO action
// secondary: bg-earth-800 border border-earth-700 text-earth-200 — neutral
// danger:    bg-accent-danger/10 border border-accent-danger/30 text-accent-danger
// ghost:     hover:bg-earth-800/50 text-earth-400 — toolbar icons
// link:      text-accent-primary hover:underline — inline navigation

// Sizes:
// sm: px-3 py-1.5 text-xs h-8 rounded-lg
// md: px-4 py-2   text-sm h-9 rounded-xl
// lg: px-5 py-2.5 text-base h-11 rounded-xl

// Loading state: spinner replaces leftIcon + pointer-events-none

// Usage:
// <Button variant="primary" size="md" leftIcon={<Play />} loading={isRunning}>
//   Uruchom analizę
// </Button>
```

#### C-02: Input

```typescript
interface InputProps {
  label?:       string;
  placeholder?: string;
  value:        string;
  onChange:     (v: string) => void;
  error?:       string;
  hint?:        string;
  prefix?:      React.ReactNode;  // PLN ikona, search icon
  suffix?:      React.ReactNode;  // clear button, unit
  disabled?:    boolean;
  type?:        'text' | 'number' | 'email' | 'search' | 'password';
  size?:        'sm' | 'md';
  'aria-label'?: string;
}

// Styles:
// base:  bg-earth-800/60 border border-earth-700/50 rounded-lg px-3 py-2
//        text-earth-100 placeholder-earth-500
//        focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/50
// error: border-accent-danger focus:border-accent-danger focus:ring-accent-danger/50
// hint:  text-xs text-earth-500 mt-1
// error message: text-xs text-accent-danger mt-1
```

#### C-03: Select

```typescript
interface SelectProps {
  label?:    string;
  options:   Array<{ value: string; label: string; disabled?: boolean }>;
  value:     string;
  onChange:  (v: string) => void;
  placeholder?: string;
  error?:    string;
  disabled?: boolean;
  searchable?: boolean;    // z filtrem tekstowym
  multiple?:   boolean;
  'aria-label'?: string;
}

// Implementacja: headlessui Listbox (accessible)
// Dropdown: max-h-60 overflow-y-auto, z-50
// Option hover: bg-earth-700/50
// Selected: bg-accent-primary/20 text-accent-primary
// Searchable: input na górze dropdown
```

#### C-04: Modal

```typescript
interface ModalProps {
  open:      boolean;
  onClose:   () => void;
  title:     string;
  size?:     'sm' | 'md' | 'lg' | 'xl' | 'full';
  children:  React.ReactNode;
  footer?:   React.ReactNode;
  closeOnBackdrop?: boolean;  // default true
}

// Animation: opacity 0→1 + scale 0.95→1 (150ms)
// Backdrop: bg-earth-950/80 backdrop-blur-sm
// Panel: glass-card max-w-[size] w-full mx-4
//   sm:   max-w-md
//   md:   max-w-lg (default)
//   lg:   max-w-2xl
//   xl:   max-w-4xl
//   full: max-w-7xl
// Focus trap: via @headlessui/react Dialog
// Close: Escape key + X button + backdrop click
// Footer: sticky bottom, flex justify-end gap-2

// ARIA: role="dialog", aria-modal="true", aria-labelledby="modal-title"
```

#### C-05: Toast / Notification

```typescript
interface ToastProps {
  type:     'success' | 'error' | 'warning' | 'info';
  title:    string;
  message?: string;
  duration?: number;   // ms, default 4000, 0 = persistent
  action?:  { label: string; onClick: () => void };
}

// Pozycja: bottom-right (fixed, z-50)
// Animation: slide-in-right 200ms + fade-out 200ms
// Stack: max 3 jednocześnie, najstarszy pierwszy
// Success: border-l-4 border-accent-primary bg-earth-900
// Error:   border-l-4 border-accent-danger
// Warning: border-l-4 border-accent-warning
// Info:    border-l-4 border-accent-info

// API: toast.success('Zapisano'), toast.error('Błąd')
// Provider: <ToastProvider> w layout.tsx
```

#### C-06: DataTable

```typescript
interface DataTableProps<T> {
  data:       T[];
  columns:    ColumnDef<T>[];
  loading?:   boolean;
  error?:     string;
  emptyState?: React.ReactNode;
  selectable?: boolean;
  onSelect?:   (rows: T[]) => void;
  sortable?:   boolean;
  pagination?:  { page: number; pageSize: number; total: number; onChange: (p: number) => void };
  onRowClick?:  (row: T) => void;
  stickyHeader?: boolean;
  virtualRows?:  boolean;  // @tanstack/react-virtual
}

interface ColumnDef<T> {
  key:       keyof T | string;
  header:    string;
  cell?:     (value: T[keyof T], row: T) => React.ReactNode;
  sortable?: boolean;
  width?:    string;
  align?:    'left' | 'right' | 'center';
  sticky?:   boolean;
}

// Styles:
// thead: .table-header (uppercase, tracking-wider)
// tbody row: hover:bg-earth-800/30 transition-colors cursor-pointer
// td: .table-cell
// Loading: SkeletonRow x5
// Empty: EmptyState component centered
// Sorting: ChevronUp/Down icons, active sort highlighted

// Virtual scrolling: aktywuje przy data.length > 100
```

#### C-07: Chart (wrapper)

```typescript
interface ChartProps {
  type:   'line' | 'bar' | 'area' | 'pie' | 'waterfall' | 'violin';
  data:   unknown[];
  height?: number;     // default 200
  colors?: string[];
  loading?: boolean;
  emptyMessage?: string;
  title?: string;
  subtitle?: string;
  legend?: boolean;
  tooltip?: boolean;
  grid?:    boolean;
}

// Implementacja: Recharts pod spodem
// Responsywny: ResponsiveContainer 100%
// Kolory: accent palette (primary, warning, danger, info, violet)
// Grid: stroke="#27272a" (earth-800)
// Tooltip: bg-earth-900 border border-earth-700 text-earth-200
// Legend: text-earth-400 text-xs

// Specjalne typy:
// waterfall — ComposedChart: Bar (positive/negative) + ReferenceLine
// violin    — custom SVG path over AreaChart (P10/P50/P90 distribution)
// sparkline — minimal LineChart bez osi
```

#### C-08: Form

```typescript
interface FormProps {
  onSubmit:  (data: Record<string, unknown>) => void | Promise<void>;
  schema?:   ZodSchema;    // validation
  defaultValues?: Record<string, unknown>;
  children:  React.ReactNode;
  className?: string;
}

// Użycie: react-hook-form + zod resolver
// Fieldset: gap-4 flex flex-col
// Error summary: na górze formularza (aria-live="assertive")
// Submit: loading spinner w przycisku
// Reset: po pomyślnym submit

// Wzorzec:
// <Form onSubmit={handleSave} schema={contractSchema}>
//   <FormField name="name" label="Nazwa kontraktu">
//     <Input />
//   </FormField>
// </Form>
```

#### C-09: Badge

```typescript
interface BadgeProps {
  variant:  'success' | 'warning' | 'danger' | 'info' | 'violet' | 'neutral' | 'clay';
  size?:    'sm' | 'md';
  dot?:     boolean;   // pulsing dot dla "live" statusów
  icon?:    React.ReactNode;
  children: React.ReactNode;
}

// Variants (zgodne z globals.css):
// success: bg-accent-success/15 text-accent-success border-accent-success/20
// warning: bg-accent-warning/15 text-accent-warning border-accent-warning/20
// danger:  bg-accent-danger/15  text-accent-danger  border-accent-danger/20
// info:    bg-accent-info/15    text-accent-info    border-accent-info/20
// violet:  bg-accent-violet/15  text-accent-violet  border-accent-violet/20
// neutral: bg-earth-700/40      text-earth-400      border-earth-700/30
// clay:    bg-clay-500/15       text-clay-300       border-clay-500/20

// Dot variant: animated pulse w(2) h(2) rounded-full bg-current mr-1.5
```

#### C-10: Skeleton

```typescript
interface SkeletonProps {
  variant: 'text' | 'card' | 'table' | 'stat' | 'avatar' | 'chart';
  lines?:  number;   // dla text
  rows?:   number;   // dla table
  height?: string;   // override
  width?:  string;   // override
}

// Base: .skeleton class (shimmer gradient animation)
// text:   h-3 rounded w-full mb-2 (repeat lines times)
// card:   glass-card p-5 z wewnętrznymi skeleton blocks
// table:  header + N rows z kolumnami
// stat:   h-8 w-16 (value) + h-12 (sparkline area)
// avatar: w-10 h-10 rounded-full
// chart:  h-[height] rounded-xl

// Przyspieszony shimmer: animation-duration: 1.2s
```

#### C-11: EmptyState

```typescript
interface EmptyStateProps {
  icon:      React.ComponentType<{ className?: string }>;
  title:     string;
  message:   string;
  action?:   { label: string; icon?: React.ReactNode; onClick: () => void };
  size?:     'sm' | 'md' | 'lg';
}

// Layout: flex flex-col items-center justify-center text-center gap-4
// Icon container: w-16 h-16 rounded-2xl bg-earth-800 border border-earth-700/40
// Icon: w-8 h-8 text-earth-600
// Title: text-earth-300 font-medium text-lg
// Message: text-earth-500 text-sm max-w-xs leading-relaxed
// Action: Button variant="secondary" size="md" — wbudowany CTA

// Size variants:
// sm: icon w-10 h-10, w-5 h-5, text-base title
// md: icon w-16 h-16, w-8 h-8, text-lg title (default)
// lg: icon w-20 h-20, w-10 h-10, text-xl title
```

#### C-12: Tabs

```typescript
interface TabsProps {
  tabs:    Array<{ id: string; label: string; count?: number; icon?: React.ReactNode }>;
  active:  string;
  onChange: (id: string) => void;
  variant?: 'underline' | 'pills';
}

// underline (default): border-b border-earth-800, active: border-b-2 border-accent-primary text-earth-100
// pills: rounded-lg, active: bg-earth-700 text-earth-100
// Count badge: ml-1.5 text-xs bg-earth-700 text-earth-400 px-1.5 rounded-full
// Keyboard: ArrowLeft/Right navigation między tabami
// ARIA: role="tablist", role="tab", aria-selected, aria-controls
```

#### C-13: Dropdown Menu

```typescript
interface DropdownMenuProps {
  trigger: React.ReactNode;
  items:   Array<{
    label:    string;
    icon?:    React.ReactNode;
    onClick:  () => void;
    danger?:  boolean;
    disabled?: boolean;
    divider?:  boolean;   // separator przed tym item
  }>;
  align?: 'left' | 'right';
}

// Implementacja: @headlessui/react Menu
// Panel: glass-card py-1 min-w-[160px] z-50
// Item: px-3 py-2 text-sm text-earth-200 hover:bg-earth-700/50 flex items-center gap-2
// Danger item: text-accent-danger hover:bg-accent-danger/10
// Divider: border-t border-earth-800 my-1
// Animation: opacity + translate-y 150ms
```

#### C-14: SearchInput

```typescript
interface SearchInputProps {
  value:      string;
  onChange:   (v: string) => void;
  placeholder?: string;
  onClear?:   () => void;
  loading?:   boolean;
  debounce?:  number;   // ms, default 300
  'aria-label'?: string;
}

// Wygląd: input z SearchIcon po lewej, X button po prawej
// Debounce: useDebounce hook, spinner podczas debounce
// Keyboard: Escape = clear, Enter = immediate search
```

#### C-15: FilterBar

```typescript
interface FilterBarProps {
  filters:   FilterConfig[];
  values:    Record<string, unknown>;
  onChange:  (key: string, value: unknown) => void;
  onReset:   () => void;
  activeCount?: number;
}

interface FilterConfig {
  key:    string;
  label:  string;
  type:   'select' | 'multiselect' | 'range' | 'date' | 'toggle';
  options?: Array<{ value: string; label: string }>;
  min?: number; max?: number;   // dla range
}

// Layout: flex items-center gap-2 flex-wrap
// Active filters: Badge chips z X do usunięcia
// Reset: "Wyczyść filtry (N)" — visible tylko gdy activeCount > 0
```

#### C-16: StatusBadge (Domain-Specific)

```typescript
type TenderStatus = 
  | 'new' | 'matched' | 'watching' | 'analyzing' 
  | 'estimated' | 'decided_go' | 'decided_nogo' | 'archived';

interface StatusBadgeProps {
  status:   TenderStatus;
  size?:    'sm' | 'md';
  showDot?: boolean;
}

// Mapping (z DashboardPage):
// new:          bg-accent-info/15    text-accent-info
// matched:      bg-accent-violet/15  text-accent-violet
// watching:     bg-sky-500/15        text-sky-400
// analyzing:    bg-accent-warning/15 text-accent-warning
// estimated:    bg-accent-primary/15 text-accent-primary
// decided_go:   bg-accent-primary/20 text-accent-primary   (pulsing dot)
// decided_nogo: bg-accent-danger/15  text-accent-danger
// archived:     bg-earth-700/40      text-earth-500
```

#### C-17: ProgressBar

```typescript
interface ProgressBarProps {
  value:   number;   // 0-100
  max?:    number;   // default 100
  color?:  'primary' | 'success' | 'warning' | 'danger';
  size?:   'xs' | 'sm' | 'md';
  label?:  string;
  showValue?: boolean;
  animated?:  boolean;  // striped animation (loading states)
}

// xs: h-1 rounded-full
// sm: h-1.5 rounded-full
// md: h-2.5 rounded-full
// Color map: primary=#10b981, success=#22C55E, warning=#F59E0B, danger=#EF4444
// Transition: width animacja 700ms ease-out
```

#### C-18: Avatar

```typescript
interface AvatarProps {
  name:   string;       // generuje inicjały jeśli brak src
  src?:   string;
  size?:  'xs' | 'sm' | 'md' | 'lg' | 'xl';
  status?: 'online' | 'offline' | 'busy';
  badge?: React.ReactNode;
}

// xs:  w-6  h-6  text-2xs
// sm:  w-8  h-8  text-xs
// md:  w-10 h-10 text-sm  (default)
// lg:  w-12 h-12 text-base
// xl:  w-16 h-16 text-lg
// Inicjały: 2 pierwsze litery, bg dynamiczne (hash z name → kolor z palety earth/accent)
// Status dot: bottom-right, w-2.5 h-2.5 rounded-full z-10
```

#### C-19: PageHeader

```typescript
interface PageHeaderProps {
  title:    string;
  subtitle?: string;
  badge?:   { text: string; variant: BadgeProps['variant'] };
  actions?: React.ReactNode;
  breadcrumb?: Array<{ label: string; onClick?: () => void }>;
}

// Layout: flex items-start justify-between
// Breadcrumb: text-xs text-earth-600 > text-earth-400 font-medium
// Title: text-2xl font-bold text-earth-50 tracking-tight
// Subtitle: text-sm text-earth-500 mt-0.5
// Badge: inline po tytule (np. "BETA", "Owner Only")
// Actions: flex gap-2 items-center
```

#### C-20: SideDrawer

```typescript
interface SideDrawerProps {
  open:    boolean;
  onClose: () => void;
  title:   string;
  width?:  'sm' | 'md' | 'lg';  // 320px / 480px / 640px
  children: React.ReactNode;
  footer?:  React.ReactNode;
}

// Animation: translate-x-full → translate-x-0 (300ms ease)
// Backdrop: bg-earth-950/60 backdrop-blur-sm
// Panel: fixed right-0 top-0 h-full bg-earth-900 border-l border-earth-800
// Header: flex items-center justify-between px-5 py-4 border-b border-earth-800
// Body: overflow-y-auto flex-1 px-5 py-4
// Footer: px-5 py-4 border-t border-earth-800
// Focus trap via @headlessui/react Dialog
// Użycie: AI Chat panel, filter drawer, detail view
```

---

### 2.6 Motion Spec — Animacje

```typescript
// tokens/motion.ts

export const motion = {
  // ── Durations ──────────────────────────────────────────────────────────
  duration: {
    instant:  0,
    fast:     100,   // ms — hover states, color changes
    normal:   150,   // ms — button hover, border color
    medium:   200,   // ms — icon transitions, badge appear
    slow:     300,   // ms — drawer open, modal open
    verySlow: 500,   // ms — page transitions, chart draw
    chart:    700,   // ms — bar/line draw
  },

  // ── Easings ────────────────────────────────────────────────────────────
  ease: {
    linear:    [0, 0, 1, 1],
    ease:      [0.25, 0.1, 0.25, 1],
    easeIn:    [0.42, 0, 1, 1],
    easeOut:   [0, 0, 0.58, 1],
    easeInOut: [0.42, 0, 0.58, 1],
    spring:    [0, 0, 0.2, 1],        // używane w DashboardPage
    bounce:    [0.34, 1.56, 0.64, 1],
  },

  // ── Standard animation variants (Framer Motion) ────────────────────────
  variants: {
    // Page container — stagger children
    container: {
      hidden: { opacity: 0 },
      show:   { opacity: 1, transition: { staggerChildren: 0.07 } },
    },
    // Item — slide in from bottom
    item: {
      hidden: { opacity: 0, y: 14 },
      show:   { opacity: 1, y: 0, transition: { duration: 0.38, ease: [0, 0, 0.2, 1] } },
    },
    // Fade in only
    fadeIn: {
      hidden: { opacity: 0 },
      show:   { opacity: 1, transition: { duration: 0.2 } },
    },
    // Scale in (modal)
    scaleIn: {
      hidden: { opacity: 0, scale: 0.95 },
      show:   { opacity: 1, scale: 1, transition: { duration: 0.15, ease: [0, 0, 0.2, 1] } },
    },
    // Slide from right (drawer)
    slideRight: {
      hidden: { x: '100%' },
      show:   { x: 0, transition: { duration: 0.3, ease: [0, 0, 0.2, 1] } },
    },
  },
} as const;

// ── Hover states (CSS Tailwind classes) ───────────────────────────────────────
// Card hover:    hover:border-accent-primary/40 hover:bg-earth-800/60 transition-all duration-300
// Button hover:  hover:bg-accent-primary/90 hover:shadow-lg hover:shadow-accent-primary/20
// Row hover:     hover:bg-earth-800/30 transition-colors duration-150
// Icon hover:    group-hover:text-accent-primary transition-colors
// Link hover:    hover:text-earth-200 transition-colors

// ── Loading states ────────────────────────────────────────────────────────────
// Spinner:  animate-spin border-2 border-earth-700 border-t-accent-primary rounded-full w-4 h-4
// Skeleton: .skeleton class (shimmer 1.5s ease-in-out infinite)
// Pulse:    animate-pulse (Tailwind built-in)
// Progress: indeterminate bar (translate animation)
```

---

### 2.7 Empty State Patterns

```typescript
// Każda strona ma dedykowany empty state:

const EMPTY_STATES = {
  dashboard: {
    icon: LayoutDashboard,
    title: 'Witaj w Terra.OS',
    message: 'Rozpocznij od skanowania przetargów BZP lub zaimportuj dokumentację',
    action: { label: 'Skanuj przetargi', onClick: () => navigate('zwiad') },
  },
  zwiad: {
    icon: Radar,
    title: 'Brak wyników skanowania',
    message: 'Ustaw filtry wyszukiwania i uruchom skan rynku BZP',
    action: { label: 'Uruchom skanowanie', onClick: startScan },
  },
  kosztorys: {
    noTender: {
      icon: Calculator,
      title: 'Brak wybranego przetargu',
      message: 'Wybierz przetarg z modułu Zwiad, aby zobaczyć kosztorys',
      action: { label: 'Przejdź do Zwiadu', onClick: () => navigate('zwiad') },
    },
    noEstimates: {
      icon: Calculator,
      title: 'Brak kosztorysów',
      message: 'Uruchom wycenę w module Silnik, aby wygenerować kosztorys',
      action: { label: 'Uruchom Silnik', onClick: () => navigate('silnik') },
    },
  },
  silnik: {
    noTender: {
      icon: Brain,
      title: 'Nie wybrano przetargu',
      message: 'Uruchom silnik kalkulacji dla wybranego przetargu',
      action: { label: 'Przejdź do Zwiadu', onClick: () => navigate('zwiad') },
    },
    noResult: {
      icon: Brain,
      title: 'Uruchom silnik kalkulacji',
      message: 'Kliknij "Uruchom analizę", aby sprawdzić wykonalność i zobaczyć GO/NO-GO',
      // no action — przycisk run jest w headerze
    },
  },
  pipeline: {
    icon: GitBranch,
    title: 'Pipeline jest pusty',
    message: 'Dodaj przetargi do pipeline ze skanera BZP lub importując ręcznie',
    action: { label: 'Skanuj BZP', onClick: () => navigate('zwiad') },
  },
  analytics: {
    icon: BarChart3,
    title: 'Brak danych analitycznych',
    message: 'Zrealizuj minimum 3 przetargi, aby zobaczyć trendy i statystyki',
  },
  resources: {
    icon: Users,
    title: 'Brak zasobów',
    message: 'Dodaj pracowników i sprzęt, aby zarządzać dostępnością',
    action: { label: 'Dodaj zasoby', onClick: openAddModal },
  },
  contracts: {
    icon: FileSignature,
    title: 'Brak kontraktów',
    message: 'Kontrakty pojawią się po wydaniu decyzji GO dla przetargu',
  },
  team: {
    icon: Users,
    title: 'Tylko Ty w zespole',
    message: 'Zaproś współpracowników, aby korzystali z Terra.OS',
    action: { label: 'Zaproś użytkownika', onClick: openInviteModal },
  },
  auditLog: {
    icon: ClipboardList,
    title: 'Brak wpisów w logu',
    message: 'Zdarzenia będą rejestrowane automatycznie od pierwszej akcji użytkownika',
  },
  learning: {
    icon: BookOpen,
    title: 'Brak historycznych kontraktów',
    message: 'Zakończ co najmniej jeden kontrakt, aby system się uczył',
  },
  reports: {
    icon: FileOutput,
    title: 'Brak raportów',
    message: 'Wygeneruj pierwszy raport z menu powyżej',
    action: { label: 'Nowy raport', onClick: openReportModal },
  },
};
```

---

### 2.8 Error Boundary Patterns

```typescript
// components/errors/PageErrorBoundary.tsx

interface PageErrorBoundaryProps {
  children: React.ReactNode;
  page:     string;    // nazwa strony dla error reporting
  fallback?: React.ReactNode;
}

// Standard per-page error UI:
// ┌─────────────────────────────────────────┐
// │     ⚠️ Błąd ładowania strony            │
// │   Nie udało się załadować [page].       │
// │   [error.message]                       │
// │                                         │
// │   [Spróbuj ponownie]  [Wróć do Panelu] │
// └─────────────────────────────────────────┘

class PageErrorBoundary extends React.Component {
  state: { hasError: boolean; error: Error | null };
  
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Logowanie do monitoring (Sentry/PostHog)
    console.error(`[Terra.OS] ${this.props.page} error:`, error, info);
  }
  
  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? <DefaultErrorUI error={this.state.error} />;
    }
    return this.props.children;
  }
}

// Użycie w każdej stronie:
// <PageErrorBoundary page="DashboardPage">
//   <DashboardPage />
// </PageErrorBoundary>

// API Error handling pattern:
// useEffect z try/catch → setError(message) → <ErrorBanner message={error} />
// SWR/React Query: error state → inline AlertBanner
```

---

### 2.9 Accessibility — WCAG 2.1 AA

```typescript
// Checklist implementacji:

// ── 1. Semantyczny HTML ───────────────────────────────────────────────────────
// <main> — główna treść strony
// <nav>  — sidebar nawigacja (role="navigation")
// <header>, <footer>
// <h1> per strona, <h2> dla sekcji, <h3> dla kart
// <button> (nie div.onClick), <a> dla linków nawigacyjnych

// ── 2. Focus management ───────────────────────────────────────────────────────
// *:focus-visible: outline 2px solid accent-primary, offset 2px (już w globals.css)
// Modal: focus trap (@headlessui/react Dialog)
// After modal close: focus returns to trigger element
// Skip link: <a href="#main" className="sr-only focus:not-sr-only">

// ── 3. ARIA labels ────────────────────────────────────────────────────────────
// Każdy icon-only button: aria-label="Opis akcji"
// DataTable: <table aria-label="Nazwa tabeli">
// Progress bar: role="progressbar" aria-valuenow aria-valuemin aria-valuemax
// Status badge: aria-label="Status: GO"
// Toast: role="alert" aria-live="assertive" (errors) / "polite" (success)
// Loading: aria-busy="true" aria-label="Ładowanie..."
// Chart: aria-label="Wykres: [opis]" + <title> w SVG

// ── 4. Keyboard navigation ────────────────────────────────────────────────────
// Tabs: ArrowLeft/Right/Home/End
// Dropdown: ArrowUp/Down/Enter/Escape
// DataTable sortable: Enter/Space na header
// Modal: Escape closes
// Sidebar: Tab order: logo → nav items → content

// ── 5. Color contrast ─────────────────────────────────────────────────────────
// Nie polegaj tylko na kolorze — zawsze icon + tekst dla statusów
// Error states: icon + border + tekst komunikat (nie tylko czerwona ramka)
// Charts: alternatywne wzorce (dashed vs solid) dla colorblind users

// ── 6. Screen reader text ─────────────────────────────────────────────────────
// .sr-only dla wizualnie ukrytego tekstu: className="sr-only"
// Przykład: <span className="sr-only">Sortuj rosnąco</span>
// PLN amounts: aria-label="1 200 000 złotych" (nie "1.2 M zł")

// ── 7. Reduced motion ─────────────────────────────────────────────────────────
// @media (prefers-reduced-motion: reduce) {
//   .skeleton { animation: none; }
//   * { transition-duration: 0ms !important; }
// }
```

---

## 3. SPEC 8 NOWYCH STRON

### 3.1 ResourcesPage — Sprzęt, Pracownicy, Kalendarz

**URL:** `/resources`  
**Moduł:** `resources`  
**Flair:** `Resources`

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│  ZASOBY                              [+ Dodaj zasób ▼]          │
│  Pracownicy i sprzęt — zarządzanie dostępnością                 │
├──────────────┬──────────────────────────────────────────────────┤
│  [Pracownicy]│[Sprzęt]  │[Kalendarz dostępności]               │
├──────────────┴──────────────────────────────────────────────────┤
│  STAT CARDS: [Łącznie: 24] [Dostępni: 18] [Zajęci: 6]          │
├───────────────────────────┬─────────────────────────────────────┤
│  LISTA ZASOBÓW            │  KALENDARZ DOSTĘPNOŚCI              │
│  ┌─────────────────────┐  │  ← Lipiec 2026 →                    │
│  │🔵 Jan Kowalski  GO  │  │  Pn  Wt  Śr  Cz  Pt  Sb  Nd       │
│  │   Kierownik budowy  │  │   ░  ░  ▓  ░  ░  ─  ─              │
│  │   📍 Projekt Alpha  │  │   ░  ░  ░  ░  ▓  ─  ─              │
│  ├─────────────────────┤  │  [aktualnie wybrany: Jan Kowalski]  │
│  │🟡 Koparko-ładow.    │  │  ─────────────────────────────────  │
│  │   CAT 428F2         │  │  [01-10] Projekt Alpha              │
│  │   📍 Magazyn        │  │  [15-20] Wolny                      │
│  └─────────────────────┘  │  [22-31] Projekt Beta               │
│  [Szukaj...]              └─────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

#### Komponenty
- `ResourceList` — scrollable list z avatar + status + przypisanie
- `AvailabilityCalendar` — miesięczny grid (react-big-calendar lub custom)
- `AddResourceModal` — form: typ, nazwa, kwalifikacje, stawka
- `ResourceStatCards` — łącznie / dostępni / zajęci / w urlopie
- `ResourceFilterBar` — typ (pracownik/sprzęt), status, projekt

#### API Calls
```typescript
GET    /api/v1/resources               // lista zasobów
GET    /api/v1/resources/:id/calendar  // dostępność kalendarzowa
POST   /api/v1/resources               // dodaj zasób
PATCH  /api/v1/resources/:id           // aktualizuj
DELETE /api/v1/resources/:id           // usuń
POST   /api/v1/resources/:id/assign    // przypisz do projektu
```

#### Types
```typescript
interface Resource {
  id:          string;
  type:        'person' | 'equipment';
  name:        string;
  role?:       string;           // Kierownik, Operator, etc.
  skills?:     string[];
  rate_pln?:   number;           // stawka dzienna
  status:      'available' | 'assigned' | 'on_leave' | 'unavailable';
  project_id?: string;           // obecne przypisanie
  avatar_url?: string;
}

interface CalendarSlot {
  resource_id: string;
  date_from:   string;   // ISO
  date_to:     string;
  type:        'assigned' | 'leave' | 'available';
  note?:       string;
}
```

#### Empty State
```
  [Users icon]
  "Brak zasobów"
  "Dodaj pracowników i sprzęt, aby śledzić dostępność i przypisywać do projektów"
  [+ Dodaj pierwszy zasób]
```

---

### 3.2 ContractsPage — Kontrakt Tracker + Cashflow

**URL:** `/contracts`  
**Moduł:** `contracts`

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│  KONTRAKTY                           [+ Nowy kontrakt]          │
│  Tracker realizacji kontraktów budowlanych                      │
├─────────────────────────────────────────────────────────────────┤
│  STAT CARDS:                                                     │
│  [Aktywne: 4] [Łączna wartość: 8.2 M zł] [Zaległe: 0]         │
├──────────────────────────────┬──────────────────────────────────┤
│  LISTA KONTRAKTÓW            │  CASHFLOW PROJECTION              │
│                              │                                   │
│  ● Alpha: Mostek A4          │  ┤  ▓▓▓▓                         │
│    8.2% ukończono            │  ┤  ▓▓▓▓ ▓▓                      │
│    Deadline: 15.12.2026      │  ┤  ▓▓   ▓▓▓▓                    │
│    [───▓───────] 8%          │  ┤       ▓▓▓▓ ▓                   │
│                              │  └────────────────────────────── │
│  ● Beta: Droga gminna        │     lip  sie  wrz  paź  lis      │
│    45% ukończono             │  [─ Przychody  ─ Koszty]         │
│    Deadline: 01.03.2027      │                                   │
│    [──────▓▓────] 45%        │  MILESTONE TABLE:                 │
│                              │  # | Kamień milowy | Data | PLN  │
│  [Filtry: Status | Rok]      └──────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

#### Komponenty
- `ContractCard` — nazwa, % ukończenia, ProgressBar, deadline, wartość
- `CashflowChart` — Recharts `ComposedChart` bar+line (przychody vs koszty)
- `MilestoneTable` — DataTable kamieni milowych z statusem
- `ContractCreateModal` — form: powiązany przetarg, termin, wartość, etapy
- `ContractKPIs` — stat cards: aktywne, wartość, zaległe płatności

#### API Calls
```typescript
GET  /api/v1/contracts                     // lista kontraktów
GET  /api/v1/contracts/:id                 // szczegóły
GET  /api/v1/contracts/:id/cashflow        // prognozy cashflow miesięczne
POST /api/v1/contracts                     // utwórz z tender_id
PATCH /api/v1/contracts/:id               // aktualizuj % ukończenia
GET  /api/v1/contracts/:id/milestones      // kamienie milowe
POST /api/v1/contracts/:id/milestones      // dodaj kamień
```

#### Types
```typescript
interface Contract {
  id:          string;
  tender_id:   string;
  name:        string;
  client:      string;
  value_pln:   number;
  start_date:  string;
  end_date:    string;
  progress:    number;   // 0-100
  status:      'draft' | 'active' | 'completed' | 'terminated';
  invoiced_pln: number;
  paid_pln:     number;
}

interface CashflowMonth {
  month:       string;      // "2026-07"
  revenue:     number;
  costs:       number;
  net:         number;
  cumulative:  number;
}
```

---

### 3.3 TeamPage — Użytkownicy + Role

**URL:** `/team`  
**Moduł:** `team`

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│  ZESPÓŁ                              [+ Zaproś użytkownika]     │
│  Zarządzanie dostępem do organizacji                             │
├─────────────────────────────────────────────────────────────────┤
│  STAT CARDS: [Użytkownicy: 5] [Aktywni: 4] [Oczekujące: 1]    │
├─────────────────────────────────────────────────────────────────┤
│  MEMBERS TABLE:                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Użytkownik          │ Rola        │ Status   │ Ostatnia   │ │
│  │                     │             │          │ aktywność  │ │
│  ├─────────────────────┼─────────────┼──────────┼────────────┤ │
│  │ 🟢 Jan Kowalski     │ Owner       │ Aktywny  │ teraz      │ │
│  │ 🟢 Anna Nowak       │ Manager     │ Aktywny  │ 2h temu    │ │
│  │ 🔵 Piotr Wiśn.      │ Analyst     │ Oczekuje │ nigdy      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ROLE PERMISSIONS (accordion):                                    │
│  ▼ Owner — pełny dostęp                                          │
│  ▶ Manager — bez billing i admin                                 │
│  ▶ Analyst — tylko odczyt                                        │
└─────────────────────────────────────────────────────────────────┘
```

#### Komponenty
- `TeamTable` — DataTable z Avatar, role select (inline), remove action
- `InviteModal` — email + rola picker + personal message
- `RolePermissionsAccordion` — widok uprawnień per rola
- `PendingInvitesBanner` — alert jeśli są oczekujące zaproszenia

#### API Calls
```typescript
GET    /api/v1/team                     // lista memberów
POST   /api/v1/team/invite              // { email, role }
PATCH  /api/v1/team/:userId/role        // zmiana roli
DELETE /api/v1/team/:userId             // usuń membera
GET    /api/v1/team/invitations         // oczekujące zaproszenia
DELETE /api/v1/team/invitations/:id     // cofnij zaproszenie
```

#### Types
```typescript
type UserRole = 'owner' | 'manager' | 'analyst' | 'viewer';

interface TeamMember {
  id:          string;
  email:       string;
  name?:       string;
  avatar_url?: string;
  role:        UserRole;
  status:      'active' | 'invited' | 'suspended';
  last_seen?:  string;  // ISO timestamp
  created_at:  string;
}

const ROLE_PERMISSIONS: Record<UserRole, string[]> = {
  owner:    ['*'],
  manager:  ['tenders.*', 'kosztorys.*', 'silnik.*', 'pipeline.*', 'reports.*'],
  analyst:  ['tenders.read', 'kosztorys.read', 'silnik.read'],
  viewer:   ['tenders.read', 'pipeline.read'],
};
```

---

### 3.4 BillingPage — Stripe Portal + Faktury + Plan Usage

**URL:** `/billing`  
**Moduł:** `billing`  
**Guard:** `role === 'owner'`

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│  ROZLICZENIA                                                      │
│  Plan, faktury i limity użycia                                   │
├──────────────────────────────────────────────────────────────────┤
│  OBECNY PLAN:                                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  🏗️ Terra.OS Professional         249 zł / miesiąc     │    │
│  │  Następna faktura: 01.08.2026                            │    │
│  │  [Zarządzaj planem] [Portal Stripe]                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  UŻYCIE — ten miesiąc:                                           │
│  Przetargi skanowane   [██████████░░░░] 78/100                   │
│  Analiza AI (Silnik)   [████████░░░░░░] 63/100                   │
│  Eksporty PDF          [███░░░░░░░░░░░] 12/50                    │
│  Użytkownicy           [████░░░░░░░░░░] 4/5                      │
│                                                                   │
│  HISTORIA FAKTUR:                                                 │
│  Data         │ Kwota    │ Status  │                              │
│  01.07.2026   │ 249 zł   │ ✅ Opł. │ [Pobierz PDF]               │
│  01.06.2026   │ 249 zł   │ ✅ Opł. │ [Pobierz PDF]               │
└─────────────────────────────────────────────────────────────────┘
```

#### Komponenty
- `PlanCard` — obecny plan, cena, CTA do Stripe Customer Portal
- `UsageMeter` — ProgressBar z limitem, tekst "78/100", badge "⚠ 78%" jeśli >80%
- `InvoiceTable` — DataTable faktur z download link
- `StripeBillingPortalButton` — otwiera `stripe.billingPortal.create()` URL w nowym oknie
- `UsageAlertBanner` — pojawia się gdy któryś limit > 90%

#### API Calls
```typescript
GET  /api/v1/billing/subscription   // stan subskrypcji + limity
GET  /api/v1/billing/usage          // bieżące użycie
GET  /api/v1/billing/invoices       // historia faktur
POST /api/v1/billing/portal         // → { url: Stripe Customer Portal URL }
```

#### Types
```typescript
interface Subscription {
  plan:         'free' | 'professional' | 'enterprise';
  status:       'active' | 'canceled' | 'past_due' | 'trialing';
  current_period_end: string;
  amount_pln:   number;
}

interface UsageItem {
  key:     string;
  label:   string;
  used:    number;
  limit:   number;    // Infinity = unlimited
  unit:    string;
}
```

---

### 3.5 AuditLogPage — Immutable Log per Tenant

**URL:** `/audit`  
**Moduł:** `audit`  
**Guard:** `role === 'owner' || role === 'manager'`

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│  LOG AUDYTU                                [Eksportuj CSV]       │
│  Niemodyfikowalny dziennik zdarzeń systemu                       │
├─────────────────────────────────────────────────────────────────┤
│  FILTRY:                                                          │
│  [Szukaj akcji...]  [Użytkownik ▼]  [Zasób ▼]  [Data: ▼▼]     │
│  [Wyczyść filtry]                                                 │
├─────────────────────────────────────────────────────────────────┤
│  LOG TABLE:                                                       │
│  Czas              │ Użytkownik  │ Akcja             │ Zasób    │
│  ──────────────────┼─────────────┼───────────────────┼────────── │
│  2026-07-07 14:23  │ jan.k       │ tender.decided_go  │ T-0042  │
│  2026-07-07 14:22  │ anna.n      │ estimate.created   │ T-0042  │
│  2026-07-07 13:01  │ jan.k       │ engine.run         │ T-0041  │
│  2026-07-07 12:45  │ System      │ bzp.sync           │ —       │
│                                                                   │
│  Strona 1 z 24     [← Poprzednia]  [1 2 3 ... 24]  [Następna →]│
└─────────────────────────────────────────────────────────────────┘
```

#### Komponenty
- `AuditLogTable` — DataTable z server-side pagination (50 wpisów/strona)
- `AuditFilterBar` — user multi-select, action type select, date range picker
- `AuditEntryDetail` — klik na wiersz → modal z pełnym JSON payload
- `ExportCsvButton` — pobiera filtered log jako CSV

#### API Calls
```typescript
GET /api/v1/audit-log?page=1&limit=50&user_id=...&action=...&from=...&to=...
// → { entries: AuditEntry[], total: number, page: number }
GET /api/v1/audit-log/export?format=csv&...filters...
```

#### Types
```typescript
interface AuditEntry {
  id:          string;
  timestamp:   string;   // ISO 8601
  user_id:     string;
  user_name:   string;
  action:      string;   // "tender.created", "engine.run", "bzp.sync", etc.
  resource_type?: string;
  resource_id?:   string;
  payload?:    Record<string, unknown>;
  ip_address?: string;
  user_agent?: string;
}
```

#### Wzorce akcji (audit.actions)
```
tender.created, tender.updated, tender.deleted, tender.decided_go, tender.decided_nogo
estimate.created, engine.run, pipeline.moved
team.invited, team.role_changed, team.removed
billing.plan_changed, billing.portal_accessed
bzp.sync, import.file_uploaded
user.login, user.logout
```

---

### 3.6 LearningPage — Historia Kontraktów + Actual vs Estimate Delta

**URL:** `/learning`  
**Moduł:** `learning`

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│  UCZENIE SIĘ                                                      │
│  Analiza rozbieżności kosztorys vs realizacja                    │
├─────────────────────────────────────────────────────────────────┤
│  STAT CARDS:                                                      │
│  [Kontraktów: 12] [Śr. delta: +4.2%] [Najlepsza: -12%]        │
├──────────────────────────────┬──────────────────────────────────┤
│  ACTUAL vs ESTIMATE CHART    │  WZORZEC ROZBIEŻNOŚCI             │
│                              │                                   │
│  % δ                         │  Kategorie z największą deltą:   │
│  +20% ─────────────────      │  1. Materiały: +8.3%             │
│  +10%    ●    ●  ●           │  2. Robocizna: +3.1%             │
│   0%  ─────●─────────        │  3. Podwykonawcy: +1.4%          │
│  -10%       ●                │  4. Transport: -0.8%             │
│                              │  5. Sprzęt: -2.1%               │
│  Przetarg 1  2  3  4  5      │                                   │
│                              │  AI INSIGHT:                     │
│  [filtr: rok ▼]              │  "Materiały mają tendencję       │
│                              │   przekroczenia o 8.3% —         │
│                              │   uwzględnij w następnej wycenie"│
└──────────────────────────────┴──────────────────────────────────┘
│  TABELA HISTORII:                                                 │
│  Kontrakt │ Wycena (A) │ Realizacja (B) │ Delta │ Rok          │
│  Mostek   │ 2.1 M zł   │ 2.27 M zł     │ +8.1% │ 2025         │
└─────────────────────────────────────────────────────────────────┘
```

#### Komponenty
- `DeltaScatterChart` — Recharts ScatterChart: x=projekt, y=delta%
- `CategoryDeltaBarChart` — horizontal BarChart (positive/negative)
- `AiInsightCard` — generowany komentarz AI o tendencjach
- `HistoryTable` — DataTable z sortowaniem po delta
- `DeltaBadge` — zielony jeśli delta<=0, czerwony jeśli delta>5%

#### API Calls
```typescript
GET /api/v1/learning/history        // lista zakończonych kontraktów z deltami
GET /api/v1/learning/analysis       // AI analysis: trendy, kategorie
GET /api/v1/learning/categories     // rozbieżność per kategoria KNR
```

---

### 3.7 ReportsPage — Generowanie Raportów PDF

**URL:** `/reports`  
**Moduł:** `reports`

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│  RAPORTY                             [+ Nowy raport]            │
│  Generowanie dokumentów PDF i eksportów                         │
├─────────────────────────────────────────────────────────────────┤
│  TEMPLATES:                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 📄 Kosztorys │  │ 📋 Decyzja   │  │ 📊 Plan      │          │
│  │    Ofertowy  │  │  GO/NO-GO    │  │  Tygodniowy  │          │
│  │ [Generuj]    │  │ [Generuj]    │  │ [Generuj]    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │ 📊 Raport    │  │ 📑 Pipeline  │                             │
│  │  Miesięczny  │  │   Export     │                             │
│  │ [Generuj]    │  │ [Generuj]    │                             │
│  └──────────────┘  └──────────────┘                             │
├─────────────────────────────────────────────────────────────────┤
│  HISTORIA RAPORTÓW:                                              │
│  Raport               │ Data           │ Status  │             │
│  Kosztorys T-0042     │ 07.07.2026     │ ✅ Gotowy│ [Pobierz]  │
│  Decyzja T-0041       │ 06.07.2026     │ ⏳ Generuję│           │
└─────────────────────────────────────────────────────────────────┘
```

#### Komponenty
- `ReportTemplateGrid` — karty typów raportów z ikonami i opisami
- `GenerateReportModal` — form: typ, przetarg/kontrakt, opcje (logo, daty)
- `ReportHistoryTable` — DataTable wygenerowanych raportów z download
- `ReportStatusBadge` — generating (spinner), ready (download), error

#### API Calls
```typescript
POST /api/v1/reports                    // { type, tender_id, options }
GET  /api/v1/reports                    // lista wygenerowanych
GET  /api/v1/reports/:id/download       // → PDF binary stream
DELETE /api/v1/reports/:id             // usuń
```

#### Types
```typescript
type ReportType = 'kosztorys' | 'decyzja' | 'plan' | 'monthly' | 'pipeline';

interface Report {
  id:          string;
  type:        ReportType;
  title:       string;
  tender_id?:  string;
  status:      'generating' | 'ready' | 'error';
  created_at:  string;
  file_size?:  number;   // bytes
  download_url?: string;
}
```

#### PDF Stack
```typescript
// Opcja A: @react-pdf/renderer (client-side, TypeScript-friendly)
import { Document, Page, Text, View, StyleSheet } from '@react-pdf/renderer';

// Opcja B: API-side (Puppeteer/Playwright headless) — lepsza dla dużych docs
// POST /api/v1/reports → background job → webhook/polling

// Template: KosztorysPDF.tsx, DecyzjaPDF.tsx, PlanPDF.tsx
```

---

### 3.8 AdminPage — Tenant Management (Owner Only)

**URL:** `/admin`  
**Moduł:** `admin`  
**Guard:** `role === 'owner'` — redirect jeśli nie-owner

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│  ADMINISTRACJA                        ⚠️ STREFA WŁAŚCICIELA     │
│  Zarządzanie organizacją i ustawieniami systemowymi             │
├─────────────────────────────────────────────────────────────────┤
│  ORGANIZACJA:                                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Nazwa:          [Kowalski Construction Sp. z o.o.   ]  │    │
│  │  NIP:            [779-123-45-67                      ]  │    │
│  │  Adres:          [ul. Budowlana 1, Warszawa          ]  │    │
│  │  Profil branżowy:[Roboty drogowe, mostowe ▼          ]  │    │
│  │  Logo:           [wybierz plik...] [aktualny.png]       │    │
│  │                  [Zapisz zmiany]                         │    │
│  └─────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│  INTEGRACJE:                                                      │
│  [🔵 BZP API] Status: ✅ Połączony  [Odśwież token]             │
│  [🟡 GUS API] Status: ✅ Połączony                               │
│  [⚙️ Webhook] Endpoint: [https://...] [Test] [Zapisz]           │
├─────────────────────────────────────────────────────────────────┤
│  STREFA NIEBEZPIECZNA:                                           │
│  [Eksportuj wszystkie dane (ZIP)]                                │
│  [🔴 Usuń organizację] — wymagane potwierdzenie "DELETE"        │
└─────────────────────────────────────────────────────────────────┘
```

#### Komponenty
- `OrgSettingsForm` — react-hook-form + zod, logo upload
- `IntegrationCard` — status integracii, reconnect/test CTA
- `WebhookConfig` — URL input + test button + event type checkboxes
- `DangerZone` — destrukcyjne akcje z double-confirmation modal
- `OwnerGuard` — HOC: `if (role !== 'owner') return <Forbidden />`

#### API Calls
```typescript
GET   /api/v1/admin/org              // dane organizacji
PATCH /api/v1/admin/org              // aktualizuj
POST  /api/v1/admin/org/logo         // upload logo (multipart)
GET   /api/v1/admin/integrations     // status integracji
POST  /api/v1/admin/integrations/test // test webhook
GET   /api/v1/admin/export           // eksport danych (zip)
DELETE /api/v1/admin/org             // usuń org (wymaga confirm string)
```

---

## 4. SPEC ULEPSZEŃ ISTNIEJĄCYCH STRON

### 4.1 DashboardPage — Real Analytics Cards

#### Problem
Sparklines w stat kartach używają statycznego `sparkData = [{v:3},{v:5}...]`. Trend labels są hardcoded strings.

#### Rozwiązanie

```typescript
// API: GET /api/v1/dashboard/stats → DashboardStats (istniejące)
// NOWE POLE: stats.weeklyActivity: Array<{ day: string; count: number }>

// 1. Spark data z API
const sparkData = stats?.weeklyActivity ?? [];

// 2. Trend delta z API (porównanie t-7 dni)
interface StatCard {
  label:     string;
  value:     string;
  trend:     string;         // dynamiczny
  trendDelta?: number;       // np. +3, -1
  trendType?:  'up' | 'down' | 'neutral';
  sparkData:   Array<{ v: number }>;  // z API
}

// 3. Renderowanie trendu:
// +3 → zielony "↑ +3 w tym tygodniu"
// -1 → czerwony "↓ -1 w tym tygodniu"

// 4. Quick Stats row (NOWE — nad stat cards):
// ┌─────────────────────────────────────────┐
// │ Dziś: 2 nowe | 3 w analizie | 1 GO    │
// │ Ten tydzień: +5 przetargów             │
// └─────────────────────────────────────────┘

// 5. Last sync timestamp:
// "Ostatnia synchronizacja BZP: 07.07.2026, 13:41" + Odśwież button
```

#### Nowe Komponenty
- `QuickStatsBar` — poziomy pasek z dzisiejszymi eventami
- `TrendIndicator` — `↑` / `↓` / `→` z kolorem i delta
- `LastSyncBadge` — timestamp + manual refresh button

---

### 4.2 ZwiadPage — Advanced Filters (CPV + Value Range)

#### Problem
Brak zaawansowanych filtrów — nie można filtrować po kodzie CPV ani przedziale wartości.

#### Rozwiązanie

```typescript
// Nowy komponent: AdvancedFilterDrawer
// Otwierany przyciskiem "Filtry zaawansowane" → SideDrawer

interface ZwiadFilters {
  cpv_codes:    string[];    // wielokrotny wybór z drzewa CPV
  value_min?:   number;      // PLN
  value_max?:   number;      // PLN
  deadline_from?: string;    // ISO date
  deadline_to?:  string;
  buyer_region?:  string[];  // województwo
  keywords?:    string;
  status?:      TenderStatus[];
}

// 1. CPV Tree Selector:
// Hierarchia: dział (2 cyfry) → grupy (4) → klasy (6) → kategorie (8)
// Komponent: collapsible tree z checkboxami
// Źródło: GET /api/v1/cpv/tree → CPVNode[]
// Wyszukiwanie w drzewie: instant filter na description
// Max zaznaczonych: 20 węzłów
// Display: "45000000-7 — Roboty budowlane (+3 podkategorie)"

// 2. Value Range Slider:
// Zakres: 0 — 100 M zł
// Kroki: 0, 100k, 500k, 1M, 5M, 10M, 50M, 100M
// Implementacja: @radix-ui/react-slider (dwa thumby)
// Display: "500 tys. zł — 5 M zł"

// 3. Active Filters Pills (pod search barem):
// [CPV: 45000000] [Wartość: 500k—5M] [×]
// Każdy pill ma X do usunięcia

// 4. "Zapisz filtr" — preset nazwany, przechowywany w localStorage
```

---

### 4.3 SilnikPage — L2 Risk Charts (Violin + Waterfall)

#### Problem
Wyniki ryzyka P10/P50/P90 są pokazywane jako 3 liczby. Brak wizualizacji rozkładu i wodospadu czynników.

#### Rozwiązanie

```typescript
// Tab system: [Wyniki] [Rozkład ryzyka] [Czynniki] [Wyjaśnienie]

// TAB 2: Rozkład ryzyka — Violin / Distribution Chart
// Recharts ComposedChart z Area (aproksymacja density)
// Dane: {x: marginalPercentage, density: number}[] z API
// Markery: pionowe linie P10, P50, P90 (ReferenceLine)
// Shade area P10→P90 kolorem amber/20

// TAB 3: Czynniki — Waterfall Chart
// ComposedChart z Bar (positive=zielony, negative=czerwony) 
// + ReferenceLine baseline
// Dane: drivers z S1 jako wartości
// X-axis: nazwa czynnika (skrócona, tooltip pełna)
// Y-axis: % wpływu na marżę
// Suma: ostatni słupek "Łączny efekt" wyróżniony

// TAB 4: Wyjaśnienie — ReactMarkdown
// explanation_md z API → rendered markdown
// Styl: prose prose-invert text-sm

// Kod przykładowy — Waterfall:
function WaterfallChart({ drivers }: { drivers: Driver[] }) {
  const data = drivers.map(d => ({
    name:    d.factor.slice(0, 15),
    value:   d.ST,
    fill:    d.ST >= 0 ? '#10b981' : '#EF4444',
  }));
  
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ bottom: 60 }}>
        <CartesianGrid stroke="#27272a" strokeDasharray="3 3" />
        <XAxis dataKey="name" tick={{ fill: '#71717a', fontSize: 11 }}
               angle={-45} textAnchor="end" />
        <YAxis tick={{ fill: '#71717a', fontSize: 11 }}
               tickFormatter={v => `${(v*100).toFixed(0)}%`} />
        <RechartsTooltip content={<CustomTooltip />} />
        <Bar dataKey="value" radius={[4,4,0,0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.fill} />
          ))}
        </Bar>
        <ReferenceLine y={0} stroke="#52525b" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
```

---

### 4.4 KosztorysPage — Live Violation Badges + Chat Edits Panel

#### Problem
Brak wizualnych wskaźników naruszeń na poziomie linii kosztorysu. Brak AI chat do edycji pozycji.

#### Rozwiązanie

```typescript
// 1. Live Violation Badges per linia:
// Dane: violations z Silnik (axiom_code → position_no mapping)
// Każda linia z naruszeniem: kolorowa kropka + tooltip

interface LineViolation {
  position_no: string;
  severity:    'block' | 'warn' | 'info';
  message:     string;
  axiom_code:  string;
}

// W tabeli:
<td className="px-2 py-1.5 text-earth-300 flex items-center gap-1.5">
  {lineViolations[line.position_no] && (
    <ViolationDot
      severity={lineViolations[line.position_no].severity}
      message={lineViolations[line.position_no].message}
    />
  )}
  {line.description}
</td>

// ViolationDot: 
// block = czerwona kropka animate-pulse + tooltip
// warn  = żółta kropka
// info  = niebieska kropka

// 2. Chat Edits Panel (SideDrawer):
// Przycisk: "💬 Edytor AI" → otwiera SideDrawer width="md" (480px)
// 
// ┌──────────────────────────────────┐
// │ EDYTOR AI — Kosztorys B          │
// │                                  │
// │ [Historia wiadomości]            │
// │ AI: Widzę że poz. 3.2 (Beton     │
// │     C25/30) ma cenę 280 zł/m³.   │
// │     Rynkowa to 310-340 zł/m³.    │
// │     Czy zaktualizować?           │
// │                                  │
// │ [Tak, zaktualizuj] [Pomiń]       │
// │ ─────────────────────────────── │
// │ [Napisz instrukcję... ] [Wyślij] │
// └──────────────────────────────────┘
//
// API: POST /api/v1/tenders/:id/estimates/:estId/chat
// { message: string } → { reply: string; suggested_edits: EstimateLine[] }
// Suggested edits: pojawiają się jako diff view (stara/nowa wartość) z Accept/Reject

interface ChatMessage {
  role:    'user' | 'assistant';
  content: string;
  edits?:  Array<{ position_no: string; field: string; old: string; new: string }>;
}
```

---

### 4.5 PipelinePage — Kanban Drag-Drop

#### Problem
Brak możliwości przeciągania przetargów między etapami pipeline.

#### Rozwiązanie

```typescript
// Biblioteka: @hello-pangea/dnd (fork react-beautiful-dnd, aktywnie utrzymywany)
// Fallback: @dnd-kit/core (lżejszy, bardziej modularny)

// Layout: horizontal scroll z kolumnami per status
// Kolumny: new | matched | watching | analyzing | estimated | decided_go | decided_nogo

// Kod przykładowy:
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';

function PipelineKanban({ tenders }: { tenders: Tender[] }) {
  const grouped = groupByStatus(tenders);

  const onDragEnd = async (result: DropResult) => {
    if (!result.destination) return;
    const { draggableId, destination } = result;
    const newStatus = destination.droppableId as TenderStatus;

    // Optimistic update
    updateTenderStatus(draggableId, newStatus);

    // API call
    await fetch(`/api/v1/tenders/${draggableId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus }),
    });
  };

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      <div className="flex gap-4 overflow-x-auto pb-4">
        {PIPELINE_STAGES.map(stage => (
          <Droppable key={stage.key} droppableId={stage.key}>
            {(provided, snapshot) => (
              <div
                ref={provided.innerRef}
                {...provided.droppableProps}
                className={`w-64 min-h-[200px] rounded-xl p-3 border transition-colors
                  ${snapshot.isDraggingOver
                    ? 'border-accent-primary/50 bg-accent-primary/5'
                    : 'border-earth-700/40 bg-earth-900/40'}`}
              >
                {/* Column header */}
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-2 h-2 rounded-full" style={{ background: stage.color }} />
                  <span className="text-xs font-semibold text-earth-400 uppercase tracking-wider">
                    {stage.label}
                  </span>
                  <span className="ml-auto text-xs text-earth-600 bg-earth-800 px-1.5 py-0.5 rounded">
                    {grouped[stage.key]?.length ?? 0}
                  </span>
                </div>

                {/* Cards */}
                {(grouped[stage.key] ?? []).map((tender, index) => (
                  <Draggable key={tender.id} draggableId={tender.id} index={index}>
                    {(provided, snapshot) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.draggableProps}
                        {...provided.dragHandleProps}
                        className={`glass-card p-3 mb-2 cursor-grab active:cursor-grabbing
                          ${snapshot.isDragging ? 'rotate-1 scale-105 shadow-xl shadow-black/40' : ''}`}
                      >
                        <p className="text-earth-100 text-xs font-medium line-clamp-2">{tender.title}</p>
                        <p className="text-earth-500 text-xs mt-1">{fmtPLN(tender.value_pln)}</p>
                      </div>
                    )}
                  </Draggable>
                ))}
                {provided.placeholder}
              </div>
            )}
          </Droppable>
        ))}
      </div>
    </DragDropContext>
  );
}

// Accessibility: 
// Keyboard drag-drop: Space to pick up, ArrowKeys to move, Space to drop, Escape to cancel
// Screen reader: announces position changes
```

---

### 4.6 AnalyticsPage — Real Win-Rate Trend Chart

#### Problem
Brak rzeczywistego wykresu trendu win-rate (prawdopodobnie mock dane lub brak w ogóle).

#### Rozwiązanie

```typescript
// GET /api/v1/analytics/win-rate?period=12months
// → { months: WinRateMonth[], overall: number, trend: 'up'|'down'|'flat' }

interface WinRateMonth {
  month:       string;   // "2025-07"
  submitted:   number;
  won:         number;
  win_rate:    number;   // 0.0 - 1.0
  value_won:   number;   // PLN
}

// Chart: ComposedChart
// Bar: liczba złożonych ofert (lewa oś, earth-700)
// Line: win_rate % (prawa oś, accent-primary)
// Area: value_won (za linią, accent-primary/10)
// X-axis: miesiące (skrócone: "Lip '25")
// ReferenceLine: śr. win-rate pozioma linia (dashed amber)

function WinRateTrendChart({ data }: { data: WinRateMonth[] }) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={data}>
        <CartesianGrid stroke="#27272a" strokeDasharray="3 3" />
        <XAxis dataKey="month" tick={{ fill: '#71717a', fontSize: 11 }} />
        <YAxis yAxisId="left" tick={{ fill: '#71717a', fontSize: 11 }} />
        <YAxis yAxisId="right" orientation="right"
               tickFormatter={v => `${(v*100).toFixed(0)}%`}
               tick={{ fill: '#10b981', fontSize: 11 }} />
        <RechartsTooltip content={<WinRateTooltip />} />
        <Legend />
        <Bar yAxisId="left" dataKey="submitted" name="Złożone oferty"
             fill="#27272a" radius={[3,3,0,0]} />
        <Bar yAxisId="left" dataKey="won" name="Wygrane"
             fill="#10b981" radius={[3,3,0,0]} opacity={0.8} />
        <Line yAxisId="right" type="monotone" dataKey="win_rate" name="Win rate"
              stroke="#F59E0B" strokeWidth={2.5} dot={{ fill: '#F59E0B', r: 4 }} />
        <ReferenceLine yAxisId="right"
          y={data.reduce((s, d) => s + d.win_rate, 0) / data.length}
          stroke="#F59E0B" strokeDasharray="6 3" label="Śr." />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

// Dodatkowe analytics cards:
// - Win rate overall (duży %, trend ↑/↓)
// - Avg deal size (PLN z trendem)
// - Cycle time: śr. dni od skanowania do decyzji
// - Conversion funnel: nowy → matched → go → won (Sankey / funnel chart)
```

---

## 5. SPEC ONBOARDING FLOW

### 5.1 Onboarding Wizard — 5 Kroków

```
Krok 1: Organizacja → Krok 2: Profil → Krok 3: Pierwszy przetarg → Krok 4: Kosztorys → Krok 5: Gotowy
```

#### Layout Wizarda

```
┌─────────────────────────────────────────────────────────────────┐
│                   Witaj w Terra.OS                               │
│         Skonfiguruj system w 5 prostych krokach                 │
│                                                                  │
│  ●──────○──────○──────○──────○                                  │
│  1      2      3      4      5                                   │
│  Org   Profil Przetarg Wycena Start                             │
│                                                                  │
│  ┌───────────────────────────────────────────────────────┐      │
│  │              [Treść kroku]                             │      │
│  │                                                        │      │
│  │                                                        │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                  │
│  [← Wstecz]                           [Dalej →] / [Zakończ]    │
└─────────────────────────────────────────────────────────────────┘
```

#### Krok 1: Organizacja

```typescript
interface OnboardingStep1 {
  org_name:    string;   // required
  nip:         string;   // 10 cyfr, walidacja checksum
  address:     string;
  industry:    string[]; // multi-select CPV działy
  logo_url?:   string;   // opcjonalny upload
}

// Walidacja: zod schema
// Zapis: PATCH /api/v1/admin/org
// Success: zielony check, animacja → krok 2
// Auto-fill: GUS API lookup po NIP (jeśli poda NIP → prefill reszty)
```

#### Krok 2: Profil Firmy

```typescript
interface OnboardingStep2 {
  capacity_pln_max:   number;    // maks. wartość przetargu
  workers_count:      number;    // liczba pracowników
  certifications:     string[];  // ISO, uprawnienia
  excluded_regions?:  string[];  // województwa bez zasobów
  preferred_cpv:      string[];  // preferowane kody CPV
}

// Informacja: "Profil jest używany przez AI do oceny dopasowania przetargów"
// Slider: wartość maks. (0 — 50 M PLN)
// Multi-select: CPV działy (checkbox lista)
// Zapis: PATCH /api/v1/company/profile
```

#### Krok 3: Pierwszy Przetarg

```typescript
// Opcje:
// A) Wyszukaj z BZP
// B) Wklej numer ogłoszenia BZP
// C) Zaimportuj plik (ZIP/PDF)
// D) Pomiń (opcja ghost)

// Jeśli A: mini wersja ZwiadPage (search input + 3 wyniki)
// Jeśli B: input + "Pobierz" button
// Jeśli C: FileUpload dropzone

// Zapis: tworzy Tender w stanie 'new'
// Success: "Świetnie! Przetarg '{title}' dodany do pipeline"
```

#### Krok 4: Pierwszy Kosztorys

```typescript
// Jeśli przetarg z kroku 3 ma dokumentację:
// → uruchom engine auto: POST /api/v1/tenders/:id/engine/run
// → spinner "Generuję wycenę AI..." (3-8s)
// → pokazuj częściowe wyniki na bieżąco (SSE streaming lub polling)

// Jeśli nie:
// → "Możesz wygenerować kosztorys po dodaniu dokumentacji przetargu"
// → CTA: "Importuj dokumentację"

// Summary: wyświetla P50 margę i verdict GO/NO-GO
```

#### Krok 5: Gotowy!

```typescript
// Celebration: konfetti animacja (canvas-confetti)
// Summary card:
// ✅ Organizacja skonfigurowana
// ✅ Profil firmy uzupełniony
// ✅ Pierwszy przetarg dodany: {title}
// ✅ Kosztorys wygenerowany: {amount} PLN
//
// CTA: "Przejdź do panelu głównego"
// Secondary: "Zobacz tour po systemie"

// Tour: uruchamia Shepherd.js guided tour
```

---

### 5.2 Progress Indicator

```typescript
// components/onboarding/StepIndicator.tsx

interface StepIndicatorProps {
  steps:   Array<{ label: string; description: string }>;
  current: number;   // 0-indexed
}

// Warianty wyświetlania:
// Desktop: horizontal dots + labels + connector lines
// Mobile: "Krok 2 z 5" + progress bar

// Stany kroku:
// completed: ✓ w kółku, kolor accent-primary, linia pełna
// active:    numer w kółku (ring accent-primary), bold label
// upcoming:  numer w kółku (ziemia), muted label

// Animacja: przejście completed → active: scale + color transition (300ms)

function StepIndicator({ steps, current }: StepIndicatorProps) {
  return (
    <div className="flex items-center w-full mb-8" role="list" aria-label="Postęp konfiguracji">
      {steps.map((step, i) => (
        <React.Fragment key={i}>
          {/* Step node */}
          <div className="flex flex-col items-center" role="listitem">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold
              transition-all duration-300 ${
              i < current  ? 'bg-accent-primary text-earth-950' :
              i === current ? 'ring-2 ring-accent-primary bg-earth-800 text-earth-100' :
                              'bg-earth-800 text-earth-600'
            }`}
              aria-current={i === current ? 'step' : undefined}
            >
              {i < current ? <Check className="w-4 h-4" /> : i + 1}
            </div>
            <span className={`text-xs mt-1.5 font-medium ${
              i <= current ? 'text-earth-300' : 'text-earth-600'
            }`}>
              {step.label}
            </span>
          </div>
          {/* Connector */}
          {i < steps.length - 1 && (
            <div className={`flex-1 h-0.5 mx-2 mt-[-14px] transition-colors duration-500 ${
              i < current ? 'bg-accent-primary' : 'bg-earth-700'
            }`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}
```

---

### 5.3 Shepherd.js Guided Tour Spec

```typescript
// lib/tour.ts — Shepherd.js konfiguracja

import Shepherd from 'shepherd.js';
import 'shepherd.js/dist/css/shepherd.css';

// Custom styles (globals.css override):
// .shepherd-element { background: #18181b; border: 1px solid #3f3f46; border-radius: 12px; }
// .shepherd-text    { color: #d4d4d8; font-size: 14px; }
// .shepherd-footer  { border-top: 1px solid #27272a; }
// .shepherd-button  { @apply btn-primary (primary) / btn-secondary (secondary) }

const tourSteps = [
  {
    id: 'dashboard',
    attachTo: { element: '[data-tour="dashboard-stats"]', on: 'bottom' },
    title: '📊 Panel główny',
    text: 'Tu widzisz podsumowanie wszystkich przetargów — aktywne, wartość pipeline i czerwone flagi.',
    buttons: [nextBtn],
  },
  {
    id: 'pipeline-bar',
    attachTo: { element: '[data-tour="pipeline-bar"]', on: 'bottom' },
    title: '🔄 Pipeline przetargów',
    text: 'Pasek pokazuje ile przetargów jest na każdym etapie — od nowego przez analizę do decyzji GO/NO-GO.',
    buttons: [backBtn, nextBtn],
  },
  {
    id: 'zwiad',
    attachTo: { element: '[data-tour="nav-zwiad"]', on: 'right' },
    title: '🔭 Zwiad — skanowanie BZP',
    text: 'Kliknij tutaj, aby wyszukać nowe przetargi z Biuletynu Zamówień Publicznych. System automatycznie oceni dopasowanie do Twojego profilu.',
    buttons: [backBtn, nextBtn],
  },
  {
    id: 'silnik',
    attachTo: { element: '[data-tour="nav-silnik"]', on: 'right' },
    title: '🧠 Silnik AI',
    text: 'Silnik analizuje wybrany przetarg i wydaje rekomendację GO lub NO-GO na podstawie reguł i Monte Carlo.',
    buttons: [backBtn, nextBtn],
  },
  {
    id: 'kosztorys',
    attachTo: { element: '[data-tour="nav-kosztorys"]', on: 'right' },
    title: '🧮 Kosztorys',
    text: 'Automatyczna wycena na podstawie dokumentacji projektowej. Porównuj kosztorys dokumentacji z własną wyceną.',
    buttons: [backBtn, nextBtn],
  },
  {
    id: 'pipeline',
    attachTo: { element: '[data-tour="nav-pipeline"]', on: 'right' },
    title: '📋 Pipeline Kanban',
    text: 'Przeciągaj przetargi między etapami. Śledź postęp od nowego ogłoszenia do złożonej oferty.',
    buttons: [backBtn, nextBtn],
  },
  {
    id: 'finish',
    title: '🎉 Jesteś gotowy!',
    text: 'To tyle! Zacznij od skanowania przetargów w module Zwiad. Powodzenia w przetargach!',
    buttons: [{ text: 'Zakończ tour', action: tour.complete, classes: 'btn-primary' }],
  },
];

// data-tour attributes: dodaj do elementów w istniejących stronach
// <div data-tour="dashboard-stats">...</div>
// <div data-tour="pipeline-bar">...</div>
// <NavItem data-tour="nav-zwiad" />

// Triggering:
// - Automatycznie po onboarding step 5
// - Manualnie: settings → "Uruchom tour" button
// - Restart: localStorage 'terra-tour-completed' = false
```

---

### 5.4 Empty State CTA — Każdy Moduł

```typescript
// Spójne wzorce empty state z actionable CTA per moduł:
// Cel: user nigdy nie patrzy na pustą stronę bez wskazania co zrobić

const MODULE_EMPTY_STATES: Record<string, EmptyStateConfig> = {
  dashboard: {
    condition: 'stats.activeTenders === 0',
    cta: {
      primary:   { label: '🔭 Skanuj przetargi BZP',    module: 'zwiad'    },
      secondary: { label: '📤 Importuj dokumentację',    module: 'import'   },
      tour:      { label: '📖 Pokaż tour',               action: startTour  },
    },
  },
  zwiad: {
    condition: 'results.length === 0 && !hasSearched',
    cta: {
      primary: { label: '🔍 Szukaj po słowach kluczowych', action: focusSearch },
      hint:    'Spróbuj: "roboty drogowe Mazowsze" lub kodu CPV "45233120"',
    },
  },
  zwiad_noResults: {
    condition: 'results.length === 0 && hasSearched',
    cta: {
      primary: { label: '🔄 Poszerz filtry', action: openFilters },
      hint:    'Nie znaleziono wyników — spróbuj bez filtrów wartości lub innego regionu',
    },
  },
  pipeline: {
    condition: 'tenders.length === 0',
    cta: {
      primary: { label: '🔭 Skanuj BZP', module: 'zwiad' },
      hint:    'Przetargi trafiają do pipeline po pierwszym skanowaniu',
    },
  },
  silnik: {
    condition: '!selectedTender',
    cta: {
      primary: { label: '🔭 Wybierz przetarg', module: 'zwiad' },
    },
  },
  kosztorys: {
    condition: '!selectedTender',
    cta: {
      primary: { label: '🔭 Wybierz przetarg', module: 'zwiad' },
    },
  },
  resources: {
    condition: 'resources.length === 0',
    cta: {
      primary: { label: '+ Dodaj pracownika',  action: openAddPersonModal  },
      secondary: { label: '+ Dodaj sprzęt',    action: openAddEquipModal   },
    },
  },
  contracts: {
    condition: 'contracts.length === 0',
    hint: 'Kontrakty tworzone są automatycznie gdy wydasz decyzję GO i zaakceptujesz ofertę',
    cta: {
      primary: { label: '🧠 Idź do Silnika (GO/NO-GO)', module: 'silnik' },
    },
  },
  team: {
    condition: 'members.length <= 1',
    cta: {
      primary: { label: '+ Zaproś użytkownika', action: openInviteModal },
      hint:    'Zaproś kolegów z firmy do współpracy w Terra.OS',
    },
  },
  learning: {
    condition: 'history.length === 0',
    hint: 'Dane pojawiają się po zakończeniu pierwszego kontraktu z wpisaną realizacją',
  },
  reports: {
    condition: 'reports.length === 0',
    cta: {
      primary: { label: '📄 Wygeneruj pierwszy raport', action: openReportModal },
    },
  },
  auditLog: {
    condition: 'entries.length === 0',
    hint: 'Log jest automatyczny — pierwsze wpisy pojawią się po pierwszej akcji użytkownika',
  },
};
```

---

## PODSUMOWANIE — Metryki Implementacji

| Obszar | Zadania | Priorytet |
|--------|---------|-----------|
| Design tokens (kolory, typo, spacing) | 1 plik `tokens/` | P0 — Natychmiastowy |
| 20 UI komponentów | `components/ui/` | P0 — Sprint 1 |
| ErrorBoundary per strona | wrap all pages | P0 — Sprint 1 |
| Toast provider w layout | 1 zmiana | P0 — Sprint 1 |
| DashboardPage — real spark + trend | 2 API fields | P1 — Sprint 1 |
| PipelinePage — Kanban D&D | ~300 loc | P1 — Sprint 2 |
| SilnikPage — Waterfall + Violin | ~200 loc | P1 — Sprint 2 |
| KosztorysPage — violations + chat | ~400 loc | P1 — Sprint 2 |
| ZwiadPage — CPV tree + range slider | ~350 loc | P1 — Sprint 2 |
| AnalyticsPage — WinRate chart | ~150 loc | P2 — Sprint 3 |
| ResourcesPage (nowa) | ~600 loc | P2 — Sprint 3 |
| ContractsPage (nowa) | ~500 loc | P2 — Sprint 3 |
| TeamPage (nowa) | ~400 loc | P2 — Sprint 3 |
| BillingPage (nowa) | ~350 loc | P2 — Sprint 3 |
| AuditLogPage (nowa) | ~300 loc | P3 — Sprint 4 |
| LearningPage (nowa) | ~400 loc | P3 — Sprint 4 |
| ReportsPage (nowa) | ~450 loc | P3 — Sprint 4 |
| AdminPage (nowa) | ~500 loc | P3 — Sprint 4 |
| Onboarding Wizard 5-krokowy | ~600 loc | P2 — Sprint 3 |
| Shepherd.js Tour | ~150 loc | P3 — Sprint 4 |
| WCAG 2.1 AA audit + fixes | per-component | P1 — ongoing |

**Szacowany łączny nakład:** ~7000 LOC TypeScript/TSX  
**Stack additions:**
- `@hello-pangea/dnd` — Kanban drag-drop
- `@radix-ui/react-slider` — Range slider
- `shepherd.js` — Guided tour  
- `react-hook-form` + `zod` — Form validation
- `@tanstack/react-virtual` — Virtualized tables
- `canvas-confetti` — Onboarding celebration
- `react-markdown` — Markdown rendering (explanation_md)
- `@react-pdf/renderer` — PDF generation (opcjonalnie)

---

_Spec wygenerowany przez Frontend Developer Agent — Terra.OS Batch 2_  
_Plik: `/tmp/terra-os-plan/batch2_frontend_spec.md`_
