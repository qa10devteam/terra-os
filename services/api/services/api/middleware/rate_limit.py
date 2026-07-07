"""Faza 63 — Rate limiting via slowapi.

Rules:
  - 100 req/min per IP  (general)
  - 10 req/min per IP   for /api/v2/auth/* (brute-force protection)
"""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")

from slowapi import Limiter
from slowapi.util import get_remote_address

# Global limiter instance — imported in main.py
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri="memory://",
)
