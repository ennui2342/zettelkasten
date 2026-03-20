#!/usr/bin/env python3
"""Full step 1 + step 2 output comparison between two prompt variants.

Runs all 5 scenarios through step 1 (variant prompt) + step 2 (fixed prompts)
for two specified variants. Saves generated note content to comparison/ and
prints a side-by-side quality summary.

Usage:
  uv run --env-file .env python spikes/merge-test/compare_outputs.py --a 0 --b 2
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from iterate_prompt import SCENARIOS, PROMPT_VARIANTS, Scenario, _parse_decision, load_form_drafts  # noqa: E402

COMPARISON_DIR = HERE / "comparison"


# ---------------------------------------------------------------------------
# Step 2 execution (inline — no store/embed needed)
# ---------------------------------------------------------------------------

def _parse_title_body(raw: str) -> tuple[str, str]:
    raw = raw.strip()
    for line in raw.splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            rest = raw[raw.index(line) + len(line):]
            return title, rest.strip()
    return "", raw


def run_full(scenario: Scenario, step1_prompt: str, llm_fast, llm_full) -> dict:
    """Run step 1 (fast LLM, variant prompt) then step 2 (full LLM, fixed prompts)."""
    from zettelkasten.prompts import STEP2_PROMPTS

    note_a_text = f"id: z20260101-001\n## {scenario.note_a_title}\n\n{scenario.note_a_body}"
    note_b_text = f"id: z20260101-002\n## {scenario.note_b_title}\n\n{scenario.note_b_body}"
    cluster_text = f"{note_a_text}\n\n---\n\n{note_b_text}"

    # Use cached Form output as draft (first draft; if multiple, prefer one matching expected)
    drafts = load_form_drafts(scenario)
    draft_text = f"## {drafts[0]['title']}\n\n{drafts[0]['body']}"
    # If Form produced multiple drafts, try each and use the one matching expected
    if len(drafts) > 1:
        for d in drafts:
            candidate = f"## {d['title']}\n\n{d['body']}"
            probe = step1_prompt.format(draft=candidate, cluster=cluster_text)
            probe_raw = llm_fast.complete(probe, max_tokens=512, temperature=0.0)
            probe_dec = _parse_decision(probe_raw)
            if probe_dec.get("operation") == scenario.expected:
                draft_text = candidate
                break

    # Step 1 (final)
    s1_prompt = step1_prompt.format(draft=draft_text, cluster=cluster_text)
    s1_raw = llm_fast.complete(s1_prompt, max_tokens=512, temperature=0.0)
    decision = _parse_decision(s1_raw)
    op = decision.get("operation", "NOTHING")
    reasoning = decision.get("reasoning", "")
    confidence = float(decision.get("confidence", 0.0))

    # Step 2 — determine targets based on operation
    if op in ("MERGE", "SYNTHESISE"):
        targets_text = cluster_text  # both notes
    elif op in ("UPDATE", "EDIT"):
        target_ids = decision.get("target_note_ids", [])
        if "z20260101-001" in target_ids or not target_ids:
            targets_text = note_a_text
        else:
            targets_text = note_b_text
    elif op in ("CREATE", "STUB"):
        targets_text = "(none)"
    else:  # NOTHING, SPLIT, unknown
        targets_text = cluster_text

    if op not in STEP2_PROMPTS:
        note_title, note_body = "", f"(no step 2 for operation {op})"
    else:
        s2_template = STEP2_PROMPTS[op]
        s2_prompt = s2_template.format(draft=draft_text, targets=targets_text)
        from zettelkasten.integrate import _STEP2_MAX_TOKENS
        max_tokens = _STEP2_MAX_TOKENS.get(op, 2048)
        s2_raw = llm_full.complete(s2_prompt, max_tokens=max_tokens, temperature=0.3)
        note_title, note_body = _parse_title_body(s2_raw)

    return {
        "key": scenario.key,
        "name": scenario.name,
        "expected": scenario.expected,
        "operation": op,
        "confidence": confidence,
        "reasoning": reasoning,
        "match": op == scenario.expected,
        "note_title": note_title,
        "note_body": note_body,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", type=int, default=0, help="First variant (default: 0)")
    parser.add_argument("--b", type=int, default=2, help="Second variant (default: 2)")
    args = parser.parse_args()

    for v in (args.a, args.b):
        if v not in PROMPT_VARIANTS:
            print(f"Unknown variant {v}. Available: {sorted(PROMPT_VARIANTS)}")
            sys.exit(1)

    from zettelkasten.config import load_config, build_llm, build_fast_llm
    cfg = load_config(ROOT / "zettelkasten.toml")
    llm_full = build_llm(cfg)
    llm_fast = build_fast_llm(cfg)

    COMPARISON_DIR.mkdir(exist_ok=True)

    all_results: dict[int, list[dict]] = {}

    for variant_idx in (args.a, args.b):
        prompt = PROMPT_VARIANTS[variant_idx]
        results = []
        print(f"\nRunning variant {variant_idx}...")
        for scenario in SCENARIOS:
            print(f"  {scenario.key} — {scenario.name[:50]}...", end=" ", flush=True)
            result = run_full(scenario, prompt, llm_fast, llm_full)
            results.append(result)
            mark = "✓" if result["match"] else "✗"
            print(f"[{mark}] {result['operation']}")

            # Save output note
            out_path = COMPARISON_DIR / f"v{variant_idx}_{scenario.key}.md"
            out_path.write_text(
                f"# V{variant_idx} / {scenario.key} — {scenario.name}\n\n"
                f"**Expected:** {scenario.expected}  \n"
                f"**Got:** {result['operation']} (conf={result['confidence']:.2f})  \n"
                f"**Reasoning:** {result['reasoning']}\n\n"
                f"---\n\n"
                f"## {result['note_title']}\n\n"
                f"{result['note_body']}\n",
                encoding="utf-8",
            )

        all_results[variant_idx] = results

    # Print comparison
    va, vb = args.a, args.b
    results_a = {r["key"]: r for r in all_results[va]}
    results_b = {r["key"]: r for r in all_results[vb]}

    print(f"\n{'='*70}")
    print(f"COMPARISON: V{va} vs V{vb}")
    print(f"{'='*70}")

    for scenario in SCENARIOS:
        ra = results_a[scenario.key]
        rb = results_b[scenario.key]
        op_changed = ra["operation"] != rb["operation"]
        title_changed = ra["note_title"] != rb["note_title"]

        print(f"\n{'─'*70}")
        print(f"{scenario.key.upper()} — {scenario.name}  [expected: {scenario.expected}]")
        print(f"  V{va}: {ra['operation']:12s}  title: {ra['note_title'][:50]}")
        print(f"  V{vb}: {rb['operation']:12s}  title: {rb['note_title'][:50]}")
        if op_changed:
            print(f"  *** OPERATION CHANGED ***")

        print(f"\n  V{va} reasoning: {ra['reasoning']}")
        print(f"  V{vb} reasoning: {rb['reasoning']}")

        # Body length delta
        len_a = len(ra["note_body"])
        len_b = len(rb["note_body"])
        delta = len_b - len_a
        print(f"\n  Body length: V{va}={len_a}  V{vb}={len_b}  delta={delta:+d}")
        print(f"  Output files: comparison/v{va}_{scenario.key}.md  vs  comparison/v{vb}_{scenario.key}.md")

    # Score summary
    score_a = sum(1 for r in all_results[va] if r["match"])
    score_b = sum(1 for r in all_results[vb] if r["match"])
    print(f"\n{'='*70}")
    print(f"Score  V{va}: {score_a}/{len(SCENARIOS)}   V{vb}: {score_b}/{len(SCENARIOS)}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
