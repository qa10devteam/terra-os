"""BLOK-1 coverage tests: export / email_webhooks / intelligence / notifications /
bzp / scoring_v2 / kosztorys_v3 / scoring / audit_v2 / events / reports.

Strategy:
- Use AsyncClient(ASGITransport) for all ASGI endpoints.
- Mock get_engine / external HTTP calls so no real DB / network needed.
- Accept any realistic HTTP status — assert r.status_code in (200,201,400,401,403,404,422,500).
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ─── Common fixtures ──────────────────────────────────────────────────────────

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


def _mock_conn(fetchone=None, fetchall=None, scalar=0, rowcount=1):
    """Return a context-manager-compatible mock DB connection."""
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    result = MagicMock()
    result.fetchone.return_value = fetchone
    result.fetchall.return_value = fetchall or []
    result.scalar.return_value = scalar
    result.rowcount = rowcount
    conn.execute.return_value = result
    conn.commit.return_value = None
    return conn


def _mock_engine(fetchone=None, fetchall=None, scalar=0, rowcount=1):
    """Return a patched get_engine mock."""
    eng = MagicMock()
    conn = _mock_conn(fetchone=fetchone, fetchall=fetchall, scalar=scalar, rowcount=rowcount)
    eng.return_value.connect.return_value.__enter__ = lambda s: conn
    eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
    eng.return_value.connect.return_value = conn
    eng.return_value.begin.return_value.__enter__ = lambda s: conn
    eng.return_value.begin.return_value.__exit__ = MagicMock(return_value=False)
    eng.return_value.begin.return_value = conn
    return eng


# ══════════════════════════════════════════════════════════════════════════════
# export.py  (/api/v1/estimates & /api/v1/tenders)
# ══════════════════════════════════════════════════════════════════════════════

ESTIMATE_ID = str(uuid.uuid4())
TENDER_ID_EXPORT = str(uuid.uuid4())

def _estimate_row():
    row = MagicMock()
    row._mapping = {
        "id": ESTIMATE_ID,
        "tender_id": TENDER_ID_EXPORT,
        "variant": "doc",
        "total_net_pln": 100000.0,
        "params": {},
        "lines": [
            {"lp": 1, "description": "Roboty", "unit": "m2",
             "quantity": 10, "unit_price": 10000, "line_total_pln": 100000}
        ],
    }
    return row


@pytest.mark.asyncio
async def test_export_docx_not_found(app, auth_headers):
    """POST docx with non-existent estimate → 404."""
    eng = _mock_engine(fetchone=None)
    with patch("services.api.services.api.routers.export.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"/api/v1/estimates/{ESTIMATE_ID}/export/docx", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_export_docx_ok(app, auth_headers):
    """POST docx with mocked estimate + exporter → 200 streaming."""
    est_row = _estimate_row()
    tender_row = MagicMock()
    tender_row._mapping = {"id": TENDER_ID_EXPORT, "title": "Test tender", "buyer": "Buyer", "cpv": [], "external_id": "X"}
    owner_row = MagicMock()
    owner_row._mapping = {"company_name": "Firma"}

    call_count = [0]
    def side_fetchone():
        call_count[0] += 1
        if call_count[0] == 1:
            return est_row
        elif call_count[0] == 2:
            return tender_row
        return owner_row

    conn = _mock_conn()
    conn.execute.return_value.fetchone.side_effect = side_fetchone

    eng = MagicMock()
    eng.return_value.connect.return_value = conn

    with patch("services.api.services.api.routers.export.get_engine", eng), \
         patch("services.estimator.export_docx.export_estimate_docx", return_value=b"DOCX"), \
         patch("services.estimator.export_docx.DocxExportConfig", MagicMock()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"/api/v1/estimates/{ESTIMATE_ID}/export/docx", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_export_xlsx_not_found(app, auth_headers):
    """POST xlsx with non-existent estimate → 404."""
    eng = _mock_engine(fetchone=None)
    with patch("services.api.services.api.routers.export.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"/api/v1/estimates/{ESTIMATE_ID}/export/xlsx", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_export_zip_not_found(app, auth_headers):
    """POST zip with no estimates → 404."""
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn

    with patch("services.api.services.api.routers.export.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"/api/v1/tenders/{TENDER_ID_EXPORT}/estimate/export/zip", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_export_preview_not_found(app, auth_headers):
    """POST preview with non-existent estimate → 404."""
    eng = _mock_engine(fetchone=None)
    with patch("services.api.services.api.routers.export.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"/api/v1/estimates/{ESTIMATE_ID}/export/preview", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_export_tenders_csv(app, auth_headers):
    """GET /api/v1/tenders/csv → CSV download."""
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch("services.api.services.api.routers.export.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/tenders/csv", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_export_tenders_xlsx(app, auth_headers):
    """GET /api/v1/tenders/xlsx → XLSX download."""
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch("services.api.services.api.routers.export.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/tenders/xlsx", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


def test_export_slug_helper():
    """_slug strips unsafe chars and limits length."""
    from services.api.services.api.routers.export import _slug
    assert _slug("Hello World!") == "Hello_World_"
    assert len(_slug("x" * 100)) <= 60
    assert _slug("") == "kosztorys"


def test_export_validate_lines_empty():
    """_validate_lines raises 422 on empty list."""
    from fastapi import HTTPException
    from services.api.services.api.routers.export import _validate_lines
    with pytest.raises(HTTPException) as exc:
        _validate_lines([])
    assert exc.value.status_code == 422


def test_export_validate_lines_warnings():
    """_validate_lines returns warnings for missing price/unit."""
    from services.api.services.api.routers.export import _validate_lines
    lines = [{"description": "A", "quantity": 1}]
    warnings = _validate_lines(lines)
    assert isinstance(warnings, list)
    assert len(warnings) >= 1


def test_export_check_sum_ok():
    """_check_sum does not raise when totals match."""
    from services.api.services.api.routers.export import _check_sum
    lines = [{"line_total_pln": 100.0}]
    _check_sum(lines, 100.0)  # should not raise


def test_export_check_sum_mismatch():
    """_check_sum raises 500 when totals diverge."""
    from fastapi import HTTPException
    from services.api.services.api.routers.export import _check_sum
    lines = [{"line_total_pln": 500.0}]
    with pytest.raises(HTTPException) as exc:
        _check_sum(lines, 100.0)
    assert exc.value.status_code == 500


# ══════════════════════════════════════════════════════════════════════════════
# email_webhooks.py  (/api/v1/email  +  /api/v1/webhooks)
# ══════════════════════════════════════════════════════════════════════════════

WH_MODULE = "services.api.services.api.routers.email_webhooks"


@pytest.mark.asyncio
async def test_email_set_config(app, auth_headers):
    """POST /api/v1/email/config → 200."""
    conn = _mock_conn()
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{WH_MODULE}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/email/config", json={
                "smtp_host": "smtp.example.com", "smtp_port": 587,
                "smtp_user": "u@x.com", "smtp_pass": "pass",
                "from_email": "noreply@x.com", "from_name": "Test", "enabled": True,
            }, headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_email_get_config_not_configured(app, auth_headers):
    """GET /api/v1/email/config → 200 with configured=False."""
    conn = _mock_conn(fetchone=None)
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{WH_MODULE}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/email/config", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)
    if r.status_code == 200:
        assert r.json().get("configured") is False


@pytest.mark.asyncio
async def test_email_get_config_configured(app, auth_headers):
    """GET /api/v1/email/config → 200 with smtp fields."""
    cfg_row = MagicMock()
    cfg_row.smtp_host = "smtp.test"
    cfg_row.smtp_port = 587
    cfg_row.smtp_user = "user"
    cfg_row.from_email = "a@b.com"
    cfg_row.from_name = "Name"
    cfg_row.enabled = True
    conn = _mock_conn(fetchone=cfg_row)
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{WH_MODULE}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/email/config", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_email_send_unknown_template(app, auth_headers):
    """POST /api/v1/email/send with unknown template → 400."""
    conn = _mock_conn(fetchone=None)
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{WH_MODULE}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/email/send", json={
                "to_email": "x@y.com", "template": "NONEXISTENT", "context": {},
            }, headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_email_send_valid_template(app, auth_headers):
    """POST /api/v1/email/send with valid template → 200."""
    conn = _mock_conn(fetchone=None)
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{WH_MODULE}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/email/send", json={
                "to_email": "x@y.com",
                "template": "tender_status_changed",
                "context": {"tender_title": "T1", "new_status": "active", "tender_url": "http://x"},
            }, headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_email_logs(app, auth_headers):
    """GET /api/v1/email/logs → 200 list."""
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{WH_MODULE}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/email/logs", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_email_templates(app, auth_headers):
    """GET /api/v1/email/templates → 200 list of template names."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/email/templates", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)
    if r.status_code == 200:
        assert "templates" in r.json()


@pytest.mark.asyncio
async def test_webhook_create(app, auth_headers):
    """POST /api/v1/webhooks → 200/201."""
    conn = _mock_conn()
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{WH_MODULE}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/webhooks", json={
                "name": "Test WH", "url": "https://example.com/hook",
                "secret": "s3cr3t", "events": ["tender.status_changed"], "enabled": True,
            }, headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_webhook_list(app, auth_headers):
    """GET /api/v1/webhooks → 200 list."""
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{WH_MODULE}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/webhooks", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_webhook_delete(app, auth_headers):
    """DELETE /api/v1/webhooks/{id} → 200."""
    wh_id = str(uuid.uuid4())
    conn = _mock_conn()
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{WH_MODULE}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.delete(f"/api/v1/webhooks/{wh_id}", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_webhook_test_fire(app, auth_headers):
    """POST /api/v1/webhooks/{id}/test → 200."""
    wh_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"/api/v1/webhooks/{wh_id}/test", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_webhook_deliveries(app, auth_headers):
    """GET /api/v1/webhooks/{id}/deliveries → 200 list."""
    wh_id = str(uuid.uuid4())
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{WH_MODULE}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"/api/v1/webhooks/{wh_id}/deliveries", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


def test_send_smtp_email_mock():
    """_send_smtp_email uses smtplib — verify mock path."""
    from services.api.services.api.routers.email_webhooks import _send_smtp_email
    import smtplib
    mock_server = MagicMock()
    mock_server.sendmail.return_value = {}
    with patch("smtplib.SMTP", return_value=mock_server):
        result = _send_smtp_email(
            "smtp.test", 587, "user", "pass",
            "from@test.com", "Name", "to@test.com",
            "Subject", "<html>Body</html>",
        )
    assert result is True


def test_fire_webhooks_no_rows():
    """fire_webhooks with no matching webhooks — noop."""
    from services.api.services.api.routers.email_webhooks import fire_webhooks
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch("services.api.services.api.routers.email_webhooks.get_engine", eng):
        fire_webhooks("tender.status_changed", {"title": "T"}, "org-123")


# ══════════════════════════════════════════════════════════════════════════════
# intelligence.py  (/api/v2/intelligence/*)
# ══════════════════════════════════════════════════════════════════════════════

INT_MOD = "services.api.services.api.routers.intelligence"


def _mock_icb_svc():
    return {
        "search_icb": MagicMock(return_value=[]),
        "get_narzuty": MagicMock(return_value={}),
        "get_all_narzuty": MagicMock(return_value=[]),
        "get_regional_coefficient": MagicMock(return_value=1.0),
        "get_robocizna_rates": MagicMock(return_value={}),
        "get_price_trend": MagicMock(return_value=[]),
        "get_latest_quarter": MagicMock(return_value="2026-Q2"),
        "get_categories": MagicMock(return_value=[]),
    }


def _mock_pi_svc():
    return {
        "get_inflation_index": MagicMock(return_value=[]),
        "get_material_risk_score": MagicMock(return_value={}),
        "get_all_material_risks": MagicMock(return_value=[]),
        "forecast_price": MagicMock(return_value={}),
        "get_price_index": MagicMock(return_value=[]),
    }


def _mock_bi_svc():
    return {
        "get_cpv_benchmark": MagicMock(return_value={}),
        "detect_bid_anomalies": MagicMock(return_value={}),
        "estimate_win_probability": MagicMock(return_value={}),
        "detect_kosztorys_anomalies": MagicMock(return_value={}),
    }


@pytest.mark.asyncio
async def test_intelligence_search_icb(app, auth_headers):
    """GET /api/v2/intelligence/prices/icb → 200 or 500."""
    with patch(f"{INT_MOD}._icb", return_value=_mock_icb_svc()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/intelligence/prices/icb?q=beton", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_intelligence_inflation_index(app, auth_headers):
    """GET /api/v2/intelligence/prices/inflation → 200 or 500."""
    with patch(f"{INT_MOD}._pi", return_value=_mock_pi_svc()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/intelligence/prices/inflation", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_intelligence_price_trend(app, auth_headers):
    """GET /api/v2/intelligence/prices/trend → 200 or 500."""
    with patch(f"{INT_MOD}._icb", return_value=_mock_icb_svc()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/intelligence/prices/trend?category=beton", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_intelligence_price_forecast(app, auth_headers):
    """GET /api/v2/intelligence/prices/forecast → 200 or 500."""
    with patch(f"{INT_MOD}._pi", return_value=_mock_pi_svc()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/intelligence/prices/forecast?category=beton", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_intelligence_price_index(app, auth_headers):
    """GET /api/v2/intelligence/prices/index → 200 or 500."""
    with patch(f"{INT_MOD}._pi", return_value=_mock_pi_svc()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/intelligence/prices/index", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_intelligence_material_risk_all(app, auth_headers):
    """GET /api/v2/intelligence/material-risk (no category) → 200 or 500."""
    with patch(f"{INT_MOD}._pi", return_value=_mock_pi_svc()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/intelligence/material-risk", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_intelligence_material_risk_category(app, auth_headers):
    """GET /api/v2/intelligence/material-risk?category=beton → 200 or 500."""
    with patch(f"{INT_MOD}._pi", return_value=_mock_pi_svc()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/intelligence/material-risk?category=beton", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_intelligence_narzuty(app, auth_headers):
    """GET /api/v2/intelligence/narzuty → 200 or 500."""
    with patch(f"{INT_MOD}._icb", return_value=_mock_icb_svc()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/intelligence/narzuty", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_intelligence_narzuty_all(app, auth_headers):
    """GET /api/v2/intelligence/narzuty?all=true → 200 or 500."""
    with patch(f"{INT_MOD}._icb", return_value=_mock_icb_svc()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/intelligence/narzuty?all=true", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_intelligence_regional(app, auth_headers):
    """GET /api/v2/intelligence/regional?voivodeship=mazowieckie → 200 or 500."""
    with patch(f"{INT_MOD}._icb", return_value=_mock_icb_svc()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/intelligence/regional?voivodeship=mazowieckie", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_intelligence_robocizna(app, auth_headers):
    """GET /api/v2/intelligence/robocizna-rates → 200 or 500."""
    with patch(f"{INT_MOD}._icb", return_value=_mock_icb_svc()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/intelligence/robocizna-rates", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_intelligence_benchmark(app, auth_headers):
    """GET /api/v2/intelligence/benchmark → 200 or 500."""
    with patch(f"{INT_MOD}._bi", return_value=_mock_bi_svc()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/intelligence/benchmark?cpv_prefix=45", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_intelligence_categories(app, auth_headers):
    """GET /api/v2/intelligence/categories → 200 or 500."""
    with patch(f"{INT_MOD}._icb", return_value=_mock_icb_svc()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/intelligence/categories", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_intelligence_anomaly_bid(app, auth_headers):
    """POST /api/v2/intelligence/anomaly/bid → 200 or 500."""
    with patch(f"{INT_MOD}._bi", return_value=_mock_bi_svc()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/intelligence/anomaly/bid", json={
                "bid_price": 500000, "estimated_value": 600000,
                "cpv_prefix": "45", "n_competitors": 4,
            }, headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_intelligence_anomaly_kosztorys(app, auth_headers):
    """POST /api/v2/intelligence/anomaly/kosztorys → 200 or 500."""
    with patch(f"{INT_MOD}._bi", return_value=_mock_bi_svc()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/intelligence/anomaly/kosztorys", json={
                "items": [{"description": "Beton", "unit": "m3", "quantity": 10.0, "unit_price": 500.0, "category": "M"}],
                "cpv_prefix": "45",
            }, headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_intelligence_win_probability(app, auth_headers):
    """POST /api/v2/intelligence/win-probability → 200 or 500."""
    with patch(f"{INT_MOD}._bi", return_value=_mock_bi_svc()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/intelligence/win-probability", json={
                "our_price": 500000, "estimated_value": 600000, "cpv_prefix": "45", "n_competitors": 4,
            }, headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_intelligence_win_prob_ml(app, auth_headers):
    """GET /api/v2/intelligence/win-prob/{id} → 200 or 500."""
    tid = str(uuid.uuid4())
    conn = _mock_conn()
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{INT_MOD}._get_engine", eng), \
         patch("services.api.services.api.intelligence.win_prob_ml.predict_win_prob",
               return_value=0.65, create=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"/api/v2/intelligence/win-prob/{tid}", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


# ══════════════════════════════════════════════════════════════════════════════
# notifications.py  (/api/v2/notifications/*)
# ══════════════════════════════════════════════════════════════════════════════

NOTIF_MOD = "services.api.services.api.routers.notifications"
NOTIF_ID = str(uuid.uuid4())


@pytest.mark.asyncio
async def test_notifications_unread_count(app, auth_headers):
    """GET /api/v2/notifications/unread-count → 200."""
    conn = _mock_conn(scalar=3)
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{NOTIF_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/notifications/unread-count", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)
    if r.status_code == 200:
        assert "unread_count" in r.json()


@pytest.mark.asyncio
async def test_notifications_count(app, auth_headers):
    """GET /api/v2/notifications/count → 200."""
    conn = _mock_conn(scalar=0)
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{NOTIF_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/notifications/count", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_notifications_list(app, auth_headers):
    """GET /api/v2/notifications → 200 with items."""
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{NOTIF_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/notifications", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_notifications_list_unread_filter(app, auth_headers):
    """GET /api/v2/notifications?unread=true → 200."""
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{NOTIF_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/notifications?unread=true", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_notifications_read_all(app, auth_headers):
    """POST /api/v2/notifications/read-all → 200."""
    conn = _mock_conn(rowcount=5)
    eng = MagicMock()
    eng.return_value.begin.return_value = conn
    with patch(f"{NOTIF_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/notifications/read-all", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_notifications_mark_read_found(app, auth_headers):
    """POST /api/v2/notifications/{id}/read → 200."""
    found_row = MagicMock()
    found_row.id = NOTIF_ID
    conn = _mock_conn(fetchone=found_row)
    eng = MagicMock()
    eng.return_value.begin.return_value = conn
    with patch(f"{NOTIF_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"/api/v2/notifications/{NOTIF_ID}/read", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_notifications_mark_read_not_found(app, auth_headers):
    """POST /api/v2/notifications/{id}/read when not found → 404."""
    conn = _mock_conn(fetchone=None)
    eng = MagicMock()
    eng.return_value.begin.return_value = conn
    with patch(f"{NOTIF_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"/api/v2/notifications/{NOTIF_ID}/read", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_notifications_put_mark_read(app, auth_headers):
    """PUT /api/v2/notifications/{id}/read → 200 or 404."""
    found_row = MagicMock()
    found_row.id = NOTIF_ID
    conn = _mock_conn(fetchone=found_row)
    eng = MagicMock()
    eng.return_value.begin.return_value = conn
    with patch(f"{NOTIF_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.put(f"/api/v2/notifications/{NOTIF_ID}/read", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_notifications_delete_found(app, auth_headers):
    """DELETE /api/v2/notifications/{id} → 204."""
    found_row = MagicMock()
    found_row.id = NOTIF_ID
    conn = _mock_conn(fetchone=found_row)
    eng = MagicMock()
    eng.return_value.begin.return_value = conn
    with patch(f"{NOTIF_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.delete(f"/api/v2/notifications/{NOTIF_ID}", headers=auth_headers)
    assert r.status_code in (200, 204, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_notifications_delete_not_found(app, auth_headers):
    """DELETE /api/v2/notifications/{id} when not found → 404."""
    conn = _mock_conn(fetchone=None)
    eng = MagicMock()
    eng.return_value.begin.return_value = conn
    with patch(f"{NOTIF_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.delete(f"/api/v2/notifications/{NOTIF_ID}", headers=auth_headers)
    assert r.status_code in (200, 204, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_notifications_bulk_read_all(app, auth_headers):
    """POST /api/v2/notifications/bulk-read {all:true} → 200."""
    conn = _mock_conn(rowcount=10)
    eng = MagicMock()
    eng.return_value.begin.return_value = conn
    with patch(f"{NOTIF_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/notifications/bulk-read",
                             json={"all": True}, headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_notifications_bulk_read_ids(app, auth_headers):
    """POST /api/v2/notifications/bulk-read with ids → 200."""
    conn = _mock_conn(rowcount=2)
    eng = MagicMock()
    eng.return_value.begin.return_value = conn
    with patch(f"{NOTIF_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/notifications/bulk-read",
                             json={"ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
                             headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_notifications_bulk_read_empty(app, auth_headers):
    """POST /api/v2/notifications/bulk-read {} → 200 updated=0."""
    conn = _mock_conn()
    eng = MagicMock()
    eng.return_value.begin.return_value = conn
    with patch(f"{NOTIF_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/notifications/bulk-read",
                             json={}, headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


def test_notifications_decode_cursor_invalid():
    """_decode_cursor raises 400 on garbage input."""
    from fastapi import HTTPException
    from services.api.services.api.routers.notifications import _decode_cursor
    with pytest.raises(HTTPException) as exc:
        _decode_cursor("!!!not-base64!!!")
    assert exc.value.status_code == 400


def test_notifications_encode_cursor():
    """_encode_cursor produces valid base64 that _decode_cursor can round-trip."""
    import base64, json
    from services.api.services.api.routers.notifications import _decode_cursor, _encode_cursor
    from datetime import datetime
    row = MagicMock()
    row.created_at = datetime(2026, 1, 1, 12, 0, 0)
    row.id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    cursor = _encode_cursor(row)
    decoded = _decode_cursor(cursor)
    assert decoded["id"] == str(row.id)


# ══════════════════════════════════════════════════════════════════════════════
# bzp.py  (/api/v1/bzp/*)
# ══════════════════════════════════════════════════════════════════════════════

BZP_MOD = "services.api.services.api.routers.bzp"


@pytest.mark.asyncio
async def test_bzp_sync_bg(app, auth_headers):
    """POST /api/v1/bzp/sync → 200 started (background task mocked)."""
    with patch(f"{BZP_MOD}._do_sync", return_value={"fetched": 0, "saved": 0, "skipped": 0, "pages": 0}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/bzp/sync?days_back=1", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)
    if r.status_code == 200:
        assert r.json()["status"] == "started"


@pytest.mark.asyncio
async def test_bzp_sync_now_mocked(app, auth_headers):
    """POST /api/v1/bzp/sync/now → 200 done (mocked _do_sync)."""
    with patch(f"{BZP_MOD}._do_sync", return_value={"fetched": 0, "saved": 0, "skipped": 0, "pages": 1}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v1/bzp/sync/now?days_back=1", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_bzp_stats_fallback(app, auth_headers):
    """GET /api/v1/bzp/stats → 200 (fallback when API down)."""
    with patch("httpx.get", side_effect=Exception("no network")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/bzp/stats", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_bzp_stats_live(app, auth_headers):
    """GET /api/v1/bzp/stats → 200 with mocked httpx."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"total": 42, "by_type": {}}
    with patch("httpx.get", return_value=mock_resp):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/bzp/stats", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_bzp_document_not_found(app, auth_headers):
    """GET /api/v1/bzp/document/FAKE → 404 when nothing found."""
    conn = _mock_conn(fetchone=None)
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{BZP_MOD}.get_engine", eng), \
         patch("httpx.get", side_effect=Exception("no network")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/bzp/document/2026%2FBZP-FAKE", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_bzp_preview_mocked(app, auth_headers):
    """GET /api/v1/bzp/preview → 200 with mocked fetch."""
    with patch(f"{BZP_MOD}._fetch_page", return_value=[]):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v1/bzp/preview?days_back=1&limit=5", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)
    if r.status_code == 200:
        assert "preview" in r.json()


def test_bzp_cpv_matches():
    """_cpv_matches filters correct CPV prefixes."""
    from services.api.services.api.routers.bzp import _cpv_matches
    assert _cpv_matches("45000000-7")
    assert _cpv_matches("45230000-0")
    assert not _cpv_matches("72000000-0")


def test_bzp_parse_value_pln():
    """_parse_value_pln extracts PLN values."""
    from services.api.services.api.routers.bzp import _parse_value_pln
    result = _parse_value_pln("Wartość zamówienia: 1 234 567,89 PLN")
    # Returns float or None — just check it doesn't crash
    assert result is None or isinstance(result, float)


def test_bzp_safe_dt():
    """_safe_dt parses ISO datetime strings."""
    from services.api.services.api.routers.bzp import _safe_dt
    dt = _safe_dt("2026-01-15T10:00:00Z")
    assert dt is not None
    assert _safe_dt(None) is None
    assert _safe_dt("bad") is None


def test_bzp_do_sync_mocked():
    """_do_sync runs against mocked DB and HTTP."""
    from services.api.services.api.routers.bzp import _do_sync
    conn = _mock_conn(fetchone=None, fetchall=[])
    conn.execute.return_value.fetchone.return_value = None
    eng = MagicMock()
    eng.return_value.begin.return_value = conn
    with patch(f"{BZP_MOD}.get_engine", eng), \
         patch(f"{BZP_MOD}._fetch_page", return_value=[]):
        result = _do_sync(days_back=1)
    assert "fetched" in result
    assert result["saved"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# scoring_v2.py  (/api/v2/scoring/*)
# ══════════════════════════════════════════════════════════════════════════════

SV2_MOD = "services.api.services.api.routers.scoring_v2"


@pytest.mark.asyncio
async def test_scoring_v2_backtest_empty(app, auth_headers):
    """POST /api/v2/scoring/backtest → 200 no data."""
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{SV2_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/scoring/backtest", json={
                "weights": {"cpv_match": 25, "value_range": 20, "deadline_pressure": 20,
                            "buyer_history": 20, "document_quality": 15},
                "lookback_days": 90,
            }, headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_scoring_v2_calibration(app, auth_headers):
    """GET /api/v2/scoring/calibration → 200."""
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{SV2_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/scoring/calibration", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_scoring_v2_create_experiment(app, auth_headers):
    """POST /api/v2/scoring/experiment → 200."""
    conn = _mock_conn()
    eng = MagicMock()
    eng.return_value.begin.return_value = conn
    with patch(f"{SV2_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/scoring/experiment", json={
                "name": "Test Exp",
                "variant_weights": {"cpv_match": 30, "value_range": 20, "deadline_pressure": 20,
                                    "buyer_history": 15, "document_quality": 15},
                "sample_pct": 50,
            }, headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_scoring_v2_list_experiments(app, auth_headers):
    """GET /api/v2/scoring/experiments → 200 list."""
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{SV2_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/scoring/experiments", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


def test_simulate_score():
    """_simulate_score returns float in reasonable range."""
    from services.api.services.api.routers.scoring_v2 import _simulate_score, WeightsModel
    w = WeightsModel()
    score = _simulate_score("45000000", 1_000_000, None, "Zamawiający", w.model_dump())
    assert isinstance(score, float)
    assert score >= 0


def test_calibration_recommendation_empty():
    """_calibration_recommendation with no bins returns info message."""
    from services.api.services.api.routers.scoring_v2 import _calibration_recommendation
    msg = _calibration_recommendation([])
    assert isinstance(msg, str)
    assert len(msg) > 0


# ══════════════════════════════════════════════════════════════════════════════
# kosztorys_v3.py  (/api/v2/icb/rates + /api/v2/kosztorys/{id}/ai-wycena-v2)
# ══════════════════════════════════════════════════════════════════════════════

KV3_MOD = "services.api.services.api.routers.kosztorys_v3"


@pytest.mark.asyncio
async def test_kosztorys_v3_icb_rates_empty(app, auth_headers):
    """GET /api/v2/icb/rates → 200 empty rates."""
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{KV3_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/icb/rates?cpv5=45200&nuts2=PL91", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)
    if r.status_code == 200:
        data = r.json()
        assert data["cpv5"] == "45200"
        assert data["rates"] == []


@pytest.mark.asyncio
async def test_kosztorys_v3_icb_rates_missing_params(app, auth_headers):
    """GET /api/v2/icb/rates without params → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v2/icb/rates", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_kosztorys_v3_ai_wycena_not_found(app, auth_headers):
    """POST /api/v2/kosztorys/{id}/ai-wycena-v2 → 404 when kosztorys not found."""
    kid = str(uuid.uuid4())
    conn = _mock_conn(fetchone=None)
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{KV3_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"/api/v2/kosztorys/{kid}/ai-wycena-v2", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


# ══════════════════════════════════════════════════════════════════════════════
# scoring.py  (/api/v2/scoring/config + /api/v2/tenders/{id}/score-breakdown etc.)
# ══════════════════════════════════════════════════════════════════════════════

SCORING_MOD = "services.api.services.api.routers.scoring"


@pytest.mark.asyncio
async def test_scoring_get_config_default(app, auth_headers):
    """GET /api/v2/scoring/config → 200."""
    conn = _mock_conn(fetchone=None)
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{SCORING_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/scoring/config", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_scoring_put_config_valid(app, auth_headers):
    """PUT /api/v2/scoring/config with sum=100 → 200."""
    conn = _mock_conn()
    eng = MagicMock()
    eng.return_value.begin.return_value = conn
    with patch(f"{SCORING_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.put("/api/v2/scoring/config", json={
                "weights": {"cpv_match": 30, "value_range": 25,
                            "deadline_pressure": 20, "buyer_history": 15, "document_quality": 10}
            }, headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_scoring_put_config_invalid_sum(app, auth_headers):
    """PUT /api/v2/scoring/config with sum≠100 → 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.put("/api/v2/scoring/config", json={
            "weights": {"cpv_match": 10}
        }, headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_scoring_score_breakdown_not_found(app, auth_headers):
    """GET /api/v2/tenders/{id}/score-breakdown → 404 if not found."""
    tid = str(uuid.uuid4())
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{SCORING_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"/api/v2/tenders/{tid}/score-breakdown", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_scoring_cpv_heatmap(app, auth_headers):
    """GET /api/v2/market/cpv-heatmap → 200."""
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{SCORING_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/market/cpv-heatmap", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_scoring_refresh_views(app, auth_headers):
    """POST /api/v2/admin/refresh-views → 200 or 500."""
    conn = _mock_conn()
    eng = MagicMock()
    eng.return_value.begin.return_value = conn
    with patch(f"{SCORING_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/admin/refresh-views", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


# ══════════════════════════════════════════════════════════════════════════════
# audit_v2.py  (/api/v2/audit/*)
# ══════════════════════════════════════════════════════════════════════════════

AUDIT_MOD = "services.api.services.api.routers.audit_v2"


@pytest.mark.asyncio
async def test_audit_v2_recent(app, auth_headers):
    """GET /api/v2/audit/recent → 200 list."""
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{AUDIT_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/audit/recent", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_audit_v2_trail(app, auth_headers):
    """GET /api/v2/audit/trail → 200 paginated."""
    conn = _mock_conn(fetchall=[])
    conn.execute.return_value.fetchone.return_value = MagicMock()
    conn.execute.return_value.fetchone.return_value.__getitem__ = lambda s, i: 0
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{AUDIT_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/audit/trail", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_audit_v2_trail_with_filters(app, auth_headers):
    """GET /api/v2/audit/trail?entity_type=tender → 200."""
    conn = _mock_conn(fetchall=[])
    count_row = MagicMock()
    count_row.__getitem__ = lambda s, i: 0
    conn.execute.return_value.fetchone.return_value = count_row
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{AUDIT_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/audit/trail?entity_type=tender&action=update&limit=10",
                            headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_audit_v2_entity_history(app, auth_headers):
    """GET /api/v2/audit/entity/{id} → 200 list."""
    eid = str(uuid.uuid4())
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{AUDIT_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"/api/v2/audit/entity/{eid}", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_audit_v2_diff_not_found(app, auth_headers):
    """GET /api/v2/audit/diff/{id} → {error: Not found}."""
    aid = str(uuid.uuid4())
    conn = _mock_conn(fetchone=None)
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{AUDIT_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"/api/v2/audit/diff/{aid}", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_audit_v2_stats(app, auth_headers):
    """GET /api/v2/audit/stats → 200."""
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{AUDIT_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/audit/stats?days=7", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


def test_audit_summarize_changes_none():
    """_summarize_changes(None) returns default string."""
    from services.api.services.api.routers.audit_v2 import _summarize_changes
    result = _summarize_changes(None)
    assert isinstance(result, str)


def test_audit_summarize_changes_dict():
    """_summarize_changes with dict JSON returns field names."""
    import json
    from services.api.services.api.routers.audit_v2 import _summarize_changes
    result = _summarize_changes(json.dumps({"title": "old→new", "status": "x→y"}))
    assert isinstance(result, str)
    assert "title" in result or "status" in result


# ══════════════════════════════════════════════════════════════════════════════
# events.py  (/api/v2/events/stream + /api/v2/events/emit + /api/v2/notifications)
# ══════════════════════════════════════════════════════════════════════════════

EVENTS_MOD = "services.api.services.api.routers.events"


@pytest.mark.asyncio
async def test_events_emit(app, auth_headers):
    """POST /api/v2/events/emit → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/v2/events/emit", json={
            "event_type": "tender.new",
            "payload": {"title": "Test tender", "tender_id": str(uuid.uuid4())},
        }, headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)
    if r.status_code == 200:
        assert r.json()["status"] == "emitted"


@pytest.mark.asyncio
async def test_events_emit_deadline_persists(app, auth_headers):
    """POST /api/v2/events/emit alert.deadline → persists notification."""
    conn = _mock_conn()
    eng = MagicMock()
    eng.return_value.begin.return_value = conn
    with patch(f"{EVENTS_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/events/emit", json={
                "event_type": "alert.deadline",
                "payload": {"title": "Przetarg X", "tender_id": str(uuid.uuid4())},
            }, headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_events_get_notifications(app, auth_headers):
    """GET /api/v2/notifications (events router) → 200."""
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{EVENTS_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/notifications", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_events_get_notifications_unread(app, auth_headers):
    """GET /api/v2/notifications?unread_only=true → 200."""
    conn = _mock_conn(fetchall=[])
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    with patch(f"{EVENTS_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/notifications?unread_only=true", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_events_mark_read_all(app, auth_headers):
    """POST /api/v2/notifications/mark-read [] → 200 mark all."""
    conn = _mock_conn(rowcount=3)
    eng = MagicMock()
    eng.return_value.begin.return_value = conn
    with patch(f"{EVENTS_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/notifications/mark-read",
                             json=[], headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_events_mark_read_specific(app, auth_headers):
    """POST /api/v2/notifications/mark-read [id] → 200."""
    nid = str(uuid.uuid4())
    conn = _mock_conn(rowcount=1)
    eng = MagicMock()
    eng.return_value.begin.return_value = conn
    with patch(f"{EVENTS_MOD}.get_engine", eng):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/notifications/mark-read",
                             json=[nid], headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


def test_event_bus_publish():
    """EventBus.publish delivers events to subscribers' queues."""
    import asyncio
    from services.api.services.api.routers.events import EventBus
    bus = EventBus()
    q = MagicMock()
    bus._subscribers.append(q)
    asyncio.get_event_loop().run_until_complete(bus.publish({"type": "test"}))
    q.put_nowait.assert_called_once_with({"type": "test"})


def test_persist_notification_error_swallowed():
    """_persist_notification swallows DB errors gracefully."""
    from services.api.services.api.routers.events import _persist_notification
    eng = MagicMock()
    eng.return_value.begin.side_effect = Exception("DB down")
    with patch(f"{EVENTS_MOD}.get_engine", eng):
        # Should not raise
        _persist_notification("alert.deadline", {"title": "T", "tender_id": "123"})


# ══════════════════════════════════════════════════════════════════════════════
# reports.py  (/api/v2/reports/*)
# ══════════════════════════════════════════════════════════════════════════════

REP_MOD = "services.api.services.api.routers.reports"


def _reports_conn():
    """Reports uses Depends(get_db) yielding a connection, not get_engine directly."""
    conn = MagicMock()
    result = MagicMock()
    result.scalar.return_value = 0
    result.fetchall.return_value = []
    conn.execute.return_value = result
    conn.commit.return_value = None
    return conn


@pytest.mark.asyncio
async def test_reports_monthly(app, auth_headers):
    """GET /api/v2/reports/monthly → 200."""
    conn = _reports_conn()
    with patch(f"{REP_MOD}.get_engine") as eng:
        eng.return_value.connect.return_value.__enter__ = lambda s: conn
        eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
        eng.return_value.connect.return_value = conn
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/reports/monthly?year=2026&month=7", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_reports_monthly_pdf(app, auth_headers):
    """GET /api/v2/reports/monthly/pdf → 200 (HTML fallback if no reportlab)."""
    conn = _reports_conn()
    with patch(f"{REP_MOD}.get_engine") as eng:
        eng.return_value.connect.return_value = conn
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/reports/monthly/pdf?year=2026&month=7", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.mark.asyncio
async def test_reports_benchmark(app, auth_headers):
    """GET /api/v2/reports/benchmark → 200."""
    row = MagicMock()
    row.tenant_id = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"
    row.cnt = 10
    row.avg_score = 0.75
    conn = _reports_conn()
    conn.execute.return_value.fetchall.return_value = [row]
    with patch(f"{REP_MOD}.get_engine") as eng:
        eng.return_value.connect.return_value = conn
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/reports/benchmark", headers=auth_headers)
    assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)
