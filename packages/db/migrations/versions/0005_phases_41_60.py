"""Fazy 41-60: BZP docs, TED, GUS, KRS, Excel imports, ATH kosztorys,
comments, email config, webhooks, subcontractors, equipment, gantt, calendar.

Revision ID: 0005_phases_41_60
Revises: 0004_api_keys
Create Date: 2026-06-30
"""
from __future__ import annotations

from alembic import op

revision: str = "0005_phases_41_60"
down_revision = "0004_api_keys"
branch_labels = None
depends_on = None


UPGRADE_SQL = """
-- Faza 41: BZP full documents
CREATE TABLE IF NOT EXISTS bzp_documents (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id    UUID REFERENCES tender(id) ON DELETE CASCADE,
    bzp_notice_id TEXT NOT NULL,
    doc_type     TEXT NOT NULL DEFAULT 'SWZ',
    filename     TEXT,
    content      TEXT,
    url          TEXT,
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_bzp_documents_tender ON bzp_documents (tender_id);
CREATE INDEX IF NOT EXISTS ix_bzp_documents_notice ON bzp_documents (bzp_notice_id);

-- Faza 42: TED EU tenders
CREATE TABLE IF NOT EXISTS ted_tenders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ted_id          TEXT UNIQUE NOT NULL,
    title           TEXT,
    buyer           TEXT,
    country         TEXT,
    cpv             TEXT[],
    value_eur       NUMERIC(18,2),
    deadline_at     TIMESTAMPTZ,
    published_at    TIMESTAMPTZ,
    url             TEXT,
    raw_json        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_ted_tenders_ted_id ON ted_tenders (ted_id);
CREATE INDEX IF NOT EXISTS ix_ted_tenders_country ON ted_tenders (country);

-- Faza 43: GUS BDL indicators
CREATE TABLE IF NOT EXISTS gus_indicators (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    variable_id  TEXT NOT NULL,
    name         TEXT NOT NULL,
    unit         TEXT,
    year         INT,
    period       TEXT,
    value        NUMERIC(18,4),
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(variable_id, year, period)
);
CREATE INDEX IF NOT EXISTS ix_gus_indicators_var ON gus_indicators (variable_id, year);

-- Faza 44: KRS/CEIDG verification cache
CREATE TABLE IF NOT EXISTS entity_verifications (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nip          TEXT NOT NULL,
    regon        TEXT,
    krs          TEXT,
    name         TEXT,
    status       TEXT,
    address      TEXT,
    source       TEXT NOT NULL DEFAULT 'krs',
    raw_json     JSONB,
    verified_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_entity_verif_nip ON entity_verifications (nip);

-- Faza 45: Excel imports/exports log
CREATE TABLE IF NOT EXISTS excel_imports (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id      UUID REFERENCES users(id),
    filename     TEXT NOT NULL,
    import_type  TEXT NOT NULL DEFAULT 'tender',
    rows_imported INT DEFAULT 0,
    errors       JSONB DEFAULT '[]',
    status       TEXT NOT NULL DEFAULT 'pending',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_excel_imports_org ON excel_imports (org_id);

-- Faza 46/47: Kosztorys (ATH/Norma PRO) items
CREATE TABLE IF NOT EXISTS kosztorys_items (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id    UUID REFERENCES tender(id) ON DELETE CASCADE,
    org_id       UUID REFERENCES organizations(id) ON DELETE CASCADE,
    lp           INT NOT NULL DEFAULT 1,
    kst_code     TEXT,
    description  TEXT NOT NULL,
    unit         TEXT NOT NULL DEFAULT 'szt',
    quantity     NUMERIC(18,4) NOT NULL DEFAULT 1,
    unit_price   NUMERIC(18,4) NOT NULL DEFAULT 0,
    total_price  NUMERIC(18,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    category     TEXT DEFAULT 'material',
    ath_xml      TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_kosztorys_tender ON kosztorys_items (tender_id);

-- Faza 48: Tender comments/collaboration
CREATE TABLE IF NOT EXISTS tender_comments (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id    UUID REFERENCES tender(id) ON DELETE CASCADE,
    user_id      UUID REFERENCES users(id) ON DELETE SET NULL,
    parent_id    UUID REFERENCES tender_comments(id) ON DELETE CASCADE,
    body         TEXT NOT NULL,
    mentions     TEXT[] DEFAULT '{}',
    edited       BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_tender_comments_tender ON tender_comments (tender_id, created_at);

-- Faza 49: Email notification config
CREATE TABLE IF NOT EXISTS email_configs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID REFERENCES organizations(id) ON DELETE CASCADE UNIQUE,
    smtp_host    TEXT NOT NULL DEFAULT 'localhost',
    smtp_port    INT NOT NULL DEFAULT 587,
    smtp_user    TEXT,
    smtp_pass    TEXT,
    from_email   TEXT,
    from_name    TEXT DEFAULT 'Terra.OS',
    enabled      BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS email_logs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID REFERENCES organizations(id) ON DELETE CASCADE,
    to_email     TEXT NOT NULL,
    subject      TEXT NOT NULL,
    template     TEXT,
    status       TEXT NOT NULL DEFAULT 'pending',
    error        TEXT,
    sent_at      TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_email_logs_org ON email_logs (org_id, created_at DESC);

-- Faza 50: Webhooks
CREATE TABLE IF NOT EXISTS webhooks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    url          TEXT NOT NULL,
    secret       TEXT,
    events       TEXT[] NOT NULL DEFAULT '{"tender.status_changed"}',
    enabled      BOOLEAN DEFAULT TRUE,
    last_fired_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_webhooks_org ON webhooks (org_id);

CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_id   UUID REFERENCES webhooks(id) ON DELETE CASCADE,
    event        TEXT NOT NULL,
    payload      JSONB,
    response_code INT,
    response_body TEXT,
    duration_ms  INT,
    status       TEXT NOT NULL DEFAULT 'pending',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_webhook_deliveries_wh ON webhook_deliveries (webhook_id, created_at DESC);

-- Faza 56: Subcontractors
CREATE TABLE IF NOT EXISTS subcontractors (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    nip          TEXT,
    specialization TEXT[],
    contact_email TEXT,
    contact_phone TEXT,
    rating       NUMERIC(3,2),
    notes        TEXT,
    active       BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_subcontractors_org ON subcontractors (org_id);

CREATE TABLE IF NOT EXISTS tender_subcontractors (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id        UUID REFERENCES tender(id) ON DELETE CASCADE,
    subcontractor_id UUID REFERENCES subcontractors(id) ON DELETE CASCADE,
    role             TEXT,
    value_pln        NUMERIC(18,2),
    UNIQUE(tender_id, subcontractor_id)
);

-- Faza 57: Equipment/machinery resources
CREATE TABLE IF NOT EXISTS equipment (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    category     TEXT NOT NULL DEFAULT 'maszyna',
    model        TEXT,
    serial_no    TEXT,
    owned        BOOLEAN DEFAULT TRUE,
    daily_cost   NUMERIC(10,2),
    status       TEXT NOT NULL DEFAULT 'available',
    notes        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_equipment_org ON equipment (org_id);

CREATE TABLE IF NOT EXISTS tender_equipment (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id    UUID REFERENCES tender(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES equipment(id) ON DELETE CASCADE,
    start_date   DATE,
    end_date     DATE,
    days         INT,
    UNIQUE(tender_id, equipment_id)
);

-- Faza 58: Gantt schedule tasks
CREATE TABLE IF NOT EXISTS gantt_tasks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id    UUID REFERENCES tender(id) ON DELETE CASCADE,
    parent_id    UUID REFERENCES gantt_tasks(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    start_date   DATE,
    end_date     DATE,
    progress     INT DEFAULT 0,
    color        TEXT DEFAULT '#3b82f6',
    position     INT DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_gantt_tasks_tender ON gantt_tasks (tender_id, position);

-- Faza 59: Calendar deadlines
CREATE TABLE IF NOT EXISTS calendar_events (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID REFERENCES organizations(id) ON DELETE CASCADE,
    tender_id    UUID REFERENCES tender(id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    event_type   TEXT NOT NULL DEFAULT 'deadline',
    event_date   DATE NOT NULL,
    notify_days_before INT DEFAULT 3,
    notified     BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_calendar_events_org ON calendar_events (org_id, event_date);
CREATE INDEX IF NOT EXISTS ix_calendar_events_tender ON calendar_events (tender_id);
"""

DOWNGRADE_SQL = """
DROP TABLE IF EXISTS calendar_events CASCADE;
DROP TABLE IF EXISTS gantt_tasks CASCADE;
DROP TABLE IF EXISTS tender_equipment CASCADE;
DROP TABLE IF EXISTS equipment CASCADE;
DROP TABLE IF EXISTS tender_subcontractors CASCADE;
DROP TABLE IF EXISTS subcontractors CASCADE;
DROP TABLE IF EXISTS webhook_deliveries CASCADE;
DROP TABLE IF EXISTS webhooks CASCADE;
DROP TABLE IF EXISTS email_logs CASCADE;
DROP TABLE IF EXISTS email_configs CASCADE;
DROP TABLE IF EXISTS tender_comments CASCADE;
DROP TABLE IF EXISTS kosztorys_items CASCADE;
DROP TABLE IF EXISTS excel_imports CASCADE;
DROP TABLE IF EXISTS entity_verifications CASCADE;
DROP TABLE IF EXISTS gus_indicators CASCADE;
DROP TABLE IF EXISTS ted_tenders CASCADE;
DROP TABLE IF EXISTS bzp_documents CASCADE;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
