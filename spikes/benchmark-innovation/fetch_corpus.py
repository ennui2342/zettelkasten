#!/usr/bin/env python3
"""Fetch the benchmark corpus from arxiv.

Retrieves papers on LLM-based multi-agent systems published after the model
training cutoff (August 2025). Papers are saved incrementally as individual
JSON files in corpus/ so a crash loses no already-fetched work. A manifest
is written to corpus/manifest.json at the end.

Two search passes:
  1. cs.MA with LLM/agent keyword filter (multi-agent systems category)
  2. cs.AI + cs.LG with title keyword search (broader catch, server-side filtered)

Results are deduplicated by arxiv ID.

Usage:
  uv run python spikes/benchmark-innovation/fetch_corpus.py
  uv run python spikes/benchmark-innovation/fetch_corpus.py --from 2025-09-01 --to 2026-02-28
  uv run python spikes/benchmark-innovation/fetch_corpus.py --dry-run   # show counts only
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime
from pathlib import Path

CORPUS_DIR = Path(__file__).parent / "corpus"
ARXIV_API = "http://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def arxiv_date(dt: str) -> str:
    """Convert YYYY-MM-DD to arxiv submittedDate format YYYYMMDDHHMMSS."""
    return datetime.strptime(dt, "%Y-%m-%d").strftime("%Y%m%d000000")


def fetch_page(query: str, start: int, max_results: int = 100) -> list[dict]:
    """Fetch one page of results from the arxiv API. Returns list of paper dicts."""
    params = urllib.parse.urlencode({
        "search_query": query,
        "start": start,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    url = f"{ARXIV_API}?{params}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        xml = resp.read()

    root = ET.fromstring(xml)
    papers = []

    for entry in root.findall("atom:entry", NS):
        arxiv_id_url = entry.findtext("atom:id", namespaces=NS) or ""
        arxiv_id = arxiv_id_url.split("/abs/")[-1].split("v")[0]

        published = entry.findtext("atom:published", namespaces=NS) or ""
        title = (entry.findtext("atom:title", namespaces=NS) or "").strip().replace("\n", " ")
        abstract = (entry.findtext("atom:summary", namespaces=NS) or "").strip().replace("\n", " ")
        authors = [
            a.findtext("atom:name", namespaces=NS) or ""
            for a in entry.findall("atom:author", NS)
        ]
        categories = [tag.get("term", "") for tag in entry.findall("atom:category", NS)]
        primary_category = entry.find("arxiv:primary_category", NS)
        primary = primary_category.get("term", "") if primary_category is not None else ""

        papers.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "published": published,
            "primary_category": primary,
            "categories": categories,
            "url": f"https://arxiv.org/abs/{arxiv_id}",
        })

    return papers


def fetch_all(
    query: str,
    date_from: str,
    date_to: str,
    label: str,
    seen: dict[str, dict],
    dry_run: bool = False,
) -> int:
    """Paginate through all results, saving new papers incrementally. Returns count added."""
    date_filter = f"submittedDate:[{arxiv_date(date_from)} TO {arxiv_date(date_to)}]"
    full_query = f"({query}) AND {date_filter}"

    print(f"\n[{label}] query: {full_query}")
    added = 0
    start = 0

    while True:
        print(f"  fetching start={start}...", end=" ", flush=True)
        try:
            page = fetch_page(full_query, start)
        except Exception as e:
            print(f"ERROR: {e}")
            break

        if not page:
            print("done (empty page)")
            break

        new_count = 0
        for paper in page:
            if paper["arxiv_id"] not in seen:
                seen[paper["arxiv_id"]] = paper
                if not dry_run:
                    save_paper(paper)
                new_count += 1
                added += 1

        print(f"{len(page)} fetched, {new_count} new (corpus total: {len(seen)})")

        if len(page) < 100:
            break
        start += 100
        time.sleep(3)  # arxiv rate limit: be polite

    return added


def save_paper(paper: dict) -> None:
    """Save a paper as an individual JSON file."""
    safe_id = paper["arxiv_id"].replace("/", "_")
    path = CORPUS_DIR / f"{safe_id}.json"
    path.write_text(json.dumps(paper, indent=2, ensure_ascii=False))


def write_manifest(seen: dict[str, dict], date_from: str, date_to: str) -> None:
    manifest = {
        "generated": datetime.utcnow().isoformat() + "Z",
        "date_from": date_from,
        "date_to": date_to,
        "total": len(seen),
        "papers": sorted(
            [
                {
                    "arxiv_id": p["arxiv_id"],
                    "title": p["title"],
                    "published": p["published"],
                    "primary_category": p["primary_category"],
                    "url": p["url"],
                }
                for p in seen.values()
            ],
            key=lambda x: x["published"],
            reverse=True,
        ),
    }
    path = CORPUS_DIR / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\nManifest written: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch arxiv benchmark corpus")
    parser.add_argument("--from", dest="date_from", default="2025-09-01")
    parser.add_argument("--to", dest="date_to", default="2026-02-28")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch metadata and print counts but don't save files")
    args = parser.parse_args()

    if not args.dry_run:
        CORPUS_DIR.mkdir(exist_ok=True)

    print(f"Corpus directory: {CORPUS_DIR}")
    print(f"Date range: {args.date_from} to {args.date_to}")
    if args.dry_run:
        print("DRY RUN — no files will be written")

    # Load already-fetched papers to support resuming
    seen: dict[str, dict] = {}
    if CORPUS_DIR.exists():
        for f in CORPUS_DIR.glob("*.json"):
            if f.name == "manifest.json":
                continue
            try:
                paper = json.loads(f.read_text())
                seen[paper["arxiv_id"]] = paper
            except Exception:
                pass
    if seen:
        print(f"Resuming: {len(seen)} papers already in corpus")

    # Pass 1: cs.MA filtered to LLM/agent content
    # cs.MA is the dedicated category but includes classical game theory, robotics,
    # distributed systems. Title search for LLM-era terms focuses the corpus.
    llm_agent_terms = " OR ".join([
        'ti:"multi-agent"',
        'ti:multiagent',
        'ti:"language model"',
        'ti:"large language"',
        'ti:"LLM agent"',
        'ti:"language agent"',
        'ti:"agent framework"',
        'ti:"agent coordination"',
        'ti:"agent collaboration"',
        'ti:"agent system"',
        'ti:"agentic"',
    ])
    fetch_all(
        f"cat:cs.MA AND ({llm_agent_terms})",
        args.date_from, args.date_to,
        "cs.MA + LLM/agent title filter",
        seen, args.dry_run,
    )

    # Pass 2: cs.AI + cs.LG with multi-agent title terms (server-side filtered)
    # Narrower title search avoids the 10K pagination limit.
    multiagent_title_terms = " OR ".join([
        'ti:"multi-agent"',
        'ti:multiagent',
        'ti:"agent framework"',
        'ti:"agent coordination"',
        'ti:"agent collaboration"',
        'ti:"multi agent"',
        'ti:"agent communication"',
        'ti:"agent memory"',
        'ti:"swarm"',
    ])
    fetch_all(
        f"(cat:cs.AI OR cat:cs.LG) AND ({multiagent_title_terms})",
        args.date_from, args.date_to,
        "cs.AI+cs.LG + multi-agent title filter",
        seen, args.dry_run,
    )

    if not args.dry_run:
        write_manifest(seen, args.date_from, args.date_to)

    print(f"\nDone. {len(seen)} papers total.")

    months = Counter(p["published"][:7] for p in seen.values())
    print("\nPapers by month:")
    for month in sorted(months):
        print(f"  {month}: {months[month]}")


if __name__ == "__main__":
    main()
