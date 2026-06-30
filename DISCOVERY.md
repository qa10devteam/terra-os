# Terra.OS — Discovery: 10 Faz Dominacji Rynku

> Analiza API → roadmap wdrożeń → przewaga konkurencyjna
> Data: 2026-06-30 | Autor: Hermes / QA10

---

## TL;DR — Problem i Pozycja

**Kim jest wykonawca robót ziemnych dziś?**
- Przetargi śledzi przez BZP ręcznie (sprawdza PDF co rano)
- Kosztorys robi w Excelu 3-4 dni
- Ryzyko ocenia „czuciem" kierownika
- Przegrywa przetargi bo nie zdąży lub się pomylił o 8%

**Terra.OS po 10 fazach:**
- Przetargi przychodzą same, preselekcja AI w 4s
- Kosztorys z przedmiaru → 12 minut
- Ryzyko: Monte Carlo + LLM → decyzja z uzasadnieniem
- Wygrywa przetargi bo ma przewagę informacyjną 3-5 dni i dokładność ±3%

---

## FAZA 1 — Żywy Feed Przetargów (tenders.guru + BZP REST)

### Problem który rozwiązuje
Wykonawcy codziennie ręcznie przeglądają BZP. Tracą 30-60 min/dzień. Często przegapiają.

### API
- **tenders.guru/pl** — JSON feed nowych przetargów PL, aktualizacja dzienna, darmowy
- **BZP API (ezamawiajacy.pl)** — oficjalne REST API zamówień publicznych
- **TED (Tenders Electronic Daily)** — przetargi UE powyżej progów (roboty > 5,382 MLN EUR)

### Co budujemy
```
Cron co 4h → pull tenders.guru → filter CPV 451xxxxx (roboty ziemne/drogowe) →
score match (wartość, województwo, CPV, termin) → push do kolejki "nowe"
```

### Wynik dla użytkownika
Rano otwiera Terra.OS → widzi 3-8 nowych przetargów dobranych do jego profilu. Nie musi szukać.

### KPI
- Pokrycie: >95% przetargów z BZP w kategorii roboty ziemne
- Czas od publikacji do powiadomienia: <4h
- Precision dopasowania: >70%

---

## FAZA 2 — Inteligentny Parser Dokumentów (OCR.Space + Jina AI)

### Problem który rozwiązuje
SIWZ i przedmiary to PDFy, często skany. Ręczne przepisanie przedmiaru = 4-8h pracy.

### API
- **OCR.Space** — free 25k req/mies, obsługuje PL, PDF → tekst, max 1MB/file
- **Jina AI Reader** (`r.jina.ai/{url}`) — free, konwertuje URL/PDF na czysty markdown
- **Jina Embeddings** (`jina-embeddings-v3`) — free tier 1M tokenów, multilingual

### Pipeline
```
PDF SIWZ → OCR.Space → tekst → Jina Embeddings → wektorowa baza (pgvector)
                              → Groq LLM → structured extract:
                                {przedmiar_items[], terminy, kary_umowne, 
                                 warunki_udzialu, red_flags[]}
```

### Wynik dla użytkownika
Klika „Analizuj dokumentację" → 90 sekund → widzi:
- Przedmiar w tabeli (pozycje, KNR, ilości)
- Red flags (kary umowne >10%, termin <30 dni, warunek niemożliwy do spełnienia)
- Kluczowe fakty (lokalizacja, zamawiający NIP, wcześniejsze umowy)

### KPI
- Czas analizy PDF: <120s
- Dokładność wyciągania pozycji przedmiaru: >85%
- Red flags recall: >90% blokujących warunków

---

## FAZA 3 — Kosztorys Wspomagany AI (Groq + NBP + własna baza KNR)

### Problem który rozwiązuje
Kosztorys robi się 3-4 dni. W branży robót ziemnych: robocizna, materiały, sprzęt — wszystko zmienne.

### API
- **Groq** (`llama-3.3-70b-versatile`) — free tier 14,400 req/dzień, 131k ctx, <1s response
- **NBP API** — kursy walut real-time (materiały z importu, paliwo w EUR)
- **FRED API** — indeksy CPI materiałów budowlanych (kalibracja historyczna)

### Pipeline
```
Przedmiar items → mapowanie KNR → baza cen jednostkowych (self-maintained) →
NBP kursy (materiały EUR/USD) → kalkulacja 2 warianty (doc/owner) →
Groq: "sprawdź czy ceny są realistyczne dla rynku dolnośląskiego Q2 2026"
```

### Wynik dla użytkownika
Kosztorys z 20 pozycji → 12 minut (vs 4 dni w Excel). Dwa warianty do porównania. AI komentarz.

### KPI
- Czas generacji kosztorysu: <15 min
- Dokładność wyceny vs rynek: ±8%
- Pokrycie bazy KNR: >500 najczęstszych pozycji robót ziemnych

---

## FAZA 4 — Inteligencja Lokalizacyjna (Open-Meteo + GeoNames + GraphHopper)

### Problem który rozwiązuje
Wykonawca nie wie: czy warto jechać 200km na budowę? Ile kosztuje mobilizacja sprzętu? Jaka pogoda w terminie robót?

### API
- **Open-Meteo** — darmowy, CORS, prognoza 16 dni + historia 80 lat, lat/lon
- **GeoNames** — geocoding PL, darmowy po rejestracji, postalCode search
- **GraphHopper** — routing ciężarowy (HGV), free 500 req/dzień, TomTom quality
- **Open Government Poland** — GUS dane regionalne (wskaźniki budownictwa wg województw)

### Pipeline
```
Przetarg.voivodeship → GeoNames → lat/lon centroidu →
GraphHopper: odległość od bazy sprzętu → koszt transportu (zł/km × t-km) →
Open-Meteo: prognoza na termin robót → ryzyko pogodowe →
Wynik: "Koszt mobilizacji: 8,400 PLN | Ryzyko pogodowe: WYSOKIE (sierpień, deszcz >50%)"
```

### Wynik dla użytkownika
W panelu przetargu: mapa + odległość + prognoza + szacowany koszt dojazdu/mobilizacji.
Nowe pole w kosztorysie: „Koszty mobilizacji" wyliczone automatycznie.

### KPI
- Pokrycie geocodingu PL: >99% powiatów
- Dokładność kosztu mobilizacji: ±15%
- Prognoza pogody: 14-dniowa accuracy >80%

---

## FAZA 5 — Silnik Ryzyka nowej generacji (Groq LLM + Monte Carlo)

### Problem który rozwiązuje
Obecny silnik: deterministyczne reguły + uproszczone MC. Brakuje kontekstu prawno-rynkowego.

### API
- **Groq** (`llama-3.3-70b-versatile`) — analiza klauzul umowy, risk scoring
- **Jina Reranker** — priorytetyzacja red flags wg severity
- **Open Government Poland** — historia przetargów zamawiającego (czy płaci w terminie?)

### Pipeline
```
SIWZ tekst → Groq: "Zidentyfikuj top 5 ryzyk prawnych" →
Baza historii zamawiającego (scraped z BZP) → scoring płatności →
MC 5000 próbek: rozkłady cen materiałów + ryzyko prawne + pogoda →
P10/P50/P90 marże → rekomendacja GO/NO-GO/NEGOCJUJ z uzasadnieniem
```

### Wynik dla użytkownika
„Rekomendacja: NEGOCJUJ. Główne ryzyki: kara 0.5%/dzień (rynek: 0.2%), termin 45 dni (typowy: 60). Marża P50: 7.2%, P10: -2.1% (ryzyko straty)."

### KPI
- Trafność rekomendacji GO/NOGO (weryfikacja post-factum): >75%
- Czas analizy: <30s
- Coverage ryzyk: >12 kategorii

---

## FAZA 6 — Wywiad Rynkowy (tenders.guru historia + Econdb + GUS)

### Problem który rozwiązuje
Wykonawca nie wie: ile kosztowały podobne roboty w 2024? Kto wygrał? Po jakiej cenie?

### API
- **tenders.guru historia** — archiwum wyników przetargów PL (oferty, ceny, zwycięzcy)
- **Econdb** — makrodane: indeks cen produkcji budowlanej PL (GUS data), free
- **Open Government Poland (dane.gov.pl)** — otwarte zbiory GUS o budownictwie
- **FRED** — globalne indeksy cen materiałów (stal, paliwo, cement)

### Pipeline
```
Nowy przetarg → similar CPV + region + wartość →
Szukaj wyników historycznych → wyciągnij: liczba ofert, cena min/max/avg →
Indeks cen materiałów Q2'24 vs Q2'26 → przelicz →
Output: "Podobne przetargi: 8 wyników, avg 4.2M PLN (±12%), min ofert: 2, max: 7"
```

### Wynik dla użytkownika
W Zwiadzie: panel „Benchmarki rynkowe" z historią podobnych przetargów. Wiedza o konkurencji.

### KPI
- Pokrycie historii: przetargi 2019-2026 (>50,000 rekordów roboty ziemne)
- Accuracy benchmark: ±15% vs rynek
- Avg. podobnych przetargów: ≥5 per nowy przetarg

---

## FAZA 7 — Mobilny Raport Terenowy (OCR mobile + Geolokalizacja)

### Problem który rozwiązuje
Kierownik jedzie na wizję lokalną. Robi zdjęcia. Wraca. Opisuje. Traci 3h.

### API
- **OCR.Space** — zdjęcie tablicy/dokumentu → tekst w terenie
- **Open-Meteo** — aktualna pogoda na placu budowy (warunki do oceny gruntu)
- **GeoNames + GraphHopper** — odległość od bazy, czas dojazdu sprzętu
- **Jina AI** — synteza notatek głosowych/tekstowych z wizji

### Pipeline
```
Aplikacja mobilna (PWA) → GPS → pobierz lokalizację placu →
Zrób zdjęcie dokumentu/tablicy → OCR → wyciągnij dane do przetargu →
Dodaj notatkę głosową → Jina/Groq → transkrypcja + podsumowanie →
Zapisz jako "Raport z wizji lokalnej" w przetargu
```

### Wynik dla użytkownika
Kierownik wraca z terenu: raport już gotowy w systemie. Zdjęcia, notatki, komentarze AI.

### KPI
- Czas tworzenia raportu terenowego: <5 min (vs 3h ręcznie)
- Pokrycie funkcji offline: OCR działa bez internetu (model lokalny)

---

## FAZA 8 — Zielony Kosztorys (Carbon Interface + Climatiq)

### Problem który rozwiązuje
Coraz więcej przetargów publicznych wymaga kalkulacji emisji CO₂ (kryterium środowiskowe).
Wykonawcy nie mają narzędzia → tracą punkty w kryterium → przegrywają.

### API
- **Carbon Interface** (`/estimates`) — emisja dla: electricity, fuel, shipping, construction
- **Climatiq** (`/estimate`) — 18,000+ emission factors, DEFRA/EPA/ADEME
- **SustainMetrics** — GHG factors budownictwo

### Pipeline
```
Kosztorys → pozycje: paliwo (L), energia (kWh), transport (tkm), materiały →
Climatiq: emission factor per activity →
Suma CO₂ [tCO₂e] → porównanie z benchmarkiem sektora →
Raport środowiskowy gotowy do złożenia z ofertą
```

### Wynik dla użytkownika
Jeden klik → raport emisji dla oferty. W przetargach z kryterium środowiskowym: +5-15 punktów.
Przewaga nad 90% konkurentów którzy tego nie robią.

### KPI
- Pokrycie pozycji kosztorysowych z emisją: >80%
- Czas generacji raportu CO₂: <30s
- Zgodność z normą: GHG Protocol Scope 1+2

---

## FAZA 9 — Platforma Multi-tenant SaaS (Architektura Skalowalności)

### Problem który rozwiązuje
Terra.OS działa dla 1 firmy. Rynek to 5,000+ firm robót ziemnych w Polsce.

### Co budujemy
- **Tenant isolation** — osobny profil CPV/region/marże dla każdej firmy
- **Shared intelligence** — anonymizowana baza benchmarków rynkowych (wszyscy korzystają)
- **Subscription tiers:**
  - START: 1 użytkownik, 20 przetargów/mies, brak LLM — **299 PLN/mies**
  - PRO: 5 użytkowników, unlimited, pełne AI — **999 PLN/mies**
  - ENTERPRISE: white-label, API, SSO — **3,499 PLN/mies**
- **Onboarding self-serve** — firma wypełnia profil (CPV, region, sprzęt, marże) → gotowe w 10 min
- **Billing** — Stripe (PLN, faktura VAT)

### KPI
- Time-to-value: <30 min od rejestracji do pierwszego kosztorysu
- Churn: <5%/mies (branża B2B SaaS benchmark)
- NPS target: >50

---

## FAZA 10 — Sieć Inteligencji Branżowej (Network Effect)

### Problem który rozwiązuje
Każda firma działa w silosie. Nikt nie wie kto wygrał co i po jakiej cenie.
Terra.OS może stać się repositorium wiedzy branżowej — jak Bloomberg dla budownictwa.

### Co budujemy
- **Anonimowy benchmark engine** — po każdym złożonym przetargu: zbierz cenę oferty,
  wynik, warunki → anonymizuj → wzbogać bazę → wszyscy zyskują lepsze benchmarki
- **Alerty branżowe** — „W tym tygodniu: 34 przetargi roboty ziemne PL, top region: dolnośląskie (8), avg wartość: 3.2M PLN"
- **Indeks cen Terra.OS** — własny indeks cen robót ziemnych PL (jak LIBOR dla branży)
  publikowany kwartalnie → PR + SEO + thought leadership
- **API dla biur kosztorysowych** — Terra.OS jako platforma, nie tylko produkt
- **Marketplace podwykonawców** — znajdź podwykonawcę z certyfikatem ISO, wolnego sprzętu w regionie

### Network Effect Math
```
N firm na platformie → N × przetargów w historii → lepsze benchmarki →
lepsze rekomendacje → więcej firm → ...
```

10 firm = słabe benchmarki
100 firm = użyteczne benchmarki  
1000 firm = Terra.OS jest standardem branżowym, dane CENNE, trudne do skopiowania

### KPI
- Benchmark coverage: >80% przetargów kategorii 451xxxxx po 500 klientach
- Indeks Terra.OS: kwartalny raport cytowany przez media branżowe
- API revenue: 20% total revenue przy 200+ klientach

---

## Roadmap Wdrożeń (12 miesięcy)

| Kwartał | Fazy | Cel biznesowy |
|---------|------|--------------|
| **Q3 2026** | 1 + 2 + 3 | MVP → pilot z 3 firmami, kosztorys działa |
| **Q4 2026** | 4 + 5 | Pełna analiza ryzyka, lokalizacja, pierwsze płatności |
| **Q1 2027** | 6 + 7 | Wywiad rynkowy, mobilność, 20+ klientów |
| **Q2 2027** | 8 + 9 | Zielony kosztorys, SaaS multi-tenant, skalowanie |
| **Q3+ 2027** | 10 | Network effect, indeks branżowy, market leadership |

---

## Stack Techniczny (co już mamy vs co dokładamy)

| Warstwa | Mamy dziś | Po 10 fazach |
|---------|-----------|-------------|
| Frontend | Next.js + Tailwind dark | PWA mobile + desktop |
| Backend | FastAPI + PostgreSQL | + pgvector + Redis queue + Celery |
| AI/LLM | StubClient (mock) | Groq llama-3.3-70b (live) |
| Dane przetargów | 20 seed rekordów | tenders.guru live feed |
| Kosztorys | Ręczne parametry | KNR baza + NBP kursy + ceny rynkowe |
| Dokumenty | Upload manual | OCR.Space + Jina pipeline |
| Geolokalizacja | Brak | GeoNames + GraphHopper + Open-Meteo |
| Ryzyko | Monte Carlo lokalne | MC + Groq + historia zamawiającego |
| Multi-tenant | Częściowy (tenant_id) | Full isolation + Stripe |

---

## Przewaga Konkurencyjna (vs istniejące narzędzia)

| Narzędzie | Słabość | Terra.OS advantage |
|-----------|---------|-------------------|
| **Budimex/własne systemy** | Tylko dla korporacji, CAPEX 2M+ | SaaS 999 PLN/mies |
| **Norma Pro** | Tylko kosztorys, brak AI, brak przetargów | End-to-end flow |
| **BZP ręcznie** | Codzienne przeglądanie, 60 min/dzień | Push notifications, AI preselekcja |
| **Excel** | Brak wersjonowania, brak MC, wolny | 12 min vs 4 dni |
| **Asystent BZP (startup)** | Tylko lista przetargów, brak kosztorysu | Pełny pipeline decyzyjny |

**Moat:** Baza benchmarków rośnie z każdym klientem. Po 100 klientach: niemożliwa do skopiowania.

---

*Terra.OS — od arkusza Excel do intelligence platform dla 5,000 wykonawców robót ziemnych w Polsce.*
