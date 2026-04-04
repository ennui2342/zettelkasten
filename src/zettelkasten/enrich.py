"""Navigation-based query for the zettelkasten store.

Implements the Iter 4 navigation skill as a tool-using agentic loop.
The agent uses three tools to explore the note graph:

  list_notes  — scan all note IDs and titles
  grep_notes  — text search across note content
  read_note   — read a note by ID

Notes produced by the integration pipeline include a ``## See Also`` section
with ``[[id|title]]`` links.  The LLM reads those links and follows them by
calling ``read_note`` — the same traversal strategy validated in the
enrichment spike.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from .note import ZettelNote
from .providers import ToolCall, ToolLLMProvider, ToolSpec

log = logging.getLogger("zettelkasten")

# ---------------------------------------------------------------------------
# Navigation skill prompt (Iter 4, adapted for tool-based interface)
# ---------------------------------------------------------------------------

ENRICH_SKILL = """\
The store contains synthesised notes. Each note integrates multiple source \
documents into a single concept and is already compressed — denser than the \
raw material it came from. There are typically 20–40 notes in a store.

## Navigation strategy

Start with grep_notes to anchor on relevant notes. If the anchored notes \
don't fully cover the question, follow See Also links to find adjacent notes \
you wouldn't have named. Grep finds what you can name; See Also finds what's \
adjacent but unnamed.

## Finding notes

Scan note titles before reading bodies. Titles are descriptive enough to \
judge relevance without opening the file.

## Following connections

Each note ends with a ## See Also section listing related notes with a brief \
description of the relationship. After reading a note, check its See Also \
links to find adjacent notes you might not have thought to search for — this \
is the primary way to discover notes that are conceptually close but wouldn't \
appear in a keyword search.

## When to stop

Stop reading when you have covered all aspects of the question. You do not \
need to read every note that looks relevant — read until you have enough, \
then synthesise. More reads is not better.\
"""

# ---------------------------------------------------------------------------
# Tool specifications
# ---------------------------------------------------------------------------

TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="list_notes",
        description=(
            "List all note IDs and titles in the store. "
            "Use this to scan what is available before reading."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
    ),
    ToolSpec(
        name="grep_notes",
        description=(
            "Search note titles and bodies for a regex pattern (case-insensitive). "
            "Supports regex operators: use | for OR (e.g. 'memory|retrieval'), "
            ". for any character, \\b for word boundaries. "
            "Returns matching note IDs, titles, and the matching lines."
        ),
        parameters={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Case-insensitive regex pattern to search for",
                }
            },
            "required": ["pattern"],
        },
    ),
    ToolSpec(
        name="read_note",
        description=(
            "Read the full content of a note by ID. "
            "Notes end with a ## See Also section — follow those links to "
            "discover adjacent notes."
        ),
        parameters={
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "string",
                    "description": "The note ID, e.g. z20260322-001",
                }
            },
            "required": ["note_id"],
        },
    ),
]

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _list_notes(notes_dir: Path) -> str:
    """Return a newline-separated list of 'id: title' for all notes."""
    lines: list[str] = []
    for p in sorted(notes_dir.glob("*.md")):
        try:
            note = ZettelNote.from_markdown(p.read_text(encoding="utf-8"))
            lines.append(f"{note.id}: {note.title}")
        except Exception:
            lines.append(f"{p.stem}: (unreadable)")
    return "\n".join(lines) if lines else "No notes in store"


def _grep_notes(pattern: str, notes_dir: Path) -> str:
    """Case-insensitive regex search across note titles and bodies."""
    if not pattern:
        return "Pattern must not be empty"
    try:
        pat = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"Invalid pattern: {e}"

    results: list[str] = []
    for p in sorted(notes_dir.glob("*.md")):
        try:
            note = ZettelNote.from_markdown(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        matches: list[str] = []
        if pat.search(note.title):
            matches.append(f"  title: {note.title}")
        for line in note.body.split("\n"):
            if pat.search(line):
                matches.append(f"  {line.strip()[:120]}")
                if len(matches) >= 5:
                    break
        if matches:
            results.append(f"{note.id}: {note.title}\n" + "\n".join(matches))

    return "\n\n".join(results) if results else f"No notes matching {pattern!r}"


def _read_note(note_id: str, notes_dir: Path) -> str:
    """Return the title + body of a note (frontmatter stripped)."""
    note_path = notes_dir / f"{note_id}.md"
    if not note_path.exists():
        return f"Note {note_id!r} not found"
    try:
        note = ZettelNote.from_markdown(note_path.read_text(encoding="utf-8"))
        return f"# {note.title}\n\n{note.body}"
    except Exception as exc:
        return f"Error reading {note_id!r}: {exc}"


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------


def _dispatch(tc: ToolCall, notes_dir: Path) -> str:
    inp = tc.input
    if tc.name == "list_notes":
        return _list_notes(notes_dir)
    if tc.name == "grep_notes":
        return _grep_notes(inp.get("pattern", ""), notes_dir)
    if tc.name == "read_note":
        return _read_note(inp.get("note_id", ""), notes_dir)
    return f"Unknown tool: {tc.name!r}"


# ---------------------------------------------------------------------------
# Agentic query loop
# ---------------------------------------------------------------------------


def query(
    question: str,
    notes_dir: Path,
    llm: ToolLLMProvider,
    *,
    max_rounds: int = 20,
) -> str:
    """Answer *question* by navigating the note store with the Iter 4 skill.

    The LLM is given three tools (list_notes, grep_notes, read_note)
    and a system prompt encoding the navigation strategy.
    The loop runs until the LLM returns a text response without tool calls,
    or until *max_rounds* is exceeded.
    """
    messages: list[dict] = [{"role": "user", "content": question}]

    for round_num in range(max_rounds):
        text, tool_calls = llm.complete_tools(
            messages,
            TOOL_SPECS,
            system=ENRICH_SKILL,
            max_tokens=4096,
            temperature=0.0,
        )

        if not tool_calls:
            # LLM is done — return its answer
            log.info("enrich.done rounds=%d", round_num + 1)
            return text or ""

        # Build assistant content block (text + tool_use blocks)
        assistant_content: list[dict] = []
        if text:
            assistant_content.append({"type": "text", "text": text})
        for tc in tool_calls:
            assistant_content.append(
                {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.input}
            )
        messages.append({"role": "assistant", "content": assistant_content})

        # Execute tools and collect results
        tool_results: list[dict] = []
        for tc in tool_calls:
            _key = tc.input.get("note_id") or tc.input.get("pattern") or ""
            log.info("enrich.tool round=%d name=%s input=%r", round_num + 1, tc.name, _key)
            result_content = _dispatch(tc, notes_dir)
            tool_results.append(
                {"type": "tool_result", "tool_use_id": tc.id, "content": result_content}
            )
        messages.append({"role": "user", "content": tool_results})

    log.info("enrich.done rounds=%d", max_rounds)
    raise RuntimeError(
        f"query() exceeded max_rounds={max_rounds} without a final answer"
    )
