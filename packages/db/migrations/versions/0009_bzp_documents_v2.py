"""BZP documents v2 — add is_local, size_kb, local_path, external_url columns.

Revision ID: 0009_bzp_documents_v2
Revises: 0008_org_invites
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa

revision: str = "0009_bzp_documents_v2"
down_revision = "0008_org_invites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Dodaj brakujące kolumny do bzp_documents
    op.execute("""
        ALTER TABLE bzp_documents
            ADD COLUMN IF NOT EXISTS is_local      BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS size_kb        INTEGER,
            ADD COLUMN IF NOT EXISTS local_path     TEXT,
            ADD COLUMN IF NOT EXISTS external_url   TEXT;
    """)

    # Unique constraint: jeden dokument per (tender_id, filename)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_bzp_documents_tender_filename
            ON bzp_documents (tender_id, filename)
            WHERE filename IS NOT NULL;
    """)

    # Aktualizuj istniejące rekordy: url staje się external_url, lokalne pliki oznaczamy
    op.execute("""
        UPDATE bzp_documents
        SET external_url = url
        WHERE external_url IS NULL AND url IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_bzp_documents_tender_filename;")
    op.execute("""
        ALTER TABLE bzp_documents
            DROP COLUMN IF EXISTS is_local,
            DROP COLUMN IF EXISTS size_kb,
            DROP COLUMN IF EXISTS local_path,
            DROP COLUMN IF EXISTS external_url;
    """)
