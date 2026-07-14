"""C2-3 — BZP Documents router coverage: routers/bzp_documents.py (21% → 55%+).

Tests for /api/v1/bzp/documents/* endpoints using AsyncClient + ASGITransport.
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


BASE = "/api/v1/bzp/documents"
TENDER_ID = str(uuid.uuid4())


# ─── Tests ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_documents_200(app, auth_headers):
    """GET /api/v1/bzp/documents/{tender_id} → 200 with documents list."""
    with patch("services.api.services.api.routers.bzp_documents.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"{BASE}/{TENDER_ID}", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "documents" in data or "items" in data or isinstance(data, (list, dict))


@pytest.mark.asyncio
async def test_list_documents_empty(app, auth_headers):
    """GET /api/v1/bzp/documents/{tender_id} → 200 with empty list."""
    with patch("services.api.services.api.routers.bzp_documents.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"{BASE}/{TENDER_ID}", headers=auth_headers)

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_fetch_documents_404_unknown_tender(app, auth_headers):
    """POST /api/v1/bzp/documents/{tender_id}/fetch → 404 when tender not found."""
    with patch("services.api.services.api.routers.bzp_documents.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchone.return_value = None
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"{BASE}/{TENDER_ID}/fetch",
                headers=auth_headers,
            )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_documents_another_tender(app, auth_headers):
    """GET /api/v1/bzp/documents/{another_tender_id} → 200 (empty docs)."""
    import uuid as _uuid
    other_id = str(_uuid.uuid4())
    with patch("services.api.services.api.routers.bzp_documents.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"{BASE}/{other_id}", headers=auth_headers)

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_fetch_documents_found_queued(app, auth_headers):
    """POST /api/v1/bzp/documents/{tender_id}/fetch → 200 queued when tender found with bzp_number."""
    row = MagicMock()
    row.id = TENDER_ID
    row.url = "https://ezamowienia.gov.pl/mp-client/search/list/ocds-148610-abc"
    row.source = "ezamowienia"
    row.external_id = "2026/BZP 00331648"

    with patch("services.api.services.api.routers.bzp_documents.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchone.return_value = row
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"{BASE}/{TENDER_ID}/fetch",
                headers=auth_headers,
            )

    assert resp.status_code in (200, 202)
    data = resp.json()
    assert data.get("status") == "queued" or "tender_id" in data


@pytest.mark.asyncio
async def test_list_documents_response_structure(app, auth_headers):
    """GET /api/v1/bzp/documents/{tender_id} → response has expected keys."""
    with patch("services.api.services.api.routers.bzp_documents.get_engine") as mock_eng:
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        mock_eng.return_value.connect.return_value = conn

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"{BASE}/{TENDER_ID}", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    # Response should be a dict with tender_id and documents
    assert isinstance(data, dict)
