"""M3: notifications table

Revision ID: 0003_notifications
Revises: 0002_auth
Create Date: 2026-06-30
"""
from __future__ import annotations
from alembic import op

revision: str = "0003_notifications"
down_revision = "0003_bridge"
branch_labels = None
depends_on = None


UPGRADE_SQL = """
CREATE TABLE IF NOT EXISTS notifications (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    uuid REFERENCES users(id) ON DELETE CASCADE,
    org_id     uuid REFERENCES organizations(id) ON DELETE CASCADE,
    type       text NOT NULL,
    title      text NOT NULL,
    body       text,
    read       boolean NOT NULL DEFAULT false,
    link       text,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_notifications_user ON notifications (user_id, read, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_notifications_org ON notifications (org_id, created_at DESC);
"""

DOWNGRADE_SQL = """
DROP TABLE IF EXISTS notifications CASCADE;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
