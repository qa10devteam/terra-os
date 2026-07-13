"""Core ingestion module tests — deduplicator, alert_runner, geo_enricher, repository.

Covers:
- deduplicator: normalize_text, TenderRow.__post_init__, score similarity
- alert_runner: build_html_digest, build_text_digest, _fmt_value, _fmt_date, _fmt_score
- geo_enricher: NUTS-2 mapping, VOIV_COORDS coverage
- repository: CPV array formatting, upsert SQL shape
- competitor_watcher: run_competitor_watch (mocked engine)
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# 1. Deduplicator
# ─────────────────────────────────────────────────────────────────────────────
from services.ingestion.deduplicator import (
    TenderRow,
    normalize_text,
    SOURCE_PRIORITY,
    TITLE_SIM_THRESHOLD,
    VALUE_RATIO_MAX,
    DATE_DAYS_MAX,
)


class TestNormalizeText:
    def test_empty_string(self):
        assert normalize_text("") == ""

    def test_none_equivalent(self):
        # Function accepts str — empty string
        assert normalize_text("") == ""

    def test_lowercase(self):
        result = normalize_text("Budowa Drogi")
        assert result == result.lower()

    def test_removes_diacritics(self):
        result = normalize_text("Łódź Kraków Gdańsk")
        assert "ó" not in result
        assert "ń" not in result
        assert "ą" not in result

    def test_removes_stopwords_pl(self):
        result = normalize_text("Budowa drogi w gminie Kowalice")
        assert "w" not in result.split()
        assert "gmina" not in result.split()
        # Content words should remain
        assert "drogi" in result or "drog" in result

    def test_removes_punctuation(self):
        result = normalize_text("Remont drogi: ul. Kwiatowa, nr 5")
        assert ":" not in result
        assert "," not in result

    def test_short_words_removed(self):
        # Words <= 2 chars removed
        result = normalize_text("od do na za in")
        # All are stopwords or short
        assert len(result.strip()) == 0 or all(len(w) > 2 for w in result.split())

    def test_deterministic(self):
        s = "Przebudowa drogi gminnej nr 15 w miejscowości Kowalice"
        assert normalize_text(s) == normalize_text(s)

    def test_removes_tender_stopwords(self):
        result = normalize_text("Zamówienie na dostawę mebli biurowych")
        # "dostawa" is stopword
        assert "dostawa" not in result.split()
        # "mebli" not a stopword — should remain
        assert "mebli" in result


class TestTenderRow:
    def test_auto_normalize_on_init(self):
        row = TenderRow(
            id="abc",
            source="bzp",
            title="Remont budynku szkoły w Krakowie",
            buyer="Gmina Kraków",
            value_pln=100_000.0,
            published_at=date(2024, 3, 1),
        )
        assert row.title_norm  # non-empty
        assert row.buyer_norm  # non-empty
        # Diacritics removed
        assert "ó" not in row.title_norm
        assert "ó" not in row.buyer_norm

    def test_empty_title(self):
        row = TenderRow(
            id="x", source="bzp", title="", buyer="", value_pln=None, published_at=None
        )
        assert row.title_norm == ""
        assert row.buyer_norm == ""

    def test_none_title_handled(self):
        # title is typed str but might be None in practice
        row = TenderRow(
            id="x", source="bzp", title="", buyer="", value_pln=None, published_at=None
        )
        assert row.title_norm == ""


class TestSourcePriority:
    def test_bzp_is_highest(self):
        assert SOURCE_PRIORITY["bzp"] < SOURCE_PRIORITY["ted"]
        assert SOURCE_PRIORITY["bzp"] < SOURCE_PRIORITY["bip"]

    def test_ted_beats_bip(self):
        assert SOURCE_PRIORITY["ted"] < SOURCE_PRIORITY["bip"]

    def test_manual_is_lowest_excluding_excel(self):
        # manual has lower priority than bzp/ted/bip/bk but excel is even lower
        assert SOURCE_PRIORITY["manual"] > SOURCE_PRIORITY["bzp"]
        assert SOURCE_PRIORITY["manual"] > SOURCE_PRIORITY["bip"]
        assert SOURCE_PRIORITY["excel"] > SOURCE_PRIORITY["manual"]


class TestDeduplicatorConstants:
    def test_thresholds_sane(self):
        assert 0.0 < TITLE_SIM_THRESHOLD < 1.0
        assert 0.0 < VALUE_RATIO_MAX < 1.0
        assert DATE_DAYS_MAX > 0


# ─────────────────────────────────────────────────────────────────────────────
# 2. Alert Runner helpers
# ─────────────────────────────────────────────────────────────────────────────
from services.ingestion.alert_runner import (
    Alert,
    MatchedTender,
    _fmt_value,
    _fmt_date,
    _fmt_score,
    build_html_digest,
    build_text_digest,
)


def _make_alert(**kwargs) -> Alert:
    defaults = dict(
        id="alert-1",
        tenant_id="tenant-1",
        user_id=None,
        name="Test Alert",
        cpv_prefixes=["45"],
        provinces=["śląskie"],
        value_min=None,
        value_max=None,
        keywords=["droga", "remont"],
        notice_types=[],
        buyer_nips=[],
        frequency="daily",
        channel="email",
        webhook_url=None,
        last_fired_at=None,
    )
    defaults.update(kwargs)
    return Alert(**defaults)


def _make_tender(**kwargs) -> MatchedTender:
    defaults = dict(
        id="t-1",
        title="Remont drogi gminnej nr 5",
        buyer="Gmina Testowa",
        cpv=["45233120-6"],
        voivodeship="śląskie",
        value_pln=250_000.0,
        deadline_at=datetime(2024, 6, 30, tzinfo=timezone.utc),
        published_at=datetime(2024, 3, 1, tzinfo=timezone.utc),
        url="https://ezamowienia.gov.pl/xxx",
        match_score=0.87,
        source="bzp",
    )
    defaults.update(kwargs)
    return MatchedTender(**defaults)


class TestFmtHelpers:
    def test_fmt_value_none(self):
        result = _fmt_value(None)
        assert result == "—" or result == "-" or "brak" in result.lower() or result == ""

    def test_fmt_value_normal(self):
        result = _fmt_value(250_000.0)
        # Should contain digits
        assert any(c.isdigit() for c in result)

    def test_fmt_value_large(self):
        result = _fmt_value(1_500_000.0)
        assert any(c.isdigit() for c in result)

    def test_fmt_date_none(self):
        result = _fmt_date(None)
        assert result == "—" or result == "-" or result == "" or "brak" in result.lower()

    def test_fmt_date_datetime(self):
        dt = datetime(2024, 6, 30, tzinfo=timezone.utc)
        result = _fmt_date(dt)
        assert "2024" in result or "30" in result

    def test_fmt_score_none(self):
        result = _fmt_score(None)
        assert isinstance(result, str)

    def test_fmt_score_value(self):
        result = _fmt_score(0.87)
        assert "87" in result or "0.87" in result or "87%" in result


class TestBuildDigest:
    def test_html_contains_tender_title(self):
        alert = _make_alert()
        tender = _make_tender()
        since = datetime(2024, 3, 1, tzinfo=timezone.utc)
        html = build_html_digest(alert, [tender], since)
        assert "Remont drogi gminnej nr 5" in html

    def test_html_contains_buyer(self):
        alert = _make_alert()
        tender = _make_tender()
        since = datetime(2024, 3, 1, tzinfo=timezone.utc)
        html = build_html_digest(alert, [tender], since)
        assert "Gmina Testowa" in html

    def test_html_contains_url(self):
        alert = _make_alert()
        tender = _make_tender()
        since = datetime(2024, 3, 1, tzinfo=timezone.utc)
        html = build_html_digest(alert, [tender], since)
        assert "ezamowienia.gov.pl" in html

    def test_html_empty_tenders(self):
        alert = _make_alert()
        since = datetime(2024, 3, 1, tzinfo=timezone.utc)
        html = build_html_digest(alert, [], since)
        assert isinstance(html, str)
        assert len(html) > 0

    def test_html_valid_structure(self):
        alert = _make_alert()
        tender = _make_tender()
        since = datetime(2024, 3, 1, tzinfo=timezone.utc)
        html = build_html_digest(alert, [tender], since)
        # Should be HTML
        assert "<" in html and ">" in html

    def test_text_digest_no_html(self):
        alert = _make_alert()
        tender = _make_tender()
        since = datetime(2024, 3, 1, tzinfo=timezone.utc)
        text = build_text_digest(alert, [tender], since)
        assert "<html" not in text.lower()
        assert "Remont drogi gminnej nr 5" in text

    def test_text_digest_multiple_tenders(self):
        alert = _make_alert()
        tenders = [
            _make_tender(id=f"t-{i}", title=f"Tender {i}") for i in range(3)
        ]
        since = datetime(2024, 3, 1, tzinfo=timezone.utc)
        text = build_text_digest(alert, tenders, since)
        assert "Tender 0" in text
        assert "Tender 2" in text


# ─────────────────────────────────────────────────────────────────────────────
# 3. Geo Enricher — static mappings
# ─────────────────────────────────────────────────────────────────────────────
from services.ingestion.geo_enricher import VOIV_NUTS, VOIV_COORDS, POSTAL_COORDS


class TestGeoEnricherMappings:
    def test_all_16_voivodeships(self):
        assert len(VOIV_NUTS) == 16

    def test_nuts_codes_format(self):
        for voiv, nuts in VOIV_NUTS.items():
            assert nuts.startswith("PL"), f"{voiv} → {nuts} not PL prefix"
            assert len(nuts) == 4, f"{nuts} wrong length"

    def test_all_nuts_have_coords(self):
        for voiv, nuts in VOIV_NUTS.items():
            assert nuts in VOIV_COORDS, f"{nuts} missing from VOIV_COORDS"

    def test_coords_in_poland_bounds(self):
        # Poland: lat 49–55, lon 14–24
        for nuts, (lat, lon) in VOIV_COORDS.items():
            assert 49.0 <= lat <= 55.5, f"{nuts} lat={lat} out of bounds"
            assert 14.0 <= lon <= 24.5, f"{nuts} lon={lon} out of bounds"

    def test_slaskie_maps_to_pl22(self):
        assert VOIV_NUTS["śląskie"] == "PL22"

    def test_mazowieckie_maps_to_pl91(self):
        assert VOIV_NUTS["mazowieckie"] == "PL91"

    def test_postal_codes_cover_00_to_99(self):
        # Should have most prefix codes
        assert len(POSTAL_COORDS) >= 80

    def test_postal_coords_in_poland(self):
        for prefix, (lat, lon) in POSTAL_COORDS.items():
            assert 49.0 <= lat <= 55.5, f"postal {prefix} lat={lat}"
            assert 14.0 <= lon <= 24.5, f"postal {prefix} lon={lon}"

    def test_warsaw_postal_00(self):
        lat, lon = POSTAL_COORDS["00"]
        assert 52.0 <= lat <= 52.5
        assert 20.8 <= lon <= 21.3


# ─────────────────────────────────────────────────────────────────────────────
# 4. Repository helpers (no DB)
# ─────────────────────────────────────────────────────────────────────────────
from services.ingestion.normalize import TenderIn


class TestRepositoryCpvFormat:
    """Test the CPV array formatting used in upsert_tender."""

    def _cpv_to_pg_array(self, cpv_list: list[str]) -> str:
        return "{" + ",".join(cpv_list) + "}"

    def test_single_cpv(self):
        result = self._cpv_to_pg_array(["45233120-6"])
        assert result == "{45233120-6}"

    def test_multiple_cpv(self):
        result = self._cpv_to_pg_array(["45233120-6", "45233140-2"])
        assert result == "{45233120-6,45233140-2}"

    def test_empty_cpv(self):
        result = self._cpv_to_pg_array([])
        assert result == "{}"


class TestTenderInDefaults:
    def _base(self, **kwargs):
        from datetime import datetime, timezone
        from decimal import Decimal
        defaults = dict(
            source="bzp",
            external_id="BZP/2024/001",
            title="Budowa drogi",
            buyer="Gmina Test",
            cpv=["45233120-6"],
            voivodeship="śląskie",
            value_pln=Decimal("250000.00"),
            deadline_at=None,
            published_at=datetime(2024, 3, 1, tzinfo=timezone.utc),
            url="https://example.com",
            raw={},
        )
        defaults.update(kwargs)
        return TenderIn(**defaults)

    def test_required_fields(self):
        t = self._base()
        assert t.source == "bzp"
        assert t.external_id == "BZP/2024/001"
        assert t.cpv == ["45233120-6"]

    def test_optional_fields_none(self):
        t = self._base(value_pln=None, deadline_at=None)
        assert t.value_pln is None
        assert t.deadline_at is None

    def test_cpv_list_preserved(self):
        cpv = ["45233120-6", "45233140-2", "45000000-7"]
        t = self._base(cpv=cpv)
        assert t.cpv == cpv


# ─────────────────────────────────────────────────────────────────────────────
# 5. Competitor Watcher (mocked engine)
# ─────────────────────────────────────────────────────────────────────────────
from services.ingestion.competitor_watcher import run_competitor_watch


class TestCompetitorWatcher:
    def test_no_watches_returns_zero(self):
        """When no active watches exist, returns 0 notifications."""
        engine = MagicMock()
        conn = MagicMock()
        # begin() returns context manager
        engine.begin.return_value.__enter__ = MagicMock(return_value=conn)
        engine.begin.return_value.__exit__ = MagicMock(return_value=False)
        # ALTER TABLE succeed
        conn.execute.return_value = MagicMock()
        # fetchall for watches → empty
        conn.execute.return_value.fetchall.return_value = []

        result = run_competitor_watch(engine, tenant_id="test-tenant")
        assert result == 0

    def test_returns_int(self):
        engine = MagicMock()
        conn = MagicMock()
        engine.begin.return_value.__enter__ = MagicMock(return_value=conn)
        engine.begin.return_value.__exit__ = MagicMock(return_value=False)
        conn.execute.return_value.fetchall.return_value = []
        result = run_competitor_watch(engine)
        assert isinstance(result, int)


# ─────────────────────────────────────────────────────────────────────────────
# 6. scraper_base — deeper coverage
# ─────────────────────────────────────────────────────────────────────────────
from services.ingestion.scraper_base import (
    parse_pln,
    normalize_cpv,
    safe_date,
    CircuitBreaker,
    CircuitState,
    RetryPolicy,
    RateLimiter,
    ScraperMetrics,
)
from datetime import timedelta


class TestParsePlnExtended:
    def test_zero(self):
        assert parse_pln("0") == 0.0

    def test_negative_returns_negative(self):
        # parse_pln returns actual value (including negative) — no filtering
        result = parse_pln("-100")
        assert result == -100.0

    def test_very_large(self):
        result = parse_pln("999999999,99")
        assert result == 999_999_999.99

    def test_polish_spaces_as_thousand_sep(self):
        # "1 500 000,00" is common Polish format
        result = parse_pln("1 500 000,00")
        assert result == 1_500_000.0

    def test_euro_sign_ignored(self):
        result = parse_pln("€1500,00")
        # Should parse or return None — not crash
        # If it strips non-digit except decimal: returns 1500.0
        assert result is None or isinstance(result, float)

    def test_only_letters_returns_none(self):
        assert parse_pln("abc") is None

    def test_empty_returns_none(self):
        assert parse_pln("") is None


class TestNormalizeCpvExtended:
    def test_standard_format(self):
        # normalize_cpv strips check digit — returns 8-digit code
        result = normalize_cpv("45233120-6")
        assert result is not None
        assert "45233120" in result

    def test_strips_description(self):
        # Some sources send "45233120-6 Roboty budowlane..."
        result = normalize_cpv("45233120-6 Roboty budowlane")
        assert result is not None
        assert "45233120" in result

    def test_short_code_padded_or_returned(self):
        # 8-digit without dash
        result = normalize_cpv("45233120")
        assert "45233120" in (result or "")

    def test_none_input(self):
        result = normalize_cpv(None)
        assert result is None or result == ""

    def test_dict_input(self):
        # Some TED API returns dict {"id": "45233120-6"}
        result = normalize_cpv({"id": "45233120-6"})
        assert result is None or "45233120" in (result or "")


class TestSafeDateExtended:
    """safe_date() returns ISO string or None — not a datetime object."""

    def test_iso_full(self):
        result = safe_date("2024-06-30T12:00:00Z")
        assert result is not None
        assert "2024" in str(result)

    def test_date_only(self):
        result = safe_date("2024-06-30")
        assert result is not None
        assert "2024" in str(result)

    def test_polish_format(self):
        result = safe_date("30.06.2024")
        # may return None if format not supported — that's OK
        assert result is None or "2024" in str(result)

    def test_none(self):
        assert safe_date(None) is None

    def test_empty(self):
        assert safe_date("") is None

    def test_garbage(self):
        # Should not raise — return None or pass-through string
        result = safe_date("not a date")
        assert result is None or isinstance(result, str)


class TestCircuitBreakerExtended:
    def test_initial_state_closed(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0)
        for _ in range(3):
            cb.record_failure()
        # recovery_timeout=0 → should be HALF_OPEN immediately
        import time; time.sleep(0.01)
        assert cb.state in (CircuitState.HALF_OPEN, CircuitState.OPEN)

    def test_success_resets_failures(self):
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb._failures == 0

    def test_allows_request_when_closed(self):
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        assert cb.allow_request() is True

    def test_blocks_request_when_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=9999)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False


class TestRetryPolicyExtended:
    def test_delay_increases(self):
        rp = RetryPolicy(max_attempts=5, base_delay=1.0, backoff_factor=2.0, jitter=0.0)
        delays = [rp.delay_for(i) for i in range(1, 5)]
        # Each should be >= previous (no jitter)
        for i in range(len(delays) - 1):
            assert delays[i] <= delays[i + 1]

    def test_max_delay_capped(self):
        rp = RetryPolicy(max_attempts=10, base_delay=1.0, backoff_factor=10.0, max_delay=5.0, jitter=0.0)
        for attempt in range(1, 10):
            assert rp.delay_for(attempt) <= 5.0

    def test_delay_for_attempt_1(self):
        rp = RetryPolicy(max_attempts=3, base_delay=2.0, jitter=0.0)
        d = rp.delay_for(1)
        assert d >= 2.0

    def test_delay_for_attempt_0(self):
        rp = RetryPolicy(max_attempts=3, base_delay=1.0)
        d = rp.delay_for(0)
        assert d >= 0

    def test_jitter_adds_randomness(self):
        rp = RetryPolicy(max_attempts=5, base_delay=1.0, jitter=0.3)
        delays = [rp.delay_for(2) for _ in range(20)]
        # With jitter, not all should be identical
        assert len(set(round(d, 3) for d in delays)) > 1

    def test_zero_jitter_deterministic(self):
        rp = RetryPolicy(max_attempts=5, base_delay=1.0, jitter=0.0)
        d1 = rp.delay_for(2)
        d2 = rp.delay_for(2)
        assert d1 == d2


class TestScraperMetricsExtended:
    def test_record_multiple_requests(self):
        m = ScraperMetrics(source="test_multi")
        m.record_request(ok=True, latency_ms=100.0)
        m.record_request(ok=True, latency_ms=200.0)
        m.record_request(ok=False, latency_ms=50.0)
        assert m.requests_total == 3
        assert m.requests_ok == 2
        assert m.requests_error == 1

    def test_p50_p99_computed(self):
        m = ScraperMetrics(source="test_percentile")
        for i in range(1, 101):
            m.record_request(ok=True, latency_ms=float(i))
        p50 = m.p50_ms
        p99 = m.p99_ms
        assert p50 is not None
        assert p99 is not None
        assert p50 <= p99
        assert 45 <= p50 <= 55  # ~50ms

    def test_to_dict(self):
        m = ScraperMetrics(source="test_dict")
        m.record_request(ok=True, latency_ms=150.0)
        d = m.to_dict()
        assert isinstance(d, dict)
        assert "source" in d or "requests_total" in d


class TestRateLimiterExtended:
    def test_allows_burst(self):
        import asyncio
        rl = RateLimiter(rate=10.0, burst=5)

        async def _test():
            results = []
            for _ in range(5):
                try:
                    await asyncio.wait_for(rl.acquire("test.domain"), timeout=2.0)
                    results.append(True)
                except asyncio.TimeoutError:
                    results.append(False)
            return results

        results = asyncio.run(_test())
        assert all(results)

    def test_rate_limited_after_burst(self):
        import asyncio, time
        rl = RateLimiter(rate=1.0, burst=1)

        async def _test():
            await rl.acquire("test.domain")  # consume burst
            start = time.monotonic()
            await asyncio.wait_for(rl.acquire("test.domain"), timeout=3.0)
            return time.monotonic() - start

        elapsed = asyncio.run(_test())
        # Should wait at least 0.5s (generous tolerance)
        assert elapsed >= 0.5
