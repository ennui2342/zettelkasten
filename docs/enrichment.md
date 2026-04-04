# Query and Enrichment

## Overview

`store.query()` answers a question by navigating the note store as a filesystem — searching, reading, and following links iteratively until the LLM has enough context to synthesise a response. It does not retrieve a fixed top-k set and inject it all at once.

This document explains why that design was chosen, how the navigation loop works, and when to use `query()` versus `search()`.

---

## Why iterative navigation, not retrieval injection

The naive approach to querying a note store is: embed the question, retrieve the top-20 notes, inject them all into context, generate a response. At 20 notes averaging ~6k chars each, that costs ~120k tokens before the response — the entire context window of many models.

**A memory system that consumes all the context to use it has limited practical value.** Context efficiency is not a nice-to-have; it determines whether the system can be deployed at all.

The alternative, validated in the enrichment spike, comes from observing how Claude Code navigates large codebases. It doesn't load the codebase into context — it navigates it. The key insight is that lightweight orientation tools (`grep`, `glob`) are nearly free; full file reads are expensive. The agent builds a map cheaply, then reads surgically.

Applied to the zettelkasten:

- `grep_notes` costs almost nothing — it scans titles and bodies and returns matching lines
- `read_note` costs ~6k tokens per note
- Note titles are descriptive enough to judge relevance without reading the body

The agent anchors on relevant notes via grep, reads 2-3, follows their See Also links to discover adjacent notes it wouldn't have named, and stops when covered. Total context cost: 7-11 reads × ~6k chars = **42-66k tokens**, versus 120k for full top-20 injection.

### Iteration beats single-shot

Spike results on the existing 31-note store (12 evaluation questions):

| Mode | Avg reads | Synthesis completion |
|------|-----------|----------------------|
| No skill (baseline) | 16.1 | 42% |
| Iter 4 skill | 7.7 | 100% |

Iteration reduces reads by half while achieving 100% synthesis completion (the baseline frequently hit the read limit before synthesising). The improvement comes from two mechanisms: a clear stopping criterion (stop when covered, not when reads are exhausted), and See Also link following (finds adjacent notes that keyword search misses).

---

## The notes are already synthesised

The zettelkasten notes are not summaries of individual papers — they are cross-paper concept syntheses. After ingesting 20 papers, the store holds ~30 notes, each integrating insights from multiple papers into a single coherent concept. Redundancy and raw prose are stripped; conceptual density is high.

This means reading 7-11 notes from a 30-note store gives the agent concentrated coverage of the conceptual territory — the equivalent of having read the important conclusions across all 20 source papers, but at a fraction of the token cost. The ingestion synthesis (Form → Gather → Integrate) paid down this cost upfront.

**What query is strong at:** questions that require synthesising formal results across papers into a structure no individual paper states. The integrated notes surface cross-paper chains that aren't visible in raw sources.

**What query is less strong at:** questions where the answer lives in each paper's own limitation and related-work sections — explicit disagreements, tensions each paper acknowledges, combinations listed in future-work. These require reading the raw seams between documents, which the ingestion synthesis has compressed away.

---

## The three tools

The query loop gives the LLM three tools:

### `list_notes`

Returns all note IDs and titles in the store. Use this to scan what is available before committing to reads. Note titles are expressive navigational signals — "Procedural Memory as the Mechanism That Closes the Learning Loop" tells you whether to read the note without opening it.

```
z20260315-001: Procedural Memory as the Mechanism That Closes the Learning Loop
z20260315-002: Activation-Weighted Retrieval via Co-Occurrence Graphs
...
```

### `grep_notes`

Case-insensitive regex search across note titles and bodies. Returns matching note IDs, titles, and up to 5 matches per note (title match plus body lines; truncated at 120 chars each). Supports full regex: `|` for OR, `\b` for word boundaries.

This is the primary anchoring tool. Grep finds what you can name. Start here.

### `read_note`

Returns the title and body of a note by ID, with frontmatter stripped. Notes end with a `## See Also` section listing related notes with brief descriptions. After reading a note, check its See Also links to discover adjacent notes that wouldn't appear in a keyword search — this is the primary way to find notes that are conceptually close but lexically distant from the query.

---

## The navigation skill (Iter 4)

The system prompt injected into the query loop encodes the validated navigation strategy:

1. **Start with `grep_notes`** to anchor on notes relevant to the question
2. **Scan titles** with `list_notes` if grep doesn't surface enough candidates — titles are sufficient for relevance judgement
3. **Read anchored notes**, checking their See Also sections for adjacent notes
4. **Follow See Also links** to notes that are conceptually related but wouldn't appear in a keyword search — this is how the agent recovers from vocabulary gaps
5. **Stop when covered** — not when reads are exhausted. More reads is not better

The stopping criterion (step 5) was the single largest efficiency win in the spike: read count dropped from 16.1 to 5 in the first iteration that added it.

See Also link following was the second largest win: it enabled recovery of notes in vocabulary-adjacent clusters that grep couldn't reach directly.

---

## Implementation

The agentic loop is in `src/zettelkasten/enrich.py`. `store.query()` delegates to `enrich.query()`:

```python
def query(question, notes_dir, llm, *, max_rounds=20) -> str:
    messages = [{"role": "user", "content": question}]
    for round_num in range(max_rounds):
        text, tool_calls = llm.complete_tools(messages, TOOL_SPECS, system=ENRICH_SKILL, ...)
        if not tool_calls:
            return text   # LLM synthesised its answer
        # execute tools, append results, continue
    raise RuntimeError("exceeded max_rounds")
```

The loop runs until the LLM returns a text response with no tool calls (it has synthesised its answer) or until `max_rounds` is exceeded.

**`llm` must be a `ToolLLMProvider`** — it needs to support the tool-use protocol. Use `AnthropicToolLLM` for the Anthropic API. The same `llm.model` config key used for ingestion is used for query; `fast_model` is not used here.

---

## `query()` vs `search()`

| | `query()` | `search()` |
|---|---|---|
| Returns | Synthesised text answer | Ranked list of `ZettelNote` objects |
| LLM required | Yes (`ToolLLMProvider`) | Yes (`LLMProvider` for Gather signals) |
| Use when | You want an answer to a question | You want the notes themselves |
| Cost | 7-11 LLM rounds, ~42-66k tokens avg | One Gather pass |

Use `search()` when you want to inspect or display the relevant notes directly. Use `query()` when you want a synthesised answer and are happy to let the agent decide which notes to read.
