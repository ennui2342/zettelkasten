#!/usr/bin/env python3
"""Spike 2: Fuzzy Document Form Phase

Validates H10 from zettelkasten-memory.md:
  A fuzzy document (no section headings, topics interwoven) can be decomposed
  into well-scoped topic-scoped draft notes.

Tests two approaches:
  A. Stepped  — count topics, name them, extract per topic (CARPAS-inspired)
  B. Single-shot — one prompt: document in, topic notes out

Evaluates against ground-truth.md:
  - Topics identified (expected: 4)
  - Content coverage per topic
  - Scattered content collection
  - Ambiguous sentence handling
  - Padding suppression

Run:
  docker compose run --rm dev python spikes/spike2-fuzzy-form/spike.py
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
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
ARTICLE_PATH = SPIKE_DIR / "article.md"
RESULTS_PATH = SPIKE_DIR / "results.md"

MODEL = "claude-opus-4-6"

client = anthropic.Anthropic()


def read_article() -> str:
    text = ARTICLE_PATH.read_text()
    # Strip the markdown heading line
    lines = text.strip().splitlines()
    if lines[0].startswith("#"):
        lines = lines[1:]
    return "\n".join(lines).strip()


def call(prompt: str) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


# ---------------------------------------------------------------------------
# Approach A — Stepped (CARPAS-inspired)
# ---------------------------------------------------------------------------

def approach_a_count(article: str) -> int:
    prompt = f"""The following essay covers several distinct topic areas.
How many broad topic areas does it address?

Count guidelines:
- A topic area is broad enough to have its own Wikipedia article covering many aspects and sub-concepts.
- Named techniques, specific phenomena, or mechanisms within a broader area are NOT separate topics — they belong inside one topic.
- Err on the side of fewer, broader topics rather than more, narrower ones.

Predict the count as a single integer. Output only the integer, nothing else.

Essay:
{article}"""
    result = call(prompt).strip()
    match = re.search(r"\d+", result)
    return int(match.group()) if match else 0


def approach_a_name(article: str, count: int) -> list[str]:
    prompt = f"""The following essay covers exactly {count} broad topic areas.
Name them. Each name should describe a broad subject area, not a specific technique or named phenomenon.
Group related techniques and concepts under one topic rather than listing each separately.
Output one topic name per line, nothing else.

Essay:
{article}"""
    result = call(prompt)
    return [line.strip().lstrip("-•*0123456789. ") for line in result.splitlines() if line.strip()]


def approach_a_extract(article: str, topic: str) -> str:
    prompt = f"""Topic: {topic}

Extract everything the following essay says about this topic, including all named techniques,
mechanisms, and phenomena that fall within this subject area.
Draw from anywhere in the essay — relevant content may appear in any paragraph.
Write in your own words. Do not copy sentences verbatim.
If a piece of content is relevant to this topic and also to another topic, include it here anyway.

Essay:
{article}"""
    return call(prompt)


def run_approach_a(article: str) -> dict:
    print("  Approach A: counting topics...")
    count = approach_a_count(article)
    print(f"  → model says {count} topics")

    print("  Approach A: naming topics...")
    topics = approach_a_name(article, count)
    print(f"  → topics: {topics}")

    extractions = {}
    for topic in topics:
        print(f"  Approach A: extracting '{topic}'...")
        extractions[topic] = approach_a_extract(article, topic)

    return {"count": count, "topics": topics, "extractions": extractions}


# ---------------------------------------------------------------------------
# Approach B — Single-shot
# ---------------------------------------------------------------------------

def run_approach_b(article: str) -> str:
    print("  Approach B: single-shot...")
    prompt = f"""The following essay covers several distinct topic areas.
For each broad topic area, produce a topic note.

Guidelines:
- A topic area is broad enough to warrant its own Wikipedia article covering many aspects.
- Named techniques, mechanisms, or specific phenomena within a broader area belong inside one note — do not create a separate note for each named concept.
- Draw relevant content from anywhere in the essay — relevant material may be scattered across paragraphs, not just adjacent.
- If content sits at the boundary between two topics, include it in both relevant notes.
- Write in your own words.

Format each topic note as:

## [Topic name]

[Content]

Essay:
{article}"""
    return call(prompt)


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

def write_results(a: dict, b: str) -> None:
    # Archive previous results
    if RESULTS_PATH.exists():
        runs = sorted(SPIKE_DIR.glob("results-run*.md"))
        next_run = len(runs) + 1
        shutil.copy(RESULTS_PATH, SPIKE_DIR / f"results-run{next_run}.md")
        print(f"  Archived previous results as results-run{next_run}.md")

    lines = [
        "# Spike 2 Results — Fuzzy Document Form Phase",
        "",
        f"*Run: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        f"*Model: {MODEL}*",
        "",
        "---",
        "",
        "## Approach A — Stepped (CARPAS-inspired)",
        "",
        f"**Topics identified:** {a['count']} (model count) → {len(a['topics'])} named",
        "",
        "**Topic names:**",
    ]
    for t in a["topics"]:
        lines.append(f"- {t}")

    lines += ["", "---", ""]

    for topic, extraction in a["extractions"].items():
        lines += [
            f"### A: {topic}",
            "",
            extraction,
            "",
            "---",
            "",
        ]

    lines += [
        "## Approach B — Single-shot",
        "",
        b,
        "",
        "---",
        "",
        "## Evaluation notes",
        "",
        "*(Fill in after reviewing output against ground-truth.md)*",
        "",
        "### Topic identification",
        "- Expected 4 topics: (A) testing effect, (B) spaced repetition, (C) generation effect, (D) external tools",
        "- Approach A found: [fill in]",
        "- Approach B found: [fill in]",
        "",
        "### Content coverage",
        "- A: testing effect — paragraphs 2, 3 expected; para 5 partial; para 9 bridge sentence",
        "- B: spaced repetition — paragraphs 4, 5 expected; para 6 partial",
        "- C: generation effect — paragraphs 6 partial, 7, 8 expected; para 9 bridge",
        "- D: external tools — paragraphs 8 partial, 11, 12 expected",
        "",
        "### Ambiguous sentences (should appear in two extractions each)",
        '- "That reconstruction is itself encoding." → expected in A and B',
        '- "This is where spaced repetition systems hit a ceiling..." → expected in B and C',
        '- "The explanatory effort triggers the same consolidation pathways as retrieval practice." → expected in C and A',
        "",
        "### Padding handling",
        "- Para 1 (intro) and para 10 (synthesis) should not dominate any extraction",
        "",
        "### Approach comparison",
        "- [fill in]",
        "",
        "## Go / No-go",
        "",
        "[ ] Go — proceed to Spike 3",
        "[ ] No-go — iterate prompts",
        "",
        "**Recommendation:** [fill in]",
    ]

    RESULTS_PATH.write_text("\n".join(lines))
    print(f"  Results written to {RESULTS_PATH}")


async def main() -> None:
    article = read_article()
    print(f"Article loaded: {len(article.split())} words\n")

    print("Running Approach A (stepped)...")
    a = run_approach_a(article)

    print("\nRunning Approach B (single-shot)...")
    b = run_approach_b(article)

    print("\nWriting results...")
    write_results(a, b)
    print("\nDone. Review results.md and fill in evaluation notes.")


if __name__ == "__main__":
    asyncio.run(main())
