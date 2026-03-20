# Spike 6A Results — BM25 + MuGI Query Expansion

*Run: 2026-03-15 10:11*
*299 events, cluster window top-20, 3 pseudo-notes per query*

Spike 5 ceiling for reference: body+activation R@10=0.640, MRR=0.827

---

## Baselines

| Strategy | R@3 | R@5 | R@10 | MRR |
|----------|-----|-----|------|-----|
| Body embedding (Spike 5 baseline) | 0.298 | 0.403 | 0.534 | 0.767 |
| BM25 plain (no expansion) | 0.217 | 0.285 | 0.406 | 0.630 |
| BM25 MuGI (expanded query) | 0.258 | 0.343 | 0.462 | 0.690 |

---

## Beta sweep — Body + BM25 plain

| β | R@3 | R@5 | R@10 | MRR |
|---|-----|-----|------|-----|
| β=0.1 | 0.321 | 0.411 | 0.555 | 0.774 |
| β=0.2 ★ | 0.324 | 0.423 | 0.555 | 0.775 |
| β=0.3 | 0.321 | 0.422 | 0.554 | 0.765 |
| β=0.4 | 0.312 | 0.404 | 0.545 | 0.756 |
| β=0.5 | 0.294 | 0.392 | 0.528 | 0.741 |

---

## Beta sweep — Body + BM25 MuGI

| β | R@3 | R@5 | R@10 | MRR |
|---|-----|-----|------|-----|
| β=0.1 | 0.319 | 0.427 | 0.567 | 0.790 |
| β=0.2 | 0.341 | 0.448 | 0.584 | 0.795 |
| β=0.3 | 0.349 | 0.454 | 0.590 | 0.797 |
| β=0.4 ★ | 0.343 | 0.455 | 0.590 | 0.785 |
| β=0.5 | 0.330 | 0.438 | 0.572 | 0.770 |

---

## Go / No-go

Success criterion: R@10 ≥ 0.70 (vs 0.640 body+activation ceiling)

[ ] Go — R@10 ≥ 0.70
[ ] Partial — improvement but below threshold
[ ] No-go — no improvement over body baseline