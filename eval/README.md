# Evals

Tests for design decisions that are susceptible to the **bitter lesson**: choices made because the current best model needed them may become wrong as better models are released. Each test captures the decision, the baseline result, and instructions for re-running.

## The pattern

When a design decision is motivated by *what a current model can or cannot do reliably*, that decision should be treated as provisional and re-evaluated when models improve. Common examples:

- Multi-step prompting patterns added because single-step was unreliable
- Signal fusion weights tuned to compensate for model weaknesses
- Scaffolding (count-first, chain-of-thought) added to guide weaker models
- Conservative thresholds set because a model's outputs were noisy

As models improve, these scaffolds may become unnecessary overhead. The tests here make those re-evaluations cheap.

## How to re-run

Each subdirectory has its own `README.md` with:

1. **The decision** — what was decided and why
2. **The baseline** — exact results when the decision was made (model, date, metrics)
3. **Re-run instructions** — how to reproduce the test
4. **Interpretation** — what result would warrant revisiting the decision

Re-runs should be done when:
- A new model family is released (Claude 5, etc.)
- A model within the current family is significantly upgraded
- The test results feel inconsistent with observed production behaviour

Record new baselines in `results/` with a datestamped filename.

---

## Decisions under test

| Test | Decision | Baseline | Revisit if... |
|------|----------|----------|---------------|
| [`integrate-level1/`](integrate-level1/README.md) | L1 focused three-way classifier (SYNTHESISE / INTEGRATE / NOTHING) beats multi-way mapped prompt | 9/10 correct (haiku, 2026-03-20) | Score drops below 9/10 or SYNTHESISE/INTEGRATE boundary degrades → tune prompt |
| [`integrate-level2/`](integrate-level2/README.md) | L2 focused three-way classifier (CREATE / UPDATE / NOTHING) beats multi-way mapped prompt | 7/9 correct; cases 2 & 3 are known hard cases (haiku, 2026-03-20) | Cases 2 and 3 start failing differently, or new failure modes appear → retune |
| [`integrate-level3/`](integrate-level3/README.md) | L3 EDIT/SPLIT decision uses note body only (draft excluded from classification) | 4/4 correct after fix; EDIT execution compresses to 60–66% (haiku/opus, 2026-03-20) | SPLIT fires incorrectly on off-topic drafts → draft may need re-introducing |
| [`gather/`](gather/README.md) | 5-signal fusion with weights body=0.45, bm25=0.27, activation=0.18, step_back=0.05, hyde=0.05 | R@10=0.667, MRR=0.844 (held-out n=60) | Retune weights with new model; compare R@10 |
