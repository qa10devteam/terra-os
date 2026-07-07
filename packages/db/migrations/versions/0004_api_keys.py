"""Faza 73: API Keys — table migration

Revision ID: 0004_api_keys
Revises: 0002_auth
Create Date: 2026-06-30
"""
from __future__ import annotations

from alembic import op

revision: str = "0004_api_keys"
down_revision = "0003_notifications"
branch_labels = None
depends_on = None


UPGRADE_SQL = """
CREATE TABLE IF NOT EXISTS api_keys (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    org_id       UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    key_hash     TEXT NOT NULL UNIQUE,  -- SHA256 of the actual key
    prefix       TEXT NOT NULL,         -- first 8 chars: 'terra_XX'
    scopes       TEXT[] NOT NULL DEFAULT '{}',
    last_used_at TIMESTAMPTZ,
    expires_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_api_keys_user ON api_keys (user_id);
CREATE INDEX IF NOT EXISTS ix_api_keys_org  ON api_keys (org_id);
CREATE INDEX IF NOT EXISTS ix_api_keys_hash ON api_keys (key_hash);

-- Faza 77: plan field on organizations (already exists in 0002 as DEFAULT 'free')
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL DEFAULT 'free';
"""

DOWNGRADE_SQL = """
DROP TABLE IF EXISTS api_keys CASCADE;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
