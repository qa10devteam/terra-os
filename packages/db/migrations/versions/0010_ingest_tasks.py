"""Ingest tasks — async ingest tracking table.

Revision ID: 0010_ingest_tasks
Revises: 0009_bzp_documents_v2
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0010_ingest_tasks"
down_revision = "0009_bzp_documents_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE ingest_task_status AS ENUM (
                'pending', 'running', 'done', 'failed'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.create_table(
        "ingest_task",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=False),
                  sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("params", JSONB, nullable=True),
        sa.Column("progress", JSONB, nullable=True),   # {step, pct, message}
        sa.Column("result", JSONB, nullable=True),     # IngestResult as dict
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ingest_task_tenant_created",
                    "ingest_task", ["tenant_id", "created_at"])
    op.create_index("ix_ingest_task_status",
                    "ingest_task", ["status"])


def downgrade() -> None:
    op.drop_table("ingest_task")
    op.execute("DROP TYPE IF EXISTS ingest_task_status")
