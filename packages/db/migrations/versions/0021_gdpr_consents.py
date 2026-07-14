"""Create gdpr_consents table.

Revision ID: 0021_gdpr_consents
Revises: 0020_rls_fix
Create Date: 2026-07-14
"""
from alembic import op
from sqlalchemy import text

revision = "0021_gdpr_consents"
down_revision = "0020_rls_fix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text("""
            CREATE TABLE IF NOT EXISTS gdpr_consents (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                analytics boolean NOT NULL DEFAULT false,
                marketing boolean NOT NULL DEFAULT false,
                third_party boolean NOT NULL DEFAULT false,
                recorded_at timestamptz NOT NULL DEFAULT now(),
                ip_address inet,
                user_agent text
            );
        """)
    )
    op.execute(
        text("CREATE INDEX IF NOT EXISTS idx_gdpr_consents_user ON gdpr_consents(user_id);")
    )


def downgrade() -> None:
    op.execute(text("DROP INDEX IF EXISTS idx_gdpr_consents_user;"))
    op.execute(text("DROP TABLE IF EXISTS gdpr_consents;"))
