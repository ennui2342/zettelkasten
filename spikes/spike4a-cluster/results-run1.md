# Spike 4A Results — Cluster Identification

*Run: 2026-03-14 23:22*
*Model: voyage-3-lite*
*Eval notes (with in-corpus links): 226 / 300*

---

## Retrieval strategy comparison

Ground truth: Wikipedia inter-article links. If note A links to note B, a query built from A's content should retrieve B in the top-k cluster.

### Recall@k

| Strategy | R@3 | R@5 | R@10 |
|----------|-----|-----|------|
| Body embedding, similarity only | 0.214 | 0.274 | 0.381 |
| Context field embedding, similarity only | 0.158 | 0.212 | 0.288 |
| Body embedding + link traversal depth=1 | 0.035 | 0.069 | 0.127 |
| Body embedding + link traversal depth=2 | 0.022 | 0.037 | 0.120 |

### Mean Reciprocal Rank (MRR)

| Strategy | MRR |
|----------|-----|
| Body embedding, similarity only | 0.565 |
| Context field embedding, similarity only | 0.464 |
| Body embedding + link traversal depth=1 | 0.283 |
| Body embedding + link traversal depth=2 | 0.257 |

---

## Embedding target analysis

Compare rows 1 and 2 above: does the short context field sentence retrieve better
than the full body? If yes, the context field evolution pass is load-bearing for
retrieval quality.

## Link traversal analysis

Compare rows 1, 3, 4: does link expansion improve recall? If depth=1 helps but
depth=2 does not (or hurts precision), depth=1 is the right production setting.

---

## Evaluation notes

*(Fill in after reviewing output)*

### Embedding target
- Body vs context field winner: [fill in]
- Implication for context field evolution pass: [fill in]

### Link traversal (H3)
- Does traversal improve recall? [fill in]
- Best depth (H9): [fill in]

### Retrieval quality overall
- Is top-5 similarity sufficient for production? [fill in]
- Any failure modes observed? [fill in]

## Go / No-go

[ ] Go — body_sim R@5 ≥ 0.40 (similarity alone workable); link traversal adds
         ≥0.05 R@5 improvement (worth implementing); context field ≥ body or within 0.02
[ ] No-go — similarity too weak; rethink embedding strategy

**Recommendation:** [fill in]