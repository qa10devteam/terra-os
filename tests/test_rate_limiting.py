"""A: Rate Limiting QA — tests for Redis sliding-window middleware.

Fires 110 requests to GET /api/v2/health via ASGI transport (in-process)
with TESTING=0 so the rate-limiter middleware is active.

Verifies:
- First 100 requests → 200 OK
- Requests 101–110 → 429 Too Many Requests
- X-RateLimit-Limit / Remaining / Reset headers on both 200 and 429
- 429 body contains JSON with 'error' field
- Retry-After header on 429
"""
from __future__ import annotations

import anyio
import os
import time
import pytest
import redis as _redis_mod
from httpx import ASGITransport, AsyncClient

TOTAL = 110
GENERAL_LIMIT = 100


def _clear_rate_keys() -> None:
    r = _redis_mod.Redis(host="localhost", port=6379, db=1, decode_responses=True)
    for key in r.keys("rate:*:general"):
        r.delete(key)


async def _collect_responses(app):
    """Fire TOTAL async GET requests and return list of responses."""
    results = []
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        for _ in range(TOTAL):
            resp = await c.get("/api/v2/health")
            results.append(resp)
    return results


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def responses():
    """Collect all 110 responses with rate limiting active."""
    _clear_rate_keys()

    old_testing = os.environ.get("TESTING")
    os.environ["TESTING"] = "0"

    try:
        from services.api.services.api.main import app
        results = anyio.from_thread.run_sync(
            lambda: anyio.run(_collect_responses, app)
        )
    except RuntimeError:
        # We're not inside an anyio thread — just run directly
        import asyncio
        from services.api.services.api.main import app
        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(_collect_responses(app))
        finally:
            loop.close()
    finally:
        if old_testing is None:
            os.environ.pop("TESTING", None)
        else:
            os.environ["TESTING"] = old_testing

    return results


# ---------------------------------------------------------------------------
# Test: first GENERAL_LIMIT requests return 200
# ---------------------------------------------------------------------------

def test_first_100_return_200(responses):
    """The first 100 requests should all be 200 OK."""
    first_100 = responses[:GENERAL_LIMIT]
    failing = [(i, r.status_code) for i, r in enumerate(first_100) if r.status_code != 200]
    assert not failing, f"Non-200 in first 100: {failing[:5]}"


def test_requests_after_limit_return_429(responses):
    """Requests 101+ should receive 429."""
    over_limit = responses[GENERAL_LIMIT:]
    assert over_limit
    for i, resp in enumerate(over_limit, start=GENERAL_LIMIT + 1):
        assert resp.status_code == 429, (
            f"Request #{i}: expected 429, got {resp.status_code}. Body: {resp.text}"
        )


# ---------------------------------------------------------------------------
# Test: X-RateLimit-* headers on 200
# ---------------------------------------------------------------------------

def test_x_ratelimit_limit_header_on_200(responses):
    ok_r = [r for r in responses if r.status_code == 200]
    assert ok_r
    for resp in ok_r:
        assert "x-ratelimit-limit" in resp.headers, (
            f"Missing X-RateLimit-Limit. Headers: {dict(resp.headers)}"
        )
        assert resp.headers["x-ratelimit-limit"] == str(GENERAL_LIMIT)


def test_x_ratelimit_remaining_header_on_200(responses):
    ok_r = [r for r in responses if r.status_code == 200]
    assert ok_r
    for resp in ok_r:
        assert "x-ratelimit-remaining" in resp.headers
        assert int(resp.headers["x-ratelimit-remaining"]) >= 0


def test_x_ratelimit_reset_header_on_200(responses):
    ok_r = [r for r in responses if r.status_code == 200]
    assert ok_r
    now = time.time()
    for resp in ok_r:
        assert "x-ratelimit-reset" in resp.headers
        reset = int(resp.headers["x-ratelimit-reset"])
        assert reset > now - 120, f"X-RateLimit-Reset {reset} looks stale"


# ---------------------------------------------------------------------------
# Test: X-RateLimit-* headers on 429
# ---------------------------------------------------------------------------

def test_x_ratelimit_headers_on_429(responses):
    throttled = [r for r in responses if r.status_code == 429]
    assert throttled, "No 429 responses found"
    for resp in throttled:
        assert "x-ratelimit-limit" in resp.headers, (
            f"Missing X-RateLimit-Limit on 429. Headers: {dict(resp.headers)}"
        )
        assert resp.headers["x-ratelimit-limit"] == str(GENERAL_LIMIT)
        assert "x-ratelimit-remaining" in resp.headers
        assert resp.headers["x-ratelimit-remaining"] == "0"
        assert "x-ratelimit-reset" in resp.headers


# ---------------------------------------------------------------------------
# Test: 429 body has 'error' field
# ---------------------------------------------------------------------------

def test_429_body_is_json_with_error_field(responses):
    throttled = [r for r in responses if r.status_code == 429]
    assert throttled
    for resp in throttled:
        ct = resp.headers.get("content-type", "")
        assert "application/json" in ct, f"Expected JSON, got {ct}"
        body = resp.json()
        assert "error" in body, f"Expected 'error' field, got: {body}"
        assert isinstance(body["error"], str)
        assert len(body["error"]) > 0


# ---------------------------------------------------------------------------
# Test: Retry-After header
# ---------------------------------------------------------------------------

def test_429_retry_after_header(responses):
    throttled = [r for r in responses if r.status_code == 429]
    assert throttled
    for resp in throttled:
        assert "retry-after" in resp.headers, (
            f"Missing Retry-After. Headers: {dict(resp.headers)}"
        )


# ---------------------------------------------------------------------------
# Test: remaining decrements
# ---------------------------------------------------------------------------

def test_remaining_decrements(responses):
    ok_r = [r for r in responses if r.status_code == 200]
    remainders = [int(r.headers["x-ratelimit-remaining"]) for r in ok_r]
    if len(remainders) > 1:
        assert remainders[0] >= remainders[-1], (
            f"Expected remaining to decrease: {remainders[0]} → {remainders[-1]}"
        )


# ---------------------------------------------------------------------------
# Test: summary counts
# ---------------------------------------------------------------------------

def test_summary_counts(responses):
    assert len(responses) == TOTAL
    ok_count = sum(1 for r in responses if r.status_code == 200)
    err_count = sum(1 for r in responses if r.status_code == 429)
    assert ok_count == GENERAL_LIMIT, f"Expected {GENERAL_LIMIT} OK, got {ok_count}"
    assert err_count == TOTAL - GENERAL_LIMIT, (
        f"Expected {TOTAL - GENERAL_LIMIT} throttled, got {err_count}"
    )
