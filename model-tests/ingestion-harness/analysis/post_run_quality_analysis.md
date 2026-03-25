# Post-Run Quality Analysis: 20-Paper Ingestion Run

**Completed:** 2026-03-23
**Covers:** Synthesised note quality, hub note compression, §4.7 cosine similarity

---

## 1. Synthesised Note Quality

Three SYNTHESISE operations across the run: z20260322-003 (Trilemma), z20260322-011
(Provenance Governance), z20260323-007 (Phase Transitions). All three assessed
against the key criteria: emergent vs genetic, does it articulate something no
individual paper states, does it give retrieval traction.

### z20260322-003 — The Agent System Trilemma

**Quality: Excellent.**

The core claim — that co-design of architecture and memory is economic necessity,
not engineering elegance — is derived from bridging z20260322-001 (architectures)
and z20260322-002 (procedural memory) through the trilemma constraint. Neither
source paper states this directly.

The key synthesis mechanism: memory *shifts the trilemma frontier* rather than
choosing a point on it. Orchestrator-level and task-agent-level memory attack
different trilemma facets (efficiency vs cost respectively) — a specific,
testable claim that couldn't be written from domain knowledge alone.

Retrieval traction is high. Any future paper about efficient multi-agent
deployment, cost of frontier model pipelines, or memory as amortisation will
land here usefully. The architectural overfitting section (optimal architecture
matches task complexity, not maximum capability) is particularly retrievable.

### z20260322-011 — Provenance-Enforced Governance

**Quality: Excellent.**

Bridges z20260322-010 (scientific reasoning multi-agent) and the security note
(z20260322-007) through the co-design principle. The triple coupling insight —
that the same architectural decisions simultaneously determine performance,
governability, and security — is something neither source states.

The specific synthesis: the observation that dense legitimate memories suppressing
poisoned entries (from the security note) and audit-grade provenance requirements
(from the governance paper) are *the same structural property*, not competing
concerns. This is the kind of cross-paper connection the store was designed to
produce.

The closing argument — governance and security constraints *reshape the feasible
region* of the trilemma rather than adding new dimensions — is elegant and
precise. The risk is that it sounds more principled than it is empirically
grounded; the three concrete mechanisms that precede it anchor it sufficiently.

Retrieval traction is high for institutional design problems, AI governance
papers, and adversarial security in LLM systems.

### z20260323-007 — Phase Transitions in Hierarchical Aggregation

**Quality: Good to very good, with a body quality caveat.**

The synthesis direction is correct: bridging formal λ-parameterised phase
transition theory to the three empirical communication regimes documented in
z20260323-006 is genuinely cross-paper. The key insight — effective ensemble
size ≈ 1/ρ, imposing an irreducible ceiling that horizontal scaling cannot
breach — is powerful and non-obvious.

**Body quality concern:** This is the most "PhD thesis" note in the store. The
mathematical machinery (the ρ-shared correlation model, the aggregation map
formula, the closed-form recursion) is largely compressed from the source paper
rather than derived from cross-paper synthesis. The note reads more like a dense
paper summary with a bridging opening than a note whose entire body derives
insight from cross-paper juxtaposition.

The note will likely be EDITed as the corpus grows. The risk is that compression
flattens the λ/ρ framing to "diversity of agents matters" — losing the specific
mechanism (ρ as a binding constraint, not just a design consideration). The EDIT
prompt will need to preserve the 1/ρ effective ensemble size claim specifically.

### Cross-note pattern

All three SYNTHESISE notes share a structural feature: they derive a *constraint
that reshapes the feasible region* of the design space, rather than adding a
new dimension. The Trilemma note says co-design is the principal lever. The
Governance note says governance constraints eliminate large regions of the design
space that naive optimisation would otherwise explore. The Phase Transitions note
says correlation ρ imposes an irreducible ceiling that scaling can't breach.

This is not genetic memory. The corpus has developed a perspective: a theory of
binding constraints in agent system design. The convergence across three
independently triggered SYNTHESISE operations is evidence that the store is doing
what it was designed to do — accumulating a viewpoint rather than just storing
facts.

---

## 2. Hub Note Compression: EDIT Quality Assessment

Three hub notes assessed (current state vs paper-10 snapshot):

### z20260322-001 — Multi-Agent Architectures (10,091 chars)

**Verdict: Clear improvement.**

Paper-10 state was a framework catalogue: system classes (handcrafted/partially
automated/fully automated) with framework-specific descriptions arranged by
paradigm. The insight was buried in examples.

Paper-20 state has been restructured through repeated UPDATEs and EDITs into a
principled taxonomy: centralised vs decentralised families with empirical
comparison; topology section with formal fan-in constraints ($n \cdot m \leq W$,
$\eta^L$ decay); design primitives (sub-agent autonomy, planning strategy,
context organisation). The topology analysis connects empirical observation
(star degrades at scale) to a theoretical bound. Framework-specific details are
preserved but subordinated to structure.

This is the best compression outcome of the three. EDIT reorganised content
from catalogue to taxonomy — the kind of structural improvement that human
editors do deliberately but the pipeline achieved through accumulation.

### z20260322-002 — Procedural Memory (7,228 chars)

**Verdict: Clean controlled distillation.**

Paper-10 was already well-structured but verbose — each memory type (working,
episodic, semantic, procedural) received multiple concrete implementation
paragraphs including specific tools (ChromaDB, SQLite). The RAG section was long.

Paper-20 has compressed the memory type descriptions, losing the ChromaDB/SQLite
specifics but adding the synthesis insight: the four memory types are
"multiplicative rather than additive." The RAG section is roughly 40% shorter
while the key claim about role-aware routing is preserved and actually
articulated more cleanly.

What was removed (implementation specifics, verbose examples) has lower
retrieval value than what was added (multiplicative framing, cleaner principle
statement). The co-design principle at the end is tighter. The note is more
transferable — less tied to specific tools, more about the structural principle.

### z20260322-018 — Foundations of LLM-Based Autonomous Agents (8,609 chars)

**Verdict: Mixed — narrative quality traded for encyclopaedic coverage.**

Paper-10 state (~4,500 chars) had a well-constructed explanatory arc. Key
passage: *"The transition from passive generation to active agency was catalyzed
by prompting techniques that unlocked latent reasoning capabilities..."* — a
genuine account of *why* the shift happened.

Paper-20 state has grown to 8,609 chars through 5+ UPDATE/EDIT cycles. The
Memory section (~1,600 chars) is new and valuable. The Tool Use section has
expanded to 5 paradigms including VLA robotics (Gemini Robotics, VLM-GroNav).

The opening has been compressed to a definitional framing (POMDP loop) that
is functional but loses the explanatory thread. The VLA/robotics content is the
most at-risk: it's conceptually distant from the note's original scope
(foundations of reasoning and planning) and will function as noise when this
note is retrieved for a reasoning/planning query.

**Recommendation:** This note should be actively split before its next UPDATE,
not wait for the threshold to trigger organically. Natural split point:
- Note 1: Single-agent foundations (reasoning, planning, memory, orchestration)
- Note 2: Action interfaces and deployment (tool paradigms, VLA/robotics,
  computer-use, observability, safety)

The paper-10 version covered Note 1; the paper-20 version has stretched into
Note 2's territory without clean separation. The split would preserve the
explanatory quality of the foundations section while giving the action interfaces
content its own note with a sharper scope.

### Overall pattern

EDIT is functioning as designed — controlled distillation, not lossy degradation.
Core arguments survive across all three notes. In two of three cases (001, 002),
compression actively improved the note by forcing structural clarification. The
failure mode to watch for is the 018 pattern: EDIT compressing the explanatory
framing of early sections to make room for encyclopaedic coverage of new content,
producing a note that is comprehensive but less useful as a retrieval target for
conceptual queries.

---

## 3. §4.7 Cosine Similarity Analysis

**Full write-up:** see integration-quality-strategy.md §4.7 (updated with
decision: not viable).

**Summary findings:**

- 82 drafts, 325 T scores, 979 F scores across 20 papers
- T mean = 0.579, F mean = 0.487, distributions massively overlap
- 65 of 80 drafts (81%) have F notes scoring above their lowest T note
- No threshold exists that provides useful pre-filtering without unacceptable
  T miss rate
- The 11 T scores below 0.40 are all structurally justified SYNTHESISE or
  cross-domain bridge targets — exactly the cases where multi-signal retrieval
  earns its value
- The highest F scores (0.67–0.75) are hub notes (001, 006, 016) with broad
  semantic coverage that score high by embedding but were correctly routed to
  more specific targets by L2

**Core implication:** The +12.5pp R@10 from five-signal fusion over body-only
embedding is earned specifically by differentiating within the 0.45–0.60 overlap
zone where cosine alone cannot separate gold from non-gold. Pre-filtering would
reduce input to those signals. The architecture decision is validated.

---

## 4. SPLIT Quality: z20260322-006 Two-Split Trajectory

z20260322-006 "Benchmarks and Evaluation for Agentic AI Systems" was split twice —
at papers 17 and 19 — and grew back after each split. This makes it the clearest
test case for whether SPLIT is functioning as intended or masking a structural
accumulation problem.

### Paper-17 SPLIT (2511.10949 — agent safety)

**Pre-split state:** 12,050 chars. Content conflated: CLASSic evaluation
dimensions, benchmark catalogue (task performance, multi-agent, instruction-following),
and architectural findings from the enterprise benchmark study.

**Split boundary:** The pipeline identified a safety/security evaluation thread
as separable from the main benchmark-and-methodology body. The safety thread
became z20260323-009 "Evaluation Frameworks and Metrics for Agent Safety"
(4,539 chars): adversarial benchmarks, fine-grained safety metrics, component-level
attribution for multi-agent pipelines.

**Assessment: Reasonable but not a clean partition.** z20260322-006 after the
split was 10,218 chars — barely smaller than before. The SPLIT effectively
extracted a safety appendix rather than dividing the note into two equal
conceptual halves. Combined ratio 121% (14,637/12,050) confirms the execute step
added content in the process. Confidence 0.78 was appropriate: the boundary was
real but minor.

The more fundamental problem: the paper-17 SPLIT didn't address the core
accumulation pressure. "Benchmarks and evaluation" is an inherently broad attractor
topic — any paper touching agent evaluation has legitimate reason to update this
note. Splitting out safety evaluation addresses the symptom (one content thread)
without touching the cause (topic breadth).

### Paper-19 SPLIT (2512.06196 — enterprise benchmarks)

**Pre-split state:** ~10,218 chars (grown back through paper-18 UPDATE after
the paper-17 split).

**Split boundary:** The pipeline identified a methodology/what-to-measure thread
vs a benchmark-catalogue/empirical-performance thread. The catalogue became
z20260323-011 "Benchmark Suites and Empirical Performance Landscape for Agentic
AI" (4,539 chars): specific benchmark descriptions (GAIA, SWE-bench, AgentBench,
etc.), enterprise deployment results (peak: 70.8% on simpler workflows, 35.3%
on complex), model stability coefficients (o3-mini CV: 143.7%, GPT-4.1: 27.0%).

**Assessment: Semantically cleaner.** The paper-19 split is a genuine conceptual
partition: z20260322-006 now owns *how to evaluate* (CLASSic dimensions, LLM-as-judge
methodology, efficiency metrics, failure analysis protocol), while z20260323-011
owns *what benchmarks exist and what they measure*. These are meaningfully
separable retrieval targets. Lower confidence (0.72) accurately reflected the
harder boundary — methodology and catalogue often appear together, and the
pipeline was right to be less certain.

Combined ratio reportedly 130% — higher bloat than paper-17. The execute step
appears to have generated methodology framing for 006 rather than purely
partitioning existing content.

### Post-split accumulation (paper 20)

After both splits, paper 20 added to z20260322-006 again: a new "Long-Horizon
Task Benchmarks" section (AppWorld, OfficeBench, Multi-Objective QA) and
"Relevance Horizons and Lookahead Tuning" section. z20260322-006 current body
is approximately 5,800 chars — well below the 8,000-char threshold, but the
accumulation pattern is visible.

The current See Also section of z20260322-006 is diagnostic: it points to
z20260323-009 (safety — first split child), z20260323-011 (benchmark catalogue —
second split child), and two hub notes (001, 002). The note has shed two children
and is re-growing at its centre. This is characteristic of a **topic attractor**:
a note whose scope is defined at exactly the granularity that captures something
from every paper in a domain.

### Cross-split structural assessment

The two splits have produced a reasonable note family:
- z20260322-006: evaluation methodology and dimensions (CLASSic, LLM-as-judge, efficiency metrics, failure analysis)
- z20260323-009: safety-specific evaluation (adversarial benchmarks, attribution)
- z20260323-011: benchmark catalogue + empirical performance landscape

These three notes have distinct identities and would serve different retrieval queries
well. The SPLIT operations produced value — they are not failed compressions.

The issue is trajectory, not current state. z20260322-006 will likely grow back
to threshold within 5 more papers (any paper touching evaluation methodology,
context window efficiency, or long-horizon benchmarks will land here). The next
SPLIT decision will be harder: the methodology thread itself may need to be
divided (evaluation design vs evaluation execution vs evaluation reporting), but
that is a much finer-grained distinction that L3 will struggle to make cleanly.

**Forward recommendation:** Watch the "Long-Horizon Task Benchmarks" section
specifically. If it accumulates independently across papers (papers on memory
management, context compression, or planning all have evaluation components),
that section will be the natural next split point — creating a note on
evaluation methodology for context-heavy / long-horizon tasks, distinct from
the CLASSic dimensions framing for general agentic evaluation.

---

## 5. z20260322-015: Low Activation Despite Topic Centrality

z20260322-015 "Inter-Agent Communication Protocols, Interoperability Standards,
and Zero-Trust Security for Autonomous Agents" has total activation weight 16.0
— lower than every note in the top 15 by outbound weight. Hub notes (001: 199.2,
002: 183.3, 003: 163.7) have 10–12× more activation. The question is why.

### Activation data

The note has 10 activation edges, highest weights to 001 (3.0) and 002 (3.0),
meaning it co-appeared with those notes in retrieval events exactly 3 times
each. It has never been updated since its creation at paper 7 — the body has
been 10,420 chars from creation through paper 20. All cosine-similarity
appearances from papers 8–20 are F (non-target), except:

- Paper 9: T:0.499 for draft "Inter-Agent Communication and Cognitive Modeling"
  — correctly routed, L1 target
- Paper 15: T:0.565 for draft "Agentic AI and LLM-Based Autonomous Agents"
  — L1 target in a broad agentic survey paper

All other appearances score F in the 0.33–0.59 range, outcompeted by hub notes
with higher cosine scores and existing activation edges.

### Why this is not a pipeline failure

The note's topic is genuinely orthogonal to the 20-paper corpus. The corpus
concentrated on:

- Architecture patterns (orchestration, tool use, planning) → hub 001, 018
- Memory and learning → hub 002
- Evaluation and benchmarks → 006, 009, 011
- Security within systems → 007, 009
- Reasoning and communication within teams → 016, 010

z20260322-015 covers **inter-organizational protocol standards**: ACP's four
layers (transport/semantic/negotiation/governance), Decentralized Identifiers,
Verifiable Credentials, Proof-of-Intent, federated discovery via DHTs,
reputation ledgers. This vocabulary appears nowhere else in the corpus. There
are no other notes in adjacent semantic space to provide activation boosting,
and subsequent papers didn't touch protocol standards.

The activation signal is working correctly. Activation accumulates through
co-retrieval; a note that is never co-retrieved with others (because its topic
is disjoint) will not accumulate activation. The signal correctly reports that
this note has not been a habitual retrieval companion for other notes in this
corpus — because the papers ingested so far have not required it.

### Path dependency in action

The note was created fully formed from paper 7 (two drafts about the ACP protocol
were combined at creation — the note started at 10,420 chars). Papers 8–20 then
continued in a different direction: architecture benchmarks, reasoning systems,
planning, context management, evaluation frameworks. None of those papers had
a reason to retrieve z20260322-015 except incidentally, and incidental retrieval
(appearing in the k=20 cluster without being selected as L1 target) does not
generate activation edges.

This is path dependency as described in `analysis/path_dependency.md`: the
ingestion order shaped which notes became hubs and which became specialists. A
reversed order would likely produce different hubs; in this run, 015 arrived
after the hub network was already established and its topic was orthogonal to
the network's direction.

### Retrieval risk

The concern is not the activation deficit itself — it's whether the embedding
signal alone is sufficient to retrieve 015 when a relevant future paper arrives.
Cosine scores for correctly typed drafts (paper 9's "Inter-Agent Communication"
draft) were only 0.499 — close to the hub note scores for generic drafts. The
note's title is specific and accurate ("Inter-Agent Communication Protocols...
Zero-Trust Security") but long, and it uses vocabulary (DIDs, VCs, PoI, DHTs,
reputation ledger) that may not appear in future paper drafts that are about
the same concept but frame it differently (e.g. "federated agent ecosystems" or
"trustless multi-organization AI deployment").

**The embedding will succeed** if future papers use protocol/identity/zero-trust
vocabulary. **It may miss** if future papers approach the same problem from an
ecosystem design angle without the protocol-specific terms.

### What would improve retrievability

The context field in the frontmatter (2–3 sentence semantic positioning) is the
correct lever here. z20260322-015's context field should be audited to ensure
it captures the *problem* the note addresses (cross-organization agent trust,
capability negotiation across framework boundaries, decentralized identity for
autonomous agents) rather than just describing the ACP protocol. Notes that
name the problem generically retrieve better than notes that name only the
solution specifically.

No pipeline change is indicated. This is a content quality check, not a
retrieval signal failure.

---

## 6. NOTHING Drought: Only 1 in 88 Operations

One NOTHING in 88 total operations (1.1%). The question is whether this reflects
a pipeline bias toward over-routing drafts to UPDATE rather than correctly
discarding subsumed content.

### The single NOTHING case

Paper 11 (2512.01939), draft "The draft note provides a high-level overview of
LLM-based autonomous agents...", confidence **0.92**. L1 targets: z20260322-018,
z20260322-001, z20260322-002.

The reasoning is clean: this was a *survey draft* — a high-level overview of
agent components (brain/memory/planning/tools) and development history, derived
from a survey paper. The cluster already covered every dimension in greater
depth. No novel insight, no new framework, no connection that didn't already
exist. NOTHING was the correct call, made at high confidence.

### Why the drought is expected, not alarming

**The corpus is young.** At 20 papers with ~30 notes, topic saturation is low.
A NOTHING fires when a draft's content is *entirely* subsumed by existing notes.
In a young corpus where most topic areas are sparsely covered, this is rare —
most drafts add at least incremental content to their targets.

**Form pre-divides papers into focused drafts.** A paper about "multi-agent
systems" produces 4–6 focused topic notes (architecture, evaluation, memory,
tool use), not one generic overview. A focused note almost always adds at least
incremental content to its target. Survey/overview drafts — the natural source
of NOTHING — are rare when Form is extracting focused topical content.

**The paper selection was breadth-first.** The 20 papers were chosen to cover
the domain broadly, not to add redundant depth. A corpus of 20 papers all about
the same architecture pattern would produce many NOTHINGs; these papers
consistently introduced new angles.

### The borderline zone: confidence-0.72 UPDATEs

No operations had confidence below 0.70. Seventeen (19%) fell in the 0.70–0.79
range. The most structurally interesting: z20260322-001 received 3 UPDATEs at
conf=0.72 across papers 2, 12, and 17:

- **Paper 2**: taxonomy of architecture classes (handcrafted/partially automated/
  fully automated) — new conceptual framing, not subsumed
- **Paper 12**: homogeneity/heterogeneity formalism and formal equivalence
  results — new analytical depth, not subsumed
- **Paper 17**: topology analysis with formal fan-in constraints ($n \cdot m \leq W$,
  $\eta^L$ decay) — new formal bounds, not subsumed

All three were genuine incremental additions. The low confidence reflected
overlap with existing content, but the delta was real. In a fully saturated
corpus these might eventually become NOTHING; in the current corpus they were
correctly routed to UPDATE. The 001 note's improvement from catalogue to taxonomy
(noted in §2) is the accumulated product of these additions.

z20260322-006 received 7 UPDATEs — the highest count of any note. This is the
topic-attractor pattern documented in §4, not a routing problem. Each UPDATE
added evaluation methodology content from a different angle (benchmarking,
LLM-as-judge, safety metrics, enterprise deployment); none was subsumed by
prior UPDATEs because the corpus lacked enough pre-existing evaluation depth
to exhaust the topic.

### What NOTHING is testing

NOTHING fires at L2, after L1 has already returned INTEGRATE. For L2 to return
NOTHING, it must find that a draft adds nothing over the specific notes L1
selected. This is a harder test than it sounds: if L1 selects 3 hub notes that
are each 6,000+ chars of dense content, L2 must determine that a focused 1,500-char
draft is fully covered. The paper-11 NOTHING succeeded because the draft was
explicitly a high-level overview against three exhaustive specialist notes.

The pipeline is not over-routing. UPDATE is the correct action for incremental
additions; NOTHING requires genuine subsumption.

### The NOTHING/EDIT interaction: a hidden accumulation cost

There is a cost to borderline UPDATEs that isn't visible when evaluating either
operation in isolation:

1. A borderline UPDATE adds marginal content to a hub note
2. The hub note grows back past the 8,000-char threshold
3. Step 1.5 fires EDIT — compresses the whole note, discarding content
4. Net result: the marginal content was added, the compression was triggered,
   and the EDIT discards content that predated the marginal addition

If the borderline UPDATE had been NOTHING, the note stays at its post-EDIT
compressed state — no compression triggered, no existing content at risk.
The UPDATE that "should have been" NOTHING doesn't just fail to add value;
it triggers a compression event that costs value.

This asymmetry is most acute for notes that have already been EDIT-compressed.
The first EDIT typically improves a note (removes verbose examples, improves
structure — the 001 and 002 outcomes in §2). But a second EDIT on an
already-optimised note compresses structural insights rather than verbose
scaffolding. The 018 pattern — narrative quality traded for encyclopaedic
coverage — is partly an artefact of this cycle.

**Design implication**: NOTHING's threshold should arguably be dynamic. A note
that has been EDIT-compressed once should require a *higher* content delta
before accepting a new UPDATE than a note that has never been compressed —
because the cost of triggering another compression is higher for an already-
compressed note. This is not currently modelled: L2's UPDATE/NOTHING decision
is blind to the target note's compression history.

### Forward monitoring

The expected NOTHING rate will increase as the corpus matures:

- **Survey and review papers** ingested in later phases will produce more NOTHING
  — they restate existing knowledge rather than advancing it
- **Topic saturation** in architecture, memory, and evaluation will make hub notes
  exhaustive enough to subsume incremental additions in those areas
- **Expected rate at ~50 papers**: 5–15% NOTHING (up from 1.1% at 20 papers).
  If still <5% at 50 papers, the L2 UPDATE threshold may be too permissive —
  the model is choosing to add content where NOTHING would be correct.

Trigger for investigation: NOTHING rate < 3% at 50 papers, OR any NOTHING at
confidence < 0.70 (would indicate L2 was genuinely uncertain, not confident in
subsumption).

---

## 7. Late-Paper Retrievability (Papers 14–20)

The benchmark design requires late-ingested notes to be retrievable as distinct
targets. The failure mode is content from papers 14–19 absorbed into early hub
notes via UPDATE, leaving no discrete representation.

### Operation pattern papers 14–20

| Paper | Creates | Updates to old hubs | New distinct identity? |
|-------|---------|---------------------|----------------------|
| 14 | 0 | 018, 016, 006 | **No** |
| 15 | 0 | 018, 001, 002, 006 | **No** |
| 16 | 1 (SYNTHESISE→007) | 001 | **Yes** — z20260323-007 |
| 17 | 1 (CREATE→008) | 001, SPLIT 006 | **Yes** — z20260323-008 |
| 18 | 0 | z20260323-009 (split child) | **No** |
| 19 | 1 (CREATE→010) | 016, SPLIT 006 | **Yes** — z20260323-010 |
| 20 | 2 (CREATE→012, 013) | 006 | **Yes** — z20260323-012, 013 |

Papers 14, 15, and 18 produced no new note identity. Their content was entirely
absorbed into existing notes. This is the partial failure mode: benchmark tasks
testing content specifically from those three papers must retrieve it from inside
large hub notes rather than from a dedicated note.

Papers 14–15 are the most significant: two consecutive papers added only to
pre-existing hubs (018, 001, 002, 006). Content from these papers has no
retrieval handle of its own.

### Late note activation and post-creation retrievals

| Note | Created | Activation | Post-creation retrievals | Status |
|------|---------|------------|--------------------------|--------|
| z20260323-001 | p11 | 36.8 | 4 | Strong |
| z20260323-002 | p11 | 23.8 | 3 | Good |
| z20260323-006 | p13 | 66.5 | 7 | Very strong |
| z20260323-007 | p16 | 31.0 | 3 | Good |
| z20260323-008 | p17 | 22.0 | 2 | Decent |
| z20260323-009 | p17 split | 23.0 | 2 | Decent |
| z20260323-010 | p19 | 17.0 | 0 | Unproven (too new) |
| z20260323-012 | p20 | 13.0 | 0 | Unproven (too new) |
| z20260323-013 | p20 | 15.0 | 0 | Unproven (too new) |
| z20260323-003 | p11 | 5.0 | 0 | Stranded specialist |
| z20260323-004 | p12 | 4.0 | 1 | Weak |
| z20260323-005 | p13 | 11.9 | 1 | Weak |
| z20260323-011 | p19 split | 7.0 | 1 | Weak |

z20260323-003 "Empirical Software Engineering Research Methods" is a second
stranded specialist: created at paper 11, never retrieved as a target, 5.0 total
activation. The topic (empirical software engineering methodology) is genuinely
orthogonal to the corpus's subsequent trajectory. Same pattern as z20260322-015.

### Benchmark implications

**Avoid as benchmark task sources**: papers 14, 15, 18. Their content has no
discrete retrieval target. A well-functioning retrieval system *might* surface
the right section of z20260322-018 or z20260322-001, but that tests different
capability than retrieving a dedicated note.

**Good late-paper benchmark candidates**: papers 16, 17, 19, 20. Each created
at least one distinct note. Notes from papers 19–20 need more corpus exposure
before activation builds — the embedding signal alone must carry retrieval for
now.

**Unproven late notes (010, 012, 013)**: not failed, just untested. They have
reasonable body sizes (6,500–7,000 chars) and distinct topics. Activation will
build as later papers retrieve them.

---

## 8. Quick Checks: STUBs, Epistemic Links, See-Also Integrity

### STUBs
None. No notes of `type: stub` exist in the final store. The ANALYSIS_GUIDE
flags any STUB as a pipeline failure — this check passes cleanly.

### Epistemic links
Three `supersedes` links exist in the final store:

| Note | Supersedes | Assessment |
|------|-----------|------------|
| z20260323-008 Adversarial Attacks | z20260322-007 (Security) | **Plausible** — more comprehensive treatment |
| z20260323-012 Context Engineering | z20260322-002 (Procedural Memory) | **Wrong** — adjacent topic, not supersession |
| z20260323-004 Workflow Optimization | z20260322-001 (Multi-Agent Architectures) | **Wrong** — subfield note cannot supersede hub |

The ANALYSIS_GUIDE records the first epistemic link as a milestone. It has
arrived — but two of the three appear to be misidentified. The execute prompt
appears to be treating "my topic extends and partly replaces some ideas in this
hub note" as supersession, when the intended semantics are a direct claim
conflict resulting in the target becoming `type: refuted`.

**Pipeline integrity gap**: none of the three superseded notes are marked
`type: refuted`. The execute step wrote the `supersedes` field into the
superseding note's frontmatter but did not flip the target. The two processes
are not coupled.

**Two actions indicated**:
1. Correct the two misidentified links — z20260323-012 and z20260323-004 should
   have `links: []`
2. Tighten the execute prompt's definition of `supersedes`: it should fire only
   when a new note directly contradicts and replaces a claim in the target —
   not when a new note covers adjacent territory more thoroughly.

### See-also link integrity
One broken link remains: `[[Retrieval-Augmented Generation, GraphRAG, and
Retrieval Corpus Governance]]` in z20260322-012 — the hallucinated title
documented at paper 20. The self-cleaning hypothesis (future EDITs would repair
it) has not been borne out: this note was not EDIT-compressed in papers 14–20,
so the link persisted. All other see-also links use ID-anchored format
`[[id|Title]]` and resolve correctly.

The broken link count (1) is below the trigger threshold (>3 after 10 papers).
No action required; continue monitoring.

---

## Summary and forward implications

1. **SYNTHESISE is working at the right level.** All three SYNTHESISE notes
   derive principles no individual paper states. The cross-note pattern
   (binding constraints / reshaping feasible regions) suggests the corpus is
   accumulating a coherent perspective.

2. **EDIT compression is reliable but has a failure mode.** The 001 and 002
   outcomes show compression can improve note quality. The 018 outcome shows the
   risk: narrative quality traded for coverage breadth, with out-of-scope content
   added without clean separation. Active SPLITs (before threshold triggers) may
   be needed for notes whose scope has drifted.

3. **Cosine pre-filtering is not viable.** The distributions are too overlapping
   and the most important routing decisions (cross-domain synthesis) have the
   lowest T scores. Recorded as a closed decision in integration-quality-strategy.

4. **z20260322-018 needs a proactive split.** Before the next UPDATE targeting
   this note, split it at the single-agent foundations / action interfaces
   boundary. Waiting for the 8,000-char threshold will produce a third EDIT cycle
   rather than a clean split.

5. **z20260322-006 is a topic attractor, not a broken note.** Both splits
   produced real value (safety evaluation and benchmark catalogue are now
   separable retrieval targets). The accumulation will continue; the next
   natural split point is the "Long-Horizon Task Benchmarks" thread if it grows
   independently across papers.

6. **z20260322-015's low activation is path dependency, not pipeline failure.**
   The note's specialist topic (protocol standards, zero-trust identity) is
   orthogonal to the corpus trajectory. Its embedding will retrieve it correctly
   when a relevant paper arrives; the activation deficit is structural and
   expected. See §5.

7. **NOTHING drought (1/88) is expected for a young, breadth-first corpus.**
   The Form step's focused extraction and the 20 papers' breadth mean most
   drafts add genuine incremental content. NOTHING rate should naturally rise
   to 5–15% at ~50 papers as hub notes saturate. Monitor: < 3% at 50 papers
   warrants reviewing the L2 UPDATE threshold. See §6.
