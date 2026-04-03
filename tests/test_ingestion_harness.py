"""Tests for eval/ingestion-harness/run.py helper functions."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

# Make the harness module importable from the tests/ directory
_HARNESS_DIR = Path(__file__).parent.parent / "eval" / "ingestion-harness"
if str(_HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(_HARNESS_DIR))

import run as harness


# ---------------------------------------------------------------------------
# _current_position
# ---------------------------------------------------------------------------


def test_current_position_empty():
    assert harness._current_position({"completed": []}) == 0


def test_current_position_some_done():
    assert harness._current_position({"completed": ["a", "b", "c"]}) == 3


# ---------------------------------------------------------------------------
# _snapshot_name
# ---------------------------------------------------------------------------


def test_snapshot_name_initial():
    assert harness._snapshot_name(0, "initial") == "00_initial"


def test_snapshot_name_first_paper():
    assert harness._snapshot_name(1, "2510.04851") == "01_2510.04851"


def test_snapshot_name_double_digit():
    assert harness._snapshot_name(12, "2512.06196") == "12_2512.06196"


# ---------------------------------------------------------------------------
# _detect_duplicate_titles
# ---------------------------------------------------------------------------


def test_detect_duplicate_titles_none():
    before = [("z001", "Memory Consolidation")]
    after = [
        ("z001", "Memory Consolidation"),
        ("z002", "Spaced Repetition"),
    ]
    assert harness._detect_duplicate_titles(before, after) == []


def test_detect_duplicate_titles_new_matches_existing():
    before = [("z001", "Memory Consolidation")]
    after = [
        ("z001", "Memory Consolidation"),
        ("z002", "Memory Consolidation"),  # duplicate
    ]
    dups = harness._detect_duplicate_titles(before, after)
    assert "Memory Consolidation" in dups


def test_detect_duplicate_titles_only_new_notes_checked():
    """A title that existed before (z001) being re-written is not a duplicate."""
    before = [("z001", "Memory Consolidation")]
    after = [("z001", "Memory Consolidation")]  # same note, rewritten — not a dup
    assert harness._detect_duplicate_titles(before, after) == []


def test_detect_duplicate_titles_two_new_dupes():
    before = [("z001", "Memory Consolidation")]
    after = [
        ("z001", "Memory Consolidation"),
        ("z002", "Working Memory"),
        ("z003", "Working Memory"),  # z002 and z003 share a title
    ]
    dups = harness._detect_duplicate_titles(before, after)
    assert "Working Memory" in dups


# ---------------------------------------------------------------------------
# _operation_summary
# ---------------------------------------------------------------------------


def _make_result(op: str, conf: float = 0.9):
    from zettelkasten.integrate import IntegrationResult
    return IntegrationResult(operation=op, reasoning="", confidence=conf)


def test_operation_summary_single():
    results = [_make_result("CREATE")]
    assert harness._operation_summary(results) == "CREATE×1"


def test_operation_summary_multiple_ops():
    results = [
        _make_result("CREATE"),
        _make_result("UPDATE"),
        _make_result("UPDATE"),
        _make_result("SPLIT"),
    ]
    summary = harness._operation_summary(results)
    assert "CREATE×1" in summary
    assert "UPDATE×2" in summary
    assert "SPLIT×1" in summary


def test_operation_summary_empty():
    assert harness._operation_summary([]) == "(none)"


# ---------------------------------------------------------------------------
# _low_confidence_ops
# ---------------------------------------------------------------------------


def test_low_confidence_ops_none_below_threshold():
    results = [_make_result("CREATE", 0.9), _make_result("UPDATE", 0.8)]
    assert harness._low_confidence_ops(results, threshold=0.7) == []


def test_low_confidence_ops_one_below():
    results = [_make_result("CREATE", 0.9), _make_result("UPDATE", 0.5)]
    low = harness._low_confidence_ops(results, threshold=0.7)
    assert len(low) == 1
    assert low[0].operation == "UPDATE"
    assert low[0].confidence == 0.5


# ---------------------------------------------------------------------------
# Snapshot: take and restore
# ---------------------------------------------------------------------------


def test_take_and_restore_snapshot(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "z001.md").write_text("original")
    index_path = tmp_path / "index.db"
    index_path.write_bytes(b"fake-db")
    snaps_dir = tmp_path / "snapshots"
    snaps_dir.mkdir()

    harness._take_snapshot(0, "initial", notes_dir, index_path, snaps_dir)

    # Mutate the store
    (notes_dir / "z001.md").write_text("modified")
    (notes_dir / "z002.md").write_text("new note")

    harness._restore_snapshot(0, "initial", notes_dir, index_path, snaps_dir)

    assert (notes_dir / "z001.md").read_text() == "original"
    assert not (notes_dir / "z002.md").exists()


def test_snapshot_dir_is_isolated(tmp_path):
    """Each snapshot goes to its own numbered directory."""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    index_path = tmp_path / "index.db"
    index_path.write_bytes(b"v0")
    snaps_dir = tmp_path / "snapshots"
    snaps_dir.mkdir()

    harness._take_snapshot(0, "initial", notes_dir, index_path, snaps_dir)
    index_path.write_bytes(b"v1")
    harness._take_snapshot(1, "2510.04851", notes_dir, index_path, snaps_dir)

    snap0 = snaps_dir / "00_initial" / "index.db"
    snap1 = snaps_dir / "01_2510.04851" / "index.db"
    assert snap0.read_bytes() == b"v0"
    assert snap1.read_bytes() == b"v1"
