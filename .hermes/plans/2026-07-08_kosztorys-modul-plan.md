# Moduł KOSZTORYS + INTELLIGENCE LAYER — Terra-OS

> **Status:** SPRINT K1 w toku  
> **Commit bazy:** `ac3beb0` (333 testy PASSED)

---

## Cel modułu

Terra-OS KOSZTORYS to nie kolejna kopia Normy Pro — to **intelligence layer** na 18 latach danych cenowych:

| Warstwa | Co robi |
|---------|---------|
| **Kosztorys** | CRUD pozycji R+M+S+Ko+Z, import/export ATH (Norma Pro), PDF |
| **Price Intelligence** | Trendy cen ICB 2008→2026, prognoza na +2/+4 kwartały |
| **Benchmark** | Oferta vs mediana rynku (CPV+region) z `market_results` |
| **Win Probability** | P(win) z quantile regression na 2504 wynikach real |
| **Anomaly Detection** | z-score pozycji vs ICB baza, Isolation Forest na całym kosztorysie |
| **Material Risk** | Alert: cena komponentu zmieniła się o >X% od złożenia oferty |

---

## Fakty z Discovery

### Dane w bazie
| Tabela | Wiersze | Co zawiera |
|--------|---------|------------|
| `icb_ceny_srednie` | 784 685 | R/M/S ceny Q1/2008→Q2/2026 |
| `historical_tenders` | 1 403 436 | Przetargi BZP+TED 2024-2025 |
| `market_results` | 2 504 | Wyniki z cenami (winning/lowest/highest/estimate) |
| `cpv_regional_benchmark` | **0** | Gotowa tabela — do wypełnienia |
| `bid_intelligence` | **0** | Gotowa tabela — do wypełnienia |
| `sekocenbud_items` | 23 725 | Dane SEKOCENBUD |
| `historical_bids` | 14 (demo) | Per-tenant oferty — do zasilenia przez użytkowników |

### Kluczowe obserwacje cenowe (ICB 2019→2026)
- Robocizna (R): **+81.6%** (28.69 → 52.09 zł/rbh)
- Sprzęt (S): **+154.5%** — najsilniejszy wzrost
- Materiały (M, exc. outliers): **+43.8%** (767 → 1100+ zł avg)
- Cement 2019→2023: **+82%**, następnie lekki spadek do 604 zł/t w 2026

### Benchmarki rynkowe (z `market_results`)
- Zwycięzca płaci **97.1% szacunki** zamawiającego (mediana)
- CPV 4523 (drogi): **88.5%** szacunki — silna konkurencja
- CPV 4526 (mosty), 4540 (wykończenia): **107–109%** szacunki — premium
- Sweet spot wygranej: 2.9–4.2% powyżej najtańszego oferenta

### State-of-art ML (literatura 2023-2025)
- **TFT (Temporal Fusion Transformer)**: MAPE 2–4% na kwartalnych cenach
- **XGBoost-SHAP**: dominuje w predykcji kosztów projektów
- **Features**: CPI, ceny energii, stali, kurs EUR/PLN, PMI budownictwo, lag_3/12
- **Bid rigging detection**: Huber & Imhof (2019) RF+screen tests — AUC 0.84–0.90
- **Kluczowe datasety FREE**: Eurostat `prc_ppi_con` (API), GUS BDL, World Bank Commodity Prices

### Luki rynkowe (szansa Terra-OS)
- Brak open-source PL datasetu z cenami per pozycja KNR — **my go mamy (ICB)**
- Brak API BCIS/SEKOCENBUD dla małych firm — **my to oferujemy**
- Słabe pokrycie Polski przez AI SaaS — **jedyna PL platforma**
- Brak zintegrowanego pipeline: forecast → benchmark → anomaly → win_prob

---

## Architektura

```
terra-os/
├── services/api/
│   ├── routers/
│   │   ├── kosztorys.py          ← CRUD kosztorys/działy/pozycje
│   │   ├── icb.py                ← ICB search API
│   │   └── intelligence.py       ← benchmark, forecast, win_prob, anomaly
│   └── services/
│       ├── kosztorys/
│       │   ├── engine.py         ← R+M+S+Ko+Z kalkulator
│       │   ├── ath_parser.py     ← ATH XML ↔ Python (Norma Pro)
│       │   ├── icb_service.py    ← wrapper icb_ceny_srednie
│       │   └── pdf_generator.py  ← WeasyPrint PDF
│       └── intelligence/
│           ├── benchmark.py      ← cpv_regional_benchmark builder
│           ├── forecaster.py     ← XGBoost/Prophet na ICB time series
│           ├── win_prob.py       ← quantile regression market_results
│           ├── anomaly.py        ← z-score + Isolation Forest
│           └── material_risk.py  ← alert gdy cena komponentu drożeje
├── terra_db/migrations/
│   ├── 003_kosztorys.sql         ← tabele kosztorysu
│   └── 004_intelligence.sql      ← modele, cache prognoz
└── apps/ui/src/pages/
    ├── kosztorys/                ← edytor + eksport
    └── intelligence/             ← dashboardy cenowe
```

---

## Schemat bazy — Kosztorys

```sql
-- Nagłówek
CREATE TABLE kosztorys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    tender_id UUID REFERENCES tender(id) ON DELETE SET NULL,
    nazwa TEXT NOT NULL,
    inwestor TEXT,
    obiekt TEXT,
    lokalizacja TEXT,
    data_opracowania DATE DEFAULT CURRENT_DATE,
    status TEXT DEFAULT 'draft',        -- draft|ready|submitted
    typ TEXT DEFAULT 'inwestorski',     -- inwestorski|ofertowy|szczegolowy
    kwartalnr INTEGER DEFAULT 2,
    kwartalrok INTEGER DEFAULT 2026,
    -- Narzuty globalne
    ko_r_pct NUMERIC(6,2) DEFAULT 60.0,
    ko_s_pct NUMERIC(6,2) DEFAULT 30.0,
    z_pct    NUMERIC(6,2) DEFAULT 10.0,
    kz_pct   NUMERIC(6,2) DEFAULT 7.0,
    vat_pct  NUMERIC(6,2) DEFAULT 23.0,
    -- Sumy
    suma_r       NUMERIC(18,2) DEFAULT 0,
    suma_m       NUMERIC(18,2) DEFAULT 0,
    suma_s       NUMERIC(18,2) DEFAULT 0,
    suma_ko      NUMERIC(18,2) DEFAULT 0,
    suma_z       NUMERIC(18,2) DEFAULT 0,
    suma_netto   NUMERIC(18,2) DEFAULT 0,
    suma_vat     NUMERIC(18,2) DEFAULT 0,
    suma_brutto  NUMERIC(18,2) DEFAULT 0,
    -- Intelligence cache
    benchmark_percentile NUMERIC(5,2),   -- gdzie jesteśmy w rozkładzie rynku
    win_probability      NUMERIC(5,2),   -- P(wygrania) z ML
    anomaly_score        NUMERIC(8,4),   -- Isolation Forest score
    price_forecast_q2    NUMERIC(18,2),  -- prognoza kosztu za 2 kwartały
    intelligence_at      TIMESTAMPTZ,    -- kiedy ostatnio przeliczono
    ath_xml TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Działy
CREATE TABLE kosztorys_dzial (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kosztorys_id UUID REFERENCES kosztorys(id) ON DELETE CASCADE,
    lp INTEGER NOT NULL DEFAULT 1,
    nazwa TEXT NOT NULL,
    ko_r_pct NUMERIC(6,2),    -- null = użyj z nagłówka
    ko_s_pct NUMERIC(6,2),
    z_pct    NUMERIC(6,2),
    suma_netto NUMERIC(18,2) DEFAULT 0,
    cpv_hint TEXT             -- CPV działu (do benchmark lookup)
);

-- Pozycje kosztorysowe
CREATE TABLE kosztorys_pozycja (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kosztorys_id UUID REFERENCES kosztorys(id) ON DELETE CASCADE,
    dzial_id UUID REFERENCES kosztorys_dzial(id) ON DELETE SET NULL,
    lp INTEGER NOT NULL DEFAULT 1,
    kst_code   TEXT,          -- "KNR 2-02 0101-01"
    katalog    TEXT,          -- "KNR 2-02"
    pozycja_nr TEXT,          -- "0101-01"
    opis       TEXT NOT NULL,
    jednostka  TEXT NOT NULL DEFAULT 'm2',
    ilosc      NUMERIC(18,4) NOT NULL DEFAULT 1,
    -- Ceny jednostkowe przed narzutami
    r_jcena NUMERIC(18,4) DEFAULT 0,
    m_jcena NUMERIC(18,4) DEFAULT 0,
    s_jcena NUMERIC(18,4) DEFAULT 0,
    -- Wyliczone (ilosc * jcena)
    r_total NUMERIC(18,2) GENERATED ALWAYS AS (ilosc * r_jcena) STORED,
    m_total NUMERIC(18,2) GENERATED ALWAYS AS (ilosc * m_jcena) STORED,
    s_total NUMERIC(18,2) GENERATED ALWAYS AS (ilosc * s_jcena) STORED,
    -- Narzuty (engine)
    ko_total   NUMERIC(18,2) DEFAULT 0,
    z_total    NUMERIC(18,2) DEFAULT 0,
    kz_total   NUMERIC(18,2) DEFAULT 0,
    jcena_netto   NUMERIC(18,4) DEFAULT 0,
    wartosc_netto NUMERIC(18,2) DEFAULT 0,
    -- Linki do ICB
    icb_id_r INTEGER,
    icb_id_m INTEGER,
    icb_id_s INTEGER,
    -- Anomaly
    r_zscore NUMERIC(8,4),    -- odchylenie od normy ICB
    m_zscore NUMERIC(8,4),
    s_zscore NUMERIC(8,4),
    is_anomaly BOOLEAN DEFAULT FALSE,
    uwagi TEXT,
    ath_pozycja_xml TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Składniki (R/M/S z ICB)
CREATE TABLE kosztorys_skladnik (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pozycja_id UUID REFERENCES kosztorys_pozycja(id) ON DELETE CASCADE,
    typ  CHAR(1) NOT NULL,
    icb_id   INTEGER,
    symbol   TEXT,
    nazwa    TEXT NOT NULL,
    jednostka TEXT NOT NULL,
    norma    NUMERIC(18,6) NOT NULL DEFAULT 0,
    cena_netto NUMERIC(18,4) NOT NULL DEFAULT 0,
    wartosc  NUMERIC(18,2) GENERATED ALWAYS AS (norma * cena_netto) STORED
);

-- Indeksy
CREATE INDEX ix_kosztorys_org    ON kosztorys(org_id);
CREATE INDEX ix_kosztorys_tender ON kosztorys(tender_id);
CREATE INDEX ix_kpoz_kosztorys   ON kosztorys_pozycja(kosztorys_id);
CREATE INDEX ix_kpoz_dzial       ON kosztorys_pozycja(dzial_id);
CREATE INDEX ix_kskladnik_poz    ON kosztorys_skladnik(pozycja_id);
```

---

## Schemat bazy — Intelligence (nowe tabele)

```sql
-- Cache prognoz cen ICB (odświeżany co kwartał)
CREATE TABLE icb_forecast (
    id SERIAL PRIMARY KEY,
    icb_id INTEGER NOT NULL,             -- FK do icb_ceny_srednie.id_ceny
    symbol TEXT,
    typ_rms CHAR(1),
    forecast_quarter INTEGER NOT NULL,   -- 1..4
    forecast_year    INTEGER NOT NULL,
    predicted_price  NUMERIC(12,4),
    lower_bound      NUMERIC(12,4),
    upper_bound      NUMERIC(12,4),
    model_name       TEXT DEFAULT 'prophet',
    computed_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (icb_id, forecast_quarter, forecast_year)
);

-- Material risk alerts
CREATE TABLE material_alert (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID REFERENCES organizations(id) ON DELETE CASCADE,
    kosztorys_id UUID REFERENCES kosztorys(id) ON DELETE CASCADE,
    icb_id INTEGER,
    symbol TEXT,
    nazwa TEXT,
    baseline_price  NUMERIC(12,4),   -- cena w chwili kosztorysu
    current_price   NUMERIC(12,4),   -- cena dzisiaj
    change_pct      NUMERIC(8,2),    -- (current-baseline)/baseline*100
    severity        TEXT,            -- low|medium|high|critical
    created_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ
);

-- Index
CREATE INDEX ix_matalt_org     ON material_alert(org_id, created_at DESC);
CREATE INDEX ix_icbfc_symbol   ON icb_forecast(symbol, forecast_year, forecast_quarter);
```

---

## Plan sprintów

### Sprint K1 — Fundament (DB + ICB + Engine + Benchmark seed)
**Fazy C1–C15 + I1–I3**

### Sprint K2 — ATH + API + PDF
**Fazy C16–C35**

### Sprint K3 — Intelligence API
**Fazy I4–I10 + C36–C45**

### Sprint K4 — Frontend + ZWIAD Integration
**Fazy C46–C60**

---

## Sprint K1 — Szczegóły

### C1: Migracja 003_kosztorys.sql
**Pliki:** `terra_db/migrations/003_kosztorys.sql`
Uruchom: `psql ... -f 003_kosztorys.sql`

### C2: Migracja 004_intelligence.sql
**Pliki:** `terra_db/migrations/004_intelligence.sql`

### C3: SQLAlchemy modele
**Plik:** `services/api/models/kosztorys.py`
Klasy: `Kosztorys`, `KosztorysDzial`, `KosztorysPozycja`, `KosztorysSkladnik`

### C4: Pydantic schemas
**Plik:** `services/api/schemas/kosztorys.py`

### C5: ICB Service
**Plik:** `services/api/services/kosztorys/icb_service.py`
- `search_icb(q, typ, quarter, limit)` — pg_trgm fuzzy
- `get_narzuty(quarter)` → Ko%/Z%/Kz%
- `get_regional_rate(nuts2, quarter)`

### C6: Engine kalkulacji
**Plik:** `services/api/services/kosztorys/engine.py`
- `calc_pozycja(poz, narzuty)` → Ko/Z/Kz/netto
- `recalc_kosztorys(id, db)` → update sum

### C7: Benchmark seed — wypełnij cpv_regional_benchmark
**Plik:** `services/api/services/intelligence/benchmark.py`
- Agreguj `market_results` → cpv5 × nuts2 × quarter
- Uzupełnij `icb_r_rate`, `icb_m_rate`, `icb_s_rate` z `icb_ceny_srednie`

### I1: ICB Price Forecasting (Prophet)
**Plik:** `services/api/services/intelligence/forecaster.py`
- Modele per `id_ceny` (kategorie materiałów)
- Prophet z `changepoint_prior_scale=0.3` (stability)
- Features: lag_1, lag_4, kwartał (sezonowość)
- Output → `icb_forecast` table
- Priorytet: top 100 materiałów wg częstości użycia

### I2: Win Probability (Quantile Regression)
**Plik:** `services/api/services/intelligence/win_prob.py`
- Z `market_results`: `winning_price/estimated_value` per CPV4 × nuts2
- Quantile regression → P10/P50/P90 (zakres bezpieczny, optymalny, ryzykowny)
- "Twoja oferta = 94% szacunki → percentyl 31% → P(win) ~62%"

### I3: Anomaly Detection
**Plik:** `services/api/services/intelligence/anomaly.py`
- Per pozycja: z-score vs ICB (kategoria + typ_rms + kwartał)
- Na całym kosztorysie: Isolation Forest (n_estimators=100)
- Threshold: |z| > 2.5 → is_anomaly = True

### C8–C10: API Router + testy
**Plik:** `services/api/routers/kosztorys.py`
Endpointy: GET/POST/PUT/DELETE kosztorys + działy + pozycje
Testy: 333+50 (50 nowych dla kosztorys)

---

## CPV → Działy automatyczne (starter mapping)

| CPV prefix | Dział kosztorysu |
|------------|-----------------|
| 45111 | Roboty rozbiórkowe i ziemne |
| 45112 | Roboty ziemne — wykopy, nasypy |
| 45113 | Place budowy |
| 45200 | Roboty budowlane konstrukcyjne |
| 45210 | Roboty budowlane — obiekty budowlane |
| 45223 | Konstrukcje stalowe i żelbetowe |
| 45261 | Roboty dekarskie |
| 45300 | Instalacje budowlane |
| 45310 | Roboty instalacyjne elektryczne |
| 45330 | Hydraulika, instalacje sanitarne |
| 45340 | Ogrodzenia, bariery, szlabany |
| 45400 | Roboty wykończeniowe |
| 45410 | Tynkowanie |
| 45420 | Stolarka |
| 45430 | Pokrycia podłóg i ścian |
| 45440 | Malarstwo i szklenie |
| 45500 | Wynajem maszyn z obsługą |

---

## Key metrics docelowe po wdrożeniu

| KPI | Target |
|-----|--------|
| Czas tworzenia kosztorysu (100 pozycji) | < 15 min (vs. 3h w Normie) |
| Dokładność benchmark (CPV+region) | MAPE < 8% |
| Dokładność forecast ICB (+2 kwartały) | MAPE < 5% |
| Win probability accuracy | AUC > 0.75 |
| Anomaly precision (pozycje z błędami) | > 85% |
| Import ATH z Normy | 100% roundtrip |
