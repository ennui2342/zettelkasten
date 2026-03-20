# Spike 3 — Integration Decision Quality

**Hypothesis under test:** H1 (predict-calibrate subsumed by NOTHING), H5 (SYNTHESISE operation).

---

## Outcome (completed 2026-03-14) — Go

One run on 14 synthetic test cases covering all 7 operations (2 per operation, except UPDATE ×3 and CREATE ×1). All material in the memory science domain. Full results in `spikes/spike3-integration/results.md`.

**Score: 12/14 correct (85%), 14/14 consistent (all 3 runs per case agreed).**

| Operation | Cases | Correct | Notes |
|-----------|-------|---------|-------|
| UPDATE | 3 | 3/3 | Perfect. Model reads documented gaps and matches content to them. |
| CREATE | 1 | 1/1 | Perfect. |
| NOTHING | 2 | 2/2 | Perfect. Not under-triggered. Confidence 0.95. |
| STUB | 2 | 1/2 | stub-1 called CREATE — see below. stub-2 (empty cluster) correct at confidence 0.40. |
| SPLIT | 2 | 2/2 | Perfect. Model names the conflation and how to split it. |
| MERGE | 2 | 1/2 | merge-1 called SYNTHESISE — see below. merge-2 (same phenomenon, different terminology) correct. |
| SYNTHESISE | 2 | 2/2 | Perfect. |

**Findings:**

- **7-way decision is reliable.** UPDATE, CREATE, NOTHING, SPLIT, and SYNTHESISE fire correctly on well-formed cases. Consistency is 100% — zero variance across runs.
- **STUB/CREATE boundary is semantic isolation, not content richness.** stub-1 (sleep consolidation) was called CREATE because the prompt said "sparse or empty cluster" but the model used content richness as a tiebreaker. This was a prompt definition issue: the intended STUB criterion is sparse neighbourhood (few adjacent notes to corroborate), not thin content. A rich 250-word draft in an empty KB neighbourhood is still STUB. The prompt has been updated to make this explicit.
- **MERGE/SYNTHESISE boundary is sharpened.** MERGE = obvious identity, no new structure needed (two notes are redundant). SYNTHESISE = unifying principle articulated (the draft does conceptual work that neither note does). The model correctly distinguished these when the cases were unambiguous; merge-1 was called SYNTHESISE because the draft introduced encoding specificity as a new unifying principle — a defensible and arguably correct call.
- **Documented gaps are a strong signal.** `**Gap:**` and `**Open question:**` frontmatter sections in notes are read and matched against draft content, driving high-confidence UPDATE decisions. This is a design cue worth preserving in the production schema.

---

## Validated Integration Prompt

```
You maintain a knowledge base of topic notes. You have a draft note and a cluster of related existing notes.

Draft note:
{draft}

Existing notes in cluster:
{cluster}

Decide what action to take. Choose exactly one:

- UPDATE: the draft adds to an existing note. Rewrite that note to synthesise old and new — do not append. Specify which note by its id field.
- CREATE: the draft covers a topic not in the cluster. Create a new note with links to relevant existing notes.
- SPLIT: an existing note conflates two distinct topics that the draft clarifies should be separate. Specify which note and how to split it.
- MERGE: two existing notes in the cluster cover the same topic. The draft confirms they should be one. Specify which notes.
- SYNTHESISE: the draft reveals a connection between two existing notes that neither captures. Create a new structure note articulating the bridging principle. Specify which notes it bridges.
- NOTHING: the draft is already fully covered by the existing cluster. No action needed.
- STUB: the cluster is sparse or empty — this is a new topic without an established neighbourhood. The signal is semantic isolation, not content thinness. Even a rich, well-developed draft belongs here if there are few or no adjacent notes to corroborate it. Create a provisional note at low confidence.

For UPDATE and CREATE, if the draft contradicts an existing note rather than adding to it, use CREATE and add a `contradicts` link to the conflicting note — keep competing views as separate notes.

Output JSON only. Schema:
{"operation": "<one of the seven>", "target_note_ids": ["<id>", ...], "reasoning": "<one or two sentences>", "confidence": <0.0 to 1.0>}
```

---

## One-shot vs Two-step Integration Design

The prompt above is one-shot: a single LLM call produces both the operation decision *and* the new content. An alternative is two-step:

1. Step 1 (classify): send draft + cluster, output operation type + target note IDs
2. Step 2 (execute): send step 1's decision + target note(s) + draft, output new content

Two-step benefits: each step gets a cleaner, more focused prompt; step 1 could use a cheaper model for classification; the operation type is explicit in the pipeline log rather than inferred from the output.

**Monitoring concern (not yet resolved at spike time).** In one-shot, the operation label and the content are produced in one pass and are necessarily coherent — the LLM that chose "UPDATE" also wrote the updated content, so what it wrote matches what it decided. In two-step, step 2 does not receive step 1's chain-of-thought; it knows only the operation type and target note. Step 2 may produce content that diverges from what step 1 intended (e.g., step 1 classifies "UPDATE — add a section on X," but step 2 effectively rewrites the full note). The monitoring system records the step 1 label; the actual change is larger or smaller than that label implies. Over time, operation-type distribution metrics become unreliable proxies for what the system is actually doing to the corpus. To recover reliability you'd need to diff note content before/after each event, which is a heavier monitoring step.

**Resolution: measure in E2E spike, not assumed.** The Bitter Lesson argument suggests one-shot will eventually match two-step on capability. But "eventually" is not "now" — each step was validated separately in Spike 3, and we have not tested whether a one-shot approach matches that combined performance. The end-to-end spike should run both and compare decision quality and content coherence directly.

**Outcome (E2E spike):** Two-step selected. Step 1 (temperature=0, max_tokens=512) classifies; Step 2 (temperature=0.3, max_tokens=4096/2048) executes. The classification step uses a cheaper/faster model (Haiku); the execution step uses the quality model (Opus).
