# Integration Quality Strategy

A design document for testing, diagnosing, and improving the quality of the
Form → Gather → Integrate pipeline. Covers known failure modes, the algorithmic
approaches available to address them, and the testing framework needed to
develop the system empirically.

---

## 1. Philosophy

Integration quality cannot be assessed analytically. The LLM's decisions at
each step are influenced by the full state of the corpus, the activation graph,
the specific paper content, and the accumulated history of prior ingestions. A
system that looks correct in isolation can fail in ways that are invisible until
a particular combination of note state and incoming content is reached.

This means **measurement infrastructure determines development velocity**. The
speed at which we can detect, diagnose, and fix failures — without introducing
regressions elsewhere — is the binding constraint on quality improvement.

A secondary constraint is **prompt brittleness under multi-class decisions**.
When a single prompt classifies between many operations, tuning to improve one
class shifts probability mass to others. Fixes cause regressions. The system
stabilises poorly. This is not a deficiency in any particular prompt; it is a
structural property of the architecture. The algorithmic and testing approaches
must account for it.

Development here is empirical, not theoretical. The right posture is:

- Design the algorithm to localise failure modes (changes to one decision cannot
  propagate to others)
- Build test infrastructure that covers multiple granularities (individual
  decisions, single-paper integrations, accumulation dynamics)
- Tune against ground truth, not intuition

---

## 2. Known Failure Modes

From analysis of the 2026-03-18 benchmark run (20 papers, 62 notes, 23 SPLITs).

### 2.1 SPLIT-induced duplicates

Three title collision groups were identified in the final store:

| Group | Notes | Creation mechanism |
|-------|-------|-------------------|
| Multi-Agent Architectures for Workflow Automation | z001, z029 | z029 = SPLIT of z001 (paper 8) |
| Memory and Context Management in LLM-Based Agents | z020, z022, z024 | z022 = SPLIT of z020 (paper 6); z024 = SPLIT of z001 (paper 7) |
| Evaluation Frameworks for Real-World Agent Deployment | z027, z042 | z042 = SPLIT of z027 (paper 13) |

All six are SPLIT second-halves, not independent CREATE operations. This is not
a Gather failure — the existing canonical note was never the retrieval target
being missed. The duplicate was produced by the SPLIT operation itself.

In every case, step1.5 correctly identified a conceptual distinction between the
note and the incoming draft. The failure was in step2 SPLIT execution: the
second half either received the same title and opening content as the first half
(z029, z042), or was titled by the draft's topic rather than the note's
separable thread (z024, z022).

### 2.2 Step1 UPDATE over CREATE

Step1 chose UPDATE for drafts that were conceptually adjacent but not the same
topic as the target note. This is the root trigger for all confirmed SPLIT
duplicates: if step1 had chosen CREATE for those drafts, step1.5 would never
have fired.

The Project Synapse draft (foundational hierarchical architectures, paper 8)
was routed into z001 (procedural memory for workflow automation) via UPDATE.
The OSC draft (cognitive orchestration, paper 7) was also routed into z001.
These are related but not the same topic.

Step1 is making this error inside a multi-way classification prompt where
SYNTHESISE, SPLIT, and EDIT are also competing for attention. The UPDATE/CREATE
distinction is not the focus of the prompt; it is one of several outcomes.

### 2.3 Step1.5 SPLIT when no separable thread exists

Step1.5 fires on note **size** after step1 chooses UPDATE. It then decides
between SPLIT and EDIT. EDIT is chosen when note and draft are about the same
topic (integrate by compression). SPLIT is chosen when they are about different
topics (extract a thread, create a new note).

For the problematic cases, note and draft ARE about different topics — so step1.5
correctly chooses SPLIT rather than EDIT. But the note, having been through
multiple prior SPLITs, has been whittled to a single coherent thread. There is
no second thread to extract. Step2 SPLIT then cannot find a clean boundary and
reproduces the existing framing in both halves.

The key structural problem: **step1.5 has no CREATE option**. If the note is
coherent and single-threaded, and the draft is about a different topic, the
correct answer is "step1 made the wrong call — this should have been CREATE."
Step1.5 cannot say this. Forced to choose between EDIT (wrong — topics differ)
and SPLIT (wrong — no separable thread), it picks SPLIT.

### 2.4 The masking effect

Several SPLIT second-halves that were poorly differentiated at creation
subsequently received UPDATEs from later papers, diverging them from the
original. These do not appear as duplicates in the final store but were
transiently duplicates. The confirmed visible duplicates (z022, z024, z042)
are specifically those that received no subsequent writes.

The true rate of poor SPLIT quality is therefore higher than 4 of 23 SPLITs.
The visible duplicates are the ones that were unlucky enough to not be corrected
by later ingestion. This makes the problem harder to measure from end-state
inspection alone.

### 2.5 Multi-way prompt brittleness

The current step1 prompt classifies between CREATE, UPDATE, EDIT, SPLIT,
SYNTHESISE, and NOTHING in a single pass against the full k20 cluster.
All operations and all cluster notes compete for the model's attention
simultaneously.

This architecture makes localised tuning impossible. Adjusting the prompt to
improve CREATE/UPDATE discrimination changes the model's calibration for
SYNTHESISE and SPLIT simultaneously. Empirical prompt iteration under this
constraint is whack-a-mole: fixing one failure mode predictably causes
regressions elsewhere.

---

## 3. Root Cause Chain

For SPLIT-induced duplicates, the failure chain is:

```
Step1:   multi-way classification, conceptually adjacent draft → UPDATE
         (should have been CREATE; UPDATE chosen because the full
         option space dilutes the CREATE/UPDATE discrimination)

Step1.5: Large note + different-topic draft → SPLIT
         (EDIT rejected because topics differ; SPLIT chosen as
         lesser wrong; no CREATE option available)

Step2:   SPLIT executes on a coherent single-threaded note → two
         halves with the same content; no clean boundary to cut on
```

The root is at step1. Fixing the UPDATE/CREATE discrimination directly would
prevent the cascade. The step1.5 SPLIT/EDIT decision and the step2 execution
quality are secondary failure points that would also benefit from improvement,
but fixing the root removes the primary trigger.

---

## 4. Algorithmic Approaches

A menu of approaches to the multi-class decision problem. These are not
mutually exclusive; the expected path uses several in combination.

### 4.1 Hierarchical decomposition / decision tree (primary)

Replace the single multi-way step1 prompt with a tree of focused decisions.
Each node addresses one question with limited options:

```
Level 1:  Full k20 visible. Primary question: SYNTHESISE or proceed?
            SYNTHESISE — draft spans multiple notes meaningfully; create bridge
            INTEGRATE    — pass identified cluster to level 2
            NOTHING    — available as an exit if draft is already fully covered;
                         rare in practice, not a primary decision axis
          → Activation recorded here against the identified cluster,
            regardless of which operation ultimately fires

Level 2:  CREATE or UPDATE?
          → Show the cluster identified by level 1 (~4 notes on average)
          → The currently broken decision; most important to fix

Level 3:  SPLIT or EDIT?
          → Classification: show target note ONLY (draft removed — see below)
          → Execution: show target note + draft
          → Already implemented as step1.5; refined per model-tests/integrate-level3
```

**Level 3 refinements (from model-tests/integrate-level3):**

- **Classification**: draft removed from the step1.5 prompt entirely. The SPLIT/EDIT
  decision is based solely on the note's internal structure — whether it contains
  two separable threads. Showing the draft caused false positives: when the draft
  was off-topic, the model saw "topics differ" and chose SPLIT on a coherent
  single-threaded note. Draft is passed through to step 2 but not shown at
  classification. (4/4 correct after fix.)

- **EDIT step 2**: label changed from "context only — do not add its content" to
  "integrate new insights from the draft." Trusts that step 1's UPDATE routing
  means the draft belongs in the note. Cross-topic draft content (e.g., when L2
  makes an incorrect UPDATE decision) is woven in as a bridging insight.
  (All EDIT cases 60–66% compression of original — healthy range.)

- **SPLIT step 2**: rewritten to partition the original note's two threads rather
  than keep note 1 intact and derive note 2 from the draft. The old "the second
  is the newly separated topic" framing was read as "create note 2 from the draft
  content," producing 144% combined bloat. The new framing makes explicit that
  both notes are partitions of the original content. (Case 2: 144% → 119%.)

**NOTHING at level 1**: available as an exit route, not a primary decision
axis. Fires rarely (once observed across 20 papers). The LLM can select it
when the draft is already fully covered, but the prompt frames level 1 as
SYNTHESISE-or-proceed rather than as a three-way choice.

**Activation at level 1**: activation recording is decoupled from the
CREATE/UPDATE decision and moved to level 1. Level 1 has already identified
the relevant cluster; recording co-activation there is sufficient regardless
of what level 2 ultimately decides. Level 2 does not need to carry activation
responsibility.

**Level 2 cluster size**: in practice the model selects a cluster of ~4 notes
from k20 at level 1, not 20. Level 2 therefore sees ~4 focused notes, not the
full retrieval set. Reducing further to a single top note (4→1) has marginal
focus benefit and risks missing that the draft is a better UPDATE target for
note 3 than note 1. Showing level 1's full cluster at level 2 is the right
default.

**Why this addresses the whack-a-mole problem**: decisions at each node are
structurally localised. A change to the CREATE/UPDATE prompt cannot causally
affect the SYNTHESISE/NOTHING prompt — they are separate calls with separate
test suites. Failure modes stop interacting.

**Independent calibration**: each node can be tuned against its own
ground-truth test set without affecting the others. This is the testing
complement to the architecture fix.

### 4.2 Hard pre-filtering before LLM calls

Some decisions are deterministic and should never reach the model:

- Empty corpus → always CREATE
- Note body below size threshold → step1.5 never fires (SPLIT/EDIT not
  considered; the accumulation trigger is absent)
- Embedding similarity between draft and top candidate above a high threshold
  → strong UPDATE prior; optionally skip level 2

Reducing the LLM's option space with deterministic rules means probability mass
is not wasted on dominated options.

### 4.3 Independent calibration per binary node

The model-tests pattern (already used for form granularity, integration
decisions, edit-split step1.5) applied to each node in the decision tree.
For each node: build a ground-truth labelled dataset of (note, draft, cluster)
→ expected operation; measure accuracy; iterate the prompt against that dataset
only. Changes at one node do not contaminate measurements at others.

### 4.4 Confidence-gated fallback

At each binary node, when confidence falls below a threshold, default to the
safer operation:

- UPDATE over CREATE (an unnecessary UPDATE is recoverable; a missed CREATE
  creates a duplicate)
- EDIT over SPLIT (over-compression is recoverable; a bad SPLIT creates a
  persistent duplicate)

Low confidence signals a genuinely ambiguous case. Conservative defaults fail
more gracefully than arbitrary low-confidence choices.

### 4.5 Constitutional critique pass

Generate a decision, then issue a second short call: "Here is the decision and
reasoning — identify any flaw in this classification." Reduces systematic
errors by giving the model a chance to catch its own mistakes. Most valuable
at the CREATE/UPDATE node since that is where the cascade originates. Less
expensive than full double-classification because the critique prompt is short.

### 4.6 Self-consistency / majority vote

Run a binary node at temperature > 0 N times and take the majority. Reduces
variance on boundary cases at the cost of N× API calls. Probably only worth
applying at the SPLIT/EDIT node, given the high downstream cost of a bad SPLIT
(persistent duplicate, requires curation to resolve).

### 4.7 Embedding-space pre-filtering for CREATE/UPDATE

**Status: Not viable for this corpus. Do not implement.**

Analysis of §4.7 cosine similarity data across the full 20-paper run
(82 drafts, 325 T scores, 979 F scores) shows no clean threshold exists:

| Threshold | T miss rate | F notes eliminated |
|-----------|-------------|-------------------|
| 0.40 | 3.4% | 12.6% |
| 0.45 | 9.2% | 31.7% |
| 0.50 | 19.7% | 57.5% |
| 0.55 | 35.1% | 79.6% |

To eliminate 80% of F notes requires a threshold that misses 35% of gold
targets — not a workable trade-off at any threshold.

**Why the distributions overlap so heavily:** T mean = 0.579, F mean = 0.487,
gap ≈ 0.09. 65 of 80 drafts (81%) have at least one F note scoring above their
lowest T note. The overlap zone [0.45–0.60] contains 51% of T scores and 47%
of F scores — this is the normal operating range of the retrieval system.

**Why the lowest T scores are structurally correct:** The 11 T scores below
0.40 are all SYNTHESISE or cross-domain UPDATE targets — notes that are
conceptually relevant but lexically distant from the draft (e.g. the Trilemma
note at 0.341 for a last-mile delivery paper; Procedural Memory at 0.323 for a
graph query paper). These are exactly the cases where multi-signal retrieval
earns its value. A cosine pre-filter would miss the most interesting routing
decisions in the system.

**What actually works:** The +12.5pp R@10 gain from the five-signal blend over
body-only embedding (architecture-decisions.md §2) comes from differentiating
within this overlap zone — activation, BM25, step_back, and HyDE lift gold
notes that body cosine alone cannot separate. Pre-filtering would reduce input
to these signals, not complement them.

The original framing — using cosine as a prior to frame the CREATE/UPDATE
binary — remains theoretically sound but empirically unnecessary: L2 already
receives a small cluster (3–7 notes) from L1, which is sufficient focusing
without an additional cosine anchor.

---

## 5. Testing Framework

Three complementary layers targeting different granularities of failure. They
are not alternatives — accumulation failures are invisible to layer 1 and 2;
prompt brittleness is hard to detect in layer 3.

### Layer 1: Node-level unit tests (model-tests pattern)

One test suite per binary node in the decision tree. Ground-truth labelled
cases: `(note, draft, cluster) → expected operation`. Each suite is:

- **Fast**: a single LLM call per case, no store setup
- **Isolated**: changing the CREATE/UPDATE prompt cannot affect the SPLIT/EDIT
  test results
- **Calibration-focused**: the goal is to tune each binary to a known accuracy
  against representative cases

Build these **before** implementing the full decision tree so each node has its
harness from day one. The existing model-tests for `edit-split-step15` and
`integration-decisions` are directly extensible to cover the new tree nodes.

Labelling ground truth: use the known failure cases from the 2026-03-18 run
(papers 7, 8, and 13 triggering the bad SPLITs) as negative examples, and
confirmed correct decisions from the same run as positive examples.

### Layer 2: Baseline integration tests

A fixed-corpus integration test suite. The baseline is the current
`zettel_20260318_142629` store minus the duplicate notes — approximately 56
notes with real embeddings, real activation graph, and realistic semantic
diversity from 20 papers.

**What the baseline provides**: a mature store in which some notes are likely
at a point of criticality — large, highly activated, having been through
multiple SPLITs — ready to be pushed over the edge by the right incoming paper.
This is not a stable resting state; it is a store with realistic supersaturation
in places, which gives the integration tests coverage of accumulation-sensitive
behaviours without requiring a full sequential replay.

Identifying "hot" notes: notes that are large (body length), highly connected
(activation edge count), or have been through multiple SPLITs. Once cluster
logging is in place (added 2026-03-19), notes that consistently appear as
`top_id` across diverse gathers are the high-activation candidates. Currently
requires manual audit.

**Test design**: for each hot note, select one or two papers expected to
interact with it — papers that cover closely related but not identical topics.
Run those papers against the baseline, verify the expected operations fire.

**Limitations**: cannot reproduce accumulation dynamics (behaviours that emerge
from N papers of sequential state build-up). Cannot test the exact conditions
that produced z029, because that required z001 in a specific post-whittling
state that the baseline may not replicate exactly.

**Baseline maintenance**: when a full ingestion run produces a qualitatively
better store, promote the new store as the baseline. This should be an explicit
decision, not automatic, because promotion invalidates existing test intuitions.

### Layer 3: Sequential trajectory validation

Per-paper state snapshots: after each of the 20 development papers, capture the
full `(store_dir, index)` state. This enables:

- **Rewind and replay**: modify a prompt, replay from paper N, observe forward
  trajectory changes
- **Regression detection**: after fixing paper 8's behaviour, replay papers 1–7
  to confirm the fix hasn't invalidated earlier correct decisions
- **Accumulation observation**: watch note state evolve paper by paper; identify
  exactly when a note reaches criticality

**Path dependency caveat**: fixing paper N creates a new trajectory for papers
N+1 onwards. The store state after a fix is different from the original, so
papers N+1+ will behave differently. "Rewind and retry" means committing to a
new forward trajectory, not isolated per-paper correction. Budget for replaying
N+1 through 20 after any significant fix before declaring the fix complete.

**Per-paper audit criteria**: not the full 8-step INSPECTION.md (designed for
a completed store). A lightweight per-paper profile:
- Operation count and distribution (expected profile per paper type)
- Any new notes with titles duplicating existing notes
- Confidence distribution (low confidence on core operations warrants inspection)
- Spot-check of any SPLIT second-halves produced

**Build order**: build this layer last. The sequential workbench is the most
expensive to implement and maintain. Build it after the decision tree is stable
and layer 1 and 2 tests are passing — at that point, the sequential layer is
hunting accumulation-specific bugs that the other layers cannot catch.

---

## 6. Convergence Consideration

Empirical prompt tuning alone does not converge on a general solution. It
converges on a solution for the test distribution — the specific papers, in the
specific order, against the specific baseline, that the tests cover. This is
the whack-a-mole dynamic: fix a failure on the visible test cases; an equivalent
failure appears on unseen cases.

The decision tree architecture changes this. Binary decisions at each node are
structurally isolated — a fix at one node cannot shift probability mass at
another. Each node can be driven toward high accuracy on its own test set
independently. The system stabilises node by node rather than oscillating across
the full operation space.

**The decision tree is the mechanism of convergence. The testing infrastructure
is the evidence of convergence.** Implement the structural fix before building
out the full test suite; tests written for the single-prompt architecture will
need to be redesigned when the tree is implemented.

---

## 7. Implementation Sequence

Order matters to avoid throwaway work:

1. ~~**Design the decision tree**~~ **COMPLETE** — nodes, information at each
   level, and operations at each level are agreed (see §4.1).

2. ~~**Model-tests for each binary node**~~ **COMPLETE** — test harnesses built
   and baselined for all three nodes:
   - L1 (SYNTHESISE/INTEGRATE/NOTHING): 10-case suite, current 9/10, candidate 9/10.
     Handoff validation added: when L1 returns INTEGRATE, its `target_note_ids`
     includes the expected UPDATE target in 100% of checkable cases (5/5 current,
     2/2 candidate).
   - L2 (CREATE/UPDATE/NOTHING): 9-case suite with realistic 3–4 note clusters
     simulating L1's filtered output. Current 5/9, candidate 7/9. Cases 2 and 3
     (realistic cluster triggers over-synthesis) are known hard cases.
   - L3 (EDIT/SPLIT): existing `edit-split-step15` harness. 3/3 correct.

3. ~~**Implement the decision tree**~~ **COMPLETE** (v0.2.0 + activation fix) —
   `integrate_phase` now runs L1 → L2 → step 1.5 (L3) → step 2. STUB removed
   from routing. `IntegrationResult` carries `l1_target_ids`; activation is
   recorded at L1 for all writing operations (CREATE, UPDATE, EDIT, SPLIT) using
   the L1 cluster, not the L2 targets. EDIT and SPLIT previously recorded no
   activation. All 205 unit tests pass.

4. **Baseline integration test suite** — audit the current store for hot notes;
   select targeting papers; build the single-paper test harness against the
   deduplicated baseline.

5. **Sequential workbench** — `model-tests/ingestion-harness/` — snapshot
   infrastructure, per-paper analysis tooling. CLI: `--next`, `--paper N`,
   `--rewind N`, `--context [N]`, `--status`, `--list`. Starts from empty
   store; takes full `notes/ + index.db` snapshot after each paper. Per-paper
   report covers operation distribution, store deltas, confidence distribution,
   SPLIT ratios, duplicate title detection, and §4.7 cosine similarity data.
   `--context` emits store state + embedding-similarity pre-sort of notes for
   human/Claude pre-run prediction (one embed call, no LLM). Full DEBUG log
   saved per paper (anthropic/httpx/voyageai loggers suppressed). Log noise
   reductions applied: 5 per-signal gather lines → 1 combined `gather.signals`
   line; `integrate.execute` DEBUG removed, `body_len` promoted to INFO
   `integrate.complete`. Self-contained: all 20 paper texts and metadata copied
   into the harness directory.

---

## 8. Open Questions

- **Which notes in the baseline are at criticality?** Requires manual audit.
  Easier once cluster logging produces a history of which notes surface most
  frequently as retrieval targets. Logging was added 2026-03-19; the next run
  will provide this data.

- **Does the baseline have enough supersaturation for layer 2 to cover
  accumulation behaviours?** Unknown without an audit. If not, a small number
  of targeted sequential checkpoints may be needed as a supplement to layer 2.

- ~~**Does cluster stability hold across operation types?**~~ **Validated** —
  Handoff validation (L1 model-test, 7/7 INTEGRATE cases) confirmed that L1's
  `target_note_ids` includes the expected L2 UPDATE target in 100% of cases.
  The cluster L1 passes to L2 is appropriate for CREATE/UPDATE targeting.
  No divergence between SYNTHESISE-focused and UPDATE-focused cluster selection
  was observed in the test population.

- **Will the decision tree produce different SYNTHESISE rates?** The original
  single-pass architecture produced ~19 SYNTHESISEs per 20-paper run. L1's
  isolated SYNTHESISE/INTEGRATE/NOTHING decision may calibrate differently.
  Whether any shift is desirable requires evaluation against note quality
  criteria on the next full ingestion run.

- **What is the step1.5 size threshold, and should it be tuned as part of the
  fix?** A better CREATE/UPDATE decision at level 2 reduces how often level 3
  fires in the wrong context. The threshold may need recalibration after the
  tree is in place.
