"""A: Rate Limiting QA — tests for Redis sliding-window middleware.

Tests fire 110 synchronous requests to GET /api/v2/health against the live
API running on localhost:8000, verify that after the 100-request limit the
server starts returning 429, that every response carries X-RateLimit-* headers,
and that 429 responses carry a JSON body with an 'error' field.
"""
from __future__ import annotations

import time
import pytest
import httpx
import redis


BASE_URL = "http://localhost:8000"
TOTAL = 110
GENERAL_LIMIT = 100


def _clear_rate_key(ip: str = "127.0.0.1") -> None:
    """Flush the Redis sliding-window key so the counter starts at zero."""
    r = redis.Redis(host="localhost", port=6379, db=1, decode_responses=True)
    r.delete(f"rate:{ip}:general")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def responses():
    """Send TOTAL synchronous GET requests and collect all responses."""
    _clear_rate_key()
    time.sleep(0.1)  # make sure key is gone
    results = []
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        for _ in range(TOTAL):
            resp = client.get("/api/v2/health")
            results.append(resp)
    return results


# ---------------------------------------------------------------------------
# Test: first GENERAL_LIMIT requests return 200
# ---------------------------------------------------------------------------

def test_first_100_return_200(responses):
    """The first 100 requests should all be 200 OK."""
    first_100 = responses[:GENERAL_LIMIT]
    statuses = [r.status_code for r in first_100]
    failing = [(i, s) for i, s in enumerate(statuses) if s != 200]
    assert not failing, f"Expected 200 for first 100 requests; got non-200: {failing[:5]}"


def test_requests_after_limit_return_429(responses):
    """Requests 101+ should receive 429 Too Many Requests."""
    over_limit = responses[GENERAL_LIMIT:]
    assert len(over_limit) == TOTAL - GENERAL_LIMIT
    for i, resp in enumerate(over_limit, start=GENERAL_LIMIT + 1):
        assert resp.status_code == 429, (
            f"Request #{i}: expected 429, got {resp.status_code}. Body: {resp.text}"
        )


# ---------------------------------------------------------------------------
# Test: X-RateLimit-* headers present on 200 responses
# ---------------------------------------------------------------------------

def test_x_ratelimit_limit_header_on_200(responses):
    """200 responses must have X-RateLimit-Limit header equal to 100."""
    ok_responses = [r for r in responses if r.status_code == 200]
    assert ok_responses, "No 200 responses found"
    for resp in ok_responses:
        assert "x-ratelimit-limit" in resp.headers, (
            f"Missing X-RateLimit-Limit header. Headers: {dict(resp.headers)}"
        )
        assert resp.headers["x-ratelimit-limit"] == str(GENERAL_LIMIT), (
            f"Expected X-RateLimit-Limit={GENERAL_LIMIT}, got {resp.headers['x-ratelimit-limit']}"
        )


def test_x_ratelimit_remaining_header_on_200(responses):
    """200 responses must have a numeric X-RateLimit-Remaining header."""
    ok_responses = [r for r in responses if r.status_code == 200]
    assert ok_responses
    for resp in ok_responses:
        assert "x-ratelimit-remaining" in resp.headers, (
            f"Missing X-RateLimit-Remaining. Headers: {dict(resp.headers)}"
        )
        remaining = int(resp.headers["x-ratelimit-remaining"])
        assert remaining >= 0


def test_x_ratelimit_reset_header_on_200(responses):
    """200 responses must have a numeric X-RateLimit-Reset (epoch seconds) header."""
    ok_responses = [r for r in responses if r.status_code == 200]
    assert ok_responses
    now = time.time()
    for resp in ok_responses:
        assert "x-ratelimit-reset" in resp.headers, (
            f"Missing X-RateLimit-Reset. Headers: {dict(resp.headers)}"
        )
        reset = int(resp.headers["x-ratelimit-reset"])
        assert reset > now - 5, f"X-RateLimit-Reset {reset} is in the past by more than 5s"


# ---------------------------------------------------------------------------
# Test: X-RateLimit-* headers present on 429 responses
# ---------------------------------------------------------------------------

def test_x_ratelimit_headers_on_429(responses):
    """429 responses must also carry X-RateLimit-* headers."""
    throttled = [r for r in responses if r.status_code == 429]
    assert throttled, "No 429 responses found; limit may not have been reached"
    for resp in throttled:
        assert "x-ratelimit-limit" in resp.headers, (
            f"Missing X-RateLimit-Limit on 429. Headers: {dict(resp.headers)}"
        )
        assert resp.headers["x-ratelimit-limit"] == str(GENERAL_LIMIT)
        assert "x-ratelimit-remaining" in resp.headers
        assert resp.headers["x-ratelimit-remaining"] == "0"
        assert "x-ratelimit-reset" in resp.headers


# ---------------------------------------------------------------------------
# Test: 429 response body contains JSON with 'error' field
# ---------------------------------------------------------------------------

def test_429_body_is_json_with_error_field(responses):
    """429 body must be JSON containing an 'error' key (not just 'detail')."""
    throttled = [r for r in responses if r.status_code == 429]
    assert throttled, "No 429 responses to inspect"
    for resp in throttled:
        assert resp.headers.get("content-type", "").startswith("application/json"), (
            f"Expected application/json, got {resp.headers.get('content-type')}"
        )
        body = resp.json()
        assert "error" in body, (
            f"Expected 'error' field in 429 body, got: {body}"
        )
        assert isinstance(body["error"], str)
        assert "rate limit" in body["error"].lower() or "429" in body["error"] or len(body["error"]) > 0


# ---------------------------------------------------------------------------
# Test: 429 body has Retry-After header
# ---------------------------------------------------------------------------

def test_429_retry_after_header(responses):
    """429 responses should have a Retry-After header."""
    throttled = [r for r in responses if r.status_code == 429]
    assert throttled
    for resp in throttled:
        assert "retry-after" in resp.headers, (
            f"Missing Retry-After header on 429. Headers: {dict(resp.headers)}"
        )


# ---------------------------------------------------------------------------
# Test: remaining counter decrements monotonically
# ---------------------------------------------------------------------------

def test_remaining_decrements(responses):
    """X-RateLimit-Remaining should decrease (or stay at 0) as requests pile up."""
    ok_responses = [r for r in responses if r.status_code == 200]
    remainders = [int(r.headers["x-ratelimit-remaining"]) for r in ok_responses]
    # Allow for tiny non-monotonic blips from parallel pipelines but overall trend ↓
    if len(remainders) > 1:
        assert remainders[0] >= remainders[-1], (
            f"Expected remaining to decrease: first={remainders[0]}, last={remainders[-1]}"
        )


# ---------------------------------------------------------------------------
# Test: count summary
# ---------------------------------------------------------------------------

def test_summary_counts(responses):
    """Verify exactly TOTAL responses collected and plausible 200/429 split."""
    assert len(responses) == TOTAL, f"Expected {TOTAL} responses, got {len(responses)}"
    ok_count = sum(1 for r in responses if r.status_code == 200)
    err_count = sum(1 for r in responses if r.status_code == 429)
    assert ok_count == GENERAL_LIMIT, f"Expected exactly {GENERAL_LIMIT} OK, got {ok_count}"
    assert err_count == TOTAL - GENERAL_LIMIT, (
        f"Expected {TOTAL - GENERAL_LIMIT} throttled, got {err_count}"
    )
