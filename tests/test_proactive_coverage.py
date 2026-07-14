"""C2-2 — Proactive Agent router coverage: routers/proactive.py (20% → 55%+).

Tests for /api/v2/proactive/* endpoints using AsyncClient + ASGITransport.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    from services.api.services.api.main import app as _app
    return _app


@pytest.fixture(scope="module")
def auth_headers():
    from services.api.services.api.auth.utils import create_access_token
    token = create_access_token(
        user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
        email="demo@terra-os.pl",
        org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
        role="owner",
    )
    return {"Authorization": f"Bearer {token}"}


BASE = "/api/v2/proactive"


# ─── Tests ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_alerts_200(app, auth_headers):
    """GET /api/v2/proactive/alerts → 200 with list."""
    with patch("services.api.services.api.routers.proactive.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"{BASE}/alerts", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_alerts_severity_filter(app, auth_headers):
    """GET /api/v2/proactive/alerts?severity=critical → 200."""
    with patch("services.api.services.api.routers.proactive.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"{BASE}/alerts?severity=critical&days_ahead=7",
                headers=auth_headers,
            )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_portfolio_200(app, auth_headers):
    """GET /api/v2/proactive/portfolio → 200 with optimization data."""
    with patch("services.api.services.api.routers.proactive.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"{BASE}/portfolio", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "optimal_portfolio" in data or "metrics" in data or "constraints" in data


@pytest.mark.asyncio
async def test_portfolio_custom_params(app, auth_headers):
    """GET /api/v2/proactive/portfolio?max_concurrent=3&budget_hours=100 → 200."""
    with patch("services.api.services.api.routers.proactive.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"{BASE}/portfolio?max_concurrent=3&budget_hours=100",
                headers=auth_headers,
            )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_status_200(app, auth_headers):
    """GET /api/v2/proactive/status → 200 with agent status."""
    with patch("services.api.services.api.routers.proactive.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchone.return_value = None
        conn.execute.return_value.scalar.return_value = 0
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"{BASE}/status", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data or "last_scan" in data or "agent" in data


@pytest.mark.asyncio
async def test_alerts_days_ahead(app, auth_headers):
    """GET /api/v2/proactive/alerts?days_ahead=30 → 200."""
    with patch("services.api.services.api.routers.proactive.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"{BASE}/alerts?days_ahead=30",
                headers=auth_headers,
            )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_scan_200(app, auth_headers):
    """POST /api/v2/proactive/scan → 200 with scan results."""
    with patch("services.api.services.api.routers.proactive.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn
        mock_eng.return_value.begin.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"{BASE}/scan", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "total_found" in data or "recommendations" in data or "scanned_at" in data
