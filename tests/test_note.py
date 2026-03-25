"""Tests for ZettelNote — the core note dataclass and markdown round-trip."""
from datetime import datetime, timezone

import pytest

from zettelkasten.note import ZettelLink, ZettelNote

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CREATED = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)


def make_note(**overrides) -> ZettelNote:
    defaults = dict(
        id="z20260315-001",
        title="Testing Effect",
        body="Retrieving information from memory strengthens retention.",
        type="permanent",
        confidence=0.85,
        salience=0.5,
        stable=False,
        created=CREATED,
        updated=CREATED,
        last_accessed=CREATED,
        links=[],
    )
    defaults.update(overrides)
    return ZettelNote(**defaults)


# ---------------------------------------------------------------------------
# Round-trip: to_markdown / from_markdown
# ---------------------------------------------------------------------------


def test_round_trip_basic():
    note = make_note()
    restored = ZettelNote.from_markdown(note.to_markdown())
    assert restored == note


def test_round_trip_all_note_types():
    for t in ("permanent", "stub", "refuted", "synthesised"):
        note = make_note(type=t)
        assert ZettelNote.from_markdown(note.to_markdown()).type == t


def test_round_trip_stable_true():
    note = make_note(stable=True)
    restored = ZettelNote.from_markdown(note.to_markdown())
    assert restored.stable is True


def test_round_trip_with_links():
    links = [
        ZettelLink(target="z20260315-002", rel="contradicts", note="Earlier finding"),
        ZettelLink(target="z20260315-003", rel="supersedes"),
    ]
    note = make_note(links=links)
    restored = ZettelNote.from_markdown(note.to_markdown())
    assert restored.links == links


def test_round_trip_preserves_multiline_body():
    body = "First paragraph.\n\nSecond paragraph with **bold** and `code`."
    note = make_note(body=body)
    assert ZettelNote.from_markdown(note.to_markdown()).body == body


def test_round_trip_preserves_timestamps():
    note = make_note(
        created=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        updated=datetime(2026, 3, 10, 12, 30, 0, tzinfo=timezone.utc),
        last_accessed=datetime(2026, 3, 15, 9, 0, 0, tzinfo=timezone.utc),
    )
    restored = ZettelNote.from_markdown(note.to_markdown())
    assert restored.created == note.created
    assert restored.updated == note.updated
    assert restored.last_accessed == note.last_accessed


def test_from_markdown_handwritten():
    """Parse a note written by hand (not produced by to_markdown)."""
    md = """\
---
id: z20260315-042
type: stub
confidence: 0.40
salience: 0.3
stable: false
created: 2026-03-15T10:00:00+00:00
updated: 2026-03-15T10:00:00+00:00
last_accessed: 2026-03-15T10:00:00+00:00
links: []
---
# Spaced Repetition

Reviewing material at expanding intervals improves long-term retention.
"""
    note = ZettelNote.from_markdown(md)
    assert note.id == "z20260315-042"
    assert note.title == "Spaced Repetition"
    assert note.type == "stub"
    assert note.confidence == pytest.approx(0.40)
    assert "expanding intervals" in note.body


# ---------------------------------------------------------------------------
# ID format validation
# ---------------------------------------------------------------------------


def test_id_valid_format_accepted():
    make_note(id="z20260315-001")  # should not raise
    make_note(id="z20260315-999")


def test_id_invalid_format_rejected():
    with pytest.raises(ValueError, match="id"):
        make_note(id="invalid")

    with pytest.raises(ValueError, match="id"):
        make_note(id="20260315-001")  # missing leading 'z'

    with pytest.raises(ValueError, match="id"):
        make_note(id="z2026031-001")  # date too short

    with pytest.raises(ValueError, match="id"):
        make_note(id="z20260315-01")  # seq only 2 digits


# ---------------------------------------------------------------------------
# Note type vocabulary
# ---------------------------------------------------------------------------


def test_invalid_note_type_rejected():
    with pytest.raises(ValueError, match="type"):
        make_note(type="concept")

    with pytest.raises(ValueError, match="type"):
        make_note(type="")


# ---------------------------------------------------------------------------
# Link rel vocabulary
# ---------------------------------------------------------------------------


def test_valid_link_rels_accepted():
    for rel in ("contradicts", "supersedes", "splits-from", "merges-into"):
        ZettelLink(target="z20260315-002", rel=rel)  # should not raise


def test_invalid_link_rel_rejected():
    with pytest.raises(ValueError, match="rel"):
        ZettelLink(target="z20260315-002", rel="related-to")

    with pytest.raises(ValueError, match="rel"):
        ZettelLink(target="z20260315-002", rel="supports")


# ---------------------------------------------------------------------------
# ZettelLink defaults
# ---------------------------------------------------------------------------


def test_link_note_defaults_to_empty_string():
    link = ZettelLink(target="z20260315-002", rel="contradicts")
    assert link.note == ""


# ---------------------------------------------------------------------------
# sources field
# ---------------------------------------------------------------------------


def test_sources_defaults_to_empty_list():
    note = make_note()
    assert note.sources == []


def test_round_trip_sources_empty():
    note = make_note()
    restored = ZettelNote.from_markdown(note.to_markdown())
    assert restored.sources == []


def test_round_trip_sources_populated():
    note = make_note(sources=["https://arxiv.org/abs/2511.05269"])
    restored = ZettelNote.from_markdown(note.to_markdown())
    assert restored.sources == ["https://arxiv.org/abs/2511.05269"]


def test_round_trip_sources_multiple():
    urls = ["https://arxiv.org/abs/2511.05269", "https://arxiv.org/abs/2510.04851"]
    note = make_note(sources=urls)
    restored = ZettelNote.from_markdown(note.to_markdown())
    assert restored.sources == urls


def test_from_markdown_missing_sources_defaults_to_empty():
    """Old notes without a sources field load cleanly."""
    md = """\
---
id: z20260315-042
type: permanent
confidence: 0.8
salience: 0.5
stable: false
created: 2026-03-15T10:00:00+00:00
updated: 2026-03-15T10:00:00+00:00
last_accessed: 2026-03-15T10:00:00+00:00
links: []
---
# Old Note

Written before sources tracking was added.
"""
    note = ZettelNote.from_markdown(md)
    assert note.sources == []


def test_from_markdown_with_sources():
    md = """\
---
id: z20260315-042
type: permanent
confidence: 0.8
salience: 0.5
stable: false
created: 2026-03-15T10:00:00+00:00
updated: 2026-03-15T10:00:00+00:00
last_accessed: 2026-03-15T10:00:00+00:00
links: []
sources:
  - https://arxiv.org/abs/2511.05269
---
# Sourced Note

Body text.
"""
    note = ZettelNote.from_markdown(md)
    assert note.sources == ["https://arxiv.org/abs/2511.05269"]
