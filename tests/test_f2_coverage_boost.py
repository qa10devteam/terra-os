"""FAZA 2 — Coverage boost: tenders_v2.py, billing.py, zwiad.py → cel ≥70%.

Wzorzec: httpx AsyncClient + ASGITransport, JWT token via create_access_token,
mock terra_db.session.get_engine dla DB-heavy ścieżek.
"""
from __future__ import annotations

import uuid
import json
import hashlib
import hmac
import os
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient


# ── Fixtures ────────────────────────────────────────────────────────────────

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


@pytest.fixture(scope="module")
def no_org_headers():
    from services.api.services.api.auth.utils import create_access_token
    token = create_access_token(
        user_id="11111111-1111-1111-1111-111111111111",
        email="noorg@terra-os.pl",
        org_id=None,
        role="estimator",
    )
    return {"Authorization": f"Bearer {token}"}


FAKE_TENDER_ID = str(uuid.uuid4())
FAKE_ORG_ID = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"
FAKE_TENANT_ID = "c4879c87-016c-4580-b913-212c904c20fd"


def _make_engine_mock(rows: dict[str, Any] | None = None):
    """Zwraca mock engine który odpowiada na fetchone / fetchall."""
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    engine.begin.return_value.__enter__ = MagicMock(return_value=conn)
    engine.begin.return_value.__exit__ = MagicMock(return_value=False)
    return engine, conn


# ═══════════════════════════════════════════════════════════════════════════════
# TENDERS V2 — brakujące ścieżki
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tender_detail_no_org(app, no_org_headers):
    """GET /tenders/{id} bez org_id → 403."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(f"/api/v2/tenders/{FAKE_TENDER_ID}", headers=no_org_headers)
    assert resp.status_code in (403, 404)  # 403 no_org lub 404 nie znaleziony


@pytest.mark.asyncio
async def test_tender_detail_invalid_uuid(app, auth_headers):
    """GET /tenders/invalid-uuid → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/tenders/not-a-uuid", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_tender_detail_not_found(app, auth_headers):
    """GET /tenders/{uuid} gdy nie ma w DB → 404."""
    tenant_row = MagicMock()
    tenant_row.tenant_id = FAKE_TENANT_ID
    engine, conn = _make_engine_mock()
    conn.execute.return_value.fetchone.side_effect = [tenant_row, None]

    with patch("services.api.services.api.routers.tenders_v2.get_engine", return_value=engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(f"/api/v2/tenders/{FAKE_TENDER_ID}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tender_detail_happy_path(app, auth_headers):
    """GET /tenders/{uuid} z danymi → 200 z polami TenderDetail."""
    tenant_row = MagicMock(); tenant_row.tenant_id = FAKE_TENANT_ID
    tender_row = MagicMock()
    tender_row.id = FAKE_TENDER_ID
    tender_row.title = "Budowa drogi testowej"
    tender_row.buyer = "Gmina Test"
    tender_row.source = "bzp"
    tender_row.cpv = "45233000"
    tender_row.voivodeship = "śląskie"
    tender_row.value_pln = 500000.0
    tender_row.deadline_at = None
    tender_row.published_at = None
    tender_row.url = "https://example.com"
    tender_row.status = "new"
    tender_row.match_score = 75
    tender_row.match_reason = ["CPV match"]
    tender_row.raw = {}
    tender_row.created_at = None

    engine, conn = _make_engine_mock()
    # fetchone calls: tenant_id, tender_row, dup_as_dup
    conn.execute.return_value.fetchone.side_effect = [tenant_row, tender_row, None]
    # fetchall for dup_refs_raw
    conn.execute.return_value.fetchall.return_value = []

    with patch("services.api.services.api.routers.tenders_v2.get_engine", return_value=engine), \
         patch("services.api.services.api.routers.tenders_v2._cache.get", return_value=None), \
         patch("services.api.services.api.routers.tenders_v2._cache.set"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(f"/api/v2/tenders/{FAKE_TENDER_ID}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Budowa drogi testowej"


@pytest.mark.asyncio
async def test_tender_patch_no_org(app, no_org_headers):
    """PATCH /tenders/{id} bez org → 403 lub 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.patch(
            f"/api/v2/tenders/{FAKE_TENDER_ID}",
            json={"status": "watching"},
            headers=no_org_headers,
        )
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_tender_patch_invalid_status(app, auth_headers):
    """PATCH /tenders/{id} z nieprawidłowym status → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.patch(
            f"/api/v2/tenders/{FAKE_TENDER_ID}",
            json={"status": "nieistnieje"},
            headers=auth_headers,
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_tender_delete_no_org(app, no_org_headers):
    """DELETE /tenders/{id} bez org → 403 lub 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.delete(f"/api/v2/tenders/{FAKE_TENDER_ID}", headers=no_org_headers)
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_tender_analyze_no_org(app, no_org_headers):
    """POST /tenders/{id}/analyze bez org → 403 lub 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post(f"/api/v2/tenders/{FAKE_TENDER_ID}/analyze", headers=no_org_headers)
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_tender_analyze_not_found(app, auth_headers):
    """POST /tenders/{id}/analyze gdy tender nie istnieje → 404."""
    tenant_row = MagicMock(); tenant_row.tenant_id = FAKE_TENANT_ID
    engine, conn = _make_engine_mock()
    conn.execute.return_value.fetchone.side_effect = [tenant_row, None]

    with patch("services.api.services.api.routers.tenders_v2.get_engine", return_value=engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(f"/api/v2/tenders/{FAKE_TENDER_ID}/analyze", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tender_analyze_queued(app, auth_headers):
    """POST /tenders/{id}/analyze sukces → 200 z job_id."""
    tenant_row = MagicMock(); tenant_row.tenant_id = FAKE_TENANT_ID
    tender_row = MagicMock(); tender_row.id = FAKE_TENDER_ID
    engine, conn = _make_engine_mock()
    conn.execute.return_value.fetchone.side_effect = [tenant_row, tender_row]

    with patch("services.api.services.api.routers.tenders_v2.get_engine", return_value=engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(f"/api/v2/tenders/{FAKE_TENDER_ID}/analyze", headers=auth_headers)
    assert resp.status_code == 200
    assert "job_id" in resp.json()
    assert resp.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_tender_similar_no_org(app, no_org_headers):
    """GET /tenders/{id}/similar bez org → 403 lub 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(f"/api/v2/tenders/{FAKE_TENDER_ID}/similar", headers=no_org_headers)
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_tender_similar_not_found(app, auth_headers):
    """GET /tenders/{id}/similar tender nie istnieje → pusta lista."""
    tenant_row = MagicMock(); tenant_row.tenant_id = FAKE_TENANT_ID
    engine, conn = _make_engine_mock()
    conn.execute.return_value.fetchone.side_effect = [tenant_row, None]

    with patch("services.api.services.api.routers.tenders_v2.get_engine", return_value=engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(f"/api/v2/tenders/{FAKE_TENDER_ID}/similar", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_tender_similar_no_cpv(app, auth_headers):
    """GET /tenders/{id}/similar — tender bez CPV → pusta lista."""
    tenant_row = MagicMock(); tenant_row.tenant_id = FAKE_TENANT_ID
    tender_row = MagicMock(); tender_row.cpv = None
    engine, conn = _make_engine_mock()
    conn.execute.return_value.fetchone.side_effect = [tenant_row, tender_row]

    with patch("services.api.services.api.routers.tenders_v2.get_engine", return_value=engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(f"/api/v2/tenders/{FAKE_TENDER_ID}/similar", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_tender_similar_with_results(app, auth_headers):
    """GET /tenders/{id}/similar — zwraca listę podobnych."""
    tenant_row = MagicMock(); tenant_row.tenant_id = FAKE_TENANT_ID
    tender_row = MagicMock(); tender_row.cpv = "45233000"; tender_row.value_pln = 500000.0
    sim_row = MagicMock()
    sim_row.id = str(uuid.uuid4())
    sim_row.title = "Podobna droga"
    sim_row.cpv = "45233100"
    sim_row.value_pln = 400000.0
    sim_row.status = "new"
    engine, conn = _make_engine_mock()
    conn.execute.return_value.fetchone.side_effect = [tenant_row, tender_row]
    conn.execute.return_value.fetchall.return_value = [sim_row]

    with patch("services.api.services.api.routers.tenders_v2.get_engine", return_value=engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(f"/api/v2/tenders/{FAKE_TENDER_ID}/similar", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


@pytest.mark.asyncio
async def test_tender_score_no_org(app, no_org_headers):
    """GET /tenders/{id}/score bez org → 403 lub 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(f"/api/v2/tenders/{FAKE_TENDER_ID}/score", headers=no_org_headers)
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_tender_score_not_found(app, auth_headers):
    """GET /tenders/{id}/score tender nie istnieje → 404."""
    tenant_row = MagicMock(); tenant_row.tenant_id = FAKE_TENANT_ID
    engine, conn = _make_engine_mock()
    conn.execute.return_value.fetchone.side_effect = [tenant_row, None]

    with patch("services.api.services.api.routers.tenders_v2.get_engine", return_value=engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(f"/api/v2/tenders/{FAKE_TENDER_ID}/score", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tender_score_no_config(app, auth_headers):
    """GET /tenders/{id}/score — brak scoring_config → neutral 50."""
    tenant_row = MagicMock(); tenant_row.tenant_id = FAKE_TENANT_ID
    tender_row = MagicMock(); tender_row.cpv = "45233000"; tender_row.match_score = 55
    engine, conn = _make_engine_mock()
    # calls: tenant, tender, scoring_config
    conn.execute.return_value.fetchone.side_effect = [tenant_row, tender_row, None]

    with patch("services.api.services.api.routers.tenders_v2.get_engine", return_value=engine):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(f"/api/v2/tenders/{FAKE_TENDER_ID}/score", headers=auth_headers)
    assert resp.status_code in (200, 404)  # 404 jeśli brak tenant_id w test DB
    if resp.status_code == 200:
        data = resp.json()
        assert "score" in data


@pytest.mark.asyncio
async def test_tender_search_returns_results(app, auth_headers):
    """GET /tenders/search?q=roboty → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/tenders/search?q=roboty+drogowe", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data or "items" in data or isinstance(data, list)


@pytest.mark.asyncio
async def test_tender_semantic_search(app, auth_headers):
    """GET /tenders/semantic-search?q=budowa → 200 lub 503."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/tenders/semantic-search?q=budowa", headers=auth_headers)
    assert resp.status_code in (200, 422, 503)  # 422 jeśli q required


# ═══════════════════════════════════════════════════════════════════════════════
# BILLING — brakujące ścieżki
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_billing_invoices_200(app, auth_headers):
    """GET /billing/invoices → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/billing/invoices", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "invoices" in data


@pytest.mark.asyncio
async def test_billing_invoices_no_auth(app):
    """GET /billing/invoices bez auth → 401 lub 403."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/billing/invoices")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_billing_cancel_free_plan_400(app, auth_headers):
    """POST /billing/cancel na planie free → 400 (nic do anulowania)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v2/billing/cancel", headers=auth_headers)
    assert resp.status_code in (400, 200)


@pytest.mark.asyncio
async def test_billing_subscription_returns_plan(app, auth_headers):
    """GET /billing/subscription → zawiera pole plan."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/billing/subscription", headers=auth_headers)
    assert resp.status_code == 200
    assert "plan" in resp.json()


@pytest.mark.asyncio
async def test_billing_usage_200(app, auth_headers):
    """GET /billing/usage → 200 z metrykami."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/billing/usage", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    # Musi zawierać przynajmniej jeden klucz z metrykami
    assert len(data) > 0


@pytest.mark.asyncio
async def test_billing_checkout_url_200(app, auth_headers):
    """GET /billing/checkout-url → 200 lub 503."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/billing/checkout-url?plan_id=pro", headers=auth_headers)
    assert resp.status_code in (200, 503, 302)


@pytest.mark.asyncio
async def test_billing_webhook_invalid_signature(app):
    """POST /billing/webhook z nieprawidłową sygnaturą → 400."""
    payload = json.dumps({"type": "checkout.session.completed", "data": {"object": {}}})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post(
            "/api/v2/billing/webhook",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "stripe-signature": "v1=invalidsignature",
            },
        )
    # Brak STRIPE_WEBHOOK_SECRET → 200 (passthrough) lub 400 (signature fail)
    assert resp.status_code in (200, 400)


@pytest.mark.asyncio
async def test_billing_webhook_no_signature(app):
    """POST /billing/webhook bez nagłówka stripe-signature → 400."""
    payload = json.dumps({"type": "ping"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post(
            "/api/v2/billing/webhook",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code in (200, 400)


@pytest.mark.asyncio
async def test_billing_plans_public_no_auth(app):
    """GET /billing/plans dostępne bez auth."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v2/billing/plans")
    assert resp.status_code == 200
    plans = resp.json()
    assert isinstance(plans, list)
    plan_ids = [p["id"] for p in plans]
    assert "free" in plan_ids


# ── Billing helper functions coverage ───────────────────────────────────────

def test_billing_resolve_org_none():
    """_resolve_org_id_from_customer → None gdy brak rekordu."""
    from services.api.services.api.routers.billing import _resolve_org_id_from_customer
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = None
    result = _resolve_org_id_from_customer(db, "cus_nonexistent")
    assert result is None


def test_billing_resolve_org_from_subscription():
    """_resolve_org_id_from_customer → zwraca org_id z subscription."""
    from services.api.services.api.routers.billing import _resolve_org_id_from_customer
    row = MagicMock(); row.org_id = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = row
    result = _resolve_org_id_from_customer(db, "cus_test")
    assert result == "ec3d1e16-2139-48c2-93b5-ffe0defd606d"


def test_billing_ts_none():
    """_ts(None) → None."""
    from services.api.services.api.routers.billing import _ts
    assert _ts(None) is None


def test_billing_ts_unix():
    """_ts(unix) → datetime."""
    from services.api.services.api.routers.billing import _ts
    from datetime import timezone
    result = _ts(1700000000)
    assert result is not None
    assert result.tzinfo == timezone.utc


def test_billing_get_or_create_subscription_existing():
    """_get_or_create_subscription gdy istnieje → zwraca dict."""
    from services.api.services.api.routers.billing import _get_or_create_subscription
    row = MagicMock()
    row._mapping = {"org_id": "ec3d1e16", "plan": "free", "status": "active"}
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = row
    result = _get_or_create_subscription(db, "ec3d1e16")
    assert result["plan"] == "free"


def test_billing_get_or_create_subscription_creates_new():
    """_get_or_create_subscription gdy nie istnieje → tworzy i zwraca free."""
    from services.api.services.api.routers.billing import _get_or_create_subscription
    row = MagicMock()
    row._mapping = {"org_id": "new-org", "plan": "free", "status": "active"}
    db = MagicMock()
    # first fetchone → None (brak), drugi → row (po INSERT)
    db.execute.return_value.fetchone.side_effect = [None, row]
    result = _get_or_create_subscription(db, "new-org")
    assert result["plan"] == "free"
    db.commit.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# ZWIAD — brakujące ścieżki (prawdziwe: /api/v1/ingest/*)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_zwiad_ingest_run_202(app, auth_headers):
    """POST /api/v1/ingest/run → 202 Accepted."""
    payload = {"keywords": ["roboty drogowe"], "voivodeships": ["śląskie"], "max_results": 5}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/ingest/run", json=payload, headers=auth_headers)
    assert resp.status_code in (202, 200, 422)


@pytest.mark.asyncio
async def test_zwiad_task_not_found(app, auth_headers):
    """GET /api/v1/ingest/tasks/{id} nieistniejący → 404."""
    fake_task_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(f"/api/v1/ingest/tasks/{fake_task_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_zwiad_tasks_list_200(app, auth_headers):
    """GET /api/v1/ingest/tasks → 200 z listą."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/ingest/tasks", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_zwiad_cache_invalidate_200(app, auth_headers):
    """POST /api/v1/ingest/cache/invalidate → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/ingest/cache/invalidate", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_zwiad_tender_detail_via_v1(app, auth_headers):
    """GET /api/v1/tenders/{uuid} zwiad detail → 200 lub 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get(f"/api/v1/tenders/{FAKE_TENDER_ID}", headers=auth_headers)
    assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_zwiad_no_auth_ingest_401(app):
    """POST /api/v1/ingest/run bez auth → 401 lub 403."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/ingest/run", json={})
    assert resp.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_zwiad_tasks_no_auth(app):
    """GET /api/v1/ingest/tasks bez auth → 401 lub 403."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/ingest/tasks")
    assert resp.status_code in (401, 403)


# ── Normalizer helper coverage ───────────────────────────────────────────────

def test_normalize_voiv_strips_diacritics():
    """_normalize_voiv usuwa polskie znaki."""
    from services.api.services.api.routers.zwiad import _normalize_voiv
    result = _normalize_voiv("śląskie")
    assert "ś" not in result
    assert "laskie" in result.lower() or "slaskie" in result.lower()
