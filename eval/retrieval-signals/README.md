# Model Test: Retrieval Signal Weights

## The decision

Five-signal weighted fusion for the Gather phase, with weights:

```
body_query:       0.450   (dense embedding, asymmetric query/document)
bm25_mugi_stem:   0.270   (BM25 + MuGI pseudo-note expansion + Porter stemming)
activation:       0.180   (pairwise co-activation graph, transitive expansion)
step_back:        0.050   (LLM step-back abstraction)
hyde_multi:       0.050   (LLM hypothetical peer-note generation, avg of 3)
```

**Why these weights:** Tuned on 80% of 299 LLM-judged retrieval events (held-out 20% for validation), using grid search over ±0.05 delta steps. The weights are specific to the current model family and corpus characteristics.

**What's model-sensitive:**
- `activation` weights depend on which integration decisions the LLM made during corpus construction; a different model makes different decisions → different co-activation graph
- `step_back` and `hyde_multi` use LLM calls (temperature=0.3); quality varies by model
- `body_query` uses the Voyage embedding API — the embedding model matters independently

## Baseline

*Run: 2026-03-15 | LLM: claude-sonnet-4-6, claude-haiku-4-5 | Embed: voyage-3*

| Metric | Value |
|--------|-------|
| R@3 | 0.395 |
| R@5 | 0.524 |
| R@10 | **0.667** |
| MRR | **0.844** |
| Union coverage @20 | 93.7% |

Test set: held-out 60 events (20% of 299), fixed seed.

Per-signal baselines:

| Signal | R@10 | MRR |
|--------|------|-----|
| body_query | 0.547 | 0.771 |
| bm25_mugi_stem | 0.496 | 0.689 |
| activation | 0.503 | 0.651 |
| step_back | 0.330 | 0.496 |
| hyde_multi | 0.489 | 0.744 |

## Re-run

```bash
# From repo root — all signals, uses cached LLM outputs where available
PYTHONUNBUFFERED=1 uv run --env-file .env python eval/retrieval-signals/main.py

# Skip API calls (cached results only):
PYTHONUNBUFFERED=1 uv run --env-file .env python eval/retrieval-signals/main.py --no-api

# Re-tune weights and run activation variant comparison (Phase 3):
PYTHONUNBUFFERED=1 uv run --env-file .env python eval/retrieval-signals/tune_weights.py
```

Data lives in `data/` (corpus notes, embeddings_cache.json, ground_truth_cache.json).
LLM call results are cached in `caches/` — delete a cache file to force regeneration.

## Interpret results

| Outcome | Action |
|---------|--------|
| R@10 improves with new weights | Update weights in `src/zettelkasten/gather.py` and design docs |
| A signal drops below 0.050 weight in re-tuning | Consider removing that signal (reduce LLM calls) |
| `body_query` alone reaches R@10 ≥ 0.700 | Consider simplifying to 2-signal blend (body + activation) |
| Union coverage drops below 85% | Investigate whether a new signal type is needed |

---

## Activation architecture: the full investigation

This section exists because the activation signal is easy to misread and the design decisions are non-obvious. Read before changing the activation implementation.

### What the benchmark number actually measures

The R@10=0.667 headline figure is **not** a measurement of what the production activation implementation delivers. It is what activation *could* contribute if past integration events had been recorded perfectly — the theoretical ceiling.

The workbench is offline evaluation. It cannot replay the actual co-activation history of a live store. For each held-out event it substitutes the spike4d ground-truth gold notes (LLM-judged "correct" interactions) as the activation source. This answers: *if activation recorded the right notes every time, how much would it help?* — not: *how well does store.py's current recording logic work?*

The other four signals (body_query, bm25, step_back, hyde_multi) are **real** measurements: the workbench runs exactly the same algorithm production uses, so those numbers transfer directly. Activation is the exception.

### Pairwise graph vs scalar

The activation signal uses a **pairwise co-occurrence graph**, not a scalar per note. This distinction matters.

**Scalar model:** each note has a single `activation_strength` value. When note X is activated, X's scalar is bumped. At query time, all notes return their scalar — Q-independent. This is essentially a note-popularity signal.

**Pairwise graph:** edge weights are stored per *(note_a, note_b)* pair. When note X is integrated alongside notes A and B, edges (X,A) and (X,B) are recorded. At query time for Q, only notes with a direct edge to Q score — the signal is Q-specific.

**Transitive expansion:** when an event activates notes [A, B, C] alongside query Q, transitive expansion also adds edges (A,B), (A,C), (B,C). This creates indirect paths: notes that have been co-retrieved with Q in *other notes' events* (not just Q's own events) can score when Q is the query.

### Recording strategy

At integration time, *what* gets recorded as the activation source determines quality. Three realistic options were tested alongside the gold ceiling:

- **k20:** activate all 20 notes that Gather retrieved, regardless of LLM judgment — broad, noisy
- **B (prescriptive):** ask the LLM which notes to activate, with explicit UPDATE/SYNTHESISE operation guidance
- **C (permissive):** ask the LLM which notes to activate using open-ended INTERACT framing, no operation guidance

### Full results grid

*Run: 2026-03-17 | Phase 3 of tune_weights.py | held-out n=60*

| Recording | Pairwise | Scalar |
|-----------|----------|--------|
| Gold (ceiling) | **0.666** (transitive) / 0.630 (no transitive) | 0.607 |
| k20 | 0.603 | 0.590 |
| B prompt | 0.617 | 0.590 |
| C prompt | 0.620 | 0.590 |

### What the grid tells us

**Keep pairwise over scalar.** Scalar gold (0.607) is lower than every pairwise variant except k20. Q-specificity — knowing *which query* triggered activation — is genuinely valuable. The scalar k20/B/C results all collapse to 0.590: in the scalar model, recording strategy is irrelevant because Q-specificity is lost regardless.

**Keep transitive expansion.** Pairwise gold with vs without transitive: 0.666 vs 0.630, a real 3.6pp gain. Transitive creates activation paths into Q from events where Q appeared as a *target* alongside other notes — without it, notes only score if Q was the source of a past event.

**Use permissive C prompt for recording.** Pairwise C (0.620) vs B (0.617) — the difference is within noise on a 60-event test set, so this is a design preference not a data-driven finding. C is preferred because simpler prompts with less operation guidance give the LLM more latitude and are more robust to future operation changes.

**The remaining gap is the recording quality gap.** Pairwise C (0.620) vs pairwise gold (0.666) — 4.6pp. This is irreducible with Haiku; it reflects the difference between a well-prompted production LLM and human-judged ground truth.

### Conclusion for implementation

Pairwise graph + transitive expansion + C-style permissive INTERACT prompt at recording time. The production `co_activations` recording in `store.py` should be revised to use consistent C-prompt nominations across all operation types (currently asymmetric: UPDATE records k20, CREATE/SYNTHESISE records target_note_ids).

## Note on ground truth

The ground truth (299 events) was generated by claude-sonnet-4-6 deciding which existing notes to integrate each draft into. If you switch the integration model, rebuild ground truth via spike4d before re-running the workbench — otherwise you are measuring retrieval against a different model's decisions.
