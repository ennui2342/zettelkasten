# Spike 4D Results — LLM Ground Truth Retrieval Evaluation

*Run: 2026-03-15 01:57*
*Ground truth model: claude-sonnet-4-6*
*Embedding model: voyage-3-lite*
*Query notes: 300 total, 299 with interactions, 1 STUB (no interactions — excluded)*
*Mean gold set size: 4.6 notes per query*

Ground truth: for each query note, the integration LLM identified which existing
notes would trigger UPDATE, MERGE, SPLIT, or SYNTHESISE. Retrieval strategies are
evaluated on whether they surface those notes in the top-k cluster.

---

## Retrieval strategy comparison

| Strategy | R@3 | R@5 | R@10 | MRR |
|----------|-----|-----|------|-----|
| Body embedding, similarity only | 0.298 | 0.403 | 0.533 | 0.767 |
| Context field (first sentence) embedding | 0.207 | 0.273 | 0.379 | 0.594 |
| LLM summary embedding | 0.341 | 0.474 | 0.631 | 0.822 |

---

## Interpretation

If body_sim R@5 ≥ 0.60 against this ground truth:
  → Body embedding alone reliably surfaces the notes worth integrating.
  → Link traversal and tag-based expansion are confirmed noise — drop them.
  → Context field vs body question answered by comparing rows 1 and 2.

If body_sim R@5 < 0.40:
  → Pure similarity is insufficient; cluster identification needs rethinking.

---

## Evaluation notes

*(Fill in after reviewing output)*

### Body embedding verdict
- R@5 against LLM ground truth: [fill in]
- Verdict — sufficient for production cluster? [fill in]

### Link traversal and tags (H3)
- If body_sim sufficient: confirmed noise, eliminate from design [fill in]

### Embedding target
- Body vs context field vs LLM summary: [fill in]

## Go / No-go

[ ] Go — body_sim R@5 ≥ 0.60 against LLM ground truth
[ ] Marginal — R@5 0.40–0.60, may need hybrid approach
[ ] No-go — R@5 < 0.40, rethink cluster strategy

**Recommendation:** [fill in]