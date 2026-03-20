# Merge Behaviour Spike

**Conclusion: MERGE deprecated at ingestion time. See [results.md](results.md).**

---

## Purpose

This spike investigated whether the Step 1 classifier would fire MERGE when
presented with two existing notes covering the same concept under different
vocabulary, and whether the pipeline's MERGE operation should execute at ingestion
time at all.

Starting observation: MERGE had never fired in real ingestion runs. The initial
assumption was that the Step 1 prompt needed improving. The actual conclusion was
more fundamental.

---

## What's in this directory

| File | Purpose |
|------|---------|
| `run_test.py` | Full pipeline test — 5 scenarios, seeds a zettel and ingests bridging text |
| `cache_form_outputs.py` | Runs Form on each scenario's bridging text and caches to `form_cache/` |
| `iterate_prompt.py` | Step 1 prompt iteration — 5 scenarios, uses cached Form output, tests V0–V4 |
| `compare_outputs.py` | Full step 1 + step 2 quality comparison between two prompt variants |
| `form_cache/` | Cached Form outputs for each scenario (run `cache_form_outputs.py` to populate) |
| `comparison/` | Generated note content from `compare_outputs.py` runs |
| `work/` | Temporary zettels created by `run_test.py` |
| `results.md` | Full findings and conclusions |

---

## Scenarios

| Key | Name | Expected | Rationale |
|-----|------|----------|-----------|
| s1 | Dense Retrieval vs Semantic Search | MERGE | Same technique, different IR/NLP vocabulary |
| s3 | Cosine Similarity duplicate | MERGE | Literally the same formula described twice |
| s2 | Dropout Regularization vs Bayesian | SYNTHESISE | Same mechanism, genuinely different interpretations — anchor |
| s4 | Vanishing Gradients vs ResNets | SYNTHESISE | Problem and solution — related but distinct — anchor |
| s5 | Stub + Full Note on MoE | UPDATE | Stub should be updated and promoted — anchor |

---

## Methodology evolution

**Phase 1 — Full pipeline baseline** (`run_test.py`)

MERGE never fired across any scenario. The model produced SYNTHESISE for both
MERGE candidates, generating genuine insight in the process.

**Phase 2 — Prompt iteration** (`iterate_prompt.py`, initial version)

Attempted to fix MERGE trigger via prompt wording. V2 appeared to work (3/3 pass).
**Confound**: the script bypassed Form, feeding raw bridging text as the draft.
Raw bridging text contains explicit "these are the same thing" comparison language
that Form abstracts away. Results were invalid.

**Phase 3 — Form cache + honest rerun** (`cache_form_outputs.py` + updated `iterate_prompt.py`)

Cached actual Form outputs. Reran iteration with real drafts. V2's win collapsed
— only V3 and V4 passed with real Form outputs. V3 is the minimum passing variant.

**Phase 4 — Output quality comparison** (`compare_outputs.py`)

Compared generated note content between V0 and V3, V0 and V4. Key finding: V0's
SYNTHESISE note for S1 (the "wrong" operation) contained a genuine insight that
V3's MERGE note did not — because the model was forced to articulate what was
actually between two notes it couldn't cleanly collapse.

---

## Key findings

1. **MERGE destroys retrieval surface** — two notes covering the same concept from
   different framings provide two retrieval paths. A merged note provides one.
   Richer neighbourhoods produce better SYNTHESISE results.

2. **MERGE closes SYNTHESISE opportunities** — the V0 S1 SYNTHESISE note found
   an insight (the bi-encoder/late-interaction/cross-encoder axis as the real
   structural distinction) precisely because two notes were present. That note
   would not exist under V3.

3. **Form strips comparison framing** — bridging texts lose their explicit
   "these are the same thing" language when processed by Form. Step 1 never sees
   comparison prose; it sees topic notes.

4. **Form sometimes pre-synthesises** — S2's bridging text produced two drafts,
   the first of which already contained the synthesis insight. The pipeline does
   synthesis at Form stage, before Step 1 runs.

5. **Sharper MERGE boundary improves SYNTHESISE quality** — V3 and V4 produced
   richer SYNTHESISE notes than V0 on the same scenarios. Clearer "when not to
   SYNTHESISE" criteria appear to improve SYNTHESISE when it does fire.

---

## Decision

**MERGE deprecated at ingestion time.** `_CURATION_OPS` should be reverted to
include MERGE. If duplicate accumulation becomes a visible problem in operational
zettels, MERGE can be reintroduced as a scheduled curation pass with human review.

**V3 Step 1 prompt adopted.** The prompt improvement is valuable independently of
MERGE — it sharpens all classification decisions, particularly the SYNTHESISE
criterion ("the relationship itself is the knowledge").

---

## Running the spike

```bash
# Populate Form cache (required before iterate_prompt or compare_outputs)
uv run --env-file .env python spikes/merge-test/cache_form_outputs.py

# Run full pipeline test (all 5 scenarios)
uv run --env-file .env python spikes/merge-test/run_test.py

# Run prompt iteration (single variant)
uv run --env-file .env python spikes/merge-test/iterate_prompt.py --variant 3

# Compare two variants (full step 1 + step 2 output)
uv run --env-file .env python spikes/merge-test/compare_outputs.py --a 0 --b 3
```
