#!/usr/bin/env python3
"""Run Form on each scenario's bridging text and cache the output.

Form output is what step 1 actually sees as the draft in real ingestion.
Cached outputs are saved to form_cache/ so iterate_prompt.py and
compare_outputs.py can use them without re-running Form.

Usage:
  uv run --env-file .env python spikes/merge-test/cache_form_outputs.py
  uv run --env-file .env python spikes/merge-test/cache_form_outputs.py --scenario s1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from iterate_prompt import SCENARIOS  # noqa: E402

CACHE_DIR = HERE / "form_cache"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default=None,
                        help="Cache only this scenario key (e.g. s1). Default: all.")
    parser.add_argument("--force", action="store_true",
                        help="Re-run Form even if cached output exists.")
    args = parser.parse_args()

    from zettelkasten.config import load_config, build_llm
    from zettelkasten.form import form_phase

    cfg = load_config(ROOT / "zettelkasten.toml")
    llm = build_llm(cfg)  # Form uses full LLM

    CACHE_DIR.mkdir(exist_ok=True)

    scenarios = SCENARIOS
    if args.scenario:
        scenarios = [s for s in SCENARIOS if s.key == args.scenario]
        if not scenarios:
            print(f"Unknown scenario key {args.scenario!r}. "
                  f"Valid: {[s.key for s in SCENARIOS]}")
            sys.exit(1)

    for scenario in scenarios:
        cache_path = CACHE_DIR / f"{scenario.key}.json"

        if cache_path.exists() and not args.force:
            print(f"[skip] {scenario.key} — cached output exists ({cache_path.name})")
            print(f"       Use --force to re-run.")
            continue

        print(f"[form] {scenario.key} — {scenario.name}")
        print(f"       Bridging text: {len(scenario.bridging_text)} chars")

        drafts = form_phase(scenario.bridging_text, llm)

        print(f"       Drafts produced: {len(drafts)}")
        for i, d in enumerate(drafts):
            print(f"         {i+1}. {d.title!r} ({len(d.body)} chars)")

        # Serialise drafts to JSON (title + body only — no embeddings)
        cache = {
            "scenario_key": scenario.key,
            "scenario_name": scenario.name,
            "bridging_text_len": len(scenario.bridging_text),
            "drafts": [
                {"title": d.title, "body": d.body}
                for d in drafts
            ],
        }
        cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")
        print(f"       Saved: {cache_path}")
        print()

    # Print summary
    print("─" * 60)
    print("Cached Form outputs:")
    for scenario in SCENARIOS:
        cache_path = CACHE_DIR / f"{scenario.key}.json"
        if cache_path.exists():
            data = json.loads(cache_path.read_text())
            titles = [d["title"] for d in data["drafts"]]
            print(f"  {scenario.key}: {len(data['drafts'])} draft(s) — {titles}")
        else:
            print(f"  {scenario.key}: NOT CACHED")


if __name__ == "__main__":
    main()
