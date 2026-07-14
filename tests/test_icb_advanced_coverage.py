"""C2-5 — ICB Advanced router coverage: routers/icb_advanced.py (26% → 60%+).

Tests for /api/v2/icb/* endpoints using AsyncClient + ASGITransport.
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


BASE = "/api/v2/icb"


def _mock_icb_service():
    """Patch icb_service functions."""
    mock_search = MagicMock(return_value=[
        {
            "nazwa": "Beton B25", "symbol": "KNR-02-01-001-01",
            "jednostka": "m3", "cena_netto": 450.0,
            "category": "betoniarstwo", "typ_rms": "M",
        }
    ])
    mock_latest_quarter = MagicMock(return_value=(2026, 1))
    mock_get_price = MagicMock(return_value={
        "nazwa": "Beton B25", "symbol": "KNR-02-01-001-01",
        "cena_netto": 450.0, "jednostka": "m3",
    })
    mock_regional = MagicMock(return_value=1.05)
    return mock_search, mock_latest_quarter, mock_get_price, mock_regional


# ─── Tests ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_icb_200(app, auth_headers):
    """GET /api/v2/icb/search?q=beton → 200 with results dict."""
    mock_search, mock_lq, _, _ = _mock_icb_service()
    with patch("services.api.services.api.routers.icb_advanced.get_engine") as mock_eng, \
         patch("services.api.services.api.intelligence.icb_service.search_icb", mock_search), \
         patch("services.api.services.api.intelligence.icb_service.get_latest_quarter", mock_lq):

        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"{BASE}/search?q=beton", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data or "count" in data or "quarter" in data


@pytest.mark.asyncio
async def test_search_icb_short_query_422(app, auth_headers):
    """GET /api/v2/icb/search?q=b → 422 (min_length=2 but b is 1 char)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"{BASE}/search?q=b", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_icb_no_query_422(app, auth_headers):
    """GET /api/v2/icb/search (no q param) → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"{BASE}/search", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_categories_200(app, auth_headers):
    """GET /api/v2/icb/categories → 200 with list of categories."""
    with patch("services.api.services.api.routers.icb_advanced.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"{BASE}/categories", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_dashboard_200(app, auth_headers):
    """GET /api/v2/icb/dashboard → 200 with dashboard data."""
    # Clear cache first to ensure fresh call
    import services.api.services.api.routers.icb_advanced as _mod
    _mod._dashboard_cache.clear()

    with patch("services.api.services.api.routers.icb_advanced.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        # Return mock stats row
        stats_row = MagicMock()
        stats_row.total = 784000
        stats_row.symbols = 50000
        stats_row.categories = 25
        stats_row.quarters = 40
        conn.execute.return_value.fetchone.return_value = stats_row
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"{BASE}/dashboard", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_basket_post_200(app, auth_headers):
    """POST /api/v2/icb/basket → 200 with cost summary."""
    mock_search, mock_lq, mock_price, mock_regional = _mock_icb_service()

    with patch("services.api.services.api.intelligence.icb_service.get_latest_quarter", mock_lq), \
         patch("services.api.services.api.intelligence.icb_service.search_icb", mock_search), \
         patch("services.api.services.api.intelligence.icb_service.get_icb_price", mock_price), \
         patch("services.api.services.api.intelligence.icb_service.get_regional_coefficient", mock_regional):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"{BASE}/basket",
                json={
                    "items": [
                        {"query": "beton", "quantity": 10.0, "unit": "m3"},
                    ],
                    "voivodeship": "mazowieckie",
                },
                headers=auth_headers,
            )

    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data or "total_cost" in data


@pytest.mark.asyncio
async def test_basket_empty_items(app, auth_headers):
    """POST /api/v2/icb/basket with empty items → 200."""
    mock_lq = MagicMock(return_value=(2026, 1))
    mock_regional = MagicMock(return_value=1.0)

    with patch("services.api.services.api.intelligence.icb_service.get_latest_quarter", mock_lq), \
         patch("services.api.services.api.intelligence.icb_service.get_regional_coefficient", mock_regional):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"{BASE}/basket",
                json={"items": []},
                headers=auth_headers,
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data.get("total_cost") == 0.0


@pytest.mark.asyncio
async def test_forecast_get_200(app, auth_headers):
    """GET /api/v2/icb/forecast → 200 (may return empty list)."""
    mock_forecasts = MagicMock(return_value=[])
    with patch("services.api.services.api.intelligence.forecaster.get_forecasts", mock_forecasts):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"{BASE}/forecast", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_compare_regional_200(app, auth_headers):
    """GET /api/v2/icb/compare → 200 with regional data."""
    mock_lq = MagicMock(return_value=(2026, 1))
    mock_regional = MagicMock(return_value=1.0)

    with patch("services.api.services.api.routers.icb_advanced.get_engine") as mock_eng, \
         patch("services.api.services.api.intelligence.icb_service.get_latest_quarter", mock_lq), \
         patch("services.api.services.api.intelligence.icb_service.get_regional_coefficient", mock_regional):

        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.scalar.return_value = None  # no base data → returns error dict
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"{BASE}/compare?category=murarstwo&typ_rms=M",
                headers=auth_headers,
            )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_robocizna_map_200(app, auth_headers):
    """GET /api/v2/icb/robocizna/map → 200."""
    with patch("services.api.services.api.routers.icb_advanced.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"{BASE}/robocizna/map", headers=auth_headers)

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_volatility_matrix_200(app, auth_headers):
    """GET /api/v2/icb/volatility-matrix → 200."""
    with patch("services.api.services.api.routers.icb_advanced.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"{BASE}/volatility-matrix", headers=auth_headers)

    assert resp.status_code == 200
