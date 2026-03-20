#!/usr/bin/env python3
"""Model test: Level 1 — SYNTHESISE vs PROCEED classification.

Level 1 is the first node of the integration decision tree. It sees the full
retrieval cluster and asks one question: does this draft reveal a bridging
insight between two or more existing notes?

  SYNTHESISE — bridge note warranted; fire step2 SYNTHESISE
  PROCEED    — no bridge; pass cluster to level 2
  NOTHING    — draft already fully covered; exit (rare)

Two prompts compared:
  Current  — _STEP1_PROMPT (multi-way classifier; SYNTHESISE is one of six options)
             Output mapped: SYNTHESISE → SYNTHESISE, anything else → PROCEED,
             NOTHING → NOTHING.
  Candidate — prompts/level1.txt (focused binary: SYNTHESISE or PROCEED)

Usage:
  uv run --env-file .env python model-tests/integrate-level1/run.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
NOTES_DIR = HERE / "data" / "notes"
DRAFTS_DIR = HERE / "data" / "drafts"
RESULTS_DIR = HERE / "results"

import sys
sys.path.insert(0, str(ROOT / "src"))

_CANDIDATE_PROMPT = (HERE / "prompts" / "level1.txt").read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------
# The full cluster for each case is ALL notes in NOTES_DIR — level 1 always
# sees the complete retrieval set. Cases are drawn from integration-decisions
# ground truth, re-labelled for the SYNTHESISE/PROCEED binary.
#
# Non-SYNTHESISE cases are the important regression guards: the model must not
# over-fire SYNTHESISE when the draft simply adds to a single note.
# ---------------------------------------------------------------------------

TEST_CASES_SET1 = [
    # --- True SYNTHESISE ---
    dict(
        label="SYNTHESISE: spaced retrieval reveals multiplicative interaction between testing-effect and spaced-repetition",
        draft_file="spaced-retrieval-synthesise-draft.md",
        expected="SYNTHESISE",
        expected_bridge={"z20260314-001", "z20260314-002"},  # spaced-repetition + testing-effect
        expected_target=None,  # SYNTHESISE: no single UPDATE target
        note=(
            "The draft shows these two techniques interact multiplicatively via effortful "
            "reconstruction — a bridging mechanism neither note captures."
        ),
    ),
    dict(
        label="SYNTHESISE: generation as deep encoding reveals generation-effect and encoding-formation are complementary halves",
        draft_file="generation-encoding-synthesise-draft.md",
        expected="SYNTHESISE",
        expected_bridge={"z20260314-013", "z20260314-004"},  # generation-effect + encoding
        expected_target=None,  # SYNTHESISE: no single UPDATE target
        note=(
            "The draft shows the generation effect IS the mechanism that makes processing deep — "
            "each note is an incomplete account without the other."
        ),
    ),
    # --- PROCEED cases (should not trigger SYNTHESISE) ---
    # NOTE: testing-effect-draft.md was considered for this slot but excluded:
    # it explicitly states elaborative interrogation "achieves the same consolidation
    # benefit via the same mechanism" as retrieval testing — a genuine bridge statement.
    # The ground truth at level 2 is UPDATE, but at level 1 SYNTHESISE is defensible.
    # Using spaced-repetition-draft.md instead: purely single-topic content.
    dict(
        label="PROCEED: spaced-repetition draft resolves mechanism question for one note only",
        draft_file="spaced-repetition-draft.md",
        expected="PROCEED",
        expected_bridge=set(),
        expected_target="z20260314-001",  # spaced-repetition — L2 handoff target
        note=(
            "Draft adds retrieval-difficulty-as-mechanism to the spaced-repetition note. "
            "Single-topic extension — should not SYNTHESISE."
        ),
    ),
    dict(
        label="PROCEED: generation-effect CREATE — new topic, no bridge between existing notes",
        draft_file="generation-effect-create-draft.md",
        expected="PROCEED",
        expected_bridge=set(),
        expected_target=None,  # CREATE at L2 — no existing note to target
        note=(
            "Draft is on a new topic not covered in the cluster. "
            "Nothing to bridge — should PROCEED to level 2 (CREATE)."
        ),
    ),
    dict(
        label="PROCEED/NOTHING: massed-practice draft already covered — at most NOTHING, never SYNTHESISE",
        draft_file="massed-practice-nothing-draft.md",
        expected="PROCEED",  # NOTHING also acceptable
        expected_bridge=set(),
        expected_target="z20260314-005",  # massed-practice — L2 handoff target (NOTHING at L2)
        note=(
            "Draft is already covered. Even if it exits as NOTHING, it must not SYNTHESISE. "
            "Expected PROCEED or NOTHING."
        ),
    ),
]

# Set 2: focused INTEGRATE cases — healthy balance check.
# All from integration-decisions ground truth (now in data/), all clearly non-bridge.
# expected_target: the note L2 would pick as the UPDATE target; None for CREATE cases.
TEST_CASES_SET2 = [
    dict(
        label="INTEGRATE: external-memory draft fills documented gap in one note",
        draft_file="external-memory-draft.md",
        expected="INTEGRATE",
        expected_bridge=set(),
        expected_target="z20260314-003",  # external-memory-systems
        note="UPDATE-3 ground truth. Answers the open question about what makes external systems encode. Single note target.",
    ),
    dict(
        label="INTEGRATE/NOTHING: forgetting-curve draft already covered",
        draft_file="forgetting-curve-nothing-draft.md",
        expected="INTEGRATE",  # NOTHING also acceptable
        expected_bridge=set(),
        expected_target="z20260314-006",  # forgetting-curve (NOTHING at L2, but should be in targets)
        note="NOTHING-2 ground truth. Already covered — NOTHING or INTEGRATE, never SYNTHESISE.",
    ),
    dict(
        label="INTEGRATE: sleep-consolidation stub — new isolated topic, no bridge",
        draft_file="sleep-consolidation-stub-draft.md",
        expected="INTEGRATE",
        expected_bridge=set(),
        expected_target=None,  # CREATE at L2 — sleep consolidation has no existing note
        note="STUB-1 ground truth. Sleep/hippocampal replay — no shared mechanism with cluster notes.",
    ),
    dict(
        label="INTEGRATE: prospective-memory stub — completely separate topic",
        draft_file="prospective-memory-stub-draft.md",
        expected="INTEGRATE",
        expected_bridge=set(),
        expected_target=None,  # CREATE at L2 — prospective memory has no existing note
        note="STUB-2 ground truth. Future-intention memory — orthogonal to all cluster notes.",
    ),
    dict(
        label="INTEGRATE: interleaved-practice draft extends one note, explicitly not spacing",
        draft_file="interleaved-practice-split-draft.md",
        expected="INTEGRATE",
        expected_bridge=set(),
        expected_target="z20260314-007",  # practice-strategies
        note="SPLIT-1 ground truth. Draft explicitly distinguishes itself from spacing — no cross-note bridge.",
    ),
]

TEST_CASES = TEST_CASES_SET1

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_cluster() -> str:
    """All notes in NOTES_DIR as a single cluster string."""
    notes = sorted(NOTES_DIR.glob("*.md"))
    parts = []
    for path in notes:
        text = path.read_text(encoding="utf-8")
        # Extract id from frontmatter for reference
        id_match = re.search(r"^id:\s*(\S+)", text, re.MULTILINE)
        note_id = id_match.group(1) if id_match else path.stem
        # Strip frontmatter
        body = re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL).strip()
        parts.append(f"id: {note_id}\n{body}")
    return "\n\n---\n\n".join(parts)


def load_draft(filename: str) -> str:
    path = DRAFTS_DIR / filename
    text = path.read_text(encoding="utf-8")
    # Strip frontmatter if present
    return re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL).strip()


def parse_decision(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"operation": "PARSE_ERROR", "reasoning": raw[:200], "confidence": 0.0, "target_note_ids": []}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {"operation": "PARSE_ERROR", "reasoning": raw[:200], "confidence": 0.0, "target_note_ids": []}


def normalise(op: str) -> str:
    """Map current prompt's multi-way output to level-1 terms."""
    if op == "SYNTHESISE":
        return "SYNTHESISE"
    if op == "NOTHING":
        return "NOTHING"
    return "PROCEED"


def run_current(draft_text: str, cluster_text: str, llm) -> dict:
    from zettelkasten.prompts import _STEP1_PROMPT
    prompt = _STEP1_PROMPT.format(draft=draft_text, cluster=cluster_text)
    raw = llm.complete(prompt, max_tokens=512, temperature=0.0)
    result = parse_decision(raw)
    result["operation"] = normalise(result.get("operation", "PROCEED"))
    return result


def run_candidate(draft_text: str, cluster_text: str, llm) -> dict:
    prompt = _CANDIDATE_PROMPT.format(draft=draft_text, cluster=cluster_text)
    raw = llm.complete(prompt, max_tokens=512, temperature=0.0)
    result = parse_decision(raw)
    op = result.get("operation", "INTEGRATE")
    if op not in ("SYNTHESISE", "INTEGRATE", "NOTHING"):
        result["operation"] = "INTEGRATE"
    return result


def check_bridge(result: dict, expected_bridge: set) -> bool:
    """For SYNTHESISE cases, verify the right notes are in target_note_ids."""
    if not expected_bridge:
        return True
    targets = set(result.get("target_note_ids", []))
    return bool(expected_bridge & targets)  # at least one bridged note identified


def check_handoff(result: dict, op: str, expected_target: str | None) -> bool | None:
    """For INTEGRATE cases with a known L2 target, verify target_note_ids includes it.

    Returns True/False when checkable, None when not applicable (SYNTHESISE,
    NOTHING, or CREATE cases where expected_target is None).
    """
    if expected_target is None:
        return None  # CREATE/new-topic case — no target to verify
    if op not in ("PROCEED", "INTEGRATE"):
        return None  # SYNTHESISE or NOTHING — not a handoff scenario
    return expected_target in result.get("target_note_ids", [])


def save_results(cases: list[dict], model: str, set_label: str) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    from datetime import datetime, timezone
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
    path = RESULTS_DIR / f"run_{timestamp}.md"

    curr_score = sum(1 for c in cases if c["curr_pass"])
    cand_score = sum(1 for c in cases if c["cand_pass"])
    n = len(cases)

    curr_h_cases = [c for c in cases if c["curr_handoff"] is not None]
    cand_h_cases = [c for c in cases if c["cand_handoff"] is not None]
    curr_h_pass = sum(1 for c in curr_h_cases if c["curr_handoff"])
    cand_h_pass = sum(1 for c in cand_h_cases if c["cand_handoff"])

    with path.open("w", encoding="utf-8") as f:
        f.write(f"# Level 1 Results — {timestamp}\n\n")
        f.write(f"**Model:** {model}  \n")
        f.write(f"**Set:** {set_label}  \n")
        f.write(f"**Cases:** {n}  \n")
        f.write(f"**Current:** {curr_score}/{n}  \n")
        f.write(f"**Candidate:** {cand_score}/{n}  \n")
        if cand_h_cases:
            f.write(f"**Handoff (current):** {curr_h_pass}/{len(curr_h_cases)}  \n")
            f.write(f"**Handoff (candidate):** {cand_h_pass}/{len(cand_h_cases)}  \n")
        f.write("\n---\n\n")

        for c in cases:
            f.write(f"## Case {c['i']}: {c['label']}\n\n")
            f.write(f"**Expected:** {c['expected']}  bridge={sorted(c['expected_bridge'])}  handoff_target={c['expected_target']}  \n")
            if c.get("note"):
                f.write(f"**Context:** {c['note']}  \n\n")

            def _htag(h, tgt):
                if h is None: return ""
                return f"  handoff={'✓' if h else f'✗ (expected {tgt})'}"

            f.write(f"**Current:** `{c['curr_op']}` conf={c['curr_conf']:.2f} {'✓' if c['curr_pass'] else '✗'}  targets={c['curr_targets']}{_htag(c['curr_handoff'], c['expected_target'])}  \n")
            f.write(f"> {c['curr_reasoning']}\n\n")
            f.write(f"**Candidate:** `{c['cand_op']}` conf={c['cand_conf']:.2f} {'✓' if c['cand_pass'] else '✗'}  targets={c['cand_targets']}{_htag(c['cand_handoff'], c['expected_target'])}  \n")
            f.write(f"> {c['cand_reasoning']}\n\n")
            f.write("---\n\n")

    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    from zettelkasten.config import load_config, build_fast_llm
    from datetime import datetime, timezone
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--set", choices=["1", "2", "all"], default="1",
                        help="Test set: 1=SYNTHESISE/PROCEED (default), 2=INTEGRATE balance, all=both")
    args = parser.parse_args()

    cases = (TEST_CASES_SET1 if args.set == "1"
             else TEST_CASES_SET2 if args.set == "2"
             else TEST_CASES_SET1 + TEST_CASES_SET2)

    cfg = load_config(ROOT / "zettelkasten.toml")
    llm = build_fast_llm(cfg)
    model = cfg["llm"].get("fast_model", "unknown")

    print(f"Model: {model}")
    print(f"Date:  {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')}")
    print()
    print("=" * 72)
    print("Level 1 — SYNTHESISE vs INTEGRATE")
    print("Current: _STEP1_PROMPT (multi-way, mapped)  vs  Candidate: level1.txt")
    print("=" * 72)

    cluster_text = load_cluster()

    current_score = 0
    candidate_score = 0
    curr_handoff_pass = curr_handoff_total = 0
    cand_handoff_pass = cand_handoff_total = 0
    n = len(cases)
    results = []

    for i, tc in enumerate(cases, 1):
        draft_text = load_draft(tc["draft_file"])
        expected = tc["expected"]
        expected_target = tc.get("expected_target")

        print(f"\nCase {i}/{n}: {tc['label']}")
        print(f"  Expected: {expected}  handoff_target={expected_target}")
        if tc.get("note"):
            print(f"  Context : {tc['note'][:90]}")

        print(f"  Running current prompt...")
        curr = run_current(draft_text, cluster_text, llm)
        print(f"  Running candidate prompt...")
        cand = run_candidate(draft_text, cluster_text, llm)

        curr_op   = normalise(curr.get("operation", "?"))
        cand_op   = cand.get("operation", "?")
        if cand_op not in ("SYNTHESISE", "NOTHING"):
            cand_op = "INTEGRATE"
        curr_conf = curr.get("confidence", 0)
        cand_conf = cand.get("confidence", 0)

        # Operation correctness.
        # PROCEED and INTEGRATE are equivalent (both mean "pass to L2").
        # NOTHING is also acceptable where INTEGRATE/PROCEED expected (draft covered).
        _proceed = {"PROCEED", "INTEGRATE", "NOTHING"}
        curr_ok = curr_op == expected or (expected in ("PROCEED", "INTEGRATE") and curr_op in _proceed)
        cand_ok = cand_op == expected or (expected in ("PROCEED", "INTEGRATE") and cand_op in _proceed)

        # Bridge target check for SYNTHESISE cases
        curr_bridge_ok = check_bridge(curr, tc["expected_bridge"]) if expected == "SYNTHESISE" else True
        cand_bridge_ok = check_bridge(cand, tc["expected_bridge"]) if expected == "SYNTHESISE" else True

        curr_pass = curr_ok and curr_bridge_ok
        cand_pass = cand_ok and cand_bridge_ok

        if curr_pass:
            current_score += 1
        if cand_pass:
            candidate_score += 1

        curr_targets = curr.get("target_note_ids", [])
        cand_targets = cand.get("target_note_ids", [])

        # Handoff check: for INTEGRATE cases with a known L2 target, verify it's in target_note_ids
        curr_handoff = check_handoff(curr, curr_op, expected_target)
        cand_handoff = check_handoff(cand, cand_op, expected_target)
        if curr_handoff is not None:
            curr_handoff_total += 1
            if curr_handoff:
                curr_handoff_pass += 1
        if cand_handoff is not None:
            cand_handoff_total += 1
            if cand_handoff:
                cand_handoff_pass += 1

        def _handoff_tag(h):
            if h is None: return ""
            return f"  handoff={'✓' if h else '✗ (expected ' + str(expected_target) + ')'}"

        print(f"  Current  : {curr_op:<10} conf={curr_conf:.2f}  {'✓' if curr_pass else '✗'}  targets={curr_targets}{_handoff_tag(curr_handoff)}")
        print(f"             {curr.get('reasoning', '')}")
        print(f"  Candidate: {cand_op:<10} conf={cand_conf:.2f}  {'✓' if cand_pass else '✗'}  targets={cand_targets}{_handoff_tag(cand_handoff)}")
        print(f"             {cand.get('reasoning', '')}")

        results.append(dict(
            i=i, label=tc["label"], expected=expected,
            expected_bridge=tc.get("expected_bridge", set()),
            expected_target=expected_target,
            note=tc.get("note", ""),
            curr_op=curr_op, curr_conf=curr_conf, curr_pass=curr_pass,
            curr_targets=curr_targets, curr_reasoning=curr.get("reasoning", ""),
            curr_handoff=curr_handoff,
            cand_op=cand_op, cand_conf=cand_conf, cand_pass=cand_pass,
            cand_targets=cand_targets, cand_reasoning=cand.get("reasoning", ""),
            cand_handoff=cand_handoff,
        ))

    print()
    print("=" * 72)
    print(f"Current  : {current_score}/{n} correct")
    print(f"Candidate: {candidate_score}/{n} correct")
    if cand_handoff_total:
        print(f"\nHandoff accuracy (target in target_note_ids for INTEGRATE cases):")
        print(f"  Current  : {curr_handoff_pass}/{curr_handoff_total}")
        print(f"  Candidate: {cand_handoff_pass}/{cand_handoff_total}")
    print()
    if candidate_score > current_score:
        print("Candidate prompt improves on current. Consider promoting.")
    elif candidate_score == current_score == n:
        print("Both prompts correct on all cases.")
    else:
        print("Review failures above before making changes.")
    print("=" * 72)

    path = save_results(results, model, args.set)
    print(f"\nResults saved to {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
