#!/usr/bin/env python3
"""Download full paper text for the selected benchmark corpus.

Tries arxiv HTML first (https://arxiv.org/html/{id}), falls back to PDF
extraction via trafilatura if HTML is unavailable or extraction fails.
Saves each paper as a plain text file in corpus/papers/{arxiv_id}.txt,
suitable for direct ingestion by `zettelkasten ingest`.

Already-downloaded papers are skipped, so the script is safe to re-run.

Usage:
  uv run python spikes/benchmark-innovation/download_papers.py
  uv run python spikes/benchmark-innovation/download_papers.py --limit 10  # test run
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import trafilatura

CORPUS_DIR = Path(__file__).parent / "corpus"
PAPERS_DIR = CORPUS_DIR / "papers"
SELECTED_FILE = CORPUS_DIR / "selected.json"


def fetch_html(arxiv_id: str) -> str | None:
    """Try to fetch and extract text from arxiv HTML version."""
    url = f"https://arxiv.org/html/{arxiv_id}"
    html = trafilatura.fetch_url(url)
    if not html:
        return None
    text = trafilatura.extract(
        html,
        include_tables=False,
        include_comments=False,
        no_fallback=False,
    )
    # HTML pages with no real content (redirect to abs page, etc.) are short
    if not text or len(text) < 2000:
        return None
    return text


def fetch_pdf(arxiv_id: str) -> str | None:
    """Fallback: fetch PDF version and extract text via trafilatura."""
    url = f"https://arxiv.org/pdf/{arxiv_id}"
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    text = trafilatura.extract(downloaded, no_fallback=False)
    if not text or len(text) < 2000:
        return None
    return text


def format_document(paper: dict, text: str) -> str:
    """Prepend metadata header to extracted text."""
    authors = ", ".join(paper["authors"][:5])
    if len(paper["authors"]) > 5:
        authors += " et al."
    return (
        f"Title: {paper['title']}\n"
        f"Authors: {authors}\n"
        f"Published: {paper['published'][:10]}\n"
        f"Source: {paper['url']}\n"
        f"ArXiv ID: {paper['arxiv_id']}\n\n"
        f"{text}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Download full paper text")
    parser.add_argument("--limit", type=int, default=0,
                        help="Only download this many papers (0 = all, for testing)")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Seconds between requests (default: 2.0)")
    args = parser.parse_args()

    PAPERS_DIR.mkdir(parents=True, exist_ok=True)

    papers = json.loads(SELECTED_FILE.read_text())
    if args.limit:
        papers = papers[:args.limit]

    total = len(papers)
    downloaded = 0
    skipped = 0
    failed = []

    for i, paper in enumerate(papers, 1):
        arxiv_id = paper["arxiv_id"]
        safe_id = arxiv_id.replace("/", "_")
        out_path = PAPERS_DIR / f"{safe_id}.txt"

        if out_path.exists():
            skipped += 1
            print(f"[{i}/{total}] SKIP  {arxiv_id} (already downloaded)")
            continue

        print(f"[{i}/{total}] {arxiv_id}  {paper['title'][:60]}", end=" ... ", flush=True)

        # Try HTML first
        text = fetch_html(arxiv_id)
        source = "html"

        if not text:
            print("html failed, trying pdf", end=" ... ", flush=True)
            text = fetch_pdf(arxiv_id)
            source = "pdf"

        if not text:
            print("FAILED")
            failed.append(arxiv_id)
            time.sleep(args.delay)
            continue

        doc = format_document(paper, text)
        out_path.write_text(doc, encoding="utf-8")
        print(f"OK ({source}, {len(text):,} chars)")
        downloaded += 1
        time.sleep(args.delay)

    print(f"\n{'='*50}")
    print(f"Downloaded: {downloaded}")
    print(f"Skipped (already exist): {skipped}")
    print(f"Failed: {len(failed)}")
    if failed:
        print("Failed IDs:")
        for fid in failed:
            print(f"  {fid}")


if __name__ == "__main__":
    main()
