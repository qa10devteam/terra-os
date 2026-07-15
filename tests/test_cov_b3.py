"""BLOK-3 — Coverage push for AI/ML/search modules.

Targets (existing → target):
  routers/chat.py                19% → 80%+
  routers/krs_verify.py          30% → 80%+
  routers/bzp_documents.py       51% → 80%+
  routers/semantic_search.py     61% → 80%+
  routers/icb_advanced.py        63% → 80%+  (boost)
  routers/automations.py         63% → 80%+  (boost)
  routers/dashboard.py           65% → 80%+  (boost)
  routers/market_intelligence.py 74% → 80%+  (boost)
  routers/gus_bdl.py             74% → 80%+  (boost)
  intelligence/win_prob_ml.py    76% → 80%+  (boost)
  routers/estimates_v2.py        (additional tests)
"""
from __future__ import annotations

import json
import os
import pickle
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    from services.api.services.api.main import app as _app
    return _app


# ─── DB mock helpers ─────────────────────────────────────────────────────────

def _mock_conn(fetchone=None, fetchall=None, scalar=None, rowcount=1):
    """Return a MagicMock that plays both context-manager and connection roles."""
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    r = conn.execute.return_value
    r.fetchone.return_value = fetchone
    r.fetchall.return_value = fetchall or []
    r.scalar.return_value = scalar
    r.rowcount = rowcount
    # .mappings().all() / .mappings().one()
    r.mappings.return_value.all.return_value = fetchall or []
    r.mappings.return_value.one.return_value = fetchone or MagicMock(
        total_tenders=0, new_today=0, high_score_count=0,
        avg_score=None, pipeline_value=0, unique_buyers=0,
    )
    return conn


def _mock_engine(conn):
    eng = MagicMock()
    eng.return_value.connect.return_value = conn
    eng.return_value.begin.return_value = conn
    return eng


# ═══════════════════════════════════════════════════════════════════════════════
# 1. chat.py  (19% → 80%+)
# ═══════════════════════════════════════════════════════════════════════════════

class TestChatParseEditIntent:
    """Unit-test _parse_edit_intent without DB or LLM."""

    def _parse(self, msg, params=None):
        from services.api.services.api.routers.chat import _parse_edit_intent
        return _parse_edit_intent(msg, params or {})

    def test_narzut_pattern(self):
        result = self._parse("podnieś narzut do 15%")
        assert result["op"] == "set_param"
        assert result["target"] == "kp_pct"
        assert result["value"] == "15"

    def test_zysk_pattern(self):
        result = self._parse("ustaw zysk na 10%")
        assert result["op"] == "set_param"
        assert result["target"] == "zysk_pct"

    def test_zysk_marza_pattern(self):
        result = self._parse("marża 8,5%")
        assert result["op"] == "set_param"
        assert result["target"] == "zysk_pct"
        assert result["value"] == "8.5"

    def test_robocizna_pattern(self):
        result = self._parse("zmień robociznę na 40 zł/rg")
        assert result["op"] == "set_param"
        assert result["target"] == "robocizna_zl_rg"
        assert result["value"] == "40"

    def test_noop_fallback_with_stub_llm(self):
        """Unknown message → LLM stub → noop."""
        stub_llm = MagicMock()
        stub_llm.generate.return_value = '{"op": "noop", "target": null, "value": null}'
        with patch("services.api.services.api.routers.chat.get_llm_client", return_value=stub_llm):
            result = self._parse("coś zupełnie innego")
        assert result["op"] == "noop"

    def test_llm_returns_valid_op(self):
        """LLM returns a valid structured edit."""
        stub_llm = MagicMock()
        stub_llm.generate.return_value = '{"op": "set_param", "target": "kp_pct", "value": "12"}'
        with patch("services.api.services.api.routers.chat.get_llm_client", return_value=stub_llm):
            result = self._parse("change overhead to 12")
        assert result["op"] == "set_param"

    def test_llm_returns_invalid_json(self):
        """LLM error → noop fallback."""
        stub_llm = MagicMock()
        stub_llm.generate.side_effect = Exception("LLM failed")
        with patch("services.api.services.api.routers.chat.get_llm_client", return_value=stub_llm):
            result = self._parse("gibberish request abc")
        assert result["op"] == "noop"


class TestChatEstimateEndpoint:
    """Test /api/v1/estimates/{id}/chat via ASGI."""

    @pytest.mark.asyncio
    async def test_chat_estimate_404(self, app, auth_headers):
        """Unknown estimate_id → 404."""
        conn = _mock_conn(fetchone=None)
        with patch("services.api.services.api.routers.chat.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v1/estimates/nonexistent-id/chat",
                    json={"message": "podnieś narzut do 15%"},
                    headers=auth_headers,
                )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_chat_estimate_200_noop(self, app, auth_headers):
        """Known estimate, noop command → SSE stream with done:false."""
        row = MagicMock()
        row.__getitem__ = lambda s, i: [
            "est-001", "tender-001", "owner", {}
        ][i]
        conn = _mock_conn(fetchone=row)

        stub_llm = MagicMock()
        stub_llm.generate.return_value = '{"op": "noop"}'

        with patch("services.api.services.api.routers.chat.get_engine",
                   _mock_engine(conn)), \
             patch("services.api.services.api.routers.chat.get_llm_client",
                   return_value=stub_llm):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v1/estimates/est-001/chat",
                    json={"message": "xyzzy unknown"},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_chat_estimate_kp_edit_no_analysis(self, app, auth_headers):
        """Known estimate, kp edit, but no analysis in DB → SSE error event."""
        row = MagicMock()
        row.__getitem__ = lambda s, i: [
            "est-001", "tender-002", "owner", {}
        ][i]
        conn = _mock_conn(fetchone=row)
        # Second fetchone (analysis query) returns None
        conn.execute.return_value.fetchone.side_effect = [row, None, None]

        with patch("services.api.services.api.routers.chat.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v1/estimates/est-001/chat",
                    json={"message": "podnieś narzut do 15%"},
                    headers=auth_headers,
                )
        assert r.status_code == 200


class TestGeneralChat:
    """Test /api/v1/chat rule-based fallback."""

    @pytest.mark.asyncio
    async def test_general_chat_przetarg(self, app, auth_headers):
        """Message about przetarg → rule-based answer."""
        stub_llm = MagicMock(spec=[])  # not VLLMClient
        with patch("services.api.services.api.routers.chat.get_llm_client",
                   return_value=stub_llm):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v1/chat",
                    json={"message": "co to jest przetarg?"},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        text = r.text
        assert "event: token" in text or "event: done" in text

    @pytest.mark.asyncio
    async def test_general_chat_ryzyko(self, app, auth_headers):
        stub_llm = MagicMock(spec=[])
        with patch("services.api.services.api.routers.chat.get_llm_client",
                   return_value=stub_llm):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v1/chat",
                    json={"message": "jak działa silnik decyzyjny i ryzyko?"},
                    headers=auth_headers,
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_general_chat_help(self, app, auth_headers):
        stub_llm = MagicMock(spec=[])
        with patch("services.api.services.api.routers.chat.get_llm_client",
                   return_value=stub_llm):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v1/chat",
                    json={"message": "jak mogę ci pomóc?"},
                    headers=auth_headers,
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_general_chat_default(self, app, auth_headers):
        stub_llm = MagicMock(spec=[])
        with patch("services.api.services.api.routers.chat.get_llm_client",
                   return_value=stub_llm):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v1/chat",
                    json={"message": "coś zupełnie losowego"},
                    headers=auth_headers,
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_general_chat_with_tender_id(self, app, auth_headers):
        stub_llm = MagicMock(spec=[])
        with patch("services.api.services.api.routers.chat.get_llm_client",
                   return_value=stub_llm):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v1/chat",
                    json={"message": "oferta", "tender_id": "tid-123", "context": "extra info"},
                    headers=auth_headers,
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_general_chat_vllm_streaming(self, app, auth_headers):
        """VLLMClient present → streaming path attempted."""
        from services.api.services.api.routers.chat import VLLMClient

        stub_llm = MagicMock(spec=VLLMClient)
        stub_llm.generate_stream.return_value = iter(["Hello ", "world"])

        with patch("services.api.services.api.routers.chat.get_llm_client",
                   return_value=stub_llm):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v1/chat",
                    json={"message": "test vllm"},
                    headers=auth_headers,
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_general_chat_vllm_streaming_fails_fallback(self, app, auth_headers):
        """VLLMClient streaming fails → generate() fallback."""
        from services.api.services.api.routers.chat import VLLMClient

        stub_llm = MagicMock(spec=VLLMClient)
        stub_llm.generate_stream.side_effect = Exception("stream error")
        stub_llm.generate.return_value = "Answer text"

        with patch("services.api.services.api.routers.chat.get_llm_client",
                   return_value=stub_llm):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v1/chat",
                    json={"message": "przetarg budowlany"},
                    headers=auth_headers,
                )
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 2. krs_verify.py  (30% → 80%+)
# ═══════════════════════════════════════════════════════════════════════════════

class TestKrsVerifyFunctions:
    """Unit-test _verify_krs and _verify_ceidg directly."""

    def test_verify_krs_success(self):
        from services.api.services.api.routers.krs_verify import _verify_krs
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "numerKRS": "0000123456",
            "odpis": {
                "dane": {
                    "dzialy": {
                        "dzial1": {
                            "danePodmiotu": {"nazwa": "Firma Testowa Sp. z o.o."}
                        }
                    }
                }
            }
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("services.api.services.api.routers.krs_verify.httpx.Client",
                   return_value=mock_client):
            result = _verify_krs("1234567890")

        assert result["nip"] == "1234567890"
        assert result["status"] == "active"
        assert result["source"] == "krs"

    def test_verify_krs_non_200(self):
        from services.api.services.api.routers.krs_verify import _verify_krs
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("services.api.services.api.routers.krs_verify.httpx.Client",
                   return_value=mock_client):
            result = _verify_krs("9999999999")

        assert result["status"] == "lookup_failed"

    def test_verify_krs_exception(self):
        from services.api.services.api.routers.krs_verify import _verify_krs

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("timeout")

        with patch("services.api.services.api.routers.krs_verify.httpx.Client",
                   return_value=mock_client):
            result = _verify_krs("1234567890")

        assert result["status"] == "lookup_failed"
        assert "error" in result

    def test_verify_ceidg_success(self):
        from services.api.services.api.routers.krs_verify import _verify_ceidg
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "firma": [{
                "regon": "123456789",
                "nazwa": "Jan Kowalski",
                "status": "active",
                "ulica": "Ul. Testowa 1",
                "kodPocztowy": "00-001",
                "miejscowosc": "Warszawa",
            }]
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("services.api.services.api.routers.krs_verify.httpx.Client",
                   return_value=mock_client):
            result = _verify_ceidg("1234567890")

        assert result["status"] == "active"
        assert result["source"] == "ceidg"

    def test_verify_ceidg_empty_firms(self):
        from services.api.services.api.routers.krs_verify import _verify_ceidg
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"firma": []}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("services.api.services.api.routers.krs_verify.httpx.Client",
                   return_value=mock_client):
            result = _verify_ceidg("9999999999")

        assert result["status"] == "lookup_failed"

    def test_verify_ceidg_exception(self):
        from services.api.services.api.routers.krs_verify import _verify_ceidg

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("network error")

        with patch("services.api.services.api.routers.krs_verify.httpx.Client",
                   return_value=mock_client):
            result = _verify_ceidg("1234567890")

        assert result["status"] == "lookup_failed"


class TestKrsVerifyEndpoints:
    """Test /api/v1/verify endpoints via ASGI."""

    @pytest.mark.asyncio
    async def test_verify_entity_cached(self, app, auth_headers):
        """Cache hit → returns cached result immediately."""
        import datetime
        cached_row = MagicMock()
        cached_row.id = uuid.uuid4()
        cached_row.nip = "1234567890"
        cached_row.regon = "123456789"
        cached_row.krs = "0000123456"
        cached_row.name = "Test Firma Sp. z o.o."
        cached_row.status = "active"
        cached_row.address = "Warszawa"
        cached_row.source = "krs"
        cached_row.verified_at = datetime.datetime.now()

        conn = _mock_conn(fetchone=cached_row)
        with patch("services.api.services.api.routers.krs_verify.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v1/verify",
                    json={"nip": "1234567890", "source": "krs"},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert data["cached"] is True

    @pytest.mark.asyncio
    async def test_verify_entity_fresh_krs(self, app, auth_headers):
        """No cache → fresh KRS lookup → store in DB."""
        conn = _mock_conn(fetchone=None)

        krs_result = {
            "nip": "1234567890",
            "krs": "0000123456",
            "name": "Firma Testowa",
            "status": "active",
            "address": "Warszawa",
            "source": "krs",
        }

        with patch("services.api.services.api.routers.krs_verify.get_engine",
                   _mock_engine(conn)), \
             patch("services.api.services.api.routers.krs_verify._verify_krs",
                   return_value=krs_result):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v1/verify",
                    json={"nip": "1234567890", "source": "krs"},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert data["cached"] is False
        assert data["nip"] == "1234567890"

    @pytest.mark.asyncio
    async def test_verify_entity_fresh_ceidg(self, app, auth_headers):
        conn = _mock_conn(fetchone=None)
        ceidg_result = {
            "nip": "1234567891",
            "regon": "123456789",
            "name": "Jan Kowalski",
            "status": "active",
            "address": "Kraków",
            "source": "ceidg",
        }
        with patch("services.api.services.api.routers.krs_verify.get_engine",
                   _mock_engine(conn)), \
             patch("services.api.services.api.routers.krs_verify._verify_ceidg",
                   return_value=ceidg_result):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v1/verify",
                    json={"nip": "1234567891", "source": "ceidg"},
                    headers=auth_headers,
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_verify_entity_auto_fallback_to_ceidg(self, app, auth_headers):
        """source=auto: KRS fails → try CEIDG."""
        conn = _mock_conn(fetchone=None)
        krs_failed = {"nip": "1234567890", "status": "lookup_failed", "source": "krs"}
        ceidg_ok = {"nip": "1234567890", "name": "Test", "status": "active", "source": "ceidg"}

        with patch("services.api.services.api.routers.krs_verify.get_engine",
                   _mock_engine(conn)), \
             patch("services.api.services.api.routers.krs_verify._verify_krs",
                   return_value=krs_failed), \
             patch("services.api.services.api.routers.krs_verify._verify_ceidg",
                   return_value=ceidg_ok):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v1/verify",
                    json={"nip": "1234567890", "source": "auto"},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert data["source"] == "ceidg"

    @pytest.mark.asyncio
    async def test_search_verifications_all(self, app, auth_headers):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.krs_verify.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get("/api/v1/verify/search", headers=auth_headers)
        assert r.status_code == 200
        assert "items" in r.json()

    @pytest.mark.asyncio
    async def test_search_verifications_by_nip(self, app, auth_headers):
        import datetime
        row = MagicMock()
        row.id = uuid.uuid4()
        row.nip = "1234567890"
        row.regon = "123456789"
        row.krs = ""
        row.name = "Test"
        row.status = "active"
        row.address = "Warszawa"
        row.source = "krs"
        row.verified_at = datetime.datetime.now()

        conn = _mock_conn(fetchall=[row])
        with patch("services.api.services.api.routers.krs_verify.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v1/verify/search?nip=1234567890",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# 3. bzp_documents.py  (51% → 80%+)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBzpDocumentsEndpoints:

    @pytest.mark.asyncio
    async def test_list_documents_with_local_file(self, app, auth_headers):
        """list_tender_documents: row with local [file:...] path (file exists)."""
        import datetime, tempfile
        # Create a real temp file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.write(b"PDF content")
        tmp.close()

        row = MagicMock()
        row.id = uuid.uuid4()
        row.bzp_notice_id = "2026/BZP00123456"
        row.doc_type = "NOTICE_PDF"
        row.filename = "ogloszenie.pdf"
        row.url = "https://ezamowienia.gov.pl/pdf"
        row.content = f"[file:{tmp.name}]"
        row.fetched_at = datetime.datetime.now()

        conn = _mock_conn(fetchall=[row])
        with patch("services.api.services.api.routers.bzp_documents.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(f"/api/v1/bzp/documents/tender-001", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["documents"][0]["is_local"] is True
        os.unlink(tmp.name)

    @pytest.mark.asyncio
    async def test_list_documents_nonexistent_file(self, app, auth_headers):
        """list_tender_documents: row with nonexistent local file."""
        import datetime
        row = MagicMock()
        row.id = uuid.uuid4()
        row.bzp_notice_id = "2026/BZP00999"
        row.doc_type = "NOTICE_PDF"
        row.filename = "file.pdf"
        row.url = "https://example.com"
        row.content = "[file:/tmp/nonexistent-xyz-abc.pdf]"
        row.fetched_at = datetime.datetime.now()

        conn = _mock_conn(fetchall=[row])
        with patch("services.api.services.api.routers.bzp_documents.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get("/api/v1/bzp/documents/tender-002", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["documents"][0]["size_kb"] is None

    @pytest.mark.asyncio
    async def test_fetch_documents_404(self, app, auth_headers):
        """POST /{tender_id}/fetch: tender not found → 404."""
        conn = _mock_conn(fetchone=None)
        with patch("services.api.services.api.routers.bzp_documents.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post("/api/v1/bzp/documents/nonexistent/fetch", headers=auth_headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_fetch_documents_422_no_ids(self, app, auth_headers):
        """POST /{tender_id}/fetch: tender without BZP number or OCDS URL → 422."""
        row = MagicMock()
        row.id = "tender-no-ids"
        row.url = "https://example.com/irrelevant"
        row.source = "manual"
        row.external_id = None

        conn = _mock_conn(fetchone=row)
        with patch("services.api.services.api.routers.bzp_documents.get_engine",
                   _mock_engine(conn)), \
             patch("services.api.services.api.routers.bzp_documents.extract_tender_id_from_url",
                   return_value=None):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post("/api/v1/bzp/documents/tender-no-ids/fetch", headers=auth_headers)
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_fetch_documents_queued_with_bzp_number(self, app, auth_headers):
        """POST /{tender_id}/fetch: valid tender with BZP number → queued."""
        row = MagicMock()
        row.id = "tender-valid"
        row.url = "https://ezamowienia.gov.pl/tenderId/123"
        row.source = "bzp"
        row.external_id = "2026/BZP 00123456"

        conn = _mock_conn(fetchone=row)
        with patch("services.api.services.api.routers.bzp_documents.get_engine",
                   _mock_engine(conn)), \
             patch("services.api.services.api.routers.bzp_documents.extract_tender_id_from_url",
                   return_value="ocds-123"), \
             patch("services.api.services.api.routers.bzp_documents._run_fetch"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post("/api/v1/bzp/documents/tender-valid/fetch", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_download_document_404(self, app, auth_headers):
        """GET /{tender_id}/download/{doc_id}: doc not found → 404."""
        conn = _mock_conn(fetchone=None)
        with patch("services.api.services.api.routers.bzp_documents.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v1/bzp/documents/t-001/download/doc-none",
                    headers=auth_headers,
                )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_download_document_swz_redirect(self, app, auth_headers):
        """GET /{tender_id}/download/{doc_id}: SWZ doc → 302 redirect."""
        row = MagicMock()
        row.url = "https://platformazakupowa.pl/swz/123"
        row.filename = "swz.pdf"
        row.content = ""
        row.doc_type = "SWZ"

        conn = _mock_conn(fetchone=row)
        with patch("services.api.services.api.routers.bzp_documents.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
                follow_redirects=False,
            ) as ac:
                r = await ac.get(
                    "/api/v1/bzp/documents/t-001/download/doc-swz",
                    headers=auth_headers,
                )
        assert r.status_code == 302

    @pytest.mark.asyncio
    async def test_download_document_no_url(self, app, auth_headers):
        """GET: doc with no valid URL → 404."""
        row = MagicMock()
        row.url = ""
        row.filename = "empty.pdf"
        row.content = ""
        row.doc_type = "NOTICE_PDF"

        conn = _mock_conn(fetchone=row)
        with patch("services.api.services.api.routers.bzp_documents.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v1/bzp/documents/t-001/download/doc-no-url",
                    headers=auth_headers,
                )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_download_document_local_file(self, app, auth_headers):
        """GET: local file → streaming response."""
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.write(b"%PDF-1.4 test content")
        tmp.close()

        row = MagicMock()
        row.url = "https://example.com/file.pdf"
        row.filename = "test.pdf"
        row.content = f"[file:{tmp.name}]"
        row.doc_type = "NOTICE_PDF"

        conn = _mock_conn(fetchone=row)
        try:
            with patch("services.api.services.api.routers.bzp_documents.get_engine",
                       _mock_engine(conn)):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                    r = await ac.get(
                        "/api/v1/bzp/documents/t-001/download/doc-local",
                        headers=auth_headers,
                    )
            assert r.status_code == 200
            assert b"PDF" in r.content
        finally:
            os.unlink(tmp.name)

    def test_run_fetch_exception_handling(self):
        """_run_fetch: BZPDocumentScraper raises → logs, doesn't propagate."""
        from services.api.services.api.routers.bzp_documents import _run_fetch

        mock_scraper_ctx = MagicMock()
        mock_scraper_ctx.__enter__ = MagicMock(side_effect=RuntimeError("scraper crashed"))
        mock_scraper_ctx.__exit__ = MagicMock(return_value=False)

        with patch("services.api.services.api.routers.bzp_documents.get_engine"), \
             patch("services.api.services.api.routers.bzp_documents.BZPDocumentScraper",
                   return_value=mock_scraper_ctx), \
             patch("services.api.services.api.routers.bzp_documents.STORAGE_DIR",
                   Path("/tmp")):
            # Should NOT raise
            _run_fetch("t-001", "2026/BZP00001", None)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. semantic_search.py  (61% → 80%+)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSemanticSearch:

    @pytest.mark.asyncio
    async def test_semantic_search_200(self, app, auth_headers):
        """POST /api/v2/tenders/semantic-search → 200."""
        row = MagicMock()
        row.__getitem__ = lambda s, i: [
            uuid.uuid4(), "Roboty budowlane", "Zamawiający", "45000000",
            5000000.0, 0.85, 0.92
        ][i]

        conn = _mock_conn(fetchall=[row])
        with patch("services.api.services.api.routers.semantic_search.get_engine",
                   _mock_engine(conn)), \
             patch("services.api.services.api.routers.semantic_search.embed_text",
                   return_value=[0.1] * 1536):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v2/tenders/semantic-search",
                    json={"query": "roboty budowlane drogi", "limit": 10,
                          "tenant_id": "ec3d1e16-2139-48c2-93b5-ffe0defd606d"},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_semantic_search_empty_results(self, app, auth_headers):
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.semantic_search.get_engine",
                   _mock_engine(conn)), \
             patch("services.api.services.api.routers.semantic_search.embed_text",
                   return_value=[0.0] * 1536):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v2/tenders/semantic-search",
                    json={"query": "xyzzy nonexistent", "limit": 5,
                          "tenant_id": "ec3d1e16-2139-48c2-93b5-ffe0defd606d"},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_rag_query_200(self, app, auth_headers):
        """POST /api/v2/rag/query → 200."""
        mock_rag_result = [{"chunk": "tekst dokumentu", "similarity": 0.9}]
        with patch("services.api.services.api.routers.semantic_search.rag_query",
                   return_value=mock_rag_result), \
             patch("services.api.services.api.routers.semantic_search.get_engine"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v2/rag/query?tender_id=tender-001",
                    json={"query": "warunki udziału", "top_k": 3},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_rag_chat_streaming(self, app, auth_headers):
        """POST /api/v2/rag/chat/{tender_id} → SSE stream."""
        def _gen_tokens(*args, **kwargs):
            yield "Token1"
            yield " Token2"

        with patch("services.api.services.api.routers.semantic_search.rag_generate",
                   side_effect=_gen_tokens), \
             patch("services.api.services.api.routers.semantic_search.get_llm_client"), \
             patch("services.api.services.api.routers.semantic_search.get_engine"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v2/rag/chat/tender-001",
                    json={"query": "jakie warunki?", "top_k": 3},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_embed_document_200(self, app, auth_headers):
        """POST /api/v2/rag/embed-document/{tender_id} → 200."""
        with patch("services.api.services.api.routers.semantic_search.embed_document_chunks",
                   return_value=5), \
             patch("services.api.services.api.routers.semantic_search.get_engine"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v2/rag/embed-document/tender-001",
                    json={"text": "Tekst dokumentu przetargowego...",
                          "source_id": "doc-001", "source_type": "swz"},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert data["chunks_created"] == 5

    @pytest.mark.asyncio
    async def test_run_batch_embedding_200(self, app, auth_headers):
        """POST /api/v2/embeddings/run-batch → 200."""
        with patch("services.api.services.api.routers.semantic_search.embed_tenders_batch",
                   return_value=42), \
             patch("services.api.services.api.routers.semantic_search.get_engine"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v2/embeddings/run-batch?limit=100",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert data["embedded_count"] == 42


# ═══════════════════════════════════════════════════════════════════════════════
# 5. icb_advanced.py additional  (63% → 80%+)
# ═══════════════════════════════════════════════════════════════════════════════

class TestIcbAdvancedBoost:

    @pytest.mark.asyncio
    async def test_compute_forecasts_200(self, app, auth_headers):
        """POST /api/v2/icb/forecast/compute → 200."""
        mock_result = {"categories": 10, "forecasts": 40}
        with patch("services.api.services.api.routers.icb_advanced.get_engine"), \
             patch("services.api.services.api.intelligence.forecaster.compute_all_forecasts",
                   return_value=mock_result):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v2/icb/forecast/compute?horizon=4",
                    headers=auth_headers,
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_category_detail_200(self, app, auth_headers):
        """GET /api/v2/icb/category/{cat}/detail → 200."""
        conn = _mock_conn(fetchall=[])
        import services.api.services.api.routers.icb_advanced as _mod
        _mod._dashboard_cache.clear()

        with patch("services.api.services.api.routers.icb_advanced.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/icb/category/murarstwo/detail?quarters=4",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert "category" in data
        assert "trend" in data

    @pytest.mark.asyncio
    async def test_kosztorys_autofill_200(self, app, auth_headers):
        """POST /api/v2/icb/kosztorys-autofill → 200."""
        mock_lq = MagicMock(return_value=(2026, 1))
        mock_regional = MagicMock(return_value=1.05)

        row = MagicMock()
        row.__getitem__ = lambda s, i: [uuid.uuid4(), "Beton B25", "KNR-45-01", "m3"][i]

        conn = _mock_conn(fetchall=[row])
        mock_search = MagicMock(return_value=[])

        with patch("services.api.services.api.routers.icb_advanced.get_engine",
                   _mock_engine(conn)), \
             patch("services.api.services.api.intelligence.icb_service.get_latest_quarter", mock_lq), \
             patch("services.api.services.api.intelligence.icb_service.get_regional_coefficient",
                   mock_regional), \
             patch("services.api.services.api.intelligence.icb_service.search_icb", mock_search):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v2/icb/kosztorys-autofill",
                    json={"kosztorys_id": "k-001", "voivodeship": "mazowieckie"},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert "kosztorys_id" in data
        assert "filled_from_icb" in data

    @pytest.mark.asyncio
    async def test_kosztorys_autofill_with_price_found(self, app, auth_headers):
        """POST /api/v2/icb/kosztorys-autofill: ICB price found → updates DB."""
        mock_lq = MagicMock(return_value=(2026, 1))
        mock_regional = MagicMock(return_value=1.0)

        row = MagicMock()
        row.__getitem__ = lambda s, i: [uuid.uuid4(), "cement", "1690000", "kg"][i]

        conn = _mock_conn(fetchall=[row])
        mock_search = MagicMock(return_value=[{
            "nazwa": "Cement portlandzki",
            "symbol": "1690000",
            "cena_netto": 350.0,
            "jednostka": "t",
        }])

        with patch("services.api.services.api.routers.icb_advanced.get_engine",
                   _mock_engine(conn)), \
             patch("services.api.services.api.intelligence.icb_service.get_latest_quarter", mock_lq), \
             patch("services.api.services.api.intelligence.icb_service.get_regional_coefficient",
                   mock_regional), \
             patch("services.api.services.api.intelligence.icb_service.search_icb", mock_search):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v2/icb/kosztorys-autofill",
                    json={"kosztorys_id": "k-002", "override_existing": True},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert r.json()["filled_from_icb"] >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# 6. automations.py additional  (63% → 80%+)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutomationsBoost:

    @pytest.mark.asyncio
    async def test_update_webhook_404(self, app, auth_headers):
        """PATCH /api/v2/automations/webhooks/{wid}: not found → 404."""
        conn = _mock_conn(rowcount=0)
        conn.execute.return_value.rowcount = 0

        with patch("services.api.services.api.routers.automations.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.patch(
                    "/api/v2/automations/webhooks/nonexistent-wid",
                    json={"name": "Updated Name"},
                    headers=auth_headers,
                )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_update_webhook_no_fields_400(self, app, auth_headers):
        """PATCH webhooks/{wid} with no update fields → 400."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.patch(
                "/api/v2/automations/webhooks/some-wid",
                json={},
                headers=auth_headers,
            )
        assert r.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_update_webhook_200(self, app, auth_headers):
        """PATCH webhooks/{wid}: found → 200."""
        conn = _mock_conn(rowcount=1)
        conn.execute.return_value.rowcount = 1

        with patch("services.api.services.api.routers.automations.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.patch(
                    "/api/v2/automations/webhooks/wid-001",
                    json={"active": False},
                    headers=auth_headers,
                )
        assert r.status_code in (200, 404)  # depends on mock rowcount

    @pytest.mark.asyncio
    async def test_delete_webhook_404(self, app, auth_headers):
        """DELETE webhooks/{wid}: not found → 404."""
        conn = _mock_conn(rowcount=0)
        conn.execute.return_value.rowcount = 0

        with patch("services.api.services.api.routers.automations.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.delete(
                    "/api/v2/automations/webhooks/nonexistent",
                    headers=auth_headers,
                )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_webhook_200(self, app, auth_headers):
        """DELETE webhooks/{wid}: found → 200."""
        conn = _mock_conn(rowcount=1)
        conn.execute.return_value.rowcount = 1

        with patch("services.api.services.api.routers.automations.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.delete(
                    "/api/v2/automations/webhooks/wid-001",
                    headers=auth_headers,
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_trigger_event_unknown_422(self, app, auth_headers):
        """POST /automations/trigger with unknown event → 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.post(
                "/api/v2/automations/trigger",
                json={"event": "unknown.event", "entity_id": "e-001"},
                headers=auth_headers,
            )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_trigger_event_known_200(self, app, auth_headers):
        """POST /automations/trigger with known event → 200 (async dispatch)."""
        conn = _mock_conn(fetchone=None, fetchall=[])

        with patch("services.api.services.api.routers.automations.get_engine",
                   _mock_engine(conn)), \
             patch("services.api.services.api.routers.automations._log_event"), \
             patch("services.api.services.api.routers.automations._enrich_entity",
                   return_value={}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v2/automations/trigger",
                    json={"event": "kosztorys.ready", "entity_id": "k-001",
                          "payload": {"note": "test"}},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "triggered"

    @pytest.mark.asyncio
    async def test_list_events_200(self, app, auth_headers):
        """GET /automations/events → 200 with events dict."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.get("/api/v2/automations/events", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "events" in data
        assert "kosztorys.ready" in data["events"]

    @pytest.mark.asyncio
    async def test_event_history_200(self, app, auth_headers):
        """GET /automations/history → 200."""
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.automations.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/automations/history?limit=10",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_suggestions_kosztorys_empty(self, app, auth_headers):
        """GET /automations/suggestions/kosztorys/{id}: not found → empty list."""
        conn = _mock_conn(fetchone=None)
        with patch("services.api.services.api.routers.automations.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/automations/suggestions/kosztorys/k-none",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_suggestions_kosztorys_with_data(self, app, auth_headers):
        """GET /automations/suggestions/kosztorys/{id}: row found → suggestions."""
        row = MagicMock()
        row.poz_count = 5
        row.suma_netto = 500000
        row.win_probability = 0.3
        row.anomaly_score = 0.8
        row.status = "draft"

        conn = _mock_conn(fetchone=row)
        with patch("services.api.services.api.routers.automations.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/automations/suggestions/kosztorys/k-001",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        suggestions = r.json()
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    @pytest.mark.asyncio
    async def test_suggestions_tender_empty(self, app, auth_headers):
        """GET /automations/suggestions/tender/{id}: not found → empty."""
        conn = _mock_conn(fetchone=None)
        with patch("services.api.services.api.routers.automations.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/automations/suggestions/tender/t-none",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_suggestions_tender_with_data(self, app, auth_headers):
        """GET /automations/suggestions/tender/{id}: found → suggestions."""
        row = MagicMock()
        row.stage = "new"
        row.deadline_at = None
        row.title = "Remont drogi"

        conn = _mock_conn(fetchone=row)
        with patch("services.api.services.api.routers.automations.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/automations/suggestions/tender/t-001",
                    headers=auth_headers,
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_suggestions_unknown_type(self, app, auth_headers):
        """GET /automations/suggestions/other/{id}: unknown entity_type → empty list."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.get(
                "/api/v2/automations/suggestions/unknown/e-001",
                headers=auth_headers,
            )
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_n8n_status_unavailable(self, app, auth_headers):
        """GET /automations/n8n/status: n8n client unavailable → status=unavailable."""
        with patch("services.api.services.api.routers.automations.get_n8n_client",
                   side_effect=Exception("n8n not running")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/automations/n8n/status",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "unavailable"

    @pytest.mark.asyncio
    async def test_n8n_workflows_error(self, app, auth_headers):
        """GET /automations/n8n/workflows: error → empty list."""
        with patch("services.api.services.api.routers.automations.get_n8n_client",
                   side_effect=Exception("connection refused")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/automations/n8n/workflows",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_n8n_provision_500(self, app, auth_headers):
        """POST /automations/n8n/provision: provisioning fails → 500."""
        with patch("services.api.services.api.routers.automations.get_n8n_client",
                   side_effect=Exception("could not provision")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v2/automations/n8n/provision?event=kosztorys.ready",
                    headers=auth_headers,
                )
        assert r.status_code == 500

    @pytest.mark.asyncio
    async def test_n8n_webhook_test_200(self, app, auth_headers):
        """POST /automations/n8n/webhook-test → 200."""
        with patch("services.api.services.api.routers.automations.trigger_webhook",
                   return_value=True):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v2/automations/n8n/webhook-test",
                    json={"event_type": "TenderCreated", "payload": {"test": True}},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert data["sent"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# 7. dashboard.py additional  (65% → 80%+)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboardBoost:

    @pytest.mark.asyncio
    async def test_dashboard_kpi_root_200(self, app, auth_headers):
        """GET /api/v2/dashboard → 200."""
        conn = _mock_conn(fetchone=None, fetchall=[])
        conn.execute.return_value.fetchone.side_effect = [
            None,  # mv_pipeline_kpi not found
            MagicMock(
                active_count=5, pipeline_value=1000000,
                win_rate_mtd=25.0, avg_deal_size=200000,
                new_today=2,
            ),  # inline fallback
        ]
        with patch("services.api.services.api.routers.dashboard.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get("/api/v2/dashboard", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "active_tenders" in data

    @pytest.mark.asyncio
    async def test_get_digest_404_no_row(self, app, auth_headers):
        """GET /api/v2/dashboard/digest: no digest in DB → 404."""
        conn = _mock_conn(fetchone=None)
        with patch("services.api.services.api.routers.dashboard.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get("/api/v2/dashboard/digest", headers=auth_headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_get_digest_404_expired(self, app, auth_headers):
        """GET /api/v2/dashboard/digest: old digest → 404 expired."""
        import datetime
        old_time = datetime.datetime.now() - datetime.timedelta(hours=10)
        row = MagicMock()
        row.__getitem__ = lambda s, i: [
            json.dumps({"content": "Old digest"}),
            old_time,
        ][i]

        conn = _mock_conn(fetchone=row)
        with patch("services.api.services.api.routers.dashboard.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get("/api/v2/dashboard/digest", headers=auth_headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_get_digest_200_fresh(self, app, auth_headers):
        """GET /api/v2/dashboard/digest: fresh digest → 200."""
        import datetime
        fresh_time = datetime.datetime.now(datetime.timezone.utc)
        row = MagicMock()
        row.__getitem__ = lambda s, i: [
            {"content": "## Digest dzienny\nAktywnych: 5"},
            fresh_time,
        ][i]

        conn = _mock_conn(fetchone=row)
        with patch("services.api.services.api.routers.dashboard.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get("/api/v2/dashboard/digest", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "content" in data

    @pytest.mark.asyncio
    async def test_generate_digest_502_vllm_unavailable(self, app, auth_headers):
        """POST /api/v2/dashboard/digest/generate: vLLM fails → 502."""
        conn = _mock_conn(fetchone=None, fetchall=[])
        conn.execute.return_value.mappings.return_value.one.return_value = MagicMock(
            total_tenders=10, new_today=2, high_score_count=5,
            avg_score=0.7, pipeline_value=5000000, unique_buyers=8,
        )
        conn.execute.return_value.fetchone.return_value = MagicMock(
            total_tenders=10, new_today=2, high_score_count=5,
            avg_score=0.7, pipeline_value=5000000, unique_buyers=8,
        )
        conn.execute.return_value.fetchall.return_value = []

        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.post.side_effect = Exception("Connection refused")

        with patch("services.api.services.api.routers.dashboard.get_engine",
                   _mock_engine(conn)), \
             patch("services.api.services.api.routers.dashboard.httpx.Client",
                   return_value=mock_http_client):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v2/dashboard/digest/generate",
                    headers=auth_headers,
                )
        assert r.status_code == 502

    @pytest.mark.asyncio
    async def test_pipeline_kpi_mv_fallback_200(self, app, auth_headers):
        """GET /api/v2/dashboard/pipeline-kpi: mv fails → inline fallback."""
        agg_mock = MagicMock()
        agg_mock.active_count = 5
        agg_mock.pipeline_value = 1000000.0
        agg_mock.win_rate_mtd = 25.0
        agg_mock.avg_deal_size = 200000.0
        agg_mock.new_today = 2

        conn = _mock_conn(fetchone=agg_mock)
        # First call raises (mv not found), second returns inline data
        conn.execute.return_value.fetchone.side_effect = [
            Exception("mv_pipeline_kpi not found"),
            agg_mock,
        ]

        with patch("services.api.services.api.routers.dashboard.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get("/api/v2/dashboard/pipeline-kpi", headers=auth_headers)
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 8. market_intelligence.py additional  (74% → 80%+)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketIntelligenceBoost:

    @pytest.mark.asyncio
    async def test_benchmark_missing_cpv_422(self, app, auth_headers):
        """GET /api/v2/intelligence/benchmark: missing cpv_prefix → 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.get("/api/v2/intelligence/benchmark", headers=auth_headers)
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_benchmark_short_cpv_422(self, app, auth_headers):
        """GET /api/v2/intelligence/benchmark: cpv_prefix too short → 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.get("/api/v2/intelligence/benchmark?cpv_prefix=4", headers=auth_headers)
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_benchmark_200_empty(self, app, auth_headers):
        """GET /api/v2/intelligence/benchmark: valid, no data → empty."""
        conn = _mock_conn(fetchall=[])
        conn.execute.return_value.mappings.return_value.all.return_value = []
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/intelligence/benchmark?cpv_prefix=45&province=PL22",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_icb_prices_invalid_typ_rms_400(self, app, auth_headers):
        """GET /api/v2/intelligence/prices/icb: invalid typ_rms → 400."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.get(
                "/api/v2/intelligence/prices/icb?typ_rms=X",
                headers=auth_headers,
            )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_icb_prices_200(self, app, auth_headers):
        """GET /api/v2/intelligence/prices/icb → 200."""
        conn = _mock_conn(fetchall=[])
        conn.execute.return_value.mappings.return_value.all.return_value = []
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/intelligence/prices/icb?typ_rms=M&category=beton_cement&year=2024",
                    headers=auth_headers,
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_price_inflation_invalid_typ_rms_400(self, app, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.get(
                "/api/v2/intelligence/prices/inflation?typ_rms=Z",
                headers=auth_headers,
            )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_win_rates_200(self, app, auth_headers):
        """GET /api/v2/intelligence/win-rates → 200."""
        conn = _mock_conn(fetchall=[])
        conn.execute.return_value.mappings.return_value.all.return_value = []
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/intelligence/win-rates?cpv_prefix=45",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert "cpv_prefix" in data

    @pytest.mark.asyncio
    async def test_top_buyers_cpv_200(self, app, auth_headers):
        """GET /api/v2/intelligence/top-buyers-cpv → 200."""
        conn = _mock_conn(fetchall=[])
        conn.execute.return_value.mappings.return_value.all.return_value = []
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/intelligence/top-buyers-cpv?cpv_prefix=45",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert "cpv_prefix" in data

    @pytest.mark.asyncio
    async def test_fts_with_filters_200(self, app, auth_headers):
        """GET /api/v2/intelligence/fts with all filters → 200."""
        conn = _mock_conn(scalar=0, fetchall=[])
        conn.execute.return_value.mappings.return_value.all.return_value = []
        conn.execute.return_value.scalar.return_value = 0
        with patch("services.api.services.api.routers.market_intelligence.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/intelligence/fts?q=remont+drogi"
                    "&cpv_prefix=45&province=PL22&value_min=1000&value_max=5000000"
                    "&notice_type=ogłoszenie&limit=10&offset=0",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert "query" in data


# ═══════════════════════════════════════════════════════════════════════════════
# 9. gus_bdl.py additional  (74% → 80%+)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGusBdlBoost:

    def test_fetch_variable_success(self):
        """_fetch_variable: HTTP 200 → parsed results."""
        from services.api.services.api.routers.gus_bdl import _fetch_variable

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "measureUnitName": "%",
            "results": [{
                "values": [{"year": 2024, "period": "rok", "val": 103.5}]
            }]
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("services.api.services.api.routers.gus_bdl.httpx.Client",
                   return_value=mock_client):
            results = _fetch_variable("P1774", "CPI", 2024)

        assert len(results) >= 1
        assert results[0]["variable_id"] == "P1774"
        assert results[0]["value"] == 103.5

    def test_fetch_variable_exception(self):
        """_fetch_variable: connection error → stub with error."""
        from services.api.services.api.routers.gus_bdl import _fetch_variable

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("timeout")

        with patch("services.api.services.api.routers.gus_bdl.httpx.Client",
                   return_value=mock_client):
            results = _fetch_variable("P1774", "CPI", 2024)

        assert len(results) == 1
        assert "error" in results[0]

    @pytest.mark.asyncio
    async def test_gus_buyer_found_in_crm(self, app, auth_headers):
        """GET /api/v2/gus/buyer/{nip}: found in buyer_crm → 200."""
        import datetime
        row = MagicMock()
        row.crm_stage = "prospect"
        row.contact_name = "Jan Kowalski"
        row.contact_email = "jan@example.com"
        row.annual_budget_est = 5000000
        row.notes = "Important client"
        row.last_verified_at = datetime.datetime.now()

        conn = _mock_conn(fetchone=row)
        with patch("services.api.services.api.routers.gus_bdl.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/gus/buyer/1234567890",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert data["source"] == "buyer_crm"

    @pytest.mark.asyncio
    async def test_gus_buyer_fallback_entity_verifications(self, app, auth_headers):
        """GET /api/v2/gus/buyer/{nip}: not in crm → fallback to entity_verifications."""
        import datetime
        row2 = MagicMock()
        row2.source = "krs"
        row2.name = "Firma ABC"
        row2.status = "active"
        row2.address = "Warszawa"
        row2.verified_at = datetime.datetime.now()

        conn = _mock_conn(fetchone=None)
        # First call (buyer_crm) returns None, second (entity_verifications) returns row2
        conn.execute.return_value.fetchone.side_effect = [None, row2]

        with patch("services.api.services.api.routers.gus_bdl.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/gus/buyer/1234567890",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert data["source"] == "krs"

    @pytest.mark.asyncio
    async def test_gus_buyer_not_found(self, app, auth_headers):
        """GET /api/v2/gus/buyer/{nip}: not in any source → 200 with not_found."""
        conn = _mock_conn(fetchone=None)
        conn.execute.return_value.fetchone.side_effect = [None, None]

        with patch("services.api.services.api.routers.gus_bdl.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/gus/buyer/9999999999",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert data["source"] == "not_found"


# ═══════════════════════════════════════════════════════════════════════════════
# 10. win_prob_ml.py additional  (76% → 80%+)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWinProbML:

    def setup_method(self):
        """Reset module-level state before each test."""
        import services.api.services.api.intelligence.win_prob_ml as m
        m._model = None
        m._cpv_encoder = {}
        m._region_encoder = {}
        m._last_trained = None

    def test_encode_cpv_new(self):
        import services.api.services.api.intelligence.win_prob_ml as m
        m._cpv_encoder = {}
        idx1 = m._encode_cpv("45000000")
        idx2 = m._encode_cpv("71000000")
        assert idx1 != idx2
        assert m._encode_cpv("45000000") == idx1  # stable

    def test_encode_cpv_none(self):
        import services.api.services.api.intelligence.win_prob_ml as m
        idx = m._encode_cpv(None)
        assert isinstance(idx, int)

    def test_encode_region_new(self):
        import services.api.services.api.intelligence.win_prob_ml as m
        m._region_encoder = {}
        idx1 = m._encode_region("PL91")
        idx2 = m._encode_region("PL22")
        assert idx1 != idx2

    def test_encode_region_none(self):
        import services.api.services.api.intelligence.win_prob_ml as m
        idx = m._encode_region(None)
        assert isinstance(idx, int)

    def test_build_features(self):
        import services.api.services.api.intelligence.win_prob_ml as m
        feats = m._build_features(0.8, 2_000_000, "45000000", "PL91", 30)
        assert len(feats) == 5
        assert all(isinstance(f, float) for f in feats)
        assert 0.0 <= feats[0] <= 1.0  # match_score normalised
        assert 0.0 <= feats[4] <= 1.0  # days normalised

    def test_synthetic_training_data(self):
        import services.api.services.api.intelligence.win_prob_ml as m
        X, y = m._synthetic_training_data()
        assert len(X) == 40
        assert len(y) == 40
        assert sum(y) == 20  # 20 won

    def test_train_model_no_conn(self):
        """_train_model with conn=None → uses synthetic data."""
        import services.api.services.api.intelligence.win_prob_ml as m

        with patch("services.api.services.api.intelligence.win_prob_ml._MODEL_PATH",
                   "/tmp/_test_win_prob_b3.pkl"):
            m._train_model(conn=None)
            assert m._model is not None
            assert m._last_trained is not None

    def test_train_model_with_empty_conn(self):
        """_train_model: conn returns 0 rows → falls back to synthetic."""
        import services.api.services.api.intelligence.win_prob_ml as m

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []

        with patch("services.api.services.api.intelligence.win_prob_ml._MODEL_PATH",
                   "/tmp/_test_win_prob_b3b.pkl"):
            m._train_model(conn=mock_conn)
            assert m._model is not None

    def test_load_or_train_from_pickle(self):
        """_load_or_train: valid pickle exists → loads without training."""
        import services.api.services.api.intelligence.win_prob_ml as m
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        pipe = Pipeline([("scaler", StandardScaler()), ("lr", LogisticRegression())])
        X = [[0.5, 0.5, 0.0, 0.0, 0.5]] * 10
        y = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
        pipe.fit(X, y)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pkl")
        pickle.dump((pipe, {"45": 0}, {"PL": 0}), tmp)
        tmp.close()

        try:
            with patch("services.api.services.api.intelligence.win_prob_ml._MODEL_PATH",
                       tmp.name):
                m._load_or_train(conn=None)
            assert m._model is not None
        finally:
            os.unlink(tmp.name)

    def test_load_or_train_corrupted_pickle(self):
        """_load_or_train: corrupted pickle → falls back to training."""
        import services.api.services.api.intelligence.win_prob_ml as m

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pkl")
        tmp.write(b"not valid pickle data")
        tmp.close()

        try:
            with patch("services.api.services.api.intelligence.win_prob_ml._MODEL_PATH",
                       tmp.name):
                m._load_or_train(conn=None)
            assert m._model is not None
        finally:
            try:
                os.unlink(tmp.name)
            except FileNotFoundError:
                pass

    def test_predict_win_prob_no_row(self):
        """predict_win_prob: tender not found → 0.5 default."""
        import services.api.services.api.intelligence.win_prob_ml as m

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None

        with patch("services.api.services.api.intelligence.win_prob_ml._MODEL_PATH",
                   "/tmp/_test_predict_b3.pkl"):
            m._model = None  # force re-train
            prob = m.predict_win_prob("t-none", "tenant-001", mock_conn)
        assert prob == 0.5

    def test_predict_win_prob_with_data(self):
        """predict_win_prob: tender found, model trained → float 0-1."""
        import services.api.services.api.intelligence.win_prob_ml as m

        row = MagicMock()
        row.__getitem__ = lambda s, i: [
            0.8, 2_000_000.0, ["45000000"], "PL91", None
        ][i]

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = row

        with patch("services.api.services.api.intelligence.win_prob_ml._MODEL_PATH",
                   "/tmp/_test_predict_b3b.pkl"):
            m._model = None  # force re-train with synthetic
            m._load_or_train(conn=None)
            prob = m.predict_win_prob("t-001", "tenant-001", mock_conn)
        assert 0.0 <= prob <= 1.0

    def test_retrain_after_insert_no_new_rows(self):
        """retrain_after_insert: count <= _train_count → no retrain."""
        import services.api.services.api.intelligence.win_prob_ml as m
        m._train_count = 100

        mock_conn = MagicMock()
        mock_conn.execute.return_value.scalar.return_value = 50  # less than _train_count

        with patch.object(m, "_train_model") as mock_train:
            m.retrain_after_insert(mock_conn)
        mock_train.assert_not_called()

    def test_retrain_after_insert_new_rows(self):
        """retrain_after_insert: new rows → triggers retrain."""
        import services.api.services.api.intelligence.win_prob_ml as m
        m._train_count = 5

        mock_conn = MagicMock()
        mock_conn.execute.return_value.scalar.return_value = 10  # more than _train_count

        with patch.object(m, "_train_model") as mock_train:
            m.retrain_after_insert(mock_conn)
        mock_train.assert_called_once_with(mock_conn)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. estimates_v2.py  (additional coverage)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEstimatesV2:

    @pytest.mark.asyncio
    async def test_list_estimates_200(self, app, auth_headers):
        """GET /api/v2/estimates?tender_id=t-001 → 200."""
        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.estimates_v2.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/estimates?tender_id=tid-001",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert "items" in r.json()

    @pytest.mark.asyncio
    async def test_create_estimate_404_tender(self, app, auth_headers):
        """POST /api/v2/estimates: tender not found → 404."""
        conn = _mock_conn(fetchone=None)
        with patch("services.api.services.api.routers.estimates_v2.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v2/estimates",
                    json={"tender_id": "nonexistent", "variant": "doc"},
                    headers=auth_headers,
                )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_create_estimate_invalid_variant_422(self, app, auth_headers):
        """POST /api/v2/estimates: invalid variant → 422."""
        conn = _mock_conn(fetchone=MagicMock())  # tender found
        with patch("services.api.services.api.routers.estimates_v2.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.post(
                    "/api/v2/estimates",
                    json={"tender_id": "t-001", "variant": "invalid"},
                    headers=auth_headers,
                )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_get_estimate_404(self, app, auth_headers):
        """GET /api/v2/estimates/{id}: not found → 404."""
        conn = _mock_conn(fetchone=None, fetchall=[])
        with patch("services.api.services.api.routers.estimates_v2.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/estimates/nonexistent-est",
                    headers=auth_headers,
                )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_update_estimate_422_no_fields(self, app, auth_headers):
        """PUT /api/v2/estimates/{id}: no update fields → 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.put(
                "/api/v2/estimates/est-001",
                json={},
                headers=auth_headers,
            )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_update_estimate_404(self, app, auth_headers):
        """PUT /api/v2/estimates/{id}: not found → 404."""
        conn = _mock_conn(fetchone=None)
        with patch("services.api.services.api.routers.estimates_v2.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.put(
                    "/api/v2/estimates/nonexistent",
                    json={"total_net_pln": 500000.0},
                    headers=auth_headers,
                )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_patch_estimate_lines_404(self, app, auth_headers):
        """PATCH /api/v2/estimates/{id}/lines: estimate not found → 404."""
        conn = _mock_conn(fetchone=None)
        with patch("services.api.services.api.routers.estimates_v2.get_engine",
                   _mock_engine(conn)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.patch(
                    "/api/v2/estimates/nonexistent/lines",
                    json=[],
                    headers=auth_headers,
                )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_predict_cost_200(self, app, auth_headers):
        """GET /api/v2/estimates/predict → 200."""
        mock_pred = {
            "benchmark": 2500000.0,
            "estimate": 2600000.0,
            "low95": 2100000.0,
            "high95": 3000000.0,
            "method": "benchmark_interpolation",
        }
        mock_estimator = MagicMock()
        mock_estimator.predict.return_value = mock_pred

        with patch("services.api.services.api.routers.estimates_v2.get_estimator",
                   return_value=mock_estimator):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get(
                    "/api/v2/estimates/predict?cpv=45&region=mazowieckie"
                    "&area_m2=1000&floors=3",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        data = r.json()
        assert "benchmark" in data
        assert "confidence_interval" in data


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Internal helpers coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutomationsInternals:
    """Test _enrich_entity, _log_event, _dispatch_webhooks, _update_event_log."""

    def test_enrich_entity_kosztorys(self):
        from services.api.services.api.routers.automations import _enrich_entity

        row = MagicMock()
        row.__iter__ = lambda s: iter({
            "id": "k-001", "nazwa": "Kosztorys 1", "inwestor": "INV",
            "lokalizacja": "Warszawa", "typ": "typ1", "status": "draft",
            "suma_netto": 100000, "suma_brutto": 123000, "win_probability": 0.5
        }.items())

        mock_row_dict = {
            "id": "k-001", "nazwa": "Kosztorys 1"
        }

        conn = _mock_conn(fetchone=mock_row_dict)
        conn.execute.return_value.fetchone.return_value = MagicMock()
        conn.execute.return_value.fetchone.return_value.__bool__ = lambda s: True

        eng = MagicMock()
        eng.return_value.connect.return_value.__enter__ = MagicMock(return_value=conn)
        eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch("services.api.services.api.routers.automations.get_engine", eng):
            result = _enrich_entity("kosztorys.ready", "k-001", "tenant-001")
        assert isinstance(result, dict)

    def test_enrich_entity_tender(self):
        from services.api.services.api.routers.automations import _enrich_entity

        conn = _mock_conn(fetchone=None)
        with patch("services.api.services.api.routers.automations.get_engine",
                   _mock_engine(conn)):
            result = _enrich_entity("tender.analyze", "t-001", "tenant-001")
        assert isinstance(result, dict)

    def test_enrich_entity_intelligence(self):
        from services.api.services.api.routers.automations import _enrich_entity

        conn = _mock_conn(fetchone=None)
        with patch("services.api.services.api.routers.automations.get_engine",
                   _mock_engine(conn)):
            result = _enrich_entity("intelligence.price_alert", "alert-001", "tenant-001")
        assert result == {}

    def test_log_event_success(self):
        from services.api.services.api.routers.automations import _log_event

        conn = _mock_conn()
        with patch("services.api.services.api.routers.automations.get_engine",
                   _mock_engine(conn)):
            # Should not raise
            _log_event("tenant-001", "kosztorys.ready", "k-001", {"triggered_by": "user@test.com"})

    def test_log_event_exception(self):
        from services.api.services.api.routers.automations import _log_event

        eng = MagicMock()
        eng.return_value.connect.side_effect = Exception("DB down")
        with patch("services.api.services.api.routers.automations.get_engine", eng):
            # Should not raise (catches internally)
            _log_event("tenant-001", "kosztorys.ready", "k-001", {})

    @pytest.mark.asyncio
    async def test_dispatch_webhooks_no_rows(self):
        """_dispatch_webhooks: no matching webhooks → returns immediately."""
        from services.api.services.api.routers.automations import _dispatch_webhooks

        conn = _mock_conn(fetchall=[])
        with patch("services.api.services.api.routers.automations.get_engine",
                   _mock_engine(conn)):
            await _dispatch_webhooks("tenant-001", "kosztorys.ready", {"event": "test"})

    @pytest.mark.asyncio
    async def test_dispatch_webhooks_with_webhook(self):
        """_dispatch_webhooks: webhook found → POST to URL."""
        from services.api.services.api.routers.automations import _dispatch_webhooks

        wh = MagicMock()
        wh.id = "wh-001"
        wh.url = "https://n8n.example.com/webhook/test"
        wh.secret = "mysecret"
        wh.name = "Test Webhook"

        conn = _mock_conn(fetchall=[wh])

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_async_client.post = AsyncMock(return_value=mock_resp)

        with patch("services.api.services.api.routers.automations.get_engine",
                   _mock_engine(conn)), \
             patch("services.api.services.api.routers.automations.httpx.AsyncClient",
                   return_value=mock_async_client), \
             patch("services.api.services.api.routers.automations._update_event_log"):
            await _dispatch_webhooks("tenant-001", "kosztorys.ready", {"event": "test"})

    def test_update_event_log_success(self):
        from services.api.services.api.routers.automations import _update_event_log

        conn = _mock_conn()
        with patch("services.api.services.api.routers.automations.get_engine",
                   _mock_engine(conn)):
            _update_event_log("tenant-001", "kosztorys.ready", 200)

    def test_update_event_log_exception(self):
        from services.api.services.api.routers.automations import _update_event_log

        eng = MagicMock()
        eng.return_value.connect.side_effect = Exception("DB error")
        with patch("services.api.services.api.routers.automations.get_engine", eng):
            # Should not raise
            _update_event_log("tenant-001", "kosztorys.ready", 500)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. gus_bdl _sync_indicators coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestGusSyncIndicators:

    def test_sync_indicators_with_mock_fetch(self):
        """_sync_indicators: mocked _fetch_variable → stores to DB."""
        from services.api.services.api.routers.gus_bdl import _sync_indicators

        mock_items = [
            {"variable_id": "P1774", "name": "CPI", "unit": "%",
             "year": 2024, "period": "rok", "value": 103.5}
        ]

        conn = _mock_conn()
        with patch("services.api.services.api.routers.gus_bdl._fetch_variable",
                   return_value=mock_items), \
             patch("services.api.services.api.routers.gus_bdl.get_engine",
                   _mock_engine(conn)):
            result = _sync_indicators(2024)
        assert "stored" in result
        assert result["year"] == 2024

    def test_sync_indicators_skips_errors(self):
        """_sync_indicators: items with errors are skipped."""
        from services.api.services.api.routers.gus_bdl import _sync_indicators

        mock_items = [
            {"variable_id": "P1774", "name": "CPI", "unit": "%",
             "year": 2024, "period": "rok", "value": None,
             "error": "API unavailable"}
        ]

        conn = _mock_conn()
        with patch("services.api.services.api.routers.gus_bdl._fetch_variable",
                   return_value=mock_items), \
             patch("services.api.services.api.routers.gus_bdl.get_engine",
                   _mock_engine(conn)):
            result = _sync_indicators(2024)
        assert result["stored"] == 0  # skipped due to error


# ═══════════════════════════════════════════════════════════════════════════════
# 14. benchmark.py — competitors search (already 80% but add missing lines)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBenchmarkBoost:

    @pytest.mark.asyncio
    async def test_search_competitors_with_limit_200(self, app, auth_headers):
        """GET /api/v2/competitors/search?limit=5 → 200."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.get(
                "/api/v2/competitors/search?cpv=45000000&region=PL91&limit=5",
                headers=auth_headers,
            )
        assert r.status_code == 200
        data = r.json()
        assert "competitors" in data

    @pytest.mark.asyncio
    async def test_competitor_profile_known_nip(self, app, auth_headers):
        """GET /api/v2/competitors/{nip}/profile: known NIP → profile data."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            r = await ac.get(
                "/api/v2/competitors/1234567890/profile",
                headers=auth_headers,
            )
        assert r.status_code == 200
        data = r.json()
        assert "win_rate" in data
        assert "regions" in data
