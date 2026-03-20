#!/usr/bin/env python3
"""Spike 1: Episode Boundary Detection

Validates H2 from zettelkasten-memory.md:
  LLM-judged semantic boundaries produce well-scoped episodic units from
  real research sessions.

Tests three approaches:
  A. Nemori naïve     — one LLM call per turn; direct is_boundary judgment
  B. ES-Mem two-stage — word-overlap pre-filter, LLM confirmation on candidates
  C. Def-DTS intent   — classify each turn by type+domain; boundary = shift

Data sources:
  Primary:     pipelines/memory/research-findings.db  (real researcher pipeline)
  Supplementary: LoCoMo — see README in this directory for download instructions

Run:
  docker compose run --rm dev python spikes/spike1-boundary/spike.py

Writes:
  spikes/spike1-boundary/results.md
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import sqlite3
import sys
import textwrap
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Load .env so ANTHROPIC_API_KEY is available when run via docker compose
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# SSL_CERT_FILE from host .env may not exist inside the container; remove it
# to let httpx use its bundled CA bundle instead.
if "SSL_CERT_FILE" in os.environ and not os.path.exists(os.environ["SSL_CERT_FILE"]):
    del os.environ["SSL_CERT_FILE"]

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_PATH = Path("pipelines/memory/research-findings.db")
SESSION_KEY = "research"
RESULTS_PATH = Path("spikes/spike1-boundary/results.md")

# cheap+fast model for the spike; override with MODEL env var
MODEL = os.environ.get("MODEL", "anthropic:claude-haiku-4-5-20251001")

# Approach A: minimum confidence for LLM boundary confirmation
# Run 1 used 0.65 — over-triggered. Run 2 raises to 0.80.
CONFIDENCE_THRESHOLD = float(os.environ.get("CONF_THRESHOLD", "0.80"))

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Turn:
    content: str
    timestamp: str
    index: int
    # parsed fields (populated for structured JSON turns)
    source_type: str = ""
    area: str = ""
    title: str = ""
    summary: str = ""
    implication: str = ""

    @classmethod
    def from_row(cls, row: tuple, index: int) -> "Turn":
        content, timestamp = row
        t = cls(content=content, timestamp=timestamp, index=index)
        try:
            d = json.loads(content)
            t.source_type = d.get("source_type", "")
            t.area = d.get("area", "")
            t.title = d.get("title", "")
            t.summary = d.get("summary", "")
            t.implication = d.get("implication", "")
        except (json.JSONDecodeError, TypeError):
            # Compaction summary or plain text
            t.source_type = "text"
            t.title = content[:80]
            t.summary = content
        return t

    def as_text(self) -> str:
        """Human-readable single-line representation for LLM context."""
        if self.source_type == "text":
            return self.summary[:200]
        parts = [f"[{self.area or '?'}]", f"({self.source_type})"]
        if self.title:
            parts.append(self.title[:80])
        if self.summary:
            parts.append(f"— {self.summary[:120]}")
        return " ".join(parts)


@dataclass
class Episode:
    turns: list[Turn]
    title: str = ""

    def __len__(self) -> int:
        return len(self.turns)

    def area_summary(self) -> str:
        areas = [t.area for t in self.turns if t.area and t.area != "general"]
        source_types = [t.source_type for t in self.turns if t.source_type]
        area_str = ", ".join(sorted(set(areas))) or "general"
        type_str = ", ".join(sorted(set(source_types)))
        return f"areas={area_str} sources={type_str}"

    def render(self, width: int = 90) -> str:
        lines = [f"  Title: {self.title or '(untitled)'}",
                 f"  Turns: {len(self.turns)} | {self.area_summary()}"]
        for t in self.turns:
            lines.append(f"    [{t.index:02d}] {t.as_text()[:80]}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_turns(db_path: Path, session_key: str) -> list[Turn]:
    if not db_path.exists():
        print(f"  WARNING: {db_path} not found — using synthetic fallback data")
        return _synthetic_turns()
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT content, timestamp FROM turns WHERE session_key = ? ORDER BY timestamp ASC",
        (session_key,),
    ).fetchall()
    conn.close()
    turns = [Turn.from_row(row, i) for i, row in enumerate(rows)]
    print(f"  Loaded {len(turns)} turns from {db_path}")
    return turns


def _synthetic_turns() -> list[Turn]:
    """Minimal fallback for running without the real DB."""
    records = [
        {"source_type": "github", "area": "C5", "title": "langgraph 1.1.0", "summary": "streaming protocol update"},
        {"source_type": "github", "area": "C5", "title": "langgraph 1.1.1", "summary": "bugfix for subgraph replay"},
        {"source_type": "blog", "area": "general", "title": "Anatomy of an Agent Harness", "summary": "harness architecture overview"},
        {"source_type": "blog", "area": "general", "title": "Coding Agents Reshaping Engineering", "summary": "impact on engineering culture"},
        {"source_type": "blog", "area": "C2", "title": "Autonomous context compression", "summary": "compressing context windows"},
        {"source_type": "blog", "area": "C6", "title": "Designing agents to resist prompt injection", "summary": "security patterns"},
        {"source_type": "arxiv", "area": "C2", "title": "Missing Memory Hierarchy: Demand Paging for LLM", "summary": "paging analogy for LLM memory"},
        {"source_type": "github", "area": "C4", "title": "openai-agents-python v0.12.0", "summary": "durable execution features"},
        {"source_type": "github", "area": "C4", "title": "google/adk-python v1.27.0", "summary": "ADK update for durable tasks"},
    ]
    turns = []
    for i, r in enumerate(records):
        t = Turn(content=json.dumps(r), timestamp=f"2026-03-{11+(i//3):02d}T00:00:00",
                 index=i, **r, implication="")
        turns.append(t)
    return turns


# ---------------------------------------------------------------------------
# Utilities: word-overlap similarity (for Approach B pre-filter)
# ---------------------------------------------------------------------------

def _tokenise(text: str) -> Counter:
    """Simple word tokeniser; strips punctuation."""
    words = text.lower().split()
    words = [w.strip(".,!?;:\"'()[]{}") for w in words if len(w) > 2]
    return Counter(words)


def cosine_sim(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b[k] for k in a if k in b)
    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def window_text(turns: list[Turn], center: int, radius: int = 2) -> str:
    start = max(0, center - radius)
    end = min(len(turns), center + radius + 1)
    return " ".join(t.as_text() for t in turns[start:end])


# ---------------------------------------------------------------------------
# LLM helpers (pydantic_ai)
# ---------------------------------------------------------------------------

def _get_agent():
    try:
        from pydantic_ai import Agent
        from pydantic import BaseModel

        class BoundaryDecision(BaseModel):
            is_boundary: bool
            confidence: float
            reason: str

        agent = Agent(
            MODEL,
            output_type=BoundaryDecision,
            system_prompt=(
                "You analyse research session logs and detect topic shifts. "
                "A boundary marks the start of a meaningfully different research focus. "
                "Minor elaboration on the same topic is NOT a boundary. "
                "Return confidence 0.0–1.0 and a one-line reason."
            ),
        )
        return agent, BoundaryDecision
    except ImportError:
        raise ImportError("pydantic-ai required. Install: pip install 'aswarm[agent]'")


def _get_intent_agent():
    try:
        from pydantic_ai import Agent
        from pydantic import BaseModel

        INTENT_TAXONOMY = (
            "github_release_coordination (C3/C5/C8): multi-agent, concurrency, orchestration releases\n"
            "github_release_execution (C4): durable execution, workflow engine releases\n"
            "github_release_security (C6): tool approval, sandboxing, security releases\n"
            "blog_architecture: high-level harness/framework architectural discussion\n"
            "blog_memory_compaction (C1/C2): memory architecture, context compression\n"
            "blog_security_patterns (C6): agent security, prompt injection, sandboxing\n"
            "blog_subagent_patterns (C8): sub-agent spawning, delegation patterns\n"
            "blog_practical_case_study: concrete implementation case study\n"
            "arxiv_memory (C1/C2): academic memory or context management research\n"
            "arxiv_governance (C9/C10): pipeline governance, policy, schema evolution\n"
            "general_commentary: meta-commentary on AI/agents field"
        )

        class IntentClassification(BaseModel):
            intent: str
            domain: str
            confidence: float

        agent = Agent(
            MODEL,
            output_type=IntentClassification,
            system_prompt=(
                f"Classify each research finding into one of these intent categories:\n"
                f"{INTENT_TAXONOMY}\n\n"
                "Return the intent label exactly as listed, the primary domain area code "
                "(C1-C10 or 'general'), and confidence 0.0-1.0."
            ),
        )
        return agent, IntentClassification
    except ImportError:
        raise ImportError("pydantic-ai required.")


# ---------------------------------------------------------------------------
# Approach A: Nemori naïve boundary detector
# ---------------------------------------------------------------------------

async def approach_a_nemori(turns: list[Turn]) -> list[Episode]:
    """One LLM call per turn; direct is_boundary judgment against buffer."""
    print("\n  Running Approach A (Nemori naïve)...")
    agent, _ = _get_agent()

    episodes: list[Episode] = []
    buffer: list[Turn] = []

    for i, turn in enumerate(turns):
        if not buffer:
            buffer.append(turn)
            continue

        buffer_text = "\n".join(f"  [{t.index}] {t.as_text()}" for t in buffer[-6:])
        prompt = (
            f"Research session buffer (last {len(buffer[-6:])} entries):\n"
            f"{buffer_text}\n\n"
            f"New entry [{turn.index}]:\n  {turn.as_text()}\n\n"
            "Does this new entry start a meaningfully different research focus, "
            "or does it continue/elaborate the current one?"
        )
        result = await agent.run(prompt)
        decision = result.output
        is_boundary = decision.is_boundary and decision.confidence >= CONFIDENCE_THRESHOLD

        if is_boundary:
            episodes.append(Episode(turns=list(buffer)))
            buffer = [turn]
        else:
            buffer.append(turn)

        sys.stdout.write(
            f"    [{i+1:02d}/{len(turns)}] boundary={'YES' if is_boundary else 'no '} "
            f"conf={decision.confidence:.2f} — {decision.reason[:50]}\n"
        )
        sys.stdout.flush()

    if buffer:
        episodes.append(Episode(turns=list(buffer)))

    return episodes


# ---------------------------------------------------------------------------
# Approach B: ES-Mem two-stage
# ---------------------------------------------------------------------------

async def approach_b_esmem(turns: list[Turn]) -> list[Episode]:
    """Word-overlap MI pre-filter → LLM confirmation on candidates only."""
    print("\n  Running Approach B (ES-Mem two-stage)...")
    agent, _ = _get_agent()

    # Stage 1: compute similarity between adjacent windows; flag candidates
    candidate_boundaries: list[int] = []
    for i in range(1, len(turns)):
        before = _tokenise(window_text(turns, i - 1, radius=1))
        after = _tokenise(window_text(turns, i, radius=1))
        sim = cosine_sim(before, after)
        flag = sim < SIMILARITY_THRESHOLD
        print(f"    [{i:02d}] sim={sim:.2f} {'→ CANDIDATE' if flag else ''}")
        if flag:
            candidate_boundaries.append(i)

    print(f"  Stage 1: {len(candidate_boundaries)} candidate boundaries "
          f"(threshold={SIMILARITY_THRESHOLD})")

    # Stage 2: LLM verification for each candidate
    confirmed: list[int] = []
    for boundary_idx in candidate_boundaries:
        before_text = "\n".join(
            f"  [{t.index}] {t.as_text()}"
            for t in turns[max(0, boundary_idx - 3):boundary_idx]
        )
        after_text = "\n".join(
            f"  [{t.index}] {t.as_text()}"
            for t in turns[boundary_idx:boundary_idx + 3]
        )
        prompt = (
            f"Before potential boundary:\n{before_text}\n\n"
            f"After potential boundary:\n{after_text}\n\n"
            "Does the content AFTER represent a meaningfully different research focus "
            "from the content BEFORE? Small elaborations or same-day releases of the "
            "same tool are NOT meaningful shifts."
        )
        result = await agent.run(prompt)
        decision = result.output
        if decision.is_boundary and decision.confidence >= CONFIDENCE_THRESHOLD:
            confirmed.append(boundary_idx)
            print(f"    [CONFIRMED idx={boundary_idx}] conf={decision.confidence:.2f} "
                  f"— {decision.reason[:60]}")
        else:
            print(f"    [rejected  idx={boundary_idx}] conf={decision.confidence:.2f} "
                  f"— {decision.reason[:60]}")

    # Build episodes from confirmed boundaries
    split_points = [0] + confirmed + [len(turns)]
    episodes = []
    for i in range(len(split_points) - 1):
        segment = turns[split_points[i]:split_points[i + 1]]
        if segment:
            episodes.append(Episode(turns=segment))
    return episodes


# ---------------------------------------------------------------------------
# Approach C: Def-DTS intent taxonomy
# ---------------------------------------------------------------------------

async def approach_c_defdts(turns: list[Turn]) -> list[Episode]:
    """Classify each turn; boundary = intent category shift."""
    print("\n  Running Approach C (Def-DTS intent taxonomy)...")
    agent, _ = _get_intent_agent()

    intents: list[tuple[Turn, str, str]] = []
    for turn in turns:
        result = await agent.run(turn.as_text())
        clf = result.output
        intents.append((turn, clf.intent, clf.domain))
        print(f"    [{turn.index:02d}] {clf.intent[:45]:<45} dom={clf.domain}")

    # Detect boundaries: shift in intent (ignoring minor variations)
    def _normalise_intent(intent: str) -> str:
        """Collapse minor variants to a coarser category."""
        if intent.startswith("github_release"):
            # Group all github releases of the same tool type
            return intent
        return intent.split("_")[0] + "_" + intent.split("_")[1] if "_" in intent else intent

    episodes: list[Episode] = []
    buffer: list[Turn] = []
    prev_intent = None

    for turn, intent, domain in intents:
        coarse = _normalise_intent(intent)
        if prev_intent is not None and coarse != prev_intent and buffer:
            episodes.append(Episode(turns=list(buffer)))
            buffer = [turn]
        else:
            buffer.append(turn)
        prev_intent = coarse

    if buffer:
        episodes.append(Episode(turns=list(buffer)))

    return episodes


# ---------------------------------------------------------------------------
# Approach D: Hybrid — Def-DTS intent pre-label → Nemori boundary judgment
# ---------------------------------------------------------------------------

async def approach_d_hybrid(turns: list[Turn]) -> list[Episode]:
    """Pre-classify each turn with the intent taxonomy, then pass the label
    as structured context into the Nemori boundary judgment.

    The LLM gets a typed signal ('intent changed from X to Y') to reason with
    rather than relying solely on raw text comparison. This should reduce
    both over-triggering (Approach A's problem) and over-splitting
    (Approach C's problem).
    """
    print("\n  Running Approach D (Hybrid: intent-labelled Nemori)...")
    boundary_agent, _ = _get_agent()
    intent_agent, _ = _get_intent_agent()

    # Stage 1: classify all turns upfront
    print("  Stage 1: intent classification")
    labelled: list[tuple[Turn, str, str]] = []
    for turn in turns:
        result = await intent_agent.run(turn.as_text())
        clf = result.output
        labelled.append((turn, clf.intent, clf.domain))
        print(f"    [{turn.index:02d}] {clf.intent[:50]:<50} dom={clf.domain}")

    # Stage 2: Nemori boundary judgment with intent context
    print("  Stage 2: boundary judgment with intent context")
    episodes: list[Episode] = []
    buffer: list[tuple[Turn, str, str]] = []

    for i, (turn, intent, domain) in enumerate(labelled):
        if not buffer:
            buffer.append((turn, intent, domain))
            continue

        # Summarise the buffer's intent pattern
        buffer_intents = [f"[{t.index}] {lab} (dom={dom})" for t, lab, dom in buffer[-5:]]
        buffer_text = "\n".join(
            f"  [{t.index}] {t.as_text()[:80]}" for t, _, _ in buffer[-5:]
        )
        prev_intent = buffer[-1][1]
        intent_changed = intent != prev_intent

        prompt = (
            f"Research session buffer (last {min(len(buffer), 5)} entries):\n"
            f"{buffer_text}\n"
            f"Intent labels: {'; '.join(buffer_intents)}\n\n"
            f"New entry [{turn.index}]:\n"
            f"  Content: {turn.as_text()[:100]}\n"
            f"  Intent label: {intent} (domain={domain})\n"
            f"  Intent changed from previous: {'YES' if intent_changed else 'NO'}\n\n"
            "Given the intent label change information, does this entry start a "
            "meaningfully different research focus, or does it extend the current one?\n"
            "Note: a tool release in the same broad area as the buffer is usually a "
            "continuation, not a new episode. A genuine shift is a change in *what kind "
            "of question the research is answering*, not just a different tool or paper."
        )
        result = await boundary_agent.run(prompt)
        decision = result.output
        is_boundary = decision.is_boundary and decision.confidence >= CONFIDENCE_THRESHOLD

        if is_boundary:
            episodes.append(Episode(turns=[t for t, _, _ in buffer]))
            buffer = [(turn, intent, domain)]
        else:
            buffer.append((turn, intent, domain))

        sys.stdout.write(
            f"    [{i+1:02d}/{len(turns)}] boundary={'YES' if is_boundary else 'no '} "
            f"conf={decision.confidence:.2f} intent_changed={'Y' if intent_changed else 'n'} "
            f"— {decision.reason[:45]}\n"
        )
        sys.stdout.flush()

    if buffer:
        episodes.append(Episode(turns=[t for t, _, _ in buffer]))

    return episodes


# ---------------------------------------------------------------------------
# Title generation (shared, post-hoc)
# ---------------------------------------------------------------------------

async def generate_titles(episodes: list[Episode]) -> None:
    """Add a descriptive title to each episode via LLM."""
    from pydantic_ai import Agent

    agent = Agent(
        MODEL,
        system_prompt=(
            "Generate a concise (≤8 words) title for a cluster of research findings. "
            "Focus on the dominant topic or theme. Return only the title, no punctuation."
        ),
    )
    for ep in episodes:
        content = "\n".join(t.as_text() for t in ep.turns)
        result = await agent.run(f"Research cluster:\n{content}")
        ep.title = result.output.strip().strip('"')


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def _boundary_indices(episodes: list[Episode]) -> list[int]:
    """Return the turn indices where each episode STARTS (first = always 0)."""
    boundaries = []
    pos = 0
    for ep in episodes:
        boundaries.append(pos)
        pos += len(ep.turns)
    return boundaries


def _quality_stats(episodes: list[Episode]) -> dict:
    sizes = [len(ep) for ep in episodes]
    return {
        "n_episodes": len(episodes),
        "mean_size": sum(sizes) / max(len(sizes), 1),
        "min_size": min(sizes),
        "max_size": max(sizes),
        "singleton_count": sum(1 for s in sizes if s == 1),
    }


# ---------------------------------------------------------------------------
# Results renderer
# ---------------------------------------------------------------------------

def render_results(
    turns: list[Turn],
    results: dict[str, list[Episode]],
    llm_call_counts: dict[str, int],
) -> str:
    lines = [
        "# Spike 1 — Episode Boundary Detection: Results",
        "",
        f"*Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "---",
        "",
        f"## Input data",
        "",
        f"- Source: `{DB_PATH}` session_key=`{SESSION_KEY}`",
        f"- Total turns: {len(turns)}",
        f"- Date range: {turns[0].timestamp[:10]} → {turns[-1].timestamp[:10]}",
        "",
        "### Turn listing",
        "",
    ]
    for t in turns:
        lines.append(f"  `[{t.index:02d}]` {t.timestamp[:16]}  `{t.area or '?':>8}`  "
                     f"`{t.source_type:<10}`  {t.title[:65]}")

    lines += ["", "---", ""]

    for approach, episodes in results.items():
        stats = _quality_stats(episodes)
        lines += [
            f"## {approach}",
            "",
            f"- Episodes: **{stats['n_episodes']}**  "
            f"(mean {stats['mean_size']:.1f} turns, "
            f"min {stats['min_size']}, max {stats['max_size']}, "
            f"singletons {stats['singleton_count']})",
            f"- LLM calls: {llm_call_counts.get(approach, '?')}",
            "",
        ]
        for i, ep in enumerate(episodes, 1):
            lines.append(f"### Episode {i}: {ep.title or '(untitled)'}")
            lines.append("")
            lines.append(ep.render())
            lines.append("")

    lines += [
        "---",
        "",
        "## Qualitative scoring",
        "",
        "Score each approach 1–5 on each dimension. Fill this in manually after review.",
        "",
        "| Dimension | Approach A | Approach B | Approach C |",
        "|-----------|-----------|-----------|-----------|",
        "| Episode atomicity (one idea each?) | | | |",
        "| Boundary placement (at natural shifts?) | | | |",
        "| Granularity (not too fine, not too coarse?) | | | |",
        "| Signal quality (reasons make sense?) | | | |",
        "| **Overall** | | | |",
        "",
        "## Go / No-Go",
        "",
        "> **Go criteria:** at least 2 approaches score ≥ 3.5/5 overall.",
        "",
        "Decision: [ ] Go  [ ] No-go  [ ] Iterate",
        "",
        "Notes:",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    print("=" * 65)
    print("SPIKE 1: Episode Boundary Detection")
    print("=" * 65)

    # --- Data ---
    print("\n=== Loading data ===")
    turns = load_turns(DB_PATH, SESSION_KEY)
    if not turns:
        print("ERROR: no turns loaded")
        sys.exit(1)

    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    if not has_api_key:
        print("\nERROR: set ANTHROPIC_API_KEY (or OPENAI_API_KEY) to run LLM approaches")
        sys.exit(1)

    results: dict[str, list[Episode]] = {}
    llm_calls: dict[str, int] = {}

    # --- Approach A (tuned) ---
    print(f"\n=== Approach A: Nemori naïve (conf≥{CONFIDENCE_THRESHOLD}) ===")
    episodes_a = await approach_a_nemori(turns)
    llm_calls[f"Approach A (Nemori naïve, conf≥{CONFIDENCE_THRESHOLD})"] = max(0, len(turns) - 1)
    print(f"  → {len(episodes_a)} episodes")

    # Approach B eliminated after Run 1: word-overlap pre-filter blind to
    # domain-coherent data; would need semantic embeddings to be viable.

    # --- Approach C (baseline) ---
    print("\n=== Approach C: Def-DTS intent taxonomy ===")
    episodes_c = await approach_c_defdts(turns)
    llm_calls["Approach C (Def-DTS intent)"] = len(turns)
    print(f"  → {len(episodes_c)} episodes")

    # --- Approach D (hybrid) ---
    print("\n=== Approach D: Hybrid intent-labelled Nemori ===")
    episodes_d = await approach_d_hybrid(turns)
    llm_calls["Approach D (Hybrid)"] = len(turns) * 2  # classify + boundary per turn
    print(f"  → {len(episodes_d)} episodes")

    results[f"Approach A (Nemori naïve, conf≥{CONFIDENCE_THRESHOLD})"] = episodes_a
    results["Approach C (Def-DTS intent)"] = episodes_c
    results["Approach D (Hybrid intent-labelled Nemori)"] = episodes_d

    # --- Generate titles ---
    print("\n=== Generating episode titles ===")
    all_episodes = episodes_a + episodes_c + episodes_d
    await generate_titles(all_episodes)

    # --- Write results ---
    print("\n=== Writing results ===")
    md = render_results(turns, results, llm_calls)
    # Archive previous run before overwriting
    if RESULTS_PATH.exists():
        import shutil
        runs = sorted(RESULTS_PATH.parent.glob("results-run*.md"))
        next_run = len(runs) + 1
        shutil.copy(RESULTS_PATH, RESULTS_PATH.parent / f"results-run{next_run}.md")
        print(f"  Archived previous results as results-run{next_run}.md")
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(md)
    print(f"  Written to {RESULTS_PATH}")

    # --- Summary ---
    print("\n" + "=" * 65)
    print("RESULTS SUMMARY")
    print("=" * 65)
    for approach, episodes in results.items():
        stats = _quality_stats(episodes)
        print(f"  {approach[:40]:<40} {stats['n_episodes']:2d} episodes  "
              f"(mean {stats['mean_size']:.1f} turns/ep, "
              f"{stats['singleton_count']} singletons)")
    print(f"\nFull results: {RESULTS_PATH}")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
