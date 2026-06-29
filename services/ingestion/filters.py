"""M1 — CPV + geo filter: drops notices outside scope."""
from __future__ import annotations

from .bzp_connector import _cpv_matches, EARTHWORKS_CPV_PREFIXES
from .normalize import TenderIn

# Target voivodeships for the Dzierżoniów-based firm
# Primary: dolnośląskie + neighbours
TARGET_VOIVODESHIPS: set[str] = {
    "dolnośląskie",
    "opolskie",
    "śląskie",
}

# Optional: all Poland mode (when owner_profile.voivodeships is empty)
ALL_POLAND = False


def passes_cpv_filter(tender: TenderIn) -> bool:
    """Return True if tender CPV codes are in earthworks scope."""
    if not tender.cpv:
        return False
    return _cpv_matches(tender.cpv)


def passes_geo_filter(tender: TenderIn, *, target_voivodeships: set[str] | None = None) -> bool:
    """Return True if tender is in target voivodeship (or all-Poland mode)."""
    target = target_voivodeships or TARGET_VOIVODESHIPS
    if not target:  # empty = all Poland
        return True
    if not tender.voivodeship:
        return True  # unknown location — pass (don't drop)
    return tender.voivodeship.lower() in {v.lower() for v in target}


def passes_value_filter(tender: TenderIn) -> bool:
    """Drop clearly out-of-range contracts (>50 mln = likely too large solo)."""
    if tender.value_pln is None:
        return True  # unknown — pass
    return tender.value_pln <= 50_000_000


def apply_filters(
    tenders: list[TenderIn],
    *,
    voivodeships: set[str] | None = None,
) -> tuple[list[TenderIn], list[TenderIn]]:
    """Return (passed, dropped) lists."""
    passed: list[TenderIn] = []
    dropped: list[TenderIn] = []
    for t in tenders:
        if not passes_cpv_filter(t):
            dropped.append(t)
            continue
        if not passes_geo_filter(t, target_voivodeships=voivodeships):
            dropped.append(t)
            continue
        if not passes_value_filter(t):
            dropped.append(t)
            continue
        passed.append(t)
    return passed, dropped
