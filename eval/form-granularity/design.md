# Spike 2 — Fuzzy Document Form Phase

**Hypothesis under test:** H10 — single-shot topic extraction from fuzzy documents is sufficient; locate-then-summarise scaffolding is not needed.

---

## Outcome (completed 2026-03-14) — Go

Two runs on a synthetic 1,172-word article ("Forgetting Is Not the Enemy") with four interwoven topics (testing effect, spaced repetition, generation effect, external tools) and deliberately ambiguous boundary sentences. Four seeded prior notes in `spikes/spike2-fuzzy-form/prior-notes/`. Full results in `spikes/spike2-fuzzy-form/results.md`.

**Approach A (stepped, CARPAS count-first):** unstable. Count varied from 8 (run 1, too fine) to 2 (run 2, too coarse) with modest prompt changes. The count step amplifies variance rather than constraining it.

**Approach B (single-shot):** converged on 4 topics (matching the 4 ground-truth topics) in run 2 with no scaffolding. Correctly absorbed sub-topics (Elaborative Interrogation) under the right parent note rather than splitting them out. All three deliberately ambiguous sentences appeared in both expected topic extractions. Padding content suppressed naturally.

**Findings:**
- **Single-shot selected.** The CARPAS count-first scaffold is eliminated — it is makework that a capable model does not need when the prompt specifies broad topic areas with sub-topics-belong-inside guidance.
- **Scattered content collection confirmed.** Relevant material collected from across the article regardless of paragraph position.
- **Ambiguous boundary sentences handled correctly.** Content at the boundary between two topics appeared in both relevant extractions.
- **Eventual coherence principle applies to Form phase.** Topic boundaries in fuzzy documents are genuinely indeterminate. Single-shot handles this by reasoning holistically rather than committing to a count.

---

## Validated Form Phase Prompt

```
The following document covers several distinct topic areas.
For each broad topic area, produce a topic note.

Guidelines:
- A topic area is broad enough to warrant its own Wikipedia article.
- Named techniques, mechanisms, or phenomena within a broader area belong inside one note — do not create a separate note for each named concept.
- Draw relevant content from anywhere — material may be scattered.
- If content sits at the boundary of two topics, include it in both.
- Write in your own words.
```

**Production version** (with format instruction, from `spikes/spike-e2e/e2e.py`):

```
The following document covers several distinct topic areas.
For each broad topic area, produce a topic note.

Guidelines:
- A topic area is broad enough to warrant its own Wikipedia article covering many aspects.
- Named techniques, mechanisms, or specific phenomena within a broader area belong inside
  one note — do not create a separate note for each named concept.
- Draw relevant content from anywhere in the document — relevant material may be scattered
  across paragraphs, not just adjacent.
- If content sits at the boundary between two topics, include it in both relevant notes.
- Write in your own words.

Format each topic note as:

## [Topic name]

[Content]
```

The `## [Topic name]` format is load-bearing — the Form phase parser splits the LLM output on `##` headings to produce individual draft notes.

**Note:** H1 (Predict-Calibrate) was resolved as "subsumed by NOTHING" (Spike 3). There is no learnability filter — the integration LLM's NOTHING decision handles irrelevant content.
