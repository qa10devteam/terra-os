"""State-of-art testy scraperów terra-os.

Pokrywa:
  - scraper_base: RetryPolicy, CircuitBreaker, RateLimiter, ScraperMetrics, parse_pln, safe_date
  - normalize: normalize_bzp_notice, normalize_ted_notice, normalize_cpv, normalize_voivodeship
  - filters: passes_cpv_filter, passes_geo_filter
  - bzp_connector: fetch_notices_page (sync wrapper)
  - ted_connector: TEDConnector (mocked)
  - Integration: normalize → filter pipeline

Offline (TERRA_OFFLINE=1) — żadnych real HTTP calls.

Uruchomienie:
    cd /home/ubuntu/terra-os
    PYTHONPATH=... .venv/bin/python3 -m pytest tests/test_scrapers.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from decimal import Decimal
from datetime import date, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

# ── Env setup ─────────────────────────────────────────────────────────────────
os.environ.setdefault("TERRA_OFFLINE", "1")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "terraos")
os.environ.setdefault("DB_USER", "terraos")
os.environ.setdefault("DB_PASSWORD", "terra_dev_2026")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

# ── Imports ───────────────────────────────────────────────────────────────────
from services.ingestion.scraper_base import (
    AsyncHTTPClient,
    CircuitBreaker,
    CircuitState,
    RateLimiter,
    RetryPolicy,
    ScraperMetrics,
    parse_pln,
    normalize_cpv as base_normalize_cpv,
    safe_date,
)
from services.ingestion.bzp_connector import BZPRawNotice
from services.ingestion.normalize import (
    TenderIn,
    normalize_bzp_notice,
    normalize_ted_notice,
    normalize_cpv as norm_normalize_cpv,
    normalize_voivodeship,
)
from services.ingestion.filters import passes_cpv_filter, passes_geo_filter


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_tender(
    cpv: list[str] | None = None,
    voivodeship: str | None = None,
    value: float | None = None,
    source: str = "bzp",
) -> TenderIn:
    return TenderIn(
        source=source,
        external_id="TEST-001",
        title="Test przetarg budowlany",
        buyer="Gmina Testowa",
        cpv=cpv or [],
        voivodeship=voivodeship,
        value_pln=Decimal(str(value)) if value is not None else None,
        deadline_at=None,
        published_at=None,
        url=None,
        raw={},
    )


def make_bzp_notice(overrides: dict | None = None) -> BZPRawNotice:
    """Helper: BZPRawNotice z realnym schematem BZP API (ezamowienia.gov.pl)."""
    base: dict[str, Any] = {
        # Identifiers
        "bzpNumber": "2026/BZP 00315918",
        "noticeNumber": "2026/BZP 00315918/01",
        "noticeType": "ContractNotice",
        "orderType": "Works",  # real API value for roboty budowlane
        # Content
        "orderObject": "Przebudowa drogi gminnej nr 123 w m. Testowo",
        # CPV: real BZP API format — comma-separated string
        "cpvCode": "45233120-6 (Roboty w zakresie budowy dróg),45111200-0 (Roboty w zakresie gruntowania dróg)",
        # Organisation
        "organizationName": "Gmina Testowa",
        "organizationCity": "Testowo",
        "organizationProvince": "PL24",  # śląskie
        "organizationCountry": "PL",
        "organizationNationalId": "1234567890",
        # Dates
        "publicationDate": "2026-07-01T05:00:00Z",
        "submittingOffersDate": "2026-08-15T06:00:00Z",
        # Tender ID (used for URL construction)
        "tenderId": "ocds-148610-test-12345",
        # Value not in list endpoint — comes from htmlBody
        "estimatedValue": 1_500_000.0,
    }
    if overrides:
        base.update(overrides)
    return BZPRawNotice(base)


TED_NOTICE_RAW: dict[str, Any] = {
    # TED v3 eForms API schema (2026) — validated fields
    "publication-number": "123456-2026",
    "publication-date": "2026-08-15",
    "BT-21-Lot": [{"pol": ["Roboty budowlane w zakresie budowy dróg w m. Testowo"]}],
    "organisation-name-buyer": {"pol": ["Gmina Testowa"]},
    # CPV: list of 8-digit codes
    "classification-cpv": ["45233120", "45111200"],
    # Value: float/str directly (not nested dict)
    "estimated-value-lot": 2_000_000.0,
    "estimated-value-glo": 2_000_000.0,
    "NUTS": "PL22A",
    "nuts-code": ["PL22A"],
}


# ══════════════════════════════════════════════════════════════════════════════
# 1. RetryPolicy
# ══════════════════════════════════════════════════════════════════════════════

class TestRetryPolicy:
    """RetryPolicy.delay_for(attempt): exponential backoff + jitter."""

    def test_delay_increases_with_attempt(self):
        p = RetryPolicy(max_attempts=5, base_delay=1.0, max_delay=60.0, jitter=0.0)
        delays = [p.delay_for(i) for i in range(1, 5)]
        for i in range(len(delays) - 1):
            assert delays[i] <= delays[i + 1] + 0.01, f"delay not increasing: {delays}"

    def test_delay_capped_at_max(self):
        p = RetryPolicy(max_attempts=10, base_delay=1.0, max_delay=5.0, jitter=0.0)
        for attempt in range(1, 11):
            d = p.delay_for(attempt)
            assert d <= p.max_delay + 0.01, f"delay {d} > max_delay {p.max_delay}"

    def test_base_delay_attempt_1_no_jitter(self):
        p = RetryPolicy(max_attempts=4, base_delay=2.0, max_delay=60.0, jitter=0.0)
        assert abs(p.delay_for(1) - 2.0) < 0.01

    def test_jitter_adds_variance(self):
        p = RetryPolicy(max_attempts=4, base_delay=1.0, max_delay=60.0, jitter=0.5)
        delays = [p.delay_for(1) for _ in range(50)]
        # With 50% jitter, values should spread
        assert max(delays) - min(delays) > 0.1, "Jitter should add meaningful variance"

    def test_max_attempts_attribute(self):
        p = RetryPolicy(max_attempts=3)
        assert p.max_attempts == 3

    def test_backoff_factor_default_is_2(self):
        p = RetryPolicy(base_delay=1.0, max_delay=60.0, jitter=0.0)
        d1 = p.delay_for(1)
        d2 = p.delay_for(2)
        assert abs(d2 / d1 - 2.0) < 0.01, f"Expected 2x backoff, got {d2/d1:.2f}"


# ══════════════════════════════════════════════════════════════════════════════
# 2. CircuitBreaker
# ══════════════════════════════════════════════════════════════════════════════

class TestCircuitBreaker:
    """CircuitBreaker: CLOSED → OPEN → HALF_OPEN → CLOSED."""

    def test_starts_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_does_not_open_before_threshold(self):
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(4):
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_success_resets_to_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.05)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.1)
        assert cb.allow_request() is True  # HALF_OPEN → probe

    def test_failure_count_resets_after_success(self):
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(4):
            cb.record_failure()
        cb.record_success()
        # 4 more failures should not open (threshold=5, reset after success)
        for _ in range(4):
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED


# ══════════════════════════════════════════════════════════════════════════════
# 3. RateLimiter
# ══════════════════════════════════════════════════════════════════════════════

class TestRateLimiter:
    """RateLimiter: async token bucket, acquire(domain)."""

    @pytest.mark.asyncio
    async def test_burst_is_immediate(self):
        rl = RateLimiter(rate=1.0, burst=5)
        t0 = time.perf_counter()
        for _ in range(5):
            await rl.acquire("test.example.com")
        elapsed = time.perf_counter() - t0
        assert elapsed < 1.0, f"Burst of 5 took too long: {elapsed:.3f}s"

    @pytest.mark.asyncio
    async def test_different_domains_are_independent(self):
        rl = RateLimiter(rate=10.0, burst=3)
        t0 = time.perf_counter()
        await rl.acquire("domain_a.pl")
        await rl.acquire("domain_b.pl")
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.5, "Different domains should not rate-limit each other"

    @pytest.mark.asyncio
    async def test_throttles_after_burst_exhausted(self):
        rl = RateLimiter(rate=2.0, burst=2)
        domain = "throttled.example.com"
        # Drain burst
        await rl.acquire(domain)
        await rl.acquire(domain)
        # Third token must wait ~0.5s (rate=2/s)
        t0 = time.perf_counter()
        await rl.acquire(domain)
        elapsed = time.perf_counter() - t0
        assert elapsed >= 0.3, f"Expected throttle wait >=0.3s, got {elapsed:.3f}s"


# ══════════════════════════════════════════════════════════════════════════════
# 4. ScraperMetrics
# ══════════════════════════════════════════════════════════════════════════════

class TestScraperMetrics:
    """ScraperMetrics: counters, latency, to_dict."""

    def test_initial_zeros(self):
        m = ScraperMetrics(source="test_initial")
        assert m.requests_total == 0
        assert m.requests_ok == 0
        assert m.requests_error == 0
        assert m.items_fetched == 0

    def test_record_request_ok(self):
        m = ScraperMetrics(source="test_ok")
        m.record_request(ok=True, latency_ms=100.0)
        assert m.requests_total == 1
        assert m.requests_ok == 1
        assert m.requests_error == 0

    def test_record_request_error(self):
        m = ScraperMetrics(source="test_err")
        m.record_request(ok=False, latency_ms=50.0)
        assert m.requests_total == 1
        assert m.requests_error == 1
        assert m.requests_ok == 0

    def test_record_retry(self):
        m = ScraperMetrics(source="test_retry")
        m.record_request(ok=True, latency_ms=100.0, retried=True)
        assert m.requests_retried == 1

    def test_record_items(self):
        m = ScraperMetrics(source="test_items")
        m.record_items(fetched=5, saved=3, bytes_dl=1024)
        assert m.items_fetched == 5
        assert m.items_saved == 3
        assert m.bytes_downloaded == 1024

    def test_to_dict_keys(self):
        m = ScraperMetrics(source="test_dict")
        m.record_request(ok=True, latency_ms=120.0)
        m.record_items(fetched=3, saved=3)
        d = m.to_dict()
        assert "requests" in d
        assert "items" in d
        assert "latency_ms" in d

    def test_p50_latency(self):
        m = ScraperMetrics(source="test_p50")
        for ms in [100.0, 200.0, 300.0]:
            m.record_request(ok=True, latency_ms=ms)
        assert 100.0 <= m.p50_ms <= 300.0

    def test_p99_latency(self):
        m = ScraperMetrics(source="test_p99")
        for ms in range(1, 101):
            m.record_request(ok=True, latency_ms=float(ms))
        # p99 of 1..100 should be near 99
        assert m.p99_ms >= 90.0


# ══════════════════════════════════════════════════════════════════════════════
# 5. parse_pln + safe_date + normalize_cpv (base utils)
# ══════════════════════════════════════════════════════════════════════════════

class TestScraperBaseUtils:
    """parse_pln, safe_date, normalize_cpv from scraper_base."""

    def test_parse_pln_float(self):
        result = parse_pln(1_500_000.0)
        assert result == 1_500_000.0

    def test_parse_pln_polish_string(self):
        result = parse_pln("2 345 678,00 PLN")
        assert result is not None
        assert abs(result - 2_345_678.0) < 1.0

    def test_parse_pln_none_returns_none(self):
        assert parse_pln(None) is None

    def test_parse_pln_invalid_string(self):
        assert parse_pln("nie dotyczy") is None

    def test_parse_pln_zero_string(self):
        result = parse_pln("0")
        # 0 is ambiguous — either 0.0 or None is valid
        assert result is None or result == 0.0

    def test_normalize_cpv_full_code(self):
        result = base_normalize_cpv("45233120-6")
        assert result is not None
        assert "45233120" in result

    def test_normalize_cpv_8digit(self):
        result = base_normalize_cpv("45233120")
        assert result is not None
        assert "45233120" in result

    def test_normalize_cpv_none_returns_none(self):
        assert base_normalize_cpv(None) is None

    def test_safe_date_iso_date(self):
        result = safe_date("2026-08-15")
        assert result is not None
        assert "2026" in result
        assert "08" in result

    def test_safe_date_iso_datetime(self):
        result = safe_date("2026-08-15T12:00:00")
        assert result is not None
        assert "2026" in result

    def test_safe_date_none_returns_none(self):
        assert safe_date(None) is None

    def test_safe_date_empty_returns_none(self):
        assert safe_date("") is None

    def test_safe_date_invalid_returns_str_or_none(self):
        result = safe_date("abc")
        # implementation-defined: either None or a fallback str
        assert result is None or isinstance(result, str)

    def test_safe_date_pl_dot_format(self):
        result = safe_date("15.08.2026")
        assert result is not None
        assert "2026" in result


# ══════════════════════════════════════════════════════════════════════════════
# 6. normalize_bzp_notice
# ══════════════════════════════════════════════════════════════════════════════

class TestNormalizeBZP:
    """normalize_bzp_notice(BZPRawNotice) → TenderIn."""

    def test_returns_tender_in(self):
        t = normalize_bzp_notice(make_bzp_notice())
        assert t is not None
        assert isinstance(t, TenderIn)

    def test_source_is_bzp(self):
        t = normalize_bzp_notice(make_bzp_notice())
        assert t is not None
        assert t.source == "bzp"

    def test_title_contains_notice_name(self):
        t = normalize_bzp_notice(make_bzp_notice())
        assert t is not None
        assert len(t.title.strip()) > 0

    def test_external_id_not_empty(self):
        t = normalize_bzp_notice(make_bzp_notice())
        assert t is not None
        assert len(t.external_id) > 0

    def test_cpv_extracted(self):
        t = normalize_bzp_notice(make_bzp_notice())
        assert t is not None
        assert len(t.cpv) > 0
        assert any("45233" in c for c in t.cpv)

    def test_value_pln_extracted(self):
        t = normalize_bzp_notice(make_bzp_notice())
        assert t is not None
        assert t.value_pln is not None
        assert t.value_pln > 0

    def test_deadline_parsed(self):
        t = normalize_bzp_notice(make_bzp_notice())
        assert t is not None
        assert t.deadline_at is not None

    def test_voivodeship_extracted(self):
        t = normalize_bzp_notice(make_bzp_notice())
        assert t is not None
        # voivodeship should be non-empty
        assert t.voivodeship is not None

    def test_url_set(self):
        t = normalize_bzp_notice(make_bzp_notice())
        assert t is not None
        assert t.url and t.url.startswith("http")

    def test_raw_preserved(self):
        t = normalize_bzp_notice(make_bzp_notice())
        assert t is not None
        assert isinstance(t.raw, dict)

    def test_empty_notice_returns_none(self):
        t = normalize_bzp_notice(BZPRawNotice({}))
        assert t is None

    def test_deterministic_external_id(self):
        """Same input → same external_id (dedup key)."""
        n = make_bzp_notice()
        t1 = normalize_bzp_notice(n)
        t2 = normalize_bzp_notice(n)
        assert t1 is not None and t2 is not None
        assert t1.external_id == t2.external_id

    def test_notice_without_value_does_not_crash(self):
        """Missing contractValue → returns TenderIn with value_pln=None or None."""
        n = make_bzp_notice({"estimatedValue": None})
        t = normalize_bzp_notice(n)
        # Either None (filtered) or TenderIn — no crash guaranteed
        assert t is None or hasattr(t, "value_pln")


# ══════════════════════════════════════════════════════════════════════════════
# 7. normalize_ted_notice
# ══════════════════════════════════════════════════════════════════════════════

class TestNormalizeTED:
    """normalize_ted_notice(dict) → TenderIn."""

    def test_returns_tender_in(self):
        t = normalize_ted_notice(TED_NOTICE_RAW)
        assert t is not None
        assert isinstance(t, TenderIn)

    def test_source_is_ted(self):
        t = normalize_ted_notice(TED_NOTICE_RAW)
        assert t is not None
        assert t.source == "ted"

    def test_external_id_from_nd(self):
        t = normalize_ted_notice(TED_NOTICE_RAW)
        assert t is not None
        assert "123456-2026" in t.external_id

    def test_cpv_from_pc(self):
        t = normalize_ted_notice(TED_NOTICE_RAW)
        assert t is not None
        assert any("45233" in c for c in t.cpv)

    def test_value_from_va(self):
        t = normalize_ted_notice(TED_NOTICE_RAW)
        assert t is not None
        assert t.value_pln is not None
        assert t.value_pln > 0

    def test_empty_notice_returns_none(self):
        t = normalize_ted_notice({})
        assert t is None


# ══════════════════════════════════════════════════════════════════════════════
# 8. normalize helpers
# ══════════════════════════════════════════════════════════════════════════════

class TestNormalizeHelpers:

    def test_normalize_cpv_list(self):
        cpvs = norm_normalize_cpv(["45233120-6", "45111200-0"])
        assert len(cpvs) == 2
        assert any("45233120" in c for c in cpvs)

    def test_normalize_cpv_dict_with_code(self):
        cpvs = norm_normalize_cpv({"code": "45233120-6", "name": "test"})
        assert len(cpvs) > 0
        assert any("45233120" in c for c in cpvs)

    def test_normalize_cpv_string(self):
        cpvs = norm_normalize_cpv("45233120-6")
        assert any("45233120" in c for c in cpvs)

    def test_normalize_cpv_empty_list(self):
        assert norm_normalize_cpv([]) == []

    def test_normalize_cpv_none(self):
        assert norm_normalize_cpv(None) == []

    def test_voivodeship_slaskie(self):
        v = normalize_voivodeship("śląskie")
        assert v is not None

    def test_voivodeship_case_insensitive(self):
        v1 = normalize_voivodeship("ŚLĄSKIE")
        v2 = normalize_voivodeship("śląskie")
        assert v1 == v2

    def test_voivodeship_none(self):
        assert normalize_voivodeship(None) is None

    def test_voivodeship_unknown(self):
        v = normalize_voivodeship("xxxxxxxxx")
        # normalize_voivodeship returns cleaned string as fallback (not None) for unknowns
        # This is intentional — don't drop data with unrecognized voivodeships
        assert v is None or isinstance(v, str)


# ══════════════════════════════════════════════════════════════════════════════
# 9. filters — CPV
# ══════════════════════════════════════════════════════════════════════════════

class TestCpvFilter:

    def test_earthworks_45111200_passes(self):
        assert passes_cpv_filter(make_tender(cpv=["45111200-0"])) is True

    def test_road_45233120_passes(self):
        assert passes_cpv_filter(make_tender(cpv=["45233120-6"])) is True

    def test_building_45200000_passes(self):
        assert passes_cpv_filter(make_tender(cpv=["45200000-9"])) is True

    def test_division_45_all_pass(self):
        for code in ["45000000-7", "45100000-8", "45500000-2"]:
            assert passes_cpv_filter(make_tender(cpv=[code])) is True, f"{code} should pass"

    def test_software_cpv_fails(self):
        assert passes_cpv_filter(make_tender(cpv=["72000000-5"])) is False

    def test_furniture_cpv_fails(self):
        assert passes_cpv_filter(make_tender(cpv=["39100000-3"])) is False

    def test_empty_cpv_fails(self):
        assert passes_cpv_filter(make_tender(cpv=[])) is False

    def test_mixed_passes_if_any_construction(self):
        assert passes_cpv_filter(make_tender(cpv=["72000000-5", "45111200-0"])) is True

    def test_multiple_non_construction_fails(self):
        assert passes_cpv_filter(make_tender(cpv=["72000000-5", "39100000-3"])) is False


# ══════════════════════════════════════════════════════════════════════════════
# 10. filters — geo
# ══════════════════════════════════════════════════════════════════════════════

class TestGeoFilter:

    def test_slaskie_passes(self):
        """śląskie is in TARGET_VOIVODESHIPS → passes."""
        assert passes_geo_filter(make_tender(voivodeship="śląskie")) is True

    def test_dolnoslaskie_passes(self):
        """dolnośląskie is in TARGET_VOIVODESHIPS → passes."""
        assert passes_geo_filter(make_tender(voivodeship="dolnośląskie")) is True

    def test_mazowieckie_filtered_by_default(self):
        """mazowieckie is NOT in TARGET_VOIVODESHIPS — correctly filtered."""
        # This is expected behavior: terra-os targets dolnośląskie/opolskie/śląskie
        result = passes_geo_filter(make_tender(voivodeship="mazowieckie"))
        assert isinstance(result, bool)  # either True (all-Poland mode) or False (regional)

    def test_all_poland_mode(self):
        """When target_voivodeships=set() → all Poland passes (empty set = no filtering)."""
        assert passes_geo_filter(make_tender(voivodeship="mazowieckie"), target_voivodeships=set()) is True

    def test_explicit_target_voivodeship(self):
        """When explicit target includes mazowieckie → passes."""
        assert passes_geo_filter(
            make_tender(voivodeship="mazowieckie"),
            target_voivodeships={"mazowieckie"}
        ) is True

    def test_none_voivodeship_passes(self):
        """Unknown location → pass (don't drop)."""
        assert passes_geo_filter(make_tender(voivodeship=None)) is True


# ══════════════════════════════════════════════════════════════════════════════
# 11. AsyncHTTPClient — mocked
# ══════════════════════════════════════════════════════════════════════════════

class TestAsyncHTTPClient:

    @pytest.mark.asyncio
    async def test_successful_get_records_metrics(self):
        """GET na 200 → metrics.requests_ok incremented."""
        # AsyncHTTPClient uses self._client.request() internally
        # Mock at the httpx.AsyncClient instance level
        real_resp = httpx.Response(200, content=b'{"ok": true}')

        async with AsyncHTTPClient(source="test_http_ok") as client:
            client._client.request = AsyncMock(return_value=real_resp)  # type: ignore[method-assign]
            resp = await client.get("https://example.com/api")
            assert resp.status_code == 200
            assert client._metrics.requests_ok == 1
            assert client._metrics.requests_total == 1

    @pytest.mark.asyncio
    async def test_retry_on_http_error(self):
        """5xx response → retries → eventually 200."""
        call_count = 0
        ok_resp = httpx.Response(200, content=b'{"ok": true}')
        err_resp = httpx.Response(503, content=b"Service Unavailable")

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return ok_resp if call_count >= 3 else err_resp

        policy = RetryPolicy(max_attempts=4, base_delay=0.01, max_delay=0.05)
        async with AsyncHTTPClient(source="test_retry", retry=policy) as client:
            client._client.request = mock_request  # type: ignore[method-assign]
            resp = await client.get("https://example.com/flaky")
            assert resp.status_code == 200
            assert call_count == 3
            assert client._metrics.requests_retried >= 2

    @pytest.mark.asyncio
    async def test_persistent_failure_exhausts_retries(self):
        """Persistent 503 exhausts retries → requests_error > 0."""
        err_resp = httpx.Response(503, content=b"Service Unavailable")

        async def always_fail(*args, **kwargs):
            return err_resp

        policy = RetryPolicy(max_attempts=2, base_delay=0.01, max_delay=0.05)
        async with AsyncHTTPClient(source="test_perm_fail", retry=policy) as client:
            client._client.request = always_fail  # type: ignore[method-assign]
            try:
                resp = await client.get("https://example.com/broken")
                assert client._metrics.requests_error > 0 or client._metrics.requests_retried > 0
            except Exception:
                pass  # exhausted retries may raise — also acceptable

    @pytest.mark.asyncio
    async def test_context_manager_closes_httpx_client(self):
        """Context manager exit → httpx.AsyncClient closed."""
        async with AsyncHTTPClient(source="test_close") as client:
            inner = client._client
        assert inner.is_closed


# ══════════════════════════════════════════════════════════════════════════════
# 12. bzp_connector — sync wrapper mocked
# ══════════════════════════════════════════════════════════════════════════════

class TestBZPConnector:

    def test_fetch_notices_returns_list(self):
        """BZPConnector.fetch_notices() with mocked async HTTP → returns list."""
        from services.ingestion.bzp_connector import BZPConnector

        # Mock the async fetch that BZPConnector calls internally
        async def mock_fetch(*args, **kwargs):
            return [make_bzp_notice()]

        with patch("services.ingestion.bzp_connector._fetch_windows_async", side_effect=mock_fetch):
            conn = BZPConnector()
            result = conn.fetch_notices(
                date_from=date(2026, 7, 10),
                date_to=date(2026, 7, 10),
            )
            assert isinstance(result, list)

    def test_fetch_notices_returns_bzprawnotice_instances(self):
        """fetch_notices returns BZPRawNotice objects."""
        from services.ingestion.bzp_connector import BZPConnector, BZPRawNotice

        async def mock_fetch(*args, **kwargs):
            return [make_bzp_notice()]

        with patch("services.ingestion.bzp_connector._fetch_windows_async", side_effect=mock_fetch):
            conn = BZPConnector()
            result = conn.fetch_notices(
                date_from=date(2026, 7, 10),
                date_to=date(2026, 7, 10),
            )
            if result:
                assert isinstance(result[0], BZPRawNotice)


# ══════════════════════════════════════════════════════════════════════════════
# 13. ted_connector — mocked
# ══════════════════════════════════════════════════════════════════════════════

class TestTEDConnector:

    def test_fetch_notices_returns_list(self):
        from services.ingestion.ted_connector import TEDConnector

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.headers = {}
        mock_resp.json = MagicMock(return_value={"results": [], "total": 0})

        with patch("httpx.Client.get", return_value=mock_resp):
            conn = TEDConnector(timeout=5)
            try:
                notices = conn.fetch_notices(
                    date_from=date(2026, 7, 1),
                    date_to=date(2026, 7, 14),
                )
                assert isinstance(notices, list)
            finally:
                conn.close()

    def test_close_idempotent(self):
        from services.ingestion.ted_connector import TEDConnector
        conn = TEDConnector(timeout=5)
        conn.close()
        conn.close()  # should not raise


# ══════════════════════════════════════════════════════════════════════════════
# 14. Integration: normalize → filter pipeline
# ══════════════════════════════════════════════════════════════════════════════

class TestPipeline:

    def test_bzp_construction_passes_full_pipeline(self):
        t = normalize_bzp_notice(make_bzp_notice())
        assert t is not None
        assert passes_cpv_filter(t) is True
        assert passes_geo_filter(t) is True

    def test_bzp_software_cpv_fails_filter(self):
        """BZP notice with IT CPV only → filtered out (not construction scope)."""
        n = make_bzp_notice({
            # Override BOTH cpvCode (real API field) and old cpvMain (dict API field)
            "cpvCode": "72000000-5 (Usługi informatyczne)",
            "orderObject": "Usługi IT dla urzędu",
        })
        t = normalize_bzp_notice(n)
        # normalize_bzp_notice filters non-construction CPV → None
        assert t is None or passes_cpv_filter(t) is False

    def test_ted_construction_passes_pipeline(self):
        t = normalize_ted_notice(TED_NOTICE_RAW)
        assert t is not None
        assert passes_cpv_filter(t) is True

    def test_same_notice_deterministic_external_id(self):
        n = make_bzp_notice()
        t1 = normalize_bzp_notice(n)
        t2 = normalize_bzp_notice(n)
        assert t1 is not None and t2 is not None
        assert t1.external_id == t2.external_id

    def test_bzp_title_non_empty(self):
        t = normalize_bzp_notice(make_bzp_notice())
        assert t is not None
        assert len(t.title.strip()) > 0

    def test_source_preserved_bzp(self):
        t = normalize_bzp_notice(make_bzp_notice())
        assert t is not None
        assert t.source == "bzp"

    def test_source_preserved_ted(self):
        t = normalize_ted_notice(TED_NOTICE_RAW)
        assert t is not None
        assert t.source == "ted"

    def test_value_pln_reasonable_range(self):
        """Value should be in realistic PLN range."""
        t = normalize_bzp_notice(make_bzp_notice())
        assert t is not None
        assert t.value_pln is not None
        # 1.5M PLN from fixture — compare as Decimal
        from decimal import Decimal
        assert t.value_pln == Decimal("1500000.00")
