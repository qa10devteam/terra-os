"""
Bud.OS KNR Mapper Service
Maps OPZ (Opis Przedmiotu Zamówienia) positions to KNR catalog entries.
4 strategies: direct lookup → vector similarity → keyword rules → LLM fallback.
"""
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


# ─── Models ─────────────────────────────────────────────────────────────────

class MappingStrategy(str, Enum):
    DIRECT = "direct"
    VECTOR = "vector"
    RULES = "rules"
    LLM = "llm"


@dataclass
class KNRMapping:
    """Result of mapping an OPZ position to a KNR catalog entry."""
    knr_code: str  # e.g. "KNR 2-02 0201-04"
    description: str
    naklady_r: float  # robocizna [rbh per unit]
    naklady_m: float  # materiały [PLN per unit]
    naklady_s: float  # sprzęt [PLN per unit]
    unit: str  # "m2", "m3", "szt", "mb", etc.
    confidence: float  # 0.0 - 1.0
    strategy_used: MappingStrategy
    alternatives: list["KNRMapping"] = field(default_factory=list)


@dataclass
class OPZPosition:
    """Parsed position from OPZ document."""
    id: str
    description: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    section: Optional[str] = None
    keywords: list[str] = field(default_factory=list)


# ─── Keyword Rules (Strategy 3) ────────────────────────────────────────────

KNR_KEYWORD_RULES: dict[str, list[str]] = {
    # KNR 2-01: Roboty ziemne
    "KNR 2-01": [
        "wykop", "nasyp", "korytowanie", "plantowanie", "humusowanie",
        "roboty ziemne", "odwodnienie wykopu", "zagęszczanie",
    ],
    # KNR 2-02: Konstrukcje budowlane
    "KNR 2-02": [
        "mur", "ściana", "strop", "fundament", "betonowanie", "zbrojenie",
        "szalowanie", "deskowanie", "wieniec", "nadproże", "słup",
    ],
    # KNR 2-03: Roboty instalacyjne (wod-kan, c.o.)
    "KNR 2-03": [
        "rura", "kanalizacja", "wodociąg", "przyłącze", "studzienka",
        "instalacja sanitarna", "centralne ogrzewanie", "grzejnik",
    ],
    # KNR 2-05: Roboty drogowe
    "KNR 2-05": [
        "nawierzchnia", "podbudowa", "krawężnik", "chodnik", "asfalt",
        "kostka brukowa", "jezdnia", "droga", "parking", "warstwa ścieralna",
    ],
    # KNR 4-01: Roboty remontowe
    "KNR 4-01": [
        "remont", "naprawa", "wymiana", "skucie", "tynkowanie",
        "malowanie", "szpachlowanie", "gruntowanie",
    ],
    # KNR 2-15: Roboty instalacji elektrycznych
    "KNR 2-15": [
        "kabel", "przewód", "gniazdko", "włącznik", "rozdzielnia",
        "oświetlenie", "instalacja elektryczna", "uziemienie",
    ],
    # KNR 2-17: Stolarka
    "KNR 2-17": [
        "okno", "drzwi", "stolarka", "montaż okien", "montaż drzwi",
        "parapet", "ościeżnica",
    ],
    # KNR 2-02: Izolacje
    "KNR 2-02-I": [
        "izolacja", "hydroizolacja", "termoizolacja", "styropian",
        "wełna mineralna", "papa", "folia", "docieplenie", "ocieplenie",
    ],
    # KNR 2-02: Tynki
    "KNR 2-02-T": [
        "tynk", "zaprawa", "gładź", "wyprawa", "cementowo-wapienny",
    ],
    # KNR 2-02: Pokrycia dachowe
    "KNR 2-02-D": [
        "dach", "pokrycie dachowe", "dachówka", "blachodachówka",
        "obróbka blacharska", "rynna", "krokiew", "więźba",
    ],
}


# ─── KNR Mapper Class ──────────────────────────────────────────────────────

class KNRMapper:
    """
    Maps OPZ positions to KNR catalog entries using 4 strategies.
    Strategies are tried in order of cost-efficiency:
    1. Direct code lookup (instant, free)
    2. Vector similarity via Qdrant (fast, low cost)
    3. Keyword rules (instant, free)
    4. LLM fallback (slower, costs ~$0.002/query)
    """

    def __init__(self):
        self._qdrant_client = None
        self._bedrock_client = None

    @property
    def qdrant_client(self):
        """Lazy-load Qdrant client."""
        if self._qdrant_client is None:
            from qdrant_client import QdrantClient
            self._qdrant_client = QdrantClient(url=settings.QDRANT_URL)
        return self._qdrant_client

    @property
    def bedrock_client(self):
        """Lazy-load AWS Bedrock client."""
        if self._bedrock_client is None:
            import boto3
            self._bedrock_client = boto3.client(
                "bedrock-runtime", region_name=settings.AWS_REGION
            )
        return self._bedrock_client

    async def map_position(self, position: OPZPosition) -> KNRMapping:
        """
        Map a single OPZ position to KNR using cascading strategies.
        Returns the best match with confidence score.
        """
        # Strategy 1: Direct KNR code reference
        result = await self._strategy_direct(position)
        if result and result.confidence >= 0.95:
            return result

        # Strategy 2: Vector similarity via Qdrant
        result_vector = await self._strategy_vector(position)
        if result_vector and result_vector.confidence >= 0.85:
            return result_vector

        # Strategy 3: Keyword rules
        result_rules = await self._strategy_rules(position)
        if result_rules and result_rules.confidence >= 0.75:
            return result_rules

        # Strategy 4: LLM fallback (Claude Haiku — cost optimized)
        result_llm = await self._strategy_llm(position)
        if result_llm:
            return result_llm

        # Fallback: return best available or error
        candidates = [r for r in [result, result_vector, result_rules, result_llm] if r]
        if candidates:
            return max(candidates, key=lambda x: x.confidence)

        # No mapping found
        return KNRMapping(
            knr_code="UNMAPPED",
            description=position.description,
            naklady_r=0.0,
            naklady_m=0.0,
            naklady_s=0.0,
            unit=position.unit or "szt",
            confidence=0.0,
            strategy_used=MappingStrategy.DIRECT,
        )

    async def map_opz_positions(self, positions: list[OPZPosition]) -> list[KNRMapping]:
        """Map all OPZ positions. Returns list of KNR mappings."""
        import asyncio
        results = await asyncio.gather(*[self.map_position(p) for p in positions])
        return list(results)

    # ─── Strategy 1: Direct KNR Code Lookup ─────────────────────────────────

    async def _strategy_direct(self, position: OPZPosition) -> Optional[KNRMapping]:
        """
        Strategy 1: Direct KNR code reference in description.
        Looks for patterns like "KNR 2-02 0201-04" in the text.
        """
        import re
        # Pattern: KNR X-XX XXXX-XX (with variations)
        knr_pattern = r"KNR\s*(\d+[-/]\d+)\s*(\d{4}[-/]\d{2})"
        match = re.search(knr_pattern, position.description, re.IGNORECASE)

        if not match:
            return None

        knr_code = f"KNR {match.group(1)} {match.group(2)}".replace("/", "-")

        # TODO: lookup knr_code in DB (knr_catalog table)
        # For now, return with high confidence since we found explicit reference
        return KNRMapping(
            knr_code=knr_code,
            description=position.description,
            naklady_r=0.0,  # TODO: fill from DB
            naklady_m=0.0,
            naklady_s=0.0,
            unit=position.unit or "szt",
            confidence=0.98,
            strategy_used=MappingStrategy.DIRECT,
        )

    # ─── Strategy 2: Vector Similarity via Qdrant ───────────────────────────

    async def _strategy_vector(self, position: OPZPosition) -> Optional[KNRMapping]:
        """
        Strategy 2: Embedding-based similarity search in Qdrant.
        Collection: knr_embeddings (~45000 positions).
        Threshold: 0.85 cosine similarity.
        """
        try:
            # Generate embedding for the position description
            embedding = await self._get_embedding(position.description)

            # Search Qdrant
            results = self.qdrant_client.search(
                collection_name=settings.QDRANT_COLLECTION_KNR,
                query_vector=embedding,
                limit=3,
                score_threshold=0.85,
            )

            if not results:
                return None

            best = results[0]
            payload = best.payload

            return KNRMapping(
                knr_code=payload.get("knr_code", ""),
                description=payload.get("description", ""),
                naklady_r=payload.get("naklady_r", 0.0),
                naklady_m=payload.get("naklady_m", 0.0),
                naklady_s=payload.get("naklady_s", 0.0),
                unit=payload.get("unit", "szt"),
                confidence=round(best.score, 3),
                strategy_used=MappingStrategy.VECTOR,
                alternatives=[
                    KNRMapping(
                        knr_code=r.payload.get("knr_code", ""),
                        description=r.payload.get("description", ""),
                        naklady_r=r.payload.get("naklady_r", 0.0),
                        naklady_m=r.payload.get("naklady_m", 0.0),
                        naklady_s=r.payload.get("naklady_s", 0.0),
                        unit=r.payload.get("unit", "szt"),
                        confidence=round(r.score, 3),
                        strategy_used=MappingStrategy.VECTOR,
                    )
                    for r in results[1:]
                ],
            )
        except Exception as e:
            logger.warning(f"Vector strategy failed: {e}")
            return None

    async def _get_embedding(self, text: str) -> list[float]:
        """Generate text embedding using Bedrock Titan Embeddings."""
        response = self.bedrock_client.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            body=json.dumps({"inputText": text}),
        )
        result = json.loads(response["body"].read())
        return result["embedding"]

    # ─── Strategy 3: Keyword Rules ──────────────────────────────────────────

    async def _strategy_rules(self, position: OPZPosition) -> Optional[KNRMapping]:
        """
        Strategy 3: Keyword-based rules mapping.
        Matches description keywords to KNR groups.
        """
        text_lower = position.description.lower()
        best_group = None
        best_score = 0

        for knr_group, keywords in KNR_KEYWORD_RULES.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches > best_score:
                best_score = matches
                best_group = knr_group

        if not best_group or best_score == 0:
            return None

        # Confidence based on number of keyword matches
        confidence = min(0.5 + (best_score * 0.1), 0.85)

        # TODO: lookup specific position within group from DB
        return KNRMapping(
            knr_code=f"{best_group} (group match)",
            description=position.description,
            naklady_r=0.0,  # TODO: average for group
            naklady_m=0.0,
            naklady_s=0.0,
            unit=position.unit or "szt",
            confidence=round(confidence, 2),
            strategy_used=MappingStrategy.RULES,
        )

    # ─── Strategy 4: LLM Fallback (Claude Haiku) ───────────────────────────

    async def _strategy_llm(self, position: OPZPosition) -> Optional[KNRMapping]:
        """
        Strategy 4: LLM-based mapping using Claude Haiku (cost optimized).
        Used as last resort when other strategies fail.
        Cost: ~$0.002 per query.
        """
        prompt = f"""Jesteś ekspertem kosztorysowania budowlanego w Polsce.
Zmapuj poniższy opis roboty budowlanej na najbliższą pozycję w katalogu KNR.

Opis roboty: {position.description}
Jednostka (jeśli podana): {position.unit or 'nie podana'}
Sekcja OPZ: {position.section or 'nie podana'}

Odpowiedz w formacie JSON:
{{
    "knr_code": "KNR X-XX XXXX-XX",
    "description": "opis pozycji KNR",
    "naklady_r": 0.0,
    "naklady_m": 0.0,
    "naklady_s": 0.0,
    "unit": "m2/m3/szt/mb/etc",
    "confidence": 0.0-1.0,
    "reasoning": "krótkie uzasadnienie"
}}"""

        try:
            response = self.bedrock_client.invoke_model(
                modelId="anthropic.claude-3-haiku-20240307-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 500,
                    "temperature": 0.1,
                    "messages": [{"role": "user", "content": prompt}],
                }),
            )

            result = json.loads(response["body"].read())
            content = result["content"][0]["text"]

            # Parse JSON from response
            # Handle potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            parsed = json.loads(content.strip())

            return KNRMapping(
                knr_code=parsed["knr_code"],
                description=parsed["description"],
                naklady_r=float(parsed.get("naklady_r", 0.0)),
                naklady_m=float(parsed.get("naklady_m", 0.0)),
                naklady_s=float(parsed.get("naklady_s", 0.0)),
                unit=parsed.get("unit", position.unit or "szt"),
                confidence=min(float(parsed.get("confidence", 0.6)), 0.80),  # Cap LLM confidence
                strategy_used=MappingStrategy.LLM,
            )
        except Exception as e:
            logger.error(f"LLM strategy failed: {e}")
            return None
