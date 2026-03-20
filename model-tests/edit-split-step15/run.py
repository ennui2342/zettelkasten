#!/usr/bin/env python3
"""Model test: Is step 1.5 still needed to route UPDATE → EDIT/SPLIT on large notes?

Compares two approaches for handling UPDATE decisions on large notes:

  Option A — Modified step 1 prompt
    EDIT is listed as an operation in the step 1 prompt. Notes exceeding
    NOTE_BODY_LARGE are annotated [LARGE: N chars] in the cluster. The model
    is instructed not to choose UPDATE for large notes.

  Current approach — Step 1 (clean) + Step 1.5 (focused refinement)
    Step 1 uses the production prompt (no EDIT, no LARGE annotation).
    If step 1 returns UPDATE on a large note, step 1.5 asks a focused
    two-option question: EDIT or SPLIT?

The baseline (2026-03-17, claude-haiku-4-5) found Option A unreliable:
it drifted to SYNTHESISE rather than EDIT in 2/3 cases.

Revisit trigger: if Option A now produces EDIT/SPLIT for all 3 cases,
step 1.5 can be removed from integrate.py (saves one LLM call per
large-note integration).

Usage:
  uv run --env-file .env python model-tests/edit-split-step15/run.py
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"

# ---------------------------------------------------------------------------
# Option A prompt — single step 1 with EDIT/LARGE guidance
# This is what we tested and found insufficient. Keep it here verbatim so
# future re-runs test the same thing.
# ---------------------------------------------------------------------------

_OPTION_A_PROMPT = """\
You maintain a knowledge base of topic notes. You have a draft note and a \
cluster of related existing notes.

Draft note:
{draft}

Existing notes in cluster:
{cluster}

Decide what action to take. Choose exactly one:

- UPDATE: the draft adds to an existing note. Rewrite that note to synthesise \
old and new — do not append. Specify which note by its id field. Only valid \
for notes without a [LARGE] marker.
- EDIT: an existing note is marked [LARGE] and covers one topic but has grown \
verbose through repeated updates. Rewrite it to compress and distil — same \
topic, no new content from the draft. The draft is context only. Specify \
which note by its id field.
- CREATE: the draft covers a topic not in the cluster. Create a new note with \
links to relevant existing notes.
- SPLIT: an existing note conflates two distinct topics that the draft \
clarifies should be separate. Specify which note and how to split it.
- MERGE: two existing notes in the cluster cover the same topic. The draft \
confirms they should be one. Specify which notes.
- SYNTHESISE: the draft reveals a connection between two existing notes that \
neither captures. Create a new structure note articulating the bridging \
principle. Specify which notes it bridges.
- NOTHING: the draft is already fully covered by the existing cluster. No \
action needed.
- STUB: the cluster is sparse or empty — this is a new topic without an \
established neighbourhood. Create a provisional note at low confidence.

Notes marked [LARGE: N chars] are near the size ceiling. For LARGE notes you \
must not choose UPDATE — instead choose EDIT if the note covers one topic that \
needs compressing, or SPLIT if the draft clarifies the note conflates two \
distinct topics.

If the cluster is empty, STUB is the appropriate default unless the draft is \
clearly a subtopic of notes in the broader knowledge base.

Output JSON only. Schema:
{{
  "operation": "<one of the operations>",
  "target_note_ids": ["<id>", ...],
  "reasoning": "<one or two sentences>",
  "confidence": <0.0 to 1.0>
}}"""


# ---------------------------------------------------------------------------
# Test cases: (draft_title, draft_body, data_filename)
# Drafts are short and topically relevant — enough to trigger UPDATE on the
# large note, so we can observe what the model does instead.
# ---------------------------------------------------------------------------

TEST_CASES = [
    (
        "Compositional Evaluation of Agentic Pipelines",
        (
            "Recent work proposes evaluating agentic systems not at task completion "
            "but at the level of individual pipeline stages — tool selection, context "
            "management, and recovery from failure. This compositional approach allows "
            "pinpointing architectural weaknesses that end-to-end metrics obscure."
        ),
        "z20260317-013.md",  # Evaluating Agentic AI Systems
    ),
    (
        "Indirect Prompt Injection via Tool Outputs",
        (
            "Adversarial content embedded in tool outputs — web search results, "
            "retrieved documents, database queries — can hijack an LLM agent's "
            "reasoning chain without direct access to the system prompt. Defences "
            "require distinguishing trusted and untrusted content sources at the "
            "agent architecture level."
        ),
        "z20260317-005.md",  # Memory Poisoning & Security
    ),
    (
        "Emergent Role Specialisation in Homogeneous Agent Pools",
        (
            "In multi-agent systems where all agents share the same base model and "
            "instructions, role differentiation can emerge spontaneously through "
            "interaction history. Agents that happen to handle early subtasks develop "
            "specialised context that makes them more likely to be routed similar tasks "
            "subsequently, without explicit role assignment."
        ),
        "z20260317-001.md",  # Multi-Agent LLM Systems
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_note(filename: str):
    from zettelkasten.note import ZettelNote
    path = DATA_DIR / filename
    return ZettelNote.from_markdown(path.read_text(encoding="utf-8"))


def make_draft(title: str, body: str):
    from zettelkasten.note import ZettelNote
    now = datetime.now(tz=timezone.utc)
    return ZettelNote(
        id="",
        title=title,
        body=body,
        type="stub",
        confidence=0.5,
        salience=0.5,
        stable=False,
        created=now,
        updated=now,
        last_accessed=now,
    )


def parse_decision(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"operation": "PARSE_ERROR", "reasoning": raw[:200], "confidence": 0.0}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {"operation": "PARSE_ERROR", "reasoning": raw[:200], "confidence": 0.0}


def run_option_a(draft, note, llm) -> dict:
    """Single step 1 with EDIT/LARGE guidance (Option A)."""
    cluster_text = f"id: {note.id}  [LARGE: {len(note.body)} chars]\n## {note.title}\n\n{note.body}"
    draft_text = f"## {draft.title}\n\n{draft.body}"
    prompt = _OPTION_A_PROMPT.format(draft=draft_text, cluster=cluster_text)
    raw = llm.complete(prompt, max_tokens=512, temperature=0.0)
    return parse_decision(raw)


def run_step1_plus_step15(draft, note, llm) -> dict:
    """Production approach: clean step 1 + focused step 1.5 if UPDATE on large note."""
    from zettelkasten.integrate import _step1_classify, _step1_5_classify

    step1 = _step1_classify(draft, [note], llm)
    op = step1.get("operation")

    if op == "UPDATE" and len(note.body) > 8000:
        step15 = _step1_5_classify(note, draft, llm)
        return step15

    return step1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    from zettelkasten.config import load_config, build_fast_llm
    cfg = load_config()
    llm = build_fast_llm(cfg)

    model = cfg["llm"].get("fast_model", "unknown")
    print(f"Model: {model}")
    print(f"Date:  {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')}")
    print()
    print("=" * 72)
    print("Option A (single modified step 1)  vs  Step 1 + Step 1.5 (current)")
    print("=" * 72)

    option_a_score = 0
    step15_score = 0
    target_ops = {"EDIT", "SPLIT"}

    for draft_title, draft_body, filename in TEST_CASES:
        note = load_note(filename)
        draft = make_draft(draft_title, draft_body)

        print(f"\nDraft:  {draft_title}")
        print(f"Target: {note.title[:65]}  [{len(note.body):,} chars]")

        a = run_option_a(draft, note, llm)
        b = run_step1_plus_step15(draft, note, llm)

        a_op = a.get("operation", "?")
        b_op = b.get("operation", "?")
        a_conf = a.get("confidence", 0)
        b_conf = b.get("confidence", 0)

        a_ok = a_op in target_ops
        b_ok = b_op in target_ops
        if a_ok:
            option_a_score += 1
        if b_ok:
            step15_score += 1

        print(f"  Option A   : {a_op:<10} conf={a_conf:.2f}  {'✓' if a_ok else '✗'}  {a.get('reasoning', '')[:60]}")
        print(f"  Step 1+1.5 : {b_op:<10} conf={b_conf:.2f}  {'✓' if b_ok else '✗'}  {b.get('reasoning', '')[:60]}")

    n = len(TEST_CASES)
    print()
    print("=" * 72)
    print(f"Summary: Option A {option_a_score}/{n} correct  |  Step 1+1.5 {step15_score}/{n} correct")
    print()
    if option_a_score == n:
        print("Option A is now SUFFICIENT — step 1.5 may be removable (save one LLM call per large-note integration).")
        print("Verify with a broader test before removing step 1.5.")
    else:
        print(f"Option A still unreliable ({n - option_a_score}/{n} failures). Step 1.5 remains necessary.")
    print()
    print("Baseline (2026-03-17, claude-haiku-4-5): Option A 1/3, Step 1+1.5 3/3")


if __name__ == "__main__":
    main()
