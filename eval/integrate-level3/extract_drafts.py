#!/usr/bin/env python3
"""Extract Form-phase drafts from the problematic papers for level 3 test cases.

Runs the real Form phase on OSC (2509.04876), Project Synapse (2601.08156),
and Agentic AI (2601.12560) — the three papers whose drafts triggered the
bad SPLIT operations in the 2026-03-18 benchmark run.

Outputs one markdown file per paper into data/form_drafts/, listing all
draft notes extracted. Pick the draft(s) most relevant to the target note
and record them as TEST_CASES entries in run.py.

Usage:
  uv run --env-file .env python eval/integrate-level3/extract_drafts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
PAPERS_DIR = ROOT / "spikes/benchmark-innovation/corpus/papers"
OUT_DIR = HERE / "data" / "form_drafts"

# Papers that produced the bad SPLITs
PAPERS = {
    "osc":           "2509.04876",   # paper triggering z001 → SPLIT → z024
    "project_synapse": "2601.08156", # paper triggering z001 → SPLIT → z029
    "agentic_ai":    "2601.12560",   # paper triggering z027 → SPLIT → z042
}


def main() -> None:
    sys.path.insert(0, str(ROOT / "src"))
    from zettelkasten.config import load_config, build_llm
    from zettelkasten.form import form_phase

    cfg = load_config(ROOT / "zettelkasten.toml")
    llm = build_llm(cfg)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for name, arxiv_id in PAPERS.items():
        txt_path = PAPERS_DIR / f"{arxiv_id}.txt"
        if not txt_path.exists():
            print(f"SKIP {name}: {txt_path} not found")
            continue

        text = txt_path.read_text(encoding="utf-8")
        print(f"\n{'='*60}")
        print(f"Running Form on {name} ({arxiv_id}) — {len(text):,} chars")

        drafts = form_phase(text, llm)
        print(f"  Extracted {len(drafts)} draft(s)")

        out_path = OUT_DIR / f"{name}.md"
        lines = [f"# Form drafts — {name} ({arxiv_id})\n"]
        for i, d in enumerate(drafts, 1):
            lines.append(f"## Draft {i}: {d.title}\n")
            lines.append(d.body)
            lines.append("\n")
            print(f"  {i}. {d.title[:65]}  ({len(d.body):,} chars)")

        out_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  Written to {out_path.relative_to(ROOT)}")

    print(f"\nDone. Review data/form_drafts/ and pick drafts for TEST_CASES in run.py")


if __name__ == "__main__":
    main()
