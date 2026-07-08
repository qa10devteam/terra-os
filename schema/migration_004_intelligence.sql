-- Migration 004: Intelligence cache tables — icb_forecast, material_alert
-- Terra-OS · Sprint K2

BEGIN;

-- ─── Cache prognoz cen ICB ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS icb_forecast (
    id              SERIAL PRIMARY KEY,
    icb_id          INTEGER NOT NULL,         -- powiązany id_ceny z icb_ceny_srednie
    symbol          TEXT,
    category        TEXT,
    typ_rms         CHAR(1) NOT NULL CHECK (typ_rms IN ('R','M','S')),
    forecast_quarter INTEGER NOT NULL CHECK (forecast_quarter BETWEEN 1 AND 4),
    forecast_year    INTEGER NOT NULL CHECK (forecast_year >= 2024),
    predicted_price  NUMERIC(12,4),
    lower_bound      NUMERIC(12,4),            -- p10
    upper_bound      NUMERIC(12,4),            -- p90
    model_name       TEXT NOT NULL DEFAULT 'linear_trend',
    mape_pct         NUMERIC(6,3),             -- backtested MAPE
    computed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (icb_id, forecast_quarter, forecast_year)
);

CREATE INDEX IF NOT EXISTS ix_icbfc_symbol    ON icb_forecast(symbol, forecast_year, forecast_quarter);
CREATE INDEX IF NOT EXISTS ix_icbfc_category  ON icb_forecast(category, typ_rms, forecast_year, forecast_quarter);

-- ─── Material risk alerts ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS material_alert (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    kosztorys_id    UUID REFERENCES kosztorys(id) ON DELETE CASCADE,
    icb_id          INTEGER,
    symbol          TEXT,
    nazwa           TEXT,
    baseline_price  NUMERIC(12,4) NOT NULL,   -- cena w momencie tworzenia kosztorysu
    current_price   NUMERIC(12,4) NOT NULL,   -- cena bieżąca (aktualizowana cyklicznie)
    change_pct      NUMERIC(8,2) NOT NULL,    -- (current-baseline)/baseline*100
    severity        TEXT NOT NULL DEFAULT 'low' CHECK (severity IN ('low','medium','high','critical')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ               -- null = niepotwierdzony
);

ALTER TABLE material_alert ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON material_alert
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

CREATE INDEX IF NOT EXISTS ix_matalt_tenant    ON material_alert(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_matalt_kosztorys ON material_alert(kosztorys_id, acknowledged_at);
CREATE INDEX IF NOT EXISTS ix_matalt_severity  ON material_alert(tenant_id, severity) WHERE acknowledged_at IS NULL;

COMMIT;
