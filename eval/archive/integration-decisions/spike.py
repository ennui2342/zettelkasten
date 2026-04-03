#!/usr/bin/env python3
"""Spike 3: Integration Decision Quality

Validates H5 and H7 from zettelkasten-memory.md:
  H5 — the integration LLM reliably chooses the right structural operation
       (UPDATE/CREATE/SPLIT/MERGE/SYNTHESISE/NOTHING/STUB)
  H7 — the conservative prior (NOTHING) fires correctly and is not
       systematically under-triggered

Tests 14 cases covering all 7 operations (2 per operation, except UPDATE ×3
and CREATE ×1).  Each case runs 3 times (temperature 0, 0.3, 0.3) to measure
consistency.

Run:
  docker compose run --rm dev python spikes/spike3-integration/spike.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if "SSL_CERT_FILE" in os.environ and not os.path.exists(os.environ["SSL_CERT_FILE"]):
    del os.environ["SSL_CERT_FILE"]

import anthropic

SPIKE_DIR = Path(__file__).parent
RESULTS_PATH = SPIKE_DIR / "results.md"

MODEL = "claude-opus-4-6"
VALID_OPERATIONS = {"UPDATE", "CREATE", "SPLIT", "MERGE", "SYNTHESISE", "NOTHING", "STUB"}

client = anthropic.Anthropic()


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

INTEGRATION_PROMPT = """\
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

For UPDATE and CREATE, if the draft contradicts an existing note rather than \
adding to it, use CREATE and add a `contradicts` link to the conflicting \
note — keep competing views as separate notes.

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

def load_test_cases() -> list[dict]:
    path = SPIKE_DIR / "test-cases.json"
    return json.loads(path.read_text())


def load_note(rel_path: str) -> str:
    return (SPIKE_DIR / rel_path).read_text().strip()


def build_cluster_text(cluster_paths: list[str]) -> str:
    if not cluster_paths:
        return "(empty — no existing notes in cluster)"
    parts = []
    for path in cluster_paths:
        parts.append(load_note(path))
    return "\n\n---\n\n".join(parts)


def call(prompt: str, temperature: float) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def parse_decision(raw: str) -> dict:
    """Extract JSON from response, stripping any markdown fences."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"operation": "PARSE_ERROR", "target_note_ids": [], "reasoning": raw, "confidence": 0.0}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError as e:
        return {"operation": "PARSE_ERROR", "target_note_ids": [], "reasoning": str(e), "confidence": 0.0}


def run_case(case: dict) -> list[dict]:
    draft = load_note(case["draft"])
    cluster = build_cluster_text(case["cluster"])
    prompt = INTEGRATION_PROMPT.format(draft=draft, cluster=cluster)

    results = []
    for temp in [0.0, 0.3, 0.3]:
        raw = call(prompt, temperature=temp)
        decision = parse_decision(raw)
        decision["raw"] = raw
        results.append(decision)
    return results


# ---------------------------------------------------------------------------
# Results writer
# ---------------------------------------------------------------------------

OPERATIONS = ["UPDATE", "CREATE", "NOTHING", "STUB", "SPLIT", "MERGE", "SYNTHESISE"]


def write_results(all_results: list[dict]) -> None:
    if RESULTS_PATH.exists():
        runs = sorted(SPIKE_DIR.glob("results-run*.md"))
        next_run = len(runs) + 1
        shutil.copy(RESULTS_PATH, SPIKE_DIR / f"results-run{next_run}.md")
        print(f"  Archived previous results as results-run{next_run}.md")

    lines = [
        "# Spike 3 Results — Integration Decision Quality",
        "",
        f"*Run: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        f"*Model: {MODEL}*",
        "",
        "---",
        "",
        "## Per-case results",
        "",
    ]

    correct = 0
    total = 0
    consistent = 0  # all 3 runs agree
    confusion: dict[tuple[str, str], int] = {}  # (expected, actual) -> count

    for entry in all_results:
        case = entry["case"]
        runs = entry["runs"]
        expected = case["expected_operation"]

        ops = [r["operation"] for r in runs]
        majority = Counter(ops).most_common(1)[0][0]
        all_agree = len(set(ops)) == 1

        match = majority == expected
        if match:
            correct += 1
        total += 1
        if all_agree:
            consistent += 1

        for op in ops:
            key = (expected, op)
            confusion[key] = confusion.get(key, 0) + 1

        lines += [
            f"### {case['id']} — expected {expected}",
            "",
            f"*{case['description']}*",
            "",
            "| Run | Operation | Confidence | Reasoning |",
            "|-----|-----------|------------|-----------|",
        ]
        for i, r in enumerate(runs):
            temp_label = "temp=0" if i == 0 else "temp=0.3"
            op = r.get("operation", "?")
            conf = r.get("confidence", 0.0)
            reason = r.get("reasoning", "").replace("|", "\\|").replace("\n", " ")[:120]
            lines.append(f"| {i+1} ({temp_label}) | **{op}** | {conf:.2f} | {reason} |")

        lines += [
            "",
            f"**Majority decision:** {majority} | **All agree:** {'yes' if all_agree else 'no'} | "
            f"**Match expected:** {'✓' if match else '✗'}",
            "",
            "---",
            "",
        ]

    # Summary
    lines += [
        "## Summary",
        "",
        f"- Cases: {total}",
        f"- Correct (majority matches expected): {correct}/{total} ({100*correct//total}%)",
        f"- Consistent (all 3 runs agree): {consistent}/{total}",
        "",
        "### Confusion matrix (expected → actual, across all runs)",
        "",
        "| Expected \\ Actual | " + " | ".join(OPERATIONS) + " |",
        "|" + "----|" * (len(OPERATIONS) + 1),
    ]
    for exp in OPERATIONS:
        row = [exp]
        for act in OPERATIONS:
            count = confusion.get((exp, act), 0)
            row.append(str(count) if count else ".")
        lines.append("| " + " | ".join(row) + " |")

    lines += [
        "",
        "---",
        "",
        "## Evaluation notes",
        "",
        "*(Fill in after reviewing output)*",
        "",
        "### Operation reliability",
        "- UPDATE: [fill in]",
        "- CREATE: [fill in]",
        "- NOTHING: [fill in — was it under-triggered?]",
        "- STUB: [fill in]",
        "- SPLIT: [fill in]",
        "- MERGE: [fill in]",
        "- SYNTHESISE: [fill in]",
        "",
        "### Failure analysis",
        "- Most confused pair: [fill in]",
        "- Systematic bias observed: [fill in]",
        "",
        "### Prompt iteration needed",
        "- [fill in]",
        "",
        "## Go / No-go",
        "",
        "[ ] Go — ≥75% correct, UPDATE synthesised (not appended), NOTHING fires correctly",
        "[ ] No-go — iterate prompt",
        "",
        "**Recommendation:** [fill in]",
    ]

    RESULTS_PATH.write_text("\n".join(lines))
    print(f"  Results written to {RESULTS_PATH}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    cases = load_test_cases()
    print(f"Loaded {len(cases)} test cases\n")

    all_results = []
    for case in cases:
        print(f"Running {case['id']} (expected: {case['expected_operation']})...")
        runs = run_case(case)
        ops = [r["operation"] for r in runs]
        majority = Counter(ops).most_common(1)[0][0]
        match = "✓" if majority == case["expected_operation"] else "✗"
        print(f"  → {ops}  majority={majority}  {match}")
        all_results.append({"case": case, "runs": runs})

    print("\nWriting results...")
    write_results(all_results)
    print("Done. Review results.md and fill in evaluation notes.")


if __name__ == "__main__":
    main()
