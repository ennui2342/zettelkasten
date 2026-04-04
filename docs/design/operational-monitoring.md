# Operational Monitoring

A running zettelkasten memory store accumulates failure modes that are invisible without instrumentation. Most failures are silent: missed integrations don't raise exceptions; duplicate notes don't cause errors; a note that should have been an UPDATE silently becomes a CREATE. This document is a living wishlist of metrics and analyses — built up as the system runs and new failure modes are encountered.

The distinction between *continuous metrics* (computed cheaply on every integration event) and *periodic analyses* (heavier, run weekly or on-demand) is important. Don't make every write expensive; defer the deeper analysis to batch jobs.

---

## Continuous metrics (per integration event or daily rollup)

### Integration decision distribution

The balance of decision types tells you whether the system is healthy or drifting.

- `decision_counts` — rolling counts of UPDATE / CREATE / EDIT / SPLIT / SYNTHESISE / NOTHING per week
- `nothing_rate` — NOTHING as a fraction of all decisions; a rising NOTHING rate suggests retrieval is degrading (the cluster no longer surfaces the right notes, so the LLM sees no actionable candidates)
- `duplicate_pair_rate` — weekly count of note pairs with cosine similarity > 0.90; a rising rate alongside high CREATE rate is a duplicate risk signal

### Retrieval health proxy

Full LOO evaluation is expensive; a cheap proxy is feasible per-event.

- `mean_cluster_similarity` — average cosine similarity of the top-20 cluster to the query note; a falling mean suggests embedding drift or corpus composition shift
- `activation_coverage` — fraction of events where at least one gold note had a positive activation score; tracks whether the co-activation graph is accumulating useful signal

---

## Periodic analyses (weekly or on-demand)

### Duplicate detection

The most damaging long-term failure mode is notes that should have been integrated instead getting duplicated — the corpus grows but doesn't synthesise.

- **High-similarity scan**: for all note pairs, flag pairs with body embedding cosine similarity > 0.90. Review the flagged pairs: are they duplicates, near-duplicates, or legitimately distinct?
- **Cross-type similarity**: look for (permanent, permanent) pairs with high similarity — these are candidates for SYNTHESISE on next ingestion, or for manual curation

Implementation: `sqlite-vec` cosine scan at write time is O(n) per note; weekly full-corpus scan is feasible for corpora up to ~10k notes.

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
- `duplicate_pair_rate` rising while retrieval looks healthy — the LLM is not seeing both members of duplicate pairs in the same cluster; wider K may surface them
- Integration latency or cost concerns — if K=20 proves expensive, K=10 retains 67% coverage with meaningfully lower token cost

K could also be made variable per-agent: a *gather* agent (precision integration) uses K=20; a *discovery* agent (surfacing unexpected connections, serendipitous links) uses K=50 where weak-tie recall matters more than precision.

### Retrieval quality (full workbench)

Run the full LOO workbench (`eval/gather/`) monthly against an evolving ground truth set. As the real corpus accumulates real integration events, the synthetic Spike 4D ground truth becomes less representative — build a real evaluation set by periodically sampling recent integration events and having the LLM judge which notes the integration touched.

- R@10, MRR, coverage@20 tracked over time; regression indicates retrieval degradation
- Coverage ceiling tracks whether new notes are being added in retrievably accessible regions of the corpus, or whether the corpus is growing in isolated pockets

### Corpus health

- SYNTHESISE fraction over time — a growing SYNTHESISE fraction relative to CREATE indicates the corpus is maturing and the integration LLM is finding connections across notes rather than only adding new ones
- Mean note body length over time — if falling, the integration LLM is writing terse notes; if rising, notes may be accumulating redundant content
- **See Also link density** — mean degree of the See Also wikilink graph across the corpus; healthy growth in link density indicates the integration LLM is finding genuine connections between notes; a plateau suggests notes are being created in isolation
- **Hub note fraction** — notes with high See Also link degree (> 15 in a ~300-note corpus; scale proportionally) or high activation graph degree flagged as potential SPLIT candidates. A healthy corpus has very few hubs; rising hub count may indicate notes written at too high a level of generality. Hub notes are routing nodes, not insight nodes — they signal that a concept has outgrown its note and may benefit from subdivision. Track `hub_count` and `max_degree` over time across both the See Also graph and the activation graph; both should be bounded in a well-maintained corpus

### Activation graph health

- `orphan_node_fraction` — fraction of notes with zero activation edges; should decline over time as integration events accumulate
- `mean_degree` and `clustering_coefficient` — small-world signature should strengthen over months; CC > 0.3 and mean degree > 5 indicate a well-integrated graph
- `hub_notes` — high-degree activation nodes are the conceptual hubs of the corpus; reviewing them periodically confirms the corpus is organised around the right central concepts. Note that high activation-graph degree and high See Also link degree are different signals: activation hubs are genuinely central concepts (co-retrieved across many events); See Also hubs are notes the integration LLM consistently links to — often the same set, but not always
- `cold_start_curve` — plot R@10 vs number of integration events; the point at which activation-weighted retrieval begins outperforming body-only is the end of the cold-start period (expected ~50–100 events based on spike results)

---

## Implementation notes

All continuous metrics should be computed during `ingest_text` and written to a `metrics` SQLite table alongside the `activation` table — cheap append, queryable via standard SQL.

The periodic analyses can run as standalone scripts in `tools/`. They do not need to be part of the hot path.

This document should be updated whenever a new failure mode is encountered in production use. The goal is not a comprehensive upfront specification but a growing operational playbook.
