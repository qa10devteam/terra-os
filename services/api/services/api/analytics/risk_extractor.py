"""Faza 30 — NLP Risk Extraction.

Wyciąga ryzyka z treści SWZ używając reguł regex i opcjonalnie Claude AI.
"""
from __future__ import annotations

import json
import os
import re

RED_FLAG_RULES = [
    {
        "pattern": r"kara.*0\.5%.*dzień|0\.5%.*dziennie",
        "msg": "Kara 0.5%/dzień",
        "severity": "high",
    },
    {
        "pattern": r"brak.*waloryzac|bez.*waloryzac",
        "msg": "Brak waloryzacji",
        "severity": "high",
    },
    {
        "pattern": r"ryczałt.*bez.*wyjątk",
        "msg": "Ryczałt bez wyjątków",
        "severity": "high",
    },
    {
        "pattern": r"solidarna.*odpowiedzialn",
        "msg": "Solidarna odpowiedzialność",
        "severity": "medium",
    },
    {
        "pattern": r"kara.*[1-9]\d*%.*dzień",
        "msg": "Wysoka kara umowna dzienna",
        "severity": "high",
    },
    {
        "pattern": r"wadium.*[5-9]\d{4,}|wadium.*\d{6,}",
        "msg": "Wysokie wadium",
        "severity": "medium",
    },
    {
        "pattern": r"gwarancj.*[5-9]\s*lat|gwarancj.*10\s*lat",
        "msg": "Długi okres gwarancji",
        "severity": "medium",
    },
]


def extract_risks_from_text(text: str) -> dict:
    """Wyciąga ryzyka regułami regex (bez AI)."""
    red_flags = []
    for rule in RED_FLAG_RULES:
        if re.search(rule["pattern"], text, re.IGNORECASE):
            red_flags.append({"message": rule["msg"], "severity": rule["severity"]})

    return {
        "red_flags": red_flags,
        "penalties": [],
        "deadlines": [],
        "ai_available": bool(os.getenv("ANTHROPIC_API_KEY")),
        "method": "regex",
    }


def extract_risks_with_ai(text: str) -> dict:
    """Wyciąga ryzyka używając Claude AI (fallback do regex gdy brak klucza)."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return extract_risks_from_text(text)

    try:
        from anthropic import Anthropic  # type: ignore

        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

        prompt = (
            "Analizuj fragment SWZ i zwróć JSON z polami: "
            "penalties (lista kar umownych), deadlines (terminy), "
            "red_flags (klauzule niebezpieczne), payment_terms, warranty_years.\n"
            f"FRAGMENT SWZ:\n{text[:4000]}"
        )
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        result = json.loads(response.content[0].text)
        result["method"] = "ai"
        result["ai_available"] = True
        return result
    except Exception:
        return extract_risks_from_text(text)
