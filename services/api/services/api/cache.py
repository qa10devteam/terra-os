"""Shared in-process TTL cache for API layer.

Thread-safe, no external deps. Used by analytics, stats, dashboard endpoints
to avoid repeated heavy SQL queries.

Usage:
    from services.api.cache import api_cache

    @api_cache(ttl=60, key_fn=lambda user, **_: f"dashboard:{user.org_id}")
    def my_handler(user: AuthUser) -> dict:
        ...  # only runs on cache miss
"""
from __future__ import annotations

import functools
import logging
import threading
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_STORE: dict[str, tuple[float, Any]] = {}  # key → (expires_at, value)


def get(key: str) -> Any:
    """Return cached value or None if missing/expired."""
    with _LOCK:
        entry = _STORE.get(key)
        if entry and time.monotonic() < entry[0]:
            return entry[1]
    return None


def set(key: str, value: Any, ttl: int = 60) -> None:
    """Store value with TTL seconds."""
    with _LOCK:
        _STORE[key] = (time.monotonic() + ttl, value)


def invalidate(prefix: str | None = None) -> int:
    """Invalidate all keys (or keys starting with prefix). Returns count removed."""
    with _LOCK:
        if prefix:
            keys = [k for k in _STORE if k.startswith(prefix)]
        else:
            keys = list(_STORE.keys())
        for k in keys:
            del _STORE[k]
    logger.debug("API cache invalidated: %d entries (prefix=%s)", len(keys), prefix)
    return len(keys)


def api_cache(ttl: int = 60, key_fn: Callable[..., str] | None = None):
    """Decorator: cache function result by key derived from args.

    Args:
        ttl:    Cache TTL in seconds (default 60).
        key_fn: Callable(*args, **kwargs) → str. Default: f"{func.__name__}:{str(args)}"
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = key_fn(*args, **kwargs) if key_fn else f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            cached = get(cache_key)
            if cached is not None:
                logger.debug("Cache HIT: %s", cache_key)
                return cached
            result = func(*args, **kwargs)
            set(cache_key, result, ttl=ttl)
            logger.debug("Cache SET: %s (ttl=%ds)", cache_key, ttl)
            return result
        return wrapper
    return decorator


# ──────────────────────────────────────────────────────────────────────────────
# S86/S87 — Extended cache helpers for tenders and search
# ──────────────────────────────────────────────────────────────────────────────

def get_tender(tender_id: str) -> Any:
    """S86 — Get cached tender by ID."""
    return get(f"tender:{tender_id}")


def set_tender(tender_id: str, data: dict, ttl: int = 120) -> None:
    """S86 — Cache tender data with 120s TTL."""
    set(f"tender:{tender_id}", data, ttl)


def get_search(params_hash: str) -> Any:
    """S87 — Get cached search results by params hash."""
    return get(f"search:{params_hash}")


def set_search(params_hash: str, data: list, ttl: int = 30) -> None:
    """S87 — Cache search results with 30s TTL."""
    set(f"search:{params_hash}", data, ttl)


def invalidate_tenant(tenant_id: str) -> int:
    """S87 — Invalidate all cached keys containing tenant_id (e.g. after ingest)."""
    prefix = str(tenant_id)
    with _LOCK:
        keys = [k for k in _STORE if prefix in k]
        for k in keys:
            _STORE.pop(k, None)
    logger.debug("Cache invalidate_tenant: %d entries removed (tenant=%s)", len(keys), tenant_id)
    return len(keys)
