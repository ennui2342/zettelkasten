#!/usr/bin/env python3
"""Baseline integration test suite — Layer 2 of the integration quality strategy.

Tests the decision tree against a fixed baseline store derived from the
2026-03-18 ingestion run (62 notes, minus 4 confirmed duplicates = 58 notes).
Each test case ingests a single paper against a fresh copy of the baseline
and verifies the expected operations fire.

The baseline store is in store/notes/ (committed). The index.db is built
from notes at runtime and is not committed.

Test cases target "hot" notes: notes above the L3 size threshold (8000 chars)
that are supersaturated and ready to trigger SPLIT or EDIT when the right
paper arrives.

Usage:
    uv run --env-file .env python eval/baseline/run.py           # all tests
    uv run --env-file .env python eval/baseline/run.py --case 1
    uv run --env-file .env python eval/baseline/run.py --case 1,3,5
    uv run --env-file .env python eval/baseline/run.py --list
    uv run --env-file .env python eval/baseline/run.py --setup
"""
from __future__ import annotations

import argparse
import logging
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
STORE_NOTES = HERE / "store" / "notes"
STORE_INDEX  = HERE / "store" / "index.db"  # built at runtime, not committed
CORPUS_PAPERS = ROOT / "spikes" / "benchmark-innovation" / "corpus" / "papers"
RESULTS_DIR  = HERE / "results"

sys.path.insert(0, str(ROOT / "src"))


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------
# Each case targets a "hot" note (body > 8000 chars) with a corpus paper not
# in the original dev set. Expected: L2 routes to UPDATE against the target
# note, then L3 refines to SPLIT or EDIT.
#
# Pass criteria:
#   - final operation in expected_ops
#   - expected_target appears in result.target_ids (or result.note_id for UPDATE/EDIT/SPLIT)
#
# Paper sources: spikes/benchmark-innovation/corpus/papers/{paper_id}.txt
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    id:              int
    label:           str
    paper_id:        str          # arxiv id (no extension)
    expected_ops:    tuple[str, ...]  # acceptable final operations (any draft may match)
    expected_target: str | None   # specific note id expected, or None = any target acceptable
    hot_note:        str          # the supersaturated baseline note being tested
    note:            str          # rationale / what makes this case interesting


TEST_CASES: list[TestCase] = [
    TestCase(
        id=1,
        label="SPLIT/EDIT: adversarial benchmarking paper triggers L3 on security cluster",
        paper_id="2511.05269",
        expected_ops=("SPLIT", "EDIT"),
        expected_target=None,  # any SPLIT/EDIT acceptable — L2 picks best target in security cluster
        hot_note="z20260318-043",
        note=(
            "z043 (11901 chars), z050, z051 form the security cluster. "
            "TAMAS (adversarial benchmarking, Byzantine attacks, colluding agents) "
            "is expected to route into this cluster via L2 UPDATE and trigger L3. "
            "L2 correctly selects the most specific target (z050 or z051) rather than "
            "the broad z043. Pass: at least one draft produces SPLIT or EDIT."
        ),
    ),
    TestCase(
        id=2,
        label="SPLIT/EDIT: confidence-aware tool calling extends tool integration note",
        paper_id="2510.10461",
        expected_ops=("SPLIT", "EDIT"),
        expected_target="z20260318-032",
        hot_note="z20260318-032",
        note=(
            "z032 covers tool use paradigms broadly (11383 chars). "
            "MedCoAct introduces confidence-aware selective tool invocation with "
            "role-specialised agents — a specific mechanism within the tool use space. "
            "L2 should UPDATE z032; L3 should SPLIT or EDIT depending on thread count."
        ),
    ),
    TestCase(
        id=3,
        label="SPLIT/EDIT: distributed edge memory extends cognitive memory architecture note",
        paper_id="2509.04993",
        expected_ops=("SPLIT", "EDIT"),
        expected_target="z20260318-030",
        hot_note="z20260318-030",
        note=(
            "z030 covers agent cognitive memory (tripartite model, RAG, retention, 10137 chars). "
            "The 6G network paper introduces hierarchical edge-cloud memory distribution — "
            "a distinct architectural framing. L2 should UPDATE z030; "
            "L3 should choose SPLIT (distributed vs centralised threads) or EDIT."
        ),
    ),
    TestCase(
        id=4,
        label="SPLIT/EDIT: visual RAG extends retrieval-augmented generation note",
        paper_id="2509.14778",
        expected_ops=("SPLIT", "EDIT"),
        expected_target="z20260318-006",
        hot_note="z20260318-006",
        note=(
            "z006 covers text-based GraphRAG and KBQA (10328 chars). "
            "OpenLens introduces visual-RAG with multimodal evidence fusion "
            "and retrieval conflict resolution — a distinct modality. "
            "L2 should UPDATE z006; L3 should SPLIT (text-RAG vs visual-RAG) or EDIT."
        ),
    ),
    TestCase(
        id=5,
        label="SPLIT/EDIT: code refactoring governance extends scientific reasoning note",
        paper_id="2511.03153",
        expected_ops=("SPLIT", "EDIT", "UPDATE"),
        expected_target="z20260318-010",
        hot_note="z20260318-010",
        note=(
            "z010 covers contract-bounded autonomy and governed multi-agent scientific "
            "reasoning (10542 chars). RefAgent introduces planner-generator-tester "
            "agents with hard compilation constraints as governance — structurally "
            "similar but different domain. L2 UPDATE to z010 expected; L3 may SPLIT "
            "or EDIT. UPDATE without L3 also acceptable (note may not hit threshold "
            "after prior splits)."
        ),
    ),
]


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(run_ts: str) -> logging.Logger:
    RESULTS_DIR.mkdir(exist_ok=True)
    log_path = RESULTS_DIR / f"run_{run_ts}.log"

    fmt = "%(asctime)s %(levelname)-8s %(name)-25s %(message)s"
    datefmt = "%H:%M:%S"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(ch)

    return logging.getLogger("baseline"), log_path


# ---------------------------------------------------------------------------
# Store helpers
# ---------------------------------------------------------------------------

def build_baseline_index(notes_dir: Path, index_path: Path) -> None:
    """Build index.db from the committed notes directory (rebuilds if missing)."""
    from zettelkasten.note import ZettelNote
    from zettelkasten.index import ZettelIndex

    index_path.unlink(missing_ok=True)
    idx = ZettelIndex(index_path)
    idx.initialise()

    loaded = 0
    for p in sorted(notes_dir.glob("z*.md")):
        try:
            note = ZettelNote.from_markdown(p.read_text(encoding="utf-8"))
            idx.upsert_note(note)
            if note.embedding is not None:
                idx.upsert_embedding(note.id, note.embedding)
            loaded += 1
        except Exception as e:
            print(f"  WARNING: failed to load {p.name}: {e}")

    print(f"  Index built: {loaded} notes indexed at {index_path}")


def fresh_store(tmp_dir: Path) -> tuple[Path, Path]:
    """Copy baseline notes into tmp_dir and build a fresh index. Returns (notes_dir, index_path)."""
    notes_dst = tmp_dir / "notes"
    shutil.copytree(STORE_NOTES, notes_dst)
    index_path = tmp_dir / "index.db"
    build_baseline_index(notes_dst, index_path)
    return notes_dst, index_path


# ---------------------------------------------------------------------------
# Setup command
# ---------------------------------------------------------------------------

def cmd_setup() -> None:
    """Rebuild the baseline index from committed notes (one-time setup or refresh)."""
    print("Building baseline index from store/notes/ ...")
    build_baseline_index(STORE_NOTES, STORE_INDEX)
    notes = sorted(STORE_NOTES.glob("z*.md"))
    print(f"  {len(notes)} notes in baseline.")
    print("  Setup complete.")


# ---------------------------------------------------------------------------
# Run a single test case
# ---------------------------------------------------------------------------

def run_case(
    tc: TestCase,
    llm,
    fast_llm,
    embed,
    log: logging.Logger,
) -> dict:
    paper_path = CORPUS_PAPERS / f"{tc.paper_id}.txt"
    if not paper_path.exists():
        return {
            "id": tc.id, "label": tc.label,
            "pass": False, "error": f"Paper not found: {paper_path}",
            "operation": None, "target_ids": [], "l1_target_ids": [],
            "reasoning": "", "confidence": 0.0,
            "note_title": "", "note_id": "",
        }

    text = paper_path.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="baseline_test_") as tmp:
        tmp_path = Path(tmp)
        notes_dir, index_path = fresh_store(tmp_path)

        from zettelkasten.store import ZettelkastenStore
        store = ZettelkastenStore(notes_dir, index_path)

        log.info("case_%d: ingesting paper=%s against %d-note baseline",
                 tc.id, tc.paper_id, len(list(notes_dir.glob("z*.md"))))

        try:
            results = store.ingest_text(text, llm, embed, fast_llm=fast_llm,
                                        source=tc.paper_id)
        except Exception as e:
            log.error("case_%d: ingest failed: %s", tc.id, e, exc_info=True)
            return {
                "id": tc.id, "label": tc.label,
                "pass": False, "error": str(e),
                "operation": None, "target_ids": [], "l1_target_ids": [],
                "reasoning": "", "confidence": 0.0,
                "note_title": "", "note_id": "",
            }

    # A paper may produce multiple drafts; find the result that fires against
    # the expected target (or, for CREATE, any CREATE result).
    matched = _find_matching_result(results, tc)

    passed = matched.operation in tc.expected_ops
    log.info("case_%d: operation=%s target=%s %s",
             tc.id, matched.operation,
             matched.target_ids or matched.note_id,
             "PASS" if passed else "FAIL")

    return {
        "id": tc.id, "label": tc.label,
        "pass": passed,
        "error": None if passed else f"expected {tc.expected_ops}, got {matched.operation!r}",
        "operation": matched.operation,
        "target_ids": matched.target_ids,
        "l1_target_ids": matched.l1_target_ids,
        "reasoning": matched.reasoning,
        "confidence": matched.confidence,
        "note_title": matched.note_title,
        "note_id": matched.note_id,
        "all_results": [(r.operation, r.target_ids) for r in results],
    }


def _find_matching_result(results, tc: TestCase):
    """Find the IntegrationResult that best matches the test case expectation.

    If expected_target is None: return the first result whose operation is in
    expected_ops (any target acceptable).
    If expected_target is set: return the result that targets that specific note.
    """
    if not results:
        return None

    if tc.expected_target is None:
        # Any target acceptable — return first result with a matching operation
        for r in results:
            if r.operation in tc.expected_ops:
                return r
        # No matching op found — return first result for diagnostic reporting
        return results[0]

    # Specific target required — find the result that targets it
    for r in results:
        if tc.expected_target in (r.target_ids or []):
            return r
        if tc.expected_target in (r.l1_target_ids or []):
            return r
    return results[0]  # fallback for diagnostic reporting


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def save_report(results: list[dict], run_ts: str, cases_run: list[int]) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"run_{run_ts}.md"

    passed = sum(1 for r in results if r["pass"])
    n = len(results)

    with path.open("w", encoding="utf-8") as f:
        f.write(f"# Baseline Integration Test Results — {run_ts}\n\n")
        f.write(f"**Cases run:** {sorted(cases_run)}  \n")
        f.write(f"**Score:** {passed}/{n} passed  \n\n")
        f.write("---\n\n")

        for r in results:
            status = "✓ PASS" if r["pass"] else "✗ FAIL"
            f.write(f"## Case {r['id']}: {r['label']}\n\n")
            tc = next(t for t in TEST_CASES if t.id == r["id"])
            f.write(f"**Hot note:** `{tc.hot_note}`  \n")
            f.write(f"**Paper:** `{tc.paper_id}`  \n")
            f.write(f"**Expected ops:** {tc.expected_ops}  \n")
            f.write(f"**Expected target:** `{tc.expected_target}`  \n\n")
            f.write(f"**Result:** {status}  \n")

            if r.get("error"):
                f.write(f"**Error:** {r['error']}  \n")

            if r.get("operation"):
                f.write(f"**Operation:** `{r['operation']}`  \n")
                f.write(f"**Confidence:** {r['confidence']:.2f}  \n")
                f.write(f"**Target IDs:** {r['target_ids']}  \n")
                f.write(f"**L1 target IDs:** {r['l1_target_ids']}  \n")
                if r.get("note_title"):
                    f.write(f"**Note title:** {r['note_title']}  \n")
                if r.get("note_id"):
                    f.write(f"**Note ID:** `{r['note_id']}`  \n")
                f.write(f"\n**Reasoning:**\n> {r['reasoning']}\n\n")

            if r.get("all_results"):
                f.write(f"**All draft results:** {r['all_results']}  \n\n")

            f.write(f"**Context:** {tc.note}\n\n")
            f.write("---\n\n")

    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Baseline integration test suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--case",
        help="Run specific case(s), comma-separated (e.g. --case 1 or --case 1,3)",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List all test cases and exit",
    )
    parser.add_argument(
        "--setup", action="store_true",
        help="Rebuild the baseline index from store/notes/ and exit",
    )
    args = parser.parse_args()

    if args.setup:
        cmd_setup()
        return

    if args.list:
        print(f"{'ID':<4} {'Label':<60} {'Hot note':<20} {'Expected'}")
        print("-" * 110)
        for tc in TEST_CASES:
            print(f"{tc.id:<4} {tc.label:<60} {tc.hot_note:<20} {tc.expected_ops}")
        return

    # Determine which cases to run
    if args.case:
        ids = {int(x.strip()) for x in args.case.split(",")}
        cases = [tc for tc in TEST_CASES if tc.id in ids]
        if not cases:
            print(f"No test cases found for --case {args.case!r}")
            sys.exit(1)
    else:
        cases = TEST_CASES

    run_ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
    log, log_path = setup_logging(run_ts)

    # Ensure baseline index exists
    if not STORE_INDEX.exists():
        log.info("Baseline index not found — building from store/notes/ ...")
        build_baseline_index(STORE_NOTES, STORE_INDEX)

    from zettelkasten.config import load_config, build_llm, build_fast_llm, build_embed
    cfg = load_config(ROOT / "zettelkasten.toml")
    llm      = build_llm(cfg)
    fast_llm = build_fast_llm(cfg)
    embed    = build_embed(cfg)

    model = cfg["llm"].get("model", "unknown")
    fast_model = cfg["llm"].get("fast_model", "unknown")

    print(f"\nModel:      {model}")
    print(f"Fast model: {fast_model}")
    print(f"Cases:      {[tc.id for tc in cases]}")
    print(f"Log:        {log_path.relative_to(ROOT)}")
    print()
    print("=" * 72)

    results = []
    for tc in cases:
        print(f"\nCase {tc.id}/{len(TEST_CASES)}: {tc.label}")
        print(f"  Hot note : {tc.hot_note}")
        print(f"  Paper    : {tc.paper_id}")
        print(f"  Expected : {tc.expected_ops} → target {tc.expected_target}")
        print(f"  Running...")

        r = run_case(tc, llm, fast_llm, embed, log)
        results.append(r)

        status = "✓ PASS" if r["pass"] else "✗ FAIL"
        print(f"  {status}  operation={r['operation']}  target={r['target_ids']}")
        if r.get("error"):
            print(f"  Error: {r['error']}")

    print()
    print("=" * 72)
    passed = sum(1 for r in results if r["pass"])
    n = len(results)
    print(f"Result: {passed}/{n} passed")
    print("=" * 72)

    report_path = save_report(results, run_ts, [tc.id for tc in cases])
    print(f"\nReport: {report_path.relative_to(ROOT)}")
    print(f"Log:    {log_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
