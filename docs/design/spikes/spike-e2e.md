# Spike E2E — Form → Gather → Integrate (End-to-End)

**Purpose:** verify the full pipeline makes sensible decisions on real-ish input before committing to the build. All retrieval work is complete and validated against synthetic ground truth; this spike answers the qualitative question: *does the integration LLM actually do the right thing when given a real draft and a real cluster?*

Not a numbers-driven test. The question is whether the proposed edits are credible, appropriately scoped, and useful.

---

## Plan

**What to run:**

1. **Input:** the "Forgetting Is Not the Enemy" article from `spikes/spike2-fuzzy-form/article.md` — a dense article on memory consolidation, retrieval practice, the testing effect, and generation effects. This covers territory that the 299-note corpus overlaps with (spaced repetition, note-taking, learning science).

2. **Form:** produce draft notes from the article using the validated Spike 2 fuzzy boundary approach (or simply use the full article as a single input to the integration LLM — the point is to see what the integration decides, not to validate Form again).

3. **Gather:** run the tuned retrieval against the corpus (`spikes/spike4a-cluster/corpus/`). Weights: `body_query=0.450, bm25_mugi_stem=0.270, activation=0.180, step_back=0.050, hyde_multi=0.050`. Top-20 cluster.

4. **Integrate:** run the validated integration prompt with the draft + cluster. Inspect:
   - Which notes are targeted and why?
   - Are the operations (UPDATE/CREATE/STUB/etc.) appropriate to the content?
   - Is the proposed new or updated content coherent and non-redundant?
   - Are there obvious misses — notes that should have been surfaced but weren't?

5. **Two-step comparison (optional):** run the same input with a two-step approach (classify first, then execute) and compare output quality and decision coherence.

**Implementation:** a standalone Python script in `spikes/spike-e2e/`, not a full aswarm pipeline. The script imports retrieval workbench utilities for gather and makes direct LLM calls for integration. Estimated ~100 lines.

**Success criteria (qualitative):** the integration LLM proposes edits that a thoughtful human would consider appropriate — right notes targeted, right operation chosen, content that adds rather than duplicates. No success threshold on numbers; this is a sanity check and a staging ground for prompt iteration before the build.

**Decisions this will inform:**
- One-shot vs two-step: which produces more coherent content and better audit trails
- Whether the integration prompt needs revision for the full-article case (Spike 3 tested shorter drafts)
- Whether K=20 is the right window for this type of dense, multi-topic input

---

## Findings (2026-03-15)

Ran against a synthetic "Desirable Difficulties" article designed to trigger all seven operations across a 300-note cognitive science corpus.

### Operations confirmed working

- **CREATE** — fired at confidence 0.92 for Bjork's desirable difficulties framework (absent from corpus). Produced a well-linked structure note with 7 outbound connections. Stable across two independent runs (same operation, same confidence, same targets).
- **SYNTHESISE** — fired at confidence 0.85–0.88 for reconstructive memory and context-dependent retrieval. Both cases found a third connecting note (encoding specificity principle) as the unifier rather than simply bridging two. The synthesised notes are substantively better than either source note alone.
- **UPDATE** — fired correctly in a double-loop test (same article fed twice). Loop 2 surfaced the notes created in loop 1 at rank 1 for every draft and updated them with real additions: specific data points from the source (Ebbinghaus dating, effect size magnitudes), extended examples, and a sixth bullet in the pedagogical implications. Content genuinely improved on the second pass rather than simply restating.
- **STUB** — observed in some runs for the Feynman Technique and SRS architecture; in others, CREATE fired instead. The boundary between STUB and CREATE depends on cluster density; both are correct behaviours at the boundary.

### Operations confirmed NOT triggered by ingestion

- **SPLIT** — never fired across six test runs including purpose-built conflated notes and four different article formulations. Root cause: Form always separates conceptually distinct content into multiple draft notes; each draft then targets the conflated note with UPDATE rather than SPLIT. SPLIT cannot be triggered through normal ingestion.
- **MERGE** — fired once at confidence 0.97 (corpus-ripe test, two explicit ringer notes, article arguing synonymy). Did not fire for article-implied test where only one ringer surfaced in the cluster. Requires both target notes in the same cluster simultaneously. Only reliable from the scheduled curation pass.
- **NOTHING** — never observed for real article content. UPDATE fires instead, even when the draft content is largely covered by the existing corpus. This is likely correct behaviour for a living knowledge base where progressive enrichment is preferable to idempotence. NOTHING may only fire for degenerate cases (a draft that is literally a strict subset of an existing note).

### Double-loop (idempotency) finding

Feeding the same article twice produces UPDATE not NOTHING. Loop 2 updates are genuinely enriching — they add specific details, data points, and framings that were in the source but abstracted out in the first CREATE. The analogy to memory consolidation is apt: repeated retrieval and reconstruction strengthens and elaborates the trace. Whether this is desirable (living knowledge base) or a problem (infinite refinement) depends on whether there is a practical similarity threshold below which NOTHING should fire. Parked for now; the enrichment behaviour appears net-positive.

### Token limit finding

step2 `max_tokens=2048` truncates full rewrites of long notes. UPDATE on a note already at 700+ tokens will be cut off, potentially losing the tail sections (boundary conditions, implications). Fixed by bumping UPDATE/SPLIT/MERGE/SYNTHESISE to 4096 tokens. STUB and CREATE retain 2048 (fresh notes are typically shorter).

### Activation signal

Notes created in loop 1 appeared in the top-5 cluster for every subsequent draft in the same run, confirming that sequential corpus mutation and the in-memory activation graph both function correctly. The activation graph built across sequential notes in a single article improves cluster quality for later drafts.

### One-shot vs two-step resolution

Two-step selected. The classification step (temperature=0, max_tokens=512) produces reliable JSON with full reasoning visible in the pipeline log. The execution step (temperature=0.3, max_tokens=4096/2048) benefits from a clean focused prompt. The monitoring cost of two-step (step 1 label vs actual change) is acceptable given the audit trail benefit.

---

## Design Decisions From This Spike

These decisions are reflected in the build plan:

1. **MERGE and SPLIT execute at ingestion time** — MERGE can fire when both targets appear in the same cluster; SPLIT is mechanically blocked by Form phase separation. Both run when triggered (MERGE may fire rarely at ingestion; SPLIT only via curation).

2. **max_tokens=4096** for UPDATE, SYNTHESISE, MERGE, SPLIT; 2048 for CREATE, STUB.

3. **Two-step integration** — Step 1: classify (Haiku, temp=0, 512 tokens). Step 2: execute (Opus, temp=0.3, 4096/2048 tokens).

4. **Cold-start activation** — all 5 signals active from day one; activation scores zero until events accumulate. Confirmed to work correctly under normalisation.
