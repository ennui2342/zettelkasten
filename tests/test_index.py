"""Tests for the SQLite index — schema, rebuild_from_directory, touch_accessed."""
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from zettelkasten.index import ZettelIndex
from zettelkasten.note import ZettelNote

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CREATED = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)


def make_note(id: str = "z20260315-001", **overrides) -> ZettelNote:
    defaults = dict(
        id=id,
        title="Testing Effect",
        body="Retrieving information strengthens retention.",
        confidence=0.85,
        created=CREATED,
        updated=CREATED,
    )
    defaults.update(overrides)
    return ZettelNote(**defaults)


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def index(tmp_dir):
    idx = ZettelIndex(tmp_dir / "index.db")
    idx.initialise()
    return idx


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def test_initialise_creates_tables(tmp_dir):
    db_path = tmp_dir / "index.db"
    idx = ZettelIndex(db_path)
    idx.initialise()

    con = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    con.close()

    assert "notes" in tables
    assert "activation" in tables


def test_initialise_is_idempotent(tmp_dir):
    db_path = tmp_dir / "index.db"
    idx = ZettelIndex(db_path)
    idx.initialise()
    idx.initialise()  # second call must not raise or corrupt


# ---------------------------------------------------------------------------
# upsert / read
# ---------------------------------------------------------------------------


def test_upsert_and_read_note(index):
    note = make_note()
    index.upsert_note(note)

    row = index.get_note_row(note.id)
    assert row is not None
    assert row["id"] == note.id
    assert row["confidence"] == pytest.approx(0.85)


def test_upsert_overwrites_existing(index):
    note = make_note()
    index.upsert_note(note)
    updated = make_note(confidence=0.95)
    index.upsert_note(updated)

    row = index.get_note_row(note.id)
    assert row["confidence"] == pytest.approx(0.95)


# ---------------------------------------------------------------------------
# rebuild_from_directory
# ---------------------------------------------------------------------------


def test_rebuild_from_directory_loads_all_notes(tmp_dir):
    notes_dir = tmp_dir / "notes"
    notes_dir.mkdir()

    n1 = make_note("z20260315-001", title="Note One")
    n2 = make_note("z20260315-002", title="Note Two")
    (notes_dir / "z20260315-001.md").write_text(n1.to_markdown())
    (notes_dir / "z20260315-002.md").write_text(n2.to_markdown())

    db_path = tmp_dir / "index.db"
    idx = ZettelIndex(db_path)
    idx.rebuild_from_directory(notes_dir)

    assert idx.get_note_row("z20260315-001") is not None
    assert idx.get_note_row("z20260315-002") is not None


def test_rebuild_from_directory_clears_stale_entries(tmp_dir):
    notes_dir = tmp_dir / "notes"
    notes_dir.mkdir()

    n1 = make_note("z20260315-001")
    (notes_dir / "z20260315-001.md").write_text(n1.to_markdown())

    db_path = tmp_dir / "index.db"
    idx = ZettelIndex(db_path)
    idx.rebuild_from_directory(notes_dir)

    # Remove the file and rebuild
    (notes_dir / "z20260315-001.md").unlink()
    idx.rebuild_from_directory(notes_dir)

    assert idx.get_note_row("z20260315-001") is None


def test_rebuild_from_directory_ignores_non_md_files(tmp_dir):
    notes_dir = tmp_dir / "notes"
    notes_dir.mkdir()
    (notes_dir / "README.txt").write_text("not a note")

    db_path = tmp_dir / "index.db"
    idx = ZettelIndex(db_path)
    idx.rebuild_from_directory(notes_dir)  # should not raise


# ---------------------------------------------------------------------------
# activation table
# ---------------------------------------------------------------------------


def test_record_activation_event_basic(index):
    index.record_activation_event("z20260315-001", ["z20260315-002", "z20260315-003"])

    scores = index.get_activation_scores("z20260315-001")
    assert "z20260315-002" in scores
    assert "z20260315-003" in scores
    assert scores["z20260315-002"] > 0


def test_record_activation_event_transitive(index):
    # Transitive expansion: 002 and 003 should gain a mutual edge
    index.record_activation_event("z20260315-001", ["z20260315-002", "z20260315-003"])

    scores_002 = index.get_activation_scores("z20260315-002")
    assert "z20260315-003" in scores_002


def test_record_activation_event_no_self_edge(index):
    # qid should never appear as its own partner
    index.record_activation_event("z20260315-001", ["z20260315-001", "z20260315-002"])
    scores = index.get_activation_scores("z20260315-001")
    assert "z20260315-001" not in scores


def test_activation_accumulates(index):
    index.record_activation_event("z20260315-001", ["z20260315-002"])
    index.record_activation_event("z20260315-001", ["z20260315-002"])
    scores = index.get_activation_scores("z20260315-001")
    assert scores["z20260315-002"] > 1.5  # two events, weight > 1


def test_activation_delete_note_clears_edges(index):
    n1 = make_note("z20260315-001")
    index.upsert_note(n1)
    index.record_activation_event("z20260315-001", ["z20260315-002"])
    index.delete_note("z20260315-001")
    scores = index.get_activation_scores("z20260315-002")
    assert "z20260315-001" not in scores
