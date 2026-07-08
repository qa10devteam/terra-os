"""Faza 78 — Demo mode router.

Provides seed demo data endpoints for showcasing Terra.OS without real data.
"""
from __future__ import annotations


import os
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v2/demo", tags=["demo"])

DEMO_ENABLED = os.getenv("DEMO_MODE", "true").lower() in ("1", "true", "yes")


def _check_demo_enabled():
    if not DEMO_ENABLED:
        raise HTTPException(status_code=404, detail="Demo mode disabled")


DEMO_TENDERS = [
    {
        "id": "demo-tender-001",
        "name": "Budowa drogi gminnej w miejscowości Kowale",
        "buyer": "Gmina Kowale",
        "status": "analysis",
        "deadline": "2026-08-15",
        "value_pln": 2_450_000,
        "cpv": ["45233120-6"],
        "risk_score": 0.32,
        "ai_recommendation": "go",
        "region": "dolnośląskie",
    },
    {
        "id": "demo-tender-002",
        "name": "Remont nawierzchni ul. Lipowej w Strzelinie",
        "buyer": "Powiat Strzeliński",
        "status": "estimation",
        "deadline": "2026-07-30",
        "value_pln": 890_000,
        "cpv": ["45233220-7"],
        "risk_score": 0.18,
        "ai_recommendation": "go",
        "region": "dolnośląskie",
    },
    {
        "id": "demo-tender-003",
        "name": "Budowa zbiornika retencyjnego",
        "buyer": "Gmina Piława Górna",
        "status": "decision",
        "deadline": "2026-07-10",
        "value_pln": 3_200_000,
        "cpv": ["45247270-3"],
        "risk_score": 0.61,
        "ai_recommendation": "no_go",
        "region": "dolnośląskie",
    },
    {
        "id": "demo-tender-004",
        "name": "Termomodernizacja budynku szkoły podstawowej",
        "buyer": "Gmina Dzierżoniów",
        "status": "won",
        "deadline": "2026-06-01",
        "value_pln": 1_750_000,
        "cpv": ["45321000-3"],
        "risk_score": 0.24,
        "ai_recommendation": "go",
        "region": "dolnośląskie",
        "won": True,
    },
    {
        "id": "demo-tender-005",
        "name": "Budowa chodnika wzdłuż DW385",
        "buyer": "Zarząd Dróg Województwa Dolnośląskiego",
        "status": "lost",
        "deadline": "2026-05-15",
        "value_pln": 420_000,
        "cpv": ["45233162-2"],
        "risk_score": 0.42,
        "ai_recommendation": "go",
        "region": "dolnośląskie",
        "won": False,
    },
]

DEMO_METRICS = {
    "tenders_total": 47,
    "tenders_won": 19,
    "win_rate_pct": 40.4,
    "avg_value_pln": 1_250_000,
    "total_value_won_pln": 23_750_000,
    "pending_decisions": 3,
    "active_analyses": 5,
}


@router.get("/tenders")
def demo_tenders() -> list[dict[str, Any]]:
    """Return demo tender list."""
    _check_demo_enabled()
    return DEMO_TENDERS


@router.get("/metrics")
def demo_metrics() -> dict[str, Any]:
    """Return demo dashboard metrics."""
    _check_demo_enabled()
    return DEMO_METRICS


@router.get("/status")
def demo_status() -> dict[str, Any]:
    """Return demo mode status."""
    return {
        "demo_mode": DEMO_ENABLED,
        "message": "Demo mode aktywny — dane przykładowe" if DEMO_ENABLED else "Demo wyłączone",
    }
