# Operational Monitoring

A running zettelkasten memory store accumulates failure modes that are invisible without instrumentation. Most failures are silent: missed integrations don't raise exceptions; duplicate notes don't cause errors; an orphaned stub just quietly never develops. This document is a living wishlist of metrics and analyses — built up as the system runs and new failure modes are encountered.

The distinction between *continuous metrics* (computed cheaply on every integration event) and *periodic analyses* (heavier, run weekly or on-demand) is important. Don't make every write expensive; defer the deeper analysis to batch jobs.

---

## Continuous metrics (per integration event or daily rollup)

### Stub health

The highest-risk silent failure mode. Stubs that are retrievally invisible don't develop — they become permanent orphans or get duplicated by future integration events.

- `stub_count` — total stub notes in the corpus at time of reporting
- `stub_age_p50/p90` — age distribution of stubs since creation; rising p90 is the early warning signal
- `stub_no_update_30d` / `stub_no_update_90d` — count of stubs that have received zero UPDATE operations in the last 30/90 days; the primary orphan indicator
- `stub_conversion_rate` — fraction of stubs that receive at least one UPDATE within 30 days of creation; healthy systems should see stubs promoted steadily

Alert threshold: if `stub_no_update_90d` / `stub_count` exceeds 20%, trigger a stub review pass.

### Integration decision distribution

The balance of decision types tells you whether the system is healthy or drifting.

- `decision_counts` — rolling counts of UPDATE / CREATE / EDIT / SPLIT / SYNTHESISE / NOTHING / STUB per week
- `nothing_rate` — NOTHING as a fraction of all decisions; a rising NOTHING rate suggests retrieval is degrading (the cluster no longer surfaces the right notes, so the LLM sees no actionable candidates)
- `stub_rate` — STUB as a fraction of all decisions; healthy in early growth, concerning if it plateaus without corresponding drops in `stub_no_update_*`
- `duplicate_pair_rate` — weekly count of note pairs with cosine similarity > 0.90; a rising rate alongside high CREATE rate is a duplicate risk signal and the primary trigger for reconsidering MERGE (see `architecture-decisions.md §7a`)

### Retrieval health proxy

Full LOO evaluation is expensive; a cheap proxy is feasible per-event.

- `mean_cluster_similarity` — average cosine similarity of the top-20 cluster to the query note; a falling mean suggests embedding drift or corpus composition shift
- `activation_coverage` — fraction of events where at least one gold note had a positive activation score; tracks whether the co-activation graph is accumulating useful signal

---

## Periodic analyses (weekly or on-demand)

### Duplicate detection

The most damaging long-term failure mode is notes that should have been merged instead getting duplicated — the corpus grows but doesn't integrate.

- **High-similarity scan**: for all note pairs, flag pairs with body embedding cosine similarity > 0.90. Review the flagged pairs: are they duplicates, near-duplicates, or legitimately distinct?
- **Stub-to-stub similarity**: scan stubs specifically for pairwise similarity > 0.85 — stub duplicates are common when retrieval fails and the LLM creates a stub for a concept that already has one
- **Cross-type similarity**: look for (stub, permanent-note) pairs with high similarity — these are stubs that should have been promoted to UPDATE operations but weren't caught by retrieval

Implementation: `sqlite-vec` cosine scan at write time is O(n) per note; weekly full-corpus scan is feasible for corpora up to ~10k notes.

### Stub quality analysis

Beyond age, inspect the content quality of orphaned stubs.

- Body length distribution of stubs vs non-stubs: stubs should be shorter but not trivially so (very short = under-specified, not retrievable)
- Vocabulary richness: unique term count; stubs below a threshold (e.g. < 20 unique 4+ char tokens) are likely too sparse to surface via BM25 or embedding retrieval — candidates for manual enrichment
- Synonym/related-term coverage: does the stub body include the kind of related vocabulary specified in the stub prompt? (Can be checked by an LLM judge pass on flagged orphans)

### Candidate window size (K) tuning

The cluster size passed to the integration LLM (default K=20) is a critical trade-off between coverage and noise. The workbench shows the marginal value of each step:

| K | Coverage ceiling | Marginal gain | Notes in LLM context |
|---|---|---|---|
| 10 | ~67% | — | 10 |
| 20 | 93.7% | +26.7pp | 20 |
| 50 | 98.4% | +4.7pp | 50 |
| 100 | 99.7% | +1.3pp | 100 |

The jump from K=10→20 is large and worth the cost; K=20→50 adds only 4.7pp at 2.5× the context noise. K=20 is the recommended default, but live performance may warrant adjustment.

Signals to watch that indicate K needs tuning:
- Rising `nothing_rate` despite healthy `mean_cluster_similarity` — the cluster is semantically coherent but the gold notes are landing just outside the window; try K=30–50
- `merge_rate` plateauing while duplicate detection flags pairs — the LLM is not seeing both members of duplicate pairs in the same cluster; wider K may surface them
- Integration latency or cost concerns — if K=20 proves expensive, K=10 retains 67% coverage with meaningfully lower token cost

K could also be made variable per-agent: a *gather* agent (precision integration) uses K=20; a *discovery* agent (surfacing unexpected connections, serendipitous links) uses K=50 where weak-tie recall matters more than precision.

### Retrieval quality (full workbench)

Run the full LOO workbench (`spikes/retrieval-workbench/main.py`) monthly against an evolving ground truth set. As the real corpus accumulates real integration events, the synthetic Spike 4D ground truth becomes less representative — build a real evaluation set by periodically sampling recent integration events and having the LLM judge which notes the integration touched.

- R@10, MRR, coverage@20 tracked over time; regression indicates retrieval degradation
- Coverage ceiling tracks whether new notes are being added in retrievably accessible regions of the corpus, or whether the corpus is growing in isolated pockets

### Corpus health

- Note type distribution over time (permanent / stub / refuted / synthesised) — a healthy corpus has a declining stub fraction and a growing synthesised fraction as integration matures
- Mean note body length over time — if falling, the integration LLM is writing terse notes; if rising, notes may be accumulating redundant content rather than being merged
- Link density (mean degree of the link graph) — healthy growth in link density indicates the corpus is becoming more integrated; a plateau suggests notes are being created but not connected
- Refuted note fraction — a rising fraction of refuted notes is healthy (knowledge is being revised); a stable near-zero fraction could indicate the LLM is avoiding refutation and instead creating redundant notes
- **Hub note fraction** — notes with link degree > 15 (in a ~300-note corpus; scale proportionally) flagged as SPLIT candidates. A healthy corpus has very few hubs; rising hub count indicates the curation agent is not keeping pace with corpus growth, or that notes are being written at too high a level of generality. Hub notes are routing nodes, not insight nodes — they signal that a concept has outgrown its note and needs subdivision. Track `hub_count` and `max_link_degree` over time; both should be bounded in a well-maintained corpus

### Activation graph health

- `orphan_node_fraction` — fraction of notes with zero activation edges; should decline over time as integration events accumulate
- `mean_degree` and `clustering_coefficient` — small-world signature should strengthen over months; CC > 0.3 and mean degree > 5 indicate a well-integrated graph
- `hub_notes` — high-degree activation nodes are the conceptual hubs of the corpus; reviewing them periodically confirms the corpus is organised around the right central concepts. Note that high activation-graph degree and high *link* degree are different signals: activation hubs are genuinely central concepts; link-graph hubs are often over-broad notes that have accumulated links by being general rather than specific. The latter are SPLIT candidates (see the implementation plan §4e)
- `cold_start_curve` — plot R@10 vs number of integration events; the point at which activation-weighted retrieval begins outperforming body-only is the end of the cold-start period (expected ~50–100 events based on spike results)

---

## Implementation notes

All continuous metrics should be computed in `IntegrationProcessor` and written to a `metrics` SQLite table alongside the `co_activations` table — cheap append, queryable via standard SQL.

The periodic analyses can run as one-off aswarm pipelines (`type: script` stages reading from the SQLite index) or as standalone scripts in `tools/`. They do not need to be part of the hot path.

The monitoring section of this document should be updated whenever a new failure mode is encountered in production use. The goal is not a comprehensive upfront specification but a growing operational playbook.
