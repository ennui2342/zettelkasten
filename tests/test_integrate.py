"""Tests for the Integrate phase: levelled LLM classification + execution.

Decision tree:
  L1 classify  → SYNTHESISE → execute SYNTHESISE
               → NOTHING    → exit
               → INTEGRATE  → L2 classify → CREATE  → execute CREATE
                                          → NOTHING → exit
                                          → UPDATE  → (large?) → L3 → execute EDIT/SPLIT
                                                               → execute UPDATE
"""
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

_L1_INTEGRATE = '{"operation": "INTEGRATE", "target_note_ids": ["z20240101-001"], "reasoning": ".", "confidence": 0.9}'
_L1_INTEGRATE_BOTH = '{"operation": "INTEGRATE", "target_note_ids": ["z20240101-001", "z20240101-002"], "reasoning": ".", "confidence": 0.9}'
_L1_INTEGRATE_NONE = '{"operation": "INTEGRATE", "target_note_ids": [], "reasoning": ".", "confidence": 0.9}'
_L1_SYNTHESISE = '{"operation": "SYNTHESISE", "target_note_ids": ["z20240101-001", "z20240101-002"], "reasoning": "Bridges.", "confidence": 0.8}'
_L1_NOTHING = '{"operation": "NOTHING", "target_note_ids": [], "reasoning": "Already covered.", "confidence": 0.95}'

_L2_CREATE = '{"operation": "CREATE", "target_note_ids": [], "reasoning": "New topic.", "confidence": 0.9}'
_L2_UPDATE = '{"operation": "UPDATE", "target_note_ids": ["z20240101-001"], "reasoning": "Adds to.", "confidence": 0.85}'
_L2_NOTHING = '{"operation": "NOTHING", "target_note_ids": ["z20240101-001"], "reasoning": "Already covered.", "confidence": 0.95}'


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
    llm = _seq_llm(_L1_INTEGRATE_NONE, _L2_CREATE, _STEP2_BODY)
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert isinstance(result, IntegrationResult)


# ---------------------------------------------------------------------------
# Operation: CREATE  (L1→INTEGRATE, L2→CREATE, execute)
# ---------------------------------------------------------------------------


def test_integrate_create_operation():
    llm = _seq_llm(_L1_INTEGRATE_NONE, _L2_CREATE, _STEP2_BODY)
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.operation == "CREATE"


def test_integrate_create_populates_title_and_body():
    llm = _seq_llm(_L1_INTEGRATE_NONE, _L2_CREATE, _STEP2_BODY)
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.note_title == "Testing Effect"
    assert "Active retrieval" in result.note_body



# ---------------------------------------------------------------------------
# Operation: UPDATE  (L1→INTEGRATE, L2→UPDATE, execute)
# ---------------------------------------------------------------------------


def test_integrate_update_operation():
    llm = _seq_llm(_L1_INTEGRATE, _L2_UPDATE, _STEP2_BODY)
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.operation == "UPDATE"
    assert result.target_ids == ["z20240101-001"]


def test_integrate_update_populates_note_content():
    llm = _seq_llm(_L1_INTEGRATE, _L2_UPDATE, _STEP2_BODY)
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.note_title != ""
    assert result.note_body != ""


# ---------------------------------------------------------------------------
# Operation: SYNTHESISE  (L1→SYNTHESISE, execute — no L2 call)
# ---------------------------------------------------------------------------


def test_integrate_synthesise_operation():
    llm = _seq_llm(_L1_SYNTHESISE, _STEP2_BODY)
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.operation == "SYNTHESISE"
    assert len(result.target_ids) == 2



# ---------------------------------------------------------------------------
# Operation: NOTHING  (L1→NOTHING or L2→NOTHING)
# ---------------------------------------------------------------------------


def test_integrate_nothing_at_l1():
    llm = _seq_llm(_L1_NOTHING)
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.operation == "NOTHING"


def test_integrate_nothing_at_l2():
    llm = _seq_llm(_L1_INTEGRATE, _L2_NOTHING)
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.operation == "NOTHING"


def test_integrate_nothing_has_empty_note_content():
    llm = _seq_llm(_L1_NOTHING)
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.note_title == ""
    assert result.note_body == ""



# ---------------------------------------------------------------------------
# SPLIT — via L1→INTEGRATE, L2→UPDATE (large), L3→SPLIT, execute
# ---------------------------------------------------------------------------


def test_integrate_split_executes():
    large = _large_note("z20240101-001", "Large Note")
    split_response = (
        "## Testing Effect\n\nActive retrieval strengthens memory."
        "\n\n---SPLIT---\n\n"
        "## Spaced Repetition\n\nDistributed practice improves retention."
    )
    llm = _seq_llm(
        _L1_INTEGRATE,
        _L2_UPDATE,
        '{"operation": "SPLIT", "reasoning": "Two topics.", "confidence": 0.85}',
        split_response,
    )
    result = integrate_phase(_draft(), [large], llm)
    assert result.operation == "SPLIT"
    assert result.note_title != ""
    assert result.split_title != ""
    assert result.split_body != ""


# ---------------------------------------------------------------------------
# IntegrationResult fields
# ---------------------------------------------------------------------------


def test_integrate_result_has_reasoning():
    llm = _seq_llm(
        '{"operation": "INTEGRATE", "target_note_ids": [], "reasoning": ".", "confidence": 0.9}',
        '{"operation": "CREATE", "target_note_ids": [], "reasoning": "Brand new topic.", "confidence": 0.9}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.reasoning != ""


def test_integrate_result_has_confidence():
    llm = _seq_llm(
        '{"operation": "INTEGRATE", "target_note_ids": [], "reasoning": ".", "confidence": 0.9}',
        '{"operation": "CREATE", "target_note_ids": [], "reasoning": ".", "confidence": 0.77}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.confidence > 0.0


# ---------------------------------------------------------------------------
# Two-level classification: call counts
# ---------------------------------------------------------------------------


def test_integrate_create_makes_three_llm_calls():
    """CREATE path: L1 INTEGRATE → L2 CREATE → execute = 3 calls."""
    calls: list = []

    def capture(prompt, **kw):
        calls.append(prompt)
        if len(calls) == 1:
            return _L1_INTEGRATE_NONE
        if len(calls) == 2:
            return _L2_CREATE
        return _STEP2_BODY

    integrate_phase(_draft(), CLUSTER, MockLLM(capture))
    assert len(calls) == 3


def test_integrate_update_makes_three_llm_calls():
    """UPDATE path: L1 INTEGRATE → L2 UPDATE → execute = 3 calls."""
    calls: list = []

    def capture(prompt, **kw):
        calls.append(prompt)
        if len(calls) == 1:
            return _L1_INTEGRATE
        if len(calls) == 2:
            return _L2_UPDATE
        return _STEP2_BODY

    integrate_phase(_draft(), CLUSTER, MockLLM(capture))
    assert len(calls) == 3


def test_integrate_synthesise_skips_l2():
    """SYNTHESISE path: L1 SYNTHESISE → execute directly = 2 calls (no L2)."""
    calls: list = []

    def capture(prompt, **kw):
        calls.append(prompt)
        if len(calls) == 1:
            return _L1_SYNTHESISE
        return _STEP2_BODY

    result = integrate_phase(_draft(), CLUSTER, MockLLM(capture))
    assert len(calls) == 2
    assert result.operation == "SYNTHESISE"


def test_integrate_nothing_at_l1_makes_one_call():
    """NOTHING at L1: no L2, no execute = 1 call."""
    calls: list = []

    def capture(prompt, **kw):
        calls.append(prompt)
        return _L1_NOTHING

    result = integrate_phase(_draft(), CLUSTER, MockLLM(capture))
    assert len(calls) == 1
    assert result.operation == "NOTHING"


def test_integrate_nothing_at_l2_makes_two_calls():
    """NOTHING at L2: L1 INTEGRATE → L2 NOTHING → exit = 2 calls."""
    calls: list = []

    def capture(prompt, **kw):
        calls.append(prompt)
        if len(calls) == 1:
            return _L1_INTEGRATE
        return _L2_NOTHING

    result = integrate_phase(_draft(), CLUSTER, MockLLM(capture))
    assert len(calls) == 2
    assert result.operation == "NOTHING"


def test_integrate_large_update_makes_four_calls():
    """Large UPDATE path: L1 → L2 → L3 → execute = 4 calls."""
    large = _large_note("z20240101-001", "Large Note")
    calls: list = []

    def capture(prompt, **kw):
        calls.append(prompt)
        if len(calls) == 1:
            return _L1_INTEGRATE
        if len(calls) == 2:
            return _L2_UPDATE
        if len(calls) == 3:
            return '{"operation": "EDIT", "reasoning": "Verbose.", "confidence": 0.9}'
        return _STEP2_BODY

    result = integrate_phase(_draft(), [large], MockLLM(capture))
    assert len(calls) == 4
    assert result.operation == "EDIT"


# ---------------------------------------------------------------------------
# L2 receives filtered cluster
# ---------------------------------------------------------------------------


def test_integrate_l2_receives_filtered_cluster():
    """L2 prompt contains only the notes from L1's target_note_ids."""
    prompts: list[str] = []

    def capture(prompt, **kw):
        prompts.append(prompt)
        if len(prompts) == 1:
            # L1: target only note 001
            return _L1_INTEGRATE  # targets ["z20240101-001"]
        if len(prompts) == 2:
            return _L2_CREATE
        return _STEP2_BODY

    integrate_phase(_draft(), CLUSTER, MockLLM(capture))

    l2_prompt = prompts[1]
    assert "z20240101-001" in l2_prompt      # targeted note is present
    assert "z20240101-002" not in l2_prompt  # non-targeted note excluded


# ---------------------------------------------------------------------------
# max_tokens selection
# ---------------------------------------------------------------------------


def test_integrate_l1_uses_low_max_tokens():
    """L1 is classification-only — max_tokens should be ≤ 1024."""
    calls: list[dict] = []

    def capture(prompt, **kw):
        calls.append(kw)
        if len(calls) == 1:
            return _L1_INTEGRATE_NONE
        if len(calls) == 2:
            return _L2_CREATE
        return _STEP2_BODY

    integrate_phase(_draft(), CLUSTER, MockLLM(capture))
    assert calls[0]["max_tokens"] <= 1024


def test_integrate_l2_uses_low_max_tokens():
    """L2 is classification-only — max_tokens should be ≤ 1024."""
    calls: list[dict] = []

    def capture(prompt, **kw):
        calls.append(kw)
        if len(calls) == 1:
            return _L1_INTEGRATE_NONE
        if len(calls) == 2:
            return _L2_CREATE
        return _STEP2_BODY

    integrate_phase(_draft(), CLUSTER, MockLLM(capture))
    assert calls[1]["max_tokens"] <= 1024


def test_integrate_step2_update_uses_high_max_tokens():
    """UPDATE execute (3rd call) should use ≥ 2048 max_tokens."""
    calls: list[dict] = []

    def capture(prompt, **kw):
        calls.append(kw)
        if len(calls) == 1:
            return _L1_INTEGRATE
        if len(calls) == 2:
            return _L2_UPDATE
        return _STEP2_BODY

    integrate_phase(_draft(), CLUSTER, MockLLM(capture))
    assert calls[2]["max_tokens"] >= 2048


def test_integrate_edit_uses_lower_max_tokens():
    """EDIT execute (4th call for large UPDATE) uses 2048 max_tokens."""
    large = _large_note("z20240101-001", "Large Note")
    calls: list[dict] = []

    def capture(prompt, **kw):
        calls.append(kw)
        if len(calls) == 1:
            return _L1_INTEGRATE
        if len(calls) == 2:
            return _L2_UPDATE
        if len(calls) == 3:
            return '{"operation": "EDIT", "reasoning": "Verbose.", "confidence": 0.9}'
        return _STEP2_BODY

    integrate_phase(_draft(), [large], MockLLM(capture))
    assert calls[3]["max_tokens"] == 2048


# ---------------------------------------------------------------------------
# L3 — EDIT/SPLIT refinement for large notes
# ---------------------------------------------------------------------------


def test_integrate_edit_operation_via_l3():
    """UPDATE on a LARGE note → L3 EDIT → result is EDIT."""
    large = _large_note("z20240101-001", "Large Note")
    llm = _seq_llm(
        _L1_INTEGRATE,
        _L2_UPDATE,
        '{"operation": "EDIT", "reasoning": "Note is verbose.", "confidence": 0.9}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), [large], llm)
    assert result.operation == "EDIT"


def test_integrate_split_via_l3():
    """UPDATE on a LARGE note → L3 SPLIT → result is SPLIT."""
    large = _large_note("z20240101-001", "Large Note")
    split_response = (
        "## Part One\n\nActive retrieval strengthens memory."
        "\n\n---SPLIT---\n\n"
        "## Part Two\n\nDistributed practice improves retention."
    )
    llm = _seq_llm(
        _L1_INTEGRATE,
        _L2_UPDATE,
        '{"operation": "SPLIT", "reasoning": "Two distinct topics.", "confidence": 0.9}',
        split_response,
    )
    result = integrate_phase(_draft(), [large], llm)
    assert result.operation == "SPLIT"
    assert result.split_title != ""


def test_integrate_l3_not_called_for_normal_notes():
    """UPDATE on a normal-sized note: exactly 3 LLM calls — no L3."""
    calls: list = []

    def capture(prompt, **kw):
        calls.append(prompt)
        if len(calls) == 1:
            return _L1_INTEGRATE
        if len(calls) == 2:
            return _L2_UPDATE
        return _STEP2_BODY

    integrate_phase(_draft(), CLUSTER, MockLLM(capture))
    assert len(calls) == 3


def test_integrate_step15_called_for_large_update():
    """UPDATE on a LARGE note triggers a 4th LLM call (L3)."""
    large = _large_note("z20240101-001", "Large Note")
    calls: list = []

    def capture(prompt, **kw):
        calls.append(prompt)
        if len(calls) == 1:
            return _L1_INTEGRATE
        if len(calls) == 2:
            return _L2_UPDATE
        if len(calls) == 3:
            return '{"operation": "EDIT", "reasoning": "Verbose.", "confidence": 0.9}'
        return _STEP2_BODY

    integrate_phase(_draft(), [large], MockLLM(capture))
    assert len(calls) == 4


def test_integrate_edit_populates_note_content():
    """EDIT result has a non-empty title and body."""
    large = _large_note("z20240101-001", "Large Note")
    llm = _seq_llm(
        _L1_INTEGRATE,
        _L2_UPDATE,
        '{"operation": "EDIT", "reasoning": "Verbose.", "confidence": 0.9}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), [large], llm)
    assert result.note_title != ""
    assert result.note_body != ""


def test_integrate_l3_invalid_response_defaults_to_edit():
    """Unparseable L3 response falls back to EDIT."""
    large = _large_note("z20240101-001", "Large Note")
    llm = _seq_llm(
        _L1_INTEGRATE,
        _L2_UPDATE,
        "not valid json at all",
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), [large], llm)
    assert result.operation == "EDIT"


# ---------------------------------------------------------------------------
# l1_target_ids — L1 cluster carried through result
# ---------------------------------------------------------------------------


def test_integrate_create_carries_l1_target_ids():
    """CREATE result carries L1's target_note_ids as l1_target_ids."""
    llm = _seq_llm(_L1_INTEGRATE, _L2_CREATE, _STEP2_BODY)
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.l1_target_ids == ["z20240101-001"]


def test_integrate_update_carries_l1_target_ids():
    """UPDATE result carries L1's target_note_ids as l1_target_ids."""
    llm = _seq_llm(_L1_INTEGRATE_BOTH, _L2_UPDATE, _STEP2_BODY)
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert "z20240101-001" in result.l1_target_ids
    assert "z20240101-002" in result.l1_target_ids


def test_integrate_edit_carries_l1_target_ids():
    """EDIT result carries L1's target_note_ids as l1_target_ids."""
    large = _large_note("z20240101-001", "Large Note")
    llm = _seq_llm(
        _L1_INTEGRATE_BOTH,
        _L2_UPDATE,
        '{"operation": "EDIT", "reasoning": "Verbose.", "confidence": 0.9}',
        _STEP2_BODY,
    )
    result = integrate_phase(_draft(), [large, CLUSTER[1]], llm)
    assert "z20240101-001" in result.l1_target_ids
    assert "z20240101-002" in result.l1_target_ids


def test_integrate_synthesise_l1_target_ids_matches_target_ids():
    """SYNTHESISE result: l1_target_ids matches target_ids (both come from L1)."""
    llm = _seq_llm(_L1_SYNTHESISE, _STEP2_BODY)
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.l1_target_ids == result.target_ids


def test_integrate_nothing_l1_target_ids_populated():
    """NOTHING result still carries L1's identified target_note_ids."""
    llm = _seq_llm('{"operation": "NOTHING", "target_note_ids": ["z20240101-001"], "reasoning": "covered", "confidence": 0.9}')
    result = integrate_phase(_draft(), CLUSTER, llm)
    assert result.l1_target_ids == ["z20240101-001"]


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def test_integrate_logs_start_and_complete(caplog):
    llm = _seq_llm(_L1_INTEGRATE_NONE, _L2_CREATE, _STEP2_BODY)
    with caplog.at_level(logging.INFO, logger="zettelkasten"):
        integrate_phase(_draft(), CLUSTER, llm)

    messages = [r.message for r in caplog.records]
    assert any("integrate.start" in m for m in messages)
    assert any("integrate.complete" in m for m in messages)


def test_integrate_logs_l1_decision(caplog):
    llm = _seq_llm(_L1_INTEGRATE, _L2_UPDATE, _STEP2_BODY)
    with caplog.at_level(logging.INFO, logger="zettelkasten"):
        integrate_phase(_draft(), CLUSTER, llm)

    messages = [r.message for r in caplog.records]
    assert any("integrate.l1" in m for m in messages)


def test_integrate_logs_l2_decision(caplog):
    llm = _seq_llm(_L1_INTEGRATE_NONE, _L2_CREATE, _STEP2_BODY)
    with caplog.at_level(logging.INFO, logger="zettelkasten"):
        integrate_phase(_draft(), CLUSTER, llm)

    messages = [r.message for r in caplog.records]
    assert any("integrate.l2" in m for m in messages)


def test_integrate_logs_complete_with_body_len(caplog):
    llm = _seq_llm(_L1_INTEGRATE_NONE, _L2_CREATE, _STEP2_BODY)
    with caplog.at_level(logging.INFO, logger="zettelkasten"):
        integrate_phase(_draft(), CLUSTER, llm)

    messages = [r.message for r in caplog.records]
    assert any("integrate.complete" in m and "body_len" in m for m in messages)


def test_integrate_logs_l3(caplog):
    large = _large_note("z20240101-001", "Large Note")
    llm = _seq_llm(
        _L1_INTEGRATE,
        _L2_UPDATE,
        '{"operation": "EDIT", "reasoning": "Verbose.", "confidence": 0.9}',
        _STEP2_BODY,
    )
    with caplog.at_level(logging.INFO, logger="zettelkasten"):
        integrate_phase(_draft(), [large], llm)

    messages = [r.message for r in caplog.records]
    assert any("integrate.l3" in m for m in messages)
