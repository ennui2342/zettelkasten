# Spike 4 — Gather Phase (Cluster Identification, Link Vocabulary, Ground Truth)

Covers: 4A (cluster identification), 4B (stable notes — parked), 4C (link vocabulary — closed without spike), 4D (LLM ground truth).

---

## Hypothesis Status (after Spikes 1–3)

| Hypothesis | Status |
|------------|--------|
| H1 Predict-calibrate | Resolved — subsumed by NOTHING (Spike 3) |
| H2 Episode boundary detection | Resolved — Approach A, conf≥0.80 (Spike 1) |
| H3 Typed link traversal for retrieval | **Eliminated (Spike 4A)** — vocabulary for integration reasoning still open |
| H4 Three-component retrieval scoring | Open — recency/salience ablation not yet tested |
| H5 SYNTHESISE operation | Operation validated (Spike 3); note quality longitudinal |
| H6 Dual consolidation triggers | Open → post-spike build |
| H7 Conservative prior on stable notes | Open → Spike 4B |
| H8 Markdown filesystem (Bitter Lesson) | Long-horizon; longitudinal observation |
| H9 Graph traversal depth | **Eliminated (Spike 4A/4D)** — citation-style traversal removed |
| H10 Locate-then-summarise | Eliminated — doesn't apply to this system |
| H-new-A Activation-weighted co-retrieval links | **Confirmed (Spike 5)** — R@10=0.640 at α=0.2 vs 0.534 baseline; decay λ untested |
| H-new-B Non-acted-on notes add activation signal | **Eliminated (Spike 5)** — W_null=0.0 consistently better |
| H-new-C Vocabulary mismatch recoverable via BM25+MuGI | Open — Spike 6A |
| H-new-D Principle-level gaps recoverable via step-back prompting | Open — Spike 6B |

---

## Spike 4A — Cluster Identification

**Hypothesis cluster:** H3 (link traversal augmenting similarity), H4 (three-component scoring), H9 (graph traversal depth). Also: what to embed — note body, context field, or summary?

**What this tests:** given an incoming draft note, how do you find the right cluster of existing notes to present to the integration LLM?

### Outcome (completed 2026-03-15) — Go (body embedding); No-go (link traversal)

Evaluated on a 300-note Wikipedia cognitive science corpus using inter-article links as retrieval ground truth, then validated with LLM-judged ground truth (Spike 4D). Full results in `spikes/spike4a-cluster/results.md`.

**Embedding target: full body wins.** Body embedding (R@5=0.274, MRR=0.565) significantly outperforms context field / first sentence (R@5=0.212, MRR=0.464). LLM-generated 2–3 sentence summaries do not improve over body (MRR 0.751 vs 0.795 on 30-note subset). The full body already contains the retrieval signal; compression loses it.

**Link traversal: eliminated.** Depth-1 expansion grows clusters from 10 to 53 nodes on average (max 78); of the ~43 new nodes, only 15.6% are ground-truth targets. Depth-2 reaches 108 nodes — 36% of the corpus. The citation-style link graph short-circuits through hub articles. Both depth=1 and depth=2 strategies show worse recall than body-sim alone across all metrics.

**Tag-based expansion: eliminated.** LLM-extracted semantic tags show 0% discriminative signal on integration-relevant notes missed by body embedding.

**Design decisions:**
- Embed full note body (not context field)
- Citation-style link traversal: not used in Phase 2 Gather
- Default cluster window: top-20 (63% recall at LLM ground truth vs 49% at top-10)

**Hypotheses resolved:** H9 (graph traversal depth) eliminated. H3 revised: citation-style link traversal eliminated from retrieval; link vocabulary question for integration reasoning remains open (resolved in 4C). Embedding target question resolved in favour of full body.

---

## Spike 4B — Integration Phase: Stable Notes and Reconsolidation

**Status: parked.** 4B cannot be tested without real integration events — you need actual stability data built up over many passes to see the conservative prior in action, and reconsolidation requires a live evolving corpus to measure. Both questions are better answered empirically from a running system than from a synthetic spike. Revisit after ~100 real integration events.

**Two questions that would be tested:**

**H7 — Conservative prior on stable notes.** The integration prompt communicates note stability to the integration LLM, which should require stronger evidence to UPDATE or SPLIT a stable note. Does this work in practice? Does it prevent legitimate corrections (false negative) or correctly filter spurious contradictions (true positive)?

Test: present the integration LLM with cases where a stable note should resist UPDATE (weak new content, borderline conflict) and cases where it should accept UPDATE (strong new content, clear gap). Measure whether the `stable: true` flag changes decisions appropriately.

**Reconsolidation.** After integration writes a note, a lightweight pass over the cluster updates each neighbouring note's `context` field (the short LLM-generated semantic positioning description). The neighbourhood just changed — a note was updated or created — so adjacent notes' contextual descriptions may be stale, which would degrade Gather(A) retrieval on the next pass.

Note: the integration pass itself already constitutes a form of reconsolidation — pulling a cluster into context and deciding what to do IS the reconsolidation event. The `context` field evolution is an additional lightweight housekeeping step, not the mechanism itself.

Test: run a consolidation pass, then run a lightweight `context` evolution pass over the affected cluster. Measure whether the updated `context` fields improve retrieval in subsequent cluster identification (Spike 4A approaches).

**Go criteria:** H7 — stability flag produces correct direction of effect on UPDATE decisions. Reconsolidation — `context` field evolution measurably improves cluster retrieval precision.

---

## Spike 4C — Link Relation Vocabulary: Typed vs Untyped (H3)

**Status: closed. Decision recorded below. No spike needed.**

**The original question:** does a rich link relation vocabulary (supports, extends, refines, exemplifies, applies_to, synthesises, supersedes) improve integration decisions, or is it redundant with what the LLM infers from reading the linked note bodies?

**Design decision reached (2026-03-15):** links in this system are not semantic — they are **epistemic**. The distinction matters:

- *Semantic links* encode topical proximity: "this note is about a related subject." This is exactly what embeddings and activation already capture, more reliably and without maintenance burden. Any untyped `links:` field populated by the integration LLM would be a frozen, lower-fidelity snapshot of what retrieval already computes dynamically. These add nothing and are dropped.

- *Epistemic links* encode the logical relationship between two notes' *claims*: contradiction, revision, provenance. These cannot be inferred from similarity; two notes can be highly similar in topic and directly opposed in conclusion. Epistemic links are the only link type with genuine information content that the retrieval signals do not already capture.

**The retained vocabulary — three types only:**

| Type | Meaning | Created by |
|------|---------|-----------|
| `contradicts` | This note's claim conflicts with the target's; both are preserved as competing views; do not merge | Integration LLM, when it detects genuine conflict |
| `supersedes` | This note replaces the target after revision; target gets `type: refuted` | Integration LLM, on UPDATE that reverses a prior claim |
| `splits-from` / `merges-into` | Provenance link recording corpus restructuring | Curation agent, when SPLIT or MERGE executes |

Everything else — `supports`, `extends`, `refines`, `related-to`, `see-also`, `exemplifies` — is topical proximity and is the embedding's job. Not implemented.

**On tags:** the same argument applies. Tags are a human browsing aid; they allow filtering by topic in a UI. The system retrieves by embedding + BM25 + activation, none of which uses tags. LLM-generated tags are noisy category labels (`[cognitive-science, learning, memory, educational-psychology]`) that add maintenance burden and zero retrieval signal. The `tags:` field is dropped from system-generated notes. Existing corpus notes may retain tags for human navigation; the integration pipeline does not populate or evolve them.

**What this closes:** H3 is resolved. The link vocabulary question was: does the model need explicit `rel:` types to reason well? Answer: for topical reasoning, no — it reads the bodies. For epistemic reasoning (contradiction, revision), explicit typed links are necessary because similarity-based retrieval will actively mislead (it surfaces contradicting notes as UPDATE targets). The vocabulary is minimal not because we are being lazy but because only three relationships carry information that the retrieval signals cannot.

---

## Spike 4D — LLM Ground Truth for Retrieval Evaluation

*(Repurposed from one-shot benchmark. The one-shot benchmark is lower priority pending cluster retrieval being resolved; the one LLM call saved is minor compared to the importance of getting the cluster right.)*

**What this tests:** generates a proper retrieval ground truth by asking the integration LLM directly which existing notes it would act on for each incoming query note, then evaluates body embedding against that ground truth.

### Outcome (completed 2026-03-15)

20 query notes × full 299-note corpus presented to Claude Sonnet per query (condensed as id + context sentence). Integration LLM identified 4.7 gold notes per query on average (2–6 interactions). Full results in `spikes/spike4d-llm-ground-truth/results.md`. Diagnostic in `spikes/spike4d-llm-ground-truth/analyse.py`.

**Body embedding against LLM ground truth: R@5=0.404, R@10=0.512, MRR=0.790.** Significantly better than the Wikipedia link ground truth (R@5=0.274) — confirming that citation-style links are a poor proxy for integration relevance.

**Gold set diagnostic:**

| Metric | Value |
|--------|-------|
| Gold notes in top-10 by embedding | 49% |
| Gold notes in top-20 by embedding | 63% |
| Gold notes in top-30 by embedding | 68% |
| Gold notes with any link signal (missed by embedding) | 17% |
| Gold notes with no link or tag signal | 83% |
| Gold set internal link cohesion | 26% |

**Key finding:** 83% of the notes that the integration LLM would act on but that body embedding misses have no link or tag signal. The missed connections are inferential and cross-domain — the Zeigarnik effect connecting to Gestalt psychology, Reading connecting to Vision Span — not recoverable from structural signals in the corpus as-built. They would be recoverable from integration event history (H-new-A).

**Spot check on 5/5-miss cases:**
- *Zeigarnik effect*: gold notes span Gestalt psychology, Absent-mindedness, Problem solving — connections through intellectual lineage and contrast logic, not shared vocabulary.
- *Reading (general)*: broad topic where LLM reaches across domains; some gold notes (e.g. Lifelong learning) represent genuinely weak inferential connections that a stricter integration LLM might call NOTHING.

**Design decisions confirmed:**
- Top-20 cluster window adopted as default
- Citation-style link traversal eliminated from Phase 2 Gather
- Body embedding is the ceiling for single-pass retrieval; breaking through 63% requires either a wider window (diminishing returns past top-20) or accumulated activation history (Spike 5)
