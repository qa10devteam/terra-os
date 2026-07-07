"""Faza 71-75 — Monitoring router.

Endpoints:
  GET /api/v2/metrics             — uptime, requests_total, db_latency_ms, memory_mb
  GET /api/v2/system/status       — admin/owner only, full system status
  GET /api/v2/health/detailed     — detailed health check with all subsystems
  GET /api/v2/alerts              — active alerts / threshold violations
  GET /api/v2/sla                 — SLA tracking metrics
"""
from __future__ import annotations

import sys
sys.path.insert(0, '/home/ubuntu/terra-os/packages/vendor')

import os
import time
import threading
from datetime import datetime, timezone
from typing import Any

import psutil
from fastapi import APIRouter, Request
from sqlalchemy import text

from ..auth.deps import AuthUser
from ..security import require_admin

router = APIRouter(prefix="/api/v2", tags=["monitoring"])

# ─── In-memory counters ────────────────────────────────────────────────────────

_start_time: float = time.time()
_request_count: int = 0
_error_count: int = 0
_count_lock = threading.Lock()

# SLA tracking
_sla_total_requests: int = 0
_sla_successful_requests: int = 0
_sla_response_times: list[float] = []
_sla_lock = threading.Lock()


def increment_request_count() -> None:
    global _request_count
    with _count_lock:
        _request_count += 1


def increment_error_count() -> None:
    global _error_count
    with _count_lock:
        _error_count += 1


def get_request_count() -> int:
    with _count_lock:
        return _request_count


def record_response_time(ms: float, success: bool = True) -> None:
    global _sla_total_requests, _sla_successful_requests
    with _sla_lock:
        _sla_total_requests += 1
        if success:
            _sla_successful_requests += 1
        _sla_response_times.append(ms)
        # Keep only last 1000 measurements
        if len(_sla_response_times) > 1000:
            _sla_response_times.pop(0)


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/metrics")
async def metrics() -> dict[str, Any]:
    """Public metrics endpoint — in-memory counters + DB latency."""
    uptime = time.time() - _start_time

    # DB latency
    db_latency_ms: float | None = None
    try:
        from terra_db.session import get_engine
        engine = get_engine()
        t0 = time.perf_counter()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    except Exception:
        db_latency_ms = None

    # Memory
    memory_mb: float | None = None
    try:
        proc = psutil.Process(os.getpid())
        memory_mb = round(proc.memory_info().rss / 1024 / 1024, 2)
    except Exception:
        memory_mb = None

    with _count_lock:
        req_count = _request_count
        err_count = _error_count

    return {
        "uptime_seconds": round(uptime, 1),
        "requests_total": req_count,
        "errors_total": err_count,
        "db_latency_ms": db_latency_ms,
        "memory_mb": memory_mb,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/system/status")
async def system_status(current_user: AuthUser) -> dict[str, Any]:
    """Admin/owner only — full system status."""
    require_admin(current_user)

    uptime = time.time() - _start_time

    db_ok = False
    db_latency_ms: float | None = None
    try:
        from terra_db.session import get_engine
        engine = get_engine()
        t0 = time.perf_counter()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        db_ok = True
    except Exception:
        pass

    memory_mb: float | None = None
    cpu_percent: float | None = None
    try:
        proc = psutil.Process(os.getpid())
        memory_mb = round(proc.memory_info().rss / 1024 / 1024, 2)
        cpu_percent = proc.cpu_percent(interval=0.1)
    except Exception:
        pass

    with _count_lock:
        req_count = _request_count
        err_count = _error_count

    return {
        "status": "ok" if db_ok else "degraded",
        "uptime_seconds": round(uptime, 1),
        "requests_total": req_count,
        "errors_total": err_count,
        "db": "ok" if db_ok else "error",
        "db_latency_ms": db_latency_ms,
        "memory_mb": memory_mb,
        "cpu_percent": cpu_percent,
        "pid": os.getpid(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/detailed")
async def health_detailed() -> dict[str, Any]:
    """Detailed health check — no auth required."""
    checks: dict[str, Any] = {}

    # DB check
    try:
        from terra_db.session import get_engine
        engine = get_engine()
        t0 = time.perf_counter()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        checks["database"] = {"status": "ok", "latency_ms": latency_ms}
    except Exception as e:
        checks["database"] = {"status": "error", "error": str(e)}

    # Memory check
    try:
        proc = psutil.Process(os.getpid())
        mem = proc.memory_info()
        memory_mb = round(mem.rss / 1024 / 1024, 2)
        checks["memory"] = {
            "status": "ok" if memory_mb < 1000 else "warning",
            "rss_mb": memory_mb,
        }
    except Exception:
        checks["memory"] = {"status": "unknown"}

    # Disk check
    try:
        disk = psutil.disk_usage("/")
        disk_pct = disk.percent
        checks["disk"] = {
            "status": "ok" if disk_pct < 85 else "warning",
            "used_pct": disk_pct,
        }
    except Exception:
        checks["disk"] = {"status": "unknown"}

    all_ok = all(c.get("status") in ("ok", "warning") for c in checks.values())

    return {
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
        "uptime_seconds": round(time.time() - _start_time, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/alerts")
async def get_alerts(current_user: AuthUser) -> dict[str, Any]:
    """Return active alerts based on current system metrics."""
    require_admin(current_user)

    alerts = []

    # Memory alert
    try:
        proc = psutil.Process(os.getpid())
        memory_mb = proc.memory_info().rss / 1024 / 1024
        if memory_mb > 800:
            alerts.append({
                "id": "high_memory",
                "severity": "warning",
                "message": f"High memory usage: {memory_mb:.0f}MB",
                "threshold": "800MB",
                "current": f"{memory_mb:.0f}MB",
            })
    except Exception:
        pass

    # Error rate alert
    with _count_lock:
        req_count = _request_count
        err_count = _error_count

    if req_count > 100:
        error_rate = err_count / req_count * 100
        if error_rate > 5:
            alerts.append({
                "id": "high_error_rate",
                "severity": "critical" if error_rate > 10 else "warning",
                "message": f"High error rate: {error_rate:.1f}%",
                "threshold": "5%",
                "current": f"{error_rate:.1f}%",
            })

    # DB latency alert
    try:
        from terra_db.session import get_engine
        engine = get_engine()
        t0 = time.perf_counter()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_latency_ms = (time.perf_counter() - t0) * 1000
        if db_latency_ms > 500:
            alerts.append({
                "id": "high_db_latency",
                "severity": "warning",
                "message": f"High DB latency: {db_latency_ms:.0f}ms",
                "threshold": "500ms",
                "current": f"{db_latency_ms:.0f}ms",
            })
    except Exception:
        alerts.append({
            "id": "db_unreachable",
            "severity": "critical",
            "message": "Database unreachable",
            "threshold": "connected",
            "current": "disconnected",
        })

    return {
        "alert_count": len(alerts),
        "alerts": alerts,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/sla")
async def sla_metrics(current_user: AuthUser) -> dict[str, Any]:
    """SLA tracking metrics — uptime %, p50/p95/p99 latency."""
    require_admin(current_user)

    uptime_seconds = time.time() - _start_time
    uptime_days = uptime_seconds / 86400

    with _sla_lock:
        total = _sla_total_requests
        successful = _sla_successful_requests
        response_times = list(_sla_response_times)

    # Calculate percentiles
    p50 = p95 = p99 = None
    if response_times:
        sorted_times = sorted(response_times)
        n = len(sorted_times)
        p50 = sorted_times[int(n * 0.50)]
        p95 = sorted_times[min(int(n * 0.95), n - 1)]
        p99 = sorted_times[min(int(n * 0.99), n - 1)]

    availability_pct = (successful / total * 100) if total > 0 else 100.0

    return {
        "availability_pct": round(availability_pct, 4),
        "sla_target_pct": 99.9,
        "sla_met": availability_pct >= 99.9,
        "uptime_seconds": round(uptime_seconds, 1),
        "uptime_days": round(uptime_days, 2),
        "total_requests": total,
        "successful_requests": successful,
        "response_times_ms": {
            "p50": round(p50, 2) if p50 is not None else None,
            "p95": round(p95, 2) if p95 is not None else None,
            "p99": round(p99, 2) if p99 is not None else None,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
