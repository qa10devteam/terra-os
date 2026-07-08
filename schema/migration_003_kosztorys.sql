-- Migration 003: Moduł KOSZTORYS — tabele nagłówkowe i pozycje
-- Terra-OS · Sprint K2

BEGIN;

-- ─── Kosztorys nagłówek ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kosztorys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    tender_id       UUID REFERENCES tender(id) ON DELETE SET NULL,
    nazwa           TEXT NOT NULL,
    inwestor        TEXT,
    obiekt          TEXT,
    lokalizacja     TEXT,
    data_opracowania DATE DEFAULT CURRENT_DATE,
    status          TEXT NOT NULL DEFAULT 'draft',       -- draft|ready|submitted
    typ             TEXT NOT NULL DEFAULT 'ofertowy',    -- inwestorski|ofertowy|szczegolowy
    kwartalnr       INTEGER NOT NULL DEFAULT 2,
    kwartalrok      INTEGER NOT NULL DEFAULT 2026,
    -- Narzuty globalne (%)
    ko_r_pct        NUMERIC(6,2) NOT NULL DEFAULT 70.0,
    ko_s_pct        NUMERIC(6,2) NOT NULL DEFAULT 30.0,
    z_pct           NUMERIC(6,2) NOT NULL DEFAULT 12.5,
    kz_pct          NUMERIC(6,2) NOT NULL DEFAULT 7.1,
    vat_pct         NUMERIC(6,2) NOT NULL DEFAULT 23.0,
    -- Sumy (przeliczane przez engine)
    suma_r          NUMERIC(18,2) NOT NULL DEFAULT 0,
    suma_m          NUMERIC(18,2) NOT NULL DEFAULT 0,
    suma_s          NUMERIC(18,2) NOT NULL DEFAULT 0,
    suma_ko         NUMERIC(18,2) NOT NULL DEFAULT 0,
    suma_z          NUMERIC(18,2) NOT NULL DEFAULT 0,
    suma_kz         NUMERIC(18,2) NOT NULL DEFAULT 0,
    suma_netto      NUMERIC(18,2) NOT NULL DEFAULT 0,
    suma_vat        NUMERIC(18,2) NOT NULL DEFAULT 0,
    suma_brutto     NUMERIC(18,2) NOT NULL DEFAULT 0,
    -- Intelligence cache (wypełniany przez /intelligence/*)
    benchmark_percentile NUMERIC(5,2),
    win_probability      NUMERIC(5,4),
    anomaly_score        NUMERIC(8,4),
    price_forecast_q2    NUMERIC(18,2),
    intelligence_at      TIMESTAMPTZ,
    -- ATH export cache
    ath_xml         TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS
ALTER TABLE kosztorys ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON kosztorys
    USING (
        tenant_id = (NULLIF(current_setting('app.tenant_id', true), ''))::uuid
        OR current_setting('app.tenant_id', true) = ''
        OR current_setting('app.tenant_id', true) IS NULL
    )
    WITH CHECK (
        tenant_id = (NULLIF(current_setting('app.tenant_id', true), ''))::uuid
        OR current_setting('app.tenant_id', true) = ''
        OR current_setting('app.tenant_id', true) IS NULL
    );

-- ─── Działy kosztorysu ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kosztorys_dzial (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    kosztorys_id    UUID NOT NULL REFERENCES kosztorys(id) ON DELETE CASCADE,
    lp              INTEGER NOT NULL DEFAULT 1,
    nazwa           TEXT NOT NULL,
    -- Nadpisanie narzutów per dział (null = dziedzicz z nagłówka)
    ko_r_pct        NUMERIC(6,2),
    ko_s_pct        NUMERIC(6,2),
    z_pct           NUMERIC(6,2),
    kz_pct          NUMERIC(6,2),
    suma_r          NUMERIC(18,2) NOT NULL DEFAULT 0,
    suma_m          NUMERIC(18,2) NOT NULL DEFAULT 0,
    suma_s          NUMERIC(18,2) NOT NULL DEFAULT 0,
    suma_netto      NUMERIC(18,2) NOT NULL DEFAULT 0,
    cpv_hint        TEXT,   -- CPV kodu dla benchmark lookup
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE kosztorys_dzial ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON kosztorys_dzial
    USING (
        tenant_id = (NULLIF(current_setting('app.tenant_id', true), ''))::uuid
        OR current_setting('app.tenant_id', true) = ''
        OR current_setting('app.tenant_id', true) IS NULL
    )
    WITH CHECK (
        tenant_id = (NULLIF(current_setting('app.tenant_id', true), ''))::uuid
        OR current_setting('app.tenant_id', true) = ''
        OR current_setting('app.tenant_id', true) IS NULL
    );

-- ─── Pozycje kosztorysowe ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kosztorys_pozycja (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    kosztorys_id    UUID NOT NULL REFERENCES kosztorys(id) ON DELETE CASCADE,
    dzial_id        UUID REFERENCES kosztorys_dzial(id) ON DELETE SET NULL,
    lp              INTEGER NOT NULL DEFAULT 1,
    -- Kod katalogowy (KNR 2-02 0101-01 → katalog=KNR 2-02, nr=0101-01)
    kst_code        TEXT,
    katalog         TEXT,
    pozycja_nr      TEXT,
    opis            TEXT NOT NULL,
    jednostka       TEXT NOT NULL DEFAULT 'm2',
    ilosc           NUMERIC(18,4) NOT NULL DEFAULT 1,
    -- Ceny jednostkowe nakładów (r-g, jednostka materiału, m-g)
    r_jcena         NUMERIC(18,4) NOT NULL DEFAULT 0,
    m_jcena         NUMERIC(18,4) NOT NULL DEFAULT 0,
    s_jcena         NUMERIC(18,4) NOT NULL DEFAULT 0,
    -- Wartości nakładów (ilosc * jcena) — wyliczane
    r_total         NUMERIC(18,2) GENERATED ALWAYS AS (ilosc * r_jcena) STORED,
    m_total         NUMERIC(18,2) GENERATED ALWAYS AS (ilosc * m_jcena) STORED,
    s_total         NUMERIC(18,2) GENERATED ALWAYS AS (ilosc * s_jcena) STORED,
    -- Narzuty per pozycja (engine wypełnia)
    ko_total        NUMERIC(18,2) NOT NULL DEFAULT 0,
    z_total         NUMERIC(18,2) NOT NULL DEFAULT 0,
    kz_total        NUMERIC(18,2) NOT NULL DEFAULT 0,
    jcena_netto     NUMERIC(18,4) NOT NULL DEFAULT 0,   -- CJ netto
    wartosc_netto   NUMERIC(18,2) NOT NULL DEFAULT 0,   -- ilosc * jcena_netto
    -- Linki do ICB (do aktualizacji cen przy zmianie kwartału)
    icb_id_r        INTEGER,
    icb_id_m        INTEGER,
    icb_id_s        INTEGER,
    -- Anomaly flags (wypełniane przez intelligence)
    r_zscore        NUMERIC(8,4),
    m_zscore        NUMERIC(8,4),
    s_zscore        NUMERIC(8,4),
    is_anomaly      BOOLEAN NOT NULL DEFAULT FALSE,
    -- Misc
    uwagi           TEXT,
    ath_pozycja_xml TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE kosztorys_pozycja ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON kosztorys_pozycja
    USING (
        tenant_id = (NULLIF(current_setting('app.tenant_id', true), ''))::uuid
        OR current_setting('app.tenant_id', true) = ''
        OR current_setting('app.tenant_id', true) IS NULL
    )
    WITH CHECK (
        tenant_id = (NULLIF(current_setting('app.tenant_id', true), ''))::uuid
        OR current_setting('app.tenant_id', true) = ''
        OR current_setting('app.tenant_id', true) IS NULL
    );

-- ─── Składniki pozycji (R/M/S z ICB) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kosztorys_skladnik (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    pozycja_id  UUID NOT NULL REFERENCES kosztorys_pozycja(id) ON DELETE CASCADE,
    typ         CHAR(1) NOT NULL CHECK (typ IN ('R','M','S')),
    icb_id      INTEGER,
    symbol      TEXT,
    nazwa       TEXT NOT NULL,
    jednostka   TEXT NOT NULL,
    norma       NUMERIC(18,6) NOT NULL DEFAULT 0,   -- nakład na jednostkę
    cena_netto  NUMERIC(18,4) NOT NULL DEFAULT 0,   -- cena jednostkowa z ICB
    wartosc     NUMERIC(18,2) GENERATED ALWAYS AS (norma * cena_netto) STORED
);

ALTER TABLE kosztorys_skladnik ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON kosztorys_skladnik
    USING (
        tenant_id = (NULLIF(current_setting('app.tenant_id', true), ''))::uuid
        OR current_setting('app.tenant_id', true) = ''
        OR current_setting('app.tenant_id', true) IS NULL
    )
    WITH CHECK (
        tenant_id = (NULLIF(current_setting('app.tenant_id', true), ''))::uuid
        OR current_setting('app.tenant_id', true) = ''
        OR current_setting('app.tenant_id', true) IS NULL
    );

-- ─── Indeksy ──────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS ix_kosztorys_tenant   ON kosztorys(tenant_id);
CREATE INDEX IF NOT EXISTS ix_kosztorys_tender   ON kosztorys(tender_id);
CREATE INDEX IF NOT EXISTS ix_kosztorys_status   ON kosztorys(tenant_id, status);
CREATE INDEX IF NOT EXISTS ix_kdzial_kosztorys   ON kosztorys_dzial(kosztorys_id);
CREATE INDEX IF NOT EXISTS ix_kpoz_kosztorys     ON kosztorys_pozycja(kosztorys_id);
CREATE INDEX IF NOT EXISTS ix_kpoz_dzial         ON kosztorys_pozycja(dzial_id);
CREATE INDEX IF NOT EXISTS ix_kpoz_anomaly       ON kosztorys_pozycja(kosztorys_id, is_anomaly);
CREATE INDEX IF NOT EXISTS ix_kskladnik_poz      ON kosztorys_skladnik(pozycja_id);
CREATE INDEX IF NOT EXISTS ix_kskladnik_icb      ON kosztorys_skladnik(icb_id);

COMMIT;
