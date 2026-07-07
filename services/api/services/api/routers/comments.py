"""Faza 48 — Team Collaboration: komentarze do tenderów, @mentions, historia."""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")

import re
import uuid
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v1/comments", tags=["collaboration"])


class CommentCreate(BaseModel):
    body: str
    parent_id: str | None = None


class CommentUpdate(BaseModel):
    body: str


def _extract_mentions(body: str) -> list[str]:
    """Extract @username mentions from comment body."""
    return re.findall(r"@([a-zA-Z0-9_.-]+)", body)


@router.get("/{tender_id}")
def list_comments(
    tender_id: str,
    user: AuthUser,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    """Lista komentarzy dla przetargu (z historią zmian)."""
    import uuid
    # Validate UUID — return empty list gracefully if invalid
    try:
        uuid.UUID(tender_id)
    except ValueError:
        return {"tender_id": tender_id, "total": 0, "comments": []}
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT c.id, c.tender_id, c.user_id, c.parent_id, c.body,
                       c.mentions, c.edited, c.created_at, c.updated_at,
                       u.email AS user_email
                FROM tender_comments c
                LEFT JOIN users u ON u.id = c.user_id
                WHERE c.tender_id = :tid
                ORDER BY c.created_at ASC
                LIMIT :limit OFFSET :offset
            """),
            {"tid": tender_id, "limit": limit, "offset": offset},
        ).fetchall()
        total = conn.execute(
            sa.text("SELECT COUNT(*) FROM tender_comments WHERE tender_id = :tid"),
            {"tid": tender_id},
        ).scalar()
    return {
        "tender_id": tender_id,
        "total": int(total or 0),
        "comments": [
            {
                "id": str(r.id),
                "parent_id": str(r.parent_id) if r.parent_id else None,
                "user_id": str(r.user_id) if r.user_id else None,
                "user_email": r.user_email,
                "body": r.body,
                "mentions": list(r.mentions) if r.mentions else [],
                "edited": r.edited,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ],
    }


@router.post("/{tender_id}")
def create_comment(tender_id: str, comment: CommentCreate, user: AuthUser) -> dict:
    """Dodaj komentarz do przetargu (obsługa @mentions)."""
    engine = get_engine()
    mentions = _extract_mentions(comment.body)
    rec_id = str(uuid.uuid4())

    with engine.connect() as conn:
        # Verify tender exists
        if not conn.execute(
            sa.text("SELECT 1 FROM tender WHERE id = :id"), {"id": tender_id}
        ).fetchone():
            raise HTTPException(status_code=404, detail="Przetarg nie istnieje")

        if comment.parent_id:
            if not conn.execute(
                sa.text("SELECT 1 FROM tender_comments WHERE id = :id AND tender_id = :tid"),
                {"id": comment.parent_id, "tid": tender_id},
            ).fetchone():
                raise HTTPException(status_code=404, detail="Komentarz nadrzędny nie istnieje")

        conn.execute(
            sa.text("""
                INSERT INTO tender_comments (id, tender_id, user_id, parent_id, body, mentions)
                VALUES (:id, :tender_id, :user_id, :parent_id, :body, :mentions)
            """),
            {
                "id": rec_id,
                "tender_id": tender_id,
                "user_id": user.user_id,
                "parent_id": comment.parent_id,
                "body": comment.body,
                "mentions": mentions,
            },
        )
        conn.commit()

    # TODO: trigger notifications for @mentions (Faza 49)
    return {
        "id": rec_id,
        "tender_id": tender_id,
        "mentions": mentions,
        "status": "created",
    }


@router.patch("/{tender_id}/{comment_id}")
def update_comment(
    tender_id: str, comment_id: str, patch: CommentUpdate, user: AuthUser
) -> dict:
    """Edytuj komentarz (tylko autor)."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT user_id FROM tender_comments WHERE id = :id AND tender_id = :tid"),
            {"id": comment_id, "tid": tender_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Komentarz nie istnieje")
        if str(row.user_id) != user.user_id and user.role not in ("admin", "manager"):
            raise HTTPException(status_code=403, detail="Brak uprawnień do edycji komentarza")
        mentions = _extract_mentions(patch.body)
        conn.execute(
            sa.text("""
                UPDATE tender_comments
                SET body = :body, mentions = :mentions, edited = true, updated_at = now()
                WHERE id = :id
            """),
            {"body": patch.body, "mentions": mentions, "id": comment_id},
        )
        conn.commit()
    return {"id": comment_id, "status": "updated", "edited": True}


@router.delete("/{tender_id}/{comment_id}")
def delete_comment(tender_id: str, comment_id: str, user: AuthUser) -> dict:
    """Usuń komentarz (autor lub admin)."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT user_id FROM tender_comments WHERE id = :id AND tender_id = :tid"),
            {"id": comment_id, "tid": tender_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Komentarz nie istnieje")
        if str(row.user_id) != user.user_id and user.role not in ("admin", "manager"):
            raise HTTPException(status_code=403, detail="Brak uprawnień do usunięcia")
        conn.execute(
            sa.text("DELETE FROM tender_comments WHERE id = :id"), {"id": comment_id}
        )
        conn.commit()
    return {"id": comment_id, "status": "deleted"}


@router.get("/{tender_id}/activity")
def tender_activity(
    tender_id: str,
    user: AuthUser,
    limit: int = Query(50),
) -> dict:
    """Historia aktywności i zmian dla przetargu (komentarze + zmiany statusu)."""
    engine = get_engine()
    with engine.connect() as conn:
        # Comments
        comments = conn.execute(
            sa.text("""
                SELECT c.id, 'comment' AS type, c.body AS detail,
                       u.email AS actor, c.created_at
                FROM tender_comments c
                LEFT JOIN users u ON u.id = c.user_id
                WHERE c.tender_id = :tid
                ORDER BY c.created_at DESC LIMIT :limit
            """),
            {"tid": tender_id, "limit": limit},
        ).fetchall()

        # Audit log entries for this tender
        # FIX: columns are entity_id, actor, at — not resource_id, actor_email, created_at
        audit_rows = conn.execute(
            sa.text("""
                SELECT id, 'audit' AS type,
                       action || ': ' || coalesce(entity, '') AS detail,
                       actor AS actor, at AS created_at
                FROM audit_log
                WHERE entity_id = :tid::uuid
                ORDER BY at DESC LIMIT :limit
            """),
            {"tid": tender_id, "limit": limit},
        ).fetchall() if _table_exists(conn, "audit_log") else []

    activity = sorted(
        [
            {
                "id": str(r.id),
                "type": r.type,
                "detail": r.detail,
                "actor": r.actor,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in list(comments) + list(audit_rows)
        ],
        key=lambda x: x["created_at"] or "",
        reverse=True,
    )
    return {"tender_id": tender_id, "activity": activity[:limit]}


def _table_exists(conn: Any, table_name: str) -> bool:
    r = conn.execute(
        sa.text(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name=:t)"
        ),
        {"t": table_name},
    ).scalar()
    return bool(r)
