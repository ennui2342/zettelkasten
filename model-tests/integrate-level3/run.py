#!/usr/bin/env python3
"""Model test: Level 3 decision — SPLIT or EDIT for large UPDATE targets.

Level 3 is the focused binary decision that fires when:
  - Step 1 returns UPDATE for a note above NOTE_BODY_LARGE (8,000 chars), AND
  - The note has already been routed here by the level 2 CREATE/UPDATE node.

Known failure mode (2026-03-18 benchmark): when the note is coherent and
single-threaded but the draft is about a different topic, the current prompt
chooses SPLIT because EDIT feels wrong (topics differ). But SPLIT on a
single-threaded note produces two near-identical halves — a duplicate.

The correct answer in that case is EDIT: compress the existing note; the
draft's different topic is for level 2 to handle (it should have been CREATE).

This test compares the current _STEP1_5_PROMPT against a candidate prompt
that adds explicit guidance on the single-thread case.

Usage:
  uv run --env-file .env python model-tests/integrate-level3/run.py

Populate TEST_CASES with real Form-phase drafts using extract_drafts.py.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"

ROOT = HERE.parent.parent

import sys
sys.path.insert(0, str(ROOT / "src"))

# ---------------------------------------------------------------------------
# Candidate prompt — level 3 refinement
# Key change: explicit guidance that EDIT is correct when the NOTE is
# single-threaded, regardless of whether the draft is a different topic.
# ---------------------------------------------------------------------------

_CANDIDATE_PROMPT = (HERE / "prompts" / "step1_5.txt").read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Test cases
# Expected: EDIT or SPLIT
# Failure mode: current prompt chooses SPLIT when EDIT is correct (cases 3, 4)
#
# NOTE: Cases 3 and 4 use synthetic drafts as placeholders.
# Run extract_drafts.py to get real Form-phase outputs from the problematic
# papers, then replace the synthetic draft bodies below.
# ---------------------------------------------------------------------------

TEST_CASES = [
    # Case 1: Regression guard — focused single-topic note, same-topic draft → EDIT
    # z059 is a prose note on rubric-based evaluation with no internal sub-headings.
    # It is unambiguously single-threaded. Both prompts must agree on EDIT here.
    # If either prompt produces SPLIT on this case, it has a systematic false-positive.
    dict(
        label="Regression: focused single-topic note + same-topic draft → EDIT",
        target_file="z20260318-059.md",  # Rubric-Based Evaluation of AI Systems (8.7k, no sub-headings)
        draft_title="Calibrating Rubric Weights Through Contrastive Human Feedback",
        draft_body=(
            "The effectiveness of rubric-based evaluation depends not just on criterion "
            "selection but on weight calibration. When rubric criteria conflict — a response "
            "that is maximally concise may sacrifice completeness — the relative weights "
            "determine which trade-off is rewarded. Contrastive human feedback, where "
            "evaluators compare pairs of outputs with similar criterion profiles but "
            "different weight distributions, provides a signal for calibrating weights that "
            "simple agreement scoring cannot. Bayesian weight inference from pairwise "
            "comparisons has been shown to converge on human preference orderings with "
            "significantly fewer annotations than criterion-level rating."
        ),
        expected="EDIT",
        note=(
            "z059 is a single-prose-thread note on rubric-based evaluation (no sub-headings, 8.7k). "
            "Draft is on the same topic. If either prompt produces SPLIT, it has a false-positive problem."
        ),
    ),
    # Case 2: Positive SPLIT — z001 final state covers two separable threads:
    # (1) workflow automation architectures, (2) procedural memory for agent systems.
    # A draft about hierarchical orchestration should surface this division.
    dict(
        label="Positive SPLIT: z001 final state has two genuine threads",
        target_file="z20260318-001.md",   # Multi-Agent Architectures + Procedural Memory (9.8k)
        draft_title="Hierarchical Multi-Agent Systems",
        draft_body=(
            "Hierarchical multi-agent systems (HMAS) have emerged as a dominant architectural "
            "pattern for tackling problems beyond the scope of individual agents. By organizing "
            "agents into structured hierarchies, these systems enable sophisticated task "
            "decomposition, parallel execution, and efficient coordination—mirroring the "
            "division of labor in effective human organizations.\n\n"
            "Several architectural paradigms illustrate the power of this approach. The "
            "\"Manager-Expert\" paradigm involves a manager agent that decomposes high-level "
            "tasks and assigns sub-tasks to specialized expert agents. A key feature is "
            "feedback-driven replanning, where experts report on failures and learned insights, "
            "allowing the manager to adapt strategy dynamically. Centralized control models, "
            "exemplified by frameworks like MetaGPT and AutoAct, use a central controller to "
            "manage predefined workflows and assign roles to specialized agents, ensuring "
            "structured and predictable processes.\n\n"
            "More advanced frameworks explore automated and self-evolving hierarchies. "
            "Pyramid-like directed acyclic graph (DAG)-based architectures with generalized "
            "\"agent-as-a-tool\" mechanisms allow higher-level agents to invoke lower-level "
            "agents as tools, enabling automatic task decomposition and the potential for agent "
            "hierarchies to evolve and adapt over time. Workflow orchestration in such systems "
            "can be modeled as directed conditional graphs, where nodes represent agents or "
            "processing modules and edges represent possible control flow transitions."
        ),
        expected="SPLIT",
        note=(
            "z001 final state has workflow automation architectures AND procedural memory "
            "as distinct threads. Both prompts should agree on SPLIT."
        ),
    ),
    # Case 3: Failure case — tightly-focused note + different-topic draft → EDIT
    # z027 (8.6k) is a focused single-threaded note about evaluation frameworks.
    # The hierarchical architectures draft is a completely different topic.
    # When step1 wrongly routes architectural content into an evaluation note as UPDATE,
    # step1.5 should produce EDIT (compress the note; CREATE handles the draft separately).
    # If it produces SPLIT instead, it will create a duplicate of the evaluation content.
    dict(
        label="Failure case: focused evaluation note + different-topic (architectures) draft → EDIT",
        target_file="z20260318-027.md",   # Evaluation Frameworks (8.6k chars, focused single topic)
        draft_title="Hierarchical Multi-Agent Systems",
        draft_body=(
            "Hierarchical multi-agent systems (HMAS) have emerged as a dominant architectural "
            "pattern for tackling problems beyond the scope of individual agents. By organizing "
            "agents into structured hierarchies, these systems enable sophisticated task "
            "decomposition, parallel execution, and efficient coordination—mirroring the "
            "division of labor in effective human organizations.\n\n"
            "Several architectural paradigms illustrate the power of this approach. The "
            "\"Manager-Expert\" paradigm involves a manager agent that decomposes high-level "
            "tasks and assigns sub-tasks to specialized expert agents. A key feature is "
            "feedback-driven replanning, where experts report on failures and learned insights, "
            "allowing the manager to adapt strategy dynamically. Centralized control models, "
            "exemplified by frameworks like MetaGPT and AutoAct, use a central controller to "
            "manage predefined workflows and assign roles to specialized agents, ensuring "
            "structured and predictable processes.\n\n"
            "More advanced frameworks explore automated and self-evolving hierarchies. "
            "Pyramid-like directed acyclic graph (DAG)-based architectures with generalized "
            "\"agent-as-a-tool\" mechanisms allow higher-level agents to invoke lower-level "
            "agents as tools, enabling automatic task decomposition and the potential for agent "
            "hierarchies to evolve and adapt over time. Workflow orchestration in such systems "
            "can be modeled as directed conditional graphs, where nodes represent agents or "
            "processing modules and edges represent possible control flow transitions."
        ),
        expected="EDIT",
        note=(
            "Core failure scenario: focused single-threaded note + different-topic draft. "
            "Current prompt may see 'topics differ' → SPLIT, creating a duplicate of the "
            "evaluation content. Candidate should recognise the note has no separable "
            "threads → EDIT."
        ),
    ),
    # Case 4: EDIT on same-topic evaluation note — guards against regression
    # z027 (evaluation frameworks) + Agentic AI evaluation draft — same topic area.
    # z027 triggered a bad SPLIT → z042 in the benchmark; the CLASSic-framework content
    # duplicated because step2 SPLIT found no boundary. The level-3 test here checks
    # that same-topic drafts on evaluation notes don't incorrectly produce SPLIT.
    dict(
        label="Same-topic EDIT: evaluation note + evaluation benchmarking draft",
        target_file="z20260318-027.md",   # Evaluation Frameworks for Real-World Agent Deployment (8.6k)
        draft_title="Evaluation and Benchmarking of AI Agents",
        draft_body=(
            "Evaluating agentic AI systems requires methodologies that go beyond traditional "
            "text similarity metrics like BLEU or ROUGE. The CLASSic framework assesses agents "
            "across five critical dimensions: Cost, Latency, Accuracy, Security, and Stability.\n\n"
            "Cost reflects the efficiency–intelligence trade-off inherent in agent design. High "
            "reasoning depth often comes at significant computational overhead. Hierarchical "
            "architectures maximize task proficiency but incur exponential increases in token "
            "consumption compared to linear chains or zero-shot prompting.\n\n"
            "Latency evaluation reveals that agents frequently fail when tasks involve variable "
            "temporal delays. Asynchronous benchmarks like Robotouille reveal dramatic "
            "performance drops when tasks involve waiting (from 47% success in synchronous "
            "settings to 11% in asynchronous ones).\n\n"
            "Agent accuracy cannot be captured by static question-answering alone — success "
            "can collapse when tasks require tool use, state tracking, and long-horizon "
            "recovery. GAIA highlights gaps for general assistants on human-easy tasks "
            "requiring multi-step decomposition. Modern evaluation increasingly reports "
            "compute budgets, run-to-run variance, and failure severity distributions "
            "alongside mean success rates."
        ),
        expected="EDIT",
        note=(
            "z027 is single-threaded (CLASSic framework + evaluation benchmarks). "
            "Draft covers the same evaluation territory. Both prompts should choose EDIT. "
            "This is a regression guard for same-topic behaviour on the note that produced z042."
        ),
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


def run_current(note, draft, llm) -> dict:
    """Current _STEP1_5_PROMPT from prompts.py."""
    from zettelkasten.prompts import _STEP1_5_PROMPT
    target_text = f"id: {note.id}\n## {note.title}\n\n{note.body}"
    draft_text = f"## {draft.title}\n\n{draft.body}"
    prompt = _STEP1_5_PROMPT.format(
        note_size=len(note.body),
        target=target_text,
        draft=draft_text,
    )
    raw = llm.complete(prompt, max_tokens=256, temperature=0.0)
    result = parse_decision(raw)
    if result.get("operation") not in ("EDIT", "SPLIT"):
        result["operation"] = "EDIT"
    return result


def run_candidate(note, draft, llm) -> dict:
    """Candidate prompt — note only, no draft."""
    target_text = f"id: {note.id}\n## {note.title}\n\n{note.body}"
    prompt = _CANDIDATE_PROMPT.format(
        note_size=len(note.body),
        target=target_text,
    )
    raw = llm.complete(prompt, max_tokens=256, temperature=0.0)
    result = parse_decision(raw)
    if result.get("operation") not in ("EDIT", "SPLIT"):
        result["operation"] = "EDIT"
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    from zettelkasten.config import load_config, build_fast_llm

    cfg = load_config(ROOT / "zettelkasten.toml")
    llm = build_fast_llm(cfg)

    model = cfg["llm"].get("fast_model", "unknown")
    print(f"Model: {model}")
    print(f"Date:  {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')}")
    print()
    print("=" * 72)
    print("Current step1.5 prompt  vs  Candidate level-3 prompt")
    print("=" * 72)

    current_score = 0
    candidate_score = 0
    n = len(TEST_CASES)

    for i, tc in enumerate(TEST_CASES, 1):
        note = load_note(tc["target_file"])
        draft = make_draft(tc["draft_title"], tc["draft_body"])
        expected = tc["expected"]

        print(f"\nCase {i}/{n}: {tc['label']}")
        print(f"  Target  : {note.title[:65]}  [{len(note.body):,} chars]")
        print(f"  Draft   : {draft.title[:65]}")
        print(f"  Expected: {expected}")
        if tc.get("note"):
            print(f"  Context : {tc['note'][:90]}")

        print(f"  Running current prompt...")
        curr = run_current(note, draft, llm)
        print(f"  Running candidate prompt...")
        cand = run_candidate(note, draft, llm)

        curr_op   = curr.get("operation", "?")
        cand_op   = cand.get("operation", "?")
        curr_conf = curr.get("confidence", 0)
        cand_conf = cand.get("confidence", 0)
        curr_ok   = curr_op == expected
        cand_ok   = cand_op == expected

        if curr_ok:
            current_score += 1
        if cand_ok:
            candidate_score += 1

        print(f"  Current  : {curr_op:<6} conf={curr_conf:.2f}  {'✓' if curr_ok else '✗'}  {curr.get('reasoning', '')[:65]}")
        print(f"  Candidate: {cand_op:<6} conf={cand_conf:.2f}  {'✓' if cand_ok else '✗'}  {cand.get('reasoning', '')[:65]}")

    print()
    print("=" * 72)
    print(f"Current  : {current_score}/{n} correct")
    print(f"Candidate: {candidate_score}/{n} correct")
    print()
    if candidate_score > current_score:
        print("Candidate prompt improves on current. Consider promoting to _STEP1_5_PROMPT.")
    elif candidate_score == current_score == n:
        print("Both prompts correct on all cases. Candidate may be promoted for its clearer framing.")
    else:
        print("Review failures above before making changes.")
    print("=" * 72)


if __name__ == "__main__":
    main()
