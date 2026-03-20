# Spike 4A — Cluster Identification

**What this spike tests:** given an incoming draft note, which retrieval strategy best finds the right cluster of existing notes?

**Hypotheses under test:** H3 (link traversal augments similarity), H9 (optimal traversal depth), plus the embedding target question (full body vs short context field).

**Ground truth:** Wikipedia's own inter-article link structure. If article A links to article B, a retrieval query built from A's content should surface B in the top-k cluster. No hand-labelling required.

---

## Setup

```bash
# Install spike dependencies (inside container)
docker compose run --rm dev pip install voyageai numpy

# Or install from requirements.txt
docker compose run --rm dev pip install -r spikes/spike4a-cluster/requirements.txt
```

`VOYAGE_API_KEY` must be in `.env`.

---

## Step 1 — Build corpus

Fetches ~200–300 Wikipedia articles from cognitive science / memory categories,
converts each to a zettelkasten-format note with frontmatter.

```bash
docker compose run --rm dev python spikes/spike4a-cluster/build_corpus.py
```

Output: `corpus/` directory with one `.md` per article, and `title_map.json`.

---

## Step 2 — Run spike

Embeds all corpus notes with Voyage AI (cached after first run), then evaluates
four retrieval strategies against the Wikipedia link ground truth.

```bash
docker compose run --rm dev python spikes/spike4a-cluster/spike.py
```

Embeddings are cached in `embeddings_cache.json` — re-running the spike after
the first time is fast (no API calls).

---

## Strategies compared

| ID | Strategy |
|----|----------|
| body_sim | Body embedding, cosine similarity only |
| ctx_sim | Context field (first sentence) embedding, cosine similarity only |
| body_link1 | Body similarity top-10, expanded by following links depth=1 |
| body_link2 | Body similarity top-10, expanded by following links depth=2 |

---

## What to look for

**Embedding target (body vs context field):**
- If `ctx_sim` ≥ `body_sim`: the short context sentence is as good or better for retrieval than the full body. This validates the A-MEM finding and makes the context field evolution pass load-bearing — keeping it fresh matters for cluster quality.
- If `body_sim` >> `ctx_sim`: full body embedding is better; context field evolution is a nice-to-have, not critical.

**Link traversal (H3, H9):**
- If `body_link1` > `body_sim`: link traversal genuinely surfaces notes that similarity missed. Worth implementing in production Gather(A).
- If `body_link2` > `body_link1`: depth=2 adds more value; deeper traversal warranted.
- If `body_link1` ≈ `body_sim`: linked notes are already similar enough to appear in top-k without traversal. H3 is not load-bearing for this domain.

**Overall quality:**
- R@5 ≥ 0.40 means the right notes appear in a cluster of 5 more than 40% of the time — workable for production where the integration LLM reads the whole cluster.
- R@5 < 0.30 means retrieval is too noisy; consider richer embeddings (voyage-3 vs voyage-3-lite) or reframing.

---

## Go criteria

- `body_sim` R@5 ≥ 0.40 — similarity alone is workable
- `body_link1` R@5 ≥ `body_sim` R@5 + 0.05 — link traversal adds meaningful value
- `ctx_sim` R@5 within 0.05 of `body_sim` — context field is a viable embedding target
