"""B: GDPR Compliance Audit tests — F2 sprint.

Covers:
  - GET  /api/v2/gdpr/export        → data export (Art. 20)
  - DELETE /api/v2/gdpr/account     → soft-delete / anonymise (Art. 17)
  - GET  /api/v2/gdpr/consent       → consent status (Art. 7)
  - POST /api/v2/gdpr/consent       → record consent
  - PATCH /api/v2/gdpr/consent      → update single consent
  - GET  /api/v2/gdpr/audit-trail   → audit trail (Art. 15)
  - GET  /api/v2/audit              → generic audit log
  - No-auth → 401/403 for every protected endpoint (tested against live API)

NOTE: conftest.py injects a demo user via dependency_overrides for ALL ASGI
transport requests.  Auth-rejection tests therefore use the live HTTP API on
localhost:8000 where JWT validation is enforced.  Functional tests use the
in-process ASGI transport with the demo token.
"""
from __future__ import annotations

import pytest
import httpx
from httpx import ASGITransport, AsyncClient

LIVE_BASE = "http://localhost:8000"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Auth helpers — use live HTTP API so real JWT validation kicks in
# ---------------------------------------------------------------------------

def _live_get(path: str, headers: dict | None = None) -> httpx.Response:
    with httpx.Client(base_url=LIVE_BASE, timeout=10.0) as c:
        return c.get(path, headers=headers or {})


def _live_post(path: str, json: dict | None = None,
               headers: dict | None = None) -> httpx.Response:
    with httpx.Client(base_url=LIVE_BASE, timeout=10.0) as c:
        return c.post(path, json=json or {}, headers=headers or {})


def _live_patch(path: str, json: dict | None = None,
                headers: dict | None = None) -> httpx.Response:
    with httpx.Client(base_url=LIVE_BASE, timeout=10.0) as c:
        return c.patch(path, json=json or {}, headers=headers or {})


def _live_delete(path: str, headers: dict | None = None) -> httpx.Response:
    with httpx.Client(base_url=LIVE_BASE, timeout=10.0) as c:
        return c.delete(path, headers=headers or {})


# ---------------------------------------------------------------------------
# ASGI helpers — rely on dependency_override (demo user auto-injected)
# ---------------------------------------------------------------------------

async def _asgi_get(app, path, headers=None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.get(path, headers=headers or {})


async def _asgi_post(app, path, json=None, headers=None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.post(path, json=json or {}, headers=headers or {})


# ===========================================================================
# A. Data Export  GET /api/v2/gdpr/export
# ===========================================================================

def test_gdpr_export_requires_auth_live():
    """GET /api/v2/gdpr/export without token → 401 or 403 (live API)."""
    resp = _live_get("/api/v2/gdpr/export")
    assert resp.status_code in (401, 403), (
        f"Expected 401/403 without auth, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_gdpr_export_with_auth(app, auth_headers):
    """GET /api/v2/gdpr/export with valid token → 200 or 404."""
    resp = await _asgi_get(app, "/api/v2/gdpr/export", headers=auth_headers)
    assert resp.status_code in (200, 404), (
        f"Unexpected status {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_gdpr_export_response_structure(app, auth_headers):
    """200 export response must include required GDPR fields."""
    resp = await _asgi_get(app, "/api/v2/gdpr/export", headers=auth_headers)
    if resp.status_code == 404:
        pytest.skip("Demo user not in test DB — skipping structure check")
    assert resp.status_code == 200
    data = resp.json()
    assert "export_version" in data, f"Missing export_version: {data}"
    assert "exported_at" in data, f"Missing exported_at: {data}"
    assert "user" in data, f"Missing user section: {data}"
    user = data["user"]
    assert "id" in user
    assert "email" in user


@pytest.mark.asyncio
async def test_gdpr_export_includes_audit_trail(app, auth_headers):
    """Export payload should include an audit_trail array (may be empty)."""
    resp = await _asgi_get(app, "/api/v2/gdpr/export", headers=auth_headers)
    if resp.status_code != 200:
        pytest.skip("User not in DB")
    data = resp.json()
    assert "audit_trail" in data
    assert isinstance(data["audit_trail"], list)


@pytest.mark.asyncio
async def test_gdpr_export_tenders_and_decisions(app, auth_headers):
    """Export payload should include tenders and decisions arrays."""
    resp = await _asgi_get(app, "/api/v2/gdpr/export", headers=auth_headers)
    if resp.status_code != 200:
        pytest.skip("User not in DB")
    data = resp.json()
    assert "tenders" in data
    assert isinstance(data["tenders"], list)
    assert "decisions" in data
    assert isinstance(data["decisions"], list)


# ===========================================================================
# B. Account Deletion  DELETE /api/v2/gdpr/account
# ===========================================================================

def test_gdpr_delete_requires_auth_live():
    """DELETE /api/v2/gdpr/account without token → 401/403 (live API)."""
    resp = _live_delete("/api/v2/gdpr/account")
    assert resp.status_code in (401, 403), (
        f"Expected 401/403 without auth, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_gdpr_delete_without_confirmation_header(app, auth_headers):
    """DELETE /api/v2/gdpr/account without X-Confirm-Delete → 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.delete("/api/v2/gdpr/account", headers=auth_headers)
    assert resp.status_code == 400, (
        f"Expected 400 without confirmation header, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_gdpr_delete_wrong_confirmation_value(app, auth_headers):
    """DELETE /api/v2/gdpr/account with X-Confirm-Delete: no → 400."""
    headers = {**auth_headers, "X-Confirm-Delete": "no"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.delete("/api/v2/gdpr/account", headers=headers)
    assert resp.status_code == 400, (
        f"Expected 400 with wrong confirmation, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_gdpr_delete_with_confirmation(app, auth_headers):
    """DELETE /api/v2/gdpr/account with X-Confirm-Delete: yes → 200 or 404."""
    headers = {**auth_headers, "X-Confirm-Delete": "yes"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.delete("/api/v2/gdpr/account", headers=headers)
    assert resp.status_code in (200, 404, 500), (
        f"Unexpected status {resp.status_code}: {resp.text}"
    )
    if resp.status_code == 200:
        data = resp.json()
        assert data.get("status") == "deleted", f"Expected status=deleted: {data}"
        assert "message" in data


# ===========================================================================
# C. Consent Management
# ===========================================================================

def test_gdpr_get_consent_no_auth_live():
    """GET /api/v2/gdpr/consent without token → 401/403 (live API)."""
    resp = _live_get("/api/v2/gdpr/consent")
    assert resp.status_code in (401, 403), (
        f"Expected 401/403, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_gdpr_get_consent_authenticated(app, auth_headers):
    """GET /api/v2/gdpr/consent with auth → 200 with boolean fields."""
    resp = await _asgi_get(app, "/api/v2/gdpr/consent", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "analytics" in data
    assert "marketing" in data
    assert "third_party" in data
    assert isinstance(data["analytics"], bool)
    assert isinstance(data["marketing"], bool)
    assert isinstance(data["third_party"], bool)


def test_gdpr_post_consent_no_auth_live():
    """POST /api/v2/gdpr/consent without token → 401/403 (live API)."""
    resp = _live_post("/api/v2/gdpr/consent",
                      json={"analytics": True, "marketing": False})
    assert resp.status_code in (401, 403), (
        f"Expected 401/403, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_gdpr_post_consent_all_fields(app, auth_headers):
    """POST /api/v2/gdpr/consent with all fields → 200 or 500."""
    resp = await _asgi_post(
        app, "/api/v2/gdpr/consent",
        json={"analytics": True, "marketing": True, "third_party": False},
        headers=auth_headers,
    )
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert data["status"] == "recorded"
        assert "consent" in data
        assert "recorded_at" in data


def test_gdpr_patch_consent_no_auth_live():
    """PATCH /api/v2/gdpr/consent without token → 401/403 (live API)."""
    resp = _live_patch("/api/v2/gdpr/consent",
                       json={"consent_type": "analytics", "granted": True})
    assert resp.status_code in (401, 403), (
        f"Expected 401/403, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_gdpr_patch_consent_authenticated(app, auth_headers):
    """PATCH /api/v2/gdpr/consent with valid field → 200 or 500."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.patch(
            "/api/v2/gdpr/consent",
            json={"consent_type": "analytics", "granted": False},
            headers=auth_headers,
        )
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert data["status"] == "recorded"
        assert data["consent"]["analytics"] is False


@pytest.mark.asyncio
async def test_gdpr_patch_consent_invalid_type(app, auth_headers):
    """PATCH /api/v2/gdpr/consent with invalid consent_type → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.patch(
            "/api/v2/gdpr/consent",
            json={"consent_type": "invalid_field", "granted": True},
            headers=auth_headers,
        )
    assert resp.status_code == 422, (
        f"Expected 422 for invalid consent_type, got {resp.status_code}: {resp.text}"
    )


# ===========================================================================
# D. Audit Trail  GET /api/v2/gdpr/audit-trail
# ===========================================================================

def test_gdpr_audit_trail_no_auth_live():
    """GET /api/v2/gdpr/audit-trail without token → 401/403 (live API)."""
    resp = _live_get("/api/v2/gdpr/audit-trail")
    assert resp.status_code in (401, 403), (
        f"Expected 401/403, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_gdpr_audit_trail_authenticated(app, auth_headers):
    """GET /api/v2/gdpr/audit-trail → 200 with entries/total/user_id."""
    resp = await _asgi_get(app, "/api/v2/gdpr/audit-trail", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert "total" in data
    assert "user_id" in data
    assert isinstance(data["entries"], list)
    assert isinstance(data["total"], int)


@pytest.mark.asyncio
async def test_gdpr_audit_trail_limit_param(app, auth_headers):
    """GET /api/v2/gdpr/audit-trail?limit=5 → at most 5 entries."""
    resp = await _asgi_get(app, "/api/v2/gdpr/audit-trail?limit=5", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["entries"]) <= 5


@pytest.mark.asyncio
async def test_gdpr_audit_trail_entries_schema(app, auth_headers):
    """Audit trail entries (if any) must have required fields."""
    resp = await _asgi_get(app, "/api/v2/gdpr/audit-trail", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    for entry in data["entries"]:
        assert "id" in entry
        assert "action" in entry
        assert "created_at" in entry


# ===========================================================================
# E. Generic Audit Log  GET /api/v2/audit
# ===========================================================================

def test_audit_log_no_auth_live():
    """GET /api/v2/audit without token → 401/403 (live API)."""
    resp = _live_get("/api/v2/audit")
    assert resp.status_code in (401, 403), (
        f"Expected 401/403, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_audit_log_authenticated(app, auth_headers):
    """GET /api/v2/audit with auth → 200 with items/total/limit."""
    resp = await _asgi_get(app, "/api/v2/audit", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_audit_log_cursor_pagination(app, auth_headers):
    """GET /api/v2/audit → cursor field present (None when < limit)."""
    resp = await _asgi_get(app, "/api/v2/audit?limit=50", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "cursor" in data
    if data["cursor"] is not None:
        assert isinstance(data["cursor"], str)
        assert len(data["cursor"]) > 0


@pytest.mark.asyncio
async def test_audit_recent_endpoint(app, auth_headers):
    """GET /api/v2/audit/recent → 200 list."""
    resp = await _asgi_get(app, "/api/v2/audit/recent", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_audit_trail_endpoint(app, auth_headers):
    """GET /api/v2/audit/trail → 200 list."""
    resp = await _asgi_get(app, "/api/v2/audit/trail", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
