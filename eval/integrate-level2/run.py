#!/usr/bin/env python3
"""Model test: Level 2 — CREATE vs UPDATE vs NOTHING.

Level 2 is the second node of the integration decision tree. It receives the
cluster identified by level 1 (~4 notes) and decides:

  UPDATE  — draft extends an existing note on the same topic; select target
  CREATE  — draft introduces a new topic; create a new note
  NOTHING — draft is already fully covered; no action needed

Two prompts compared:
  Current   — _L2_PROMPT (CREATE / UPDATE / NOTHING)
  Candidate — prompts/level2.txt (focused three-way decision)

Usage:
  uv run --env-file .env python eval/integrate-level2/run.py
  uv run --env-file .env python eval/integrate-level2/run.py --only update
  uv run --env-file .env python eval/integrate-level2/run.py --only create
  uv run --env-file .env python eval/integrate-level2/run.py --only nothing
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
NOTES_DIR = HERE / "data" / "notes"
DRAFTS_DIR = HERE / "data" / "drafts"
RESULTS_DIR = HERE / "results"

import sys
sys.path.insert(0, str(ROOT / "src"))

_CANDIDATE_PROMPT = (HERE / "prompts" / "level2.txt").read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------
# Cluster is the pre-filtered set level 1 would pass to level 2.
# STUB maps to CREATE (new topic, sparse cluster).
# SPLIT maps to UPDATE (the conflated note needs updating; level 3 decides EDIT/SPLIT).
# ---------------------------------------------------------------------------

TEST_CASES = [
    # --- UPDATE ---
    dict(
        group="update",
        label="UPDATE: testing-effect draft fills elaborative interrogation gap",
        draft_file="testing-effect-draft.md",
        cluster_files=["testing-effect.md", "spaced-repetition.md", "encoding-and-memory-formation.md"],
        expected="UPDATE",
        expected_target="z20260314-002",
        note="Draft adds elaborative interrogation as equivalent mechanism to testing effect.",
    ),
    dict(
        group="update",
        label="UPDATE: spaced-repetition draft resolves retrieval-difficulty mechanism",
        draft_file="spaced-repetition-draft.md",
        cluster_files=["spaced-repetition.md", "testing-effect.md", "spaced-learning.md", "forgetting-curve.md"],
        expected="UPDATE",
        expected_target="z20260314-001",
        note="Draft resolves open question: retrieval difficulty is a mechanism, not just a side effect.",
    ),
    dict(
        group="update",
        label="UPDATE: external-memory draft answers open question about encoding properties",
        draft_file="external-memory-draft.md",
        cluster_files=["external-memory-systems.md", "encoding-and-memory-formation.md", "retrieval-cues.md"],
        expected="UPDATE",
        expected_target="z20260314-003",
        note="Draft fills the documented gap: active engagement and retrieval friction produce internal encoding.",
    ),
    # --- UPDATE (SPLIT cases — same note, level 3 will decide EDIT/SPLIT) ---
    dict(
        group="update",
        label="UPDATE→SPLIT: interleaved-practice draft targets practice-strategies note",
        draft_file="interleaved-practice-split-draft.md",
        cluster_files=["practice-strategies.md", "distributed-practice.md", "spaced-repetition.md"],
        expected="UPDATE",
        expected_target="z20260314-007",
        note="SPLIT-1 ground truth. At level 2 this is UPDATE — the note conflates two topics; level 3 splits.",
    ),
    dict(
        group="update",
        label="UPDATE→SPLIT: working-memory draft targets memory-systems-overview note",
        draft_file="working-memory-split-draft.md",
        cluster_files=["memory-systems-overview.md", "encoding-and-memory-formation.md", "retrieval-cues.md", "context-dependent-memory.md"],
        expected="UPDATE",
        expected_target="z20260314-008",
        note="SPLIT-2 ground truth. At level 2 this is UPDATE — level 3 will decide to split the note.",
    ),
    # --- CREATE ---
    dict(
        group="create",
        label="CREATE: generation-effect draft — no existing note covers this topic",
        draft_file="generation-effect-create-draft.md",
        # generation-effect.md excluded: it does not exist yet in this scenario (this draft creates it).
        # Cluster is what retrieval returns for a draft about generation/encoding depth.
        cluster_files=["encoding-and-memory-formation.md", "testing-effect.md", "massed-practice.md"],
        expected="CREATE",
        expected_target=None,
        note="Cluster has only adjacent notes (encoding depth, retrieval practice). Generation effect is a distinct topic warranting its own note.",
    ),
    dict(
        group="create",
        label="CREATE: sleep-consolidation stub — new topic not in cluster",
        draft_file="sleep-consolidation-stub-draft.md",
        cluster_files=["spaced-learning.md", "spaced-repetition.md", "forgetting-curve.md", "memory-systems-overview.md"],
        expected="CREATE",
        expected_target=None,
        note="STUB-1 ground truth. Sleep/hippocampal replay is not covered by any cluster note.",
    ),
    # --- NOTHING ---
    dict(
        group="nothing",
        label="NOTHING: massed-practice draft already fully covered",
        draft_file="massed-practice-nothing-draft.md",
        cluster_files=["massed-practice.md", "practice-strategies.md", "distributed-practice.md", "spaced-repetition.md"],
        expected="NOTHING",
        expected_target=None,
        note="Existing note covers mechanism, empirical finding, fluency illusion comprehensively.",
    ),
    dict(
        group="nothing",
        label="NOTHING: forgetting-curve draft already fully covered",
        draft_file="forgetting-curve-nothing-draft.md",
        cluster_files=["forgetting-curve.md", "spaced-repetition.md", "spaced-learning.md", "massed-practice.md"],
        expected="NOTHING",
        expected_target=None,
        note="Existing note covers Ebbinghaus, exponential decay, savings effect, and timing implications.",
    ),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_note(filename: str) -> str:
    path = NOTES_DIR / filename
    text = path.read_text(encoding="utf-8")
    id_match = re.search(r"^id:\s*(\S+)", text, re.MULTILINE)
    note_id = id_match.group(1) if id_match else path.stem
    body = re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL).strip()
    return f"id: {note_id}\n{body}"


def load_cluster(filenames: list[str]) -> str:
    return "\n\n---\n\n".join(load_note(f) for f in filenames)


def load_draft(filename: str) -> str:
    text = (DRAFTS_DIR / filename).read_text(encoding="utf-8")
    return re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL).strip()


def parse_decision(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"operation": "PARSE_ERROR", "reasoning": raw[:200], "confidence": 0.0, "target_note_ids": []}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {"operation": "PARSE_ERROR", "reasoning": raw[:200], "confidence": 0.0, "target_note_ids": []}


def run_current(draft: str, cluster: str, llm) -> dict:
    from zettelkasten.prompts import _L2_PROMPT
    raw = llm.complete(_L2_PROMPT.format(draft=draft, cluster=cluster), max_tokens=512, temperature=0.0)
    result = parse_decision(raw)
    if result.get("operation") not in ("UPDATE", "CREATE", "NOTHING"):
        result["operation"] = "CREATE"
    return result


def run_candidate(draft: str, cluster: str, llm) -> dict:
    raw = llm.complete(_CANDIDATE_PROMPT.format(draft=draft, cluster=cluster), max_tokens=512, temperature=0.0)
    result = parse_decision(raw)
    if result.get("operation") not in ("UPDATE", "CREATE", "NOTHING"):
        result["operation"] = "CREATE"
    return result


def check_target(result: dict, expected_target: str | None) -> bool:
    if expected_target is None:
        return True
    targets = result.get("target_note_ids", [])
    return expected_target in targets


def save_results(cases: list[dict], model: str) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
    path = RESULTS_DIR / f"run_{timestamp}.md"

    curr_score = sum(1 for c in cases if c["curr_pass"])
    cand_score = sum(1 for c in cases if c["cand_pass"])
    n = len(cases)

    with path.open("w", encoding="utf-8") as f:
        f.write(f"# Level 2 Results — {timestamp}\n\n")
        f.write(f"**Model:** {model}  \n")
        f.write(f"**Cases:** {n}  \n")
        f.write(f"**Current:** {curr_score}/{n}  \n")
        f.write(f"**Candidate:** {cand_score}/{n}  \n\n")
        f.write("---\n\n")

        for c in cases:
            f.write(f"## Case {c['i']}: {c['label']}\n\n")
            f.write(f"**Expected:** {c['expected']}  target={c['expected_target']}  \n")
            if c.get("note"):
                f.write(f"**Context:** {c['note']}  \n")
            f.write(f"**Cluster:** {', '.join(c['cluster_files'])}  \n\n")
            f.write(f"**Current:** `{c['curr_op']}` conf={c['curr_conf']:.2f} {'✓' if c['curr_pass'] else '✗'}  targets={c['curr_targets']}  \n")
            f.write(f"> {c['curr_reasoning']}\n\n")
            f.write(f"**Candidate:** `{c['cand_op']}` conf={c['cand_conf']:.2f} {'✓' if c['cand_pass'] else '✗'}  targets={c['cand_targets']}  \n")
            f.write(f"> {c['cand_reasoning']}\n\n")
            f.write("---\n\n")

    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    from zettelkasten.config import load_config, build_fast_llm

    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["update", "create", "nothing", "all"], default="all")
    args = parser.parse_args()

    cases = [tc for tc in TEST_CASES if args.only == "all" or tc["group"] == args.only]

    cfg = load_config(ROOT / "zettelkasten.toml")
    llm = build_fast_llm(cfg)
    model = cfg["llm"].get("fast_model", "unknown")

    print(f"Model: {model}")
    print(f"Date:  {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')}")
    print(f"Cases: {len(cases)} ({args.only})")
    print()
    print("=" * 72)
    print("Level 2 — CREATE / UPDATE / NOTHING")
    print("Current: _L2_PROMPT  vs  Candidate: level2.txt")
    print("=" * 72)

    results = []
    curr_score = 0
    cand_score = 0

    for i, tc in enumerate(cases, 1):
        draft = load_draft(tc["draft_file"])
        cluster = load_cluster(tc["cluster_files"])

        print(f"\nCase {i}/{len(cases)}: {tc['label']}")
        print(f"  Expected : {tc['expected']}  target={tc['expected_target']}")
        if tc.get("note"):
            print(f"  Context  : {tc['note'][:80]}")

        curr = run_current(draft, cluster, llm)
        cand = run_candidate(draft, cluster, llm)

        curr_op, cand_op = curr.get("operation"), cand.get("operation")
        curr_conf, cand_conf = curr.get("confidence", 0), cand.get("confidence", 0)
        curr_targets = curr.get("target_note_ids", [])
        cand_targets = cand.get("target_note_ids", [])

        curr_ok = curr_op == tc["expected"]
        cand_ok = cand_op == tc["expected"]
        curr_target_ok = check_target(curr, tc["expected_target"])
        cand_target_ok = check_target(cand, tc["expected_target"])
        curr_pass = curr_ok and curr_target_ok
        cand_pass = cand_ok and cand_target_ok

        if curr_pass: curr_score += 1
        if cand_pass: cand_score += 1

        print(f"  Current  : {curr_op:<8} conf={curr_conf:.2f}  {'✓' if curr_pass else '✗'}  targets={curr_targets}")
        print(f"             {curr.get('reasoning', '')}")
        print(f"  Candidate: {cand_op:<8} conf={cand_conf:.2f}  {'✓' if cand_pass else '✗'}  targets={cand_targets}")
        print(f"             {cand.get('reasoning', '')}")

        results.append(dict(
            i=i, label=tc["label"], expected=tc["expected"],
            expected_target=tc["expected_target"], note=tc.get("note", ""),
            cluster_files=tc["cluster_files"],
            curr_op=curr_op, curr_conf=curr_conf, curr_pass=curr_pass,
            curr_targets=curr_targets, curr_reasoning=curr.get("reasoning", ""),
            cand_op=cand_op, cand_conf=cand_conf, cand_pass=cand_pass,
            cand_targets=cand_targets, cand_reasoning=cand.get("reasoning", ""),
        ))

    print()
    print("=" * 72)
    print(f"Current  : {curr_score}/{len(cases)} correct")
    print(f"Candidate: {cand_score}/{len(cases)} correct")
    print()
    if cand_score > curr_score:
        print("Candidate improves on current.")
    elif cand_score == curr_score == len(cases):
        print("Both prompts correct on all cases.")
    else:
        print("Review failures above before making changes.")
    print("=" * 72)

    path = save_results(results, model)
    print(f"\nResults saved to {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
