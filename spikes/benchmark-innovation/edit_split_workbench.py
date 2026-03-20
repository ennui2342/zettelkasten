#!/usr/bin/env python3
"""Workbench for testing EDIT/SPLIT decision quality and EDIT execution quality.

Two independent tests:

  Test 1 — Decision quality
    Given a large note and a relevant draft, does the classifier choose EDIT or
    SPLIT rather than UPDATE? Runs the same (draft, cluster) pair through both
    the baseline prompt (no EDIT/LARGE awareness) and Option A (the modified
    prompt from integrate.py). Prints decisions side by side.

  Test 2 — Execution quality
    Given that EDIT was chosen, does the step 2 prompt produce a well-compressed
    note? Measures input vs output size and prints a preview for inspection.
    EDIT is hardcoded — this test is independent of Test 1.

Usage:
  uv run python spikes/benchmark-innovation/edit_split_workbench.py           # both tests
  uv run python spikes/benchmark-innovation/edit_split_workbench.py --test 1  # decision only
  uv run python spikes/benchmark-innovation/edit_split_workbench.py --test 2  # execution only
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
STORE_DIR = HERE / "store"

# ---------------------------------------------------------------------------
# Baseline prompt — original _STEP1_PROMPT without EDIT/LARGE additions
# ---------------------------------------------------------------------------

_BASELINE_PROMPT = """\
You maintain a knowledge base of topic notes. You have a draft note and a \
cluster of related existing notes.

Draft note:
{draft}

Existing notes in cluster:
{cluster}

Decide what action to take. Choose exactly one:

- UPDATE: the draft adds to an existing note. Rewrite that note to synthesise \
old and new — do not append. Specify which note by its id field.
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

If the cluster is empty, STUB is the appropriate default unless the draft is \
clearly a subtopic of notes in the broader knowledge base.

Output JSON only. Schema:
{{
  "operation": "<one of the seven>",
  "target_note_ids": ["<id>", ...],
  "reasoning": "<one or two sentences>",
  "confidence": <0.0 to 1.0>
}}"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_large_notes(threshold: int = 8000) -> list:
    """Load notes from the benchmark store that exceed the size threshold."""
    from zettelkasten.note import ZettelNote
    notes = []
    for p in sorted(STORE_DIR.glob("*.md")):
        try:
            note = ZettelNote.from_markdown(p.read_text(encoding="utf-8"))
            if len(note.body) > threshold:
                notes.append(note)
        except Exception:
            pass
    return sorted(notes, key=lambda n: len(n.body), reverse=True)


def make_draft(title: str, body: str):
    """Construct a minimal draft ZettelNote (no id required)."""
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
        return {"operation": "PARSE_ERROR", "reasoning": raw[:200], "confidence": 0.0, "target_note_ids": []}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {"operation": "PARSE_ERROR", "reasoning": raw[:200], "confidence": 0.0, "target_note_ids": []}


def run_classify(draft, cluster: list, llm, prompt_template: str, annotate_large: bool) -> dict:
    """Run step 1 classification with a given prompt template."""
    if cluster:
        parts = []
        for n in cluster:
            header = f"id: {n.id}"
            if annotate_large and len(n.body) > 8000:
                header += f"  [LARGE: {len(n.body)} chars]"
            parts.append(f"{header}\n## {n.title}\n\n{n.body}")
        cluster_text = "\n\n---\n\n".join(parts)
    else:
        cluster_text = "(empty — no existing notes in cluster)"

    draft_text = f"## {draft.title}\n\n{draft.body}"
    prompt = prompt_template.format(draft=draft_text, cluster=cluster_text)
    raw = llm.complete(prompt, max_tokens=512, temperature=0.0)
    return parse_decision(raw)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

# Each case: (draft_title, draft_body, target_note_partial_title)
# Drafts are deliberately short and relevant — we want to see UPDATE vs EDIT/SPLIT
TEST_CASES = [
    (
        "Compositional Evaluation of Agentic Pipelines",
        (
            "Recent work proposes evaluating agentic systems not at task completion "
            "but at the level of individual pipeline stages — tool selection, context "
            "management, and recovery from failure. This compositional approach allows "
            "pinpointing architectural weaknesses that end-to-end metrics obscure."
        ),
        "Evaluating Agentic",
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
        "Memory Poisoning",
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
        "Multi-Agent LLM",
    ),
]


# ---------------------------------------------------------------------------
# Test 1 — Decision quality
# ---------------------------------------------------------------------------

def test_decision_quality(llm) -> None:
    from zettelkasten.integrate import _STEP1_PROMPT  # Option A (modified)

    print("\n" + "=" * 70)
    print("TEST 1 — Decision Quality")
    print("Baseline (no EDIT/LARGE) vs Option A (EDIT/LARGE guidance)")
    print("=" * 70)

    large_notes = load_large_notes()
    if not large_notes:
        print("No large notes found in store (threshold: 8000 chars). Run ingestion first.")
        return

    print(f"Found {len(large_notes)} large notes in store\n")

    for draft_title, draft_body, note_partial in TEST_CASES:
        # Find the matching large note
        target = next((n for n in large_notes if note_partial in n.title), None)
        if not target:
            print(f"  [SKIP] No large note matching {note_partial!r}")
            continue

        draft = make_draft(draft_title, draft_body)
        cluster = [target]

        print(f"Draft:  {draft_title}")
        print(f"Target: {target.title[:65]}  [{len(target.body)} chars]")

        baseline = run_classify(draft, cluster, llm, _BASELINE_PROMPT, annotate_large=False)
        option_a = run_classify(draft, cluster, llm, _STEP1_PROMPT, annotate_large=True)

        b_op = baseline.get("operation", "?")
        a_op = option_a.get("operation", "?")
        b_conf = baseline.get("confidence", 0)
        a_conf = option_a.get("confidence", 0)
        changed = "  ← changed" if a_op != b_op else ""

        print(f"  Baseline : {b_op:<8}  conf={b_conf:.2f}  {baseline.get('reasoning', '')[:60]}")
        print(f"  Option A : {a_op:<8}  conf={a_conf:.2f}  {option_a.get('reasoning', '')[:60]}{changed}")
        print()


# ---------------------------------------------------------------------------
# Test 2 — EDIT execution quality
# ---------------------------------------------------------------------------

def test_edit_execution(llm) -> None:
    from zettelkasten.integrate import _step2_execute
    from zettelkasten.note import ZettelNote

    print("\n" + "=" * 70)
    print("TEST 2 — EDIT Execution Quality")
    print("Does the EDIT prompt produce a meaningfully smaller note?")
    print("=" * 70)

    large_notes = load_large_notes()
    if not large_notes:
        print("No large notes found in store (threshold: 8000 chars). Run ingestion first.")
        return

    # Use the top 3 largest notes
    for note in large_notes[:3]:
        draft_title, draft_body, _ = next(
            (c for c in TEST_CASES if c[2] in note.title),
            ("Context note", "Related content for context.", ""),
        )
        draft = make_draft(draft_title, draft_body)

        print(f"\nNote: {note.title[:65]}")
        print(f"  Input size:  {len(note.body):,} chars")
        print(f"  Calling EDIT (Opus)...", flush=True)

        title, body = _step2_execute("EDIT", draft, [note], llm)

        ratio = len(body) / len(note.body) * 100
        delta = len(note.body) - len(body)
        flag = "  ✓" if len(body) < len(note.body) else "  ✗ NOT SMALLER"

        print(f"  Output size: {len(body):,} chars  ({ratio:.0f}% of original, -{delta:,} chars){flag}")
        print(f"  Output title: {title}")
        print(f"  Preview: {body[:300].replace(chr(10), ' ')[:200]}...")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="EDIT/SPLIT workbench")
    parser.add_argument(
        "--test", choices=["1", "2"], default=None,
        help="Run only test 1 (decision) or test 2 (execution). Default: both.",
    )
    args = parser.parse_args()

    print("Loading providers...")
    from zettelkasten.config import load_config, build_llm, build_fast_llm
    cfg = load_config()
    llm = build_llm(cfg)
    fast_llm = build_fast_llm(cfg)
    print(f"LLM: {cfg['llm']['model']}  |  Fast LLM: {cfg['llm']['fast_model']}")

    if args.test != "2":
        test_decision_quality(fast_llm)   # classify uses fast_llm

    if args.test != "1":
        test_edit_execution(llm)          # execution uses main llm


if __name__ == "__main__":
    main()
