# Spike 6 — Retrieval Ceiling & Retrieval Workbench

---

## Spike 6 — Breaking Through the Inferential Tail (completed 2026-03-15)

**The question:** can any retrieval mechanism reach the 36% of gold notes with no body embedding, link, or tag signal? These are inferential cross-domain connections — the primary value-add of a knowledge synthesis system. If they are systematically unreachable, the ceiling is architectural.

The literature confirms this is a well-studied problem under several names: the *vocabulary mismatch problem*, the *semantic gap*, and the *cross-domain generalisation failure* of contrastively trained encoders. The key insight is that different mechanisms fail on orthogonal subsets — making complementary stacking the right strategy. Fine-tuning improves the same embedding mechanism on the same failure set; the mechanisms below add genuinely independent retrieval lanes.

The 36% miss decomposes into two separable failure modes:

1. **Vocabulary mismatch** — notes are inferentially related but use different terminology; embedding distance is high because surface forms are disjoint. Attack: BM25 + LLM query expansion.
2. **Principle-level inferential gap** — notes share an abstract principle that neither expresses explicitly. Attack: step-back prompting with abstract query retrieval.

**Outcome summary:** All four new signals (6A BM25+MuGI, 6B step-back, plus BM25 keyword and HyDE added in the workbench) were evaluated. The 36% structural ceiling has been broken — the union of all six signals covers **93% of gold notes at K=20**, leaving only 7% truly unreachable. The retrieval problem has shifted from *coverage* to *ranking*: the right notes are in the candidate pool, but not ranked high enough within each signal for fusion to reliably surface them in R@10.

---

### 6A — BM25 + MuGI (LLM multi-text query expansion) — completed

**Paper:** "Enhancing Information Retrieval through Multi-Text Generation Integration with Large Language Models" (Zhang et al., EMNLP 2024 Findings — arXiv 2401.06311)

**Mechanism:** Generate 3–5 pseudo-notes from the incoming note using an LLM. Concatenate their text to form an expanded BM25 query. Retrieve against all existing notes using this expanded query as a second retrieval lane alongside dense embedding. Merge the two candidate sets before truncating to top-20.

**Why this directly addresses vocabulary mismatch:** the pseudo-notes introduce terminology the original note lacks. An incoming note about the Zeigarnik effect generates expansions that introduce terms like "closure," "Gestalt," "incompleteness," "perceptual organisation" — terms BM25 can then exactly match against notes sharing no embedding-space proximity with the original.

**Evidence:** BM25+MuGI outperforms strong trained dense retrievers (ANCE, DPR) on BEIR out-of-domain benchmarks — +18% Recall@10 on TREC DL, +7.5% across BEIR. Complementarity ratio studies (ACL 2023) confirm sparse and dense retrievers fail on orthogonal document subsets. The independent signal claim is empirically validated.

**Why more robust than fine-tuning:** fine-tuning improves the dense embedding mechanism on the training distribution. BM25 is a completely different signal (lexical exact-match) that generalises across domains by design.

**Results (N=299 events):** R@10=0.462, MRR=0.693 standalone. Coverage@20=58.4%, with 169 notes (12.3%) uniquely found only by this signal. Confirmed independent lexical signal — adds notes that embedding cannot reach.

---

### 6B — Step-back prompting (abstract principle retrieval) — completed

**Paper:** "Take a Step Back: Evoking Reasoning via Abstraction in Large Language Models" (Zheng, Mishra et al., Google DeepMind — ICLR 2024 — arXiv 2310.06117)

**Mechanism:** Before retrieval, prompt the LLM: *"What broader principle or theme does this note exemplify?"* Embed the abstract answer and retrieve against it as a third candidate lane. Merge with the embedding and BM25+MuGI sets before truncation.

**Why this addresses principle-level inferential gaps:** cross-domain connections often exist at the level of shared abstract principles that neither note explicitly states. The Zeigarnik effect and Gestalt psychology share "incompleteness drives sustained cognitive engagement" — but no note says that. A step-back query framed at the principle level retrieves from the right region of embedding space even when the original note does not.

**Evidence:** +7% MMLU Physics, +11% MMLU Chemistry, +27% TimeQA, +7% MuSiQue (ICLR 2024). Gains concentrated on tasks requiring abstraction from specifics to general principles — exactly the inferential gap regime.

**Results (N=299 events):** R@10=0.330, MRR=0.496 standalone. Coverage@20=45.4%, with 18 notes (1.3%) uniquely found only by this signal. Weaker precision ranker than expected, but contributes coverage of notes unreachable by all other signals. Role: discovery, not precision.

---

### 6C — Fine-tuned embeddings (deferred)

The 300-event ground truth provides ~1,380 (query, positive-note) pairs with hard negatives from the top-20-retrieved-but-NOTHING set. Sufficient to fine-tune a bi-encoder (Voyage fine-tuning API) for integration relevance.

- Highest single-mechanism yield on the training distribution
- **Risk: overfits to the Wikipedia cognitive science corpus** — likely to degrade on a real KB covering different domains
- More robust if applied after 6A+6B: fine-tuning then addresses residual failures not covered by the independent lanes
- Deferred until the real KB accumulates integration event history; use that as training data rather than the spike corpus

---

### 6D — IRCoT: iterative retrieval with chain-of-thought (deferred)

**Paper:** "Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions" (Trivedi et al., ACL 2023 — arXiv 2212.10509)

Alternate between LLM reasoning steps and retrieval, using each intermediate reasoning sentence as the next retrieval query. If the first retrieved note is about Zeigarnik, the CoT step reasons "this relates to how Gestalt psychology describes incompleteness" — and that sentence becomes the next retrieval query. Up to +21pp on multi-hop retrieval benchmarks. Deferred: higher latency, iterative loop; best after 6A+6B are validated.

---

### Spike 6 priority order

| Spike | Mechanism | Failure mode addressed | Independent signal? | Cost | Status |
|-------|-----------|----------------------|---------------------|------|--------|
| **6A** | BM25 + MuGI | Vocabulary mismatch | Yes — lexical exact-match | Low | Done |
| **6B** | Step-back prompting | Principle-level inferential gap | Partial — different embedding region | Low | Done |
| **6E** | HyDE | Vocabulary mismatch + peer-note framing | Partial — generative embedding | Low | Done |
| 6C | Fine-tuned embeddings | Residual dense failures | No — same mechanism | Medium | Deferred |
| 6D | IRCoT | Multi-hop inferential chains | No — same retrieval, different queries | Medium | Deferred |

Original success criterion: R@10 ≥ 0.70. Actual best (6-signal equal blend): R@10=**0.663**. Coverage criterion exceeded: 93% at K=20 vs 64% body+activation baseline.

---

## §4d — Retrieval Workbench (completed 2026-03-15)

`spikes/retrieval-workbench/` — a pluggable LOO evaluation framework for testing new retrieval signals. Replaces the ad-hoc per-spike evaluation scripts. All prior spike caches are reused; new signals drop in as a single Python file implementing the `Signal` interface.

### Architecture

```
signals/
  _base.py         — Signal(name, needs_loo, setup(), scores())
  body.py          — cosine similarity against body_mat
  activation.py    — LOO co-activation graph (needs_loo=True)
  bm25_mugi.py     — BM25 + Haiku pseudo-note expansion
  bm25_keyword.py  — BM25 with TF-IDF top-25 keyword query
  step_back.py     — Haiku abstraction + Voyage embedding
  hyde.py          — Haiku hypothetical peer note + Voyage embedding
harness.py         — LOO evaluation: coverage diagnostic + per-signal metrics + fusion
main.py            — entry point; loads corpus, embeddings, ground truth; wires signals
caches/            — incremental LLM caches (pseudo_notes.json, step_back.json, hyde.json)
results/           — timestamped run-YYYY-MM-DD_HH-MM.md + latest.md
```

### Six-signal run results (N=299 events, top-20 cluster)

**Coverage diagnostic:**

| Signal | K=20 | K=50 | K=100 | K=200 | Unique@20 |
|--------|------|------|-------|-------|-----------|
| body | 68.1% | 83.7% | 93.4% | 99.3% | 2.6% (35) |
| bm25_mugi | 58.4% | 73.0% | 82.3% | 93.0% | 2.0% (28) |
| activation | 58.1% | 64.8% | 71.3% | 85.6% | **3.5% (48)** |
| hyde | 53.3% | 72.6% | 86.7% | 97.4% | 1.8% (24) |
| bm25_keyword | 48.2% | 64.0% | 77.3% | 90.7% | 1.1% (15) |
| step_back | 45.4% | 65.4% | 81.3% | 95.0% | 1.3% (18) |
| **All signals** | **93.0%** | **97.8%** | **99.7%** | **100.0%** | — |
| *Unreachable* | *7.0%* | *2.2%* | *0.3%* | *0.0%* | — |

**Per-signal retrieval:**

| Signal | R@3 | R@5 | R@10 | MRR |
|--------|-----|-----|------|-----|
| body | 0.298 | 0.403 | 0.533 | 0.767 |
| bm25_mugi | 0.258 | 0.343 | 0.462 | 0.693 |
| activation | 0.291 | 0.398 | 0.503 | 0.651 |
| hyde | 0.221 | 0.298 | 0.408 | 0.614 |
| bm25_keyword | 0.209 | 0.268 | 0.360 | 0.592 |
| step_back | 0.175 | 0.229 | 0.330 | 0.496 |

**Fusion:**

| Strategy | R@3 | R@5 | R@10 | MRR |
|----------|-----|-----|------|-----|
| Equal blend (all 6) | **0.383** | **0.515** | **0.663** | **0.851** |
| RRF (all 6) | 0.354 | 0.479 | 0.631 | 0.800 |

Best prior result (3-signal hand-tuned blend 0.6/0.2/0.2): R@10=0.685. Six-signal equal blend (0.663) is slightly below — the coverage expansion from step_back/HyDE introduces some noise at the top ranks that degrades precision marginally. Fusion weight tuning across 6 signals is the next optimisation step.

### Key observations

**Activation has the highest unique coverage** (48 notes, 3.5%) — more than any other signal. The co-activation graph reaches notes that are invisible to all embedding and lexical signals, confirming it as a structurally independent retrieval lane.

**step_back and HyDE are discovery signals, not precision signals.** They have the weakest per-signal R@10 but together contribute ~30 unique notes to the 93% union ceiling. Their weight in the fusion blend should be kept low (0.1–0.15) to preserve precision while retaining coverage benefit.

**Equal blend beats RRF** in this setting. RRF is rank-based and immune to score scale differences, but loses information when one signal has a gold note at rank 3 and another at rank 17. Weighted sum using min-max normalised scores retains the magnitude gradient.

**The retrieval problem has shifted from coverage to ranking.** The right notes are in the candidate pool 93% of the time at K=20. The R@10=0.663 gap below the 93% ceiling reflects ranking quality within each signal, not coverage failure. Further investment should target per-signal ranking improvement, not additional coverage signals.

### Characterising the 7% unreachable — findings (2026-03-15)

`spikes/retrieval-workbench/diagnose_unreachable.py` ran a per-pair analysis across all 299 events.

**The 7% is almost entirely contextual, not structural:**

- 100 unreachable (query, gold) pairs at K=20
- **65 pairs** involve notes that *are* reached in other events — they're borderline (rank 21–30 in some queries, inside K=20 in others). These will be addressed by activation weighting over time: the first co-activation event seeds the edge; every subsequent related query gets the pair boosted.
- **Only 4 unique notes** are truly unreachable in every event they appear in — zero links in/out, shortest bodies (avg 757 chars vs 1,282 for all gold), lowest embedding similarity (0.24–0.39), Jaccard vocabulary overlap median = 0.041.

The 4 permanently unreachable notes are broad encyclopedic Wikipedia articles (Metacognition, Lifelong Learning, Vision Span, Culturally Relevant Teaching) that connect to specific cognitive science notes only through inferential leaps the corpus doesn't encode. In a real knowledge base built from actual writing, notes will have richer interlinking and the graph won't have isolated nodes. This is an artefact of the synthetic corpus, not a property of the retrieval architecture.

**No 7th signal is warranted.** IRCoT-style multi-hop reasoning would likely reach these 4 notes, but the cost/benefit is poor for 4 notes out of 1,371 gold pairs. The 65 contextually missed pairs are the right target — activation weighting handles them.

**The stub risk.** These 4 notes share the structural profile of a freshly-created STUB: short body, no links, low embedding similarity. If stubs are retrievally invisible, they don't develop — the integration LLM misses them, writes NOTHING or creates a duplicate, and the stub becomes a permanent orphan. Two mitigations warranted at build time:

1. **Richer stub prompt.** When the integration LLM creates a STUB, prompt it to include: concept title, 1-2 sentence definition, and 3-5 synonyms/related terms. This directly addresses vocabulary mismatch and gives the embedding more surface area. Example output: *"Metacognition — thinking about thinking; includes self-regulation, executive function monitoring, working memory awareness, reflective practice."* This is a prompt engineering change with no architectural cost.

2. **Stub age monitoring.** Track how long each STUB note goes without receiving an UPDATE operation. Stubs that age beyond a threshold without development are candidates for review — either they should be enriched, merged, or flagged as orphans.

---

### Ranking improvements and weight tuning (completed 2026-03-15)

**Ranking improvement experiments:**

*Asymmetric embedding (`body_query`):* re-embeds query notes with Voyage `input_type='query'` at evaluation time (corpus remains `input_type='document'`). Result: R@10 0.533→0.547 (+1.4pp). Modest — Wikipedia articles are document-like, not short queries; gain will be larger for real integration queries.

*MuGI N=5:* more pseudo-notes adds vocabulary noise, not signal. N=3 stays (N=5 regresses: 0.462→0.446).

*MuGI + Porter stemming (`bm25_mugi_stem`):* stemming reduces surface-form variation so learning/learns/learned all match the same stem, increasing vocabulary overlap between query and corpus. Result: R@10 0.462→0.496 (+3.4pp), coverage@20 58.4%→61.9%. Significant gain at zero API cost. **Replaces `bm25_mugi` in production config.**

*MuGI + TF-IDF weighted query (`bm25_mugi_tfidf`):* discriminative keyword filtering from pseudo-note tokens. R@10 0.462→0.474 (+1.2pp). Positive but smaller than stemming; not worth the additional complexity when stemming already wins.

*HyDE multi-sample (`hyde_multi`):* generate 3 hypothetical notes, average their embeddings for a stable centroid. vs single HyDE: R@10 0.408→0.489 (+8.1pp), coverage 53.3%→61.3%, MRR 0.614→0.744. Large improvement — single-sample HyDE has high variance; averaging eliminates unlucky generations. **Replaces `hyde` in production config.**

*LLM cross-encoder reranker:* post-fusion Haiku call scoring 20 candidates per event. Result: R@10=0.660 vs equal blend 0.674 — worse, not better. Haiku at 400-char snippets is too noisy as a relevance scorer. Would require a proper bi-encoder/cross-encoder model, not a prompted chat LLM. **Not recommended at current quality level.**

**Weight tuning — proper 80/20 held-out validation (seed=42, 239 train / 60 test):**

Previous tuning used all 299 events; corrected to avoid overfitting.

*Phase 1 — precision core (body_query / bm25_mugi_stem / activation) on train:*

| body_query | bm25_stem | activation | R@10(tr) | MRR(tr) |
|-----------|----------|-----------|----------|---------|
| **0.5** | **0.3** | **0.2** | **0.682** | **0.842** ★ |
| 0.6 | 0.2 | 0.2 | 0.681 | 0.836 |
| 0.4 | 0.4 | 0.2 | 0.678 | 0.844 |

Stemming earns more weight (0.2→0.3); body_query drops correspondingly (0.6→0.5). The improved lexical signal is pulling its weight.

*Phase 2 — discovery tier δ at best core, train then test:*

| δ | R@10(tr) | R@10(te) | MRR(tr) | MRR(te) |
|---|----------|----------|---------|---------|
| 0.00 | 0.682 | 0.671 | 0.842 | 0.853 |
| **0.10** | **0.694** | **0.667** | **0.853** | **0.844** ★ |
| 0.20 | 0.686 | 0.684 | 0.866 | 0.836 |

δ=0.10 is the training optimum and conservative choice. (δ=0.20 achieves 0.684 on test, slightly higher, but with more discovery-signal dilution — noisy at n=60.)

Train/test gap: 2.7pp (vs 3.4pp for previous config) — upgraded signals generalise better.

**Final tuned weights (upgraded signals, held-out validated):**

| Signal | Weight | Role |
|--------|--------|------|
| body_query | 0.450 | Primary ranker (asymmetric embedding) |
| bm25_mugi_stem | 0.270 | Lexical complement (stemmed MuGI expansion) |
| activation | 0.180 | Graph complement (co-activation history) |
| step_back | 0.050 | Discovery (abstract principle retrieval) |
| hyde_multi | 0.050 | Discovery (3-sample averaged hypothetical) |

**Validated result: R@10=0.667, MRR=0.844 (held-out test, n=60)** — vs body-only baseline on same test set R@10=0.542, MRR=0.775. **+12.5pp R@10, +6.9pp MRR — confirmed out-of-sample.**

Coverage@20=93.7% (full 8-signal union). The tuned 5-signal config is the production default; bm25_mugi_tfidf and bm25_keyword are available in the workbench for future experimentation.

**MRR interpretation:** MRR=0.844 means the single most relevant note is at rank 1 in ~84% of events. The integration LLM reads notes in rank order; the highest-priority integration target is reliably at the top of the cluster.
