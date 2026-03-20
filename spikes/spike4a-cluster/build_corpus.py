#!/usr/bin/env python3
"""Build Wikipedia corpus for Spike 4A cluster retrieval evaluation.

Resumable: saves intermediate state to JSON caches so a failed run picks up
where it left off rather than starting from scratch.

  articles_cache.json  -- article data (title, intro, pageid); written once
  links_cache.json     -- per-article link lists; updated incrementally

Run:
  docker compose run --rm dev python spikes/spike4a-cluster/build_corpus.py
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

SPIKE_DIR = Path(__file__).parent
CORPUS_DIR = SPIKE_DIR / "corpus"
ARTICLES_CACHE = SPIKE_DIR / "articles_cache.json"
LINKS_CACHE = SPIKE_DIR / "links_cache.json"

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_HEADERS = {
    "User-Agent": "aswarm-spike4a/1.0 (zettelkasten research spike; contact via github)"
}

CATEGORIES = [
    "Memory",
    "Memory_processes",
    "Learning_and_memory",
    "Mnemonics",
    "Educational_psychology",
    "Cognitive_psychology",
    "Attention",
    "Metacognition",
]

MAX_ARTICLES = 300
MIN_INTRO_WORDS = 80

SKIP_PREFIXES = (
    "List of", "Timeline of", "Outline of", "Index of",
    "Glossary of", "Template:", "Category:", "Wikipedia:",
)


# ---------------------------------------------------------------------------
# Wikipedia API — with retry / backoff
# ---------------------------------------------------------------------------

def wiki_get(params: dict, timeout: int = 15) -> dict:
    """GET the Wikipedia API with exponential backoff on 429/5xx."""
    delay = 1.0
    for attempt in range(6):
        r = requests.get(WIKI_API, params=params, headers=WIKI_HEADERS, timeout=timeout)
        if r.status_code == 429 or r.status_code >= 500:
            wait = delay * (2 ** attempt)
            print(f"\n  Rate limited / server error ({r.status_code}), waiting {wait:.0f}s...")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Wikipedia API repeatedly rate-limited; aborting.")


def get_category_members(category: str) -> list[str]:
    titles = []
    params: dict = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmtype": "page",
        "cmnamespace": 0,
        "cmlimit": 500,
        "format": "json",
    }
    while True:
        data = wiki_get(params)
        for member in data["query"]["categorymembers"]:
            titles.append(member["title"])
        if "continue" not in data:
            break
        params["cmcontinue"] = data["continue"]["cmcontinue"]
        time.sleep(0.5)
    return titles


def get_article_batch(titles: list[str]) -> dict:
    params = {
        "action": "query",
        "titles": "|".join(titles[:20]),
        "prop": "extracts|info",
        "exintro": True,
        "explaintext": True,
        "inprop": "url",
        "format": "json",
    }
    return wiki_get(params)["query"]["pages"]


def get_article_links(title: str) -> list[str]:
    links = []
    params: dict = {
        "action": "query",
        "titles": title,
        "prop": "links",
        "pllimit": 500,
        "plnamespace": 0,
        "format": "json",
    }
    while True:
        data = wiki_get(params)
        for page in data["query"]["pages"].values():
            for link in page.get("links", []):
                links.append(link["title"])
        if "continue" not in data:
            break
        params["plcontinue"] = data["continue"]["plcontinue"]
        time.sleep(0.3)
    return links


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def should_skip(title: str, intro: str) -> bool:
    if any(title.startswith(p) for p in SKIP_PREFIXES):
        return True
    if "(disambiguation)" in title:
        return True
    if len(intro.split()) < MIN_INTRO_WORDS:
        return True
    return False


def first_sentence(text: str) -> str:
    text = text.strip()
    match = re.match(r"([^.!?]*(?:\([^)]*\))?[^.!?]*[.!?])", text)
    return match.group(1).strip() if match else text[:200].strip()


def note_id(pageid: int) -> str:
    return f"wiki-{pageid}"


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50]


def salience_from_length(intro: str) -> float:
    words = len(intro.split())
    return round(min(1.0, max(0.3, words / 500)), 2)


# ---------------------------------------------------------------------------
# Phase 1: collect articles (resumable)
# ---------------------------------------------------------------------------

def collect_articles() -> dict[int, dict]:
    if ARTICLES_CACHE.exists():
        print("Loading articles from cache...")
        raw = json.loads(ARTICLES_CACHE.read_text())
        articles = {int(k): v for k, v in raw.items()}
        print(f"  {len(articles)} articles loaded")
        return articles

    print("Collecting article titles from categories...")
    all_titles: set[str] = set()
    for cat in CATEGORIES:
        titles = get_category_members(cat)
        print(f"  Category:{cat} → {len(titles)} articles")
        all_titles.update(titles)
        time.sleep(0.5)
    print(f"\nTotal unique titles: {len(all_titles)}")

    title_list = list(all_titles)
    articles: dict[int, dict] = {}
    batch_limit = MAX_ARTICLES * 2

    print(f"Fetching article data (up to {batch_limit} candidates)...")
    for i in range(0, min(len(title_list), batch_limit), 20):
        batch = title_list[i : i + 20]
        pages = get_article_batch(batch)
        for page in pages.values():
            if "missing" in page:
                continue
            pageid = page.get("pageid")
            if not pageid:
                continue
            title = page["title"]
            intro = page.get("extract", "").strip()
            if not should_skip(title, intro):
                articles[pageid] = {
                    "title": title,
                    "intro": intro,
                    "pageid": pageid,
                    "context": first_sentence(intro),
                    "salience": salience_from_length(intro),
                }
        time.sleep(0.2)
        print(f"  {min(i + 20, batch_limit)}/{batch_limit} processed, "
              f"{len(articles)} kept so far", end="\r")
        if len(articles) >= MAX_ARTICLES:
            break

    articles = dict(list(articles.items())[:MAX_ARTICLES])
    print(f"\nKept {len(articles)} articles after filtering")

    ARTICLES_CACHE.write_text(json.dumps(articles))
    print(f"  Saved to {ARTICLES_CACHE}")
    return articles


# ---------------------------------------------------------------------------
# Phase 2: fetch links (resumable — saves after each article)
# ---------------------------------------------------------------------------

def collect_links(articles: dict[int, dict]) -> dict[int, list[int]]:
    title_to_pageid: dict[str, int] = {a["title"]: pid for pid, a in articles.items()}

    # Load existing progress
    links_cache: dict[str, list[int]] = {}
    if LINKS_CACHE.exists():
        raw = json.loads(LINKS_CACHE.read_text())
        links_cache = {k: v for k, v in raw.items()}

    already_done = set(links_cache.keys())
    remaining = [(pid, a) for pid, a in articles.items()
                 if str(pid) not in already_done]

    if already_done:
        print(f"Resuming links: {len(already_done)} already fetched, "
              f"{len(remaining)} remaining")
    else:
        print(f"Fetching in-corpus links for {len(articles)} articles...")

    for i, (pageid, article) in enumerate(remaining):
        raw_links = get_article_links(article["title"])
        internal = [title_to_pageid[t] for t in raw_links if t in title_to_pageid]
        links_cache[str(pageid)] = internal
        # Save incrementally after every article
        LINKS_CACHE.write_text(json.dumps(links_cache))
        time.sleep(0.8)  # conservative delay to avoid 429
        if (i + 1) % 10 == 0:
            print(f"  {len(already_done) + i + 1}/{len(articles)}")

    return {int(k): v for k, v in links_cache.items()}


# ---------------------------------------------------------------------------
# Phase 3: write notes
# ---------------------------------------------------------------------------

def write_notes(articles: dict[int, dict], links: dict[int, list[int]]) -> None:
    CORPUS_DIR.mkdir(exist_ok=True)

    existing = {p.stem.split("-")[0] + "-" + p.stem.split("-")[1]
                for p in CORPUS_DIR.glob("wiki-*.md")}

    written = 0
    for pageid, article in articles.items():
        nid = note_id(pageid)
        # Skip if already written (idempotent)
        slug = slugify(article["title"])
        filename = f"{nid}-{slug}.md"
        if (CORPUS_DIR / filename).exists():
            continue

        links_block = ""
        for linked_pid in links.get(pageid, [])[:30]:
            links_block += f"  - id: {note_id(linked_pid)}\n"
        links_or_empty = links_block if links_block else "  []\n"

        context_line = article["context"].replace("\n", " ").replace('"', "'")
        wiki_source = article["title"].replace(" ", "_")

        note = f"""\
---
id: {nid}
type: topic
confidence: 0.75
salience: {article['salience']}
stable: true
context: >
  {context_line}
tags: [wikipedia, cognitive-science]
sources:
  - wikipedia:{wiki_source}
links:
{links_or_empty}\
created: 2026-03-14T00:00:00Z
updated: 2026-03-14T00:00:00Z
---

{article['intro']}
"""
        (CORPUS_DIR / filename).write_text(note.strip())
        written += 1

    link_counts = [len(links.get(pid, [])) for pid in articles]
    linked_count = sum(1 for c in link_counts if c > 0)
    print(f"\nNotes written: {written} new, "
          f"{len(articles) - written} already existed")
    print(f"Notes with in-corpus links: {linked_count}/{len(articles)}")
    print(f"Avg links per note: {sum(link_counts) / len(link_counts):.1f}")

    title_map = {a["title"]: note_id(pid) for pid, a in articles.items()}
    (SPIKE_DIR / "title_map.json").write_text(json.dumps(title_map, indent=2))
    print(f"Title map: {SPIKE_DIR / 'title_map.json'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_corpus() -> None:
    articles = collect_articles()
    links = collect_links(articles)
    write_notes(articles, links)
    print("\nCorpus build complete.")


if __name__ == "__main__":
    build_corpus()
