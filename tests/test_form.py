"""Tests for the Form phase: single-shot topic extraction from a document."""
import logging

import pytest

from zettelkasten.form import form_phase
from zettelkasten.note import ZettelNote
from zettelkasten.providers import MockLLM

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MULTI_TOPIC_RESPONSE = """\
## Testing Effect

Retrieving information from memory strengthens retention more than re-reading.
Practice tests outperform passive study across age groups and subject domains.

## Spaced Repetition

Reviewing material at expanding intervals reduces forgetting. The spacing effect
means distributed practice beats massed practice for long-term retention.

## Generation Effect

Generating an answer, even an incorrect one, leads to better recall than reading
the answer. The effort of retrieval is itself the mechanism of consolidation.
"""

SINGLE_TOPIC_RESPONSE = """\
## Testing Effect

Active retrieval is more effective than passive review for long-term retention.
"""


# ---------------------------------------------------------------------------
# Basic extraction
# ---------------------------------------------------------------------------


def test_form_phase_returns_list_of_zettel_notes():
    llm = MockLLM(MULTI_TOPIC_RESPONSE)
    drafts = form_phase("some document text", llm)
    assert isinstance(drafts, list)
    assert all(isinstance(n, ZettelNote) for n in drafts)


def test_form_phase_extracts_correct_number_of_topics():
    llm = MockLLM(MULTI_TOPIC_RESPONSE)
    drafts = form_phase("document", llm)
    assert len(drafts) == 3


def test_form_phase_extracts_titles():
    llm = MockLLM(MULTI_TOPIC_RESPONSE)
    titles = [n.title for n in form_phase("document", llm)]
    assert "Testing Effect" in titles
    assert "Spaced Repetition" in titles
    assert "Generation Effect" in titles


def test_form_phase_extracts_bodies():
    llm = MockLLM(SINGLE_TOPIC_RESPONSE)
    drafts = form_phase("document", llm)
    assert len(drafts) == 1
    assert "Active retrieval" in drafts[0].body


def test_form_phase_single_topic():
    llm = MockLLM(SINGLE_TOPIC_RESPONSE)
    drafts = form_phase("document", llm)
    assert len(drafts) == 1
    assert drafts[0].title == "Testing Effect"


# ---------------------------------------------------------------------------
# Draft note properties
# ---------------------------------------------------------------------------


def test_draft_notes_have_no_id():
    """Drafts are unstored — IDs assigned later by the store."""
    llm = MockLLM(SINGLE_TOPIC_RESPONSE)
    drafts = form_phase("document", llm)
    assert drafts[0].id == ""


def test_draft_notes_have_low_confidence():
    llm = MockLLM(MULTI_TOPIC_RESPONSE)
    for draft in form_phase("document", llm):
        assert draft.confidence < 0.5


def test_draft_notes_have_no_embedding():
    llm = MockLLM(MULTI_TOPIC_RESPONSE)
    for draft in form_phase("document", llm):
        assert draft.embedding is None


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------


def test_form_phase_ignores_content_before_first_heading():
    response = "Some preamble the LLM added.\n\n" + SINGLE_TOPIC_RESPONSE
    llm = MockLLM(response)
    drafts = form_phase("document", llm)
    assert len(drafts) == 1
    assert drafts[0].title == "Testing Effect"


def test_form_phase_empty_response_returns_empty_list():
    llm = MockLLM("No topics found.")
    drafts = form_phase("document", llm)
    assert drafts == []


def test_form_phase_strips_whitespace_from_bodies():
    llm = MockLLM(MULTI_TOPIC_RESPONSE)
    for draft in form_phase("document", llm):
        assert draft.body == draft.body.strip()


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def test_form_phase_logs_start_and_complete(caplog):
    llm = MockLLM(MULTI_TOPIC_RESPONSE)
    with caplog.at_level(logging.INFO, logger="zettelkasten"):
        form_phase("document text here", llm)

    messages = [r.message for r in caplog.records]
    assert any("form.start" in m for m in messages)
    assert any("form.complete" in m for m in messages)


def test_form_phase_logs_draft_details(caplog):
    llm = MockLLM(MULTI_TOPIC_RESPONSE)
    with caplog.at_level(logging.DEBUG, logger="zettelkasten"):
        form_phase("document text", llm)

    messages = [r.message for r in caplog.records]
    assert any("form.draft" in m for m in messages)
