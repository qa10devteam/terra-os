"""Bridge organizations ↔ tenant + notifications table.

Revision ID: 0003_bridge
Revises: 0002_auth
Create Date: 2026-06-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0003_bridge"
down_revision = "0002_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add tenant_id to organizations (nullable first)
    op.add_column(
        "organizations",
        sa.Column("tenant_id", UUID(as_uuid=False), sa.ForeignKey("tenant.id"), nullable=True),
    )
    op.create_index("ix_org_tenant", "organizations", ["tenant_id"])

    # 2. For each existing org without tenant, create a tenant and link it
    op.execute("""
        INSERT INTO tenant (id, name, created_at)
        SELECT gen_random_uuid(), o.name, now()
        FROM organizations o
        WHERE o.tenant_id IS NULL
        RETURNING id
    """)
    # Update organizations to link to newly created tenants by matching name+time
    op.execute("""
        UPDATE organizations o
        SET tenant_id = t.id
        FROM tenant t
        WHERE o.tenant_id IS NULL
          AND t.name = o.name
          AND t.created_at >= now() - interval '5 seconds'
    """)

    # 3. Notifications table
    op.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT,
            read BOOLEAN NOT NULL DEFAULT false,
            link TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_notif_user_unread ON notifications(user_id, read) WHERE read = false")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notif_org ON notifications(org_id, created_at DESC)")

    # 4. API keys table
    op.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            key_hash TEXT NOT NULL UNIQUE,
            prefix TEXT NOT NULL,
            scopes TEXT[] NOT NULL DEFAULT '{}',
            last_used_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # 5. Historical bids table (for ML models)
    op.execute("""
        CREATE TABLE IF NOT EXISTS historical_bids (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
            tender_id UUID REFERENCES tender(id) ON DELETE SET NULL,
            our_price NUMERIC(14,2),
            winning_price NUMERIC(14,2),
            n_competitors INTEGER,
            won BOOLEAN,
            markup_pct NUMERIC(6,4),
            actual_cost NUMERIC(14,2),
            margin_pct NUMERIC(6,4),
            cpv TEXT,
            region TEXT,
            bid_date DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_hist_bids_org ON historical_bids(org_id)")

    # 6. Job status tracking table
    op.execute("""
        CREATE TABLE IF NOT EXISTS job_status (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            total INTEGER DEFAULT 100,
            result JSONB DEFAULT '{}',
            error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS job_status")
    op.execute("DROP TABLE IF EXISTS historical_bids")
    op.execute("DROP TABLE IF EXISTS api_keys")
    op.execute("DROP TABLE IF EXISTS notifications")
    op.drop_column("organizations", "tenant_id")
