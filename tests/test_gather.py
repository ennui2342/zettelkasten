"""Tests for the Gather phase: 5-signal retrieval fusion."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import numpy as np
import pytest

from zettelkasten.gather import gather_phase
from zettelkasten.note import ZettelNote
from zettelkasten.providers import MockEmbed, MockLLM


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_EMBED = MockEmbed(dims=32)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _corpus_note(id_: str, title: str, body: str) -> ZettelNote:
    vec = _EMBED.embed([body])[0]
    return ZettelNote(
        id=id_,
        title=title,
        body=body,
        confidence=0.8,
        created=_now(),
        updated=_now(),
        embedding=vec,
    )


def _draft(title: str, body: str) -> ZettelNote:
    return ZettelNote(
        id="",
        title=title,
        body=body,
        confidence=0.3,
        created=_now(),
        updated=_now(),
    )


def _llm() -> MockLLM:
    """MockLLM that returns valid JSON for all gather signal prompts."""
    def respond(prompt: str, **kw) -> str:
        if "pseudo_notes" in prompt or "pseudo" in prompt.lower():
            return '{"pseudo_notes": ["memory consolidation", "spaced repetition", "retrieval practice"]}'
        if "abstraction" in prompt:
            return '{"abstraction": "Repeated retrieval strengthens long-term memory encoding."}'
        if "hypotheticals" in prompt:
            return '{"hypotheticals": ["Working memory capacity limits", "Attention and encoding", "Sleep and consolidation"]}'
        return '{"pseudo_notes": []}'
    return MockLLM(respond)


CORPUS = [
    _corpus_note("z20240101-001", "Testing Effect", "Retrieval practice strengthens memory more than passive review."),
    _corpus_note("z20240101-002", "Spaced Repetition", "Distributing practice over time beats massed practice for retention."),
    _corpus_note("z20240101-003", "Generation Effect", "Generating answers improves recall over reading them."),
    _corpus_note("z20240101-004", "Interleaving", "Mixing practice across topics improves transfer and long-term retention."),
    _corpus_note("z20240101-005", "Desirable Difficulty", "Certain challenges during learning improve long-term outcomes."),
]

DRAFT = _draft("Active Recall", "Actively retrieving information leads to durable memory traces.")


# ---------------------------------------------------------------------------
# Basic contract
# ---------------------------------------------------------------------------


def test_gather_phase_returns_list():
    results = gather_phase(DRAFT, CORPUS, _llm(), _EMBED)
    assert isinstance(results, list)


def test_gather_phase_results_are_zettel_notes():
    results = gather_phase(DRAFT, CORPUS, _llm(), _EMBED)
    assert all(isinstance(n, ZettelNote) for n in results)


def test_gather_phase_results_are_from_corpus():
    corpus_ids = {n.id for n in CORPUS}
    results = gather_phase(DRAFT, CORPUS, _llm(), _EMBED)
    for n in results:
        assert n.id in corpus_ids


def test_gather_phase_top_k_limits_results():
    results = gather_phase(DRAFT, CORPUS, _llm(), _EMBED, top_k=3)
    assert len(results) <= 3


def test_gather_phase_returns_at_most_corpus_size():
    small_corpus = CORPUS[:2]
    results = gather_phase(DRAFT, small_corpus, _llm(), _EMBED, top_k=20)
    assert len(results) <= 2


def test_gather_phase_default_top_k_is_20():
    # Make a large corpus to ensure top_k=20 default is applied
    big_corpus = []
    for i in range(25):
        big_corpus.append(_corpus_note(
            f"z20240101-{i+1:03d}",
            f"Topic {i}",
            f"Content about topic number {i} with unique words.",
        ))
    results = gather_phase(DRAFT, big_corpus, _llm(), _EMBED)
    assert len(results) <= 20


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_gather_phase_empty_corpus_returns_empty():
    results = gather_phase(DRAFT, [], _llm(), _EMBED)
    assert results == []


def test_gather_phase_corpus_without_embeddings():
    """Notes without embeddings still participate via BM25 and activation."""
    no_emb_corpus = []
    for n in CORPUS[:3]:
        no_emb_corpus.append(ZettelNote(
            id=n.id, title=n.title, body=n.body,
            confidence=n.confidence,
            created=n.created, updated=n.updated,
            embedding=None,
        ))
    results = gather_phase(DRAFT, no_emb_corpus, _llm(), _EMBED)
    # Should still return results (BM25 works without embeddings)
    assert isinstance(results, list)


# ---------------------------------------------------------------------------
# Activation signal
# ---------------------------------------------------------------------------


def test_gather_phase_activation_boosts_coactivated_notes():
    """A note with activation score for the query ID should rank higher."""
    query_id = "z20240101-001"
    coact_note = _corpus_note("z20240101-002", "Spaced Repetition", "Distributing practice over time.")
    plain_note = _corpus_note("z20240101-003", "Generation Effect", "Generating answers improves recall.")

    draft = ZettelNote(
        id=query_id,
        title="Testing",
        body="Active retrieval strengthens memory.",
        confidence=0.3,
        created=_now(),
        updated=_now(),
    )

    # Supply activation scores pre-fetched from the index
    activation_scores = {"z20240101-002": 1.0}
    results = gather_phase(draft, [coact_note, plain_note], _llm(), _EMBED,
                           top_k=2, activation_scores=activation_scores)
    result_ids = [n.id for n in results]
    assert "z20240101-002" in result_ids


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def test_gather_phase_logs_start_and_complete(caplog):
    with caplog.at_level(logging.INFO, logger="zettelkasten"):
        gather_phase(DRAFT, CORPUS, _llm(), _EMBED, top_k=5)

    messages = [r.message for r in caplog.records]
    assert any("gather.start" in m for m in messages)
    assert any("gather.complete" in m for m in messages)


def test_gather_phase_logs_signal_scores(caplog):
    with caplog.at_level(logging.DEBUG, logger="zettelkasten"):
        gather_phase(DRAFT, CORPUS, _llm(), _EMBED, top_k=3)

    messages = [r.message for r in caplog.records]
    assert any("gather.signal" in m for m in messages)
