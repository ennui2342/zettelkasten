#!/usr/bin/env python3
"""Select ~100 papers from the full corpus for benchmark ingestion.

Scoring approach:
  - Score each paper by keyword presence in title + abstract
  - Assign a thematic bucket (framework, coordination, memory, planning,
    evaluation, safety, application)
  - Stratified sample: ~15 per bucket, balanced across months
  - Exclude clearly off-topic papers (classical MARL, pure robotics, game theory)

Output: corpus/selected.json  — the 100 selected papers with scores and buckets.

Usage:
  uv run python spikes/benchmark-innovation/select_corpus.py
  uv run python spikes/benchmark-innovation/select_corpus.py --n 100 --show-buckets
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

CORPUS_DIR = Path(__file__).parent / "corpus"

# ---------------------------------------------------------------------------
# Relevance scoring
# ---------------------------------------------------------------------------

# High-value terms — strong signal of LLM-based multi-agent content
HIGH = [
    r"\bllm agent", r"\bllm-based agent", r"\blarge language model agent",
    r"\bagent framework", r"\bagent architecture", r"\bagent system",
    r"\bmulti.agent llm", r"\bllm multi.agent",
    r"\bagent coordination", r"\bagent collaboration", r"\bagent communication",
    r"\bagent memory", r"\bagent planning", r"\bagent reasoning",
    r"\btool.use", r"\btool use", r"\bfunction call",
    r"\bagentic workflow", r"\bagentic system",
    r"\borchestrat", r"\bsub.agent", r"\bsupervisor agent",
]

# Medium-value terms — relevant but could be non-LLM
MED = [
    r"\blarge language model", r"\bgpt-?[34o]", r"\bclaude", r"\bgemini",
    r"\bautonomous agent", r"\bai agent", r"\bchat", r"\bprompt",
    r"\breasoning agent", r"\bplanning agent",
    r"\bchain.of.thought", r"\breact\b", r"\breflect",
    r"\bemergen", r"\bself.organis", r"\bself.improv",
    r"\bmulti.hop", r"\bworkflow",
]

# Exclusion signals — strong indicator of off-topic content
EXCLUDE = [
    r"\bgame.theoret", r"\bnash equilibri", r"\bmechanism design",
    r"\bswarm robot", r"\bquadrotor", r"\bdrone", r"\buav\b",
    r"\bparticle swarm", r"\bant colony",
    r"\bsupply chain(?! agent)", r"\bstock market(?! agent)",
    r"\bwireless network", r"\bfederated learn(?!.*agent)",
    r"\bimage segment", r"\bobject detect", r"\bcomputer vision(?!.*agent)",
    r"\bformula 1\b", r"\brace strateg",
]

# ---------------------------------------------------------------------------
# Thematic bucketing
# ---------------------------------------------------------------------------

BUCKETS = {
    "framework":     [r"\bframework", r"\barchitecture", r"\bplatform", r"\binfrastructure",
                      r"\bsystem design", r"\borchestrat"],
    "coordination":  [r"\bcoordinat", r"\bcollaborat", r"\bcommunicat", r"\bnegotiat",
                      r"\bconsensus", r"\bdebate", r"\bdiscuss", r"\bemerg"],
    "memory":        [r"\bmemory", r"\bknowledge graph", r"\bknowledge base",
                      r"\bretrieval", r"\brag\b", r"\blong.term", r"\bcontext manag",
                      r"\bforgett", r"\bconsolidat"],
    "planning":      [r"\bplanning", r"\breasoning", r"\bchain.of.thought", r"\breact\b",
                      r"\bdecompos", r"\btask allocation", r"\bgoal", r"\bscaffold"],
    "evaluation":    [r"\bbenchmark", r"\bevaluat", r"\bmetric", r"\bassess",
                      r"\bleaderboard", r"\btest", r"\bsafety", r"\btrust",
                      r"\balign", r"\brobust"],
    "application":   [r"\bcode gen", r"\bsoftware engineer", r"\bweb", r"\bsearch",
                      r"\bresearch agent", r"\bscientific", r"\bmedical",
                      r"\bfinance", r"\bcustomer", r"\bgame\b(?!.*theory)"],
}


def score(paper: dict) -> tuple[int, bool]:
    """Return (relevance_score, is_excluded)."""
    text = (paper["title"] + " " + paper["abstract"]).lower()
    if any(re.search(p, text) for p in EXCLUDE):
        return 0, True
    s = sum(3 for p in HIGH if re.search(p, text))
    s += sum(1 for p in MED if re.search(p, text))
    return s, False


def bucket(paper: dict) -> str:
    """Assign primary thematic bucket."""
    text = (paper["title"] + " " + paper["abstract"]).lower()
    scores = {
        b: sum(1 for p in patterns if re.search(p, text))
        for b, patterns in BUCKETS.items()
    }
    best = max(scores, key=lambda b: scores[b])
    return best if scores[best] > 0 else "framework"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=100, help="Target corpus size")
    parser.add_argument("--show-buckets", action="store_true")
    parser.add_argument("--min-score", type=int, default=2,
                        help="Minimum relevance score to be considered")
    args = parser.parse_args()

    # Load all papers
    papers = []
    for f in CORPUS_DIR.glob("*.json"):
        if f.name in ("manifest.json", "selected.json"):
            continue
        try:
            papers.append(json.loads(f.read_text()))
        except Exception:
            pass

    print(f"Loaded {len(papers)} papers from corpus")

    # Score and filter
    scored = []
    excluded = 0
    low_score = 0
    for p in papers:
        s, is_excl = score(p)
        if is_excl:
            excluded += 1
            continue
        if s < args.min_score:
            low_score += 1
            continue
        p["_score"] = s
        p["_bucket"] = bucket(p)
        scored.append(p)

    print(f"Excluded (off-topic signals): {excluded}")
    print(f"Below min score ({args.min_score}): {low_score}")
    print(f"Eligible papers: {len(scored)}")

    # Show bucket distribution before selection
    by_bucket = defaultdict(list)
    for p in scored:
        by_bucket[p["_bucket"]].append(p)

    print("\nEligible papers by bucket:")
    for b in BUCKETS:
        print(f"  {b}: {len(by_bucket[b])}")

    if args.show_buckets:
        print("\nTop 5 per bucket:")
        for b in BUCKETS:
            print(f"\n  [{b}]")
            top = sorted(by_bucket[b], key=lambda x: x["_score"], reverse=True)[:5]
            for p in top:
                print(f"    ({p['_score']}) [{p['published'][:7]}] {p['title'][:75]}")

    # Stratified selection: proportional to bucket size, capped at ~20 per bucket,
    # within each bucket sort by score then take top-N spread across months.
    target_per_bucket = max(args.n // len(BUCKETS), 5)
    selected = []

    seen_ids: set[str] = set()
    for b in BUCKETS:
        # Sort by score desc; within same score, spread across months by interleaving
        pool = sorted(by_bucket[b], key=lambda x: x["_score"], reverse=True)

        # Group by month, interleave so we pick from different months
        by_month: dict[str, list] = defaultdict(list)
        for p in pool:
            by_month[p["published"][:7]].append(p)
        months = sorted(by_month.keys())

        # Build interleaved list: one from each month in rotation
        interleaved = []
        max_per_month = max(len(v) for v in by_month.values())
        for i in range(max_per_month):
            for m in months:
                if i < len(by_month[m]):
                    interleaved.append(by_month[m][i])

        bucket_selected = []
        for p in interleaved:
            if p["arxiv_id"] not in seen_ids:
                bucket_selected.append(p)
                seen_ids.add(p["arxiv_id"])
            if len(bucket_selected) >= target_per_bucket:
                break

        selected.extend(bucket_selected)

    # Trim to exactly n, prioritising highest scores
    selected = sorted(selected, key=lambda x: x["_score"], reverse=True)[:args.n]

    print(f"\nSelected {len(selected)} papers")

    # Final stats
    from collections import Counter
    bucket_counts = Counter(p["_bucket"] for p in selected)
    month_counts = Counter(p["published"][:7] for p in selected)

    print("\nSelected by bucket:")
    for b in BUCKETS:
        print(f"  {b}: {bucket_counts.get(b, 0)}")

    print("\nSelected by month:")
    for m in sorted(month_counts):
        print(f"  {m}: {month_counts[m]}")

    print("\nSelected papers:")
    for p in sorted(selected, key=lambda x: x["published"], reverse=True):
        print(f"  [{p['published'][:10]}] ({p['_score']:2d}) [{p['_bucket']:<12}] {p['title'][:70]}")

    # Save
    out = [
        {k: v for k, v in p.items() if not k.startswith("_")} | {
            "benchmark_score": p["_score"],
            "benchmark_bucket": p["_bucket"],
        }
        for p in selected
    ]
    out_path = CORPUS_DIR / "selected.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
