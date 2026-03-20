"""Tests for the Integrate phase: two-step LLM decision + execution."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import pytest

from zettelkasten.integrate import IntegrationResult, NOTE_BODY_LARGE, integrate_phase
from zettelkasten.note import ZettelNote
from zettelkasten.providers import MockLLM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STEP2_BODY = "## Testing Effect\n\nActive retrieval strengthens memory more than passive review of material."


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _note(id_: str, title: str, body: str) -> ZettelNote:
    return ZettelNote(
        id=id_, title=title, body=body,
        type="permanent", confidence=0.8, salience=0.5,
        stable=True, created=_now(), updated=_now(), last_accessed=_now(),
    )


def _draft(title: str = "Active Recall", body: str = "Retrieving information leads to durable memory.") -> ZettelNote:
    return ZettelNote(
        id="", title=title, body=body,
        type="stub", confidence=0.3, salience=0.5,
        stable=False, created=_now(), updated=_now(), last_accessed=_now(),
    )


def _seq_llm(*responses: str) -> MockLLM:
    """MockLLM that returns responses in sequence."""
    it = iter(responses)
    return MockLLM(lambda prompt, **kw: next(it))


CLUSTER = [
    _note("z20240101-001", "Testing Effect", "Retrieval practice beats re-reading."),
    _note("z20240101-002", "Spaced Repetition", "Distributed practice improves retention."),
]


def _large_note(id_: str, title: str) -> ZettelNote:
    """A note whose body exceeds NOTE_BODY_LARGE."""
    body = ("Retrieval practice beats re-reading. " * 300)[:NOTE_BODY_LARGE + 500]
    return _note(id_, title, body)


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


def test_integrate_phase_returns_integration_result():
    llm = _seq_llm(
        '{"operation": "CREATE", "target_note_ids": [], "reasoning": "New topic.", "confidence": 0.9}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert isinstance(result, IntegrationResult)


# ---------------------------------------------------------------------------
# Operation: CREATE
# ---------------------------------------------------------------------------


def test_integrate_create_operation():
    llm = _seq_llm(
        '{"operation": "CREATE", "target_note_ids": [], "reasoning": "New topic.", "confidence": 0.9}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.operation == "CREATE"


def test_integrate_create_populates_title_and_body():
    llm = _seq_llm(
        '{"operation": "CREATE", "target_note_ids": [], "reasoning": "New.", "confidence": 0.9}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.note_title == "Testing Effect"
    assert "Active retrieval" in result.note_body


def test_integrate_create_is_not_curation():
    llm = _seq_llm(
        '{"operation": "CREATE", "target_note_ids": [], "reasoning": ".", "confidence": 0.9}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.is_curation is False


# ---------------------------------------------------------------------------
# Operation: UPDATE
# ---------------------------------------------------------------------------


def test_integrate_update_operation():
    llm = _seq_llm(
        '{"operation": "UPDATE", "target_note_ids": ["z20240101-001"], "reasoning": "Adds to.", "confidence": 0.85}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.operation == "UPDATE"
    assert result.target_ids == ["z20240101-001"]


def test_integrate_update_populates_note_content():
    llm = _seq_llm(
        '{"operation": "UPDATE", "target_note_ids": ["z20240101-001"], "reasoning": ".", "confidence": 0.85}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.note_title != ""
    assert result.note_body != ""


# ---------------------------------------------------------------------------
# Operation: STUB
# ---------------------------------------------------------------------------


def test_integrate_stub_operation():
    llm = _seq_llm(
        '{"operation": "STUB", "target_note_ids": [], "reasoning": "No neighbourhood.", "confidence": 0.6}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), [], llm)
    assert result.operation == "STUB"


# ---------------------------------------------------------------------------
# Operation: SYNTHESISE
# ---------------------------------------------------------------------------


def test_integrate_synthesise_operation():
    llm = _seq_llm(
        '{"operation": "SYNTHESISE", "target_note_ids": ["z20240101-001", "z20240101-002"], "reasoning": "Bridges.", "confidence": 0.8}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.operation == "SYNTHESISE"
    assert len(result.target_ids) == 2


def test_integrate_synthesise_is_not_curation():
    llm = _seq_llm(
        '{"operation": "SYNTHESISE", "target_note_ids": ["z20240101-001", "z20240101-002"], "reasoning": ".", "confidence": 0.8}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.is_curation is False


# ---------------------------------------------------------------------------
# Operation: NOTHING
# ---------------------------------------------------------------------------


def test_integrate_nothing_operation():
    llm = _seq_llm(
        '{"operation": "NOTHING", "target_note_ids": [], "reasoning": "Already covered.", "confidence": 0.95}',
    )
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.operation == "NOTHING"


def test_integrate_nothing_has_empty_note_content():
    llm = _seq_llm(
        '{"operation": "NOTHING", "target_note_ids": [], "reasoning": ".", "confidence": 0.95}',
    )
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.note_title == ""
    assert result.note_body == ""


def test_integrate_nothing_is_not_curation():
    llm = _seq_llm(
        '{"operation": "NOTHING", "target_note_ids": [], "reasoning": ".", "confidence": 0.95}',
    )
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.is_curation is False


# ---------------------------------------------------------------------------
# SPLIT — executed at ingestion time
# ---------------------------------------------------------------------------


def test_integrate_split_executes():
    split_response = (
        "## Testing Effect\n\nActive retrieval strengthens memory."
        "\n\n---SPLIT---\n\n"
        "## Spaced Repetition\n\nDistributed practice improves retention."
    )
    llm = _seq_llm(
        '{"operation": "SPLIT", "target_note_ids": ["z20240101-001"], "reasoning": "Two topics.", "confidence": 0.85}',
        split_response,
    )
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.operation == "SPLIT"
    assert result.note_title != ""
    assert result.split_title != ""
    assert result.split_body != ""


# ---------------------------------------------------------------------------
# IntegrationResult fields
# ---------------------------------------------------------------------------


def test_integrate_result_has_reasoning():
    llm = _seq_llm(
        '{"operation": "CREATE", "target_note_ids": [], "reasoning": "Brand new topic.", "confidence": 0.9}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert "new topic" in result.reasoning.lower()


def test_integrate_result_has_confidence():
    llm = _seq_llm(
        '{"operation": "CREATE", "target_note_ids": [], "reasoning": ".", "confidence": 0.9}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert abs(result.confidence - 0.9) < 0.01


# ---------------------------------------------------------------------------
# max_tokens selection (verified via a capturing MockLLM)
# ---------------------------------------------------------------------------


def test_integrate_step1_uses_low_max_tokens():
    """Step 1 is classification-only — max_tokens should be ≤ 1024."""
    calls: list[dict] = []

    def capture(prompt, **kw):
        calls.append(kw)
        if len(calls) == 1:
            return '{"operation": "CREATE", "target_note_ids": [], "reasoning": ".", "confidence": 0.9}'
        return _STEP2_BODY

    result = integrate_phase(_draft(), CLUSTER, MockLLM(capture))
    assert calls[0]["max_tokens"] <= 1024


def test_integrate_step2_update_uses_high_max_tokens():
    """UPDATE step 2 rewrites existing notes — max_tokens should be ≥ 2048."""
    calls: list[dict] = []

    def capture(prompt, **kw):
        calls.append(kw)
        if len(calls) == 1:
            return '{"operation": "UPDATE", "target_note_ids": ["z20240101-001"], "reasoning": ".", "confidence": 0.85}'
        return _STEP2_BODY

    result = integrate_phase(_draft(), CLUSTER, MockLLM(capture))
    assert calls[1]["max_tokens"] >= 2048


def test_integrate_step2_stub_uses_lower_max_tokens():
    """STUB step 2 creates a brief note — max_tokens should be < 4096."""
    calls: list[dict] = []

    def capture(prompt, **kw):
        calls.append(kw)
        if len(calls) == 1:
            return '{"operation": "STUB", "target_note_ids": [], "reasoning": ".", "confidence": 0.6}'
        return _STEP2_BODY

    result = integrate_phase(_draft(), [], MockLLM(capture))
    assert calls[1]["max_tokens"] <= 2048


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def test_integrate_logs_start_and_complete(caplog):
    llm = _seq_llm(
        '{"operation": "CREATE", "target_note_ids": [], "reasoning": ".", "confidence": 0.9}',
        _STEP2_BODY,
    )
    with caplog.at_level(logging.INFO, logger="zettelkasten"):
        integrate_phase(_draft(), CLUSTER, llm)

    messages = [r.message for r in caplog.records]
    assert any("integrate.start" in m for m in messages)
    assert any("integrate.complete" in m for m in messages)


def test_integrate_logs_step1_decision(caplog):
    llm = _seq_llm(
        '{"operation": "UPDATE", "target_note_ids": ["z20240101-001"], "reasoning": ".", "confidence": 0.85}',
        _STEP2_BODY,
    )
    with caplog.at_level(logging.INFO, logger="zettelkasten"):
        integrate_phase(_draft(), CLUSTER, llm)

    messages = [r.message for r in caplog.records]
    assert any("integrate.step1" in m for m in messages)


def test_integrate_logs_step2(caplog):
    llm = _seq_llm(
        '{"operation": "CREATE", "target_note_ids": [], "reasoning": ".", "confidence": 0.9}',
        _STEP2_BODY,
    )
    with caplog.at_level(logging.DEBUG, logger="zettelkasten"):
        integrate_phase(_draft(), CLUSTER, llm)

    messages = [r.message for r in caplog.records]
    assert any("integrate.step2" in m for m in messages)


# ---------------------------------------------------------------------------
# Step 1.5 — EDIT/SPLIT refinement for large notes
# ---------------------------------------------------------------------------


def test_integrate_edit_operation_via_step15():
    """UPDATE on a LARGE note → step 1.5 returns EDIT → result is EDIT."""
    large = _large_note("z20240101-001", "Large Note")
    llm = _seq_llm(
        '{"operation": "UPDATE", "target_note_ids": ["z20240101-001"], "reasoning": "Adds to.", "confidence": 0.85}',
        '{"operation": "EDIT", "reasoning": "Note is verbose.", "confidence": 0.9}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), [large], llm)
    assert result.operation == "EDIT"


def test_integrate_split_via_step15():
    """UPDATE on a LARGE note → step 1.5 returns SPLIT → result is SPLIT."""
    large = _large_note("z20240101-001", "Large Note")
    split_response = (
        "## Part One\n\nActive retrieval strengthens memory."
        "\n\n---SPLIT---\n\n"
        "## Part Two\n\nDistributed practice improves retention."
    )
    llm = _seq_llm(
        '{"operation": "UPDATE", "target_note_ids": ["z20240101-001"], "reasoning": ".", "confidence": 0.85}',
        '{"operation": "SPLIT", "reasoning": "Two distinct topics.", "confidence": 0.9}',
        split_response,
    )
    result = integrate_phase(_draft(), [large], llm)
    assert result.operation == "SPLIT"
    assert result.split_title != ""


def test_integrate_step15_not_called_for_normal_notes():
    """UPDATE on a normal-sized note uses exactly 2 LLM calls — no step 1.5."""
    calls: list = []

    def capture(prompt, **kw):
        calls.append(prompt)
        if len(calls) == 1:
            return '{"operation": "UPDATE", "target_note_ids": ["z20240101-001"], "reasoning": ".", "confidence": 0.85}'
        return _STEP2_BODY

    integrate_phase(_draft(), CLUSTER, MockLLM(capture))
    assert len(calls) == 2


def test_integrate_step15_called_for_large_update():
    """UPDATE on a LARGE note triggers a third LLM call (step 1.5)."""
    large = _large_note("z20240101-001", "Large Note")
    calls: list = []

    def capture(prompt, **kw):
        calls.append(prompt)
        if len(calls) == 1:
            return '{"operation": "UPDATE", "target_note_ids": ["z20240101-001"], "reasoning": ".", "confidence": 0.85}'
        if len(calls) == 2:
            return '{"operation": "EDIT", "reasoning": "Verbose.", "confidence": 0.9}'
        return _STEP2_BODY

    integrate_phase(_draft(), [large], MockLLM(capture))
    assert len(calls) == 3


def test_integrate_edit_populates_note_content():
    """EDIT result has a non-empty title and body."""
    large = _large_note("z20240101-001", "Large Note")
    llm = _seq_llm(
        '{"operation": "UPDATE", "target_note_ids": ["z20240101-001"], "reasoning": ".", "confidence": 0.85}',
        '{"operation": "EDIT", "reasoning": "Verbose.", "confidence": 0.9}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), [large], llm)
    assert result.note_title != ""
    assert result.note_body != ""


def test_integrate_edit_uses_lower_max_tokens():
    """EDIT step 2 uses 2048 max_tokens — reductive, not expansive."""
    large = _large_note("z20240101-001", "Large Note")
    calls: list[dict] = []

    def capture(prompt, **kw):
        calls.append(kw)
        if len(calls) == 1:
            return '{"operation": "UPDATE", "target_note_ids": ["z20240101-001"], "reasoning": ".", "confidence": 0.85}'
        if len(calls) == 2:
            return '{"operation": "EDIT", "reasoning": "Verbose.", "confidence": 0.9}'
        return _STEP2_BODY

    integrate_phase(_draft(), [large], MockLLM(capture))
    assert calls[2]["max_tokens"] == 2048


def test_integrate_logs_step15(caplog):
    """Step 1.5 fires an integrate.step1_5 log entry."""
    large = _large_note("z20240101-001", "Large Note")
    llm = _seq_llm(
        '{"operation": "UPDATE", "target_note_ids": ["z20240101-001"], "reasoning": ".", "confidence": 0.85}',
        '{"operation": "EDIT", "reasoning": "Verbose.", "confidence": 0.9}',
        _STEP2_BODY,
    )
    with caplog.at_level(logging.INFO, logger="zettelkasten"):
        integrate_phase(_draft(), [large], llm)

    messages = [r.message for r in caplog.records]
    assert any("integrate.step1_5" in m for m in messages)


def test_integrate_step15_invalid_response_defaults_to_edit():
    """Unparseable step 1.5 response falls back to EDIT rather than crashing."""
    large = _large_note("z20240101-001", "Large Note")
    llm = _seq_llm(
        '{"operation": "UPDATE", "target_note_ids": ["z20240101-001"], "reasoning": ".", "confidence": 0.85}',
        "not valid json at all",
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), [large], llm)
    assert result.operation == "EDIT"
