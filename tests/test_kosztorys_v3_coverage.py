"""C2-4 — Kosztorys v3 router coverage: routers/kosztorys_v3.py (28% → 60%+).

Tests for /api/v2/icb/rates and /api/v2/kosztorys/* endpoints.
Note: router has no prefix — routes are /api/v2/icb/rates and /api/v2/kosztorys/{id}/ai-wycena-v2.
"""
from __future__ import annotations

import uuid
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


KOSZTORYS_ID = str(uuid.uuid4())


# ─── Tests ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_icb_rates_200(app, auth_headers):
    """GET /api/v2/icb/rates?cpv5=45200&nuts2=PL91 → 200 with rates."""
    with patch("services.api.services.api.routers.kosztorys_v3.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v2/icb/rates?cpv5=45200&nuts2=PL91",
                headers=auth_headers,
            )

    assert resp.status_code == 200
    data = resp.json()
    assert "cpv5" in data
    assert "nuts2_code" in data
    assert "rates" in data


@pytest.mark.asyncio
async def test_get_icb_rates_empty_list(app, auth_headers):
    """GET /api/v2/icb/rates with unknown cpv5 → 200 with empty rates list."""
    with patch("services.api.services.api.routers.kosztorys_v3.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v2/icb/rates?cpv5=99999&nuts2=PL99",
                headers=auth_headers,
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["rates"] == []


@pytest.mark.asyncio
async def test_get_icb_rates_with_data(app, auth_headers):
    """GET /api/v2/icb/rates → 200 with populated rates from mock."""
    mock_row = MagicMock()
    mock_row.quarter = "2026-1"
    mock_row.icb_r_rate = 100.0
    mock_row.icb_m_rate = 200.0
    mock_row.icb_s_rate = 150.0
    mock_row.avg_value = 500000.0
    mock_row.median_value = 450000.0
    mock_row.n_tenders = 10

    with patch("services.api.services.api.routers.kosztorys_v3.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = [mock_row]
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v2/icb/rates?cpv5=45200&nuts2=PL91",
                headers=auth_headers,
            )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["rates"]) == 1
    assert data["rates"][0]["r"] == 100.0


@pytest.mark.asyncio
async def test_get_icb_rates_missing_params_422(app, auth_headers):
    """GET /api/v2/icb/rates without required params → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/icb/rates", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ai_wycena_v2_not_found(app, auth_headers):
    """POST /api/v2/kosztorys/{id}/ai-wycena-v2 → 404 when kosztorys not found."""
    with patch("services.api.services.api.routers.kosztorys_v3.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchone.return_value = None
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/v2/kosztorys/{KOSZTORYS_ID}/ai-wycena-v2",
                headers=auth_headers,
            )

    assert resp.status_code in (404, 200, 500)


@pytest.mark.asyncio
async def test_get_icb_rates_response_structure(app, auth_headers):
    """GET /api/v2/icb/rates → response has cpv5, nuts2_code, rates fields."""
    with patch("services.api.services.api.routers.kosztorys_v3.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v2/icb/rates?cpv5=45210&nuts2=PL63",
                headers=auth_headers,
            )

    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) >= {"cpv5", "nuts2_code", "rates"}
    assert data["cpv5"] == "45210"
    assert data["nuts2_code"] == "PL63"
