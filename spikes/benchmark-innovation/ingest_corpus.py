#!/usr/bin/env python3
"""Ingest the benchmark corpus into a dedicated zettelkasten store.

Designed for overnight runs:
  - Idempotent: skips papers already ingested (tracked in state file)
  - Resilient: per-paper error handling — one failure doesn't stop the run
  - Dual logging: console + timestamped log file in logs/
  - Rate-limit aware: exponential backoff on Anthropic 429/overload errors
  - Clean reset: --reset wipes the store and state for a fresh run

All artifacts for a run share a timestamp (RUN_TS = YYYYMMDD_HHMMSS):
  - Store:      zettel_{RUN_TS}/
  - Index:      benchmark_{RUN_TS}.db
  - Log:        logs/ingest_{RUN_TS}.log
  - State:      corpus/ingested_{corpus}_{RUN_TS}.json

Usage:
  uv run python spikes/benchmark-innovation/ingest_corpus.py              # dev subset (~20 papers)
  uv run python spikes/benchmark-innovation/ingest_corpus.py --corpus full  # all 91 papers
  uv run python spikes/benchmark-innovation/ingest_corpus.py --reset      # wipe + reingest dev subset
  uv run python spikes/benchmark-innovation/ingest_corpus.py --dry-run    # show plan, no API calls
  uv run python spikes/benchmark-innovation/ingest_corpus.py --run-ts 20260317_022556  # resume a run
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import time
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = Path(__file__).parent
CORPUS_DIR = HERE / "corpus"
PAPERS_DIR = CORPUS_DIR / "papers"
LOGS_DIR = HERE / "logs"

CORPUS_FILES = {
    "dev":  CORPUS_DIR / "dev_subset.json",
    "full": CORPUS_DIR / "selected.json",
}


def run_paths(run_ts: str, corpus_name: str) -> tuple[Path, Path, Path]:
    """Return (store_dir, index_path, state_path) for a given run timestamp."""
    store_dir = HERE / f"zettel_{run_ts}"
    index_path = HERE / f"benchmark_{run_ts}.db"
    state_path = CORPUS_DIR / f"ingested_{corpus_name}_{run_ts}.json"
    return store_dir, index_path, state_path

# ---------------------------------------------------------------------------
# Logging: dual output (console + file)
# ---------------------------------------------------------------------------

def setup_logging(run_ts: str, dry_run: bool) -> logging.Logger:
    LOGS_DIR.mkdir(exist_ok=True)
    suffix = "_dryrun" if dry_run else ""
    log_path = LOGS_DIR / f"ingest_{run_ts}{suffix}.log"

    fmt = "%(asctime)s %(levelname)-8s %(name)-20s %(message)s"
    datefmt = "%H:%M:%S"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # File handler — everything including DEBUG from the library
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(fh)

    # Console handler — INFO and above only (less noisy for watching overnight)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(ch)

    log = logging.getLogger("ingest")
    log.info("Log file: %s", log_path)
    return log


# ---------------------------------------------------------------------------
# State tracking (which papers have been ingested)
# ---------------------------------------------------------------------------

def load_state(state_path: Path) -> dict:
    if state_path.exists():
        return json.loads(state_path.read_text())
    return {"ingested": [], "failed": [], "skipped_no_text": []}


def save_state(state: dict, state_path: Path) -> None:
    state_path.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Rate-limit aware wrapper
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Store snapshot / rollback (atomicity for per-paper writes)
# ---------------------------------------------------------------------------


def snapshot_paths(store_dir: Path, index_path: Path) -> tuple[Path, Path]:
    return store_dir.parent / f"{store_dir.name}_snap", index_path.with_suffix(".snap.db")


def take_snapshot(store_dir: Path, index_path: Path, log: logging.Logger) -> None:
    snap_dir, snap_db = snapshot_paths(store_dir, index_path)
    if snap_dir.exists():
        shutil.rmtree(snap_dir)
    shutil.copytree(store_dir, snap_dir)
    if index_path.exists():
        shutil.copy2(index_path, snap_db)
    log.debug("  Snapshot taken (%d notes)", len(list(snap_dir.glob("*.md"))))


def restore_snapshot(store_dir: Path, index_path: Path, log: logging.Logger) -> None:
    snap_dir, snap_db = snapshot_paths(store_dir, index_path)
    if not snap_dir.exists():
        log.warning("  No snapshot to restore — store may be inconsistent")
        return
    shutil.rmtree(store_dir)
    shutil.copytree(snap_dir, store_dir)
    if snap_db.exists():
        shutil.copy2(snap_db, index_path)
    log.info("  Store rolled back to pre-paper snapshot")
    discard_snapshot(store_dir, index_path)


def discard_snapshot(store_dir: Path, index_path: Path) -> None:
    snap_dir, snap_db = snapshot_paths(store_dir, index_path)
    if snap_dir.exists():
        shutil.rmtree(snap_dir)
    if snap_db.exists():
        snap_db.unlink()


# ---------------------------------------------------------------------------
# Rate-limit aware wrapper
# ---------------------------------------------------------------------------


def ingest_with_retry(store, text: str, llm, embed, fast_llm, source: str,
                      log: logging.Logger, max_retries: int = 5):
    """Call store.ingest_text with exponential backoff on rate-limit errors."""
    delay = 10.0
    for attempt in range(1, max_retries + 1):
        try:
            return store.ingest_text(text, llm, embed, source=source, fast_llm=fast_llm)
        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = any(x in err_str for x in [
                "rate_limit", "rate limit", "429", "overloaded",
                "too many requests", "capacity",
            ])
            if is_rate_limit and attempt < max_retries:
                log.warning(
                    "Rate limit on attempt %d/%d — sleeping %.0fs before retry",
                    attempt, max_retries, delay,
                )
                time.sleep(delay)
                delay = min(delay * 2, 120.0)  # cap at 2 minutes
            else:
                raise


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest benchmark corpus")
    parser.add_argument(
        "--corpus", choices=["dev", "full"], default="dev",
        help="Which corpus to ingest: dev (~20 papers) or full (~91 papers). Default: dev",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Wipe the store and state file, then reingest from scratch",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be ingested without making any API calls",
    )
    parser.add_argument(
        "--delay", type=float, default=2.0,
        help="Seconds to pause between papers (default: 2.0)",
    )
    parser.add_argument(
        "--run-ts", type=str, default=None,
        help="Resume an existing run by its timestamp (YYYYMMDD_HHMMSS). "
             "Omit to start a new run.",
    )
    args = parser.parse_args()

    run_ts = args.run_ts or datetime.now().strftime("%Y%m%d_%H%M%S")
    store_dir, index_path, state_path = run_paths(run_ts, args.corpus)

    log = setup_logging(run_ts, args.dry_run)
    log.info("=" * 60)
    log.info("Benchmark corpus ingestion")
    log.info("Run TS: %s  |  Corpus: %s  |  Reset: %s  |  Dry-run: %s",
             run_ts, args.corpus, args.reset, args.dry_run)

    # ---- Reset ----
    if args.reset and not args.dry_run:
        log.info("RESET: wiping store and state")
        if store_dir.exists():
            shutil.rmtree(store_dir)
            log.info("Deleted %s", store_dir)
        if index_path.exists():
            index_path.unlink()
            log.info("Deleted %s", index_path)
        if state_path.exists():
            state_path.unlink()
            log.info("Deleted %s", state_path)
        discard_snapshot(store_dir, index_path)

    # ---- Load corpus ----
    corpus_file = CORPUS_FILES[args.corpus]
    if not corpus_file.exists():
        log.error("Corpus file not found: %s", corpus_file)
        sys.exit(1)

    papers = json.loads(corpus_file.read_text())
    log.info("Loaded %d papers from %s", len(papers), corpus_file.name)

    # ---- Load state ----
    state = load_state(state_path)
    already_done = set(state["ingested"])
    already_failed = set(state["failed"])
    log.info("State: %d ingested, %d failed, %d no-text",
             len(state["ingested"]), len(state["failed"]),
             len(state["skipped_no_text"]))

    # ---- Filter to pending ----
    pending = [
        p for p in papers
        if p["arxiv_id"] not in already_done
    ]
    log.info("Pending: %d papers to ingest", len(pending))

    if args.dry_run:
        log.info("DRY RUN — would ingest:")
        for p in pending:
            txt = PAPERS_DIR / f"{p['arxiv_id'].replace('/', '_')}.txt"
            has_txt = "OK " if txt.exists() else "NO "
            log.info("  %s [%s] %s  %s", has_txt, p["benchmark_bucket"],
                     p["arxiv_id"], p["title"][:55])
        log.info("Dry run complete. No API calls made.")
        return

    if not pending:
        log.info("Nothing to do — all papers already ingested.")
        return

    # ---- Set up providers ----
    log.info("Initialising providers...")
    try:
        from zettelkasten.config import load_config, build_llm, build_fast_llm, build_embed
        from zettelkasten.store import ZettelkastenStore
    except ImportError as e:
        log.error("Could not import zettelkasten library: %s", e)
        sys.exit(1)

    # Load config for API keys, but override store paths to use benchmark store
    cfg = load_config()
    llm = build_llm(cfg)
    fast_llm = build_fast_llm(cfg)
    embed = build_embed(cfg)

    store_dir.mkdir(exist_ok=True)
    store = ZettelkastenStore(notes_dir=store_dir, index_path=index_path)
    log.info("Store: %s  |  Index: %s", store_dir, index_path)
    log.info("LLM: %s  |  Fast LLM: %s  |  Embed: %s",
             cfg["llm"]["model"], cfg["llm"]["fast_model"], cfg["embed"]["model"])
    log.info("=" * 60)

    # ---- Ingest loop ----
    total = len(pending)
    op_counts: Counter = Counter()
    t_run_start = time.monotonic()

    for i, paper in enumerate(pending, 1):
        arxiv_id = paper["arxiv_id"]
        safe_id = arxiv_id.replace("/", "_")
        txt_path = PAPERS_DIR / f"{safe_id}.txt"

        log.info("[%d/%d] %s  %s", i, total, arxiv_id, paper["title"][:55])

        if not txt_path.exists():
            log.warning("  No text file — skipping")
            if arxiv_id not in state["skipped_no_text"]:
                state["skipped_no_text"].append(arxiv_id)
            save_state(state, state_path)
            continue

        text = txt_path.read_text(encoding="utf-8")
        log.info("  Text: %d chars  |  Bucket: %s  |  Score: %d",
                 len(text), paper["benchmark_bucket"], paper["benchmark_score"])

        take_snapshot(store_dir, index_path, log)
        t_paper_start = time.monotonic()
        try:
            results = ingest_with_retry(
                store, text, llm, embed, fast_llm,
                source=arxiv_id, log=log,
            )

            # Log each integration result
            paper_ops: Counter = Counter()
            for r in results:
                paper_ops[r.operation] += 1
                op_counts[r.operation] += 1
                note_id = getattr(r, "note_id", "") or ""
                log.info(
                    "  %-10s  conf=%.2f  id=%-14s  %s",
                    r.operation, r.confidence, note_id,
                    r.note_title[:45] if r.note_title else r.reasoning[:45],
                )

            elapsed = time.monotonic() - t_paper_start
            log.info("  Done in %.1fs — ops: %s", elapsed,
                     " ".join(f"{op}×{n}" for op, n in sorted(paper_ops.items())))

            state["ingested"].append(arxiv_id)
            # Remove from failed if it was there before
            if arxiv_id in already_failed:
                state["failed"] = [x for x in state["failed"] if x != arxiv_id]
            discard_snapshot(store_dir, index_path)

        except KeyboardInterrupt:
            restore_snapshot(store_dir, index_path, log)
            log.warning("  Interrupted mid-paper — store rolled back, state saved up to previous paper.")
            save_state(state, state_path)
            raise

        except Exception:
            elapsed = time.monotonic() - t_paper_start
            restore_snapshot(store_dir, index_path, log)
            log.error("  FAILED after %.1fs:", elapsed)
            log.error("  %s", traceback.format_exc().strip().split("\n")[-1])
            log.debug("  Full traceback:\n%s", traceback.format_exc())
            if arxiv_id not in state["failed"]:
                state["failed"].append(arxiv_id)

        save_state(state, state_path)

        # Brief pause between papers
        if i < total:
            time.sleep(args.delay)

    # ---- Summary ----
    elapsed_total = time.monotonic() - t_run_start
    log.info("=" * 60)
    log.info("Run complete in %.0fs (%.1f min)", elapsed_total, elapsed_total / 60)
    log.info("Papers ingested this run: %d", len(state["ingested"]) - len(already_done))
    log.info("Total ingested to date:  %d / %d", len(state["ingested"]), len(papers))
    if state["failed"]:
        log.warning("Papers failed: %d — rerun with same --run-ts to retry:", len(state["failed"]))
        paper_titles = {p["arxiv_id"]: p["title"] for p in papers}
        for fid in state["failed"]:
            log.warning("  FAILED  %s  %s", fid, paper_titles.get(fid, "")[:55])
    else:
        log.info("Papers failed:           0")
    log.info("Operations this run:     %s",
             " ".join(f"{op}×{n}" for op, n in sorted(op_counts.items())))

    notes = list(store_dir.glob("*.md"))
    log.info("Notes in store:          %d", len(notes))
    log.info("=" * 60)


if __name__ == "__main__":
    main()
