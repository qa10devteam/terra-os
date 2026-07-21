import Link from 'next/link';
import {
  RefreshCw,
  Brain,
  Calculator,
  GitBranch,
  BarChart3,
  Shield,
} from 'lucide-react';

// ── Metadata ───────────────────────────────────────────────────────────────────

export const metadata = {
  title:       'YU-NA — Wygrywaj przetargi budowlane',
  description: 'Platforma do zarządzania przetargami budowlanymi. AI analiza ryzyka SWZ, automatyczny BZP sync, silnik kosztorysowy KNR.',
};

// ── Data ───────────────────────────────────────────────────────────────────────

const features = [
  {
    Icon:  RefreshCw,
    title: 'Automatyczny BZP Sync',
    desc:  'Nowe przetargi trafiają do systemu co godzinę. Zero ręcznego przeszukiwania portali.',
  },
  {
    Icon:  Brain,
    title: 'AI Analiza Ryzyka SWZ',
    desc:  'Sztuczna inteligencja czyta Specyfikację i wskazuje ryzyka w 3 minuty, nie 3 godziny.',
  },
  {
    Icon:  Calculator,
    title: 'Silnik Kosztorysowy KNR',
    desc:  'Automatyczne wyceny z bazy cen InterCenBud. Kosztorys w Excel gotowy do podpisu.',
  },
  {
    Icon:  GitBranch,
    title: 'Lejek Ofertowy Kanban',
    desc:  'Prowadź każdy przetarg od rozpoznania przez wycenę po podpisaną umowę.',
  },
  {
    Icon:  BarChart3,
    title: 'Raporty Win / Loss',
    desc:  'Analiza skuteczności ofert, porównanie z konkurencją, rekomendacje poprawy marży.',
  },
  {
    Icon:  Shield,
    title: 'Alerty o Terminach',
    desc:  'Powiadomienia gdy zbliża się deadline składania ofert. Nigdy więcej spóźnienia.',
  },
];

const testimonials = [
  {
    quote:   'YU-NA skróciła czas przygotowania oferty z 3 dni do 4 godzin. Wygrywamy 40% więcej przetargów.',
    name:    'MK',
    role:    'Dyrektor ds. ofertowania',
    company: 'BudMaster Sp. z o.o.',
  },
  {
    quote:   'Synchronizacja z BZP i automatyczna analiza ryzyka to game-changer dla każdej firmy budowlanej.',
    name:    'AW',
    role:    'Prezes',
    company: 'Konstrukt Pro S.A.',
  },
  {
    quote:   'ROI zwrócił się w 2 miesiące. Polecam każdemu, kto traci czas na ręczne szukanie przetargów.',
    name:    'TN',
    role:    'CEO',
    company: 'Inżbud Kielce Sp. z o.o.',
  },
];

const problems = [
  {
    before: 'Ręczne przeglądanie BZP co rano',
    after:  'Automatyczny sync co godzinę',
  },
  {
    before: 'Analiza SWZ zajmuje cały dzień',
    after:  'AI ocena ryzyka w 3 minuty',
  },
  {
    before: 'Kosztorysy rozciągnięte na arkusze Excel',
    after:  'Automatyczny silnik KNR jednym kliknięciem',
  },
];

// ── Page ───────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-ink-950 text-slate-100 font-sans">

      {/* ── Nav ───────────────────────────────────────────────────────── */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-ink-950/90 backdrop-blur border-b border-ink-700/40">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <span className="text-xl font-bold text-slate-100">
            YU-NA
            <span className="text-em text-sm font-normal ml-1.5">budos</span>
          </span>
          <div className="flex items-center gap-4">
            <Link href="/landing#pricing" className="text-slate-400 hover:text-slate-100 text-sm transition-colors hidden sm:block">
              Cennik
            </Link>
            <Link href="/docs" className="text-slate-400 hover:text-slate-100 text-sm transition-colors hidden sm:block">
              Dokumentacja
            </Link>
            <Link
              href="/register"
              className="btn-primary text-sm"
            >
              Zacznij bezpłatnie
            </Link>
          </div>
        </div>
      </nav>

      {/* ── 1. Hero ───────────────────────────────────────────────────── */}
      <section className="pt-32 pb-20 px-6 text-center">
        <div className="max-w-4xl mx-auto">
          <div className="inline-block bg-ink-800/60 border border-em/20 text-em text-xs font-semibold px-3 py-1 rounded-full mb-6 uppercase tracking-wider">
            Zaufało nam ponad 50 firm budowlanych
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold text-ink-950/30 leading-tight mb-6 tracking-tight">
            Wygrywaj przetargi{' '}
            <span className="text-em">3× szybciej</span>
          </h1>
          <p className="text-xl text-slate-400 mb-10 max-w-2xl mx-auto leading-relaxed">
            Twój następny kontrakt jest już w systemie. Automatyczna analiza BZP,
            AI ocena ryzyka SWZ i silnik kosztorysowy KNR — w jednej platformie.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/register"
              className="btn-primary text-lg px-8 py-4 rounded-xl shadow-md-glow"
            >
              Zacznij bezpłatnie
            </Link>
            <a
              href="mailto:demo@yu-na.pl"
              className="inline-flex items-center justify-center gap-2 border border-ink-700/50 text-slate-200 px-8 py-4 rounded-xl font-semibold text-lg hover:border-em/40 hover:text-ink-950/30 transition-all duration-200"
            >
              Umów demo
            </a>
          </div>
          <p className="text-slate-600 text-sm mt-5">
            Bez karty kredytowej &bull; 14 dni bezpłatnie &bull; Anuluj kiedy chcesz
          </p>
        </div>
      </section>

      {/* ── 2. Problem vs Solution ────────────────────────────────────── */}
      <section className="py-16 px-6 bg-ink-900/40 border-y border-ink-700/30">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-slate-100 mb-10">
            Analiza przetargu zajmuje{' '}
            <span className="text-nogo">3 godziny</span>.
            YU-NA robi to w{' '}
            <span className="text-go">3 minuty</span>.
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {problems.map((p) => (
              <div
                key={p.before}
                className="bg-ink-800/40 rounded-xl p-5 border border-ink-700/40 text-left"
              >
                <p className="text-nogo/80 text-sm line-through mb-2">{p.before}</p>
                <p className="text-go text-sm font-semibold">{p.after}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 3. Features bento ────────────────────────────────────────── */}
      <section className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-slate-100 mb-3">
              Wszystko czego potrzebujesz
            </h2>
            <p className="text-slate-500">Jeden system zamiast pięciu arkuszy i trzech portali</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((f) => (
              <div
                key={f.title}
                className="bg-ink-900/60 border border-ink-700/40 rounded-xl p-6 hover:border-em/30 hover:bg-ink-800/60 transition-all duration-200 group"
              >
                <div className="w-10 h-10 rounded-md bg-em/10 border border-em/20 flex items-center justify-center mb-4 group-hover:bg-em/15 transition-colors">
                  <f.Icon className="w-5 h-5 text-em" />
                </div>
                <h3 className="text-base font-bold text-slate-100 mb-2">{f.title}</h3>
                <p className="text-slate-500 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 4. Testimonials ──────────────────────────────────────────── */}
      <section className="py-20 px-6 bg-ink-900/30 border-y border-ink-700/30">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-slate-100 mb-3">Co mówią nasi klienci</h2>
            <p className="text-slate-500">Firmy budowlane, które wygrywają więcej dzięki YU-NA</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {testimonials.map((t) => (
              <div
                key={t.name}
                className="bg-ink-800/40 border border-ink-700/40 rounded-xl p-6"
              >
                <p className="text-slate-300 text-sm leading-relaxed mb-5 italic">
                  &ldquo;{t.quote}&rdquo;
                </p>
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-em/15 border border-em/20 flex items-center justify-center text-sm font-bold text-em flex-shrink-0">
                    {t.name}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-slate-200">{t.role}</div>
                    <div className="text-xs text-slate-500">{t.company}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 5. Pricing ───────────────────────────────────────────────── */}
      <section id="pricing" className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-slate-100 mb-3">Prosty cennik</h2>
          <p className="text-slate-500 mb-10">
            Od <span className="text-slate-200 font-semibold">0 PLN</span> do pełnego enterprise — bez gwiazdek
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { name: 'Free',       price: '0 PLN',      note: 'do 5 przetargów / mies.' },
              { name: 'Pro',        price: '499 PLN',    note: 'do 50 przetargów + AI',   popular: true },
              { name: 'Business',   price: '1 499 PLN',  note: 'bez limitu + API' },
              { name: 'Enterprise', price: 'Wycena',     note: 'on-premise + SSO' },
            ].map((p) => (
              <div
                key={p.name}
                className={[
                  'rounded-xl p-5 border text-center',
                  p.popular
                    ? 'border-em/60 bg-em/5 ring-1 ring-em/20'
                    : 'border-ink-700/40 bg-ink-800/30',
                ].join(' ')}
              >
                {p.popular && (
                  <div className="text-[10px] font-bold uppercase tracking-wider text-em mb-2">
                    Popularny
                  </div>
                )}
                <div className={`font-bold text-sm mb-1 ${p.popular ? 'text-em' : 'text-slate-200'}`}>
                  {p.name}
                </div>
                <div className="text-slate-100 font-extrabold text-lg">{p.price}</div>
                <div className="text-slate-600 text-xs mt-1">{p.note}</div>
              </div>
            ))}
          </div>
          <Link
            href="/pricing"
            className="text-em hover:text-em/80 font-semibold text-sm underline underline-offset-4 transition-colors"
          >
            Porównaj pełne plany →
          </Link>
        </div>
      </section>

      {/* ── 6. CTA końcowe ───────────────────────────────────────────── */}
      <section className="py-20 px-6 bg-ink-900/60 border-t border-ink-700/30">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-slate-100 mb-4 leading-tight">
            Twój następny przetarg<br />
            <span className="text-em">jest już w systemie</span>
          </h2>
          <p className="text-slate-500 mb-8 text-lg">
            Zacznij bezpłatnie i przekonaj się, że wygrywanie przetargów może być prostsze.
          </p>
          <Link
            href="/register"
            className="btn-primary text-lg px-10 py-4 rounded-xl shadow-md-glow"
          >
            Zacznij bezpłatnie — bez karty kredytowej
          </Link>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer className="border-t border-ink-700/40 py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4 text-slate-600 text-sm">
          <span className="font-bold text-slate-400">YU-NA</span>
          <div className="flex gap-6">
            <Link href="/docs"     className="hover:text-slate-200 transition-colors">Dokumentacja</Link>
            <Link href="/pricing"  className="hover:text-slate-200 transition-colors">Cennik</Link>
            <a href="mailto:kontakt@yu-na.pl" className="hover:text-slate-200 transition-colors">Kontakt</a>
          </div>
          <span>© 2026 YU-NA. Wszelkie prawa zastrzeżone.</span>
        </div>
      </footer>
    </div>
  );
}
