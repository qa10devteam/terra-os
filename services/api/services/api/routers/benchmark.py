"""Faza 26 — Atlas Przetargów benchmark + Faza 27 — Competitor Intelligence.

GET /api/v2/benchmark/{cpv}?region=PL91&period=2y
GET /api/v2/competitors/{nip}/profile
GET /api/v2/competitors/search?cpv=45000000&region=PL91
"""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")

import random
import hashlib
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel

from ..auth.deps import get_current_user

router = APIRouter(prefix="/api/v2", tags=["benchmark"])

# ── Seed-stable helpers ─────────────────────────────────────────────────────────

def _seed(s: str) -> int:
    return int(hashlib.md5(s.encode()).hexdigest(), 16) % (2**31)

CPV_NAMES = {
    "45000000": "Roboty budowlane",
    "45200000": "Roboty budowlane: obiekty",
    "45210000": "Roboty budowlane: budynki",
    "45230000": "Roboty: infrastruktura",
    "45310000": "Roboty: instalacje elektryczne",
    "45330000": "Roboty: hydrauliczne",
    "71000000": "Usługi architektoniczne",
}

REGIONS = {
    "PL91": "mazowieckie", "PL22": "śląskie", "PL63": "pomorskie",
    "PL21": "małopolskie", "PL41": "wielkopolskie", "PL51": "dolnośląskie",
}

COMPETITORS = [
    {"name": "Budimex SA",      "nip": "1234567890", "avg_value": 12_300_000, "win_rate": 0.28},
    {"name": "Strabag Sp. z o.o.", "nip": "2345678901", "avg_value": 8_500_000, "win_rate": 0.31},
    {"name": "Porr SA",         "nip": "3456789012", "avg_value": 6_200_000, "win_rate": 0.24},
    {"name": "Skanska SA",      "nip": "4567890123", "avg_value": 15_000_000, "win_rate": 0.22},
    {"name": "Erbud SA",        "nip": "5678901234", "avg_value": 3_800_000, "win_rate": 0.35},
    {"name": "Unibep SA",       "nip": "6789012345", "avg_value": 4_100_000, "win_rate": 0.29},
    {"name": "Mota-Engil",      "nip": "7890123456", "avg_value": 9_700_000, "win_rate": 0.26},
    {"name": "Hochtief Polska", "nip": "8901234567", "avg_value": 18_000_000, "win_rate": 0.19},
]


# ── Faza 26 — Benchmark ─────────────────────────────────────────────────────────

@router.get("/benchmark/{cpv}")
def get_benchmark(
    cpv: str,
    region: str = Query(default="PL91", description="Kod NUTS regionu"),
    period: str = Query(default="2y", description="Okres: 1y/2y/5y"),
    _user=Depends(get_current_user),
):
    """Benchmark historycznych wartości przetargów dla CPV × region.
    
    Dane syntetyczne — w produkcji zastąpić danymi z Atlas Przetargów (1.4M rekordów BZP).
    """
    rng = random.Random(_seed(f"{cpv}{region}{period}"))
    
    base_value = rng.randint(800_000, 8_000_000)
    n_tenders  = rng.randint(12, 340)
    
    # Quarterly data
    periods_map = {"1y": 4, "2y": 8, "5y": 20}
    n_quarters  = periods_map.get(period, 8)
    
    quarterly = []
    v = base_value
    for q in range(n_quarters):
        v = v * (1 + rng.uniform(-0.03, 0.06))
        quarterly.append({
            "quarter": f"Q{(q % 4)+1}/{2024 - (n_quarters - q) // 4}",
            "avg_value": round(v),
            "n_tenders": rng.randint(3, 30),
            "avg_n_bidders": round(rng.uniform(2.5, 7.5), 1),
        })
    
    cpv_2 = cpv[:2]
    price_per_m2_range = {
        "45": (2500, 5500),
        "71": (80, 350),
    }.get(cpv_2, (1000, 4000))
    
    similar_projects = [
        {
            "bzp_number": f"2024/{rng.randint(10000,99999)}/N",
            "value_contract": round(base_value * rng.uniform(0.7, 1.4)),
            "n_bidders": rng.randint(2, 9),
            "region": region,
            "date": f"2024-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}",
        }
        for _ in range(5)
    ]
    
    return {
        "cpv": cpv,
        "cpv_name": CPV_NAMES.get(cpv, f"CPV {cpv}"),
        "region": region,
        "region_name": REGIONS.get(region, region),
        "period": period,
        "n_tenders_analyzed": n_tenders,
        "avg_value": round(base_value),
        "median_value": round(base_value * rng.uniform(0.85, 0.95)),
        "p10_value": round(base_value * 0.4),
        "p90_value": round(base_value * 1.8),
        "avg_n_bidders": round(rng.uniform(3.0, 6.5), 1),
        "avg_price_per_m2": round(rng.uniform(*price_per_m2_range)),
        "yoy_change_pct": round(rng.uniform(-2, 12), 1),
        "quarterly_trend": quarterly,
        "similar_projects": similar_projects,
        "data_source": "Atlas Przetargów BZP (synthetic — replace with 1.4M record dataset)",
        "last_updated": "2024-12-01",
    }


# ── Faza 27 — Competitor Intelligence ──────────────────────────────────────────

@router.get("/competitors/{nip}/profile")
def get_competitor_profile(
    nip: str,
    _user=Depends(get_current_user),
):
    """Profil konkurenta na podstawie historycznych przetargów BZP."""
    comp = next((c for c in COMPETITORS if c["nip"] == nip), None)
    if not comp:
        # Generate synthetic profile for any NIP
        rng = random.Random(_seed(nip))
        comp = {
            "name": f"Firma Budowlana {nip[-4:]}",
            "nip": nip,
            "avg_value": rng.randint(500_000, 20_000_000),
            "win_rate": round(rng.uniform(0.15, 0.45), 2),
        }
    
    rng = random.Random(_seed(nip + "profile"))
    
    regions_raw = {k: round(rng.uniform(0.05, 0.40), 2) for k in list(REGIONS.keys())[:4]}
    total = sum(regions_raw.values())
    regions = {k: round(v / total, 2) for k, v in regions_raw.items()}
    
    cpv_codes = random.Random(_seed(nip)).sample(list(CPV_NAMES.keys()), k=3)
    
    won = rng.randint(20, 900)
    total_tenders = round(won / comp["win_rate"])
    
    return {
        "nip": nip,
        "name": comp["name"],
        "won_tenders": won,
        "total_tenders": total_tenders,
        "win_rate": comp["win_rate"],
        "avg_value": comp["avg_value"],
        "total_won_value": won * comp["avg_value"],
        "regions": regions,
        "cpv_codes": cpv_codes,
        "avg_n_competitors_when_won": round(rng.uniform(3.0, 7.5), 1),
        "avg_markup_vs_second": round(rng.uniform(-0.08, -0.01), 3),
        "active_since": f"20{rng.randint(5,18):02d}",
        "last_won": f"2024-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}",
        "data_source": "BZP historical data (synthetic)",
    }


@router.get("/competitors/search")
def search_competitors(
    cpv: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    _user=Depends(get_current_user),
):
    """Wyszukaj konkurentów aktywnych w segmencie CPV × region."""
    rng = random.Random(_seed(f"{cpv}{region}"))
    
    n = min(limit, len(COMPETITORS))
    selected = rng.sample(COMPETITORS, n)
    
    results = []
    for c in selected:
        r = random.Random(_seed(c["nip"] + str(cpv)))
        results.append({
            **c,
            "cpv_match": cpv is not None,
            "region_match": region is not None,
            "recent_activity": r.randint(1, 15),  # tenders in last 12 months
            "estimated_n_competitors": r.randint(3, 9),
        })
    
    results.sort(key=lambda x: x["win_rate"], reverse=True)
    
    return {
        "cpv": cpv,
        "region": region,
        "total": len(results),
        "competitors": results,
    }
