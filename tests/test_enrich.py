"""Tests for the enrich module: tool implementations and agentic query loop."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from zettelkasten.enrich import (
    _grep_notes,
    _list_notes,
    _read_note,
    query,
)
from zettelkasten.note import ZettelNote
from zettelkasten.providers import MockToolLLM, ToolCall


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_note(
    notes_dir: Path,
    note_id: str,
    title: str,
    body: str,
) -> ZettelNote:
    now = datetime.now(tz=timezone.utc)
    note = ZettelNote(
        id=note_id,
        title=title,
        body=body,
        type="permanent",
        confidence=0.9,
        salience=0.5,
        stable=False,
        created=now,
        updated=now,
        last_accessed=now,
    )
    (notes_dir / f"{note_id}.md").write_text(note.to_markdown(), encoding="utf-8")
    return note


@pytest.fixture()
def notes_dir(tmp_path: Path) -> Path:
    d = tmp_path / "notes"
    d.mkdir()
    _make_note(d, "z20260101-001", "Agent Memory Systems",
               "Memory in agents can be episodic or semantic.\n\nEpisodic stores past events.\n\n"
               "## See Also\n\n"
               "- [[z20260101-002|Multi-Agent Coordination]] — memory shapes coordination strategy")
    _make_note(d, "z20260101-002", "Multi-Agent Coordination",
               "Coordination between agents requires communication protocols.\n\n"
               "## See Also\n\n"
               "- [[z20260101-001|Agent Memory Systems]] — coordination depends on memory")
    _make_note(d, "z20260101-003", "Retrieval Augmented Generation",
               "RAG augments LLM responses with retrieved context from a corpus.")
    return d


# ---------------------------------------------------------------------------
# list_notes
# ---------------------------------------------------------------------------


def test_list_notes_returns_all(notes_dir: Path) -> None:
    result = _list_notes(notes_dir)
    assert "z20260101-001: Agent Memory Systems" in result
    assert "z20260101-002: Multi-Agent Coordination" in result
    assert "z20260101-003: Retrieval Augmented Generation" in result


def test_list_notes_empty_store(tmp_path: Path) -> None:
    d = tmp_path / "empty"
    d.mkdir()
    assert _list_notes(d) == "No notes in store"


# ---------------------------------------------------------------------------
# grep_notes
# ---------------------------------------------------------------------------


def test_grep_notes_finds_title_match(notes_dir: Path) -> None:
    result = _grep_notes("memory", notes_dir)
    assert "z20260101-001" in result
    assert "Agent Memory Systems" in result


def test_grep_notes_finds_body_match(notes_dir: Path) -> None:
    result = _grep_notes("episodic", notes_dir)
    assert "z20260101-001" in result
    assert "episodic" in result.lower()


def test_grep_notes_case_insensitive(notes_dir: Path) -> None:
    result = _grep_notes("RETRIEVAL", notes_dir)
    assert "z20260101-003" in result


def test_grep_notes_regex_alternation(notes_dir: Path) -> None:
    """LLMs naturally use | for OR — must work, not silently fail."""
    result = _grep_notes("memory|coordination", notes_dir)
    assert "z20260101-001" in result
    assert "z20260101-002" in result


def test_grep_notes_no_match(notes_dir: Path) -> None:
    result = _grep_notes("xyzzy_not_found", notes_dir)
    assert "No notes matching" in result


def test_grep_notes_empty_pattern(notes_dir: Path) -> None:
    result = _grep_notes("", notes_dir)
    assert "empty" in result.lower()


# ---------------------------------------------------------------------------
# read_note
# ---------------------------------------------------------------------------


def test_read_note_returns_content(notes_dir: Path) -> None:
    result = _read_note("z20260101-001", notes_dir)
    assert "# Agent Memory Systems" in result
    assert "episodic" in result


def test_read_note_missing(notes_dir: Path) -> None:
    result = _read_note("z99999999-999", notes_dir)
    assert "not found" in result


def test_read_note_includes_see_also(notes_dir: Path) -> None:
    """See Also section must be visible so the LLM can follow the links."""
    result = _read_note("z20260101-001", notes_dir)
    assert "## See Also" in result
    assert "z20260101-002" in result


# ---------------------------------------------------------------------------
# query() agentic loop
# ---------------------------------------------------------------------------


def test_query_no_tools_needed(notes_dir: Path) -> None:
    """LLM answers immediately without calling any tools."""
    llm = MockToolLLM([("The answer is 42.", [])])
    result = query("What is the meaning of life?", notes_dir, llm)
    assert result == "The answer is 42."


def test_query_single_tool_round(notes_dir: Path) -> None:
    """LLM calls grep_notes once, then answers."""
    tool_call = ToolCall(id="t1", name="grep_notes", input={"pattern": "memory"})
    llm = MockToolLLM([
        (None, [tool_call]),
        ("Memory systems store episodic and semantic information.", []),
    ])
    result = query("What kinds of memory exist?", notes_dir, llm)
    assert "Memory" in result


def test_query_multi_tool_round(notes_dir: Path) -> None:
    """LLM calls list_notes then read_note, then answers."""
    llm = MockToolLLM([
        (None, [ToolCall(id="t1", name="list_notes", input={})]),
        (None, [ToolCall(id="t2", name="read_note", input={"note_id": "z20260101-001"})]),
        ("Agent memory includes episodic and semantic components.", []),
    ])
    result = query("Tell me about agent memory.", notes_dir, llm)
    assert "memory" in result.lower()


def test_query_find_related_tool(notes_dir: Path) -> None:
    """LLM calls find_related, receives results, then answers."""
    llm = MockToolLLM([
        (None, [ToolCall(id="t1", name="find_related", input={"note_id": "z20260101-001"})]),
        ("Related notes were found.", []),
    ])
    result = query("What is related to memory?", notes_dir, llm)
    assert result == "Related notes were found."


def test_query_max_rounds_exceeded(notes_dir: Path) -> None:
    """RuntimeError raised if loop never terminates."""
    # Always returns a tool call, never a final answer
    endless = [(None, [ToolCall(id=f"t{i}", name="list_notes", input={})]) for i in range(25)]
    llm = MockToolLLM(endless)
    with pytest.raises(RuntimeError, match="max_rounds"):
        query("loop forever", notes_dir, llm, max_rounds=3)


def test_query_intermediate_text_preserved(notes_dir: Path) -> None:
    """Text that accompanies tool calls is included in the assistant message."""
    # The loop should not crash when the LLM emits text + tool calls together
    llm = MockToolLLM([
        ("Let me look that up.", [ToolCall(id="t1", name="list_notes", input={})]),
        ("Here is the answer.", []),
    ])
    result = query("Any question.", notes_dir, llm)
    assert result == "Here is the answer."
