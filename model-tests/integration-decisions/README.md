# Model Test: Integration Decision Quality

*Moved from `spikes/spike3-integration/`. See original README below for spike context.*

## The decision

Two-step integration (classify then execute) is reliable enough to drive automated corpus writes without human review of each decision.

**What's model-sensitive:** Step 1 uses a fast/cheap model. If a weaker model misclassifies, or a stronger model resolves ambiguity differently, the prompt may need updating. Run this test when upgrading the classify model.

## Baseline

*Run: 2026-03-14 | Model: claude-opus-4-6*

**14 test cases × 3 runs (temperature 0, 0.3, 0.3): 14/14 correct, 100% consistent.** See `results.md` for full per-case breakdown.

## Re-run

```bash
docker compose run --rm dev python model-tests/integration-decisions/spike.py
```

## Interpret results

| Outcome | Action |
|---------|--------|
| 14/14 correct, all consistent | No change needed |
| Any case incorrect | Check test design is still fair; review step 1 prompt |
| Any case inconsistent across runs | Investigate temperature sensitivity; consider prompt tightening |
| UPDATE cases producing SYNTHESISE | Model over-extends the synthesis operation — clarify UPDATE/SYNTHESISE boundary in prompt |
| NOTHING cases producing UPDATE | Conservative prior weakening — review cluster construction |

---

## Original spike documentation

**What this spike tests:** whether the integration LLM reliably selects the correct structural operation (UPDATE, CREATE, SPLIT, MERGE, SYNTHESISE, NOTHING, STUB) when given a draft note and a cluster of related existing notes.

**Hypotheses under test:**
- **H5:** the integration LLM makes consistent and correct 7-way structural decisions, sufficient to drive automated writes.
- **H7:** the conservative prior (NOTHING) fires correctly — the system does not integrate when it should leave things alone.

**Scope:** integration decision only. No file writes, no link resolution, no gather phase. The test measures: does the model choose the right operation? Is the reasoning coherent? Is the choice consistent across runs?

---

## Test material

All content is in the memory science domain (same as Spike 2), allowing the prior notes from Spike 2 to be reused as part of the cluster for integration cases.

### notes/

Existing knowledge base notes used as cluster inputs:

| File | ID | Used in |
|------|-----|---------|
| `testing-effect.md` | z20260314-002 | UPDATE-1, SYNTHESISE-1 |
| `spaced-repetition.md` | z20260314-001 | UPDATE-2, STUB-1, SYNTHESISE-1 |
| `external-memory-systems.md` | z20260314-003 | UPDATE-3 |
| `encoding-and-memory-formation.md` | z20260314-004 | CREATE-1, SYNTHESISE-2 |
| `massed-practice.md` | z20260314-005 | NOTHING-1 |
| `forgetting-curve.md` | z20260314-006 | NOTHING-2 |
| `practice-strategies.md` | z20260314-007 | SPLIT-1 (conflates interleaving + spacing) |
| `memory-systems-overview.md` | z20260314-008 | SPLIT-2 (conflates working + long-term memory) |
| `retrieval-cues.md` | z20260314-009 | MERGE-1 |
| `context-dependent-memory.md` | z20260314-010 | MERGE-1 |
| `spaced-learning.md` | z20260314-011 | MERGE-2 |
| `distributed-practice.md` | z20260314-012 | MERGE-2 |
| `generation-effect.md` | z20260314-013 | SYNTHESISE-2 |

### drafts/

One draft per test case:

| File | Case | Expected operation |
|------|------|--------------------|
| `testing-effect-draft.md` | update-1 | UPDATE z20260314-002 |
| `spaced-repetition-draft.md` | update-2 | UPDATE z20260314-001 |
| `external-memory-draft.md` | update-3 | UPDATE z20260314-003 |
| `generation-effect-create-draft.md` | create-1 | CREATE |
| `massed-practice-nothing-draft.md` | nothing-1 | NOTHING |
| `forgetting-curve-nothing-draft.md` | nothing-2 | NOTHING |
| `sleep-consolidation-stub-draft.md` | stub-1 | STUB |
| `prospective-memory-stub-draft.md` | stub-2 | STUB |
| `interleaved-practice-split-draft.md` | split-1 | SPLIT z20260314-007 |
| `working-memory-split-draft.md` | split-2 | SPLIT z20260314-008 |
| `encoding-retrieval-match-merge-draft.md` | merge-1 | MERGE z20260314-009 + z20260314-010 |
| `distributed-spacing-merge-draft.md` | merge-2 | MERGE z20260314-011 + z20260314-012 |
| `spaced-retrieval-synthesise-draft.md` | synthesise-1 | SYNTHESISE z20260314-002 + z20260314-001 |
| `generation-encoding-synthesise-draft.md` | synthesise-2 | SYNTHESISE z20260314-004 + z20260314-013 |

---

## Test case design rationale

### UPDATE (×3)
Each existing note has a documented gap. Each draft fills exactly that gap without covering new enough territory to warrant CREATE.
- **update-1:** testing-effect note documents gap "techniques other than direct testing." Draft adds elaborative interrogation as equivalent mechanism via same consolidation pathway.
- **update-2:** spaced-repetition note has open question about whether spacing interval alone explains the benefit. Draft resolves this: retrieval difficulty is itself a mechanism.
- **update-3:** external-memory note has open question about what properties produce genuine encoding. Draft specifies: active engagement + retrieval friction.

### CREATE (×1)
- **create-1:** generation effect is a distinct topic; only distantly related encoding note in cluster. No existing note mentions generation as a phenomenon.

### NOTHING (×2)
The existing cluster notes are rich and pre-emptive; the draft is a shorter restatement of the same content. No new mechanism, finding, or framing.
- **nothing-1:** massed-practice note covers mechanism, empirical finding, fluency illusion, and metacognitive failure. Draft repeats these at lower depth.
- **nothing-2:** forgetting-curve note covers Ebbinghaus, exponential decay, savings effect, and timing implications. Draft covers the same ground.

### STUB (×2)
Draft covers a real topic with no or minimal cluster. The system should not CREATE (too little to establish a full note) but should STUB (acknowledge the topic for future development).
- **stub-1:** sleep consolidation — genuine memory science topic, but the cluster only has the spaced-repetition note as a distant neighbour.
- **stub-2:** prospective memory — distinct topic with empty cluster.

### SPLIT (×2)
Existing note visibly conflates two distinct topics. Incoming draft is squarely about one of them, making the conflation legible.
- **split-1:** practice-strategies note mixes spacing (when to practice) and interleaving (what order to practice) under "strategic practice." Draft is specifically about interleaving and the within-session ordering mechanism.
- **split-2:** memory-systems-overview conflates working memory and long-term memory under "memory." Draft is specifically about working memory — its capacity limits, decay, chunking, and cognitive load implications.

### MERGE (×2)
Two notes cover the same concept with different terminology or framing. Draft makes the identity explicit.
- **merge-1:** retrieval-cues (retrieval-side view) and context-dependent-memory (encoding-side view) both describe encoding specificity. Draft explicitly states this and shows the symmetry.
- **merge-2:** spaced-learning (cognitive psychology framing) and distributed-practice (educational psychology framing) describe the same spacing effect. Draft explicitly states they are the same phenomenon.

### SYNTHESISE (×2)
Two well-formed, separate notes lack an explicit connection. Draft articulates a bridging principle that neither note captures.
- **synthesise-1:** testing-effect and spaced-repetition — both are individually established. Draft shows their interaction is multiplicative (spaced retrieval practice), not just additive, because they share a mechanism (effortful reconstruction).
- **synthesise-2:** encoding-and-memory-formation and generation-effect — both are individually established. Draft shows that the generation effect IS the mechanism that produces deep encoding, making these two notes complementary halves of one account.

---

## Run

```
docker compose run --rm dev python spikes/spike3-integration/spike.py
```

Each test case runs 3 times (temperature 0, 0.3, 0.3). Results written to `results.md`.

---

## Evaluation

For each case, check:
1. **Operation correct?** Does the majority decision match the expected operation?
2. **Reasoning coherent?** Does the reasoning identify the right feature of the case (the gap, the conflation, the redundancy, the bridge)?
3. **Consistent?** Do all 3 runs agree? Inconsistency on a case is a signal the case is ambiguous or the prompt is insufficiently discriminating.
4. **UPDATE synthesised?** For UPDATE cases, does the model produce a synthesised note (not an appended one)?

---

## Go criteria

- ≥ 75% of cases (11/14) match expected operation on majority vote
- All 3 UPDATE cases select UPDATE and describe synthesis (not append)
- NOTHING fires correctly in both NOTHING cases (not under-triggered)
- Consistency ≥ 2/3 runs for each case

## No-go

Fewer than 10/14 correct after prompt iteration. Genuine no-go: the 7-way decision is too ambiguous to be reliable with a single prompt and must be decomposed into a decision tree.
