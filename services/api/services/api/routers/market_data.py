"""
Faza 2+4 — Market Data: NBP (kursy walut) + Open-Meteo (pogoda dla budowy).
Wszystkie API bezpłatne, bez klucza, oficjalne.
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/market", tags=["market-data"])

NBP_BASE = "https://api.nbp.pl/api/exchangerates/rates"
WEATHER_BASE = "https://api.open-meteo.com/v1/forecast"

# Główne miasta PL z koordynatami (dla placów budowy)
CITIES_PL = {
    "warszawa":   (52.2297, 21.0122),
    "krakow":     (50.0647, 19.9450),
    "wroclaw":    (51.1079, 17.0385),
    "gdansk":     (54.3520, 18.6466),
    "poznan":     (52.4064, 16.9252),
    "katowice":   (50.2649, 19.0238),
    "lodz":       (51.7592, 19.4560),
    "lublin":     (51.2465, 22.5684),
    "szczecin":   (53.4285, 14.5528),
    "bialystok":  (53.1325, 23.1688),
    "bielsko":    (49.8225, 19.0444),
    "rzeszow":    (50.0412, 21.9991),
    "opole":      (50.6751, 17.9213),
    "zielona":    (51.9356, 15.5062),
    "kielce":     (50.8661, 20.6286),
    "olsztyn":    (53.7784, 20.4801),
    "torun":      (53.0138, 18.5983),
    "bydgoszcz":  (53.1235, 18.0084),
}


# ─── NBP: Kursy walut ─────────────────────────────────────────────────────────

@router.get("/currencies")
def get_currencies():
    """
    Aktualne kursy walut z NBP (Tabela A — kursy średnie).
    Używane do kalibracji kosztorysów: materiały EUR/USD → PLN.
    """
    try:
        r = httpx.get(f"{NBP_BASE}/a/eur/?format=json", timeout=10)
        eur = r.json()["rates"][0] if r.status_code == 200 else None

        r2 = httpx.get(f"{NBP_BASE}/a/usd/?format=json", timeout=10)
        usd = r2.json()["rates"][0] if r2.status_code == 200 else None

        r3 = httpx.get(f"{NBP_BASE}/a/chf/?format=json", timeout=10)
        chf = r3.json()["rates"][0] if r3.status_code == 200 else None
    except Exception as e:
        raise HTTPException(502, f"NBP API niedostępne: {e}")

    return {
        "source": "NBP (Narodowy Bank Polski)",
        "table": "A",
        "effective_date": eur["effectiveDate"] if eur else None,
        "rates": {
            "EUR": {"mid": eur["mid"] if eur else None, "name": "Euro"},
            "USD": {"mid": usd["mid"] if usd else None, "name": "Dolar USA"},
            "CHF": {"mid": chf["mid"] if chf else None, "name": "Frank szwajcarski"},
        },
        "note": "Kursy średnie NBP — do przeliczania materiałów importowanych i indeksacji kontraktów.",
    }


@router.get("/currencies/{code}/history")
def get_currency_history(code: str, days: int = Query(30, le=93)):
    """
    Historia kursu waluty z ostatnich N dni (max 93).
    Np. GET /market/currencies/eur/history?days=30
    """
    code = code.lower()
    now = datetime.now(timezone.utc)
    date_from = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    date_to = now.strftime("%Y-%m-%d")

    try:
        r = httpx.get(
            f"{NBP_BASE}/a/{code}/{date_from}/{date_to}/?format=json",
            timeout=15,
        )
        if r.status_code == 404:
            raise HTTPException(404, f"Waluta {code.upper()} nie znaleziona w tabeli NBP A")
        r.raise_for_status()
        data = r.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"NBP API error: {e}")

    rates = data.get("rates", [])
    return {
        "code": data.get("code", code.upper()),
        "currency": data.get("currency", ""),
        "source": "NBP Tabela A",
        "from": date_from,
        "to": date_to,
        "count": len(rates),
        "rates": [{"date": r["effectiveDate"], "mid": r["mid"]} for r in rates],
        "min": min(r["mid"] for r in rates) if rates else None,
        "max": max(r["mid"] for r in rates) if rates else None,
        "avg": round(sum(r["mid"] for r in rates) / len(rates), 4) if rates else None,
    }


@router.get("/currencies/table/all")
def get_all_currencies():
    """Cała Tabela A NBP — wszystkie waluty (do wyboru w kosztorysie)."""
    try:
        r = httpx.get("https://api.nbp.pl/api/exchangerates/tables/a/?format=json", timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise HTTPException(502, f"NBP API error: {e}")

    table = data[0] if isinstance(data, list) else data
    return {
        "effective_date": table.get("effectiveDate"),
        "no": table.get("no"),
        "rates": [
            {"code": r["code"], "currency": r["currency"], "mid": r["mid"]}
            for r in table.get("rates", [])
        ],
    }


# ─── Open-Meteo: Pogoda dla placów budowy ────────────────────────────────────

@router.get("/weather/forecast")
def get_weather_forecast(
    lat: float = Query(..., description="Szerokość geograficzna"),
    lon: float = Query(..., description="Długość geograficzna"),
    days: int = Query(14, le=16, description="Liczba dni prognozy (max 16)"),
):
    """
    Prognoza pogody dla placu budowy (lat/lon).
    Zwraca dane istotne dla robót: opady, temperatura gruntu, wiatr, śnieg.
    Darmowe, bez klucza API — Open-Meteo.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "forecast_days": days,
        "timezone": "Europe/Warsaw",
        "daily": ",".join([
            "temperature_2m_max", "temperature_2m_min",
            "precipitation_sum", "snowfall_sum",
            "wind_speed_10m_max", "wind_gusts_10m_max",
            "weather_code", "precipitation_probability_max",
        ]),
        "hourly": "soil_temperature_0cm,freezing_level_height",
    }
    try:
        r = httpx.get(WEATHER_BASE, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise HTTPException(502, f"Open-Meteo niedostępne: {e}")

    daily = data.get("daily", {})
    dates = daily.get("time", [])

    # Oblicz ryzyko dla placu budowy
    days_list = []
    for i, date in enumerate(dates):
        precip = (daily.get("precipitation_sum") or [])[i] if i < len(daily.get("precipitation_sum") or []) else 0
        snow = (daily.get("snowfall_sum") or [])[i] if i < len(daily.get("snowfall_sum") or []) else 0
        wind = (daily.get("wind_speed_10m_max") or [])[i] if i < len(daily.get("wind_speed_10m_max") or []) else 0
        tmin = (daily.get("temperature_2m_min") or [])[i] if i < len(daily.get("temperature_2m_min") or []) else 99

        # Ryzyko robót: wysoki = stop, średni = utrudnienia, niski = OK
        risk = "niski"
        risk_reasons = []
        if (precip or 0) > 20:
            risk = "wysoki"
            risk_reasons.append(f"intensywne opady {precip}mm")
        if (snow or 0) > 5:
            risk = "wysoki"
            risk_reasons.append(f"opady śniegu {snow}cm")
        if (wind or 0) > 60:
            risk = "wysoki"
            risk_reasons.append(f"silny wiatr {wind}km/h")
        if (tmin or 99) < 0 and risk != "wysoki":
            risk = "średni"
            risk_reasons.append(f"temp. poniżej 0°C (mróz {tmin}°C)")
        if 10 <= (precip or 0) <= 20 and risk == "niski":
            risk = "średni"
            risk_reasons.append(f"opady {precip}mm")

        days_list.append({
            "date": date,
            "temp_min": tmin,
            "temp_max": (daily.get("temperature_2m_max") or [])[i] if i < len(daily.get("temperature_2m_max") or []) else None,
            "precipitation_mm": precip,
            "snowfall_cm": snow,
            "wind_max_kmh": wind,
            "wind_gusts_kmh": (daily.get("wind_gusts_10m_max") or [])[i] if i < len(daily.get("wind_gusts_10m_max") or []) else None,
            "precip_probability_pct": (daily.get("precipitation_probability_max") or [])[i] if i < len(daily.get("precipitation_probability_max") or []) else None,
            "construction_risk": risk,
            "risk_reasons": risk_reasons,
        })

    high_risk_days = sum(1 for d in days_list if d["construction_risk"] == "wysoki")
    medium_risk_days = sum(1 for d in days_list if d["construction_risk"] == "średni")

    return {
        "lat": lat,
        "lon": lon,
        "timezone": "Europe/Warsaw",
        "source": "Open-Meteo (ERA5)",
        "forecast_days": len(days_list),
        "summary": {
            "high_risk_days": high_risk_days,
            "medium_risk_days": medium_risk_days,
            "low_risk_days": len(days_list) - high_risk_days - medium_risk_days,
            "overall_risk": "wysoki" if high_risk_days > 3 else "średni" if high_risk_days > 0 or medium_risk_days > 5 else "niski",
        },
        "forecast": days_list,
    }


@router.get("/weather/city/{city}")
def get_weather_by_city(city: str, days: int = Query(14, le=16)):
    """
    Prognoza pogody dla polskiego miasta (nazwa po polsku bez ogonków).
    Np. GET /market/weather/city/wroclaw
    """
    city_key = city.lower().replace("ó", "o").replace("ą", "a").replace("ę", "e").replace("ź", "z")
    coords = CITIES_PL.get(city_key)
    if not coords:
        available = list(CITIES_PL.keys())
        raise HTTPException(404, f"Miasto '{city}' nieznane. Dostępne: {available}")

    lat, lon = coords
    return get_weather_forecast(lat=lat, lon=lon, days=days)


@router.get("/weather/history")
def get_weather_history(
    lat: float,
    lon: float,
    start_date: str = Query(..., description="Format: YYYY-MM-DD"),
    end_date: str = Query(..., description="Format: YYYY-MM-DD"),
):
    """
    Historia pogody dla lokalizacji (od 1940 — ERA5).
    Używane do oceny ryzyka sezonowego i walidacji harmonogramów.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "Europe/Warsaw",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,snowfall_sum,wind_speed_10m_max",
    }
    try:
        r = httpx.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params=params, timeout=20,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise HTTPException(502, f"Open-Meteo archive error: {e}")

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    return {
        "lat": lat, "lon": lon,
        "period": {"from": start_date, "to": end_date},
        "source": "Open-Meteo Archive (ERA5)",
        "days_count": len(dates),
        "history": [
            {
                "date": dates[i],
                "temp_max": (daily.get("temperature_2m_max") or [])[i] if i < len(daily.get("temperature_2m_max") or []) else None,
                "temp_min": (daily.get("temperature_2m_min") or [])[i] if i < len(daily.get("temperature_2m_min") or []) else None,
                "precipitation_mm": (daily.get("precipitation_sum") or [])[i] if i < len(daily.get("precipitation_sum") or []) else None,
                "snowfall_cm": (daily.get("snowfall_sum") or [])[i] if i < len(daily.get("snowfall_sum") or []) else None,
                "wind_max_kmh": (daily.get("wind_speed_10m_max") or [])[i] if i < len(daily.get("wind_speed_10m_max") or []) else None,
            }
            for i in range(len(dates))
        ],
    }
