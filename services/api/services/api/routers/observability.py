"""S127-S129 — Observability: in-process metrics endpoint."""
from __future__ import annotations

import logging
from typing import Any, Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text

from ..auth.deps import AuthUser
from terra_db.session import get_engine
from ..services.metrics import get_all

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v2/observability', tags=['observability'])


def get_db():
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
        conn.commit()


DB = Annotated[Any, Depends(get_db)]


@router.get('/metrics')
def obs_metrics(user: AuthUser):
    return get_all()
