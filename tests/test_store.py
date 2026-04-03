"""Tests for ZettelkastenStore — write, update, atomicity."""
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from zettelkasten.note import ZettelNote
from zettelkasten.store import ZettelkastenStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CREATED = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)


def make_note(id: str = "z20260315-001", **overrides) -> ZettelNote:
    defaults = dict(
        id=id,
        title="Testing Effect",
        body="Retrieving information strengthens retention.",
        type="permanent",
        confidence=0.85,
        salience=0.5,
        stable=False,
        created=CREATED,
        updated=CREATED,
        last_accessed=CREATED,
    )
    defaults.update(overrides)
    return ZettelNote(**defaults)


@pytest.fixture
def store(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    return ZettelkastenStore(
        notes_dir=notes_dir,
        index_path=tmp_path / "index.db",
    )


# ---------------------------------------------------------------------------
# write
# ---------------------------------------------------------------------------


def test_write_returns_note_id(store):
    note = make_note()
    result = store.write(note)
    assert result == note.id


def test_write_creates_markdown_file(store):
    note = make_note()
    store.write(note)
    md_file = store._notes_dir / f"{note.id}.md"
    assert md_file.exists()


def test_write_file_round_trips_note(store):
    note = make_note()
    store.write(note)
    md_file = store._notes_dir / f"{note.id}.md"
    restored = ZettelNote.from_markdown(md_file.read_text())
    assert restored == note


def test_write_indexes_note(store):
    note = make_note()
    store.write(note)
    row = store._index.get_note_row(note.id)
    assert row is not None
    assert row["type"] == "permanent"


def test_write_is_atomic_file_and_index_together(store):
    """If the index write were to fail, the file should not be left behind.
    We can't easily inject a DB failure in a unit test, but we verify that
    the file and index row are always both present after a successful write.
    """
    note = make_note()
    store.write(note)

    md_file = store._notes_dir / f"{note.id}.md"
    row = store._index.get_note_row(note.id)
    assert md_file.exists() and row is not None


def test_write_multiple_notes(store):
    n1 = make_note("z20260315-001", title="Note One")
    n2 = make_note("z20260315-002", title="Note Two")
    store.write(n1)
    store.write(n2)

    assert (store._notes_dir / "z20260315-001.md").exists()
    assert (store._notes_dir / "z20260315-002.md").exists()


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def test_update_changes_fields(store):
    note = make_note()
    store.write(note)

    store.update(note.id, confidence=0.95, stable=True)

    row = store._index.get_note_row(note.id)
    assert row["confidence"] == pytest.approx(0.95)
    assert row["stable"] == 1


def test_update_rewrites_markdown_file(store):
    note = make_note()
    store.write(note)

    store.update(note.id, body="New body content.")

    md_file = store._notes_dir / f"{note.id}.md"
    restored = ZettelNote.from_markdown(md_file.read_text())
    assert restored.body == "New body content."


def test_update_bumps_updated_timestamp(store):
    note = make_note()
    store.write(note)

    store.update(note.id, body="changed")

    md_file = store._notes_dir / f"{note.id}.md"
    restored = ZettelNote.from_markdown(md_file.read_text())
    assert restored.updated > CREATED


def test_update_preserves_unchanged_fields(store):
    note = make_note()
    store.write(note)

    store.update(note.id, body="New body.")

    md_file = store._notes_dir / f"{note.id}.md"
    restored = ZettelNote.from_markdown(md_file.read_text())
    assert restored.title == "Testing Effect"
    assert restored.confidence == pytest.approx(0.85)


def test_update_nonexistent_note_raises(store):
    with pytest.raises(KeyError):
        store.update("z20260315-999", body="x")


# ---------------------------------------------------------------------------
# _apply_result: EDIT operation
# ---------------------------------------------------------------------------


from zettelkasten.integrate import IntegrationResult
from zettelkasten.providers import MockEmbed

_EMBED = MockEmbed(dims=32)


def _edit_result(target_id: str, new_title: str, new_body: str) -> IntegrationResult:
    return IntegrationResult(
        operation="EDIT",
        reasoning="Note grew verbose.",
        confidence=0.9,
        target_ids=[target_id],
        note_title=new_title,
        note_body=new_body,
    )


def test_store_edit_rewrites_note_body(store):
    note = make_note("z20260315-001", body="Original long body content.")
    store.write(note)

    result = _edit_result("z20260315-001", "Testing Effect", "Compressed body.")
    store._apply_result(result, note, [note], _EMBED)

    reloaded = store._load_corpus()[0]
    assert reloaded.body == "Compressed body."


def test_store_edit_preserves_id(store):
    note = make_note("z20260315-001")
    store.write(note)

    result = _edit_result("z20260315-001", "Testing Effect", "Compressed body.")
    store._apply_result(result, note, [note], _EMBED)

    files = list(store._notes_dir.glob("*.md"))
    assert len(files) == 1
    assert files[0].stem == "z20260315-001"


def test_store_edit_no_activation_recorded(store):
    """EDIT is a compression pass — it must not record new activation edges."""
    note = make_note("z20260315-001")
    store.write(note)
    other = make_note("z20260315-003")
    store.write(other)

    result = _edit_result("z20260315-001", "Testing Effect", "Compressed body.")
    store._apply_result(result, note, [note, other], _EMBED)

    # No activation edges should exist for the edited note
    scores = store._index.get_activation_scores("z20260315-001")
    assert scores == {}
