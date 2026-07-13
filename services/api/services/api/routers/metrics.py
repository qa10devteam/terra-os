"""API Metrics & System Health — comprehensive platform diagnostics.

Endpoints:
  GET /api/v2/system/metrics     — aggregate API metrics (routes, DB, embeddings)
  GET /api/v2/system/db-stats    — database table sizes and row counts
  GET /api/v2/system/routes      — list all registered API routes
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
import sqlalchemy as sa

from terra_db.session import get_engine

router = APIRouter(prefix="/api/v2/system", tags=["system"])
logger = logging.getLogger(__name__)


@router.get("/metrics")
def get_system_metrics() -> dict[str, Any]:
    """Aggregate platform metrics — single-call system overview."""
    engine = get_engine()

    with engine.connect() as conn:
        # Core counts
        tenders = conn.execute(sa.text("SELECT COUNT(*) FROM tender")).scalar() or 0
        embeddings = conn.execute(sa.text("SELECT COUNT(*) FROM tender WHERE embedding IS NOT NULL")).scalar() or 0
        doc_chunks = conn.execute(sa.text("SELECT COUNT(*) FROM doc_chunks")).scalar() or 0
        notifications = conn.execute(sa.text("SELECT COUNT(*) FROM notifications WHERE read = false")).scalar() or 0
        audit_entries = conn.execute(sa.text("SELECT COUNT(*) FROM audit_log")).scalar() or 0
        users = conn.execute(sa.text("SELECT COUNT(*) FROM users")).scalar() or 0
        orgs = conn.execute(sa.text("SELECT COUNT(*) FROM organizations")).scalar() or 0

        # Pipeline
        pipeline_stats = conn.execute(sa.text("""
            SELECT pipeline_status, COUNT(*) 
            FROM tender 
            WHERE pipeline_status IS NOT NULL
            GROUP BY 1
        """)).fetchall()

        # ICB
        icb_count = conn.execute(sa.text("SELECT COUNT(*) FROM icb_ceny_srednie")).scalar() or 0
        icb_forecast = conn.execute(sa.text("SELECT COUNT(*) FROM icb_forecast")).scalar() or 0

        # DB size
        db_size = conn.execute(sa.text(
            "SELECT pg_size_pretty(pg_database_size(current_database()))"
        )).scalar() or "?"

    return {
        "platform": "budos",
        "version": "2.0-m8",
        "database": {
            "size": db_size,
            "tenders": tenders,
            "embeddings": embeddings,
            "doc_chunks": doc_chunks,
            "icb_records": icb_count,
            "icb_forecast": icb_forecast,
            "users": users,
            "organizations": orgs,
            "audit_entries": audit_entries,
            "unread_notifications": notifications,
        },
        "pipeline": {s: c for s, c in pipeline_stats},
        "ai": {
            "embedding_coverage": round(embeddings / tenders * 100, 1) if tenders > 0 else 0,
            "rag_chunks": doc_chunks,
            "model": "paraphrase-multilingual-MiniLM-L12-v2",
            "vector_dim": 384,
        },
    }


@router.get("/db-stats")
def get_db_stats() -> list[dict[str, Any]]:
    """Database table sizes and row counts."""
    engine = get_engine()

    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT 
                schemaname || '.' || relname as table_name,
                n_live_tup as row_count,
                pg_size_pretty(pg_relation_size(relid)) as size,
                pg_relation_size(relid) as size_bytes
            FROM pg_stat_user_tables
            ORDER BY pg_relation_size(relid) DESC
            LIMIT 30
        """)).fetchall()

    return [{
        "table": r[0],
        "rows": int(r[1]),
        "size": r[2],
        "size_bytes": int(r[3]),
    } for r in rows]


@router.get("/routes")
def get_routes() -> dict[str, Any]:
    """List all registered API routes."""
    from services.api.services.api.main import app as _app

    routes = []
    for route in _app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": sorted(route.methods - {"HEAD", "OPTIONS"}),
                "name": route.name or "",
            })

    # Group by prefix
    prefixes: dict[str, int] = {}
    for r in routes:
        parts = r["path"].split("/")
        prefix = "/".join(parts[:4]) if len(parts) >= 4 else r["path"]
        prefixes[prefix] = prefixes.get(prefix, 0) + 1

    return {
        "total_routes": len(routes),
        "routes": sorted(routes, key=lambda x: x["path"]),
        "by_prefix": dict(sorted(prefixes.items(), key=lambda x: -x[1])),
    }
