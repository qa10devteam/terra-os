"""Shared pytest configuration for terra-os test suite."""
from __future__ import annotations

import sys
import os

# Project root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add all necessary paths at collection time (before any test imports)
for path in [
    ROOT,
    os.path.join(ROOT, "packages", "vendor"),
    os.path.join(ROOT, "packages", "shared"),
    os.path.join(ROOT, "packages", "db"),
    os.path.join(ROOT, "services", "api"),
    os.path.join(ROOT, "services", "estimator"),
]:
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("TERRA_OFFLINE", "1")
os.environ.setdefault("ENVIRONMENT", "dev")
