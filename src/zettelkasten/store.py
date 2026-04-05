"""ZettelkastenStore — top-level store: file + index writes, with atomic operations."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .index import ZettelIndex
from .integrate import IntegrationResult, integrate_phase
from .note import ZettelNote
from .providers import EmbedProvider, LLMProvider

log = logging.getLogger("zettelkasten")


class ZettelkastenStore:
    """Manages a directory of markdown notes and a SQLite index in sync."""

    def __init__(
        self,
        notes_dir: Path | str,
        index_path: Path | str,
    ) -> None:
        self._notes_dir = Path(notes_dir)
        self._index = ZettelIndex(index_path)
        self._notes_dir.mkdir(parents=True, exist_ok=True)
        self._index.initialise()

    # ------------------------------------------------------------------
    # write
    # ------------------------------------------------------------------

    def write(self, note: ZettelNote) -> str:
        """Write a note to disk and index it. Returns the note ID."""
        md_path = self._notes_dir / f"{note.id}.md"
        md_path.write_text(note.to_markdown(), encoding="utf-8")
        self._index.upsert_note(note)
        return note.id

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------

    def update(self, note_id: str, **changes: Any) -> ZettelNote:
        """Update fields on an existing note. Raises KeyError if not found."""
        md_path = self._notes_dir / f"{note_id}.md"
        if not md_path.exists():
            raise KeyError(f"Note {note_id!r} not found")

        note = ZettelNote.from_markdown(md_path.read_text(encoding="utf-8"))

        for field, value in changes.items():
            if not hasattr(note, field):
                raise AttributeError(f"ZettelNote has no field {field!r}")
            object.__setattr__(note, field, value)

        # Always bump updated timestamp
        object.__setattr__(note, "updated", datetime.now(tz=timezone.utc))

        self.write(note)
        return note

    # ------------------------------------------------------------------
    # ID generation
    # ------------------------------------------------------------------

    def _next_id(self) -> str:
        """Return the next available z{YYYYMMDD}-NNN ID for today."""
        today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
        existing_seqs: list[int] = []
        for p in self._notes_dir.glob(f"z{today}-???.md"):
            m = re.match(r"z\d{8}-(\d{3})$", p.stem)
            if m:
                existing_seqs.append(int(m.group(1)))
        seq = max(existing_seqs) + 1 if existing_seqs else 1
        return f"z{today}-{seq:03d}"

    # ------------------------------------------------------------------
    # Corpus helpers
    # ------------------------------------------------------------------

    def _load_corpus(self) -> list[ZettelNote]:
        """Load all notes from the notes directory."""
        notes: list[ZettelNote] = []
        for p in self._notes_dir.glob("*.md"):
            try:
                note = ZettelNote.from_markdown(p.read_text(encoding="utf-8"))
                notes.append(note)
            except Exception:
                pass
        return notes

    # ------------------------------------------------------------------
    # ingest_text
    # ------------------------------------------------------------------

    def ingest_text(
        self,
        text: str,
        llm: LLMProvider,
        embed: EmbedProvider,
        source: str | None = None,
        fast_llm: LLMProvider | None = None,
        integrate_fn=None,
    ) -> list[IntegrationResult]:
        """Run the full Form → Gather → Integrate pipeline on *text*.

        Returns one :class:`~zettelkasten.integrate.IntegrationResult` per
        draft note produced by the Form phase.  *integrate_fn* overrides the
        default :func:`integrate_phase` — used by spikes and experiments.

        *fast_llm* is forwarded to gather and integrate for cheap LLM tasks.
        Falls back to *llm* if not provided.
        """
        from .form import form_phase
        from .gather import gather_phase

        _fast = fast_llm or llm

        log.info("store.ingest source=%r text_len=%d", source, len(text))

        drafts = form_phase(text, llm)
        results: list[IntegrationResult] = []

        for draft in drafts:
            corpus = self._load_corpus()
            activation_scores = self._index.get_activation_scores(draft.id)
            cluster = gather_phase(draft, corpus, _fast, embed, activation_scores=activation_scores)
            if integrate_fn is not None:
                result = integrate_fn(draft, cluster, llm, fast_llm=_fast)
            else:
                result = integrate_phase(draft, cluster, llm, fast_llm=_fast, embed=embed)

            self._apply_result(result, draft, cluster, embed, source=source)
            results.append(result)

        self._index.increment_ingestion_count()
        log.info("store.ingest_complete results=%d", len(results))
        return results

    def _apply_result(
        self,
        result: IntegrationResult,
        draft: ZettelNote,
        cluster: list[ZettelNote],
        embed: EmbedProvider,
        source: str | None = None,
    ) -> None:
        """Write/update notes on disk and index according to *result*."""
        op = result.operation

        if op == "NOTHING":
            return

        now = datetime.now(tz=timezone.utc)

        if op in ("CREATE", "SYNTHESISE"):
            note_id = self._next_id()
            note = ZettelNote(
                id=note_id,
                title=result.note_title or draft.title,
                body=result.note_body or draft.body,
                confidence=result.confidence,
                created=now,
                updated=now,
                sources=[source] if source else [],
            )
            vecs = embed.embed([note.body])
            note = _with_embedding(note, vecs[0])
            self.write(note)
            self._index.record_activation_event(note_id, result.l1_target_ids)
            result.note_id = note_id  # type: ignore[attr-defined]
            log.info("store.wrote op=%s id=%s", op, note_id)

        elif op in ("UPDATE", "EDIT"):
            if not result.target_ids:
                return
            target_id = result.target_ids[0]
            md_path = self._notes_dir / f"{target_id}.md"
            if not md_path.exists():
                log.warning("store.update_target_missing id=%s", target_id)
                return
            existing = ZettelNote.from_markdown(md_path.read_text(encoding="utf-8"))
            note = ZettelNote(
                id=existing.id,
                title=result.note_title or existing.title,
                body=result.note_body or existing.body,
                confidence=existing.confidence,
                created=existing.created,
                updated=now,
                sources=existing.sources,
                embedding=existing.embedding,
            )
            vecs = embed.embed([note.body])
            note = _with_embedding(note, vecs[0])
            self.write(note)
            # Record activation against L1-identified cluster for both UPDATE and EDIT
            l1_others = [t for t in result.l1_target_ids if t != target_id]
            self._index.record_activation_event(target_id, l1_others)
            result.note_id = target_id  # type: ignore[attr-defined]
            log.info("store.wrote op=%s id=%s", op, target_id)

        elif op == "SPLIT":
            if not result.target_ids:
                return
            source_id = result.target_ids[0]
            md_path = self._notes_dir / f"{source_id}.md"
            if not md_path.exists():
                log.warning("store.split_target_missing id=%s", source_id)
                return
            existing = ZettelNote.from_markdown(md_path.read_text(encoding="utf-8"))
            # Rewrite the source note with the first half
            note1 = ZettelNote(
                id=source_id,
                title=result.note_title or existing.title,
                body=result.note_body or existing.body,
                confidence=existing.confidence,
                created=existing.created,
                updated=now,
                sources=existing.sources,
            )
            # Allocate the second note's ID now so note1 can reference it correctly
            new_id = self._next_id() if (result.split_title and result.split_body) else None
            # Resolve bare partner title link in note1's body, e.g. [[Title]] → [[id|Title]]
            body1 = note1.body
            if new_id and result.split_title:
                body1 = body1.replace(
                    f"[[{result.split_title}]]",
                    f"[[{new_id}|{result.split_title}]]",
                )
            note1 = ZettelNote(
                id=note1.id, title=note1.title, body=body1,
                confidence=note1.confidence,
                created=note1.created, updated=note1.updated,
            )
            vecs1 = embed.embed([note1.body])
            note1 = _with_embedding(note1, vecs1[0])
            self.write(note1)
            result.note_id = source_id  # type: ignore[attr-defined]
            log.info("store.wrote op=SPLIT id=%s (first half)", source_id)
            # Create a new note for the second half
            if new_id and result.split_title and result.split_body:
                note2 = ZettelNote(
                    id=new_id,
                    title=result.split_title,
                    body=result.split_body,
                    confidence=result.confidence,
                            created=now,
                    updated=now,
                        sources=[source] if source else [],
                )
                vecs2 = embed.embed([note2.body])
                note2 = _with_embedding(note2, vecs2[0])
                self.write(note2)
                log.info("store.wrote op=SPLIT id=%s (second half)", new_id)
            # Record activation for source note against L1-identified cluster
            l1_others = [t for t in result.l1_target_ids if t != source_id]
            self._index.record_activation_event(source_id, l1_others)
            # Record activation for new note against source + L1 cluster
            if new_id:
                all_related = [source_id] + [t for t in result.l1_target_ids if t != source_id]
                self._index.record_activation_event(new_id, all_related)

    # ------------------------------------------------------------------
    # search
    # ------------------------------------------------------------------

    def query(
        self,
        question: str,
        llm: "ToolLLMProvider",
        *,
        max_rounds: int = 20,
    ) -> str:
        """Answer *question* by navigating the store with the Iter 4 skill.

        Uses an agentic loop: the LLM calls list_notes / grep_notes /
        read_note / find_related until it has enough context to synthesise
        an answer.  Unlike :meth:`search`, this returns a synthesised text
        response rather than a list of notes.

        *llm* must satisfy the :class:`~zettelkasten.providers.ToolLLMProvider`
        protocol (tool-use capable).  :class:`~zettelkasten.providers.AnthropicToolLLM`
        is the concrete implementation for the Anthropic API.
        """
        from .enrich import query as _query
        from .providers import ToolLLMProvider

        return _query(question, self._notes_dir, llm, max_rounds=max_rounds)

    def search(
        self,
        query: str,
        llm: LLMProvider,
        embed: EmbedProvider,
        top_k: int = 10,
    ) -> list[ZettelNote]:
        """Return up to *top_k* notes relevant to *query* using the Gather signals."""
        from .gather import gather_phase

        corpus = self._load_corpus()
        if not corpus:
            return []

        # Create a temporary draft from the query text
        now = datetime.now(tz=timezone.utc)
        query_note = ZettelNote(
            id="",
            title="",
            body=query,
            confidence=0.0,
            created=now,
            updated=now,
        )
        return gather_phase(query_note, corpus, llm, embed, top_k=top_k)

# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _with_embedding(note: ZettelNote, vec) -> ZettelNote:
    """Return a copy of *note* with the embedding set."""
    import numpy as np
    import dataclasses
    return dataclasses.replace(note, embedding=np.array(vec, dtype=np.float32))
