"""Faza 43 — GUS BDL API: wskaźniki makroekonomiczne (ceny materiałów, inflacja)."""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")

import uuid
from typing import Any

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, Query

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v1/gus", tags=["gus-bdl"])

GUS_BDL_BASE = "https://bdl.stat.gov.pl/api/v1"

# Kluczowe wskaźniki: wskaźnik cen materiałów budowlanych, inflacja CPI
DEFAULT_VARIABLES = [
    ("P3808", "Wskaźnik cen materiałów budowlanych"),
    ("P1774", "Wskaźnik cen towarów i usług konsumpcyjnych (CPI)"),
    ("P2137", "Ceny kruszyw i materiałów ziemnych"),
    ("P2511", "Zatrudnienie w budownictwie"),
    ("P3800", "Produkcja budowlano-montażowa"),
]


def _fetch_variable(var_id: str, var_name: str, year: int = 2024) -> list[dict]:
    """Fetch single variable data from GUS BDL."""
    results = []
    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(
                f"{GUS_BDL_BASE}/data/by-variable/{var_id}",
                params={
                    "year": year,
                    "unitLevel": 0,
                    "lang": "pl",
                    "format": "json",
                },
                headers={"X-ClientId": "terra-os-app"},
            )
            resp.raise_for_status()
            data = resp.json()
            results_raw = data.get("results", [])
            for item in results_raw[:5]:
                values = item.get("values", [])
                for v in values:
                    results.append({
                        "variable_id": var_id,
                        "name": var_name,
                        "unit": data.get("measureUnitName", ""),
                        "year": v.get("year", year),
                        "period": str(v.get("period", "")),
                        "value": v.get("val"),
                    })
    except Exception as exc:
        # Store stub value on failure
        results.append({
            "variable_id": var_id,
            "name": var_name,
            "unit": "%",
            "year": year,
            "period": "rok",
            "value": None,
            "error": str(exc),
        })
    return results


def _sync_indicators(year: int = 2024) -> dict:
    """Sync all key indicators from GUS BDL."""
    engine = get_engine()
    total_stored = 0
    for var_id, var_name in DEFAULT_VARIABLES:
        items = _fetch_variable(var_id, var_name, year)
        for item in items:
            if item.get("error"):
                continue
            with engine.connect() as conn:
                conn.execute(
                    sa.text("""
                        INSERT INTO gus_indicators (id, variable_id, name, unit, year, period, value, fetched_at)
                        VALUES (:id, :var_id, :name, :unit, :year, :period, :value, now())
                        ON CONFLICT (variable_id, year, period) DO UPDATE SET
                            value = EXCLUDED.value, fetched_at = now()
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "var_id": item["variable_id"],
                        "name": item["name"],
                        "unit": item.get("unit", ""),
                        "year": item["year"],
                        "period": item["period"],
                        "value": item.get("value"),
                    },
                )
                conn.commit()
                total_stored += 1
    return {"stored": total_stored, "year": year}


@router.post("/sync")
def gus_sync(
    background_tasks: BackgroundTasks,
    user: AuthUser,
    year: int = Query(2024, ge=2015, le=2030),
) -> dict:
    """Synchronizuj wskaźniki makroekonomiczne z GUS BDL."""
    background_tasks.add_task(_sync_indicators, year)
    return {
        "status": "started",
        "year": year,
        "variables": [v[0] for v in DEFAULT_VARIABLES],
        "message": f"Synchronizacja GUS BDL dla roku {year}",
    }


@router.get("/indicators")
def list_indicators(
    user: AuthUser,
    variable_id: str | None = Query(None),
    year: int | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    """Lista wskaźników makroekonomicznych z GUS BDL."""
    engine = get_engine()
    filters = []
    params: dict = {"limit": limit}
    if variable_id:
        filters.append("variable_id = :var_id")
        params["var_id"] = variable_id
    if year:
        filters.append("year = :year")
        params["year"] = year
    where = "WHERE " + " AND ".join(filters) if filters else ""
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(f"""
                SELECT id, variable_id, name, unit, year, period, value, fetched_at
                FROM gus_indicators {where}
                ORDER BY year DESC, variable_id, period
                LIMIT :limit
            """),
            params,
        ).fetchall()
    return {
        "items": [
            {
                "id": str(r.id),
                "variable_id": r.variable_id,
                "name": r.name,
                "unit": r.unit,
                "year": r.year,
                "period": r.period,
                "value": float(r.value) if r.value is not None else None,
                "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None,
            }
            for r in rows
        ]
    }


@router.get("/inflation")
def get_inflation_summary(user: AuthUser) -> dict:
    """Podsumowanie wskaźników inflacji i cen materiałów budowlanych."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT variable_id, name, unit, year, value, fetched_at
                FROM gus_indicators
                WHERE variable_id IN ('P1774', 'P3808')
                ORDER BY year DESC, variable_id
                LIMIT 20
            """),
        ).fetchall()
    return {
        "summary": [
            {
                "variable_id": r.variable_id,
                "name": r.name,
                "unit": r.unit,
                "year": r.year,
                "value": float(r.value) if r.value is not None else None,
            }
            for r in rows
        ],
        "note": "P1774=CPI, P3808=Ceny materiałów budowlanych",
    }
