# Activation Network

The activation network is a weighted co-occurrence graph stored in SQLite. It records which notes tend to appear together during integration events, giving the retrieval system a signal that goes beyond embedding similarity: notes that have a history of being relevant to the same ingested content rank higher when that context recurs.

## What it is

Each integration event produces a set of notes selected by the L1 classifier (`target_note_ids`). The activation network records pairwise edges between the query note and each selected note, and transitively between all selected notes. Each edge carries a weight that reflects how often those two notes have been co-activated.

At retrieval time, `get_activation_scores(qid)` returns the effective weight of all notes co-activated with the query note. This becomes one of five signals fused in the gather phase (weight 0.18).

## What it is not

Activation is not a citation graph. It is not derived from links between notes. It is purely a record of integration history — which notes the system chose to involve when processing new content.

## Decay: keeping the network current

Without decay, activation weights grow without bound and early hubs dominate permanently. A note that accumulates high weight in the first ten papers ingested remains at the top of the activation signal indefinitely, regardless of whether subsequent literature reinforces it.

The design goal for decay is not forgetting — it is **keeping the network current with the Overton window of the literature being ingested**. If cloud hosting dominates discussion for twenty papers and then the literature shifts to edge computing, the activation network should reflect that shift: cloud-adjacent notes should fade, edge-adjacent notes should rise.

### Event-based decay

Decay is measured in **ingestion events** (papers), not wall-clock time. This is a better unit for a knowledge base that grows through document ingestion: "how many papers ago was this connection last reinforced?" is a meaningful question; "how many days ago?" is arbitrary, since ten papers might arrive in a day or over a month.

A global `ingestion_count` is maintained in the index and incremented once per `ingest_text` call. Each activation edge stores the `ingestion_at` value — the counter at the time the edge was last written.

Effective weight at query time:

```
effective = stored_weight * factor ** (current_count - ingestion_at)
```

When an edge is reinforced by a new event, the existing weight is decayed to its effective value before the increment is added:

```
effective = stored_weight * factor ** (current_count - ingestion_at)
new_stored = effective + 1.0
ingestion_at = current_count
```

### Tuning factor

`factor` is the fraction of weight retained per ingestion event. A reasonable starting point:

- `factor = 0.95` → half-life ≈ 14 papers
- `factor = 0.93` → half-life ≈ 10 papers
- `factor = 0.90` → half-life ≈ 7 papers

For a note activated every paper, weight asymptotes at `1.0 / (1 - factor)`. With `factor = 0.95` that ceiling is 20; with `factor = 0.90` it is 10. The ratio between a constantly-reinforced hub and a note last activated five papers ago stays bounded and self-correcting.

The default is `ACTIVATION_DECAY_FACTOR = 0.95`. This can be overridden per call for experimentation.

### What this replaces

The previous design used time-based exponential decay (`exp(-λ * elapsed_days)`) with a 14-day half-life. This was a placeholder: λ was never tuned against real temporal data, and real-world time is a poor unit for a system whose ingestion rate is irregular. The `updated` timestamp column in the `activation` table is replaced by `ingestion_at` (an integer).

## Schema

```sql
CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- key = 'ingestion_count', value = integer as text

CREATE TABLE activation (
    note_a       TEXT NOT NULL,
    note_b       TEXT NOT NULL,
    weight       REAL NOT NULL DEFAULT 0.0,
    ingestion_at INTEGER NOT NULL,
    PRIMARY KEY (note_a, note_b)
);
```

## Properties

- **New hubs can always emerge.** A note that appears in every cluster for ten consecutive papers will accumulate weight quickly regardless of what came before.
- **Old hubs fade if not reinforced.** A note that stops appearing in clusters loses weight with each subsequent ingestion, eventually becoming indistinguishable from background.
- **Weights are bounded.** The asymptotic ceiling for a constantly-activated note is `1.0 / (1 - factor)`, not infinity.
- **No background sweep needed.** Decay is applied lazily at read and write time. The database stores raw weights; effective weights are always computed on access.
- **Time-independent.** Ingestion rate does not affect decay. A slow week and a fast week produce the same decay per paper ingested.
