# 🧭 Terra.OS — Batch 3: Product Manager Deliverables
**QA10 sp. z o.o. | KRS 0001232199 | NIP 9542906279 | Katowice**
**Kontakt:** hello@qa10.io | qa10.io
**Founder:** Mateusz Jakimow (CEO), Adrianna Kmieciak (CTO)
**Data:** Lipiec 2026

---

## SPIS TREŚCI

1. [Discovery Research](#1-discovery-research)
   - 1.1 Job Stories (3 persony × 5 historii)
   - 1.2 Customer Journey Map — Kierownik Przetargów
   - 1.3 Competitive Analysis — Feature Matrix
2. [Go-To-Market Plan](#2-go-to-market-plan)
   - 2.1 Beta Acquisition Plan (Q3 2026)
   - 2.2 Content Strategy — 12-tygodniowy plan LinkedIn
   - 2.3 Pricing Justification & ROI Calculator
3. [PRD — M7 Module 3: Logistyka OR-Tools](#3-prd--m7-module-3-logistyka-or-tools)
4. [Enterprise Roadmap](#4-enterprise-roadmap)
5. [Beta Program Plan](#5-beta-program-plan)

---

# 1. DISCOVERY RESEARCH

## 1.1 Job Stories — 3 Persony × 5 Historii

> **Format:** "Gdy [sytuacja], chcę [motywacja], żeby [efekt]"

---

### 🧑‍💼 PERSONA 1: Kierownik Przetargów (Piotr, 42 l., firma 80 os., Katowice)
*Odpowiada za identyfikację przetargów, wstępną kwalifikację, koordynację oferty. Zarządza 15-30 przetargami miesięcznie.*

| # | Job Story |
|---|-----------|
| JS-1 | Gdy przeglądanm BZP o 7:00 rano i widzę 40 nowych ogłoszeń CPV 45112xxx, **chcę** automatycznie posortować je wg szansy na wygraną i pasowania do naszych kompetencji, **żeby** skupić zespół tylko na 3-5 realnych szansach i nie marnować czasu na analizę nieopłacalnych postępowań. |
| JS-2 | Gdy mam deadline na złożenie oferty za 48h, **chcę** mieć gotowy szkielet dokumentacji z pre-wypełnionymi danymi firmy, referencjami i certyfikatami, **żeby** zespół skupił się na wycenie zamiast na zbieraniu tych samych dokumentów po raz n-ty. |
| JS-3 | Gdy zamawiający zmienia SIWZ w trakcie przetargu, **chcę** otrzymać natychmiastowy alert z wyróżnieniem zmienionych paragrafów i oceną wpływu na naszą ofertę, **żeby** nie przegapić krytycznych zmian w harmonogramie lub warunkach płatności. |
| JS-4 | Gdy przegrywamy przetarg, **chcę** zobaczyć analizę dlaczego (cena vs. budżet, punkty JEDZ, kryteria pozacenowe), **żeby** zrozumieć wzorzec porażek i poprawić scoring w kolejnych postępowaniach. |
| JS-5 | Gdy buduję raport miesięczny dla prezesa, **chcę** jednym kliknięciem wygenerować dashboard z win-rate, średnim marginesem, wartością pipeline i trendami, **żeby** mieć argumenty do decyzji o zatrudnieniu dodatkowego kosztorysanta. |

---

### 🔢 PERSONA 2: Kosztorysant (Magda, 35 l., firma 50 os., Kraków)
*Tworzy kosztorysy ofertowe dla robót ziemnych. Pracuje z KNR, SEKOCENBUD, Excel. Główna bolączka: czas i błędy mnożnikowe.*

| # | Job Story |
|---|-----------|
| JS-6 | Gdy dostaję przedmiar robót z projektu technicznego (PDF/DWG), **chcę** aby system automatycznie wyciągnął pozycje KNR i powiązał je z aktualnymi cenami SEKOCENBUD, **żeby** zamiast 6h wprowadzania danych robić 30-minutową korektę eksperta. |
| JS-7 | Gdy wyceniam roboty ziemne na trudnym gruncie (kategoria IV-V), **chcę** aby silnik AI sugerował odpowiednie narzuty i katalogowe modyfikacje na podstawie geologii z BDG (baza danych geologicznych PIG), **żeby** moja wycena była defensywna i chroniła firmę przed stratą na kontrakcie. |
| JS-8 | Gdy porównuję alternatywne scenariusze sprzętu (koparka kołowa vs. gąsienicowa), **chcę** symulację Monte Carlo kosztów z uwzględnieniem zmienności paliwa i przestojów, **żeby** wybrać wariant z najlepszym stosunkiem koszt/ryzyko. |
| JS-9 | Gdy kończę kosztorys, **chcę** automatyczny audit PZP który sprawdza czy wycena jest zgodna z art. 246 PZP (cena jako jedyne kryterium), **żeby** nie stracić oferty na etapie formalnym. |
| JS-10 | Gdy przetarg jest podobny do kosztorysu który robiłam rok temu, **chcę** klonować i aktualizować poprzednią wycenę z przeliczeniem cen na bieżący kwartał SEKOCENBUD, **żeby** nie zaczynać od zera i zaoszczędzić 3-4h pracy. |

---

### 👔 PERSONA 3: Prezes SMB (Andrzej, 55 l., firma 120 os., Gliwice)
*Właściciel. Decyduje o inwestycjach, odpowiada za rentowność. Technicznie niebiegły, wymagający, ROI-oriented.*

| # | Job Story |
|---|-----------|
| JS-11 | Gdy planuję budżet na przyszły rok, **chcę** prognozę pipeline przetargów CPV 45112 w moim regionie na 6 miesięcy do przodu (dane TED + BZP), **żeby** decydować o rozbudowie floty sprzętu z wyprzedzeniem, nie na ostatnią chwilę. |
| JS-12 | Gdy mój kierownik przetargów odchodzi z firmy, **chcę** mieć pełną historię postępowań, szablony i know-how zdeponowane w systemie, **żeby** nie tracić wiedzy instytucjonalnej i onboardować następcę w tygodnie, nie miesiące. |
| JS-13 | Gdy negocjuję warunki z bankiem pod linię kredytową na przetarg, **chcę** wygenerować profesjonalny raport cash-flow projektu z scenariuszami pesymistycznym/bazowym/optymistycznym, **żeby** przekonać bank do finansowania bez tygodniowego oczekiwania na zewnętrznego konsultanta. |
| JS-14 | Gdy porównuję wyniki naszej firmy vs. rynek (win-rate, marże, wartość wygranych kontraktów), **chcę** benchmark anonimizowany vs. inne firmy CPV 45112 w regionie korzystające z Terra.OS, **żeby** wiedzieć czy jesteśmy powyżej czy poniżej mediany branżowej. |
| JS-15 | Gdy mój CFO pyta o zwrot z licencji Terra.OS, **chcę** gotowy raport ROI z wyliczeniem zaoszczędzonych roboczogodzin, wygranych przetargów przypisanych do systemu i wzrostu win-rate YoY, **żeby** uzasadnić kontynuację subskrypcji i ewentualny upgrade do Enterprise. |

---

## 1.2 Customer Journey Map — Kierownik Przetargów

*Piotr, Katowice, firma budowlana 80 os., zarządza przetargami CPV 45112*

### Etap 1: ODKRYCIE BZP

| Element | Opis |
|---------|------|
| **Akcja** | Codziennie rano (7:00) manualnie przegląda BZP.gov.pl, TED.europa.eu, ewentualnie emailowe alerty. Otwiera 10-15 zakładek, kopiuje linki do Excela. |
| **Emocja** | 😩 Przytłoczenie, rutyna, FOMO (co jeśli przegapił?) |
| **Pain Point** | Brak filtrowania po CPV + wartości + regionie jednocześnie. BZP wyszukiwarka jest prymitywna. 45-60 min dziennie "zmarnowane" na skanowanie. |
| **Terra.OS Moment** | ✅ **Inteligentny feed przetargów** — automatyczne alerty dopasowane do profilu firmy (CPV, region, wartość, typ zamawiającego). Skrócenie do 10 min/dzień. Powiadomienie push/email z pre-oceną GO/NO-GO. |

### Etap 2: ANALIZA PRZETARGU

| Element | Opis |
|---------|------|
| **Akcja** | Pobiera SIWZ (często 200+ stron PDF), ręcznie szuka kryteriów, terminów, warunków udziału. Zaznacza markerem, przepisuje do Excela. Konsultuje z CTO czy firma spełnia warunki. |
| **Emocja** | 😤 Frustracja, ryzyko przeoczenia (art. 226 PZP — odrzucenie oferty), presja czasu |
| **Pain Point** | Analiza 1 SIWZ = 2-3h. Przy 15 przetargach/mies. = 30-45h tylko na analizę. Błędy ludzkie przy przepisywaniu danych. |
| **Terra.OS Moment** | ✅ **AI Parser SIWZ** — automatyczne wyciąganie: terminów, kryteriów oceny, warunków udziału, kluczowych klauzul ryzyka. Skrócenie do 20 min/SIWZ. Alert na potencjalne pułapki prawne. |

### Etap 3: KOSZTORYS

| Element | Opis |
|---------|------|
| **Akcja** | Przekazuje przedmiar do kosztorysanta. Czeka 3-5 dni. Kosztorysant używa Normy/Excel. Wielokrotne iteracje emailowe. Brak wersjonowania. |
| **Emocja** | 😰 Stres (deadline), niepewność (czy cena jest konkurencyjna?), silosowość komunikacji |
| **Pain Point** | Kosztorys = wąskie gardło firmy. Jeden kosztorysant obsługuje 4-5 firm jednocześnie. Błędy arytmetyczne w Excel. Ceny nieaktualne (SEKOCENBUD kwartalnie). |
| **Terra.OS Moment** | ✅ **Auto-kosztorys z KNR+SEKOCENBUD** — draft w 2h zamiast 3-5 dni. Real-time collaboration Piotr↔Magda. Wersjonowanie. Alerty na nieaktualne ceny. |

### Etap 4: DECYZJA GO/NO-GO

| Element | Opis |
|---------|------|
| **Akcja** | Meeting z prezesem (często bez danych). Decyzja intuicyjna lub oparta na "gut feeling". Brak systematycznego scoringu. |
| **Emocja** | 🤔 Niepewność, polityka wewnętrzna ("prezes chce, to składamy"), ryzyko złej decyzji |
| **Pain Point** | Brak obiektywnego frameworku GO/NO-GO. Firma składa za dużo słabych ofert zamiast mniej, ale dobrych. Win-rate 8-12% (branżowa średnia). |
| **Terra.OS Moment** | ✅ **GO/NO-GO Scorecard** — automatyczny scoring: szansa wygranej (ML model), marżowość, ryzyko płynności, dopasowanie do kompetencji. Rekomendacja z uzasadnieniem dla prezesa. |

### Etap 5: ZŁOŻENIE OFERTY

| Element | Opis |
|---------|------|
| **Akcja** | Kompletuje dokumenty (KRS, zaświadczenia ZUS/US, referencje, JEDZ). Tworzy formularz ofertowy. Upload na platformę zamawiającego (ePUAP, ezamowienia.gov.pl). Stres przed deadlinem. |
| **Emocja** | 😓 Ulga po złożeniu, ale też lęk ("czy czegoś nie zapomniałem?") |
| **Pain Point** | Zbieranie dokumentów = 2-4h. Duplikacja: te same zaświadczenia do każdej oferty. Ryzyko odrzucenia formalnego przez brakujący dokument. |
| **Terra.OS Moment** | ✅ **Document Vault + Pre-submission Checklist** — repozytorium aktualnych dokumentów firmy z alertami wygaśnięcia. Automatyczna lista kontrolna przed złożeniem. Integracja z ezamowienia.gov.pl API. |

---

## 1.3 Competitive Analysis — Feature Matrix

> Oceny 1-5: 1=brak/bardzo słabe, 5=doskonałe

| Feature / Narzędzie | **Excel/Białe tabelki** | **Procore** | **PlanRadar** | **Access/FileMaker** | **ChatGPT/Jasper** | **⭐ Terra.OS** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Monitorowanie BZP/TED** | 1 | 2 | 1 | 1 | 2 | **5** |
| **Parser SIWZ (AI)** | 1 | 1 | 1 | 1 | 3 | **5** |
| **Kosztorys KNR-compliant** | 3 | 2 | 1 | 3 | 2 | **5** |
| **Ceny SEKOCENBUD (auto-update)** | 1 | 1 | 1 | 1 | 1 | **5** |
| **Symulacja Monte Carlo** | 1 | 1 | 1 | 1 | 2 | **5** |
| **GO/NO-GO Scoring (ML)** | 1 | 2 | 1 | 1 | 2 | **5** |
| **PZP Compliance Check** | 1 | 1 | 1 | 1 | 2 | **5** |
| **Document Vault** | 2 | 4 | 3 | 2 | 1 | **4** |
| **Pipeline Dashboard** | 2 | 4 | 3 | 2 | 1 | **4** |
| **Field Management** | 1 | 5 | 5 | 2 | 1 | **2** |
| **Polska lokalizacja (język, prawo)** | 5 | 1 | 3 | 4 | 2 | **5** |
| **Cena (PL SMB-friendly)** | 5 | 1 | 3 | 4 | 3 | **4** |
| **Onboarding (czas do wartości)** | 5 | 1 | 3 | 2 | 4 | **4** |
| **Integracja ezamowienia.gov.pl** | 1 | 1 | 1 | 1 | 1 | **5** |
| **Branżowe AI (roboty ziemne)** | 1 | 1 | 1 | 1 | 2 | **5** |
| **SUMA (max 75)** | **30** | **27** | **25** | **27** | **28** | **73** |

### Wnioski z analizy konkurencji:

1. **Brak realnej konkurencji** w niszy PZP + AI + roboty ziemne w Polsce — Terra.OS nie ma bezpośredniego konkurenta.
2. **Status quo (Excel)** jest najgroźniejszym "konkurentem" — nie przez jakość, ale przez inercję i zero kosztu wejścia. Strategia: pokazuj czas zaoszczędzony, nie features.
3. **Procore** — zagrożenie długoterminowe (kapitał, brand), ale: $10k+/rok, brak PZP, brak polskiego wsparcia. Dla PL SMB nieosiągalny.
4. **ChatGPT** — ryzyko DIY ("sam sobie zbuduję"). Odpowiedź: domain-specific AI beats generic AI. Demonstracja: Terra.OS vs. ChatGPT na realnym SIWZ.

---

# 2. GO-TO-MARKET PLAN

## 2.1 Beta Acquisition Plan — Q3 2026 (3 klientów)

### Cel: 3 podpisane Beta Agreements do 30 września 2026

---

### 📧 Cold Email Sequence — Kierownik Przetargów

**Profil targetu:** Kierownik Przetargów / Kosztorysant w firmie budowlanej 20-200 os., CPV 45112, region Śląsk + Małopolska. LinkedIn + email firmowy.

---

#### EMAIL #1 — DAY 0: "Ból"
**Subject:** Ile czasu traci Pana zespół na analizę SIWZ?
**From:** Mateusz Jakimow, CEO, Terra.OS <mateusz@qa10.io>

```
Dzień dobry [Imię],

Pracując z firmami budowlanymi w Waszym segmencie CPV 45112 
zauważyłem, że analiza jednej SIWZ zajmuje zwykle 2-3 godziny.

Przy 15 przetargach miesięcznie to prawie cały tydzień roboczy 
tylko na "czytanie PDFów".

Terra.OS robi to w 20 minut.

Nie jestem pewny czy to problem który Pana dotyczy — 
dlatego pytam wprost.

Czy mogę wysłać 2-minutowe demo na konkretnym przetargu z BZP?

Pozdrawiam,
Mateusz Jakimow
CEO, Terra.OS (qa10.io)
+48 XXX XXX XXX
```

---

#### EMAIL #2 — DAY 4: "Dowód"
**Subject:** Re: Wynik testu na przetargu z Katowic [wyniki w środku]

```
[Imię],

Na wypadek gdyby pierwszy email zaginął — krótki dowód.

Wziąłem losowy przetarg z BZP sprzed tygodnia 
(roboty ziemne, Katowice, wartość ~2,3 mln PLN).

Terra.OS w 18 minut:
✅ Wyciągnął wszystkie terminy i kryteria
✅ Zidentyfikował 3 klauzule ryzyka w §12 SIWZ
✅ Wygenerował szkielet kosztorysu KNR
✅ Ocenił GO/NO-GO: 67% szansy na wygraną

Link do nagrania (2 min): [LINK]

Robimy zamknięty program beta — 3 firmy, 0 PLN przez 3 miesiące, 
w zamian za szczery feedback.

Interesuje Pana jedno rozmowa w tym tygodniu?

Mateusz
```

---

#### EMAIL #3 — DAY 9: "Ograniczenie"
**Subject:** Ostatnie miejsce beta — decyzja do piątku

```
[Imię],

Wiem, że jesteście zajęci — sezon przetargowy w pełni.

Dlatego krótko: zostało nam 1 miejsce w programie beta 
na region Śląsk/Małopolska.

Dwa poprzednie zajęły firmy z Gliwic i Krakowa.

Jeśli myśli Pan o usprawnieniu procesu ofertowania przed Q4 
(tradycyjnie gorący okres dla CPV 45112) — to dobry moment.

15 minut rozmowy → decyzja. Bez żadnych zobowiązań.

Czy pasuje Panu wtorek lub środa przyszłego tygodnia?

Mateusz Jakimow
CEO, Terra.OS

P.S. Firma z Gliwic po 2 tygodniach beta zaoszczędziła 
11h kosztorysanta na 4 przetargach. Chętnie opowiem jak.
```

---

### 📱 LinkedIn Targeting Strategy

**Parametry wyszukiwania Sales Navigator:**

| Parametr | Wartość |
|----------|---------|
| **Tytuł stanowiska** | "kierownik przetargów" OR "kosztorysant" OR "dział ofert" OR "manager kontraktów" |
| **Branża** | Construction, Civil Engineering |
| **Wielkość firmy** | 11-200 pracowników |
| **Lokalizacja** | Katowice, Gliwice, Sosnowiec, Kraków, Bielsko-Biała, Tychy (50km radius) |
| **Seniorność** | Mid, Senior, Manager, Director |
| **Keywords profilu** | "przetargi publiczne" OR "PZP" OR "SIWZ" OR "roboty ziemne" OR "CPV 45112" |

**Taktyka outreach LinkedIn:**
1. **Dzień 1:** Wyślij zaproszenie BEZ wiadomości (wyższy accept rate)
2. **Dzień 2-3 po akceptacji:** Wiadomość powitalna: *"Dziękuję za akceptację. Widzę że zajmuje się Pan przetargami — właśnie robimy beta Terra.OS (AI do PZP). Czy mógłbym wysłać 2-minutowe demo?"*
3. **Dzień 7 bez odpowiedzi:** Follow-up z konkretem: *"Nagrałem demo na przetargu z Katowic CPV 45112112-1 sprzed tygodnia. Zajęło 18 min vs. standardowe 2-3h. Czy warto pokazać?"*

**Cel:** 50 połączeń/tydzień → 30% akceptacja = 15 połączeń → 20% odpowiedź = 3 rozmowy/tydzień → 1 beta/miesiąc = 3 beta w Q3 ✅

---

### 🎥 Webinar Plan: "AI w przetargach robót ziemnych"

**Tytuł:** *"Jak wygrywać przetargi CPV 45112 używając AI — case study z beta Terra.OS"*

| Element | Szczegóły |
|---------|-----------|
| **Data** | Wrzesień 2026 (tydzień 2), Wtorek 10:00 |
| **Platforma** | Zoom Webinar (do 100 uczestników, recording) |
| **Czas trwania** | 60 minut + 15 min Q&A |
| **Target** | 50+ rejestracji, 30+ live, 3+ hot leads |
| **Rejestracja** | Landing page (qa10.io/webinar) + formularz z: imię, firma, wielkość, "ile przetargów/mies" |

**Agenda:**

| Czas | Segment | Prezenter |
|------|---------|-----------|
| 0:00-5:00 | Intro: "Dlaczego 88% ofert CPV 45112 przegrywa?" (statystyki BZP) | Mateusz Jakimow |
| 5:00-15:00 | Pain Point Deep Dive: Czas kosztorysanta, błędy SIWZ, brak GO/NO-GO | Mateusz |
| 15:00-30:00 | **Live Demo Terra.OS** — realny przetarg z BZP z tego tygodnia | Adrianna Kmieciak |
| 30:00-40:00 | Case Study beta: Firma z Gliwic (anonimowy) — wyniki 4 tygodnie | Mateusz |
| 40:00-50:00 | ROI Calculator — "Ile oszczędzasz przy Twoich liczbach" | Mateusz |
| 50:00-60:00 | Beta Program: Jak dołączyć, co dostają, harmonogram | Mateusz |
| 60:00-75:00 | Q&A | Oboje |

**CTA (Call to Action):**
- Podczas webinaru: ankieta Mentimeter ("Ile przetargów miesięcznie?")
- Po webinarze: email z recording + link do zapisu beta (3 miejsca, deadline 7 dni)
- Follow-up call ze wszystkimi którzy zostali >40 minut

**Promocja webinaru:**
- LinkedIn post (organic): 3 posty w tygodniu przed (teaser, speaker bio, statystyki BZP)
- Email do listy (jeśli istnieje) + cold outreach do 100 firm z CPV 45112 Śląsk+Małopolska
- Ewentualnie: post w grupach LinkedIn "Przetargi publiczne Polska", "Budownictwo PL"

---

## 2.2 Content Strategy — 12-tygodniowy plan LinkedIn

**Rytm:** 3 posty/tydzień (Poniedziałek + Środa + Piątek)
**Głos:** Ekspercki, ale ludzki. Dane + storytelling. Bez buzzwordów.
**Format mix:** 60% edukacja, 25% produkt/dowód, 15% firma/team

| Tydzień | Temat pon. | Temat śr. | Temat pt. |
|---------|-----------|----------|----------|
| **T1** | 📊 "Ile polskich firm budowlanych traci rocznie przez złe wyceny?" (dane BZP) | 🔍 "5 pułapek w SIWZ robót ziemnych których szukamy za Ciebie" | 👥 "Kim jest Piotr — kierownik przetargów którego narzędzia mamy zastąpić" |
| **T2** | ⏱️ "2h vs. 20 min — analiza SIWZ przed i po AI" (screencast) | 📐 "KNR, SEKOCENBUD i dlaczego Excel tu nie wystarczy" | 🎯 "GO/NO-GO: jak firmy Top 10% CPV 45112 decydują" |
| **T3** | 💡 "Art. 246 PZP — pułapka na kosztorysantów" (edukacja prawna) | 🤖 "Czym różni się Terra.OS od ChatGPT do przetargów?" | 📈 "Win-rate 8% vs. 23% — co robią inaczej firmy które wygrywają" |
| **T4** | 🗓️ "Q3 2026 — jakie przetargi CPV 45112 warto obserwować?" | 🧮 "Monte Carlo w wycenie robót ziemnych — przykład" | 🏗️ "Case: Jak kosztorysant zaoszczędził 11h w 2 tygodnie" (beta story) |
| **T5** | 🔔 "BZP vs. TED — gdzie szukać największych przetargów?" | 📋 "JEDZ — jak nie stracić przetargu przez błąd formalny" | 💬 "Q&A: Najczęstsze pytania o AI w przetargach" |
| **T6** | 🌍 "Jak Niemcy i Czechy cyfryzują przetargi budowlane?" | ⚙️ "OR-Tools w logistyce budowy — co to daje kierownikowi?" | 🧭 "Roadmapa Terra.OS na 2026 — co budujemy" |
| **T7** | 📉 "Dlaczego SMB traci do korporacji na przetargach publicznych" | 💰 "ROI z Terra.OS: liczymy na Twoich liczbach" | 🎤 Zapowiedź webinaru: "AI w przetargach CPV 45112" |
| **T8** | 🎥 Teaser demo: "18 minut na SIWZ z Katowic" (krótki video) | 📣 "Rejestruj się: webinar 'AI w przetargach' — [data]" | 📊 Infografika: "Anatomia wygrywającej oferty CPV 45112" |
| **T9** | 🔴 WEBINAR WEEK: Przypomnienie (jutro live!) | 🎬 Post-webinar: "Co powiedzieli uczestnicy" | 📝 "3 lekcje z webinaru o AI w przetargach" |
| **T10** | 🤝 "Zaczynamy beta — spotykamy 3 firmy z Śląska i Małopolski" | 🧱 "Czego nauczyliśmy się z pierwszych rozmów z firmami budowlanymi" | 💬 Testimonial (jeśli jest) lub behind-the-scenes |
| **T11** | 📈 "Jak mierzyć efektywność procesu przetargowego?" | 🔐 "RODO i dane przetargowe — jak to rozwiązujemy w Terra.OS" | 🛤️ "Enterprise roadmap: SSO, white-label, on-prem" |
| **T12** | 🏆 "Podsumowanie Q3: czego się nauczyliśmy jako startup" | 💡 "Największe zaskoczenie z beta: [insight]" | 🚀 "Co dalej: roadmapa Q4 i otwieramy zapisy Pro" |

**KPIs LinkedIn:**
- Followings CEO: +200/mies (target: 1000 do końca Q3)
- Engagement rate: >3% (benchmark SaaS LinkedIn: 1.5-2%)
- Leads z LinkedIn: 5+ qualified/mies

---

## 2.3 Pricing Justification & ROI Calculator

### ROI Calculator — Tier Starter (299 PLN/mies)

**Założenia bazowe (typowa firma SMB 50 os.):**

| Parametr | Wartość | Źródło |
|----------|---------|--------|
| Przetargi/miesiąc | 12 | Wywiad z personą |
| Czas analizy SIWZ (przed) | 2.5h/przetarg | Wywiad |
| Czas kosztorysu (przed) | 6h/przetarg | Wywiad |
| Czas składania dokumentów | 2h/przetarg | Wywiad |
| **Łączny czas/przetarg (przed)** | **10.5h** | |
| Stawka kosztorysanta | 65 PLN/h brutto | Rynek PL 2026 |
| Stawka kierownika przetargów | 75 PLN/h | Rynek PL 2026 |
| Win-rate przed Terra.OS | 10% | Branżowa średnia |

**Po wdrożeniu Terra.OS (Starter):**

| Parametr | Wartość | Redukcja |
|----------|---------|----------|
| Czas analizy SIWZ | 0.35h/przetarg | -86% |
| Czas kosztorysu | 2h/przetarg | -67% |
| Czas składania dokumentów | 0.75h/przetarg | -62% |
| **Łączny czas/przetarg (po)** | **3.1h** | **-70%** |
| Win-rate | 16% | +6pp (estymacja) |

**Wyliczenie ROI:**

```
OSZCZĘDNOŚĆ CZASU:
Zaoszczędzony czas = (10.5h - 3.1h) × 12 przetargów = 88.8h/mies
Wartość zaoszczędzonego czasu = 88.8h × 65 PLN = 5,772 PLN/mies

DODATKOWY PRZYCHÓD (z wyższego win-rate):
Średnia wartość kontraktu CPV 45112 (SMB): 800,000 PLN
Marża netto: 8%
Dodatkowe wygrane/mies: 12 × (16%-10%) = 0.72 kontraktu/mies
Dodatkowy zysk/mies: 0.72 × 800,000 PLN × 8% = 46,080 PLN/mies

KOSZT Terra.OS Starter: 299 PLN/mies

ROI = (5,772 + 46,080 - 299) / 299 = 17,300% 🚀

PAYBACK PERIOD: < 1 dzień roboczy
```

---

### ROI Calculator — Tier Pro (799 PLN/mies)

**Dodatkowe założenia Pro:**

| Feature Pro | Wartość dodana |
|-------------|----------------|
| Monte Carlo symulacje | Unikanie kontraktów stratnych: est. +2pp marży |
| Benchmark vs. rynek | Optymalizacja wycen: est. +3pp win-rate |
| Pipeline dashboard | Czas prezesa/managementu: -5h/mies |
| API integracja | Eliminacja podwójnego wprowadzania danych: -3h/mies |

```
OSZCZĘDNOŚĆ (Pro vs. Starter):
Dodatkowe zaoszczędzone godziny (zarząd): 5h × 75 PLN = 375 PLN/mies
Dodatkowe zaoszczędzone godziny (API): 3h × 65 PLN = 195 PLN/mies
Wzrost win-rate (+3pp vs. Starter): 0.72 × 800k × 8% = 46,080 PLN dodatkowych
Uniknięte straty (Monte Carlo): est. 1 kontrakt/rok × -2% marży × 1M = 20,000 PLN/rok = 1,667 PLN/mies

DODATKOWA WARTOŚĆ PRO vs. STARTER: ~48,317 PLN/mies
RÓŻNICA KOSZTU: 799 - 299 = 500 PLN/mies

ROI inkrementalny (Pro vs Starter): 9,563%
```

---

### Pricing Summary Table

| Tier | Miesięcznie | Rocznie (ACV) | Breakeven | ROI (czas) | ROI (czas+przychód) |
|------|-------------|---------------|-----------|------------|---------------------|
| **Starter** | 299 PLN | 3,588 PLN | < 1 dzień | 1,830% | 17,300% |
| **Pro** | 799 PLN | 9,588 PLN | < 2 dni | 722% | 6,050% |
| **Enterprise** | ~3,000 PLN | ~36,000 PLN | < 1 tydzień | est. 500%+ | est. 4,000%+ |
| | | | | | |
| **Portfel 10 Starter** | - | 35,880 PLN | - | - | - |
| **Portfel 10 Pro** | - | 95,880 PLN | - | - | - |
| **Mix (7S+3P)** | - | 54,072 PLN | - | - | - |

**Milestone ARR:**
- 10 klientów (mix): ~54k PLN ARR
- 50 klientów (mix): ~270k PLN ARR
- 100 klientów (mix): ~540k PLN ARR
- **1M PLN ARR target: ~185 klientów**

---

# 3. PRD — M7 Module 3: Logistyka OR-Tools

## Product Requirements Document
**Moduł:** M7 — Optymalizacja Logistyki Budowy
**Sub-moduł:** Module 3 — Harmonogramowanie Zasobów (OR-Tools)
**Wersja:** 1.0
**Status:** Draft — Review Required
**Owner:** Adrianna Kmieciak (CTO)
**Stakeholders:** Mateusz Jakimow (CEO), Beta Klienci (3 firmy)
**Target Release:** Q4 2026 (Sprint 14-16)

---

### 3.1 Problem Statement

#### Kontekst biznesowy
Kierownik budowy robót ziemnych zarządza jednocześnie: flotą sprzętu ciężkiego (3-15 maszyn), brygadami pracowniczymi (5-50 os.), dostawami materiałów i podwykonawcami. Harmonogramowanie odbywa się dziś w głowie lub na whiteboardzie.

#### Zidentyfikowane bóle (wywiad z personami, lipiec 2026)
1. **Przestoje sprzętu:** Koparka czeka na wywózkę, wywrotka czeka na koparkę — brak synchronizacji = 15-25% czasu idle, koszt 800-2,500 PLN/h/maszyna
2. **Przeplanowywanie po zdarzeniach:** Deszcz, awaria, zmiana projektu → ręczne przesuwanie harmonogramu = 2-4h/zdarzenie, błędy kaskadowe
3. **Overcommitment zasobów:** Ten sam operator/maszyna przypisany do dwóch zadań jednocześnie — konflikty wykrywane za późno
4. **Brak widoczności:** Podwykonawca nie wie kiedy może wejść na teren → konflikty na placu budowy, przestoje
5. **Brak optimum kosztowego:** Harmonogram tworzony "żeby zdążyć", nie żeby minimalizować koszty idle i overtime

#### Quantified Pain (estymacja)
- Projekt 3-miesięczny roboty ziemne 500k PLN: ~8-12% wartości traci się na nieefektywności logistycznej
- = 40,000-60,000 PLN strat na 1 projekcie
- Firma z 5 projektami/rok: 200,000-300,000 PLN strat możliwych do odzyskania

---

### 3.2 User Stories — Top 5 (z Kryteriami Akceptacji)

---

#### US-1: Automatyczne generowanie harmonogramu
**Jako** Kierownik Budowy,
**chcę** wygenerować optymalny harmonogram pracy maszyn i brygad na podstawie listy zadań i dostępnych zasobów,
**żeby** zminimalizować przestoje i dotrzymać terminu kontraktu.

**Kryteria Akceptacji (AC):**
- [ ] AC-1.1: System przyjmuje listę zadań (nazwa, czas trwania, wymagany sprzęt, wymagana brygada, zależności predecessor/successor)
- [ ] AC-1.2: System przyjmuje listę zasobów (maszyny: typ, dostępność, koszty; pracownicy: kwalifikacje, dostępność, koszt/h)
- [ ] AC-1.3: OR-Tools generuje harmonogram w <30 sekund dla projektu ≤100 zadań, ≤20 zasobów
- [ ] AC-1.4: Harmonogram wizualizowany jako Gantt chart na ResourcesPage
- [ ] AC-1.5: Koszt całkowity harmonogramu wyświetlany (suma: praca + sprzęt + overtime)
- [ ] AC-1.6: System informuje jeśli problem jest INFEASIBLE (np. za mało sprzętu) z wyjaśnieniem dlaczego

---

#### US-2: Wykrywanie i rozwiązywanie konfliktów zasobów
**Jako** Kierownik Budowy,
**chcę** być natychmiast informowany gdy dwa zadania potrzebują tego samego zasobu w tym samym czasie,
**żeby** eliminować konflikty zanim spowodują przestoje na budowie.

**Kryteria Akceptacji:**
- [ ] AC-2.1: System wykrywa wszystkie konflikty zasobów w harmonogramie w czasie rzeczywistym (przy każdej zmianie)
- [ ] AC-2.2: Konflikty wyświetlane jako czerwone alerty na Gantt chart z opisem ("Koparka CAT 320 — conflict: Zadanie A vs. Zadanie B, 14:00-16:00")
- [ ] AC-2.3: Przycisk "Auto-resolve" próbuje przesunąć jeden z konfliktujących tasków z zachowaniem zależności
- [ ] AC-2.4: Jeśli auto-resolve niemożliwy — proponuje 3 alternatywne rozwiązania z kosztami
- [ ] AC-2.5: Historia zmian harmonogramu (audit log) dostępna

---

#### US-3: Replanning po zdarzeniu losowym
**Jako** Kierownik Budowy,
**chcę** po zgłoszeniu awarii maszyny lub opóźnienia dostawy automatycznie przeplanować pozostałe zadania,
**żeby** zminimalizować wpływ zdarzenia na termin całego projektu.

**Kryteria Akceptacji:**
- [ ] AC-3.1: Użytkownik może zgłosić zdarzenie: awaria_maszyny | opóźnienie_dostawy | złe_warunki_pogodowe | absencja_pracownika
- [ ] AC-3.2: Dla każdego zdarzenia: czas trwania problemu (w godzinach/dniach), dotknięty zasób
- [ ] AC-3.3: System w <60s prezentuje nowy optymalny harmonogram dla pozostałych zadań
- [ ] AC-3.4: Nowy harmonogram pokazuje: nowa data końca, zmiana kosztu (jeśli overtime), lista przesuniętych zadań
- [ ] AC-3.5: Użytkownik może zaakceptować lub odrzucić replan (powrót do poprzedniego)
- [ ] AC-3.6: Automatyczny alert do podwykonawców (email/SMS) jeśli ich zadanie zostało przesunięte >1 dzień

---

#### US-4: Multi-projekt widok zasobów
**Jako** Kierownik Floty / Dyrektor Operacyjny,
**chcę** widzieć zaangażowanie wszystkich maszyn i kluczowych pracowników we wszystkich aktywnych projektach jednocześnie,
**żeby** nie przydzielać tego samego sprzętu do dwóch projektów równocześnie.

**Kryteria Akceptacji:**
- [ ] AC-4.1: ResourcesPage wyświetla timeline wszystkich zasobów × wszystkich projektów (widok tygodniowy/miesięczny)
- [ ] AC-4.2: Filtrowanie po: typie zasobu, projekcie, statusie (dostępny/zajęty/awaria)
- [ ] AC-4.3: Kolor kodowanie: zielony=dostępny, niebieski=zajęty, czerwony=konflikt, szary=awaria/urlop
- [ ] AC-4.4: Drag&drop przenoszenie zadania między projektami z natychmiastowym wykryciem konfliktów
- [ ] AC-4.5: Export widoku do PDF (raport dla właściciela/klienta)

---

#### US-5: Optymalizacja kosztów harmonogramu
**Jako** Kierownik Budowy,
**chcę** porównać kilka wariantów harmonogramu (szybki vs. tani vs. zbalansowany) i wybrać najlepszy dla moich celów,
**żeby** świadomie decydować o kompromisie czas vs. koszt.

**Kryteria Akceptacji:**
- [ ] AC-5.1: PlanPage oferuje 3 tryby optymalizacji: "Minimize Duration", "Minimize Cost", "Balanced"
- [ ] AC-5.2: Dla każdego trybu — osobna propozycja harmonogramu z podsumowaniem: data końca, koszt całkowity, % idle sprzętu
- [ ] AC-5.3: Wykres Pareto (czas vs. koszt) dla wygenerowanych rozwiązań
- [ ] AC-5.4: Użytkownik może ręcznie przesuwać slider "time/cost tradeoff" i widzieć aktualizację w real-time
- [ ] AC-5.5: Wybrany harmonogram zapisywany jako "Baseline" — kolejne wersje porównywane do baseline

---

### 3.3 Success Metrics

| Metryka | Baseline (przed) | Target M7 (3 mies. po wdrożeniu) | Metoda Pomiaru |
|---------|-----------------|----------------------------------|----------------|
| **Czas planowania harmonogramu** | 3-5h/projekt | <30 min/projekt (-90%) | In-app time tracking |
| **% idle time sprzętu** | 20-25% | <12% | Raporty z maszyn (jeśli GPS) lub self-report |
| **Konflikty zasobów wykryte przez system (vs. na placu)** | 0% (wszystkie na placu) | >80% wykrytych pre-emptively | Incident log |
| **Czas replanningu po zdarzeniu** | 2-4h | <15 min | In-app time tracking |
| **NPS modułu logistyki** | N/A (nowy) | >40 | In-app survey po 30 dniach |
| **Feature adoption** | N/A | >60% aktywnych userów korzysta z OR-Tools | Mixpanel/Posthog events |
| **Retencja 90-dniowa (Terra.OS ogółem)** | Baseline | >85% | Subscription data |

---

### 3.4 Non-Goals — Czego NIE robimy w M7

| # | Non-Goal | Dlaczego |
|---|----------|---------|
| NG-1 | **IoT integracja z maszynami** (GPS tracker, telematyka) | Osobny moduł M9 — zbyt złożone na M7 |
| NG-2 | **Automatyczne zamawianie materiałów** (ERP/SCM) | Wymaga integracji z zewnętrznymi systemami — M10+ |
| NG-3 | **Płatności i rozliczenia podwykonawców** | Moduł finansowy — osobna ścieżka, inne persony |
| NG-4 | **BIM integracja** (Autodesk, Revit) | Złożoność techniczna, nisza w niszy — post-Series A |
| NG-5 | **Optymalizacja tras transportu** (VRP solver) | Osobny solver, requires GPS data — M9 |
| NG-6 | **Multi-tenant flota (leasing/wynajem)** | Edge case — <5% firm beta ma zewnętrzną flotę |
| NG-7 | **Mobile app offline** | PWA offline w M8 — priorytet po M7 stabilności |

---

### 3.5 Technical Requirements — OR-Tools Constraints

#### Solver Configuration

```python
# OR-Tools CP-SAT Solver Setup
from ortools.sat.python import cp_model

# Model parameters
MAX_TASKS = 200           # Hard limit M7
MAX_RESOURCES = 30        # Maszyny + brygady
HORIZON_DAYS = 180        # Max projekt 6 mies.
SOLVER_TIME_LIMIT = 30    # sekund (SLA dla UI)
SOLVER_NUM_WORKERS = 4    # CPU threads

# Objective weights (konfigurowalny per tryb)
WEIGHT_MAKESPAN = 0.6     # Minimize duration (default balanced)
WEIGHT_COST = 0.4         # Minimize cost (default balanced)
```

#### Constraints wymagane (muszą być zaimplementowane):

| ID | Constraint | Priorytet | Opis |
|----|-----------|-----------|------|
| C-01 | No-overlap resource | P0 | Jeden zasób = jedno zadanie w danym czasie |
| C-02 | Precedence (FS/SS/FF/SF) | P0 | Zależności Finish-Start, Start-Start etc. |
| C-03 | Resource availability windows | P0 | Maszyny/ludzie mają okna dostępności (np. 6:00-18:00 pn-pt) |
| C-04 | Fixed deadlines | P0 | Milestone deadlines nie do przekroczenia |
| C-05 | Skill matching | P1 | Zadanie wymaga konkretnych kwalifikacji (operator klasa III) |
| C-06 | Min/max crew size | P1 | Zadanie wymaga min 2 pracowników, max 5 |
| C-07 | Overtime modeling | P1 | Overtime możliwy z kosztem ×1.5, max 2h/dzień |
| C-08 | Weather windows | P2 | Niektóre zadania: no-go przy opadach (z IMGW API) |
| C-09 | Multi-mode tasks | P2 | Jedno zadanie można wykonać różnym sprzętem (różny czas/koszt) |
| C-10 | Buffer time | P2 | Minimalny czas między zadaniami tego samego zasobu |

#### Tech Stack M7:
- **Backend:** Python 3.11, FastAPI, OR-Tools 9.x (CP-SAT)
- **Database:** PostgreSQL (harmonogramy), Redis (cache solverow)
- **Frontend:** React + TypeScript, Gantt: dhtmlx-gantt lub custom D3
- **Solver API:** Async job queue (Celery/Redis), webhook na ukończenie
- **Tests:** pytest + property-based tests (Hypothesis) dla constraint correctness

---

### 3.6 UI Requirements

#### ResourcesPage — Wireframe Description

```
┌─────────────────────────────────────────────────────────────────┐
│  RESOURCES                        [+ Add Resource] [Export PDF] │
├──────────────┬──────────────────────────────────────────────────┤
│ FILTERS      │  TIMELINE VIEW          Week: [◀] 14-20 Jul [▶]  │
│ □ Maszyny    ├─────────┬────┬────┬────┬────┬────┬──────────────┤
│ □ Brygady    │ Resource│ Pn │ Wt │ Sr │ Cz │ Pt │ Sb │ Nd      │
│ □ Konflikt   ├─────────┼────┼────┼────┼────┼────┼────┼─────────┤
│              │ CAT 320 │████│████│░░░│████│████│    │         │
│ PROJECT      │ CAT 336 │████│ !! │████│████│░░░│    │         │
│ ▼ Projekt A  │ Brig.1  │████│████│████│░░░│████│    │         │
│ ▼ Projekt B  │ Brig.2  │░░░│████│████│████│░░░│    │         │
│              ├─────────┴────┴────┴────┴────┴────┴────┴─────────┤
│ LEGEND       │  ████ Zajęty   ░░░ Dostępny  !! Konflikt         │
│ ████ Zajęty  │                                                   │
│ ░░░ Wolny    │  [Click on conflict !! to see details & resolve]  │
│ !! Konflikt  │                                                   │
└──────────────┴───────────────────────────────────────────────────┘
```

#### PlanPage — Wireframe Description

```
┌─────────────────────────────────────────────────────────────────┐
│  PLAN: Projekt A — Roboty ziemne faza 1         [Run Optimizer] │
├─────────────────────────────────────────────────────────────────┤
│  OPTIMIZATION MODE:  ◉ Balanced  ○ Min Duration  ○ Min Cost    │
│  TIME/COST SLIDER:   [Speed ◀────────●──────── Cost ▶]          │
├─────────────────┬───────────────────────────────────────────────┤
│  VARIANTS       │  GANTT CHART                                   │
│                 │  Zadanie        Jul  Aug  Sep                  │
│  A: Balanced    │  ├─ Wykop K1   ███                            │
│  End: 15 Sep    │  ├─ Wywóz gr.      ██                         │
│  Cost: 485k PLN │  ├─ Zasypanie         ███                     │
│  Idle: 11%      │  └─ Zagęszcz.            ██                   │
│                 │                                                 │
│  B: Min Cost    │  [▶ Play animation]  [📌 Set as Baseline]      │
│  End: 28 Sep    ├───────────────────────────────────────────────┤
│  Cost: 421k PLN │  PARETO CHART: Time vs. Cost                   │
│  Idle: 8%       │  Cost                                          │
│                 │  500k │  •A                                    │
│  C: Min Time    │  450k │     •C                                 │
│  End: 01 Sep    │  400k │  •B                                    │
│  Cost: 531k PLN │       └──────────────── Time                  │
│  Idle: 19%      │        1 Sep  15 Sep  28 Sep                  │
└─────────────────┴───────────────────────────────────────────────┘
```

---

### 3.7 Definition of Done

| # | Kryterium | Weryfikacja |
|---|-----------|------------|
| DoD-1 | Wszystkie 5 User Stories zaimplementowane z pełnymi AC | Demo na review meeting |
| DoD-2 | OR-Tools solver działa <30s dla max projektu (100 zadań, 20 zasobów) | Benchmark test automated |
| DoD-3 | Unit tests coverage ≥80% dla modelu solverowego | CI/CD raport |
| DoD-4 | Brak P0/P1 bugów otwartych | Jira/Linear board |
| DoD-5 | ResourcesPage + PlanPage zaimplementowane wg wireframes | Design review z CTO |
| DoD-6 | 2 beta klientów przetestowało moduł z pozytywnym feedbackiem | NPS ≥7/10 |
| DoD-7 | Dokumentacja API (OpenAPI spec) dla logistyki | Swagger endpoint dostępny |
| DoD-8 | RODO compliance: dane harmonogramów nie opuszczają EU datacenter | Security review |
| DoD-9 | Performance: Gantt chart płynny dla 200 zadań (60fps) | Lighthouse/Profiler |
| DoD-10 | Rollback plan: feature flag do wyłączenia M7 bez restartu aplikacji | DevOps review |

---

# 4. ENTERPRISE ROADMAP

## 4.1 Enterprise Features Priority List

> Kontekst: Terra.OS enterprise = firmy budowlane 200+ os., grupy kapitałowe, spółki Skarbu Państwa (PSE, PKP, GDDKiA jako zamawiający, nie jako klient — ale ich dostawcy/wykonawcy)

### Priority Matrix

| Feature | Business Value | Dev Effort | Priority | Target Quarter |
|---------|---------------|------------|----------|----------------|
| **SSO/SAML 2.0** | Bardzo wysoki | Średni | P0 | Q1 2027 |
| **Role-Based Access Control (RBAC)** | Bardzo wysoki | Średni | P0 | Q4 2026 |
| **Audit Log (pełny)** | Wysoki | Niski | P0 | Q4 2026 |
| **SCIM 2.0 (user provisioning)** | Wysoki | Średni | P1 | Q1 2027 |
| **White-label** | Średni | Wysoki | P1 | Q2 2027 |
| **On-premise / Private Cloud** | Wysoki | Bardzo wysoki | P1 | Q2 2027 |
| **Data Residency (EU-only)** | Wysoki | Średni | P1 | Q1 2027 |
| **Custom SLA (99.9% uptime)** | Wysoki | Niski | P0 | Q4 2026 |
| **Dedykowany CSM** | Wysoki | Niski (people) | P0 | Q4 2026 |
| **Multi-tenant (holding/group)** | Wysoki | Wysoki | P2 | Q3 2027 |
| **Custom Reporting / BI** | Średni | Wysoki | P2 | Q3 2027 |
| **API (pełne REST/webhooks)** | Bardzo wysoki | Wysoki | P1 | Q1 2027 |
| **RODO/DPA Agreement** | Wymagany prawnie | Niski | P0 | Q4 2026 |

---

### Słownik Enterprise Features dla Budownictwa B2B w Polsce

| Feature | Co to znaczy w praktyce dla polskiej firmy budowlanej |
|---------|-------------------------------------------------------|
| **SSO/SAML 2.0** | Pracownik loguje się przez swoje firmowe konto Microsoft/Google (Active Directory). Zero osobnych haseł. Wymagane przez działy IT dużych firm ("musi być przez nasz IdP"). Blocker dla sprzedaży Enterprise. |
| **SCIM 2.0** | Gdy pracownik odchodzi z firmy → automatycznie traci dostęp do Terra.OS. Gdy nowy pracownik przychodzi → automatycznie dostaje właściwe uprawnienia. Kluczowe dla firm 200+ os. z rotacją. |
| **White-label** | Firma budowlana "Kowalski Budownictwo" widzi swoje logo zamiast Terra.OS. Ważne dla grup kapitałowych które chcą "własne narzędzie" w oczach spółek córek lub dla partnerów/resellerów. |
| **On-premise** | Serwery Terra.OS zainstalowane w serwerowni klienta lub prywatnej chmurze. Kluczowe dla: spółek z udziałem SP, firm z przetargów obronnych, firm z politykami "dane nie opuszczają firmy". |
| **Data Residency** | Dane przechowywane wyłącznie w Polsce lub UE. Wymagane przez DPO firm które mają restrykcyjną interpretację RODO. "Hosting w AWS Frankfurt" zwykle wystarczy dla 90% firm. |
| **RBAC** | Prezes widzi wszystko, kierownik widzi tylko swoje projekty, kosztorysant widzi tylko kosztorysy (nie dane finansowe klientów). Granularne uprawnienia. Wymagane przez każdą firmę 50+ os. |
| **Audit Log** | Kto co zmienił i kiedy. "Kto zmienił cenę w kosztorysie z 450k na 420k dwa dni przed złożeniem?" Krytyczne dla firm z ISO 9001, wewnętrznych kontroli i due diligence. |
| **Custom SLA** | Umowna gwarancja dostępności systemu (np. 99.9% = <8.7h downtime/rok). Z karami umownymi. Wymagane przez działy prawne dużych klientów przy podpisywaniu umów Enterprise. |

---

## 4.2 Series A Readiness Checklist

### Wymagane Metryki do Rozmów z Inwestorami

| Metryka | Definicja | Target (pre-Series A) | Red Flag |
|---------|-----------|----------------------|----------|
| **ARR** | Annual Recurring Revenue | **≥ 1,000,000 PLN** (~250k USD) | <500k PLN |
| **MoM Growth** | Month-over-month ARR growth | **≥ 15%** | <8% |
| **Churn Rate (monthly)** | % ARR utracone/mies | **< 2%** | >5% |
| **NPS** | Net Promoter Score | **≥ 40** | <20 |
| **DAU/MAU** | Engagement ratio | **≥ 40%** | <20% |
| **Payback Period** | Mies. do odzyskania CAC | **< 12 miesięcy** | >18 mies. |
| **LTV/CAC** | Customer lifetime value / acq. cost | **≥ 3:1** | <2:1 |
| **# Paying Customers** | Aktywne płacące konta | **≥ 50** | <30 |
| **Logo Churn** | % klientów odchodzących/rok | **< 15%** | >25% |
| **Gross Margin** | Marża brutto SaaS | **≥ 70%** | <60% |
| **Magic Number** | S&M efficiency | **≥ 0.75** | <0.5 |

---

### Data Room Struktura

```
📁 Terra.OS Data Room — Series A
│
├── 📁 01_Company
│   ├── KRS, NIP, wpis do rejestru (QA10 sp. z o.o.)
│   ├── Cap table (aktualna, post-beta)
│   ├── Shareholders agreement
│   └── Org chart
│
├── 📁 02_Financials
│   ├── P&L last 12 months (miesięcznie)
│   ├── Balance sheet
│   ├── Cash flow statement
│   ├── ARR bridge (MRR waterfall chart)
│   ├── Unit economics (CAC, LTV, payback per segment)
│   └── Financial model 36-mies. (assumptions visible)
│
├── 📁 03_Product
│   ├── Product roadmap (public version)
│   ├── Tech architecture diagram
│   ├── Security & compliance summary
│   ├── IP ownership (patents, trademarks)
│   └── PRD dokumenty (M1-M7)
│
├── 📁 04_Commercial
│   ├── Customer list (anonymized → deanon for investors NDA)
│   ├── Sample customer contracts
│   ├── Pipeline CRM export (Hubspot/Pipedrive)
│   ├── Churn analysis (każdy odejście z powodami)
│   └── Reference customers (do rozmów z VC)
│
├── 📁 05_Market
│   ├── TAM/SAM/SOM analysis
│   ├── Competitive landscape
│   ├── Market research (wywiady z personami)
│   └── Industry reports (BZP statistics, GUS budownictwo)
│
├── 📁 06_Team
│   ├── Founder CVs (Mateusz Jakimow, Adrianna Kmieciak)
│   ├── Key hire plan (Series A roles)
│   ├── Employment agreements
│   └── Advisor agreements
│
├── 📁 07_Legal
│   ├── RODO/DPA documentation
│   ├── Terms of Service + Privacy Policy
│   ├── IP assignments (founder → company)
│   ├── No open source license conflicts
│   └── NDA template
│
└── 📁 08_Tech_Due_Diligence
    ├── Code repository access (private, controlled)
    ├── Security audit (jeśli dostępny)
    ├── Infrastructure cost breakdown
    ├── Scalability analysis
    └── Tech debt log
```

---

### Milestone: 50 Klientów + 1M PLN ARR

**Mapa drogi do milestone:**

| Quarter | # Klientów (skum.) | MRR | ARR | Kluczowe działania |
|---------|-------------------|-----|-----|-------------------|
| **Q3 2026** | 3 (beta) | 0 PLN | 0 PLN | Beta acquisition, product-market fit |
| **Q4 2026** | 12 | ~6,500 PLN | ~78k PLN | Launch Pro, pierwsze płatne kontrakty |
| **Q1 2027** | 25 | ~14,000 PLN | ~168k PLN | Scale outbound, webinary, content |
| **Q2 2027** | 40 | ~25,000 PLN | ~300k PLN | First enterprise deals, Partner channel |
| **Q3 2027** | **55** | **~85,000 PLN** | **~1,020k PLN** | **🎯 MILESTONE: 50+ klientów, 1M ARR** |
| Q4 2027 | 75 | 120,000 PLN | 1,440k PLN | Series A close, expand team |

> Uwaga: Skok MRR w Q3 2027 zakłada 3-5 kontraktów Enterprise (avg. 3,000 PLN/mies.) dołączonych do ~50 SMB.

---

# 5. BETA PROGRAM PLAN

## 5.1 Kryteria Selekcji — 3 Beta Klientów

### Must-Have (wszystkie wymagane)

| Kryterium | Uzasadnienie |
|-----------|-------------|
| ✅ **Firma 20-200 pracowników** | Target segment — brak enterprise overhead, brak enterprise rigidity |
| ✅ **Aktywna działalność CPV 45112xxx** | Core use case — roboty ziemne, nie budownictwo ogólne |
| ✅ **Min. 8 przetargów/mies.** | Wystarczający wolumen do mierzenia wpływu |
| ✅ **Kosztorysant in-house lub dedykowany** | Muszą mieć kogoś kto będzie core userem modułu wyceny |
| ✅ **Chęć cotygodniowego feedbacku (30 min call)** | Kluczowe dla iteracji produktu |
| ✅ **Tech-savvy POC** (1 osoba, nie CEO) | Ktoś kto rzeczywiście używa narzędzi online, nie boi się nowego software |

### Should-Have (przynajmniej 2 z 3 klientów)

| Kryterium | Powód |
|-----------|-------|
| 🟡 Firma z regionu Śląsk LUB Małopolska | Łatwość dojazdu na sesje onsite w razie potrzeby |
| 🟡 Różna wielkość (np. 25 os. / 80 os. / 150 os.) | Pokrycie spektrum segmentu |
| 🟡 Jedno z nich "cyniczny realistyk" (nie early adopter) | Twardy feedback > entuzjazm |
| 🟡 Jedno z nich z doświadczeniem Procore/PlanRadar | Benchmark dla porównań |

### Nice-to-Have

| Kryterium |
|-----------|
| 🔵 Firma z projektem aktywnym (nie tylko przetargi, ale też realizacja) — pod przyszły moduł M7 |
| 🔵 Właściciel/prezes zaangażowany — przyszły case study / testimonial |
| 🔵 Firma z >50% kontraktów samorządowych (gminy, powiaty) — core PZP persona |

---

## 5.2 Beta Agreement — Główne Punkty

**Dokument:** Umowa Uczestnictwa w Programie Beta Terra.OS
**Strony:** QA10 sp. z o.o. ("Dostawca") ↔ [Firma] ("Uczestnik")
**Czas trwania:** 3 miesiące (data_start – data_start+90 dni)

| # | Punkt | Treść kluczowa |
|---|-------|----------------|
| 1 | **Dostęp bezpłatny** | Uczestnik otrzymuje dostęp do Terra.OS (plan Pro) bez opłat przez czas trwania beta. Po zakończeniu: oferta Pro z 30% rabatem na 12 mies. |
| 2 | **Zobowiązanie do feedbacku** | Uczestnik zobowiązuje się do: (a) cotygodniowego 30-min call z PM, (b) wypełnienia ankiet NPS/CSAT po każdym module, (c) zgłaszania bugów przez dedykowany kanał (Slack/Jira) |
| 3 | **Dane testowe** | Uczestnik może wprowadzać dane produkcyjne. Dostawca gwarantuje szyfrowanie AES-256, backup dzienny, hosting EU (AWS Frankfurt). |
| 4 | **Poufność** | Obie strony: NDA wzajemny, 3 lata. Uczestnik nie ujawnia funkcji beta publicznie bez zgody Dostawcy. |
| 5 | **Case Study** | Po zakończeniu beta, za zgodą Uczestnika, Dostawca może opublikować anonimizowany lub jawny case study z wynikami. Uczestnik ma prawo review i veto. |
| 6 | **Własność danych** | Wszystkie dane wprowadzone przez Uczestnika są własnością Uczestnika. Dostawca może używać zanonimizowanych, zagregowanych danych do trenowania modeli AI i benchmarku. |
| 7 | **SLA (beta)** | Best-effort. Brak gwarantowanego uptime. Planowane przestoje z 24h notice. Krytyczne bugi naprawiane w <48h. |
| 8 | **Zakończenie** | Każda ze stron może zakończyć uczestnictwo z 7-dniowym wypowiedzeniem. Dane Uczestnika dostępne do eksportu przez 30 dni po zakończeniu. |
| 9 | **Wyłączenie odpowiedzialności** | Oprogramowanie w wersji beta — Dostawca nie odpowiada za decyzje biznesowe podjęte na podstawie outputów systemu. Użytkownik weryfikuje wyniki przed złożeniem oferty. |
| 10 | **Prawo** | Prawo polskie. Sąd właściwy: Katowice. |

---

## 5.3 Onboarding Timeline

### Dzień 1 (Kick-off Call — 90 min)

| Agenda | Czas | Odpowiedzialny |
|--------|------|---------------|
| Welcome + cele beta programu | 10 min | CEO |
| Tech setup: konto, 2FA, pierwsze logowanie | 15 min | CTO |
| Import danych: profil firmy, lista zasobów, CPV | 20 min | CTO + Uczestnik |
| Live demo: analiza pierwszego przetargu z BZP | 25 min | CTO (screen share) |
| Q&A + ustalenie POC i kanału komunikacji (Slack) | 20 min | CEO |

**Deliverable Dzień 1:** Konto aktywne, profil firmy wypełniony, 1 przetarg załadowany

---

### Tydzień 1 (Dni 2-7)

| Dzień | Zadanie Uczestnika | Wsparcie QA10 |
|-------|--------------------|---------------|
| Dzień 2 | Analiza 3 przetargów przez Terra.OS (samodzielnie) | Dostępny na Slack |
| Dzień 3 | Wygenerowanie pierwszego kosztorysu auto-draft | Tutorial video (loom) |
| Dzień 4 | Wypełnienie ankiety "First Week" (5 pytań, Google Form) | Przypomnienie od PM |
| Dzień 5 | Call 30 min: pierwsze wrażenia, blokery, pytania | PM (Mateusz lub Adrianna) |
| Dzień 7 | Zadanie: użycie GO/NO-GO scorecard na realnym przetargu | Tutorial + Slack wsparcie |

**Deliverable Tydzień 1:** 5+ przetargów przeanalizowanych, 1 kosztorys wygenerowany, ankieta wypełniona

---

### Miesiąc 1 (Dni 8-30)

| Tydzień | Cel | KPI |
|---------|-----|-----|
| Tydzień 2 | Uczestnik samodzielnie używa Terra.OS do codziennej pracy (bez wsparcia QA10) | DAU ≥ 3 dni/tydzień |
| Tydzień 3 | Złożenie pierwszej oferty z kosztorysem Terra.OS | 1 przetarg end-to-end |
| Tydzień 4 | Review call 60 min: co działa, co nie, 3 najważniejsze feature requesty | Priorytetyzacja backlogu |

**Deliverable Miesiąc 1:**
- 15+ przetargów przeanalizowanych
- 3+ kosztorysy wygenerowane
- 1 oferta złożona z Terra.OS
- Lista 3-5 prioritetowych zmian przekazana do backlogs

---

## 5.4 Feedback Loop Design

### Framework: Ciągły Feedback → Tygodniowe Priorytety

```
📊 ZBIERANIE FEEDBACKU
         │
    ┌────▼──────────────────────────────────────────────────┐
    │  KANAŁY:                                               │
    │  • Slack (real-time): bugi, quick questions           │
    │  • In-app (Hotjar/Posthog): heatmaps, session replay  │
    │  • Intercom widget: "Give Feedback" po każdej akcji   │
    │  • Weekly call 30 min: głębszy kontekst, "why"        │
    │  • Monthly NPS survey: trend, ogólna satysfakcja      │
    └────────────────────────────────────────────────────────┘
         │
    ┌────▼──────────────────────────────────────────────────┐
    │  KATEGORYZACJA (PM robi co piątek):                   │
    │  Bug 🐛 → Linear issue, severity P0/P1/P2             │
    │  Feature Request 💡 → Feature backlog (Notion)        │
    │  UX Confusion 😕 → UX debt backlog                    │
    │  Positive Signal ⭐ → Case study bank                 │
    └────────────────────────────────────────────────────────┘
         │
    ┌────▼──────────────────────────────────────────────────┐
    │  PRIORYTETYZACJA (Monday planning):                   │
    │  ICE Score: Impact × Confidence × Ease / 1000        │
    │  Próg wejścia do sprintu: ICE ≥ 40                   │
    │  Zasada: jeśli 2/3 beta klientów zgłasza to samo     │
    │  → automatycznie P1 backlog                           │
    └────────────────────────────────────────────────────────┘
         │
    ┌────▼──────────────────────────────────────────────────┐
    │  ZAMKNIĘCIE PĘTLI (kluczowe dla retencji beta!):      │
    │  • Email do klienta: "Twoja sugestia [X] weszła do    │
    │    sprintu. Deploy w piątek."                         │
    │  • Monthly "What We Built From Your Feedback" digest  │
    │  • Tablica "Beta Champions" — kto zgłosił ile bugów  │
    └────────────────────────────────────────────────────────┘
```

### Metryki Feedback Loop

| Metryka | Target | Alarm |
|---------|--------|-------|
| Czas reakcji na buga P0 | <4h | >24h |
| Czas reakcji na buga P1 | <48h | >1 tydzień |
| % Feature requests z odpowiedzią | 100% | <80% |
| Czas od zgłoszenia do "w produkcji" (P1) | <2 tygodnie | >4 tygodnie |
| NPS beta (mies. 1) | ≥30 | <15 |
| NPS beta (mies. 3) | ≥50 | <30 |
| Retention beta klientów do końca (3 mies.) | 100% (3/3) | <2/3 |

---

## APPENDIX: Kluczowe Liczby Terra.OS — Quick Reference

| Parametr | Wartość |
|----------|---------|
| Target market (PL SMB budownictwo CPV 45112) | ~4,500 firm |
| TAM szacunkowy | ~162M PLN ARR (4,500 × 3,000 PLN avg) |
| SAM (Śląsk+Małopolska, 20-200 os.) | ~800 firm |
| SAM value | ~29M PLN ARR |
| SOM (3-letni target, 10% SAM) | 80 firm / ~2.9M PLN ARR |
| Pricing: Starter | 299 PLN/mies = 3,588 PLN ACV |
| Pricing: Pro | 799 PLN/mies = 9,588 PLN ACV |
| Pricing: Enterprise | ~3,000 PLN/mies = ~36,000 PLN ACV |
| Break-even (estymacja) | ~25 klientów Pro |
| Series A target | 1M PLN ARR (~55 klientów mix) |

---

*Dokument przygotowany przez: 🧭 Product Manager — Agency Agents dla QA10 sp. z o.o.*
*Data: Lipiec 2026 | Wersja: 1.0 | Status: DRAFT — Do Review przez Mateusz Jakimow i Adrianna Kmieciak*
