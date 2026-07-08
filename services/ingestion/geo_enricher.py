"""Geo enricher — uzupełnia NUTS-2, latitude, longitude w tabeli tender.

Mapuje:
- voivodeship (text) → NUTS-2 code
- postal code prefix (pierwsze 2 cyfry) → przybliżone coords centrum
- TED: place-of-performance-post-code-part z raw_data

CLI:
    python3 geo_enricher.py [--limit 5000] [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
from typing import Any

from sqlalchemy import text
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

# NUTS-2 mapping: voivodeship → NUTS code
VOIV_NUTS: dict[str, str] = {
    "dolnośląskie":          "PL51",
    "kujawsko-pomorskie":    "PL61",
    "lubelskie":             "PL81",
    "lubuskie":              "PL43",
    "łódzkie":               "PL71",
    "małopolskie":           "PL21",
    "mazowieckie":           "PL91",
    "opolskie":              "PL52",
    "podkarpackie":          "PL82",
    "podlaskie":             "PL84",
    "pomorskie":             "PL63",
    "śląskie":               "PL22",
    "świętokrzyskie":        "PL72",
    "warmińsko-mazurskie":   "PL62",
    "wielkopolskie":         "PL41",
    "zachodniopomorskie":    "PL42",
}

# Centrum każdego województwa (lat, lon) — do fallback gdy brak postal code
VOIV_COORDS: dict[str, tuple[float, float]] = {
    "PL51": (51.10, 17.03),   # Wrocław
    "PL61": (53.12, 18.01),   # Bydgoszcz
    "PL81": (51.25, 22.57),   # Lublin
    "PL43": (51.93, 15.51),   # Zielona Góra
    "PL71": (51.77, 19.46),   # Łódź
    "PL21": (50.06, 19.94),   # Kraków
    "PL91": (52.23, 21.01),   # Warszawa
    "PL52": (50.67, 17.93),   # Opole
    "PL82": (50.04, 22.00),   # Rzeszów
    "PL84": (53.13, 23.16),   # Białystok
    "PL63": (54.35, 18.65),   # Gdańsk
    "PL22": (50.26, 19.02),   # Katowice
    "PL72": (50.87, 20.63),   # Kielce
    "PL62": (53.78, 20.49),   # Olsztyn
    "PL41": (52.41, 16.93),   # Poznań
    "PL42": (53.43, 14.55),   # Szczecin
}

# Kody pocztowe prefix (00-99) → przybliżone coords
# Uproszczona mapa, wystarczająca do ~50km dokładności
POSTAL_COORDS: dict[str, tuple[float, float]] = {
    "00": (52.23, 21.01), "01": (52.23, 21.01), "02": (52.18, 21.00),
    "03": (52.25, 21.08), "04": (52.19, 21.00), "05": (52.10, 21.15),
    "06": (52.70, 21.00), "07": (52.85, 21.50), "08": (52.55, 21.80),
    "09": (52.55, 20.50), "10": (53.78, 20.49), "11": (53.95, 20.90),
    "12": (53.60, 20.80), "13": (53.45, 20.25), "14": (53.40, 19.70),
    "15": (53.13, 23.16), "16": (53.30, 23.50), "17": (52.80, 22.80),
    "18": (53.10, 22.10), "19": (53.65, 22.80), "20": (51.25, 22.57),
    "21": (51.10, 22.90), "22": (51.25, 23.10), "23": (51.05, 23.30),
    "24": (51.40, 21.97), "25": (50.87, 20.63), "26": (51.00, 20.90),
    "27": (50.72, 21.45), "28": (50.47, 20.72), "29": (50.68, 21.10),
    "30": (50.06, 19.94), "31": (50.07, 19.98), "32": (50.13, 19.70),
    "33": (49.98, 20.62), "34": (49.76, 19.76), "35": (50.04, 22.00),
    "36": (50.25, 22.25), "37": (50.13, 22.70), "38": (49.68, 22.00),
    "39": (50.05, 21.90), "40": (50.26, 19.02), "41": (50.30, 18.80),
    "42": (50.48, 18.95), "43": (49.82, 18.96), "44": (50.30, 18.60),
    "45": (50.67, 17.93), "46": (50.72, 17.60), "47": (50.43, 17.97),
    "48": (50.10, 17.60), "49": (50.53, 17.35), "50": (51.10, 17.03),
    "51": (51.14, 17.05), "52": (51.17, 16.95), "53": (51.08, 17.05),
    "54": (51.14, 17.00), "55": (51.00, 17.40), "56": (51.43, 17.50),
    "57": (50.72, 16.55), "58": (50.52, 16.18), "59": (51.30, 16.40),
    "60": (52.41, 16.93), "61": (52.41, 16.93), "62": (52.20, 17.20),
    "63": (52.12, 17.60), "64": (52.13, 16.55), "65": (51.93, 15.51),
    "66": (52.25, 15.55), "67": (51.52, 15.85), "68": (51.63, 15.10),
    "69": (52.73, 14.73), "70": (53.43, 14.55), "71": (53.43, 14.55),
    "72": (53.75, 14.80), "73": (53.30, 14.60), "74": (53.55, 15.80),
    "75": (54.20, 16.20), "76": (54.19, 15.57), "77": (53.90, 16.70),
    "78": (53.50, 16.18), "79": (53.20, 16.00), "80": (54.35, 18.65),
    "81": (54.52, 18.53), "82": (53.87, 18.20), "83": (53.97, 18.85),
    "84": (54.20, 18.60), "85": (53.12, 18.01), "86": (53.35, 18.20),
    "87": (53.01, 18.61), "88": (52.75, 18.08), "89": (53.72, 17.62),
    "90": (51.77, 19.46), "91": (51.79, 19.42), "92": (51.74, 19.50),
    "93": (51.72, 19.46), "94": (51.78, 19.38), "95": (51.95, 19.80),
    "96": (52.12, 20.30), "97": (51.40, 19.60), "98": (51.50, 19.80),
    "99": (51.90, 19.10),
}


def _nuts_from_voiv(voiv: str | None) -> str | None:
    if not voiv:
        return None
    v = voiv.lower().strip()
    return VOIV_NUTS.get(v)


def _coords_from_postal(postal: str | None) -> tuple[float, float] | None:
    if not postal:
        return None
    prefix = str(postal).replace("-", "").strip()[:2]
    return POSTAL_COORDS.get(prefix)


def _extract_postal_from_raw(raw: Any) -> str | None:
    """Wyciąga kod pocztowy z raw_data TED."""
    if not raw or not isinstance(raw, dict):
        return None
    for key in ("place-of-performance-post-code-part", "placeofperformancepostcode",
                "postal-code", "postalcode"):
        val = raw.get(key)
        if val:
            if isinstance(val, list) and val:
                val = val[0]
            return str(val).strip()
    return None


def enrich_batch(limit: int = 5000, dry_run: bool = False) -> dict:
    engine = get_engine()
    updated = 0
    skipped = 0

    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT id, source, voivodeship, raw
            FROM tender
            WHERE nuts_code IS NULL OR latitude IS NULL
            LIMIT :lim
        """), {"lim": limit}).fetchall()

        for row in rows:
            tid, source, voiv, raw_data = row

            nuts = _nuts_from_voiv(voiv)
            lat, lon = None, None

            # Try postal code first (more accurate)
            postal = None
            if source in ("ted", "bip") and raw_data:
                postal = _extract_postal_from_raw(raw_data)

            if postal:
                coords = _coords_from_postal(postal)
                if coords:
                    lat, lon = coords

            # Fallback to voivodeship centroid
            if (lat is None or lon is None) and nuts:
                coords = VOIV_COORDS.get(nuts)
                if coords:
                    lat, lon = coords

            if not nuts and not lat:
                skipped += 1
                continue

            if not dry_run:
                conn.execute(text("""
                    UPDATE tender
                    SET nuts_code = :nuts, latitude = :lat, longitude = :lon
                    WHERE id = :id
                """), {"nuts": nuts, "lat": lat, "lon": lon, "id": str(tid)})
            updated += 1

    logger.info(f"Geo enrichment: updated={updated}, skipped={skipped} {'(dry-run)' if dry_run else ''}")
    return {"updated": updated, "skipped": skipped}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Geo enricher for tender table")
    ap.add_argument("--limit", type=int, default=5000)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    result = enrich_batch(limit=args.limit, dry_run=args.dry_run)
    print(f"Done: {result}")
