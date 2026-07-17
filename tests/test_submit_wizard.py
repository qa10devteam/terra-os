"""Tests for submit_wizard.py — /api/v2/submit endpoints.

Covers:
- GET /wizard/{bid_id} — wizard status
- POST /wizard/{bid_id}/step/{step_nr} — step confirmation
- POST /confirm/{bid_id} — final confirmation
- GET /tracking/{bid_id} — post-submission tracking
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from contextlib import contextmanager

import pytest
from httpx import ASGITransport, AsyncClient


BID_ID = "11111111-1111-1111-1111-111111111111"
TENDER_ID = "22222222-2222-2222-2222-222222222222"
BASE_URL = "http://test"
PREFIX = "/api/v2/submit"


@pytest.fixture(scope="module")
def app():
    from services.api.services.api.main import app as _app
    return _app


def _make_mock_cursor(fetchone_returns=None, fetchall_returns=None):
    """Create a mock cursor that returns specified values on fetchone/fetchall."""
    cur = MagicMock()
    cur.fetchone = MagicMock(return_value=fetchone_returns)
    cur.fetchall = MagicMock(return_value=fetchall_returns or [])
    cur.execute = MagicMock()
    return cur


def _make_mock_conn():
    conn = MagicMock()
    conn.commit = MagicMock()
    conn.close = MagicMock()
    return conn


@contextmanager
def _mock_db_cursor_ctx(cur, conn=None):
    """Context manager that yields (conn, cur) mocks."""
    if conn is None:
        conn = _make_mock_conn()
    yield conn, cur


# ─── GET /wizard/{bid_id} ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wizard_get_status_happy_path(app):
    """GET /wizard/{bid_id} returns wizard state with all 7 steps."""
    offer_row = {
        "id": BID_ID,
        "tender_id": TENDER_ID,
        "title": "Test Tender",
        "status": "draft",
        "stage": "",
        "metadata": json.dumps({}),
        "updated_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
    }
    tender_row = {
        "title": "Test Tender Title",
        "deadline_at": datetime(2099, 12, 31, 23, 59, tzinfo=timezone.utc),
    }

    call_count = [0]
    def mock_fetchone():
        call_count[0] += 1
        # 1st call: offers lookup
        if call_count[0] == 1:
            return offer_row
        # 2nd call: tender lookup
        if call_count[0] == 2:
            return tender_row
        # Remaining: step checks (kosztorys, documents, etc.)
        return None

    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(side_effect=mock_fetchone)

    with patch("services.api.services.api.routers.submit_wizard.db_cursor") as mock_db:
        mock_db.return_value = _mock_db_cursor_ctx(cur)
        mock_db.side_effect = None
        mock_db.__enter__ = MagicMock()
        # Use proper context manager patching
        mock_db.return_value.__enter__ = lambda s: (MagicMock(), cur)
        mock_db.return_value.__exit__ = lambda s, *a: None

        # Patch as context manager properly
        @contextmanager
        def fake_db_cursor():
            yield _make_mock_conn(), cur

        mock_db.side_effect = fake_db_cursor

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.get(f"{PREFIX}/wizard/{BID_ID}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["bid_id"] == BID_ID
    assert data["total_steps"] == 7
    assert len(data["steps"]) == 7
    assert "overall_progress_pct" in data
    assert "can_submit" in data
    assert "time_remaining" in data


@pytest.mark.asyncio
async def test_wizard_get_status_invalid_uuid(app):
    """GET /wizard/{bad_uuid} → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
        resp = await c.get(f"{PREFIX}/wizard/not-a-uuid")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_wizard_get_status_db_error_fallback(app):
    """GET /wizard/{bid_id} with DB error returns fallback all-pending steps."""
    with patch("services.api.services.api.routers.submit_wizard.db_cursor") as mock_db:
        mock_db.side_effect = Exception("Connection refused")

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.get(f"{PREFIX}/wizard/{BID_ID}")

    # Should still return 200 with fallback
    assert resp.status_code == 200
    data = resp.json()
    assert data["bid_id"] == BID_ID
    assert data["total_steps"] == 7
    assert len(data["steps"]) == 7
    # All steps should be pending in fallback
    for step in data["steps"]:
        assert step["status"] == "pending"
    assert data["overall_progress_pct"] == 0.0
    assert data["can_submit"] is False


@pytest.mark.asyncio
async def test_wizard_get_status_offer_not_found_tries_bid_intelligence(app):
    """GET /wizard/{bid_id} when offer not in offers table, falls back to bid_intelligence."""
    bi_row = {
        "id": BID_ID,
        "tender_id": TENDER_ID,
        "our_price": 100000.0,
        "won": True,
        "bid_date": None,
        "created_at": datetime(2025, 5, 1, tzinfo=timezone.utc),
    }
    tender_row = {
        "title": "Tender from BI",
        "deadline_at": datetime(2099, 12, 31, 23, 59, tzinfo=timezone.utc),
    }

    call_count = [0]
    def mock_fetchone():
        call_count[0] += 1
        if call_count[0] == 1:
            return None  # offers table: not found
        if call_count[0] == 2:
            return bi_row  # bid_intelligence: found
        if call_count[0] == 3:
            return tender_row  # tender lookup
        return None

    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(side_effect=mock_fetchone)

    @contextmanager
    def fake_db_cursor():
        yield _make_mock_conn(), cur

    with patch("services.api.services.api.routers.submit_wizard.db_cursor", side_effect=fake_db_cursor):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.get(f"{PREFIX}/wizard/{BID_ID}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["bid_id"] == BID_ID


@pytest.mark.asyncio
async def test_wizard_all_steps_completed(app):
    """GET /wizard/{bid_id} with status='confirmed' marks all steps completed."""
    offer_row = {
        "id": BID_ID,
        "tender_id": TENDER_ID,
        "title": "Test Confirmed",
        "status": "confirmed",
        "stage": "",
        "metadata": json.dumps({"wizard_steps": {}}),
        "updated_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
    }
    tender_row = {
        "title": "Tender Confirmed",
        "deadline_at": datetime(2099, 12, 31, 23, 59, tzinfo=timezone.utc),
    }

    call_count = [0]
    def mock_fetchone():
        call_count[0] += 1
        if call_count[0] == 1:
            return offer_row
        if call_count[0] == 2:
            return tender_row
        # Step 1 kosztorys check — return approved
        if call_count[0] == 3:
            return {"id": "k1", "status": "approved", "updated_at": datetime(2025, 5, 1, tzinfo=timezone.utc)}
        # Step 2 document count
        if call_count[0] == 4:
            return {"cnt": 6, "last_at": datetime(2025, 5, 2, tzinfo=timezone.utc)}
        return None

    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(side_effect=mock_fetchone)

    @contextmanager
    def fake_db_cursor():
        yield _make_mock_conn(), cur

    with patch("services.api.services.api.routers.submit_wizard.db_cursor", side_effect=fake_db_cursor):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.get(f"{PREFIX}/wizard/{BID_ID}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["can_submit"] is True
    assert data["overall_progress_pct"] == 100.0


@pytest.mark.asyncio
async def test_wizard_progress_partial(app):
    """GET /wizard/{bid_id} with some steps done shows partial progress."""
    offer_row = {
        "id": BID_ID,
        "tender_id": TENDER_ID,
        "title": "Partial",
        "status": "draft",
        "stage": "",
        "metadata": json.dumps({"wizard_steps": {"1": {"status": "completed"}}}),
        "updated_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
    }
    tender_row = {
        "title": "Partial Tender",
        "deadline_at": datetime(2099, 12, 31, 23, 59, tzinfo=timezone.utc),
    }

    call_count = [0]
    def mock_fetchone():
        call_count[0] += 1
        if call_count[0] == 1:
            return offer_row
        if call_count[0] == 2:
            return tender_row
        # Step 1 kosztorys: approved
        if call_count[0] == 3:
            return {"id": "k1", "status": "approved", "updated_at": datetime(2025, 5, 1, tzinfo=timezone.utc)}
        # Step 2 docs: 0
        if call_count[0] == 4:
            return {"cnt": 0, "last_at": None}
        if call_count[0] == 5:
            return {"cnt": 0, "last_at": None}
        return None

    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(side_effect=mock_fetchone)

    @contextmanager
    def fake_db_cursor():
        yield _make_mock_conn(), cur

    with patch("services.api.services.api.routers.submit_wizard.db_cursor", side_effect=fake_db_cursor):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.get(f"{PREFIX}/wizard/{BID_ID}")

    assert resp.status_code == 200
    data = resp.json()
    # Step 1 completed, rest not → progress ~14.3%
    assert data["overall_progress_pct"] > 0
    assert data["overall_progress_pct"] < 100
    assert data["can_submit"] is False


# ─── POST /wizard/{bid_id}/step/{step_nr} ───────────────────────────────────

@pytest.mark.asyncio
async def test_step_confirm_happy_path(app):
    """POST /wizard/{bid_id}/step/1 with confirmed=true → success."""
    offer_row = {
        "id": BID_ID,
        "metadata": json.dumps({}),
        "status": "draft",
    }

    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(return_value=offer_row)

    @contextmanager
    def fake_db_cursor():
        yield _make_mock_conn(), cur

    with patch("services.api.services.api.routers.submit_wizard.db_cursor", side_effect=fake_db_cursor):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.post(
                f"{PREFIX}/wizard/{BID_ID}/step/1",
                json={"confirmed": True, "notes": "All good"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["bid_id"] == BID_ID
    assert data["step_nr"] == 1
    assert data["status"] == "completed"
    assert data["next_step"] == 2


@pytest.mark.asyncio
async def test_step_confirm_not_confirmed(app):
    """POST /wizard/{bid_id}/step/1 with confirmed=false → returns pending."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
        resp = await c.post(
            f"{PREFIX}/wizard/{BID_ID}/step/1",
            json={"confirmed": False},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["next_step"] == 1


@pytest.mark.asyncio
async def test_step_confirm_invalid_step_0(app):
    """POST /wizard/{bid_id}/step/0 → 400 (step must be 1-7)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
        resp = await c.post(
            f"{PREFIX}/wizard/{BID_ID}/step/0",
            json={"confirmed": True},
        )

    assert resp.status_code == 400
    assert "1-7" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_step_confirm_invalid_step_8(app):
    """POST /wizard/{bid_id}/step/8 → 400 (step must be 1-7)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
        resp = await c.post(
            f"{PREFIX}/wizard/{BID_ID}/step/8",
            json={"confirmed": True},
        )

    assert resp.status_code == 400
    assert "1-7" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_step_confirm_invalid_uuid(app):
    """POST /wizard/bad-uuid/step/1 → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
        resp = await c.post(
            f"{PREFIX}/wizard/not-a-uuid/step/1",
            json={"confirmed": True},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_step_confirm_dependency_violation(app):
    """POST /wizard/{bid_id}/step/3 when step 2 not completed → 400."""
    offer_row = {
        "id": BID_ID,
        "metadata": json.dumps({"wizard_steps": {"1": {"status": "completed"}}}),
        "status": "draft",
    }

    call_count = [0]
    def mock_fetchone():
        call_count[0] += 1
        if call_count[0] == 1:
            return offer_row
        return None

    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(side_effect=mock_fetchone)

    @contextmanager
    def fake_db_cursor():
        yield _make_mock_conn(), cur

    with patch("services.api.services.api.routers.submit_wizard.db_cursor", side_effect=fake_db_cursor):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.post(
                f"{PREFIX}/wizard/{BID_ID}/step/3",
                json={"confirmed": True},
            )

    assert resp.status_code == 400
    assert "nie jest ukończony" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_step_confirm_step2_requires_kosztorys(app):
    """POST /wizard/{bid_id}/step/2 when kosztorys not approved → 400."""
    offer_row = {
        "id": BID_ID,
        "metadata": json.dumps({"wizard_steps": {}}),
        "status": "draft",
    }

    call_count = [0]
    def mock_fetchone():
        call_count[0] += 1
        if call_count[0] == 1:
            return offer_row  # offers lookup
        if call_count[0] == 2:
            return None  # kosztorys not approved
        return None

    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(side_effect=mock_fetchone)

    @contextmanager
    def fake_db_cursor():
        yield _make_mock_conn(), cur

    with patch("services.api.services.api.routers.submit_wizard.db_cursor", side_effect=fake_db_cursor):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.post(
                f"{PREFIX}/wizard/{BID_ID}/step/2",
                json={"confirmed": True},
            )

    assert resp.status_code == 400
    assert "nie jest ukończony" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_step_confirm_offer_not_found_graceful(app):
    """POST /wizard/{bid_id}/step/1 when offer not in DB → still succeeds (graceful)."""
    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(return_value=None)

    @contextmanager
    def fake_db_cursor():
        yield _make_mock_conn(), cur

    with patch("services.api.services.api.routers.submit_wizard.db_cursor", side_effect=fake_db_cursor):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.post(
                f"{PREFIX}/wizard/{BID_ID}/step/1",
                json={"confirmed": True},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert "nie znaleziona" in data["message"]


@pytest.mark.asyncio
async def test_step_confirm_last_step_next_is_none(app):
    """POST /wizard/{bid_id}/step/7 → next_step is null."""
    offer_row = {
        "id": BID_ID,
        "metadata": json.dumps({"wizard_steps": {
            "1": {"status": "completed"},
            "2": {"status": "completed"},
            "3": {"status": "completed"},
            "4": {"status": "completed"},
            "5": {"status": "completed"},
            "6": {"status": "completed"},
        }}),
        "status": "draft",
    }

    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(return_value=offer_row)

    @contextmanager
    def fake_db_cursor():
        yield _make_mock_conn(), cur

    with patch("services.api.services.api.routers.submit_wizard.db_cursor", side_effect=fake_db_cursor):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.post(
                f"{PREFIX}/wizard/{BID_ID}/step/7",
                json={"confirmed": True},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["next_step"] is None


@pytest.mark.asyncio
async def test_step_confirm_db_error_graceful(app):
    """POST /wizard/{bid_id}/step/1 with DB error → graceful offline response."""
    with patch("services.api.services.api.routers.submit_wizard.db_cursor") as mock_db:
        mock_db.side_effect = Exception("DB unreachable")

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.post(
                f"{PREFIX}/wizard/{BID_ID}/step/1",
                json={"confirmed": True},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert "offline" in data["message"]


# ─── POST /confirm/{bid_id} ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_final_confirm_happy_path(app):
    """POST /confirm/{bid_id} with all confirmations → success."""
    offer_row = {
        "id": BID_ID,
        "metadata": json.dumps({"wizard_steps": {
            "1": {"status": "completed"},
            "2": {"status": "completed"},
            "3": {"status": "completed"},
            "4": {"status": "completed"},
            "5": {"status": "completed"},
            "6": {"status": "completed"},
            "7": {"status": "completed"},
        }}),
        "status": "validated",
    }

    call_count = [0]
    def mock_fetchone():
        call_count[0] += 1
        if call_count[0] == 1:
            return offer_row  # offers lookup
        if call_count[0] == 2:
            return {"id": "k1"}  # kosztorys approved check
        return None

    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(side_effect=mock_fetchone)

    @contextmanager
    def fake_db_cursor():
        yield _make_mock_conn(), cur

    with patch("services.api.services.api.routers.submit_wizard.db_cursor", side_effect=fake_db_cursor):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.post(
                f"{PREFIX}/confirm/{BID_ID}",
                json={
                    "confirm_price_correct": True,
                    "confirm_documents_complete": True,
                    "confirm_deadline_met": True,
                    "confirm_authorized": True,
                    "electronic_signature_id": "sig-123",
                },
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["bid_id"] == BID_ID
    assert data["submission_status"] == "confirmed"
    assert data["confirmation_hash"] is not None
    assert data["confirmation_hash"].startswith("sha256:")


@pytest.mark.asyncio
async def test_final_confirm_missing_confirmation_field(app):
    """POST /confirm/{bid_id} with confirm_price_correct=false → 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
        resp = await c.post(
            f"{PREFIX}/confirm/{BID_ID}",
            json={
                "confirm_price_correct": False,
                "confirm_documents_complete": True,
                "confirm_deadline_met": True,
                "confirm_authorized": True,
            },
        )

    assert resp.status_code == 400
    assert "potwierdzenia" in resp.json()["detail"].lower() or "muszą" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_final_confirm_all_false(app):
    """POST /confirm/{bid_id} with all false → 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
        resp = await c.post(
            f"{PREFIX}/confirm/{BID_ID}",
            json={
                "confirm_price_correct": False,
                "confirm_documents_complete": False,
                "confirm_deadline_met": False,
                "confirm_authorized": False,
            },
        )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_final_confirm_missing_required_steps(app):
    """POST /confirm/{bid_id} when steps not all completed → 400."""
    offer_row = {
        "id": BID_ID,
        "metadata": json.dumps({"wizard_steps": {
            "1": {"status": "completed"},
            # Steps 2-7 missing
        }}),
        "status": "draft",
    }

    call_count = [0]
    def mock_fetchone():
        call_count[0] += 1
        if call_count[0] == 1:
            return offer_row
        if call_count[0] == 2:
            return {"id": "k1"}  # kosztorys OK
        return None

    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(side_effect=mock_fetchone)

    @contextmanager
    def fake_db_cursor():
        yield _make_mock_conn(), cur

    with patch("services.api.services.api.routers.submit_wizard.db_cursor", side_effect=fake_db_cursor):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.post(
                f"{PREFIX}/confirm/{BID_ID}",
                json={
                    "confirm_price_correct": True,
                    "confirm_documents_complete": True,
                    "confirm_deadline_met": True,
                    "confirm_authorized": True,
                },
            )

    assert resp.status_code == 400
    assert "kroki" in resp.json()["detail"].lower() or "Krok" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_final_confirm_offer_not_found_graceful(app):
    """POST /confirm/{bid_id} when offer not in DB → graceful offline response."""
    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(return_value=None)

    @contextmanager
    def fake_db_cursor():
        yield _make_mock_conn(), cur

    with patch("services.api.services.api.routers.submit_wizard.db_cursor", side_effect=fake_db_cursor):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.post(
                f"{PREFIX}/confirm/{BID_ID}",
                json={
                    "confirm_price_correct": True,
                    "confirm_documents_complete": True,
                    "confirm_deadline_met": True,
                    "confirm_authorized": True,
                },
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["submission_status"] == "confirmed"
    assert "offline" in data["message"].lower() or "nie znaleziono" in data["message"].lower()


@pytest.mark.asyncio
async def test_final_confirm_invalid_uuid(app):
    """POST /confirm/bad-uuid → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
        resp = await c.post(
            f"{PREFIX}/confirm/bad-uuid",
            json={
                "confirm_price_correct": True,
                "confirm_documents_complete": True,
                "confirm_deadline_met": True,
                "confirm_authorized": True,
            },
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_final_confirm_db_error_graceful(app):
    """POST /confirm/{bid_id} with DB error → graceful offline response."""
    with patch("services.api.services.api.routers.submit_wizard.db_cursor") as mock_db:
        mock_db.side_effect = Exception("Connection timeout")

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.post(
                f"{PREFIX}/confirm/{BID_ID}",
                json={
                    "confirm_price_correct": True,
                    "confirm_documents_complete": True,
                    "confirm_deadline_met": True,
                    "confirm_authorized": True,
                },
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["submission_status"] == "confirmed"
    assert data["confirmation_hash"] is not None


@pytest.mark.asyncio
async def test_final_confirm_missing_body(app):
    """POST /confirm/{bid_id} without body → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
        resp = await c.post(f"{PREFIX}/confirm/{BID_ID}")
    assert resp.status_code == 422


# ─── GET /tracking/{bid_id} ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tracking_happy_path_bid_intelligence(app):
    """GET /tracking/{bid_id} with bid_intelligence data → full tracking."""
    bi_row = {
        "id": BID_ID,
        "tender_id": TENDER_ID,
        "our_price": 250000.50,
        "winning_price": 240000.00,
        "n_competitors": 5,
        "rank_position": 2,
        "won": False,
        "bid_date": datetime(2025, 3, 15).date(),
        "created_at": datetime(2025, 3, 20, tzinfo=timezone.utc),
    }

    call_count = [0]
    def mock_fetchone():
        call_count[0] += 1
        if call_count[0] == 1:
            return bi_row
        return None

    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(side_effect=mock_fetchone)

    @contextmanager
    def fake_db_cursor():
        yield _make_mock_conn(), cur

    with patch("services.api.services.api.routers.submit_wizard.db_cursor", side_effect=fake_db_cursor):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.get(f"{PREFIX}/tracking/{BID_ID}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["bid_id"] == BID_ID
    assert data["tender_id"] == TENDER_ID
    assert data["submission_status"] == "lost"
    assert data["result"] == "lost"
    assert data["ranking_position"] == 2
    assert data["total_bidders"] == 5
    assert data["our_price"] == 250000.50
    assert data["winning_price"] == 240000.00
    assert len(data["events"]) >= 1


@pytest.mark.asyncio
async def test_tracking_won_bid(app):
    """GET /tracking/{bid_id} for a won bid."""
    bi_row = {
        "id": BID_ID,
        "tender_id": TENDER_ID,
        "our_price": 200000.0,
        "winning_price": 200000.0,
        "n_competitors": 3,
        "rank_position": 1,
        "won": True,
        "bid_date": datetime(2025, 4, 1).date(),
        "created_at": datetime(2025, 4, 5, tzinfo=timezone.utc),
    }

    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(return_value=bi_row)

    @contextmanager
    def fake_db_cursor():
        yield _make_mock_conn(), cur

    with patch("services.api.services.api.routers.submit_wizard.db_cursor", side_effect=fake_db_cursor):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.get(f"{PREFIX}/tracking/{BID_ID}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["submission_status"] == "won"
    assert data["result"] == "won"
    assert data["ranking_position"] == 1


@pytest.mark.asyncio
async def test_tracking_from_offers_table(app):
    """GET /tracking/{bid_id} when not in bid_intelligence but in offers."""
    offer_row = {
        "id": BID_ID,
        "tender_id": TENDER_ID,
        "status": "confirmed",
        "price_gross_pln": 300000.0,
        "created_at": datetime(2025, 5, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2025, 5, 2, tzinfo=timezone.utc),
        "metadata": json.dumps({"confirmation": {"confirmation_hash": "sha256:abc123def456"}}),
    }

    call_count = [0]
    def mock_fetchone():
        call_count[0] += 1
        if call_count[0] == 1:
            return None  # bid_intelligence not found
        if call_count[0] == 2:
            return offer_row  # offers table
        return None

    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(side_effect=mock_fetchone)

    @contextmanager
    def fake_db_cursor():
        yield _make_mock_conn(), cur

    with patch("services.api.services.api.routers.submit_wizard.db_cursor", side_effect=fake_db_cursor):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.get(f"{PREFIX}/tracking/{BID_ID}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["submission_status"] == "confirmed"
    assert data["our_price"] == 300000.0
    assert len(data["events"]) >= 1


@pytest.mark.asyncio
async def test_tracking_bid_not_found(app):
    """GET /tracking/{bid_id} when bid not in any table → returns draft with not_found event."""
    call_count = [0]
    def mock_fetchone():
        call_count[0] += 1
        return None  # Nothing found

    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(side_effect=mock_fetchone)

    @contextmanager
    def fake_db_cursor():
        yield _make_mock_conn(), cur

    with patch("services.api.services.api.routers.submit_wizard.db_cursor", side_effect=fake_db_cursor):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.get(f"{PREFIX}/tracking/{BID_ID}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["submission_status"] == "draft"
    assert any(e["event"] == "not_found" for e in data["events"])


@pytest.mark.asyncio
async def test_tracking_invalid_uuid(app):
    """GET /tracking/bad-uuid → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
        resp = await c.get(f"{PREFIX}/tracking/not-a-uuid")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_tracking_db_error_graceful(app):
    """GET /tracking/{bid_id} with DB error → returns error event."""
    with patch("services.api.services.api.routers.submit_wizard.db_cursor") as mock_db:
        mock_db.side_effect = Exception("DB down")

        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.get(f"{PREFIX}/tracking/{BID_ID}")

    assert resp.status_code == 200
    data = resp.json()
    assert any(e["event"] == "error" for e in data["events"])


@pytest.mark.asyncio
async def test_tracking_pending_result(app):
    """GET /tracking/{bid_id} with won=None → result is pending."""
    bi_row = {
        "id": BID_ID,
        "tender_id": TENDER_ID,
        "our_price": 180000.0,
        "winning_price": None,
        "n_competitors": None,
        "rank_position": None,
        "won": None,
        "bid_date": datetime(2025, 6, 1).date(),
        "created_at": datetime(2025, 6, 2, tzinfo=timezone.utc),
    }

    cur = MagicMock()
    cur.execute = MagicMock()
    cur.fetchone = MagicMock(return_value=bi_row)

    @contextmanager
    def fake_db_cursor():
        yield _make_mock_conn(), cur

    with patch("services.api.services.api.routers.submit_wizard.db_cursor", side_effect=fake_db_cursor):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
            resp = await c.get(f"{PREFIX}/tracking/{BID_ID}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["submission_status"] == "submitted"
    assert data["result"] == "pending"
    assert data["next_expected_event"] == "Otwarcie ofert"
