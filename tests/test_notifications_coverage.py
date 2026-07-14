"""C1-3 — Notifications router coverage: routers/notifications.py (28% → 65%+).

Tests for /api/v2/notifications/* endpoints.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


# ─── App + auth fixtures ─────────────────────────────────────────────────────

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


# ─── GET /api/v2/notifications ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notifications_list_200(app, auth_headers):
    """GET /api/v2/notifications → 200 with items list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/notifications", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_notifications_list_has_next_cursor(app, auth_headers):
    """GET /api/v2/notifications → has next_cursor field."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/notifications", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "next_cursor" in data


@pytest.mark.asyncio
async def test_notifications_list_unread_filter(app, auth_headers):
    """GET /api/v2/notifications?unread=true → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/notifications?unread=true", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    # All items should be unread
    for item in data["items"]:
        assert item["read"] is False


@pytest.mark.asyncio
async def test_notifications_list_limit_param(app, auth_headers):
    """GET /api/v2/notifications?limit=5 → 200, respects limit."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/notifications?limit=5", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 5


@pytest.mark.asyncio
async def test_notifications_list_invalid_cursor(app, auth_headers):
    """GET /api/v2/notifications?cursor=BADCURSOR → 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/notifications?cursor=BADCURSOR", headers=auth_headers)
    assert resp.status_code == 400


# ─── GET /api/v2/notifications/count ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_notifications_count_200(app, auth_headers):
    """GET /api/v2/notifications/count → 200 with unread_count."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/notifications/count", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "unread_count" in data
    assert isinstance(data["unread_count"], int)
    assert data["unread_count"] >= 0


@pytest.mark.asyncio
async def test_notifications_unread_count_alias(app, auth_headers):
    """GET /api/v2/notifications/unread-count → 200 (alias endpoint)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/notifications/unread-count", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "unread_count" in data


# ─── POST /api/v2/notifications/read-all ─────────────────────────────────────

@pytest.mark.asyncio
async def test_notifications_read_all_200(app, auth_headers):
    """POST /api/v2/notifications/read-all → 200 with updated count."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v2/notifications/read-all", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "updated" in data
    assert isinstance(data["updated"], int)


@pytest.mark.asyncio
async def test_notifications_read_all_idempotent(app, auth_headers):
    """POST /api/v2/notifications/read-all twice → 200 both times."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.post("/api/v2/notifications/read-all", headers=auth_headers)
        r2 = await client.post("/api/v2/notifications/read-all", headers=auth_headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Second call should update 0 (already all read)
    assert r2.json()["updated"] == 0


# ─── POST /{id}/read ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notifications_mark_single_not_found(app, auth_headers):
    """POST /api/v2/notifications/{fake_id}/read → 404 for unknown id."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v2/notifications/{fake_id}/read",
            headers=auth_headers,
        )
    assert resp.status_code == 404


# ─── PUT /{id}/read ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notifications_put_mark_read_not_found(app, auth_headers):
    """PUT /api/v2/notifications/{fake_id}/read → 404."""
    fake_id = "00000000-0000-0000-0000-000000000001"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.put(
            f"/api/v2/notifications/{fake_id}/read",
            headers=auth_headers,
        )
    assert resp.status_code == 404


# ─── DELETE /{id} ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notifications_delete_not_found(app, auth_headers):
    """DELETE /api/v2/notifications/{fake_id} → 404 for unknown id."""
    fake_id = "00000000-0000-0000-0000-000000000002"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            f"/api/v2/notifications/{fake_id}",
            headers=auth_headers,
        )
    assert resp.status_code == 404
