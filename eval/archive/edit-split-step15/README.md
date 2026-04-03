# Model Test: Step 1.5 — Large-Note Refinement

## The decision

When step 1 (classify) returns `UPDATE` for a note exceeding `NOTE_BODY_LARGE` (8 000 chars), a dedicated **step 1.5** call is made before step 2. Step 1.5 uses a focused two-option prompt (EDIT or SPLIT) to refine the decision.

**Why it exists:** A `max_tokens=4096` UPDATE on a 21 000-char note truncates output silently. The real question before triggering that truncation is: should this note be compressed (EDIT) or structurally divided (SPLIT)? We couldn't get this decision reliably from a modified step 1 prompt alone.

**The alternative tested (Option A):** Add EDIT operation and a `[LARGE: N chars]` annotation to the step 1 prompt, instructing the model not to choose UPDATE for large notes. Cheaper (no extra call), but found unreliable.

## Baseline

*Run: 2026-03-17 | Model: claude-haiku-4-5 (fast_llm)*

| Case | Draft | Target note | Option A | Step 1 + 1.5 |
|------|-------|-------------|----------|--------------|
| 1 | Compositional Evaluation | Evaluating Agentic AI Systems (21 004 chars) | SYNTHESISE | EDIT |
| 2 | Indirect Prompt Injection | Memory Poisoning & Security (21 571 chars) | UPDATE | EDIT |
| 3 | Emergent Role Specialisation | Multi-Agent LLM Systems (21 095 chars) | SYNTHESISE | EDIT |

**Conclusion:** Option A unreliable (2/3 cases wrong — SYNTHESISE rather than EDIT). Step 1.5 needed.

## Re-run

```bash
# From repo root
uv run --env-file .env python eval/edit-split-step15/run.py
```

The script compares Option A (modified step 1 only) against the current step 1 + step 1.5 approach for each test case.

## Interpret results

| Outcome | Action |
|---------|--------|
| Option A produces EDIT/SPLIT for all 3 cases | Remove step 1.5 from `integrate.py` — save one LLM call per large-note integration |
| Option A still fails on 1+ cases | Keep step 1.5 |
| Step 1 + 1.5 starts failing | Investigate prompt changes; check if NOTE_BODY_LARGE threshold needs adjusting |

## Test data

`data/` contains the three large notes from the benchmark-innovation corpus:

| File | Title | Size |
|------|-------|------|
| `z20260317-013.md` | Benchmarking and Evaluating Agentic AI Systems | 21 004 chars |
| `z20260317-005.md` | Memory Poisoning, Multi-Agent Security, Non-Determinism… | 21 571 chars |
| `z20260317-001.md` | Multi-Agent LLM Systems: Architecture, Memory, and Collaborative Reasoning | 21 095 chars |

These are snapshots from 2026-03-17. They remain fixed across re-runs so results are comparable.
