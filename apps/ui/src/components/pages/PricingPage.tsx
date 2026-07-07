'use client';

import Link from 'next/link';

const plans = [
  {
    id: 'free',
    name: 'Free',
    price: '0 PLN',
    period: 'bezpłatny',
    popular: false,
    features: [
      'Do 5 przetargów',
      'Ręczne zarządzanie',
      'Podstawowe raporty',
      'Wsparcie e-mail',
    ],
    cta: 'Zacznij bezpłatnie',
    ctaHref: '/register',
    highlight: false,
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '499 PLN',
    period: '/miesiąc',
    popular: true,
    features: [
      'Do 50 przetargów',
      'AI analiza ryzyka SWZ',
      'Automatyczny BZP sync',
      'Silnik kalkulacji',
      '5 członków zespołu',
      'Eksport Excel / PDF',
      'Priorytetowe wsparcie',
    ],
    cta: 'Wybierz Pro',
    ctaHref: '/register?plan=pro',
    highlight: true,
  },
  {
    id: 'business',
    name: 'Business',
    price: '1 499 PLN',
    period: '/miesiąc',
    popular: false,
    features: [
      'Nielimitowane przetargi',
      'Pełne AI analizy',
      'Dostęp API',
      'Nieograniczony zespół',
      'Zaawansowane raporty',
      'Dedykowany opiekun',
    ],
    cta: 'Wybierz Business',
    ctaHref: '/register?plan=business',
    highlight: false,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 'Wycena',
    period: 'indywidualna',
    popular: false,
    features: [
      'On-premise / self-hosted',
      'SSO / SAML',
      'SLA 99.9%',
      'Dedykowany opiekun',
      'Własne integracje',
      'Audyt bezpieczeństwa',
    ],
    cta: 'Skontaktuj się',
    ctaHref: 'mailto:sales@terra.os',
    highlight: false,
  },
];

export function PricingPage() {
  return (
    <div className="min-h-screen bg-[#0f1117] text-white py-16 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-4">
            Prosty, przejrzysty cennik
          </h1>
          <p className="text-[#8b9eb0] text-lg max-w-2xl mx-auto">
            Zacznij bezpłatnie, skaluj w miarę wzrostu. Bez ukrytych kosztów.
          </p>
        </div>

        {/* Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={`relative rounded-2xl border p-6 flex flex-col ${
                plan.highlight
                  ? 'border-[#c8a96e] bg-[#1a1d26] shadow-[0_0_40px_rgba(200,169,110,0.15)]'
                  : 'border-[#2a2d3a] bg-[#141720]'
              }`}
            >
              {/* Popular badge */}
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-[#c8a96e] text-[#0f1117] text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wide">
                    Najpopularniejszy
                  </span>
                </div>
              )}

              {/* Plan name */}
              <h2 className={`text-xl font-bold mb-1 ${plan.highlight ? 'text-[#c8a96e]' : 'text-white'}`}>
                {plan.name}
              </h2>

              {/* Price */}
              <div className="mb-6">
                <span className="text-3xl font-extrabold text-white">{plan.price}</span>
                <span className="text-[#8b9eb0] text-sm ml-1">{plan.period}</span>
              </div>

              {/* Features */}
              <ul className="space-y-2 flex-1 mb-8">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2 text-sm text-[#c5ccd6]">
                    <span className="text-[#4caf7d] mt-0.5">✓</span>
                    {feature}
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <Link
                href={plan.ctaHref}
                className={`block text-center rounded-xl py-3 px-4 font-semibold text-sm transition-all ${
                  plan.highlight
                    ? 'bg-[#c8a96e] text-[#0f1117] hover:bg-[#d4b87e]'
                    : 'bg-[#2a2d3a] text-white hover:bg-[#333647] border border-[#3a3d4a]'
                }`}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>

        {/* Footer note */}
        <p className="text-center text-[#8b9eb0] text-sm mt-10">
          Wszystkie plany zawierają 14-dniowy bezpłatny okres próbny. Rezygnacja w dowolnym momencie.
        </p>
      </div>
    </div>
  );
}
