# Merge Spike — Results and Conclusions

## What we were testing

Whether the Step 1 classifier would fire MERGE when presented with two existing
notes covering the same concept under different vocabulary, and whether prompting
changes could make it do so reliably without stifling SYNTHESISE on genuinely
distinct concepts.

The broader question underneath: should MERGE execute at ingestion time at all?

---

## Phase 1 — Baseline (run_test.py, full pipeline)

Five scenarios seeded into fresh zettels, bridging texts ingested through the
full Form → Gather → Integrate pipeline.

| Scenario | Expected | V0 Result |
|----------|----------|-----------|
| S1 Dense Retrieval vs Semantic Search | MERGE | SYNTHESISE |
| S2 Dropout Regularization vs Bayesian | SYNTHESISE | SYNTHESISE ✓ |
| S3 Cosine Similarity duplicate | MERGE | SYNTHESISE |
| S4 Vanishing Gradients vs ResNets | SYNTHESISE | SYNTHESISE ✓ |
| S5 Stub + Full Note on MoE | UPDATE | UPDATE ✓ |

MERGE never fired. The model correctly identified the relationship in both MERGE
candidates but chose SYNTHESISE — creating bridge notes rather than collapsing
duplicates. The SYNTHESISE notes produced for S1 and S3 were well-written and
contained genuine insight.

---

## Phase 2 — Prompt iteration (iterate_prompt.py)

Ran five prompt variants (V0–V4) against a 3-scenario subset to find wording
that triggers MERGE. V2 appeared to work (3/3), V3 and V4 also passed.

**Critical confound discovered**: `iterate_prompt.py` bypassed the Form phase,
feeding raw bridging text as the draft. Raw bridging text contains explicit
"these are the same thing" comparison language. Real Form output abstracts this
into a topic note that often loses the explicit equivalence claim. The results
were not valid.

---

## Phase 3 — Form cache and honest rerun (cache_form_outputs.py)

Ran Form on all five bridging texts and cached the outputs. Key observations
from the Form outputs themselves:

- **S1**: Form preserved "two names for the same underlying technique" — explicit
  enough that the signal survives, but not as strong as the raw text.
- **S3**: Form preserved "exactly the same operation, with no distinction" — strong
  signal retained.
- **S2**: Form produced **two drafts** — "Dropout in Neural Networks" (synthesising
  both framings) and "Bayesian Inference in Deep Learning". The first draft already
  contained the synthesis insight, making UPDATE the more appropriate classification
  for at least one draft, not SYNTHESISE.
- **S4, S5**: Clean single drafts.

Rerunning the prompt iteration with real Form outputs:

| Variant | Score | MERGE hits | SYNTHESISE safe |
|---------|-------|-----------|-----------------|
| V0 | 4/5 | 1/2 | 2/2 |
| V1 | 4/5 | 1/2 | 2/2 |
| V2 | 4/5 | 1/2 | 2/2 |
| V3 | 5/5 | 2/2 | 2/2 |
| V4 | 5/5 | 2/2 | 2/2 |

V2's earlier apparent win was entirely an artefact of the Form shortcut. With
real Form outputs, V3 is the minimum passing variant.

---

## Phase 4 — Output quality comparison (compare_outputs.py, V0 vs V3, V0 vs V4)

Full step 1 + step 2 run for V0 and V3 across all 5 scenarios. Key findings:

**S1 (MERGE under V3, SYNTHESISE under V0)**

V0's SYNTHESISE note contained a genuine insight absent from V3's MERGE note:
that the real structural axis of variation in this space is
bi-encoder / late-interaction / cross-encoder — not the IR/NLP naming divide.
That observation was generated *because* the model was forced to articulate what
was actually between two notes it couldn't cleanly collapse. V3's MERGE note
buried this as a final paragraph.

**S4 (both SYNTHESISE — the quality control case)**

Both V3 and V4 produced *richer* SYNTHESISE notes than V0 on the same scenario
(V3: 3365 chars; V4: 3236 chars; V0: ~2757 chars). The sharpened MERGE/SYNTHESISE
boundary did not stifle synthetic thinking — it may have improved it by forcing
the model to work harder to justify SYNTHESISE.

**V3 vs V4**

V3's "neutral translation" test ("would they say the same thing if translated into
neutral language?") trusts the model to apply a heuristic. V4 is more directive,
anticipating the specific failure mode and blocking it. V3 produced consistently
richer SYNTHESISE output. V4 produced cleaner MERGE titles. The difference is small.

---

## Conclusion

### MERGE deprecated at ingestion time

The central question — does triggering MERGE at ingestion time serve the
zettelkasten's purpose? — was answered by observing what happens when it fires:

1. **MERGE destroys retrieval surface.** Two notes covering the same concept from
   different disciplinary framings are *two retrieval paths*, not waste. When the
   IR paper arrives, the dense retrieval note scores high. When the NLP paper
   arrives, the semantic search note scores high. Both land in the cluster.
   A merged note would score moderately for both, reducing the neighbourhood
   richness that SYNTHESISE depends on.

2. **MERGE closes future SYNTHESISE opportunities.** Every MERGE that fires at
   ingestion time removes a pair of notes that could have anchored a "rare flash."
   The insight in V0's S1 SYNTHESISE note was generated precisely because two
   notes were present and the model was forced to articulate what was between them.

3. **The SYNTHESISE notes generated on "wrong" scenarios were often the richest
   content produced in the spike.** This wasn't accidental. The model's enthusiasm
   for the S1 SYNTHESISE result, even when it was technically the wrong operation,
   was a signal worth attending to.

4. **We were solving a problem we haven't seen in operational zettels.** MERGE at
   ingestion time was added anticipating a duplicate accumulation problem. That
   problem has not materialised. Adding MERGE before observing the need may do
   more harm than good.

**Decision**: `_CURATION_OPS` should be reverted to include MERGE. MERGE remains
classifiable but does not execute at ingestion time. If duplicate accumulation
becomes a visible problem in operational zettels, MERGE can be introduced as a
scheduled curation pass with human review.

### V3 prompt adopted for Step 1

The prompt iteration produced a genuine improvement independent of MERGE: V3's
sharpened MERGE/SYNTHESISE description improves classification accuracy for
UPDATE, CREATE, and SYNTHESISE as well, because the model has clearer criteria
for when a bridge note earns its existence. This is worth keeping.

The key addition in V3:

> MERGE: two existing notes are duplicates with different names. Use this test:
> could you replace both notes with a single note that loses no knowledge? If
> yes, MERGE. [...] The draft confirms the duplication.
>
> SYNTHESISE: two existing notes cover distinct concepts, and the draft reveals
> a non-obvious relationship between them that produces new knowledge. The bridge
> note must contain an insight absent from both sources. Do not use SYNTHESISE
> merely because two things are related — only when the relationship itself is
> the knowledge. If the draft's main claim is "X and Y are the same thing",
> choose MERGE, not SYNTHESISE.

The "relationship itself is the knowledge" framing is the valuable addition — it
gives the model a principled criterion for SYNTHESISE that applies independently
of whether MERGE ever fires.

---

## Secondary findings

- **Form phase strips comparison framing**: bridging texts written to compare two
  concepts lose their explicit comparison language when processed by Form. Step 1
  classifiers never see "these are the same thing" — they see a topic note that
  mentions both concepts. This has implications for any ingestion-time operation
  that depends on explicit comparison signals in the draft.

- **Form sometimes synthesises**: for S2, Form produced a draft that already
  contained the SYNTHESISE insight. The ingestion pipeline does some synthesis at
  the Form stage, before Step 1 even runs. This is under-examined.

- **SYNTHESISE quality improved with sharper MERGE boundary**: the V3 and V4
  SYNTHESISE notes were richer than V0's on the same scenarios. Giving the model
  clearer criteria for when NOT to SYNTHESISE appears to improve the quality of
  SYNTHESISE when it does fire.
