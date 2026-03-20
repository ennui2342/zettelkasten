# Spike 4A Results — Cluster Identification

*Run: 2026-03-15 00:09*
*Model: voyage-3-lite*
*Eval notes (with in-corpus links): 226 / 300*

Ground truth: Wikipedia inter-article links. If note A links to note B, a query built from A's content should retrieve B in the top-k cluster.

---

## Base retrieval strategies (N=226)

| Strategy | R@3 | R@5 | R@10 | MRR |
|----------|-----|-----|------|-----|
| Body embedding, similarity only | 0.214 | 0.274 | 0.381 | 0.565 |
| Context field (first sentence) embedding | 0.158 | 0.212 | 0.288 | 0.464 |
| Body embedding + link traversal depth=1 | 0.047 | 0.098 | 0.184 | 0.310 |
| Body embedding + link traversal depth=2 | 0.032 | 0.050 | 0.087 | 0.168 |

## Summary and tag strategies (N=30)

Evaluated on the 30 most-connected notes only (those with LLM-generated summaries/tags).
Query: LLM summary embedding or extracted tags. Retrieval pool: all 300 note bodies.

| Strategy | R@3 | R@5 | R@10 | MRR |
|----------|-----|-----|------|-----|
| Body embedding (subset baseline) | 0.044 | 0.070 | 0.132 | 0.795 |
| LLM summary embedding | 0.043 | 0.063 | 0.119 | 0.751 |
| Tag keyword count | 0.033 | 0.043 | 0.062 | 0.553 |
| Tag keyword + body embedding (50/50) | 0.044 | 0.062 | 0.113 | 0.749 |

## Link expansion fan-out diagnostic

How many notes does depth-1 link expansion draw into the cluster, and what fraction of the *newly added* nodes (beyond the top-10 similarity anchor) are actually in the ground truth?

| Metric | Value |
|--------|-------|
| Mean cluster size — top-10 only | 10 |
| Mean cluster size — depth=1 expanded | 52.7 |
| Max cluster size — depth=1 expanded | 78 |
| Mean cluster size — depth=2 expanded | 107.8 |
| Max cluster size — depth=2 expanded | 128 |
| Precision of new nodes added at depth=1 | 0.156 |

Precision of new nodes: what fraction of the nodes *added* by link expansion (not already in the top-10) are ground-truth targets. Low precision means expansion is drawing in noise.

---

## Evaluation notes

*(Fill in after reviewing output)*

### Embedding target (body vs context field vs LLM summary)
- Body vs context field: [fill in]
- Body vs LLM summary: [fill in]
- Does context field evolution pass matter for retrieval? [fill in]

### Tag-based retrieval
- Tag keyword vs body embedding: [fill in]
- Does tag+body blend beat either alone? [fill in]

### Link traversal (H3)
- Fan-out diagnostic: does expansion pull in mostly noise? [fill in]
- Should link traversal be used in production? [fill in]

### Ground truth quality
- Wikipedia links as proxy for 'notes worth integrating': [fill in]
- What a better ground truth would look like: [fill in]

## Go / No-go

[ ] Go — best strategy R@5 ≥ 0.40; embedding target question answered
[ ] Conditional — similarity workable but tag/summary improvement worth pursuing
[ ] No-go — similarity too weak; rethink embedding strategy

**Recommendation:** [fill in]