"""S125-S126 — Data Quality service helper."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def completeness_score(total: int, no_cpv: int, no_value: int, no_deadline: int) -> float:
    """Return completeness score as percentage 0-100."""
    if total == 0:
        return 100.0
    incomplete = max(no_cpv, no_value, no_deadline)
    return round((total - incomplete) / total * 100, 1)


def field_coverage(with_field: int, total: int) -> float:
    if total == 0:
        return 100.0
    return round(with_field / total * 100, 1)
