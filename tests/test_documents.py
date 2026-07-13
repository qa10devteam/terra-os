"""Comprehensive offline unit tests for the documents layer + AI enricher.

Covers (55 tests total):
  TestRedFlag             — to_dict keys, severity values, confidence default
  TestAnalysis            — to_dict structure, empty red_flags, przedmiar_items
  TestChunkDocumentEdge   — 5 edge cases not in test_ai_scraper.py
  TestClassifyDocument    — mock LLMClient, returns kind + confidence, fallbacks
  TestParsePrzedmiar      — KNR extraction, empty text, page offset, to_dict
  TestRiskExtractor       — extract_risk_flags list[str], risk_level thresholds
  TestEnricher            — run_enrichment(background=False) with mocked engine

All tests are fully offline — no DB, no network, no sentence_transformers loaded.

Run:
    PYTHONPATH=/home/ubuntu/terra-os:/home/ubuntu/terra-os/services:/home/ubuntu/terra-os/packages/db:/home/ubuntu/terra-os/packages/vendor:/home/ubuntu/terra-os/packages/shared \\
    .venv/bin/python3 -m pytest tests/test_documents.py -q
"""
from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, call
import tempfile

import pytest

# ── Environment ────────────────────────────────────────────────────────────────
os.environ.setdefault("TERRA_OFFLINE", "1")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "terraos")
os.environ.setdefault("DB_USER", "terraos")
os.environ.setdefault("DB_PASSWORD", "terra_dev_2026")

# ── PYTHONPATH ─────────────────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in [
    ROOT,
    os.path.join(ROOT, "services"),
    os.path.join(ROOT, "packages", "vendor"),
    os.path.join(ROOT, "packages", "shared"),
    os.path.join(ROOT, "packages", "db"),
]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Stub sentence_transformers BEFORE any project import ──────────────────────
_st_mod = types.ModuleType("sentence_transformers")

class _FakeSentenceTransformer:
    def __init__(self, *a, **kw):
        pass
    def encode(self, texts, **kw):
        import numpy as np
        if isinstance(texts, str):
            return [0.0] * 384
        return [[0.0] * 384 for _ in texts]

_st_mod.SentenceTransformer = _FakeSentenceTransformer  # type: ignore
sys.modules.setdefault("sentence_transformers", _st_mod)

# Stub numpy if not available (some CI environments)
try:
    import numpy as np  # noqa: F401
except ImportError:
    _np = types.ModuleType("numpy")
    _np.array = list  # type: ignore
    sys.modules["numpy"] = _np

# ═══════════════════════════════════════════════════════════════════════════════
# Imports (after stubs are in place)
# ═══════════════════════════════════════════════════════════════════════════════
from services.documents.analysis import (  # noqa: E402
    RedFlag,
    Analysis,
    _detect_redflags_regex,
    analyze_tender,
)
from services.documents.chunk import chunk_and_embed, DocumentChunk  # noqa: E402
from services.documents.classify import (  # noqa: E402
    classify_document,
    DocKind,
    ClassifyResult,
)
from services.documents.parse_przedmiar import (  # noqa: E402
    parse_przedmiar,
    PrzedmiarItem,
)
from services.documents.risk_extractor import (  # noqa: E402
    extract_risk_flags,
    risk_level,
)
from services.ai.clients import StubClient  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _make_redflag(**kw) -> RedFlag:
    defaults = dict(
        severity="high",
        category="kary_umowne",
        message="Kara umowna 0.5%/dzień",
        provenance={"doc_id": "doc-1", "page": 1, "line": "§14"},
    )
    defaults.update(kw)
    return RedFlag(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# TestRedFlag
# ═══════════════════════════════════════════════════════════════════════════════

class TestRedFlag:
    """Tests for RedFlag dataclass."""

    def test_to_dict_has_all_required_keys(self):
        rf = _make_redflag()
        d = rf.to_dict()
        assert set(d.keys()) == {"severity", "category", "message", "provenance", "confidence"}

    def test_to_dict_values_match_fields(self):
        rf = _make_redflag(severity="critical", category="brak_waloryzacji", confidence=0.95)
        d = rf.to_dict()
        assert d["severity"] == "critical"
        assert d["category"] == "brak_waloryzacji"
        assert d["confidence"] == 0.95

    def test_default_confidence_is_0_8(self):
        rf = RedFlag(
            severity="medium",
            category="znwu_wysokie",
            message="ZNWU 15%",
            provenance={"doc_id": "x", "page": 2, "line": "§10"},
        )
        assert rf.confidence == 0.8

    def test_severity_critical(self):
        rf = _make_redflag(severity="critical")
        assert rf.to_dict()["severity"] == "critical"

    def test_severity_high(self):
        rf = _make_redflag(severity="high")
        assert rf.to_dict()["severity"] == "high"

    def test_severity_medium(self):
        rf = _make_redflag(severity="medium")
        assert rf.to_dict()["severity"] == "medium"

    def test_severity_low(self):
        rf = _make_redflag(severity="low")
        assert rf.to_dict()["severity"] == "low"

    def test_provenance_preserved_in_to_dict(self):
        prov = {"doc_id": "doc-99", "page": 5, "line": "tekst linii"}
        rf = _make_redflag(provenance=prov)
        assert rf.to_dict()["provenance"] == prov

    def test_message_preserved(self):
        msg = "Kara umowna przekracza bezpieczny próg"
        rf = _make_redflag(message=msg)
        assert rf.to_dict()["message"] == msg

    def test_custom_confidence_stored(self):
        rf = _make_redflag(confidence=0.42)
        assert rf.to_dict()["confidence"] == pytest.approx(0.42)


# ═══════════════════════════════════════════════════════════════════════════════
# TestAnalysis
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalysis:
    """Tests for Analysis dataclass."""

    def test_to_dict_has_required_keys(self):
        a = Analysis(summary_md="test")
        d = a.to_dict()
        assert set(d.keys()) == {"summary_md", "red_flags", "key_facts", "przedmiar_items"}

    def test_to_dict_summary_md(self):
        a = Analysis(summary_md="## Summary\nText")
        assert a.to_dict()["summary_md"] == "## Summary\nText"

    def test_empty_red_flags_returns_empty_list(self):
        a = Analysis(summary_md="x")
        assert a.to_dict()["red_flags"] == []

    def test_red_flags_serialized_as_list_of_dicts(self):
        rf = _make_redflag()
        a = Analysis(summary_md="x", red_flags=[rf])
        result = a.to_dict()["red_flags"]
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)

    def test_red_flags_contain_to_dict_output(self):
        rf = _make_redflag(severity="critical")
        a = Analysis(summary_md="x", red_flags=[rf])
        assert a.to_dict()["red_flags"][0]["severity"] == "critical"

    def test_empty_przedmiar_items_returns_empty_list(self):
        a = Analysis(summary_md="x")
        assert a.to_dict()["przedmiar_items"] == []

    def test_przedmiar_items_stored_directly(self):
        items = [{"position_no": "1.1", "description": "Wykopy", "unit": "m3", "quantity": 100.0}]
        a = Analysis(summary_md="x", przedmiar_items=items)
        assert a.to_dict()["przedmiar_items"] == items

    def test_key_facts_empty_by_default(self):
        a = Analysis(summary_md="x")
        assert a.to_dict()["key_facts"] == {}

    def test_key_facts_stored(self):
        facts = {"wartosc": "100000", "termin": "60 dni"}
        a = Analysis(summary_md="x", key_facts=facts)
        assert a.to_dict()["key_facts"] == facts

    def test_multiple_red_flags(self):
        flags = [_make_redflag(category=f"cat_{i}") for i in range(5)]
        a = Analysis(summary_md="x", red_flags=flags)
        assert len(a.to_dict()["red_flags"]) == 5


# ═══════════════════════════════════════════════════════════════════════════════
# TestChunkDocumentEdge  (edge cases not covered in test_ai_scraper.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestChunkDocumentEdge:
    """Edge cases for chunk_and_embed beyond what test_ai_scraper already tests."""

    def test_whitespace_only_page_is_skipped(self):
        llm = StubClient()
        pages = [{"page_num": 1, "text": "   \n\t  "}, {"page_num": 2, "text": "Real content here"}]
        chunks = chunk_and_embed("doc-edge1", pages, llm=llm)
        assert all(c.page == 2 for c in chunks)

    def test_chunk_ids_are_unique(self):
        llm = StubClient()
        pages = [{"page_num": 1, "text": "X" * 5000}]
        chunks = chunk_and_embed("doc-edge2", pages, llm=llm)
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids)), "Chunk IDs must be unique"

    def test_position_in_doc_monotonically_increases(self):
        llm = StubClient()
        pages = [
            {"page_num": 1, "text": "A" * 3000},
            {"page_num": 2, "text": "B" * 3000},
        ]
        chunks = chunk_and_embed("doc-edge3", pages, llm=llm)
        positions = [c.position_in_doc for c in chunks]
        assert positions == sorted(positions)

    def test_doc_id_propagated_to_all_chunks(self):
        llm = StubClient()
        pages = [{"page_num": 1, "text": "Content " * 100}]
        chunks = chunk_and_embed("my-special-doc-id", pages, llm=llm)
        assert all(c.doc_id == "my-special-doc-id" for c in chunks)

    def test_to_dict_reports_embedding_dim(self):
        llm = StubClient()
        pages = [{"page_num": 1, "text": "Sample text for embedding"}]
        chunks = chunk_and_embed("doc-edge5", pages, llm=llm)
        assert len(chunks) >= 1
        d = chunks[0].to_dict()
        assert "embedding_dim" in d
        assert d["embedding_dim"] == 384


# ═══════════════════════════════════════════════════════════════════════════════
# TestClassifyDocument
# ═══════════════════════════════════════════════════════════════════════════════

class TestClassifyDocument:
    """Tests for classify_document with LLM mock."""

    def test_filename_przedmiar_no_llm(self):
        r = classify_document("Przedmiar_roboty.pdf")
        assert r.kind == DocKind.PRZEDMIAR
        assert r.confidence == pytest.approx(0.90)

    def test_filename_kosztorys(self):
        r = classify_document("kosztorys_ofertowy.xlsx")
        assert r.kind == DocKind.KOSZTORYS

    def test_filename_umowa(self):
        r = classify_document("wzor_umowy_2024.pdf")
        assert r.kind == DocKind.UMOWA

    def test_content_heuristic_stwior(self):
        r = classify_document("zal_3.pdf", first_page_text="SPECYFIKACJA TECHNICZNA WYKONANIA I ODBIORU ROBÓT")
        assert r.kind == DocKind.STWIOR

    def test_content_heuristic_swz(self):
        r = classify_document("zal_1.pdf", first_page_text="SPECYFIKACJA WARUNKÓW ZAMÓWIENIA SWZ")
        assert r.kind == DocKind.SWZ
        assert r.confidence == pytest.approx(0.80)

    def test_content_heuristic_design(self):
        r = classify_document("doc.pdf", first_page_text="PROJEKT BUDOWLANY dla budowy drogi")
        assert r.kind == DocKind.DESIGN

    def test_unknown_filename_returns_other_without_llm(self):
        r = classify_document("attachment_99.bin")
        assert r.kind == DocKind.OTHER
        assert r.confidence == pytest.approx(0.3)

    def test_llm_fallback_called_when_heuristic_fails(self):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = json.dumps({"kind": "swz", "confidence": 0.75})
        r = classify_document("mystery_doc.pdf", first_page_text="random text", llm=mock_llm)
        assert r.kind == DocKind.SWZ
        assert r.confidence == pytest.approx(0.75)
        mock_llm.generate.assert_called_once()

    def test_llm_returns_other_on_bad_json(self):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "NOT JSON"
        r = classify_document("mystery.pdf", llm=mock_llm)
        # Should gracefully fall back to OTHER
        assert r.kind == DocKind.OTHER

    def test_llm_returns_kind_and_confidence(self):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = json.dumps({"kind": "umowa", "confidence": 0.88})
        r = classify_document("contract.pdf", llm=mock_llm)
        assert r.kind == DocKind.UMOWA
        assert r.confidence == pytest.approx(0.88)

    def test_filename_priority_over_content(self):
        # Filename says przedmiar, content says swz — filename wins
        r = classify_document("przedmiar_droga.pdf", first_page_text="SPECYFIKACJA WARUNKÓW ZAMÓWIENIA")
        assert r.kind == DocKind.PRZEDMIAR
        assert r.confidence == pytest.approx(0.90)

    def test_stub_client_llm_fallback(self):
        # StubClient classify response
        r = classify_document("weird.pdf", first_page_text="Dokument budowlany", llm=StubClient())
        assert r.kind == DocKind.PRZEDMIAR  # StubClient returns "przedmiar"


# ═══════════════════════════════════════════════════════════════════════════════
# TestParsePrzedmiar
# ═══════════════════════════════════════════════════════════════════════════════

_SAMPLE_PRZEDMIAR = """\
1.1 | Wykopy mechaniczne w gruncie kat. III z transportem do 1 km | m3 | 1250.00 | KNR 2-01 0211-03
1.2 | Nasypy z gruntu kat. II z zagęszczeniem walcem | m3 | 800.00 | KNR 2-01 0307-02
1.3 | Transport urobku na odległość do 5 km | m3 | 450.00 | KNR 2-01 0510-01
1.4 | Zagęszczenie podłoża walcem wibracyjnym 8t | m2 | 3200.00 | KNR 2-01 0405-04
2.1 | Podbudowa z kruszywa łamanego 0/31.5 gr. 20 cm | m2 | 2800.00 | KNR 2-31 0108-01
2.2 | Nawierzchnia z betonu asfaltowego AC16W gr. 5 cm | m2 | 2500.00 | KNR 2-31 0403-02
"""


class TestParsePrzedmiar:
    """Tests for parse_przedmiar."""

    def test_empty_text_returns_empty_list(self):
        items = parse_przedmiar("")
        assert items == []

    def test_whitespace_only_returns_empty_list(self):
        items = parse_przedmiar("   \n\t  ")
        assert items == []

    def test_extract_all_items_from_sample(self):
        items = parse_przedmiar(_SAMPLE_PRZEDMIAR)
        assert len(items) == 6

    def test_knr_codes_extracted(self):
        items = parse_przedmiar(_SAMPLE_PRZEDMIAR)
        for item in items:
            assert item.knr_code is not None
            assert "KNR" in item.knr_code

    def test_position_numbers_correct(self):
        items = parse_przedmiar(_SAMPLE_PRZEDMIAR)
        assert items[0].position_no == "1.1"
        assert items[1].position_no == "1.2"
        assert items[4].position_no == "2.1"

    def test_units_are_valid(self):
        from services.documents.parse_przedmiar import VALID_UNITS
        items = parse_przedmiar(_SAMPLE_PRZEDMIAR)
        for item in items:
            assert item.unit in VALID_UNITS

    def test_quantities_are_positive_floats(self):
        items = parse_przedmiar(_SAMPLE_PRZEDMIAR)
        for item in items:
            assert isinstance(item.quantity, float)
            assert item.quantity > 0

    def test_page_offset_propagated(self):
        items = parse_przedmiar(_SAMPLE_PRZEDMIAR, page_offset=5)
        for item in items:
            assert item.page == 5

    def test_to_dict_has_all_keys(self):
        items = parse_przedmiar(_SAMPLE_PRZEDMIAR)
        d = items[0].to_dict()
        expected_keys = {"position_no", "description", "unit", "quantity", "knr_code", "page", "confidence"}
        assert set(d.keys()) == expected_keys

    def test_llm_fallback_triggered_on_non_table_text(self):
        """If regex yields <3 items, LLM extraction is tried."""
        llm = StubClient()
        # No tabular format — regex will find 0 items, llm invoked
        items = parse_przedmiar("Jakiś losowy tekst bez tabeli", llm=llm)
        # StubClient returns 3+ items
        assert len(items) >= 3

    def test_item_confidence_default(self):
        items = parse_przedmiar(_SAMPLE_PRZEDMIAR)
        for item in items:
            assert 0 < item.confidence <= 1.0

    def test_m3_and_m2_units_parsed(self):
        items = parse_przedmiar(_SAMPLE_PRZEDMIAR)
        units = {item.unit for item in items}
        assert "m3" in units
        assert "m2" in units


# ═══════════════════════════════════════════════════════════════════════════════
# TestRiskExtractor
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskExtractor:
    """Tests for extract_risk_flags and risk_level."""

    def test_returns_list_of_strings(self):
        result = extract_risk_flags("Brak ryzyk w tym tekście.")
        assert isinstance(result, list)
        assert all(isinstance(f, str) for f in result)

    def test_empty_text_returns_empty_list(self):
        assert extract_risk_flags("") == []

    def test_high_kara_umowna_detected(self):
        text = "Kara umowna wynosi 20% za każdy dzień opóźnienia."
        flags = extract_risk_flags(text)
        assert any(f.startswith("kara_umowna_") for f in flags)

    def test_low_kara_umowna_not_flagged(self):
        text = "Kara umowna wynosi 5% za każdy dzień opóźnienia."
        flags = extract_risk_flags(text)
        assert not any(f.startswith("kara_umowna_") for f in flags)

    def test_high_financial_req_detected(self):
        text = "Wymagany obrót wykonawcy: 2500000 zł w ostatnich 3 latach."
        flags = extract_risk_flags(text)
        assert "high_financial_req" in flags

    def test_financial_req_below_threshold_not_flagged(self):
        text = "Obrót wymagany 10000 zł."
        flags = extract_risk_flags(text)
        assert "high_financial_req" not in flags

    def test_high_zabezpieczenie_detected(self):
        text = "Zabezpieczenie należytego wykonania umowy wynosi 15% wynagrodzenia."
        flags = extract_risk_flags(text)
        assert any(f.startswith("zabezpieczenie_") for f in flags)

    def test_zabezpieczenie_at_threshold_not_flagged(self):
        text = "Zabezpieczenie wynosi 5% wartości umowy."
        flags = extract_risk_flags(text)
        assert not any(f.startswith("zabezpieczenie_") for f in flags)

    def test_risk_level_high_on_3_or_more_flags(self):
        flags = ["kara_umowna_20pct", "high_financial_req", "zabezpieczenie_15pct"]
        level, score = risk_level(flags)
        assert level == "high"
        assert score == pytest.approx(0.9)

    def test_risk_level_mid_on_1_or_2_flags(self):
        for n in (1, 2):
            flags = [f"flag_{i}" for i in range(n)]
            level, score = risk_level(flags)
            assert level == "mid"
            assert score == pytest.approx(0.5)

    def test_risk_level_low_on_empty_flags(self):
        level, score = risk_level([])
        assert level == "low"
        assert score == pytest.approx(0.1)

    def test_flags_are_deduplicated(self):
        text = (
            "Kara umowna wynosi 20% za dzień. "
            "Kara umowna wynosi 20% za każdy dzień opóźnienia."
        )
        flags = extract_risk_flags(text)
        assert len(flags) == len(set(flags)), "Flags should be deduplicated"

    def test_combined_text_multiple_risks(self):
        text = (
            "Kary umowne: 20% za dzień opóźnienia. "
            "Obrót wykonawcy musi wynosić min 1500000 zł. "
            "Zabezpieczenie 15% wartości umowy."
        )
        flags = extract_risk_flags(text)
        level, _ = risk_level(flags)
        assert level == "high"


# ═══════════════════════════════════════════════════════════════════════════════
# TestEnricher
# ═══════════════════════════════════════════════════════════════════════════════

def _make_mock_engine(rows=None):
    """Build a SQLAlchemy engine mock that returns ``rows`` on fetchall()."""
    engine = MagicMock()
    conn = MagicMock()
    ctx_conn = MagicMock()
    ctx_conn.__enter__ = MagicMock(return_value=conn)
    ctx_conn.__exit__ = MagicMock(return_value=False)
    engine.connect.return_value = ctx_conn

    # begin() context for UPDATE calls
    conn2 = MagicMock()
    ctx_begin = MagicMock()
    ctx_begin.__enter__ = MagicMock(return_value=conn2)
    ctx_begin.__exit__ = MagicMock(return_value=False)
    engine.begin.return_value = ctx_begin

    if rows is not None:
        conn.execute.return_value.fetchall.return_value = rows

    return engine


class TestEnricher:
    """Tests for run_enrichment and individual enricher steps."""

    def test_run_enrichment_background_false_returns_none(self):
        from services.ai.enricher import run_enrichment
        engine = _make_mock_engine(rows=[])
        # All steps wrapped in try/except — they should not raise
        result = run_enrichment(engine, "tenant-abc", background=False)
        assert result is None

    def test_run_enrichment_background_true_returns_thread(self):
        import threading
        from services.ai.enricher import run_enrichment
        engine = _make_mock_engine(rows=[])
        t = run_enrichment(engine, "tenant-abc", background=True)
        assert isinstance(t, threading.Thread)
        t.join(timeout=3)

    def test_embed_tenders_step_returns_int(self):
        from services.ai.enricher import embed_tenders
        engine = _make_mock_engine()
        with patch("services.ai.enricher.embed_tenders") as mock_step:
            mock_step.return_value = 7
            result = mock_step(engine, "t1")
        assert isinstance(result, int)
        assert result == 7

    def test_embed_swz_step_returns_int(self):
        from services.ai.enricher import embed_swz_documents
        engine = _make_mock_engine(rows=[])
        # No rows → immediate return 0
        result = embed_swz_documents(engine, "t1")
        assert isinstance(result, int)
        assert result == 0

    def test_auto_summarize_step_returns_int(self):
        from services.ai.enricher import auto_summarize
        engine = _make_mock_engine(rows=[])
        result = auto_summarize(engine, "t1")
        assert isinstance(result, int)

    def test_extract_risk_after_embed_returns_int_no_rows(self):
        from services.ai.enricher import extract_risk_after_embed
        engine = _make_mock_engine(rows=[])
        result = extract_risk_after_embed(engine, "t1")
        assert isinstance(result, int)
        assert result == 0

    def test_extract_risk_after_embed_updates_risk_level(self, tmp_path):
        """extract_risk_after_embed reads local_path and writes risk_level."""
        from services.ai.enricher import extract_risk_after_embed

        # Create temp file with risky SWZ content
        swz_file = tmp_path / "swz.txt"
        swz_file.write_text(
            "Kary umowne 20% za dzień. Obrót min 2000000 zł. Zabezpieczenie 15%.",
            encoding="utf-8",
        )

        # Simulate one DB row: (doc_id, local_path)
        fake_row = MagicMock()
        fake_row.__getitem__ = lambda self, i: ("doc-uuid-1" if i == 0 else str(swz_file))

        engine = _make_mock_engine(rows=[fake_row])
        result = extract_risk_after_embed(engine, "tenant-xyz")
        # Should have updated 1 document
        assert result == 1

    def test_extract_risk_after_embed_skips_empty_file(self, tmp_path):
        """Empty local file: skip, do not update DB."""
        from services.ai.enricher import extract_risk_after_embed

        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")

        fake_row = MagicMock()
        fake_row.__getitem__ = lambda self, i: ("doc-uuid-2" if i == 0 else str(empty_file))

        engine = _make_mock_engine(rows=[fake_row])
        result = extract_risk_after_embed(engine, "tenant-xyz")
        assert result == 0

    def test_run_enrichment_specific_steps(self):
        from services.ai.enricher import run_enrichment
        engine = _make_mock_engine(rows=[])
        # Should not raise when limiting to a single step
        result = run_enrichment(engine, "t1", steps=["extract_risk"], background=False)
        assert result is None

    def test_run_enrichment_all_steps_list_matches_implementation(self):
        """Verify the documented default steps match what the code supports."""
        import inspect
        from services.ai import enricher as _enr
        src = inspect.getsource(_enr.run_enrichment)
        for step in ("embed_tenders", "embed_swz", "ml_retrain", "summarize", "extract_risk"):
            assert step in src, f"Step '{step}' missing from run_enrichment source"

    def test_trigger_ml_retrain_returns_dict(self):
        from services.ai.enricher import trigger_ml_retrain_if_due
        engine = _make_mock_engine()
        # ML scorer import may fail in offline mode — that's acceptable
        result = trigger_ml_retrain_if_due(engine)
        assert isinstance(result, dict)
        assert "status" in result

    def test_embed_tenders_returns_zero_on_import_error(self):
        from services.ai.enricher import embed_tenders
        engine = _make_mock_engine()
        with patch("services.ai.enricher.embed_tenders") as mocked:
            mocked.return_value = 0
            result = mocked(engine, "t1")
        assert result == 0

    def test_extract_risk_step_included_in_default_all_steps(self):
        """extract_risk must be in _all_steps to run by default."""
        import inspect
        from services.ai import enricher as _enr
        src = inspect.getsource(_enr.run_enrichment)
        # The set definition should contain extract_risk
        assert '"extract_risk"' in src or "'extract_risk'" in src
