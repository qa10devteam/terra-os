"""ensure audit_log has all required HTTP-logging columns

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-18

The original audit_log table (0001_initial) tracks business-level events
(actor, action, entity) for tenant-scoped operations.  This migration adds
HTTP-request-level columns so the AuditLogMiddleware can record who called
which endpoint, from where, and with what result — without touching the
existing schema or data.
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add HTTP-specific columns to the existing audit_log table.
    # All nullable so legacy rows are not affected.
    op.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS user_id TEXT")
    op.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS org_id TEXT")
    op.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS method TEXT")
    op.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS path TEXT")
    op.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS status_code INTEGER")
    op.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS ip TEXT")
    op.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS duration_ms INTEGER")
    op.execute("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS ts TIMESTAMPTZ")

    # Supporting indexes for common query patterns
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_org_id ON audit_log(org_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_ts ON audit_log(ts)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_audit_log_ts")
    op.execute("DROP INDEX IF EXISTS idx_audit_log_org_id")
    op.execute("DROP INDEX IF EXISTS idx_audit_log_user_id")
    op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS ts")
    op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS duration_ms")
    op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS ip")
    op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS status_code")
    op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS path")
    op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS method")
    op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS org_id")
    op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS user_id")
