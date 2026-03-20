"""Spike: spontaneous topical links via formatting instruction only.

No extra LLM call. No cluster index. A single sentence is appended to every
step 2 prompt:

  "If you feel a genuine connection to any note visible in your context above,
   express it in a ## See Also section using [[id|title]] — relationship syntax.
   Omit the section if no genuine connection exists."

Links can only form to notes the LLM already sees in {targets} — i.e. notes
that were retrieved into this cluster and flagged by step 1. If a connection
exists but the target wasn't retrieved, the LLM will express it in prose.
That prose becomes a wikilink when a future ingestion brings the two notes
into the same cluster and triggers an UPDATE.

Relationship vocabulary (keep small for consistency):
  elaborates | applies | grounds | contrasts | exemplifies
"""
from __future__ import annotations

from zettelkasten.integrate import (
    _CURATION_OPS,
    _EXECUTABLE_OPS,
    _STEP2_MAX_TOKENS,
    _step1_classify,
    _parse_title_body,
    IntegrationResult,
)
from zettelkasten.note import ZettelNote
from zettelkasten.providers import LLMProvider
import logging

log = logging.getLogger("zettelkasten.spike")

_SEE_ALSO_INSTRUCTION = (
    "\n\nIf you feel a genuine connection to any note visible in your context "
    "above, add a ## See Also section at the very end:\n\n"
    "## See Also\n\n"
    "- [[<id>|<title>]] — <elaborates | applies | grounds | contrasts | exemplifies>\n\n"
    "Omit the section entirely if no genuine connection exists."
)


def spike_integrate_phase(
    draft: ZettelNote,
    cluster: list[ZettelNote],
    llm: LLMProvider,
) -> IntegrationResult:
    log.info("spike.integrate draft_title=%r cluster_size=%d", draft.title, len(cluster))

    decision = _step1_classify(draft, cluster, llm)
    op        = decision["operation"]
    target_ids = decision.get("target_note_ids") or []
    reasoning  = decision.get("reasoning", "")
    confidence = float(decision.get("confidence", 0.0))

    log.info("spike.integrate step1 op=%s confidence=%.2f", op, confidence)

    if op in _CURATION_OPS:
        return IntegrationResult(
            operation=op, reasoning=reasoning, confidence=confidence,
            target_ids=target_ids, is_curation=True,
        )
    if op == "NOTHING":
        return IntegrationResult(operation="NOTHING", reasoning=reasoning, confidence=confidence)
    if op not in _EXECUTABLE_OPS:
        return IntegrationResult(operation="NOTHING", reasoning=f"Unknown op {op!r}", confidence=0.0)

    target_notes = [n for n in cluster if n.id in target_ids]
    title, body  = _spike_step2(op, draft, target_notes, llm)

    log.info("spike.integrate step2 op=%s title=%r", op, title)
    return IntegrationResult(
        operation=op, reasoning=reasoning, confidence=confidence,
        target_ids=target_ids, note_title=title, note_body=body,
    )


def _spike_step2(
    op: str,
    draft: ZettelNote,
    targets: list[ZettelNote],
    llm: LLMProvider,
) -> tuple[str, str]:
    from zettelkasten.integrate import _STEP2_PROMPTS
    template     = _STEP2_PROMPTS[op] + _SEE_ALSO_INSTRUCTION
    draft_text   = f"## {draft.title}\n\n{draft.body}"
    targets_text = "\n\n---\n\n".join(
        f"id: {n.id}\n## {n.title}\n\n{n.body}" for n in targets
    ) if targets else "(none)"
    prompt = template.format(draft=draft_text, targets=targets_text)
    raw    = llm.complete(prompt, max_tokens=_STEP2_MAX_TOKENS[op], temperature=0.3)
    return _parse_title_body(raw)
