#!/usr/bin/env python3
"""Gather probe — diagnose duplicate note creation.

Seeds a fresh store with the *first* note from each duplicate pair, then
ingests the *second* note's body through the full pipeline.  If the pipeline
finds the seeded note and returns UPDATE (or MERGE), the duplicate would have
been caught.  If it returns CREATE, we have a confirmed miss — and the step1
reasoning line tells us why.

This runs the real Form → Gather → Integrate pipeline, so results reflect
actual behaviour rather than an offline approximation.

The `--cluster` flag adds a second mode: for each duplicate pair it prints the
raw k20 cluster returned by gather (using the stored embeddings + offline
signals) so you can see whether the sibling even ranked in the top 20 before
step1 ever saw it.  This mode requires no LLM calls.

Usage:
  uv run --env-file .env python spikes/benchmark-innovation/gather_probe.py
  uv run --env-file .env python spikes/benchmark-innovation/gather_probe.py --cluster
"""
from __future__ import annotations

import argparse
import logging
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "src"))

STORE_DIR  = HERE / "zettel_20260318_142629"
INDEX_PATH = HERE / "benchmark_20260318_142629.db"

# ---------------------------------------------------------------------------
# Duplicate pairs to probe.
# (canonical_id, duplicate_id) — canonical is the earlier note, duplicate is
# the one that should have been an UPDATE but was created fresh.
# ---------------------------------------------------------------------------

@dataclass
class Pair:
    label: str
    canonical_id: str   # the note that existed first
    duplicate_id: str   # the note that was incorrectly CREATEd


PAIRS: list[Pair] = [
    Pair(
        label="Multi-Agent Architectures for Workflow Automation",
        canonical_id="z20260318-001",
        duplicate_id="z20260318-029",
    ),
    Pair(
        label="Memory and Context Management in LLM-Based Agents (020→022)",
        canonical_id="z20260318-020",
        duplicate_id="z20260318-022",
    ),
    Pair(
        label="Memory and Context Management in LLM-Based Agents (020→024)",
        canonical_id="z20260318-020",
        duplicate_id="z20260318-024",
    ),
    Pair(
        label="Evaluation Frameworks for Real-World Agent Deployment",
        canonical_id="z20260318-027",
        duplicate_id="z20260318-042",
    ),
]


# ---------------------------------------------------------------------------
# Offline cluster inspection (--cluster mode, no LLM calls)
# ---------------------------------------------------------------------------

def _unit(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    return v / norm if norm > 1e-9 else v


def _normalise(v: np.ndarray) -> np.ndarray:
    m = v.max()
    return v / m if m > 0 else v


def _stem(word: str) -> str:
    if word.endswith("sses"):   word = word[:-2]
    elif word.endswith("ies"):  word = word[:-2]
    elif word.endswith("ss"):   pass
    elif word.endswith("s"):    word = word[:-1]
    if word.endswith("eed"):
        if len(word) > 4:       word = word[:-1]
    elif word.endswith("ed") and any(c in word[:-2] for c in "aeiou"):
        word = word[:-2]
        if word.endswith("at") or word.endswith("bl") or word.endswith("iz"):
            word += "e"
    elif word.endswith("ing") and any(c in word[:-3] for c in "aeiou"):
        word = word[:-3]
        if word.endswith("at") or word.endswith("bl") or word.endswith("iz"):
            word += "e"
    if word.endswith("y") and any(c in word[:-1] for c in "aeiou"):
        word = word[:-1] + "i"
    for suffix, replacement in [
        ("ational", "ate"), ("tional", "tion"), ("enci", "ence"),
        ("anci", "ance"), ("izer", "ize"), ("ising", "ise"),
        ("izing", "ize"), ("alism", "al"), ("ation", "ate"),
        ("ator", "ate"), ("ness", ""), ("fulness", "ful"), ("ousness", "ous"),
    ]:
        if word.endswith(suffix) and len(word) - len(suffix) > 2:
            word = word[:-len(suffix)] + replacement
            break
    return word


def _tokenize(text: str) -> list[str]:
    return [_stem(w) for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 3]


def show_offline_cluster(pair: Pair, notes: dict) -> None:
    """Print the ranked k20 for duplicate_id querying against the full store."""
    from rank_bm25 import BM25Okapi
    import sqlite3, math

    draft = notes.get(pair.duplicate_id)
    canonical = notes.get(pair.canonical_id)
    if draft is None or canonical is None:
        print(f"  ERROR: notes not found")
        return
    if draft.embedding is None:
        print(f"  ERROR: {pair.duplicate_id} has no embedding")
        return

    corpus = [n for n in notes.values() if n.id != draft.id]
    ids = [n.id for n in corpus]
    id_to_pos = {nid: i for i, nid in enumerate(ids)}

    # body signal (document embedding as query proxy)
    s_body = np.zeros(len(corpus), dtype=np.float32)
    q = _unit(draft.embedding)
    for i, n in enumerate(corpus):
        if n.embedding is not None:
            s_body[i] = float(_unit(n.embedding) @ q)

    # BM25 (offline, no MuGI)
    corpus_tokens = [_tokenize(n.body) for n in corpus]
    bm25 = BM25Okapi(corpus_tokens) if any(corpus_tokens) else None
    s_bm25 = np.array(bm25.get_scores(_tokenize(draft.body)), dtype=np.float32) if bm25 else np.zeros(len(corpus))

    # activation from SQLite
    s_act = np.zeros(len(corpus), dtype=np.float32)
    if INDEX_PATH.exists():
        now = datetime.now(tz=timezone.utc)
        con = sqlite3.connect(str(INDEX_PATH))
        rows = con.execute(
            "SELECT note_a, note_b, weight, updated FROM activation WHERE note_a=? OR note_b=?",
            (draft.id, draft.id),
        ).fetchall()
        con.close()
        for note_a, note_b, weight, upd in rows:
            peer = note_b if note_a == draft.id else note_a
            if peer in id_to_pos:
                try:
                    upd_dt = datetime.fromisoformat(upd)
                    if upd_dt.tzinfo is None:
                        upd_dt = upd_dt.replace(tzinfo=timezone.utc)
                    days = (now - upd_dt).total_seconds() / 86400
                    s_act[id_to_pos[peer]] = weight * math.exp(-0.05 * days)
                except Exception:
                    s_act[id_to_pos[peer]] = weight

    # blend (renormalised weights: body=0.500, bm25=0.300, act=0.200)
    blended = (
        0.500 * _normalise(s_body)
        + 0.300 * _normalise(s_bm25)
        + 0.200 * _normalise(s_act)
    )

    top20 = list(np.argsort(-blended)[:20])
    print(f"  Query: {pair.duplicate_id}  \"{draft.title[:55]}\"")
    print(f"  Looking for canonical: {pair.canonical_id}")
    canonical_rank = None
    for rank, idx in enumerate(top20, 1):
        nid = ids[idx]
        marker = " <-- CANONICAL" if nid == pair.canonical_id else ""
        print(f"    {rank:2d}. {nid}  {blended[idx]:.4f}  {corpus[idx].title[:50]}{marker}")
        if nid == pair.canonical_id:
            canonical_rank = rank

    if canonical_rank is None:
        can_score = blended[id_to_pos[pair.canonical_id]] if pair.canonical_id in id_to_pos else 0.0
        print(f"  *** CANONICAL NOT IN TOP-20  (score={can_score:.4f}) — Mode 1: search miss")
    else:
        print(f"  *** CANONICAL at rank {canonical_rank} — in k20, check step1 output with full pipeline")


# ---------------------------------------------------------------------------
# Full-pipeline probe
# ---------------------------------------------------------------------------

def run_pipeline_probe(pair: Pair, notes: dict, llm, fast_llm, embed, work_dir: Path, log) -> dict:
    """
    Seed a fresh store with ALL notes except the duplicate, then ingest the
    duplicate's body through the full pipeline.

    Seeding the full corpus (minus the duplicate) gives Gather a realistic k20
    to work with — the same conditions step1 would have seen during the real run.
    Seeding only the canonical note would return a cluster of 1, changing how
    step1 reasons about the decision.
    """
    from zettelkasten.store import ZettelkastenStore

    store_dir  = work_dir / f"zettel_{pair.duplicate_id}"
    index_path = work_dir / f"index_{pair.duplicate_id}.db"

    if store_dir.exists():
        shutil.rmtree(store_dir)
    if index_path.exists():
        index_path.unlink()

    duplicate = notes[pair.duplicate_id]
    seed_notes = [n for n in notes.values() if n.id != pair.duplicate_id]

    store = ZettelkastenStore(notes_dir=store_dir, index_path=index_path)

    # Seed all notes except the duplicate, preserving real embeddings
    for n in seed_notes:
        store.write(n)
        if n.embedding is not None:
            store._index.upsert_embedding(n.id, n.embedding)

    log.info("Seeded %d notes (all except %s)", len(seed_notes), pair.duplicate_id)
    log.info("Ingesting duplicate body: %s  \"%s\"", duplicate.id, duplicate.title[:55])

    # Ingest the duplicate's body as the source text.
    # The Form phase will extract drafts from it; those drafts go through
    # the real Gather → Integrate flow against the seeded corpus.
    results = store.ingest_text(
        duplicate.body,
        llm=llm,
        embed=embed,
        fast_llm=fast_llm,
        source=f"gather-probe/{pair.duplicate_id}",
    )

    return {
        "pair": pair,
        "operations": [(r.operation, r.confidence, r.note_id, r.note_title, r.reasoning) for r in results],
    }


# ---------------------------------------------------------------------------
# Setup / reporting
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    fmt = "%(asctime)s %(levelname)-8s %(name)-20s %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt, datefmt="%H:%M:%S")
    logging.getLogger("zettelkasten").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return logging.getLogger("gather-probe")


def print_pipeline_result(result: dict) -> None:
    pair = result["pair"]
    ops  = result["operations"]
    print(f"\n  Canonical: {pair.canonical_id}")
    print(f"  Duplicate body ingested as text")
    for op, conf, note_id, title, reasoning in ops:
        target_is_canonical = note_id == pair.canonical_id
        marker = "  <-- UPDATE on canonical" if (op == "UPDATE" and target_is_canonical) else ""
        print(f"    {op:<12} conf={conf:.2f}  id={note_id or '—':<16}  {(title or reasoning or '')[:50]}{marker}")

    # Diagnosis
    any_update_on_canonical = any(
        op == "UPDATE" and nid == pair.canonical_id
        for op, _, nid, _, _ in ops
    )
    any_create = any(op == "CREATE" for op, _, _, _, _ in ops)

    if any_update_on_canonical:
        print(f"\n  RESULT: UPDATE on canonical — pipeline WOULD have caught this duplicate")
    elif any_create:
        print(f"\n  RESULT: CREATE fired — Mode 3 confirmed (integration miss)")
        for op, conf, nid, title, reasoning in ops:
            if op == "CREATE":
                print(f"    CREATE reasoning: {reasoning[:200]}")
    else:
        print(f"\n  RESULT: no CREATE or UPDATE on canonical — unexpected ops: {[o for o,*_ in ops]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Probe gather for duplicate note diagnosis")
    parser.add_argument(
        "--cluster", action="store_true",
        help="Show offline k20 cluster for each pair (no LLM calls). "
             "Diagnoses Mode 1 (search miss) before running the full pipeline.",
    )
    args = parser.parse_args()

    log = setup_logging()

    # Load all notes from the real store
    try:
        from zettelkasten.note import ZettelNote
    except ImportError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    notes: dict[str, ZettelNote] = {}
    for f in sorted(STORE_DIR.glob("*.md")):
        try:
            n = ZettelNote.from_markdown(f.read_text(encoding="utf-8"))
            notes[n.id] = n
        except Exception as e:
            log.warning("Could not load %s: %s", f.name, e)

    log.info("Loaded %d notes from %s", len(notes), STORE_DIR.name)

    # --cluster mode: offline only, no API calls
    if args.cluster:
        print()
        print("=" * 70)
        print("OFFLINE CLUSTER INSPECTION  (document embedding as query proxy)")
        print("Weights: body=0.500  bm25=0.300 (no MuGI)  activation=0.200")
        print("=" * 70)
        for pair in PAIRS:
            print(f"\n{pair.label}")
            show_offline_cluster(pair, notes)
        print()
        print("Mode 1 = canonical NOT in top-20 → search/ranking problem")
        print("Other  = canonical IS in top-20  → run without --cluster to test step1")
        return

    # Full pipeline mode
    from zettelkasten.config import load_config, build_llm, build_fast_llm, build_embed
    cfg = load_config(ROOT / "zettelkasten.toml")
    llm      = build_llm(cfg)
    fast_llm = build_fast_llm(cfg)
    embed    = build_embed(cfg)
    log.info("LLM: %s", cfg["llm"]["model"])

    work_dir = HERE / "work_probe"
    work_dir.mkdir(exist_ok=True)

    print()
    print("=" * 70)
    print("FULL PIPELINE PROBE")
    print("Seeding with canonical, ingesting duplicate body, watching step1")
    print("=" * 70)

    all_results = []
    for pair in PAIRS:
        if pair.canonical_id not in notes or pair.duplicate_id not in notes:
            log.warning("Skipping %s — notes not found", pair.label)
            continue
        log.info("--- %s ---", pair.label)
        try:
            result = run_pipeline_probe(pair, notes, llm, fast_llm, embed, work_dir, log)
            all_results.append(result)
            print(f"\n{pair.label}")
            print_pipeline_result(result)
        except Exception as e:
            log.error("FAILED: %s", e, exc_info=True)

    print()
    print("=" * 70)
    print("SUMMARY")
    caught    = sum(1 for r in all_results if any(op == "UPDATE" and nid == r["pair"].canonical_id for op, _, nid, _, _ in r["operations"]))
    missed    = len(all_results) - caught
    print(f"  Pairs tested: {len(all_results)}")
    print(f"  Would have caught: {caught}")
    print(f"  Would have missed: {missed}")
    print()
    if missed == len(all_results):
        print("  All missed → Mode 1 (search) most likely. Run with --cluster to confirm.")
    elif caught == len(all_results):
        print("  All caught → the pipeline CAN find duplicates; the real-run failure was")
        print("  likely Mode 2 (activation miss during the actual ingestion context).")
    else:
        print("  Mixed results — check per-pair reasoning above.")
    print("=" * 70)


if __name__ == "__main__":
    main()
