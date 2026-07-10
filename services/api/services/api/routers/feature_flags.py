"""S132 — Feature Flags management endpoints."""
from __future__ import annotations

import logging
from typing import Any, Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text

from ..auth.deps import AuthUser
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v2/feature-flags', tags=['feature_flags'])


def get_db():
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
        conn.commit()


DB = Annotated[Any, Depends(get_db)]


@router.get('/')
def list_flags(user: AuthUser, db: DB):
    rows = db.execute(
        text('SELECT name, enabled, rollout_pct FROM feature_flags WHERE tenant_id=:t'),
        {'t': str(user.org_id)}
    ).fetchall()
    return [dict(r._mapping) for r in rows]


@router.post('/{name}/toggle')
def toggle_flag(name: str, user: AuthUser, db: DB):
    db.execute(
        text(
            'INSERT INTO feature_flags(name, tenant_id, enabled) VALUES(:n, :t, true) '
            'ON CONFLICT(name, tenant_id) DO UPDATE SET enabled = NOT feature_flags.enabled'
        ),
        {'n': name, 't': str(user.org_id)}
    )
    db.commit()
    row = db.execute(
        text('SELECT enabled FROM feature_flags WHERE name=:n AND tenant_id=:t'),
        {'n': name, 't': str(user.org_id)}
    ).fetchone()
    return {'name': name, 'enabled': row.enabled if row else None}
