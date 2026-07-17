"""F2 — Integration tests for Terra-OS live API (http://localhost:8000).

Tests run against a real running API server with real PostgreSQL.
Marks: integration (skipped in CI unless TERRA_INTEGRATION=1 is set).

User test41@terra.os has password Test1234! (bcrypt updated in DB).
User existing@example.com has org_id — used for org-scoped endpoints.
"""
from __future__ import annotations

import os
import pytest
import httpx

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE = os.getenv("TERRA_API_BASE", "http://127.0.0.1:8000")
TEST_EMAIL = os.getenv("TERRA_TEST_EMAIL", "existing@example.com")
TEST_PASS = os.getenv("TERRA_TEST_PASS", "Test1234!")

# Secondary user (no org) — for no-org tests
NO_ORG_EMAIL = os.getenv("TERRA_NO_ORG_EMAIL", "test41@terra.os")
NO_ORG_PASS = os.getenv("TERRA_NO_ORG_PASS", "Test1234!")

pytestmark = pytest.mark.integration


# ── Session-scoped fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client():
    """Shared httpx client, TESTING=1 bypasses rate-limiter."""
    with httpx.Client(
        base_url=API_BASE,
        headers={"X-Testing": "1"},
        timeout=10,
        follow_redirects=True,
    ) as c:
        yield c


@pytest.fixture(scope="session")
def token(client):
    """Obtain JWT for the org user once per test session."""
    # Use TESTING env to bypass 5-req/min rate limiter
    resp = client.post(
        "/api/v2/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASS},
        headers={"X-Testing": "1"},
    )
    assert resp.status_code == 200, f"Login failed ({resp.status_code}): {resp.text}"
    data = resp.json()
    assert "access_token" in data, f"No access_token in response: {data}"
    return data["access_token"]


@pytest.fixture(scope="session")
def auth(token):
    """Authorization header dict for authenticated requests."""
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def no_org_token(client):
    """Token for user without organisation (test41@terra.os)."""
    resp = client.post(
        "/api/v2/auth/login",
        json={"email": NO_ORG_EMAIL, "password": NO_ORG_PASS},
    )
    assert resp.status_code == 200, f"no-org login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def no_org_auth(no_org_token):
    return {"Authorization": f"Bearer {no_org_token}"}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Health
# ═══════════════════════════════════════════════════════════════════════════════

def test_health_status_ok(client):
    """GET /api/v2/health → 200, status=ok, db=ok."""
    r = client.get("/api/v2/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"


def test_health_has_version(client):
    """GET /api/v2/health → response contains version field."""
    r = client.get("/api/v2/health")
    assert r.status_code == 200
    body = r.json()
    assert "version" in body
    assert body["version"]  # non-empty


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Auth — login
# ═══════════════════════════════════════════════════════════════════════════════

def test_auth_login_valid(client):
    """POST /api/v2/auth/login with valid credentials → 200, access_token present."""
    r = client.post(
        "/api/v2/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASS},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert len(body["access_token"]) > 20
    assert body.get("token_type") == "bearer"


def test_auth_login_invalid_password(client):
    """POST /api/v2/auth/login with wrong password → 401."""
    r = client.post(
        "/api/v2/auth/login",
        json={"email": TEST_EMAIL, "password": "wrong_password_xyz"},
    )
    assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"


def test_auth_login_unknown_email(client):
    """POST /api/v2/auth/login with unknown email → 401."""
    r = client.post(
        "/api/v2/auth/login",
        json={"email": "nobody@nowhere.invalid", "password": "password"},
    )
    assert r.status_code == 401


def test_auth_login_missing_fields(client):
    """POST /api/v2/auth/login with empty body → 422 validation error."""
    r = client.post("/api/v2/auth/login", json={})
    assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Auth — /me
# ═══════════════════════════════════════════════════════════════════════════════

def test_auth_me_returns_user(client, auth):
    """GET /api/v2/auth/me → 200, returns email and id."""
    r = client.get("/api/v2/auth/me", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == TEST_EMAIL
    assert "id" in body


def test_auth_me_unauthorized(client):
    """GET /api/v2/auth/me without token → 401 or 403."""
    r = client.get("/api/v2/auth/me")
    assert r.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Tenders
# ═══════════════════════════════════════════════════════════════════════════════

def test_tenders_list_authenticated(client, auth):
    """GET /api/v2/tenders → 200, response has items list and total."""
    r = client.get("/api/v2/tenders?limit=5", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert isinstance(body["items"], list)
    assert "total" in body
    assert isinstance(body["total"], int)


def test_tenders_list_unauthenticated(client):
    """GET /api/v2/tenders without token → 401 or 403."""
    r = client.get("/api/v2/tenders")
    assert r.status_code in (401, 403)


def test_tenders_list_pagination(client, auth):
    """GET /api/v2/tenders?limit=2 honours limit parameter."""
    r = client.get("/api/v2/tenders?limit=2", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["items"], list)
    assert len(body["items"]) <= 2


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Estimates
# ═══════════════════════════════════════════════════════════════════════════════

def test_estimates_requires_tender_id(client, auth):
    """GET /api/v2/estimates without tender_id → 422 (required param)."""
    r = client.get("/api/v2/estimates", headers=auth)
    assert r.status_code == 422


def test_estimates_invalid_tender_id(client, auth):
    """GET /api/v2/estimates?tender_id=nonexistent-uuid → 404 or empty list."""
    r = client.get(
        "/api/v2/estimates?tender_id=00000000-0000-0000-0000-000000000000",
        headers=auth,
    )
    # Either 404 (tender not found) or 200 with empty items
    assert r.status_code in (200, 404), f"Unexpected: {r.status_code} {r.text}"
    if r.status_code == 200:
        body = r.json()
        assert "items" in body or isinstance(body, list)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Dashboard stats
# ═══════════════════════════════════════════════════════════════════════════════

def test_dashboard_stats_authenticated(client, auth):
    """GET /api/v2/dashboard/stats → 200, has total_tenders integer."""
    r = client.get("/api/v2/dashboard/stats", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert "total_tenders" in body
    assert isinstance(body["total_tenders"], int)


def test_dashboard_stats_unauthenticated(client):
    """GET /api/v2/dashboard/stats without token → 401 or 403."""
    r = client.get("/api/v2/dashboard/stats")
    assert r.status_code in (401, 403)


def test_dashboard_stats_structure(client, auth):
    """GET /api/v2/dashboard/stats → response has expected keys."""
    r = client.get("/api/v2/dashboard/stats", headers=auth)
    assert r.status_code == 200
    body = r.json()
    # At minimum these keys must be present
    for key in ("total_tenders", "new_today", "new_this_week"):
        assert key in body, f"Missing key '{key}' in dashboard stats"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. BZP search
# ═══════════════════════════════════════════════════════════════════════════════

def test_bzp_tenders_endpoint_exists(client, auth):
    """GET /api/v2/bzp/tenders → 200, returns items list."""
    r = client.get("/api/v2/bzp/tenders?limit=2", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert isinstance(body["items"], list)


def test_search_query_roboty(client, auth):
    """GET /api/v2/search?q=roboty → 200, returns items list."""
    r = client.get("/api/v2/search?q=roboty&limit=5", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert isinstance(body["items"], list)
    # Check total and query fields if present
    if "total" in body:
        assert isinstance(body["total"], int)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Forgot password
# ═══════════════════════════════════════════════════════════════════════════════

def test_forgot_password_known_email(client):
    """POST /api/v2/auth/forgot-password with known email → 200, message returned."""
    r = client.post(
        "/api/v2/auth/forgot-password",
        json={"email": TEST_EMAIL},
    )
    assert r.status_code == 200
    body = r.json()
    # Response should have a message (not expose whether email exists)
    assert "message" in body or "detail" in body or "msg" in body


def test_forgot_password_unknown_email(client):
    """POST /api/v2/auth/forgot-password with unknown email → 200 (no info leak)."""
    r = client.post(
        "/api/v2/auth/forgot-password",
        json={"email": "nobody@nowhere.invalid"},
    )
    # Should NOT reveal if email exists — return 200 regardless
    assert r.status_code == 200


def test_forgot_password_missing_email(client):
    """POST /api/v2/auth/forgot-password with no body → 422."""
    r = client.post("/api/v2/auth/forgot-password", json={})
    assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Token validity and expiry
# ═══════════════════════════════════════════════════════════════════════════════

def test_invalid_token_rejected(client):
    """Any protected endpoint with garbage token → 401 or 403."""
    r = client.get(
        "/api/v2/auth/me",
        headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
    )
    assert r.status_code in (401, 403)


def test_bearer_prefix_required(client):
    """Protected endpoint with raw token (no Bearer prefix) → 401 or 403."""
    fake_token = "eyJhbGciOiJIUzI1NiJ9.e30.invalid"
    r = client.get(
        "/api/v2/auth/me",
        headers={"Authorization": fake_token},
    )
    assert r.status_code in (401, 403)
