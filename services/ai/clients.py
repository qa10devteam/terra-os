"""LLM Client protocol + StubClient for CI (zero-network)."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Generator, Protocol

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    """Protocol for LLM clients (OllamaClient, BedrockClient, StubClient)."""

    def generate(self, prompt: str, *, system: str = "", json_mode: bool = False) -> str:
        ...

    def generate_stream(
        self, prompt: str, *, system: str = "", max_tokens: int = 4096
    ) -> Generator[str, None, None]:
        ...

    def embed(self, text: str) -> list[float]:
        ...


class StubClient:
    """Deterministic stub for CI — returns canned responses per task type.

    Used when TERRA_OFFLINE=1 or in tests. Ensures zero network calls.
    """

    def __init__(self) -> None:
        self._call_count = 0

    def generate(self, prompt: str, *, system: str = "", json_mode: bool = False) -> str:
        self._call_count += 1
        prompt_lower = prompt.lower()
        system_lower = system.lower()

        if "classify" in system_lower or "dokument" in prompt_lower:
            return json.dumps({"kind": "przedmiar", "confidence": 0.85})

        if "red_flag" in system_lower or "klauzul" in prompt_lower or "ryzyko" in prompt_lower:
            return json.dumps({
                "red_flags": [
                    {
                        "severity": "high",
                        "category": "kary_umowne",
                        "message": "Kara umowna 0.5%/dzień przekracza bezpieczny próg 0.3%/dzień",
                        "provenance": {"doc_id": "doc-001", "page": 12, "line": "§14 ust. 2"},
                        "confidence": 0.9,
                    }
                ]
            })

        if "summary" in system_lower or "podsumow" in prompt_lower:
            return json.dumps({
                "summary_md": (
                    "## Podsumowanie przetargu\n\nPrzetarg na roboty ziemne i drogowe. "
                    "Wartość szacunkowa: 850 000 PLN. Termin: 90 dni od podpisania umowy. "
                    "Wymagane doświadczenie: min. 2 roboty o wartości >500 000 PLN w ostatnich 5 lat."
                ),
                "key_facts": {
                    "value_pln": 850000,
                    "deadline_days": 90,
                    "experience_required": "2 roboty >500k PLN / 5 lat",
                },
            })

        if "przedmiar" in prompt_lower or "pozycj" in prompt_lower:
            return json.dumps({
                "items": [
                    {
                        "position_no": "1.1",
                        "description": "Wykopy mechaniczne w gruncie kat. III",
                        "unit": "m3",
                        "quantity": 1250.0,
                        "knr_code": "KNR 2-01 0211-03",
                        "page": 3,
                        "confidence": 0.92,
                    },
                    {
                        "position_no": "1.2",
                        "description": "Nasypy z gruntu kat. II z zagęszczeniem",
                        "unit": "m3",
                        "quantity": 800.0,
                        "knr_code": "KNR 2-01 0307-02",
                        "page": 3,
                        "confidence": 0.88,
                    },
                    {
                        "position_no": "1.3",
                        "description": "Transport urobku na odległość do 5 km",
                        "unit": "m3",
                        "quantity": 450.0,
                        "knr_code": "KNR 2-01 0510-01",
                        "page": 4,
                        "confidence": 0.90,
                    },
                ]
            })

        if "extract" in system_lower or "wyodrębn" in prompt_lower or "fields" in system_lower:
            return json.dumps({
                "cpv": "45233120-6",
                "value_pln": 500000.0,
                "deadline": "2025-12-31",
                "buyer": "Gmina Testowa",
                "requirements": ["doświadczenie min. 3 lata", "polisa OC 500 000 PLN"],
            })

        if "axiom" in system_lower or "zasad" in prompt_lower:
            return json.dumps({
                "axioms": [
                    {"rule": "CPV match required", "weight": 0.4},
                    {"rule": "Region match preferred", "weight": 0.2},
                ]
            })

        if "decyzj" in prompt_lower or "verdict" in system_lower or "recommend" in system_lower:
            return json.dumps({
                "verdict": "bid",
                "confidence": 0.78,
                "reasoning": "Przetarg pasuje do profilu — CPV, region i budżet w zakresie.",
                "risk_level": "medium",
            })

        # Default generic response
        return json.dumps({"result": "ok", "confidence": 0.7})

    def generate_stream(
        self, prompt: str, *, system: str = "", max_tokens: int = 4096
    ) -> Generator[str, None, None]:
        """Stream stub — yields one chunk per sentence."""
        response = self.generate(prompt, system=system)
        # Simulate streaming by yielding word by word
        try:
            data = json.loads(response)
            text = data.get("summary_md") or data.get("reasoning") or str(data)
        except (json.JSONDecodeError, TypeError):
            text = response
        words = text.split()
        for i in range(0, len(words), 5):
            yield " ".join(words[i : i + 5]) + " "

    def embed(self, text: str) -> list[float]:
        """Return deterministic fake embedding (384-dim, content-based hash)."""
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        embedding = []
        for i in range(384):
            byte_val = h[i % 32]
            embedding.append((byte_val - 128) / 128.0)
        return embedding


def get_llm_client() -> "LLMClient":
    """Factory: returns StubClient in TERRA_OFFLINE mode, VLLMClient otherwise.

    Uses TERRA_OFFLINE env var for zero-network CI/test environments.
    """
    if os.getenv("TERRA_OFFLINE", "0") == "1":
        logger.debug("source=ai_clients TERRA_OFFLINE=1, using StubClient")
        return StubClient()
    try:
        from services.ai.vllm_client import VLLMClient
        return VLLMClient()
    except Exception as exc:
        logger.warning("source=ai_clients VLLMClient unavailable (%s), falling back to StubClient", exc)
        return StubClient()
