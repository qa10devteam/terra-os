"""Faza 14 — Notifications router with SSE."""
from __future__ import annotations

import asyncio
import base64
import json
import uuid
from typing import AsyncGenerator

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/notifications", tags=["notifications"])


def _row_to_dict(row) -> dict:
    return {
        "id": str(row.id),
        "type": row.type,
        "title": row.title,
        "body": row.body,
        "read": row.read,
        "link": row.link,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("")
def list_notifications(
    user: AuthUser,
    unread: bool | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Lista powiadomień z cursor pagination."""
    engine = get_engine()

    conditions = ["user_id = :user_id"]
    params: dict = {"user_id": user.user_id, "limit": limit + 1}

    if unread is True:
        conditions.append("read = false")

    cursor_cond = ""
    if cursor:
        try:
            cd = json.loads(base64.b64decode(cursor).decode())
            cursor_cond = "AND created_at < :cursor_ts"
            params["cursor_ts"] = cd["created_at"]
        except Exception:
            raise HTTPException(status_code=400, detail={"error": "invalid_cursor", "message": "Nieprawidłowy cursor"})

    where = " AND ".join(conditions)

    with engine.connect() as conn:
        total = conn.execute(
            sa.text(f"SELECT COUNT(*) FROM notifications WHERE {where}"),
            {k: v for k, v in params.items() if k != "limit"},
        ).scalar() or 0

        rows = conn.execute(
            sa.text(
                f"""SELECT id, type, title, body, read, link, created_at
                   FROM notifications
                   WHERE {where} {cursor_cond}
                   ORDER BY created_at DESC
                   LIMIT :limit"""
            ),
            params,
        ).fetchall()

    items = [_row_to_dict(r) for r in rows[:limit]]
    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        cd = {"created_at": last.created_at.isoformat()}
        next_cursor = base64.b64encode(json.dumps(cd).encode()).decode()

    return {"items": items, "total": int(total), "next_cursor": next_cursor}


@router.post("/{notification_id}/read")
def mark_read(notification_id: str, user: AuthUser) -> dict:
    """Oznacz powiadomienie jako przeczytane."""
    engine = get_engine()

    with engine.begin() as conn:
        result = conn.execute(
            sa.text(
                """UPDATE notifications SET read = true
                   WHERE id = :id AND user_id = :user_id
                   RETURNING id"""
            ),
            {"id": notification_id, "user_id": user.user_id},
        ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Powiadomienie nie znalezione"})

    return {"id": notification_id, "read": True}


@router.post("/read-all")
def mark_all_read(user: AuthUser) -> dict:
    """Oznacz wszystkie powiadomienia jako przeczytane."""
    engine = get_engine()

    with engine.begin() as conn:
        result = conn.execute(
            sa.text(
                """UPDATE notifications SET read = true
                   WHERE user_id = :user_id AND read = false"""
            ),
            {"user_id": user.user_id},
        )

    return {"updated": result.rowcount}


@router.get("/count")
def unread_count(user: AuthUser) -> dict:
    """Liczba nieprzeczytanych powiadomień."""
    engine = get_engine()

    with engine.connect() as conn:
        count = conn.execute(
            sa.text(
                "SELECT COUNT(*) FROM notifications WHERE user_id = :user_id AND read = false"
            ),
            {"user_id": user.user_id},
        ).scalar() or 0

    return {"unread_count": int(count)}


@router.get("/stream")
async def notification_stream(user: AuthUser) -> StreamingResponse:
    """SSE stream powiadomień."""
    engine = get_engine()

    async def event_generator() -> AsyncGenerator[str, None]:
        # Wyślij nagłówek SSE
        yield "data: {\"type\": \"connected\", \"message\": \"SSE connected\"}\n\n"

        last_id = None
        while True:
            try:
                with engine.connect() as conn:
                    query = "SELECT id, type, title, body, link, created_at FROM notifications WHERE user_id = :uid AND read = false"
                    params: dict = {"uid": user.user_id}
                    if last_id:
                        query += " AND created_at > :last_ts"
                        params["last_ts"] = last_id
                    query += " ORDER BY created_at ASC LIMIT 10"

                    rows = conn.execute(sa.text(query), params).fetchall()

                for row in rows:
                    data = json.dumps({
                        "id": str(row.id),
                        "type": row.type,
                        "title": row.title,
                        "body": row.body,
                        "link": row.link,
                    })
                    last_id = row.created_at.isoformat()
                    yield f"data: {data}\n\n"

            except Exception:
                yield "data: {\"type\": \"error\"}\n\n"

            await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
