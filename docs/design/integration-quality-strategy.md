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
            Proceed    — pass identified cluster to level 2
            NOTHING    — available as an exit if draft is already fully covered;
                         rare in practice, not a primary decision axis
          → Activation recorded here against the identified cluster,
            regardless of which operation ultimately fires

Level 2:  CREATE or UPDATE?
          → Show the cluster identified by level 1 (~4 notes on average)
          → The currently broken decision; most important to fix

Level 3:  SPLIT or EDIT?
          → Show target note + draft only
          → Already implemented as step1.5; refine in this context
```

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

Use cosine similarity between the draft embedding and the top candidate note
embedding as a prior before the LLM CREATE/UPDATE decision:

- High similarity → strong UPDATE prior; present to model with UPDATE framing
- Low similarity → strong CREATE prior; present to model with CREATE framing
- Middle range → present as an open binary choice

This gives the model an anchor and reduces the chance of the decision being
swayed by irrelevant cluster content.

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

2. **Model-tests for each binary node** — build the test harness and label
   ground-truth cases before touching the implementation. Validates the design
   early and provides a baseline accuracy measurement.

3. **Implement the decision tree** — replace the single step1 prompt. The
   step1.5 logic (SPLIT/EDIT) becomes level 3 of the tree with a refined prompt.

4. **Baseline integration test suite** — audit the current store for hot notes;
   select targeting papers; build the single-paper test harness against the
   deduplicated baseline.

5. **Sequential workbench** — snapshot infrastructure, per-paper analysis
   tooling. Build once the tree is stable and layers 1 and 2 are passing.

---

## 8. Open Questions

- **Which notes in the baseline are at criticality?** Requires manual audit.
  Easier once cluster logging produces a history of which notes surface most
  frequently as retrieval targets. Logging was added 2026-03-19; the next run
  will provide this data.

- **Does the baseline have enough supersaturation for layer 2 to cover
  accumulation behaviours?** Unknown without an audit. If not, a small number
  of targeted sequential checkpoints may be needed as a supplement to layer 2.

- **What is the step1.5 size threshold, and should it be tuned as part of the
  fix?** Currently fixed. A lower threshold means step1.5 fires more often on
  smaller notes; a higher threshold means notes grow larger before any action
  is taken. The right value may depend on the decision tree's CREATE/UPDATE
  accuracy — a better step1 reduces how often step1.5 fires on bad UPDATEs.

- **Does cluster stability hold across operation types?** Level 1 passes its
  identified cluster (~4 notes) to level 2 on the assumption that the notes
  relevant for SYNTHESISE evaluation are the same notes relevant for
  CREATE/UPDATE targeting. The SYNTHESISE question favours complementary angles;
  the UPDATE question favours overlapping content — these could surface different
  parts of k20. If they diverge significantly in practice, level 2 may be
  working with the wrong notes. Validate by running both levels in isolation on
  the same papers and comparing which notes each would have selected.

- **Will the decision tree produce different SYNTHESISE rates?** The current
  architecture produces ~19 SYNTHESISEs per 20-paper run. A better-calibrated
  SYNTHESISE/not node may raise or lower this. Whether the shift is desirable
  requires evaluation against note quality criteria, not just operation counts.

- **What is the step1.5 size threshold, and should it be tuned as part of the
  fix?** A better CREATE/UPDATE decision at level 2 reduces how often level 3
  fires in the wrong context. The threshold may need recalibration after the
  tree is in place.
