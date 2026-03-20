"""All LLM prompt constants for the zettelkasten pipeline.

Shared guidelines are defined once and composed into per-phase prompts.
Add new shared guidelines here; include them in every prompt that writes
note content.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Shared writing guidelines
# ---------------------------------------------------------------------------

# Included in every prompt that generates note body content.
_NO_SOURCE_REFS = (
    'Write in your own words. Never use source-referential phrases such as '
    '"this paper", "the authors", "this article", "the study", "they show", '
    'or "the proposed method" — write as if synthesising knowledge, not '
    'summarising a document.'
)

# ---------------------------------------------------------------------------
# Shared See Also snippets (appended to relevant Step 2 prompts)
# ---------------------------------------------------------------------------

_SEE_ALSO = (
    "\n\nIf you feel a genuine connection to any note visible in your context "
    "above, add a ## See Also section at the very end:\n\n"
    "## See Also\n\n"
    "- [[<id>|<title>]] — <elaborates | applies | grounds | contrasts | exemplifies>\n\n"
    "Omit the section entirely if no genuine connection exists."
)

_SEE_ALSO_SPLIT = (
    "\n\nFor each section, if you feel a genuine connection to any note visible "
    "in your context above, add a ## See Also section at the end of that section "
    "before the ---SPLIT--- delimiter (or at the end of the second section):\n\n"
    "## See Also\n\n"
    "- [[<id>|<title>]] — <elaborates | applies | grounds | contrasts | exemplifies>\n\n"
    "Use [[<id>|<title>]] for all existing notes. "
    "To cross-reference the partner split note, use bare [[<title>]] — "
    "the ID will be resolved automatically after both notes are written.\n\n"
    "Omit the section entirely from either note if no genuine connection exists."
)

# ---------------------------------------------------------------------------
# Form phase
# ---------------------------------------------------------------------------

_FORM_PROMPT = (
    "The following document covers several distinct topic areas.\n"
    "For each broad topic area, produce a topic note.\n"
    "\n"
    "Guidelines:\n"
    "- A topic area is broad enough to warrant its own Wikipedia article covering many aspects.\n"
    "- Named techniques, mechanisms, or specific phenomena within a broader area belong inside\n"
    "  one note — do not create a separate note for each named concept.\n"
    "- Draw relevant content from anywhere in the document — relevant material may be scattered\n"
    "  across paragraphs, not just adjacent.\n"
    "- If content sits at the boundary between two topics, include it in both relevant notes.\n"
    f"- {_NO_SOURCE_REFS}\n"
    "\n"
    "Format each topic note as:\n"
    "\n"
    "## [Topic name]\n"
    "\n"
    "[Content]\n"
    "\n"
    "Document:\n"
    "{document}"
)

# ---------------------------------------------------------------------------
# Integrate: Step 1 — classify
# ---------------------------------------------------------------------------
# Integrate: Step 1 L1 — SYNTHESISE / INTEGRATE / NOTHING
# ---------------------------------------------------------------------------

_STEP1_L1_PROMPT = """\
You maintain a knowledge base of topic notes. You have a draft note and a \
cluster of related existing notes.

Draft note:
{draft}

Existing notes in cluster:
{cluster}

Decide how this draft relates to the existing cluster.

Choose exactly one:

- INTEGRATE: the draft is an elaboration of the notes in the cluster. It adds \
to, extends, fills a gap, or enhances the insights of existing notes and \
should be integrated.
- SYNTHESISE: the draft reveals a connection between the notes in the cluster \
that produces a new insight none of the notes articulate on their own. The \
connection must earn its existence — use SYNTHESISE only when the relationship \
itself is the knowledge, not merely because two things are related.
- NOTHING: the draft is already fully covered by the existing cluster and adds \
nothing new.

In target_note_ids, list the notes the draft most directly interacts with. \
For SYNTHESISE, list the notes being bridged. For INTEGRATE or NOTHING, list \
the most relevant notes.

Output JSON only. Schema:
{{
  "operation": "INTEGRATE" | "SYNTHESISE" | "NOTHING",
  "target_note_ids": ["<id>", ...],
  "reasoning": "<one or two sentences>",
  "confidence": <0.0 to 1.0>
}}"""

# ---------------------------------------------------------------------------
# Integrate: Step 1 L2 — CREATE / UPDATE / NOTHING
# ---------------------------------------------------------------------------

_STEP1_L2_PROMPT = """\
You maintain a knowledge base of topic notes. You have a draft note and a \
cluster of closely related existing notes.

Draft note:
{draft}

Existing notes in cluster:
{cluster}

Decide what to do with this draft.

Choose exactly one:

- UPDATE: the draft adds new content to an existing note in the cluster — it \
extends, refines, or fills a gap in a note already about this topic. Select \
the single best target note.
- CREATE: the draft introduces a topic not sufficiently covered by any note in \
the cluster. A new note is needed.
- NOTHING: the draft is already fully covered by the cluster notes. No new \
note is needed and no update is warranted.

UPDATE requires the draft to be on the same topic as an existing note — not \
merely related or adjacent. When in doubt between UPDATE and CREATE, \
prefer CREATE.

In target_note_ids, for UPDATE provide the single best target note ID. For \
CREATE and NOTHING, list the most relevant cluster notes.

Output JSON only. Schema:
{{
  "operation": "UPDATE" | "CREATE" | "NOTHING",
  "target_note_ids": ["<id>"],
  "reasoning": "<one or two sentences>",
  "confidence": <0.0 to 1.0>
}}"""

# ---------------------------------------------------------------------------
# Integrate: Step 1 (legacy single-pass classifier — kept for reference)
# ---------------------------------------------------------------------------

_STEP1_PROMPT = """\
You maintain a knowledge base of topic notes. You have a draft note and a \
cluster of related existing notes.

Draft note:
{draft}

Existing notes in cluster:
{cluster}

Decide what action to take. Choose exactly one:

- UPDATE: the draft adds to an existing note. Rewrite that note to synthesise \
old and new — do not append.
- CREATE: the draft covers a topic not in the cluster. Create a new note.
- SPLIT: an existing note conflates two distinct topics that the draft \
clarifies should be separate.
- SYNTHESISE: the draft reveals a connection between two existing notes that \
produces new insight neither note captures on its own. Create a new structure \
note articulating the bridging principle. The bridge note must earn its \
existence — use SYNTHESISE only when the relationship itself is the knowledge, \
not merely because two things are related.
- NOTHING: the draft is already fully covered by the existing cluster. No \
action needed.
- STUB: the cluster is sparse or empty — this is a new topic without an \
established neighbourhood. Create a provisional note at low confidence.

If the cluster is empty, STUB is the appropriate default unless the draft is \
clearly a subtopic of notes in the broader knowledge base.

In target_note_ids, list the existing notes that this draft directly \
INTERACTS with — notes whose content this draft meaningfully extends, \
challenges, or bridges. For UPDATE/SPLIT the primary operation target must \
be listed first; for CREATE/STUB include the most relevant neighbours; for \
SYNTHESISE include the notes being bridged.

Output JSON only. Schema:
{{
  "operation": "<one of the six>",
  "target_note_ids": ["<id>", ...],
  "reasoning": "<one or two sentences>",
  "confidence": <0.0 to 1.0>
}}"""

# ---------------------------------------------------------------------------
# Integrate: Step 1.5 — refine UPDATE on large notes
# ---------------------------------------------------------------------------

_STEP1_5_PROMPT = """\
You are reviewing an UPDATE decision for a note that has grown very large \
({note_size} chars). Assess whether the note should be split or compressed.

Note:
{target}

Choose exactly one:

- EDIT: the note covers one coherent topic. Compress and distil it.
- SPLIT: the note contains two distinct topics that should each be their \
own note. Divide it.

SPLIT requires clear evidence of two separable threads within the note \
itself. When uncertain, choose EDIT.

Output JSON only. Schema:
{{
  "operation": "EDIT" | "SPLIT",
  "reasoning": "<one or two sentences>",
  "confidence": <0.0 to 1.0>
}}"""

# ---------------------------------------------------------------------------
# Integrate: Step 2 — execute
# ---------------------------------------------------------------------------

_STEP2_CREATE = (
    "Execute a CREATE operation.\n"
    "\n"
    "Draft note (content for the new note):\n"
    "{draft}\n"
    "\n"
    "Related notes in cluster (for context):\n"
    "{targets}\n"
    "\n"
    f"{_NO_SOURCE_REFS}\n"
    "\n"
    "Output format — a markdown heading followed by the note body:\n"
    "\n"
    "## [Note title]\n"
    "\n"
    "[Note body]\n"
    "\n"
    "Output only the heading and body. No frontmatter, no preamble."
) + _SEE_ALSO

_STEP2_EDIT = (
    "Execute an EDIT operation on the existing note.\n"
    "\n"
    "Existing note to compress:\n"
    "{targets}\n"
    "\n"
    "Draft note (integrate new content into the rewritten note):\n"
    "{draft}\n"
    "\n"
    "Rewrite the existing note to be tighter and more concise, integrating any "
    "new insights from the draft. Remove redundancy, repeated framings of the same "
    "point, and over-elaboration. Preserve all essential claims, distinctions, and "
    "examples.\n"
    "\n"
    "The rewritten note must be meaningfully shorter than the original.\n"
    "\n"
    "Output format — a markdown heading followed by the rewritten note body:\n"
    "\n"
    "## [Note title]\n"
    "\n"
    "[Note body]\n"
    "\n"
    "Output only the heading and body. No frontmatter, no preamble."
)

_STEP2_UPDATE = (
    "Execute an UPDATE operation on the existing note.\n"
    "\n"
    "Draft note (new content to integrate):\n"
    "{draft}\n"
    "\n"
    "Existing note to update:\n"
    "{targets}\n"
    "\n"
    "Rewrite the existing note to synthesise old and new content into a single "
    "coherent note. Do not append — integrate the new material throughout so the "
    "result reads as a unified topic note. Preserve the note's identity and core "
    "claims; add, clarify, or correct where the draft warrants it.\n"
    "\n"
    f"{_NO_SOURCE_REFS}\n"
    "\n"
    "Output format — a markdown heading followed by the rewritten note body:\n"
    "\n"
    "## [Note title]\n"
    "\n"
    "[Note body]\n"
    "\n"
    "Output only the heading and body. No frontmatter, no preamble."
) + _SEE_ALSO

_STEP2_SYNTHESISE = (
    "Execute a SYNTHESISE operation.\n"
    "\n"
    "Draft note (reveals the connection):\n"
    "{draft}\n"
    "\n"
    "Existing notes being bridged:\n"
    "{targets}\n"
    "\n"
    "Create a new structure note that articulates the bridging principle connecting "
    "the target notes. This note should express what neither target note currently "
    "captures — the connecting insight or unifying mechanism.\n"
    "\n"
    f"{_NO_SOURCE_REFS}\n"
    "\n"
    "Output format — a markdown heading followed by the note body:\n"
    "\n"
    "## [Note title]\n"
    "\n"
    "[Note body]\n"
    "\n"
    "Output only the heading and body. No frontmatter, no preamble."
) + _SEE_ALSO

_STEP2_STUB = (
    "Execute a STUB operation.\n"
    "\n"
    "Draft note (new topic without established neighbourhood):\n"
    "{draft}\n"
    "\n"
    "Create a minimal stub note. Include: concept title, 1-2 sentence definition, "
    "and 3-5 synonyms or related terms to make the note retrievable in future. "
    "Keep it brief but specific.\n"
    "\n"
    f"{_NO_SOURCE_REFS}\n"
    "\n"
    "Output format — a markdown heading followed by the stub body:\n"
    "\n"
    "## [Note title]\n"
    "\n"
    "[Note body]\n"
    "\n"
    "Output only the heading and body. No frontmatter, no preamble."
)

_STEP2_SPLIT = (
    "Execute a SPLIT operation.\n"
    "\n"
    "Note to split:\n"
    "{targets}\n"
    "\n"
    "Draft note (integrate into the appropriate output note):\n"
    "{draft}\n"
    "\n"
    "The existing note conflates two distinct topics. Identify the two threads "
    "within the note itself and rewrite it as TWO separate topic notes by "
    "partitioning its content. Each output note contains only the content "
    "relevant to its topic. Integrate any new insights from the draft into "
    "whichever output note they best belong to.\n"
    "\n"
    "The first note retains the original note's title and identity. Assign an "
    "appropriate new title to the second. Both notes together should account for "
    "all content in the original. Each note will be meaningfully shorter than "
    "the original since it carries only one thread.\n"
    "\n"
    f"{_NO_SOURCE_REFS}\n"
    "\n"
    "Output format — exactly two sections separated by the delimiter below:\n"
    "\n"
    "## [First note title]\n"
    "\n"
    "[First note body]\n"
    "\n"
    "---SPLIT---\n"
    "\n"
    "## [Second note title]\n"
    "\n"
    "[Second note body]\n"
    "\n"
    "Output only the two sections and the delimiter. No frontmatter, no preamble."
) + _SEE_ALSO_SPLIT

# Public dict consumed by integrate.py
STEP2_PROMPTS: dict[str, str] = {
    "CREATE":    _STEP2_CREATE,
    "EDIT":      _STEP2_EDIT,
    "UPDATE":    _STEP2_UPDATE,
    "SYNTHESISE": _STEP2_SYNTHESISE,
    "STUB":      _STEP2_STUB,
    "SPLIT":     _STEP2_SPLIT,
}
