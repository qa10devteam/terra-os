"""S127-S129 — In-process metrics store (thread-safe counters/gauges)."""
from __future__ import annotations

from collections import defaultdict
from threading import Lock
from datetime import datetime

_metrics: dict = defaultdict(float)
_lock = Lock()


def increment(key: str, val: float = 1.0):
    with _lock:
        _metrics[key] += val


def gauge(key: str, val: float):
    with _lock:
        _metrics[key] = val


def get_all() -> dict:
    with _lock:
        return dict(_metrics)
