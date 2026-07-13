"""AI Router — routes tasks to local or cloud LLM target.

Usage:
    from services.ai.router import Task, route, get_client_for_task

    target = route(Task.SUMMARIZE)           # -> LLMTarget.CLOUD
    client = get_client_for_task(Task.EMBED) # -> appropriate LLMClient
"""
from __future__ import annotations

import logging
import os
from enum import Enum
from typing import NamedTuple, TYPE_CHECKING

if TYPE_CHECKING:
    from services.ai.clients import LLMClient

logger = logging.getLogger(__name__)


class LLMTarget(str, Enum):
    LOCAL = "local"      # Ollama / vLLM / StubClient
    CLOUD = "cloud"      # Bedrock Claude / OpenAI / StubClient


class Task(str, Enum):
    CLASSIFY          = "classify"           # doc type classification
    EXTRACT_FIELDS    = "extract_fields"     # structured field extraction from BZP/TED
    EXTRACT_PRZEDMIAR = "extract_przedmiar"  # BOQ / bill-of-quantities extraction
    OCR_VLM           = "ocr_vlm"            # vision OCR for scanned docs
    PREFILTER_MATCH   = "prefilter_match"    # fast relevance pre-filter
    REASON_REDFLAGS   = "reason_redflags"    # contract red-flag reasoning
    EXTRACT_AXIOMS    = "extract_axioms"     # axiom extraction for engine
    EXPLAIN_VERDICT   = "explain_verdict"    # explain bid/skip/watch verdict
    DECISION          = "decision"           # bid/skip/watch decision with reasoning
    CHAT_EDIT         = "chat_edit"          # interactive chat / document editing
    SUMMARIZE         = "summarize"          # tender summary generation
    EMBED             = "embed"              # text embedding


# Tasks that run locally (zero egress, zero marginal cost, fast)
_LOCAL_TASKS = {
    Task.CLASSIFY,
    Task.EXTRACT_FIELDS,
    Task.EXTRACT_PRZEDMIAR,
    Task.OCR_VLM,
    Task.PREFILTER_MATCH,
    Task.EMBED,
}

# Tasks that benefit from cloud reasoning (complex, high-value outputs)
_CLOUD_TASKS = {
    Task.REASON_REDFLAGS,
    Task.EXTRACT_AXIOMS,
    Task.EXPLAIN_VERDICT,
    Task.DECISION,
    Task.CHAT_EDIT,
    Task.SUMMARIZE,
}


def route(task: Task) -> LLMTarget:
    """Route a task to the appropriate LLM target.

    Returns the logical target — use get_client_for_task() to get an actual client.
    TERRA_OFFLINE mode is handled at client-factory level, not here.
    """
    if task in _LOCAL_TASKS:
        return LLMTarget.LOCAL
    if task in _CLOUD_TASKS:
        return LLMTarget.CLOUD
    # Default: local (safe fallback)
    return LLMTarget.LOCAL


def get_client_for_task(task: Task) -> "LLMClient":
    """Return the appropriate LLMClient for a given task.

    Uses TERRA_OFFLINE=1 to force StubClient for all tasks (CI/test).
    Falls back gracefully: CLOUD unavailable -> LOCAL -> StubClient.
    """
    from services.ai.clients import StubClient, get_llm_client

    if os.getenv("TERRA_OFFLINE", "0") == "1":
        return StubClient()

    target = route(task)

    if target == LLMTarget.LOCAL:
        try:
            from services.ai.vllm_client import VLLMClient
            return VLLMClient()
        except Exception as exc:
            logger.debug("source=router task=%s LOCAL vllm unavailable: %s", task.value, exc)
            return StubClient()

    # CLOUD target
    try:
        from services.ai.bedrock_client import BedrockClient  # type: ignore[import]
        return BedrockClient()
    except Exception:
        pass
    try:
        from services.ai.vllm_client import VLLMClient
        logger.debug("source=router task=%s CLOUD unavailable, using local vLLM", task.value)
        return VLLMClient()
    except Exception as exc:
        logger.debug("source=router task=%s all clients failed, using StubClient: %s", task.value, exc)
        return StubClient()


# ── Convenience: task metadata ─────────────────────────────────────────────────

_TASK_SYSTEM_PROMPTS: dict[Task, str] = {
    Task.CLASSIFY: (
        "Jesteś klasyfikatorem dokumentów przetargowych. "
        "Zwróć JSON: {\"kind\": \"przedmiar|swz|opis|umowa|oferta|inne\", \"confidence\": 0.0-1.0}."
    ),
    Task.EXTRACT_FIELDS: (
        "Jesteś ekstrakcją strukturalną danych przetargowych. "
        "Zwróć JSON z polami: cpv, value_pln, deadline, buyer, requirements[]."
    ),
    Task.EXTRACT_PRZEDMIAR: (
        "Jesteś parserem przedmiarów robót (KNR). "
        "Zwróć JSON: {\"items\": [{\"position_no\",\"description\",\"unit\",\"quantity\",\"knr_code\",\"confidence\"}]}."
    ),
    Task.SUMMARIZE: (
        "Jesteś ekspertem przetargów budowlanych. Piszesz po polsku, zwięźle. "
        "Zwróć JSON: {\"summary_md\": \"...\", \"key_facts\": {\"value_pln\": N, \"deadline_days\": N}}."
    ),
    Task.REASON_REDFLAGS: (
        "Analizujesz klauzule umowne pod kątem ryzyka. "
        "Zwróć JSON: {\"red_flags\": [{\"severity\",\"category\",\"message\",\"provenance\",\"confidence\"}]}."
    ),
    Task.DECISION: (
        "Jesteś doradcą decyzji przetargowych. "
        "Zwróć JSON: {\"verdict\": \"bid|skip|watch\", \"confidence\": 0.0-1.0, \"reasoning\": \"...\", \"risk_level\": \"low|medium|high\"}."
    ),
    Task.EXPLAIN_VERDICT: (
        "Wyjaśnij po polsku decyzję przetargową. Bądź konkretny i zwięzły."
    ),
}


def system_prompt_for(task: Task) -> str:
    """Return the standard system prompt for a task, or empty string."""
    return _TASK_SYSTEM_PROMPTS.get(task, "")
