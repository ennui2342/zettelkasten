# Model Tests

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
| [`edit-split-step15/`](edit-split-step15/README.md) | Step 1.5 needed to route UPDATE→EDIT/SPLIT on large notes | Option A (modified step 1 prompt) drifted to SYNTHESISE in 2/3 cases; step 1.5 reliable | Option A correctly produces EDIT/SPLIT in all cases → remove step 1.5 |
| [`retrieval-signals/`](retrieval-signals/README.md) | 5-signal fusion with weights body=0.45, bm25=0.27, activation=0.18, step_back=0.05, hyde=0.05 | R@10=0.667, MRR=0.844 (held-out n=60) | Retune weights with new model; compare R@10 |
| [`integration-decisions/`](integration-decisions/README.md) | Two-step integration reliable enough for automated writes | 100% correct, 100% consistent across 14 cases × 3 runs (claude-opus-4-6) | Any case failing or inconsistent — investigate prompt/model changes |
| [`form-granularity/`](form-granularity/README.md) | Single-shot Form wins over stepped (CARPAS count-first eliminated) | Single-shot: 4 topics, correct; Stepped: 2 topics, too coarse | Stepped produces better granularity → re-evaluate prompt design |
