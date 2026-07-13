"""Proactive Agent — scheduled scans, deadline alerts, portfolio optimization.

Faza 8.21: autonomiczny agent który:
1. Skanuje nowe przetargi i matchuje z profilem firmy
2. Wysyła alerty deadlinowe (3d, 7d, 14d)
3. Optymalizuje portfolio LP (linear programming)
4. Generuje weekly digest

Endpoints:
  POST /api/v2/proactive/scan          — trigger manual scan
  GET  /api/v2/proactive/alerts        — pending deadline alerts
  GET  /api/v2/proactive/portfolio     — portfolio optimization result
  POST /api/v2/proactive/schedule      — configure scan schedule
  GET  /api/v2/proactive/status        — agent status & last run
"""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Query
import sqlalchemy as sa

from terra_db.session import get_engine

router = APIRouter(prefix="/api/v2/proactive", tags=["proactive-agent"])
logger = logging.getLogger(__name__)


# ── Deadline Alerts ────────────────────────────────────────────────────────────

@router.get("/alerts")
def get_deadline_alerts(
    days_ahead: int = Query(14, ge=1, le=90),
    severity: Optional[str] = Query(None, pattern="^(critical|warning|info)$"),
) -> list[dict[str, Any]]:
    """Get upcoming deadline alerts sorted by urgency."""
    engine = get_engine()
    sql = sa.text("""
        SELECT id, title, buyer, deadline_at, value_pln, match_score, pipeline_status,
               EXTRACT(DAY FROM (deadline_at - NOW())) AS days_left
        FROM tender
        WHERE deadline_at IS NOT NULL
          AND deadline_at > NOW()
          AND deadline_at <= NOW() + INTERVAL '1 day' * :days
          AND pipeline_status NOT IN ('won', 'lost', 'cancelled')
        ORDER BY deadline_at ASC
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"days": days_ahead}).fetchall()

    alerts = []
    for r in rows:
        days_left = float(r[7]) if r[7] else 0
        if days_left <= 3:
            sev = "critical"
        elif days_left <= 7:
            sev = "warning"
        else:
            sev = "info"

        if severity and sev != severity:
            continue

        alerts.append({
            "tender_id": str(r[0]),
            "title": r[1],
            "buyer": r[2],
            "deadline_at": r[3].isoformat() if r[3] else None,
            "value_pln": float(r[4]) if r[4] else None,
            "match_score": float(r[5]) if r[5] else None,
            "pipeline_status": r[6],
            "days_left": round(days_left, 1),
            "severity": sev,
            "action_required": _suggest_action(sev, r[6], days_left),
        })
    return alerts


def _suggest_action(severity: str, status: str, days_left: float) -> str:
    if severity == "critical":
        if status == "new":
            return "PILNE: Zdecyduj GO/NO-GO natychmiast lub odrzuć"
        return f"Deadline za {days_left:.0f}d — finalizuj ofertę"
    elif severity == "warning":
        if status == "new":
            return "Przeprowadź analizę i oceń potencjał"
        return "Przygotuj dokumentację ofertową"
    return "Monitoruj — czas na przygotowanie"


# ── Proactive Scan ─────────────────────────────────────────────────────────────

@router.post("/scan")
def trigger_scan() -> dict[str, Any]:
    """Run proactive scan — find high-potential unscored tenders."""
    engine = get_engine()

    # Find tenders without analysis that have high potential
    sql = sa.text("""
        WITH unscored AS (
            SELECT t.id, t.title, t.buyer, t.value_pln, t.cpv, t.deadline_at, t.match_score
            FROM tender t
            LEFT JOIN agent_run ar ON ar.tender_id = t.id
            WHERE ar.id IS NULL
              AND t.pipeline_status = 'new'
              AND t.created_at > NOW() - INTERVAL '30 days'
            ORDER BY t.match_score DESC NULLS LAST, t.value_pln DESC NULLS LAST
            LIMIT 20
        )
        SELECT * FROM unscored
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql).fetchall()

    recommendations = []
    for r in rows:
        score = float(r[6]) if r[6] else 0
        value = float(r[3]) if r[3] else 0
        priority = _calc_priority(score, value, r[5])

        recommendations.append({
            "tender_id": str(r[0]),
            "title": r[1],
            "buyer": r[2],
            "value_pln": value,
            "match_score": score,
            "deadline_at": r[5].isoformat() if r[5] else None,
            "priority": priority,
            "recommendation": "Uruchom analizę AI" if priority > 0.7 else "Oceń manualnie",
        })

    # Log scan to audit
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO audit_log (action, entity_type, details)
            VALUES ('proactive_scan', 'system', :det)
        """), {"det": json.dumps({"found": len(recommendations), "timestamp": datetime.utcnow().isoformat()})})

    return {
        "scanned_at": datetime.utcnow().isoformat(),
        "total_found": len(recommendations),
        "high_priority": sum(1 for r in recommendations if r["priority"] > 0.7),
        "recommendations": recommendations,
    }


def _calc_priority(match_score: float, value: float, deadline) -> float:
    """Priority 0-1 based on score, value, and deadline urgency."""
    score_factor = min(match_score / 100, 1.0) if match_score else 0.3
    value_factor = min(value / 5_000_000, 1.0) if value else 0.2

    deadline_factor = 0.5
    if deadline:
        days_left = (deadline - datetime.now(deadline.tzinfo if deadline.tzinfo else None)).days if hasattr(deadline, 'days') else 30
        try:
            days_left = (deadline - datetime.utcnow()).days
        except TypeError:
            days_left = 30
        if days_left < 7:
            deadline_factor = 1.0
        elif days_left < 14:
            deadline_factor = 0.8
        elif days_left < 30:
            deadline_factor = 0.6

    return round(0.4 * score_factor + 0.3 * value_factor + 0.3 * deadline_factor, 3)


# ── Portfolio Optimization ─────────────────────────────────────────────────────

@router.get("/portfolio")
def portfolio_optimization(
    max_concurrent: int = Query(5, ge=1, le=20),
    budget_hours: int = Query(200, ge=10, le=2000),
) -> dict[str, Any]:
    """Portfolio optimization — maximize expected value under resource constraints.
    
    Simple LP approximation: greedy knapsack by EV/effort ratio.
    """
    engine = get_engine()
    sql = sa.text("""
        SELECT id, title, value_pln, match_score, deadline_at, pipeline_status
        FROM tender
        WHERE pipeline_status IN ('new', 'qualified', 'analyzing', 'bidding')
          AND deadline_at > NOW()
        ORDER BY match_score DESC NULLS LAST
        LIMIT 50
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql).fetchall()

    candidates = []
    for r in rows:
        value = float(r[2]) if r[2] else 100_000
        score = float(r[3]) if r[3] else 30
        win_prob = min(score / 100, 0.95)
        # Effort estimate: base 20h + 10h per 1M PLN
        effort_hours = 20 + (value / 1_000_000) * 10
        ev = value * win_prob
        efficiency = ev / max(effort_hours, 1)

        candidates.append({
            "tender_id": str(r[0]),
            "title": r[1],
            "value_pln": value,
            "win_probability": round(win_prob, 3),
            "effort_hours": round(effort_hours, 1),
            "expected_value": round(ev, 0),
            "efficiency": round(efficiency, 2),
            "status": r[5],
        })

    # Greedy knapsack: sort by efficiency, pick until budget exhausted
    candidates.sort(key=lambda x: x["efficiency"], reverse=True)
    selected = []
    remaining_hours = budget_hours
    for c in candidates:
        if len(selected) >= max_concurrent:
            break
        if c["effort_hours"] <= remaining_hours:
            selected.append(c)
            remaining_hours -= c["effort_hours"]

    total_ev = sum(s["expected_value"] for s in selected)
    total_effort = sum(s["effort_hours"] for s in selected)

    return {
        "constraints": {"max_concurrent": max_concurrent, "budget_hours": budget_hours},
        "optimal_portfolio": selected,
        "metrics": {
            "total_expected_value": round(total_ev, 0),
            "total_effort_hours": round(total_effort, 1),
            "portfolio_efficiency": round(total_ev / max(total_effort, 1), 2),
            "utilization_pct": round(100 * total_effort / budget_hours, 1),
        },
        "dropped": [c for c in candidates if c not in selected][:5],
    }


# ── Schedule Config ────────────────────────────────────────────────────────────

@router.post("/schedule")
def update_schedule(
    scan_interval_minutes: int = Query(60, ge=15, le=1440),
    alert_check_minutes: int = Query(30, ge=5, le=360),
) -> dict[str, Any]:
    """Update proactive agent schedule configuration."""
    engine = get_engine()
    config = {
        "scan_interval_minutes": scan_interval_minutes,
        "alert_check_minutes": alert_check_minutes,
        "updated_at": datetime.utcnow().isoformat(),
    }
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO app_config (key, value, updated_at)
            VALUES ('proactive_schedule', :val, NOW())
            ON CONFLICT (key) DO UPDATE SET value = :val, updated_at = NOW()
        """), {"val": json.dumps(config)})
    return {"status": "ok", "config": config}


@router.get("/status")
def agent_status() -> dict[str, Any]:
    """Get proactive agent status — last runs, config."""
    engine = get_engine()
    with engine.connect() as conn:
        # Last scan
        last_scan = conn.execute(sa.text("""
            SELECT detail, at FROM audit_log
            WHERE action = 'proactive_scan'
            ORDER BY at DESC LIMIT 1
        """)).fetchone()

        # Config
        config_row = conn.execute(sa.text("""
            SELECT value FROM app_config WHERE key = 'proactive_schedule'
        """)).fetchone()

        # Alert stats
        alert_count = conn.execute(sa.text("""
            SELECT COUNT(*) FROM tender
            WHERE deadline_at BETWEEN NOW() AND NOW() + INTERVAL '14 days'
              AND pipeline_status NOT IN ('won', 'lost', 'cancelled')
        """)).scalar()

    return {
        "active": True,
        "last_scan": {
            "details": json.loads(last_scan[0]) if last_scan and last_scan[0] else None,
            "timestamp": last_scan[1].isoformat() if last_scan else None,
        },
        "pending_alerts": alert_count or 0,
        "config": json.loads(config_row[0]) if config_row else {"scan_interval_minutes": 60, "alert_check_minutes": 30},
    }
