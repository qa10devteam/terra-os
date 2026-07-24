-- migration_005_company_kb.sql
-- Baza Wiedzy Firmy: referencje projektów + import stawek roboczych

-- 1. Referencje projektów zrealizowanych przez firmę
CREATE TABLE IF NOT EXISTS company_references (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    nazwa           TEXT NOT NULL,           -- nazwa zadania/kontraktu
    inwestor        TEXT,                    -- zamawiający
    lokalizacja     TEXT,
    rok_realizacji  INTEGER,
    wartosc_pln     NUMERIC(14,2),           -- wartość kontraktu
    cpv_codes       TEXT[],                  -- kody CPV
    zakres_md       TEXT,                    -- opis zakresu (markdown)
    certyfikaty     TEXT[],                  -- uprawnienia/certyfikaty
    zdjecia_urls    TEXT[],                  -- zdjęcia (opcjonalne)
    source_doc_id   UUID REFERENCES tender_documents(id) ON DELETE SET NULL,
    ai_summary      TEXT,                    -- streszczenie AI do wklejania w oferty
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_company_references_tenant ON company_references(tenant_id);
CREATE INDEX IF NOT EXISTS idx_company_references_cpv ON company_references USING GIN(cpv_codes);

-- 2. Import własnych stawek (z Excela lub ręcznie)
CREATE TABLE IF NOT EXISTS company_rates_import (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    source      TEXT DEFAULT 'manual',  -- 'excel_import' | 'manual' | 'kosztorys_sync'
    symbol      TEXT NOT NULL,
    nazwa       TEXT NOT NULL,
    jednostka   TEXT,
    typ_rms     CHAR(1),                -- R/M/S
    cena_netto  NUMERIC(12,4),
    katalog     TEXT,                   -- np. KNR 2-02, KSNR
    aktywna     BOOLEAN DEFAULT TRUE,
    import_batch UUID,                  -- grupuje wiersze z jednego importu
    uwagi       TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_company_rates_tenant ON company_rates_import(tenant_id, aktywna);

-- 3. Rozszerz owner_profile o nowe pola (jeśli jeszcze nie istnieją)
ALTER TABLE owner_profile
    ADD COLUMN IF NOT EXISTS nip                TEXT,
    ADD COLUMN IF NOT EXISTS regon              TEXT,
    ADD COLUMN IF NOT EXISTS krs                TEXT,
    ADD COLUMN IF NOT EXISTS adres              TEXT,
    ADD COLUMN IF NOT EXISTS uprawnienia        TEXT[],
    ADD COLUMN IF NOT EXISTS personel_kluczowy  JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS certyfikaty        TEXT[],
    ADD COLUMN IF NOT EXISTS ai_context_md      TEXT,   -- kontekst AI do wypełniania ofert
    ADD COLUMN IF NOT EXISTS logo_url           TEXT;
