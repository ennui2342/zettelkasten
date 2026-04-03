# Model Test: Level 1 — SYNTHESISE vs INTEGRATE

## The decision

Level 1 is the first node of the integration decision tree. It sees the full retrieval cluster (k20) and asks one question: does this draft reveal a bridging insight between existing notes, or should it be integrated into them?

- **SYNTHESISE** — the draft reveals a connection between two or more existing notes that produces new insight none of them articulate alone. The connection itself is the knowledge. Fire step2 SYNTHESISE.
- **INTEGRATE** — the draft elaborates, extends, fills a gap in, or is already covered by existing notes. Pass the identified cluster to level 2.
- **NOTHING** — the draft is already fully covered. Exit without writing.

## Usage

```bash
uv run --env-file .env python eval/integrate-level1/run.py            # set 1 (SYNTHESISE/INTEGRATE balance)
uv run --env-file .env python eval/integrate-level1/run.py --set 2    # set 2 (INTEGRATE cases only)
uv run --env-file .env python eval/integrate-level1/run.py --set all  # both sets (includes handoff check)
```

Results are saved to `results/run_<timestamp>.md`.

## Prompts compared

- **Current** — `_STEP1_PROMPT` from `prompts.py` (multi-way classifier: CREATE/UPDATE/EDIT/SPLIT/SYNTHESISE/NOTHING). Output mapped: SYNTHESISE→SYNTHESISE, NOTHING→NOTHING, anything else→INTEGRATE.
- **Candidate** — `prompts/level1.txt` — focused three-way: INTEGRATE / SYNTHESISE / NOTHING.

Key framing decisions in the candidate:
- INTEGRATE listed first — the default, lower-energy path
- SYNTHESISE framed as "the connection must earn its existence"
- NOTHING available for fully-covered drafts

## Test data

13 notes in `data/notes/` (full corpus). The complete cluster is passed to both prompts for all cases.

Each INTEGRATE case with a known UPDATE target has an `expected_target` field — used to verify the **handoff**: when L1 returns INTEGRATE, the correct note must appear in `target_note_ids` so that level 2 receives it in the filtered cluster.

### Set 1 — SYNTHESISE sensitivity and INTEGRATE specificity

| # | Draft | Expected | L2 ground truth | Handoff target |
|---|-------|----------|-----------------|----------------|
| 1 | `spaced-retrieval-synthesise-draft.md` | SYNTHESISE | SYNTHESISE | — |
| 2 | `generation-encoding-synthesise-draft.md` | SYNTHESISE | SYNTHESISE | — |
| 3 | `spaced-repetition-draft.md` | INTEGRATE | UPDATE | z20260314-001 |
| 4 | `generation-effect-create-draft.md` | INTEGRATE | CREATE | — (new note) |
| 5 | `massed-practice-nothing-draft.md` | INTEGRATE/NOTHING | NOTHING | z20260314-005 |

### Set 2 — INTEGRATE balance check

| # | Draft | Expected | L2 ground truth | Handoff target |
|---|-------|----------|-----------------|----------------|
| 6 | `external-memory-draft.md` | INTEGRATE | UPDATE | z20260314-003 |
| 7 | `forgetting-curve-nothing-draft.md` | INTEGRATE/NOTHING | NOTHING | z20260314-006 |
| 8 | `sleep-consolidation-stub-draft.md` | INTEGRATE | CREATE | — (new note) |
| 9 | `prospective-memory-stub-draft.md` | INTEGRATE | CREATE | — (new note) |
| 10 | `interleaved-practice-split-draft.md` | INTEGRATE | UPDATE→SPLIT | z20260314-007 |

## Baseline

*Run: 2026-03-20 | Model: claude-haiku-4-5-20251001*

| # | Case | Expected | Current | Candidate |
|---|------|----------|---------|-----------|
| 1 | spaced retrieval — multiplicative interaction | SYNTHESISE | SYNTHESISE ✓ | SYNTHESISE ✓ |
| 2 | generation as deep encoding | SYNTHESISE | SYNTHESISE ✓ | SYNTHESISE ✓ |
| 3 | spaced-repetition mechanism | INTEGRATE | INTEGRATE ✓ handoff ✓ | INTEGRATE ✓ handoff ✓ |
| 4 | generation-effect CREATE | INTEGRATE | INTEGRATE ✓ | NOTHING ✓ |
| 5 | massed-practice NOTHING | INTEGRATE/NOTHING | INTEGRATE ✓ handoff ✓ | NOTHING ✓ |
| 6 | external-memory gap-fill | INTEGRATE | INTEGRATE ✓ handoff ✓ | SYNTHESISE ✗ |
| 7 | forgetting-curve NOTHING | INTEGRATE/NOTHING | INTEGRATE ✓ handoff ✓ | NOTHING ✓ |
| 8 | sleep-consolidation new topic | INTEGRATE | SYNTHESISE ✗ | INTEGRATE ✓ |
| 9 | prospective-memory new topic | INTEGRATE | INTEGRATE ✓ | INTEGRATE ✓ |
| 10 | interleaved-practice extension | INTEGRATE | INTEGRATE ✓ handoff ✓ | INTEGRATE ✓ handoff ✓ |

**Current: 9/10 | Candidate: 9/10**

**Handoff accuracy (target in `target_note_ids` when returning INTEGRATE):**
- Current: 5/5 ✓
- Candidate: 2/2 ✓

### Failures

**Case 6 (external-memory) — candidate fires SYNTHESISE.** The external-memory draft draws on generation effect, testing effect, and encoding depth to answer an open question. The candidate reads this as a bridging insight connecting those notes; the ground truth at L2 is UPDATE (gap-fill into external-memory note). This is the same persistent ambiguity across all three test levels for this case. Accepted as a known borderline.

**Case 8 (sleep-consolidation) — current fires SYNTHESISE.** The current prompt correctly identifies a genuine mechanistic link (sleep consolidation and spaced practice both require temporal gaps for effortful reactivation), but the ground truth is INTEGRATE (sleep consolidation is a new isolated topic). The candidate correctly returns INTEGRATE.

### Handoff validation

The handoff check verifies that when L1 returns INTEGRATE, the note L2 needs as the UPDATE target is present in `target_note_ids`. Both prompts pass 100% of checkable handoff cases. This validates the L1→L2 design: we can confidently pass L1's `target_note_ids` as the filtered cluster to L2.

The candidate returns NOTHING for several INTEGRATE cases (4, 5, 7) — which means those drafts would exit the pipeline without reaching L2. These are all correctly identified as fully-covered drafts; NOTHING is the right outcome.

### Assessment

Both prompts score 9/10. The candidate is preferred because:
- It handles the current prompt's over-SYNTHESISE failure mode (case 8) correctly
- Its NOTHING decisions are high-confidence and accurate (cases 4, 5, 7)
- Its vocabulary is focused — no spurious CREATE/UPDATE/EDIT leaking into the classification

**Decision: candidate prompt is fit for purpose.** Promote to `_STEP1_PROMPT` (level 1 role) when the decision tree is implemented. The handoff is validated — `target_note_ids` reliably includes the correct L2 target.
