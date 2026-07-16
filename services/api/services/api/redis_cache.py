"""Redis-backed distributed cache layer for Terra-OS API.

Provides a Redis cache that falls back gracefully to the in-process cache
when Redis is unavailable. Used for:
  - intelligence summary endpoints (TTL 5min)
  - analytics dashboard (TTL 2min)
  - icb suggest / search (TTL 10min)

Usage:
    from services.api.redis_cache import rcache_get, rcache_set, redis_cache

    # Decorator style:
    @redis_cache(ttl=300, key_prefix="intel_summary")
    def get_intelligence_summary(tenant_id: str) -> dict:
        ...

    # Manual style:
    data = rcache_get("mykey")
    rcache_set("mykey", data, ttl=120)
"""
from __future__ import annotations

import functools
import json
import logging
import os
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ─── TTL Constants ─────────────────────────────────────────────────────────────
TTL_INTELLIGENCE_SUMMARY = 300   # 5 min
TTL_ANALYTICS_DASHBOARD  = 120   # 2 min
TTL_ICB_SUGGEST          = 600   # 10 min
TTL_TENDER_STATS         = 120   # 2 min
TTL_DASHBOARD_STATS      = 60    # 1 min (existing)

# ─── Redis Client (lazy singleton) ─────────────────────────────────────────────

_redis_client = None
_redis_lock = threading.Lock()
_redis_available = None  # None = not tested yet


def _get_redis():
    """Return Redis client, or None if unavailable."""
    global _redis_client, _redis_available

    if _redis_available is False:
        return None

    if _redis_client is not None:
        return _redis_client

    with _redis_lock:
        if _redis_client is not None:
            return _redis_client

        try:
            import redis

            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))
            db = int(os.getenv("REDIS_DB", "0"))
            password = os.getenv("REDIS_PASSWORD", None)

            client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=True,
            )
            # Test connection
            client.ping()
            _redis_client = client
            _redis_available = True
            logger.info("Redis cache connected: %s:%d db=%d", host, port, db)
            return _redis_client
        except Exception as e:
            _redis_available = False
            logger.warning("Redis unavailable, falling back to in-process cache: %s", e)
            return None


def rcache_get(key: str) -> Any | None:
    """Get value from Redis cache. Returns None on miss or error."""
    r = _get_redis()
    if r is None:
        # Fallback to in-process cache
        from . import cache as _c
        return _c.get(key)

    try:
        raw = r.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.debug("Redis GET error for key %s: %s", key, e)
        return None


def rcache_set(key: str, value: Any, ttl: int = 60) -> None:
    """Set value in Redis cache with TTL. Falls back silently on error."""
    r = _get_redis()
    if r is None:
        # Fallback to in-process cache
        from . import cache as _c
        _c.set(key, value, ttl=ttl)
        return

    try:
        serialized = json.dumps(value, default=str)
        r.setex(key, ttl, serialized)
    except Exception as e:
        logger.debug("Redis SET error for key %s: %s", key, e)
        # Also set in-process cache as backup
        try:
            from . import cache as _c
            _c.set(key, value, ttl=ttl)
        except Exception:
            pass


def rcache_delete(key: str) -> None:
    """Delete a key from Redis cache."""
    r = _get_redis()
    if r is None:
        from . import cache as _c
        _c.invalidate(prefix=key)
        return

    try:
        r.delete(key)
    except Exception as e:
        logger.debug("Redis DEL error for key %s: %s", key, e)


def rcache_invalidate_prefix(prefix: str) -> int:
    """Delete all keys starting with prefix. Returns count deleted."""
    r = _get_redis()

    # Always invalidate in-process cache too
    try:
        from . import cache as _c
        _c.invalidate(prefix=prefix)
    except Exception:
        pass

    if r is None:
        return 0

    try:
        keys = list(r.scan_iter(f"{prefix}*"))
        if keys:
            return r.delete(*keys)
        return 0
    except Exception as e:
        logger.debug("Redis SCAN/DEL error for prefix %s: %s", prefix, e)
        return 0


def redis_cache(ttl: int = 60, key_prefix: str = "", key_fn: Callable | None = None):
    """Decorator: cache function result in Redis (with in-process fallback).

    Args:
        ttl:        Cache TTL in seconds.
        key_prefix: Prefix added to cache key.
        key_fn:     Callable(*args, **kwargs) → str key suffix.
                    Default: uses first positional arg (tenant_id or similar).
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if key_fn:
                suffix = key_fn(*args, **kwargs)
            elif args:
                suffix = str(args[0])
            else:
                suffix = json.dumps(sorted(kwargs.items()), default=str)

            cache_key = f"{key_prefix or func.__name__}:{suffix}"

            cached = rcache_get(cache_key)
            if cached is not None:
                logger.debug("Redis cache HIT: %s", cache_key)
                return cached

            result = func(*args, **kwargs)
            rcache_set(cache_key, result, ttl=ttl)
            logger.debug("Redis cache SET: %s (ttl=%ds)", cache_key, ttl)
            return result

        return wrapper
    return decorator


def get_redis_status() -> dict:
    """Return Redis connection status for health checks."""
    r = _get_redis()
    if r is None:
        return {"redis": "unavailable", "fallback": "in-process"}
    try:
        info = r.info("server")
        return {
            "redis": "connected",
            "version": info.get("redis_version"),
            "used_memory_human": info.get("used_memory_human"),
        }
    except Exception as e:
        return {"redis": "error", "detail": str(e)}
