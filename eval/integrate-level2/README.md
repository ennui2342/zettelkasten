# Model Test: Level 2 — CREATE vs UPDATE vs NOTHING

## The decision

Level 2 is the second node of the integration decision tree. It receives a pre-filtered cluster from level 1 (~4 notes) and decides:

- **UPDATE** — the draft extends an existing note on the same topic; select the single best target note. Fires step 1.5 if the target is large.
- **CREATE** — the draft introduces a new topic not covered by any note in the cluster. Create a new note.
- **NOTHING** — the draft is already fully covered by the cluster. No action needed.

This is the "currently broken" decision in the design: the original single-pass step 1 prompt over-fires UPDATE/SYNTHESISE for adjacent-but-distinct topics and cannot recognise NOTHING.

## Usage

```bash
uv run --env-file .env python eval/integrate-level2/run.py             # all cases
uv run --env-file .env python eval/integrate-level2/run.py --only update
uv run --env-file .env python eval/integrate-level2/run.py --only create
uv run --env-file .env python eval/integrate-level2/run.py --only nothing
```

Results are saved to `results/run_<timestamp>.md`.

## Prompts compared

- **Current** — `_STEP1_PROMPT` from `prompts.py` (multi-way: CREATE/UPDATE/EDIT/SPLIT/SYNTHESISE/NOTHING). Output mapped: UPDATE/EDIT/SPLIT→UPDATE; CREATE/STUB/SYNTHESISE→CREATE; NOTHING→NOTHING.
- **Candidate** — `prompts/level2.txt` — focused three-way: UPDATE / CREATE / NOTHING with "prefer CREATE when in doubt" tiebreaker.

## Test data

9 cases drawn from `eval/integration-decisions/` ground truth. Data is self-contained in `data/` (13 notes).

Each case uses a 3–4 note cluster simulating what level 1 would pass from the full k20 retrieval: the primary target plus plausible near-misses.

| # | Draft | Expected | Cluster (primary + near-misses) |
|---|-------|----------|---------------------------------|
| 1 | `testing-effect-draft.md` | UPDATE → z20260314-002 | testing-effect + spaced-repetition + encoding |
| 2 | `spaced-repetition-draft.md` | UPDATE → z20260314-001 | spaced-repetition + testing-effect + spaced-learning + forgetting-curve |
| 3 | `external-memory-draft.md` | UPDATE → z20260314-003 | external-memory + encoding + retrieval-cues |
| 4 | `interleaved-practice-split-draft.md` | UPDATE → z20260314-007 | practice-strategies + distributed-practice + spaced-repetition |
| 5 | `working-memory-split-draft.md` | UPDATE → z20260314-008 | memory-systems-overview + encoding + retrieval-cues + context-dependent |
| 6 | `generation-effect-create-draft.md` | CREATE | encoding + testing-effect + massed-practice (no generation-effect note yet) |
| 7 | `sleep-consolidation-stub-draft.md` | CREATE | spaced-learning + spaced-repetition + forgetting-curve + memory-systems-overview |
| 8 | `massed-practice-nothing-draft.md` | NOTHING | massed-practice + practice-strategies + distributed-practice + spaced-repetition |
| 9 | `forgetting-curve-nothing-draft.md` | NOTHING | forgetting-curve + spaced-repetition + spaced-learning + massed-practice |

## Baseline

*Run: 2026-03-20 | Model: claude-haiku-4-5-20251001*

| # | Case | Expected | Current | Candidate |
|---|------|----------|---------|-----------|
| 1 | testing-effect gap-fill | UPDATE | UPDATE ✓ | UPDATE ✓ |
| 2 | spaced-repetition mechanism | UPDATE | CREATE ✗ | UPDATE ✓ |
| 3 | external-memory gap-fill | UPDATE | CREATE ✗ | UPDATE ✓ |
| 4 | interleaved-practice (→SPLIT) | UPDATE | UPDATE ✓ | UPDATE ✓ |
| 5 | working-memory (→SPLIT) | UPDATE | UPDATE ✓ | UPDATE ✓ |
| 6 | generation-effect CREATE | CREATE | CREATE ✓ | UPDATE ✗ |
| 7 | sleep-consolidation CREATE | CREATE | CREATE ✓ | CREATE ✓ |
| 8 | massed-practice NOTHING | NOTHING | UPDATE ✗ | UPDATE ✗ |
| 9 | forgetting-curve NOTHING | NOTHING | UPDATE ✗ | NOTHING ✓ |

**Current: 5/9 | Candidate: 7/9**

### Failure analysis

**Cases 2 and 3 — current fires CREATE/SYNTHESISE with multi-note clusters.** The current prompt sees testing-effect + spaced-repetition + retrieval-cues in the cluster and identifies a bridging insight, returning SYNTHESISE (mapped to CREATE). This is the documented "over-synthesis" failure mode: it confuses "adjacent notes + filling a gap" with "bridge-worthy connection". The candidate correctly routes both to UPDATE.

**Case 6 (generation-effect CREATE) — candidate fires UPDATE.** The encoding note has a documented gap ("what activities produce deep vs. shallow processing?") and the generation-effect draft answers that exact question. The candidate reads this as UPDATE filling a gap; the ground truth is CREATE because generation effect is a substantial topic warranting its own note. The candidate's "prefer CREATE when in doubt" tiebreaker does not fire because the model is confident (0.92). This is a genuine ambiguity: both readings are defensible. Accepted as a known borderline case.

**Case 8 (massed-practice NOTHING) — both prompts fire UPDATE.** With practice-strategies and distributed-practice in the cluster, both prompts notice slight framing differences between the draft and the existing note (emphasis on metacognitive failure vs. empirical evidence) and decide merging would strengthen the note. The ground truth is NOTHING because no new claims are introduced. This is the key remaining weakness of the candidate: it cannot reliably distinguish "same content, different wording" (NOTHING) from "new emphasis worth integrating" (UPDATE) when a multi-note cluster is present.

### Assessment

The candidate correctly handles the primary failure mode of the current prompt (over-synthesis when multiple notes are in cluster, cases 2–3) and correctly identifies NOTHING for the clear coverage case (case 9). The two shared or novel failures are either a genuine borderline (case 6) or a hard sub-distinction within UPDATE/NOTHING (case 8).

**Decision: candidate prompt is fit for purpose.** 7/9 on a realistic multi-note cluster test is a meaningful improvement over 5/9. Promote to the level-2 step in the decision tree when implemented (step 3). The NOTHING/UPDATE boundary (case 8) is worth monitoring in production.
