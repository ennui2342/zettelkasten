# Spike 5 — Activation-Weighted Cluster Identification

**Hypothesis cluster:** H-new-A (activation-weighted co-retrieval links improve recall); H-new-B (non-acted-on co-retrieved notes add marginal signal).

---

## The Retrieval Problem

Body embedding at top-20 achieves 63% recall on LLM-judged ground truth. 83% of missed notes have no link or tag signal — the connections are inferential and cross-domain, only recoverable from integration event history. Embedding similarity is a ceiling; breaking through it requires a signal that learns from actual usage.

---

## Proposed Mechanism

After each integration event, record which notes co-activated in the gather window. Accumulate activation strength between note pairs with exponential decay:

```
activation(A, B) = Σ_events  weight(event) · exp(-λ · age_in_days)

weight = 1.0  if both A and B received non-NOTHING operations in the event
weight = ?    if A received non-NOTHING, B was co-retrieved but got NOTHING  ← H-new-B
```

Future cluster scoring blends body similarity with activation strength:

```
score(query, candidate) = α · body_sim + (1-α) · activation(query, candidate)
```

α and λ are tunable; initial values α=0.3 (body dominates), λ=0.05 (half-life ~14 days).

**What to spike:**

1. **Simulate event history** — using the Spike 4D ground truth (20 query notes × 4.7 gold interactions each), treat those as "previous integration events" and compute the activation-weighted link graph. This gives us a small but real signal to evaluate.

2. **Re-run retrieval evaluation** — for the same 20 query notes, score all 300 corpus notes by `α·body_sim + (1-α)·activation_strength`. Measure R@10 and MRR against the same LLM ground truth.

3. **H-new-B ablation** — compare: (a) activation weight from non-NOTHING operations only vs. (b) with fractional weight for co-retrieved-but-NOTHING notes. Does the fractional weight help or hurt?

4. **Network diagnostics** — as the activation graph builds from Spike 4D events, measure: mean node degree, clustering coefficient, path length. Does the small-world signature emerge even from 20 × 5 events?

**The bootstrapping problem:** a real deployment has no integration history on day one. Three mitigations:
- For existing notes (bootstrapped KB), run a batch integration pass to seed the activation graph.
- Accept lower recall in early operation; the graph fills in as the KB is used.
- Pre-seed activation from the gather phase alone (weaker signal) rather than waiting for integration decisions.

**Theoretical connections:**
- ACT-R base-level activation (Anderson et al.): `A_i = ln(Σ t_j^(-d))` — the sum over all past activation times with power-law decay. Our exponential decay is an approximation; power-law may be a better long-term fit.
- Temporal Context Model (Howard & Kahana, 2002): co-activated items share a temporal context vector; reinstating one reinstates the context for others.
- Small-world network properties (Watts & Strogatz, 1998): expected to emerge from preferential co-activation of semantically clustered notes, with occasional long-range links from cross-domain integrations.

**Go criteria:** `α·body_sim + (1-α)·activation` achieves R@10 ≥ 0.65 on the Spike 4D ground truth (vs 0.512 for body-sim alone). If go: activation-weighted links are incorporated into Phase 2 Gather in the build; the decay rate λ and blend factor α are tunable parameters.

---

## Outcome (completed 2026-03-15) — Partial go: mechanism confirmed, ceiling at 0.64

Two runs. The first used 20 Spike 4D events (data-starved: only 89/300 nodes covered, blending hurt). The second expanded Spike 4D to all 300 corpus notes ($11 in LLM calls), giving 299 training events per LOO fold and full node coverage. The second run is definitive. Full results in `spikes/spike5-activation-links/results.md`.

### Initial 20-event run (data-starved — superseded)

| Strategy | R@5 | R@10 | MRR |
|----------|-----|------|-----|
| Body sim (baseline) | 0.404 | 0.512 | 0.790 |
| Body + activation (α=0.3, W_null=0.0) | 0.297 | 0.482 | 0.637 |

Blending hurt because 19 training events covered only 89/300 nodes; activation score was zero for most candidates, attenuating body sim rather than augmenting it. Network structure (CC=0.877) was forming but sparse.

### Full 300-event run — definitive results

**H-new-B eliminated.** W_null=0.3 (co-retrieved-but-NOTHING notes) was consistently worse. Activation restricted to confirmed non-NOTHING interactions only.

**Baselines (N=299 events):**

| Strategy | R@3 | R@5 | R@10 | MRR |
|----------|-----|-----|------|-----|
| Body embedding | 0.298 | 0.403 | 0.534 | 0.767 |
| Summary embedding (Haiku, Voyage) | 0.300 | 0.388 | 0.530 | 0.759 |

Summary embeddings generated for all 300 notes add no retrieval signal over body. The raw body already contains the signal; Haiku compression loses it.

**Alpha sweep — Body + Activation:**

| α | R@3 | R@5 | R@10 | MRR |
|---|-----|-----|------|-----|
| 0.1 | 0.374 | 0.492 | 0.630 | 0.835 |
| **0.2** | **0.380** | **0.504** | **0.640** | **0.827** ★ |
| 0.3 | 0.370 | 0.495 | 0.638 | 0.809 |
| 0.4–0.8 | declining | | | |

**Alpha sweep — Summary + Activation:**

| α | R@3 | R@5 | R@10 | MRR |
|---|-----|-----|------|-----|
| 0.1 | 0.373 | 0.495 | 0.618 | 0.824 |
| **0.2** | **0.375** | **0.507** | **0.645** | **0.822** ★ |
| 0.3 | 0.369 | 0.495 | 0.643 | 0.812 |

Summary + activation (0.645) and body + activation (0.640) are statistically indistinguishable. Summary adds complexity for no gain; body remains the right choice.

**Top-k activation (α=0.3):** negligible differences across k=5, 10, 20, 50. Sparse graph topology is fine — no pruning needed.

**Network diagnostics (full 299-event graph):**
- 299 nodes, 2496 edges, mean degree=16.7, CC=0.541
- Small-world structure confirmed: CC=0.541 far above random graph equivalent (~0.056)

**H-new-A: confirmed at R@10=0.640.** The mechanism works. Best blend (α=0.2) is 10.6pp above body baseline. Does not reach the 0.65 go threshold but is close; see ceiling analysis below.

**Build plan impact:**
- Phase 3 write path: record co-activation pairs (non-NOTHING only) after each integration event. Simple append to SQLite `co_activations(source_id, target_id, event_ts)` table.
- Phase 2 Gather: after initial top-20 by body embedding, re-rank with activation signal if table is populated. Falls back gracefully to pure body scoring on cold start.
- Optimal α=0.2 (body dominates); no activation blending until ≥100 events accumulated.

---

## Extended Observations

### On the decay factor

All spike events were simulated at `age_days=0`. The exponential decay term `exp(-λ·t)` evaluates to 1.0 for every event regardless of λ, so the decay parameter was not exercised. It cannot be tuned or validated from synthetic data.

In a live deployment with a growing event history, decay controls the balance between recent co-activation (sharp, context-specific) and older co-activation (broad, stable background). Two plausible outcomes:

- **Optimistic:** decay sharpens the activation signal by fading old cross-topic co-activations, reducing noise when the user's focus has shifted. R@10 could improve above 0.64 once the graph has temporal structure.
- **Pessimistic:** the memory store covers stable long-term knowledge (not ephemeral sessions), so old co-activations are signal not noise. Decay gradually thins the graph toward the cold-start regime, eroding the activation benefit over time.

The right decay rate depends on how quickly the user's active topic cluster changes. This cannot be determined from a static corpus; it requires longitudinal observation of real usage patterns. **λ should be treated as a tunable parameter at deployment time, not fixed in the build.**

### On eventual consistency and the cost of a miss

R@10=0.64 means ~1.7 gold notes per query are not retrieved in any given pass. The consequence depends on the nature of those misses.

In a continuously operating memory store, a missed UPDATE or SYNTHESISE on pass N is not permanent. If the knowledge area remains active, the missed note will likely surface in a subsequent pass when a different but related query arrives. The store exhibits eventual consistency: notes that should be related eventually get linked, just not necessarily on first contact.

This framing shifts the question from "does retrieval catch everything on first pass?" to "does the graph converge to the right state over time?" That is a longitudinal question that cannot be answered with a static spike — it requires months of real operation and a comparison of note quality before and after an extended consolidation period.

The high MRR (0.83) is the more operationally significant number: the single most important interaction target is almost always at the top of the retrieved cluster. What the 0.64 ceiling misses are the secondary and tertiary interactions.

### The systemic cross-domain miss

The 36% of gold notes not reached by any current signal (body embedding + activation) are not randomly distributed. The spike4d diagnostic established that 83% of missed notes have no link or tag signal, and the spot-check cases reveal a consistent pattern: the missed connections are inferential and cross-domain. The Zeigarnik effect connecting to Gestalt psychology. Reading connecting to Vision Span. These are conceptually related through intellectual lineage, contrast logic, or shared mechanism — but not through shared vocabulary or co-occurrence history.

This is a structural ceiling, not a tuning problem. Activation links help when notes have been co-activated before; they cannot help for first-contact cross-domain connections that no prior integration event has bridged. The 36% is approximately the fraction of the gold set that is genuinely novel — connections that the system cannot predict from its history.

**Update — Spike 6 / retrieval workbench (2026-03-15):** Adding four additional signals (BM25+MuGI, BM25 keyword, step_back, HyDE) reduced the truly unreachable floor from **36% → 7%** at K=20. The union coverage across all six signals is 93% of gold notes. The remaining 7% (~96 notes) appear to be structurally isolated — no shared vocabulary, no co-activation history, and not reachable via abstract principle framing or hypothetical peer note generation. Characterising these notes is the next diagnostic task (see retrieval workbench).
