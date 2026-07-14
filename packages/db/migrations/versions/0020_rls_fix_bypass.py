"""0020 — Fix RLS bypass: remove dangerous OR clauses from tenant_isolation policies.

Revision ID: 0020_rls_fix
Revises: 0019_mv_dashboard_unique_idx
Create Date: 2026-07-14

The original 0006 policy allowed full table access when app.tenant_id was not set
(empty string or NULL) via OR clauses. This migration recreates all tenant_isolation
policies with a strict check that returns NO rows when the session variable is missing.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '0020_rls_fix'
down_revision = '0019_mv_dashboard_unique_idx'
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Helper — fetch all tables in 'public' schema that have a tenant_id column.
# ---------------------------------------------------------------------------

def _tenant_tables(conn) -> list[str]:
    result = conn.execute(sa.text(
        "SELECT table_name "
        "FROM information_schema.columns "
        "WHERE column_name='tenant_id' AND table_schema='public' "
        "ORDER BY table_name"
    ))
    return [row[0] for row in result]


# ---------------------------------------------------------------------------
# Safe policy — no OR bypass; returns zero rows when app.tenant_id is unset.
# ---------------------------------------------------------------------------

SAFE_POLICY = """
CREATE POLICY tenant_isolation ON "{table}"
  AS PERMISSIVE
  FOR ALL
  USING (
    tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
  )
  WITH CHECK (
    tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
  )
"""

# ---------------------------------------------------------------------------
# Original unsafe policy (for downgrade only)
# ---------------------------------------------------------------------------

UNSAFE_POLICY = """
CREATE POLICY tenant_isolation ON "{table}"
  AS PERMISSIVE
  FOR ALL
  USING (
    tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
    OR current_setting('app.tenant_id', true) = ''
    OR current_setting('app.tenant_id', true) IS NULL
  )
  WITH CHECK (
    tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
    OR current_setting('app.tenant_id', true) = ''
    OR current_setting('app.tenant_id', true) IS NULL
  )
"""


def upgrade() -> None:
    conn = op.get_bind()
    tables = _tenant_tables(conn)

    for table in tables:
        # Drop the existing unsafe policy
        conn.execute(sa.text(
            f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"'
        ))
        # Recreate with safe policy (no bypass)
        conn.execute(sa.text(SAFE_POLICY.format(table=table)))


def downgrade() -> None:
    conn = op.get_bind()
    tables = _tenant_tables(conn)

    for table in tables:
        # Drop the safe policy
        conn.execute(sa.text(
            f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"'
        ))
        # Recreate with original unsafe policy
        conn.execute(sa.text(UNSAFE_POLICY.format(table=table)))
