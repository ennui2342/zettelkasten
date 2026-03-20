# Spike 6A Results — BM25 + MuGI Extended (RRF, Three-Way, Coverage)

*Run: 2026-03-15 10:30*
*299 events, cluster window top-20, 3 pseudo-notes, RRF k=60*

Reference: body baseline R@10=0.534 | body+activation R@10=0.640 | target R@10≥0.700

---

## Baselines

| Strategy | R@3 | R@5 | R@10 | MRR |
|----------|-----|-----|------|-----|
| Body embedding | 0.298 | 0.403 | 0.534 | 0.767 |
| BM25 plain (full body) | 0.217 | 0.285 | 0.406 | 0.630 |
| BM25 MuGI (expanded) | 0.258 | 0.343 | 0.462 | 0.690 |
| BM25 keyword TF-IDF | 0.209 | 0.268 | 0.361 | 0.592 |

---

## Weighted sum — Body + BM25 variant

| β | BM25 plain R@10 | BM25 MuGI R@10 | BM25 keyword R@10 |
|---|----------------|----------------|-------------------|
| β=0.1 | 0.555 | 0.567 | 0.569 |
| β=0.2 | 0.555 | 0.584 | 0.544 |
| β=0.3 | 0.554 | 0.590 | 0.504 |
| β=0.4 | 0.545 | 0.590 | 0.478 |
| β=0.5 | 0.528 | 0.572 | 0.445 |

---

## RRF fusion

| Strategy | R@3 | R@5 | R@10 | MRR |
|----------|-----|-----|------|-----|
| RRF: body + BM25 plain | 0.294 | 0.388 | 0.515 | 0.736 |
| RRF: body + BM25 MuGI | 0.322 | 0.422 | 0.558 | 0.765 |
| RRF: body + BM25 keyword | 0.280 | 0.372 | 0.518 | 0.724 |

---

## Three-way: body + BM25 MuGI + activation

| Strategy | R@3 | R@5 | R@10 | MRR |
|----------|-----|-----|------|-----|
| Body only (reference) | 0.298 | 0.403 | 0.534 | 0.767 |
| RRF 3-way (body + MuGI + activation) | 0.349 | 0.467 | 0.631 | 0.805 |
| Blend 3-way (0.6 body + 0.2 MuGI + 0.2 act) | 0.389 | 0.516 | 0.685 | 0.853 |
| Blend 3-way (0.5 body + 0.3 MuGI + 0.2 act) | 0.395 | 0.521 | 0.681 | 0.849 |

---

## Go / No-go

Success criterion: R@10 ≥ 0.70 (vs 0.640 body+activation ceiling)

[ ] Go — R@10 ≥ 0.70
[ ] Partial — meaningful improvement, below threshold
[ ] No-go — coverage diagnostic shows insufficient reachable gold notes