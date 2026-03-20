"""Tests for ZettelNote embedding frontmatter field."""
from datetime import datetime, timezone

import numpy as np
import pytest

from zettelkasten.note import ZettelNote

CREATED = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)


def make_note(**overrides) -> ZettelNote:
    defaults = dict(
        id="z20260315-001",
        title="Testing Effect",
        body="Retrieving information strengthens retention.",
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
# Embedding round-trip
# ---------------------------------------------------------------------------


def test_note_without_embedding_round_trips():
    note = make_note()
    assert note.embedding is None
    restored = ZettelNote.from_markdown(note.to_markdown())
    assert restored.embedding is None


def test_embedding_round_trips_via_frontmatter():
    vec = np.array([0.1, -0.2, 0.3, 0.0], dtype=np.float32)
    note = make_note(embedding=vec)
    restored = ZettelNote.from_markdown(note.to_markdown())
    assert restored.embedding is not None
    assert np.allclose(restored.embedding, vec, atol=1e-6)


def test_embedding_stored_as_base64_string():
    """The raw markdown should contain a base64 string, not raw bytes."""
    vec = np.ones(8, dtype=np.float32)
    note = make_note(embedding=vec)
    md = note.to_markdown()
    import re
    match = re.search(r"embedding:\s*['\"]?([A-Za-z0-9+/=]+)['\"]?", md)
    assert match, "embedding should appear as a base64 string in frontmatter"


def test_full_size_embedding_round_trips():
    """Realistic 1024-dim embedding."""
    rng = np.random.default_rng(42)
    vec = rng.standard_normal(1024).astype(np.float32)
    note = make_note(embedding=vec)
    restored = ZettelNote.from_markdown(note.to_markdown())
    assert np.allclose(restored.embedding, vec, atol=1e-6)


def test_old_co_activations_frontmatter_silently_ignored():
    """Notes written before the activation redesign should load without error."""
    md = """\
---
id: z20260315-001
title: Testing Effect
type: permanent
confidence: 0.85
salience: 0.5
stable: false
created: 2026-03-15T10:00:00+00:00
updated: 2026-03-15T10:00:00+00:00
last_accessed: 2026-03-15T10:00:00+00:00
links: []
co_activations:
  - target: z20260315-002
    ts: 2026-03-15T10:00:00+00:00
---
# Testing Effect

Body text here.
"""
    note = ZettelNote.from_markdown(md)
    assert note.id == "z20260315-001"


# ---------------------------------------------------------------------------
# Combined: embedding + original fields all survive
# ---------------------------------------------------------------------------


def test_full_round_trip_with_embedding():
    from zettelkasten.note import ZettelLink

    vec = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    note = make_note(
        links=[ZettelLink(target="z20260315-002", rel="contradicts")],
        embedding=vec,
        stable=True,
        confidence=0.9,
    )
    restored = ZettelNote.from_markdown(note.to_markdown())
    assert restored.stable is True
    assert restored.confidence == pytest.approx(0.9)
    assert len(restored.links) == 1
    assert np.allclose(restored.embedding, vec, atol=1e-6)
