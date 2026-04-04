"""Form phase: single-shot topic extraction from a document."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from .note import ZettelNote
from .prompts import _FORM_PROMPT
from .providers import LLMProvider

log = logging.getLogger("zettelkasten")


def form_phase(text: str, llm: LLMProvider) -> list[ZettelNote]:
    """Extract topic notes from *text* using a single LLM call.

    Returns a list of draft :class:`~zettelkasten.note.ZettelNote` objects
    with ``id=""`` and no embedding.
    """
    log.info("form.start doc_len=%d", len(text))

    prompt = _FORM_PROMPT.format(document=text)
    response = llm.complete(prompt, max_tokens=4096, temperature=0.0)

    drafts = _parse_response(response)

    log.info("form.complete drafts=%d", len(drafts))
    for d in drafts:
        log.debug("form.draft title=%r body_len=%d", d.title, len(d.body))

    return drafts


def _parse_response(response: str) -> list[ZettelNote]:
    """Split LLM response on ## headings and build draft ZettelNotes."""
    now = datetime.now(tz=timezone.utc)

    sections: list[tuple[str, str]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in response.splitlines():
        if line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line[3:].strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        sections.append((current_title, "\n".join(current_lines).strip()))

    drafts: list[ZettelNote] = []
    for title, body in sections:
        if not title:
            continue
        note = ZettelNote(
            id="",
            title=title,
            body=body,
            confidence=0.3,
            created=now,
            updated=now,
            embedding=None,
        )
        drafts.append(note)

    return drafts
