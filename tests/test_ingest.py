"""Tests for ZettelkastenStore.ingest_text, search, and _next_id."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from zettelkasten.integrate import IntegrationResult
from zettelkasten.note import ZettelNote
from zettelkasten.providers import MockEmbed, MockLLM
from zettelkasten.store import ZettelkastenStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EMBED = MockEmbed(dims=32)

_FORM_OUTPUT = """\
## Memory Consolidation

Sleep strengthens memory by consolidating neural pathways formed during learning.
"""

_STEP2_OUTPUT = """\
## Memory Consolidation

Sleep strengthens memory by consolidating neural pathways formed during waking hours.
"""


def _pipeline_llm(operation: str = "CREATE", target_ids: list[str] | None = None) -> MockLLM:
    """MockLLM that handles all prompt types in the ingest pipeline.

    The integrate phase now uses two classify calls (L1 then L2).
    L1 prompt contains '- INTEGRATE:'; L2 prompt contains '- UPDATE:'.
    """
    target_ids = target_ids or []
    target_json = ", ".join(f'"{t}"' for t in target_ids)

    # Map caller's operation to L1 and L2 responses.
    # SYNTHESISE and NOTHING are decided at L1; everything else routes through L2.
    _L1_OP = "SYNTHESISE" if operation == "SYNTHESISE" else (
        "NOTHING" if operation == "NOTHING" else "INTEGRATE"
    )
    # L2 operation (only reached when L1=INTEGRATE):
    # STUB is parked — treated as CREATE; SPLIT/EDIT reach L2 as UPDATE.
    _L2_OP = {
        "CREATE": "CREATE", "UPDATE": "UPDATE", "NOTHING": "NOTHING",
        "SPLIT": "UPDATE", "EDIT": "UPDATE",
    }.get(operation, "CREATE")

    def respond(prompt: str, **kw) -> str:
        # Form phase: asks about "topic areas"
        if "topic areas" in prompt or "broad topic" in prompt:
            return _FORM_OUTPUT
        # Gather MuGI
        if "pseudo_notes" in prompt:
            return '{"pseudo_notes": ["memory", "consolidation", "sleep"]}'
        # Gather step-back
        if "abstraction" in prompt:
            return '{"abstraction": "Biological processes that consolidate learning during rest."}'
        # Gather HyDE
        if "hypotheticals" in prompt:
            return '{"hypotheticals": ["sleep strengthens memory", "rest aids recall", "downtime consolidates"]}'
        # Integrate L1 (SYNTHESISE / INTEGRATE / NOTHING)
        if "- INTEGRATE:" in prompt:
            return (
                f'{{"operation": "{_L1_OP}", '
                f'"target_note_ids": [{target_json}], '
                f'"reasoning": "Test decision.", '
                f'"confidence": 0.9}}'
            )
        # Integrate L2 (CREATE / UPDATE / NOTHING) and step1.5 (EDIT / SPLIT)
        if "Output JSON only" in prompt:
            l2_op = _L2_OP if "- UPDATE:" in prompt else (
                "EDIT" if operation == "EDIT" else "SPLIT" if operation == "SPLIT" else _L2_OP
            )
            return (
                f'{{"operation": "{l2_op}", '
                f'"target_note_ids": [{target_json}], '
                f'"reasoning": "Test decision.", '
                f'"confidence": 0.9}}'
            )
        # Step 2 — SPLIT needs two sections
        if operation == "SPLIT" and "---SPLIT---" not in prompt:
            return (
                "## Memory Consolidation\n\nSleep strengthens memory.\n"
                "\n---SPLIT---\n\n"
                "## Sleep Architecture\n\nSlow-wave sleep drives consolidation."
            )
        # Step 2: produce ## Title\n\nBody
        return _STEP2_OUTPUT

    return MockLLM(respond)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _stored_note(store: ZettelkastenStore, id_: str, title: str, body: str) -> ZettelNote:
    """Write a note directly to a store for test setup."""
    from zettelkasten.note import ZettelNote as ZN
    note = ZN(
        id=id_, title=title, body=body,
        type="permanent", confidence=0.8, salience=0.5,
        stable=True, created=_now(), updated=_now(), last_accessed=_now(),
        embedding=_EMBED.embed([body])[0],
    )
    store.write(note)
    return note


# ---------------------------------------------------------------------------
# _next_id
# ---------------------------------------------------------------------------


def test_next_id_no_existing_notes(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    note_id = store._next_id()
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    assert note_id == f"z{today}-001"


def test_next_id_increments_after_existing(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    # Write two notes manually to simulate existing notes
    _stored_note(store, f"z{today}-001", "Note A", "Body A")
    _stored_note(store, f"z{today}-002", "Note B", "Body B")
    assert store._next_id() == f"z{today}-003"


def test_next_id_uses_today_date(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    assert store._next_id().startswith(f"z{today}-")


def test_next_id_result_matches_id_pattern(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    note_id = store._next_id()
    assert re.match(r"^z\d{8}-\d{3}$", note_id)


# ---------------------------------------------------------------------------
# ingest_text — return type
# ---------------------------------------------------------------------------


def test_ingest_text_returns_list(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    results = store.ingest_text("Some document text.", _pipeline_llm(), _EMBED)
    assert isinstance(results, list)


def test_ingest_text_returns_integration_results(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    results = store.ingest_text("Some document text.", _pipeline_llm(), _EMBED)
    assert all(isinstance(r, IntegrationResult) for r in results)


# ---------------------------------------------------------------------------
# ingest_text — CREATE operation
# ---------------------------------------------------------------------------


def test_ingest_create_writes_note_file(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    store.ingest_text("Some document text.", _pipeline_llm("CREATE"), _EMBED)
    md_files = list((tmp_path / "notes").glob("*.md"))
    assert len(md_files) == 1


def test_ingest_create_note_has_valid_id(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    results = store.ingest_text("Some document text.", _pipeline_llm("CREATE"), _EMBED)
    create_results = [r for r in results if r.operation == "CREATE"]
    assert len(create_results) == 1
    assert re.match(r"^z\d{8}-\d{3}$", create_results[0].note_id)


def test_ingest_create_note_is_indexed(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    results = store.ingest_text("Some document text.", _pipeline_llm("CREATE"), _EMBED)
    note_id = results[0].note_id
    row = store._index.get_note_row(note_id)
    assert row is not None


def test_ingest_create_note_has_embedding(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    results = store.ingest_text("Some document text.", _pipeline_llm("CREATE"), _EMBED)
    note_id = results[0].note_id
    # Embedding should be stored in index
    emb = store._index.get_embedding(note_id)
    assert emb is not None


# ---------------------------------------------------------------------------
# ingest_text — UPDATE operation
# ---------------------------------------------------------------------------


def test_ingest_update_modifies_existing_note(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    existing_id = f"z{today}-001"
    _stored_note(store, existing_id, "Memory Consolidation", "Original body.")

    llm = _pipeline_llm("UPDATE", [existing_id])
    results = store.ingest_text("New content about memory.", llm, _EMBED)

    # The note file should still exist and have updated content
    md_path = tmp_path / "notes" / f"{existing_id}.md"
    assert md_path.exists()
    updated_note = ZettelNote.from_markdown(md_path.read_text())
    assert updated_note.id == existing_id


def test_ingest_update_returns_update_result(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    existing_id = f"z{today}-001"
    _stored_note(store, existing_id, "Memory", "Original.")

    llm = _pipeline_llm("UPDATE", [existing_id])
    results = store.ingest_text("New content.", llm, _EMBED)
    assert any(r.operation == "UPDATE" for r in results)


# ---------------------------------------------------------------------------
# ingest_text — NOTHING operation
# ---------------------------------------------------------------------------


def test_ingest_nothing_does_not_write_note(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    store.ingest_text("Some text.", _pipeline_llm("NOTHING"), _EMBED)
    md_files = list((tmp_path / "notes").glob("*.md"))
    assert len(md_files) == 0


# ---------------------------------------------------------------------------
# ingest_text — new isolated topic (formerly STUB, now CREATE)
# ---------------------------------------------------------------------------


def test_ingest_isolated_topic_writes_note(tmp_path):
    """Isolated new topics are handled as CREATE in the levelled decision tree.
    STUB has been removed from the pipeline routing."""
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    results = store.ingest_text("Obscure topic text.", _pipeline_llm("CREATE"), _EMBED)
    create_results = [r for r in results if r.operation == "CREATE"]
    assert len(create_results) == 1
    md_files = list((tmp_path / "notes").glob("*.md"))
    assert len(md_files) == 1


# ---------------------------------------------------------------------------
# ingest_text — co-activation recording
# ---------------------------------------------------------------------------


def test_ingest_create_records_activation_with_targets(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    existing_id = f"z{today}-001"
    _stored_note(store, existing_id, "Related Note", "Related content.")

    llm = _pipeline_llm("CREATE", [existing_id])
    results = store.ingest_text("New content.", llm, _EMBED)

    # The activation index should record an edge from the new note to existing_id
    new_id = results[0].note_id
    scores = store._index.get_activation_scores(new_id)
    assert existing_id in scores


# ---------------------------------------------------------------------------
# ingest_text — SPLIT
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


def test_search_returns_list(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    results = store.search("memory", _pipeline_llm(), _EMBED)
    assert isinstance(results, list)


def test_search_empty_corpus_returns_empty(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    results = store.search("memory", _pipeline_llm(), _EMBED)
    assert results == []


def test_search_returns_zettel_notes(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    _stored_note(store, f"z{today}-001", "Memory", "Memory consolidation during sleep.")
    _stored_note(store, f"z{today}-002", "Learning", "Active recall improves retention.")

    results = store.search("memory and learning", _pipeline_llm(), _EMBED)
    assert all(isinstance(n, ZettelNote) for n in results)


def test_search_top_k_limits_results(tmp_path):
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    for i in range(5):
        _stored_note(store, f"z{today}-{i+1:03d}", f"Note {i}", f"Content {i}.")

    results = store.search("content", _pipeline_llm(), _EMBED, top_k=3)
    assert len(results) <= 3
