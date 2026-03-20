# Spike 5 Results — Activation-Weighted Cluster Identification

*Run: 2026-03-15 01:08*
*Leave-one-out over 20 Spike 4D events*
*Blend α=0.3, decay λ=0.05, cluster window top-20*

Ground truth: Spike 4D LLM-judged integration targets (same evaluation set).
Spike 4D body_sim baseline for reference: R@5=0.404, R@10=0.512, MRR=0.790

---

## H-new-A: Does activation signal improve recall?

### Confirmed interactions only (W_null=0.0)

| Strategy | R@3 | R@5 | R@10 | MRR |
|----------|-----|-----|------|-----|
| Body embedding only (Spike 4D baseline) | 0.289 | 0.404 | 0.512 | 0.790 |
| Activation signal only | 0.010 | 0.010 | 0.033 | 0.045 |
| Body + activation blend (α=0.3) | 0.192 | 0.297 | 0.482 | 0.637 |

### Including co-retrieved notes (W_null=0.3)

| Strategy | R@3 | R@5 | R@10 | MRR |
|----------|-----|-----|------|-----|
| Body embedding only (Spike 4D baseline) | 0.289 | 0.404 | 0.512 | 0.790 |
| Activation signal only | 0.020 | 0.020 | 0.043 | 0.073 |
| Body + activation blend (α=0.3) | 0.192 | 0.266 | 0.482 | 0.489 |

---

## H-new-B: Does including co-retrieved-but-NOTHING notes help?

Compare body+activation rows between the two tables above.
If W_null=0.3 beats W_null=0.0: non-acted-on co-retrieval adds signal.
If W_null=0.0 beats W_null=0.3: restrict activation to confirmed interactions only.

---

## Network diagnostics (full 20-event activation graph)

| Metric | Value |
|--------|-------|
| Nodes with at least one activation link | 89 |
| Edges (unique co-activation pairs) | 265 |
| Mean degree | 6.0 |
| Max degree | 15 |
| Mean clustering coefficient | 0.877 |

A high clustering coefficient relative to a random graph of the same density
indicates small-world structure is forming. Expected: CC >> p (edge probability).
Edge probability (p) for a random graph: 0.0677

---

## Evaluation notes

*(Fill in after reviewing output)*

### H-new-A: Does activation signal help?
- body+activation vs body_sim: [fill in]
- Interpretation: [fill in]

### H-new-B: Does W_null=0.3 add signal?
- W_null=0.3 vs W_null=0.0 on body+activation: [fill in]
- Recommendation: [fill in]

### Network topology
- Is clustering coefficient >> edge probability? [fill in]
- Small-world signature emerging? [fill in]

### Caveats
- Only 20 events: LOO evaluation has high variance; treat directional not definitive
- All events simulated at age=0: decay function not yet exercised
- [Any other observations]

## Go / No-go

[ ] Go — body+activation R@10 ≥ 0.65 (vs 0.512 body_sim baseline)
[ ] Marginal — improvement < 0.10 but consistent; implement with larger event set
[ ] No-go — no improvement; activation signal too sparse at 20 events

**Recommendation:** [fill in]