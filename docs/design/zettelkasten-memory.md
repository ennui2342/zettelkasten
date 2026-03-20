# Zettelkasten Memory: Consolidation-Based Long-Term Memory for Agents

*Design exploration — revised after two literature passes (document decomposition; clinical NLP and meeting summarisation), 2026-03-14*

*For settled implementation decisions and their rationale, see [`architecture-decisions.md`](architecture-decisions.md). For spike outcomes and build status, see [`zettelkasten-implementation-plan.md`](zettelkasten-implementation-plan.md).*

---

## 1. The Problem with Distillation

aswarm's existing memory architecture covers three retrieval patterns well: ordered session history (`history`), typed key-value snapshots (`snapshot`), and planned similarity-ranked chunk retrieval (`document`). The compaction system extends `history` with a distillation pass — when a session exceeds a token threshold, the oldest turns are summarised and key facts are extracted to a long-term store.

Distillation is **append-only**. It extracts, condenses, and writes. The long-term store grows monotonically; nothing in it is ever revised in light of new information. A fact extracted six months ago sits beside a contradicting fact extracted last week, with no relationship between them.

This is the wrong model for genuine long-term knowledge. Human long-term semantic memory does not grow by accumulation — it grows by **consolidation**: active restructuring of existing knowledge in light of new experience. New information is not appended; it is *integrated*, revising what is already there, revealing relationships between previously unconnected ideas, and sometimes overturning beliefs previously held with confidence.

The goal of this document is to sketch a memory store type — tentatively `type: zettelkasten` — that implements consolidation rather than distillation.

---

## 2. Design Philosophy

Four principles constrain every design choice in this document. They are stated up front because they actively shape what is proposed and what is rejected.

### 2.1 The Bitter Lesson

Richard Sutton's "Bitter Lesson" (2019) observes that AI approaches which leverage general-purpose computation — rather than encoding human knowledge into system design — consistently win in the long run, even when the hand-crafted approaches initially appear superior. Methods that compensate for model weakness with engineering complexity become obsolete as models improve; methods that give capable models the right *representation* to reason over compound in value as models improve.

This is a design constraint, not a historical observation. Any mechanism proposed here that exists to compensate for current model limitations — complex retrieval pipelines, hand-crafted confidence update formulas, multi-stage engineering to extract meaning from text — should be treated as provisional and held lightly. The question to ask of every design choice is: *does this get better as models get better, or does it become unnecessary?*

Mechanisms that give models a richer, better-structured representation to reason over are Bitter-Lesson-resilient. Mechanisms that do reasoning *on behalf of* the model are not.

### 2.2 Agent Memory vs. Knowledge Retrieval Tool

The adjacent literature is dominated by sophisticated retrieval pipelines: bi-temporal knowledge graphs, multi-stage entity resolution, community detection algorithms, confidence update formulas applied to belief networks. These are impressive engineering, but they are building **knowledge retrieval tools** — external information systems that agents query. That is a different thing from **agent memory**.

The distinction matters. A knowledge retrieval tool is optimised for precision retrieval: given a query, return the most relevant information. Its intelligence is in the retrieval machinery. An agent's memory is optimised for giving the agent relevant context before it reasons: here is what you already know that bears on this situation. Its intelligence is in the representation — are the notes structured and linked such that an LLM reading them can reason effectively? As models become more capable, retrieval precision matters less (a capable model can synthesise across imprecise matches); note structure matters more (a capable model reasons better when the representation is clear).

The design target is a **filesystem of markdown files that the LLM makes sense of directly** — not a sophisticated information retrieval tool that the agent uses. The SQLite index exists to select *which* notes to show; the LLM does the reasoning over what it receives. The engineering should be in the representation, not the retrieval.

### 2.3 The Thousand Brains Principle

Jeff Hawkins' *A Thousand Brains* (2021) argues that the neocortex consists of ~150,000 cortical columns, each independently modelling the world using learned reference frames. Each column makes predictions about incoming sensory data, and when reality diverges from prediction, that column's model is updated. Learning is driven by prediction error — not by summarising everything that was observed, but by updating specifically where the model was wrong.

This principle directly shapes the integration pass (§6.3). The agent's Zettelkasten is the model; new episodes are incoming sensory data. The integration LLM receives the incoming draft alongside the existing cluster and asks: what does this episode contain that the existing knowledge does not already cover? Notes that confirm what was already known generate no revision. Notes grow from prediction error, not from volume.

This is also Bitter-Lesson-resilient: prediction quality improves with model capability, so better models generate less noise and higher signal in consolidation. The mechanism compounds, rather than becomes obsolete.

### 2.4 Eventual Coherence Over Per-Pass Correctness

The zettelkasten does not run in a clean room. Input material will be imprecise, inconsistently framed, and sometimes contradictory. Topic boundaries in fuzzy documents are genuinely indeterminate — not wrong to call differently on different passes, but genuinely ambiguous. Individual consolidation passes will produce imperfect integrations: thin stubs, missed connections, notes that will later need revision.

This is the expected operating mode, not a failure state.

The correctness guarantee is at the cluster level over time, not at the individual operation level. As more material covering the same topic accumulates and is consolidated, notes converge toward accuracy. A note that starts as a thin uncertain stub and develops through successive passes is the normal lifecycle. Confidence and stability scores reflect this explicitly — they grow with repetition, not with single-pass quality.

This principle has concrete design implications:
- The integration LLM should write tentative stubs rather than refusing to integrate uncertain content. An imperfect first representation is better than no representation.
- Optimising individual passes for deterministic precision — zeroing temperature on boundary detection, engineering multi-pass algorithms to force clean segmentation — is the wrong target. The system is robust to boundary imprecision because the same material re-enters via other documents and passes.
- Evaluation should measure cluster improvement over N passes on a body of material, not individual operation quality in isolation.
- The `stub` type and low confidence scores are first-class lifecycle states, not defects to be minimised.

This mirrors CLS theory: the neocortex does not integrate episodic memories perfectly on the first replay. It integrates them approximately and repeatedly until structure emerges.

---

## 3. Theoretical Grounding

### 3.1 Complementary Learning Systems

The most directly applicable neuroscience framework is **Complementary Learning Systems (CLS) theory** (McClelland, McNaughton, O'Reilly, 1995), which proposes that biological memory requires two structurally different systems operating at different timescales:

- **Hippocampus**: fast learning, stores specific episodes with high fidelity, high plasticity. It can encode a new experience in a single exposure without disrupting what is already stored.
- **Neocortex**: slow learning, extracts statistical regularities across many experiences, low plasticity. It resists rapid change precisely because rapid change would destroy the generalised structure it has built up.
- **Consolidation during sleep**: the hippocampus replays episodic memories to the neocortex, which integrates them gradually into its existing structure. The slow integration avoids "catastrophic interference" — overwriting existing cortical knowledge with new patterns.

The architectural parallel is direct:

| CLS | aswarm |
|---|---|
| Hippocampus | `history` store (fast, episodic, session-scoped) |
| Neocortex | Zettelkasten store (slow, semantic, global) |
| Sleep consolidation | Consolidation pipeline (scheduled or threshold-triggered) |
| Replay mechanism | Segment phase: decompose episodes into bounded units |

The key insight from CLS is that you cannot simply copy episodes into long-term memory — the integration must be slow and careful to avoid destroying existing structure. This justifies a dedicated consolidation pass rather than writing directly from the event stream.

### 3.2 Reconsolidation

A refinement of standard consolidation theory: when a stored memory is *retrieved*, it briefly becomes labile — open to modification — before being re-stabilised. This **reconsolidation window** is the moment at which existing memories can be updated in light of new information.

The gather+integration pass of the consolidation algorithm (§6.3) is the direct computational equivalent. Retrieving the cluster of related notes does not just read them — it opens a reconsolidation window. The integration pass can then revise, extend, or challenge those notes before they are written back. Retrieval and potential revision are coupled, as they are in biological memory. This is the mechanism. Nothing else needs to be added on top of it.

**Important naming disambiguation.** A-MEM (§3.7) uses the word "reconsolidation" for something different: after adding a new note, it retrieves the top-k neighbours and runs a lightweight LLM pass to update their `context` field, keywords, and tags. A-MEM calls this reconsolidation because retrieved neighbours are modified — but in the neuroscience sense, reconsolidation refers to the lability of the retrieved memory itself, not to housekeeping updates on neighbours. These are distinct operations:

- **Reconsolidation (neuroscience / this design):** the gather+integration pass opens a window in which retrieved notes can be substantively revised, extended, split, or merged in light of new evidence. This is the primary consolidation mechanism.
- **Context field evolution (A-MEM's usage):** after a note is written, a lightweight pass updates the `context` field of neighbouring notes to keep their semantic positioning current for future retrieval. This is an optional housekeeping step, not the consolidation event itself.

The two are occasionally conflated in discussion because both involve "updating notes after retrieval." The distinction matters: reconsolidation is the knowledge revision mechanism; context field evolution is a retrieval quality maintenance step. In the implementation, only the latter needs a separate pass — reconsolidation happens automatically as part of the integration operation.

### 3.3 Spreading Activation and Activation-Weighted Links

Collins and Loftus (1975) proposed that semantic memory is organised as a network where concepts are nodes and semantic relationships are weighted edges. Activation propagates through links, decaying with distance and time — this is the mechanism underlying priming, spreading retrieval, and associative recall.

**The critical distinction: citation links vs. activation-pattern links.** The original design assumed that links in the Zettelkasten — like Wikipedia inter-article links — would provide a useful spreading-activation substrate for cluster retrieval. Spike 4A refuted this: citation-style link traversal *degrades* retrieval quality, expanding clusters from 10 to 52 notes (depth=1) and 108 nodes (depth=2) at 15.6% precision on new nodes. The Wikipedia link graph short-circuits through hub articles (Memory, Working Memory, Long-Term Memory) that are cited by everything. Spike 4D confirmed via LLM-judged ground truth that 83% of integration-relevant notes missed by embedding have no link or tag signal at all — the connections the LLM makes are inferential and cross-domain, not encoded in the citation graph.

This eliminates one notion of spreading activation from the design. A different notion is more promising.

**Activation-pattern links.** Rather than recording citations (what an author thought was worth citing), the system could record *co-activation events*: which notes were retrieved together in the same integration window. These links encode something more useful — "was relevant in the same context as" — and emerge from the system's own integration judgements rather than from prior authors' choices.

After each integration event, the notes in the gather cluster co-activated in a reconsolidation window (§3.2). Notes that received a non-NOTHING operation were confirmed relevant; the co-retrieved notes that were not acted on may or may not be useful signal (see §11 H-new-B). The strength of co-activation links decays exponentially with time, following the ACT-R base-level activation equation (Anderson et al.):

```
activation_strength(A, B) = Σ_events exp(-λ · age_of_event)
```

where the sum is over all past integration events in which A and B co-activated. Future cluster retrieval then blends body embedding similarity with accumulated activation strength:

```
score(query, candidate) = α · body_sim + (1-α) · activation_strength(query, candidate)
```

This is self-organising and epistemically honest. The link graph that emerges reflects what the system has actually found useful — not what original authors cited or what an LLM speculates might be related. Inferential and cross-domain connections that embedding misses on first encounter accumulate activation weight as they recur across integration events. The knowledge base grows smarter about its own topology through use.

**Network theory.** The co-activation graph built from integration events is expected to exhibit small-world properties (Watts & Strogatz, 1998): high local clustering (notes in the same subdomain repeatedly co-activate) with short path lengths (occasional cross-domain integrations create long-range connections). This is the topology that makes spreading activation computationally efficient — dense local clusters with sparse hub connections. It contrasts with citation graphs, which tend toward scale-free topology (Barabási & Albert, 1999) with a few highly-cited hub articles that dominate traversal and dilute retrieval precision.

**The Temporal Context Model (TCM)** (Howard & Kahana, 2002) provides a finer-grained theoretical grounding. TCM proposes that retrieved items activate a temporal context vector representing the episode in which they were previously encountered. Retrieving item A reinstates the context that activates other items that shared A's integration window. This is the mechanism by which a co-activation graph would improve recall for inferential connections: the connection exists not in embedding space but in shared integration history. The decay function on co-activation strength is the computational analogue of TCM's contextual drift.

This design direction is validated in principle but unvalidated in practice. See §11 H-new-A and H-new-B, and Spike 5 in the implementation plan.

### 3.4 Piaget: Assimilation and Accommodation

Piaget's distinction between **assimilation** (new information absorbed into an existing schema without changing it) and **accommodation** (the schema is revised to fit information it cannot absorb) applies directly to the integration decision:

- **Assimilation**: the new concept fits an existing note — extend it, strengthen a link, raise confidence. Structure unchanged.
- **Accommodation**: the new concept reveals an existing note was wrong, incomplete, or conflating two ideas. Revise, supersede, or split. Graph restructured.

Distillation is pure assimilation — it never revises. Consolidation supports both.

### 3.5 Popper: Conjecture and Refutation

Popper's epistemology holds that knowledge grows not by accumulation but by conjecture and refutation. A new observation that contradicts an existing belief is not a problem to be suppressed — it is the mechanism by which the knowledge base improves.

This justifies the `contradicts` link type and confidence revision. Two notes that contradict each other can coexist as long as the contradiction is explicit and traversable. The knowledge base does not need to resolve every contradiction immediately — it needs to represent them faithfully.

### 3.6 Coherentism

The philosophical tradition of coherentism holds that a belief's epistemic status is determined by how well it coheres with the surrounding belief network. A belief in a dense, mutually supporting web is well-founded; an isolated or tension-generating belief is suspect.

The cluster-based integration decision implements this: "does this new concept cohere with its neighbourhood?" A concept cohering strongly with a dense, consistent cluster is integrated with high confidence. One that introduces tension gets lower confidence and explicit contradiction links.

### 3.7 A-MEM: Closest Prior Work

The closest existing system is **A-MEM** (Xu et al., 2025), which explicitly implements a Zettelkasten-inspired memory for LLM agents. A-MEM validates the core approach: 2x performance on multi-hop reasoning, 85–93% token reduction vs. full-history methods. The graph structure genuinely improves reasoning quality.

A-MEM converges on the same fundamentals independently: atomic notes, embedding-based retrieval, LLM-driven linking, link traversal augmenting similarity search. It also implements a form of reconsolidation — when a new note is added, it retrieves top-k neighbours and prompts an LLM to update their contextual descriptions, keywords, and tags.

**Where this design extends A-MEM:** A-MEM updates existing notes' *metadata* (keywords, tags, context description) but not their core content. This design allows full content revision — contradiction, supersession, splitting. A-MEM uses generic links; this design uses a typed closed vocabulary. A-MEM's link formation is always new-to-existing; this design adds a synthesis outcome that creates bridging notes between existing notes. A-MEM evolves incrementally on every write; this design proposes batch consolidation motivated by CLS slow-integration.

**What A-MEM contributes:** its seven-component note structure includes a contextual description — an LLM-generated field summarising broader context, maintained by the evolution pass, improving embedding quality. Adopted as the `context` field in §7.1.

### 3.8 Vannevar Bush: The Memex and Associative Trails

Bush's 1945 essay "As We May Think" proposed a device for storing knowledge and retrieving it via *associative trails* rather than hierarchical indexing. He also proposed trails could be shared: "Here is my trail" — packaged knowledge transferable to another person.

The portability of a markdown Zettelkasten is the direct realisation of this vision. A directory of linked files can be zipped and shared, committed to git, diffed, and published. The knowledge structure is a legible artefact. This is qualitatively different from the current SQLite `history` store, which is machine-readable but not human-inspectable.

---

## 4. Constraints Derived from Human Practice

When humans have been doing manually — and imperfectly — the very thing we are trying to automate, the practices that survive are not arbitrary conventions. They are **empirically validated solutions** to exactly the problems the automated system will face. The practices evolved under selection pressure: approaches that failed to maintain knowledge quality, coherence, or navigability were abandoned; approaches that worked were codified as policies, standards, or norms.

This gives us a design method: identify human domains that have grappled with the same problems and mine their evolved practices for constraints. The constraints carry more epistemic weight than design choices made from first principles, because they have already been tested against reality.

### 4.1 Wikipedia's Editorial Policies

Wikipedia is the most directly analogous system: a large-scale, continuously evolving, collaboratively maintained knowledge base built from messy real-world sources. Its editorial policies evolved specifically to solve the problems of quality, coherence, and navigability at scale. Each maps to a concrete design choice:

| Wikipedia policy | Problem it solves | Design constraint |
|---|---|---|
| **Notability** | Don't create articles for things without sufficient evidence | The `defer` outcome: low-evidence candidates become provisional `type: question` notes |
| **Neutral Point of View** | Don't resolve genuine disputes by picking a side | The `contradicts` link: represent tension faithfully; let downstream reasoning engage |
| **Verifiability** | Every claim must be traceable to its source | The `sources:` field; every note carries its provenance chain |
| **No Original Research** | Distinguish reported facts from editorial synthesis | The `type` vocabulary: `observation` (from sources) vs. `claim` (generalised) vs. `structure` (synthesis) |
| **Stub vs. Featured Article** | Represent knowledge quality explicitly | The `confidence` + `stable` fields: stubs are low-confidence; featured articles are stable and highly-linked |
| **Article splitting and merging** | A single article can conflate two distinct concepts | `supersedes` can split; `synthesises` merges into a structure note |
| **Talk pages** | Represent editorial reasoning without polluting the article | The `note:` field on a link: reasoning recorded without entering the note body |
| **Corrections policy** | Don't silently alter the record | `type: refuted`: superseded notes retained for provenance, not deleted |

The power of this mapping is not that Wikipedia invented these ideas, but that each policy is a hardened response to a failure mode encountered at scale. An automated system will encounter the same failure modes.

### 4.2 Library Science: Controlled Vocabularies and Faceted Classification

**Thesauri and controlled vocabularies** were developed to solve consistent relationship labelling across large collections built by many contributors over time. The link relation vocabulary in §7.2 (`supports`, `contradicts`, `extends`, `synthesises`, etc.) is a thesaurus for a knowledge graph — a closed vocabulary so that the integration LLM's choices are consistent and the graph is queryable.

**Faceted classification** (Ranganathan, 1933) rejected hierarchical taxonomies in favour of multiple independent orthogonal facets. The `tags:` field implements this: a note is simultaneously in the `memory`, `consolidation`, and `agents` facets without being forced into a single hierarchy.

### 4.3 Academic Peer Review: Replication and Retraction

**Replication as confidence building.** A claim confirmed by multiple independent consolidation passes (from different source documents) earns higher confidence than one seen only once. The `stable` promotion criterion is a replication threshold.

**Meta-analysis as synthesis.** A `structure` note that aggregates multiple `observation` notes into a generalisation — with links back to the source notes — is the computational equivalent of a meta-analysis.

**Retraction without erasure.** `type: refuted` applies the retraction principle: superseded notes are retained for provenance, not deleted.

### 4.4 Legal Reasoning: Precedent and Burden of Proof

**Stare decisis (precedent):** the `stable` flag and conservative prior (§7.4) implement this directly. A well-established, highly-linked note is not casually revised by a single contradicting observation. The burden of evidence for overturning a stable note is higher than for revising a provisional one.

**Burden of proof:** a new claim enters as a provisional `observation` with moderate confidence and must accumulate corroboration before promotion. The `defer` outcome is "insufficient evidence to decide."

### 4.5 Organisational Learning: Double-Loop Learning

Argyris and Schön's distinction between **single-loop** (correct errors within existing assumptions) and **double-loop** (question the assumptions themselves) learning maps cleanly to the integration decision:

- Single-loop → `assimilate` and `extend`: new information fits the existing structure.
- Double-loop → `supersede`: the existing belief structure itself is revised.

Distillation can only single-loop: it appends corrections on top of a potentially flawed model without ever questioning it. The `contradicts` and `supersedes` mechanisms enable double-loop learning.

### 4.6 The General Principle

Across these domains, the same patterns recur: **represent uncertainty explicitly**, **record provenance**, **protect stable knowledge from casual revision**, **use controlled vocabularies for relationships**, and **distinguish types of knowledge**. None of these are ML research contributions. They are evolved constraints, tested under selection pressure of real-world knowledge management at scale. An automated system that ignores them is starting from scratch on problems that have already been solved.

---

## 5. Why Markdown and Why Zettelkasten

**Human readability enables quality assessment.** The current distillation output is opaque — there is no practical way to evaluate whether extracted knowledge is accurate, coherent, or useful. A Zettelkasten of markdown notes is directly inspectable. An agent's long-term memory becomes something a human collaborator can read, audit, and correct. This is the grokipedia vision at personal scale: building a clean, structured, legible knowledge base from messy real-world data.

**Portability enables transfer.** A directory of markdown files with YAML frontmatter is a self-contained, format-agnostic artefact. It can be compressed and shared, committed to a git repository, branched and merged, published as a static site. The knowledge is not locked to aswarm's runtime or SQLite schema.

**The Zettelkasten principle of emergence.** Niklas Luhmann's original Zettelkasten — which produced ~90,000 notes over 40 years — was organised not by category but by connection. Notes were atomic (one idea each), permanent (never deleted, only extended or linked), and linked explicitly. The structure of knowledge emerged from the pattern of links, not from a taxonomy imposed in advance. Luhmann described the Zettelkasten as an intellectual partner: the emergent link graph represented understanding that exceeded what any individual note contained.

**Atomic notes force precision.** A Zettel is one idea. Decomposing what was learned into atomic units is a forcing function for clarity. A note that covers two ideas should be split. This produces a knowledge base that is more navigable and more useful than a collection of summaries.

**Resilience to model improvement.** A filesystem of markdown files that an LLM reads directly gets *better* as models improve — a more capable model reasons more effectively over the same representation. A sophisticated retrieval pipeline that compensates for weaker models may become unnecessary overhead. The markdown format is the Bitter-Lesson-resilient choice.

---

## 6. The Consolidation Algorithm

Consolidation is triggered either on a nightly schedule (§6.5) or when accumulated material exceeds a salience threshold (§6.5). The algorithm has three phases.

The central abstraction is **episode as zettel**: the incoming material — whatever its source — is first synthesised into a note-shaped representation (a draft note). The draft and the existing cluster are then the same kind of thing. The integration pass is a symmetric operation: given two sets of topic-scoped notes, produce the coherent revised cluster that results from merging them. This symmetry is load-bearing: it means the same mechanism that integrates a single article also merges two entire knowledge bases, at scale.

### 6.1 Phase 1 — Form

The Form phase produces one or more **draft notes** from the incoming material. The draft note is topic-scoped — the same shape as notes in the Zettelkasten — but unpolished. It represents the incoming material's content expressed in the knowledge base's vocabulary, ready to be compared against the existing cluster.

The Form phase has three modes depending on source type:

**Stream episode (monitoring feeds, conversation logs).** A stream of turns is first segmented into coherent episodic units using a boundary detector, then each episode is synthesised into a draft note.

Stream segmentation follows **Event Segmentation Theory** (Zacks et al., 2007). An LLM examines an accumulating buffer and makes a per-turn judgment:

```
(is_boundary, confidence) = boundary_detector(new_turn, buffer)
```

A boundary triggers when `is_boundary AND confidence ≥ 0.80`, or at a maximum buffer backstop of 8–10 turns. Validated by Spike 1: Approach A (Nemori naïve, conf≥0.80) produced 7 well-scoped episodes from 21 research findings (see `spikes/spike1-boundary/results-run2.md`).

The Def-DTS intent taxonomy (He et al., 2024) is applied as a *labelling* pass on each flushed episode — not as a boundary trigger — producing `(type, domain)` metadata that becomes tags on the draft note and eventually on the Zettel.

The episode is then synthesised into a draft note: *"Summarise this cluster of related findings as a topic-scoped note in the domain's vocabulary."*

**Structured document (research paper, outlined article).** Section or chapter boundaries give natural episode boundaries. Each section is synthesised into a draft note. For a 1000-word article with four clear sections, Form produces four draft notes. This is the easy case; no boundary detection required beyond the document's own structure.

**Fuzzy document (email, blog post, LinkedIn article, X thread).** The most common case in practice. Topics are present but their boundaries are gradients rather than hard transitions — the text moves between subjects without explicit markers. Applying boundary detection to a fuzzy document produces arbitrary cuts at zones rather than real transitions.

The correct framing is not *find the boundaries* but *identify the topics, then extract per topic*. Topic-relevant content is often scattered: a sentence buried in paragraph 8 may be more relevant to a given topic than the paragraph nominally about it. Overlap at thematic boundaries is permitted — content partially about two topics appears in both extractions. The integration phase handles redundancy; the Form phase should not sacrifice recall trying to prevent it.

**When the cluster is non-empty**, the existing notes already define the topics. The task is to identify what the new document adds to each existing topic, drawing from anywhere in the document. Content not meaningfully relevant to any existing note is a candidate for new-topic creation.

**When the cluster is empty** (bootstrapping), topic discovery must run on the document directly. CARPAS-inspired constrained generation applies: predict the number of distinct topics first, then identify and extract them. The count constraint prevents LLM over-generation of spurious sub-topics — a known failure mode without it (CARPAS, 2025).

**Two candidate approaches — which Spike 2 compares:**
- *Single-shot*: present the existing notes and full document in one prompt — "here is what we already know, here is new material, produce draft updates per topic." Minimal engineering; the right choice if a capable model handles it reliably.
- *Locate-then-summarise*: use each existing note as an explicit topic query against the document, collect all relevant content regardless of position, then synthesise per topic. More structured; may outperform for long or diffuse documents.

Neither is prescribed. The Bitter Lesson applies directly here: if the single-shot approach works, the locate-then-summarise algorithm is unnecessary. Spike 2 determines which approach holds up in practice, and the benchmark should be revisited as models improve.

### 6.2 Phase 2 — Gather

For each draft note from Phase 1, assemble the **cluster**: the neighbourhood of existing notes most relevant to this topic.

**Retrieval scoring.** Following Generative Agents (Park et al., 2023), each note receives a combined score:

```
score(note, query) = α·recency + β·salience + γ·similarity

recency    = exp(-λ · hours_since_last_accessed)   # λ ≈ 0.005 (0.995 decay/hour)
salience   = note.salience                          # ∈ [0,1]; set at creation
similarity = cosine(embed(query), embed(note.body))
α = β = γ = 1  (equal weights; tunable)
```

`recency` is computed on **last access time**, not creation time — spaced repetition embedded in retrieval. Frequently-accessed notes stay salient; neglected notes decay out of contention.

**Embedding target: full note body.** Spike 4A established that full body embedding significantly outperforms the context field (first sentence) for cluster retrieval (MRR 0.565 vs 0.464 on the Wikipedia corpus; R@5 0.404 vs 0.263 against LLM-judged ground truth). LLM-generated summaries do not improve over body embeddings — the body already contains the retrieval signal in a form the embedding model can use. The context field evolution pass (§6.4) remains useful for human readability and semantic positioning but is not load-bearing for retrieval quality.

**Cluster window size: top-20.** Spike 4D showed that body embedding recall against LLM-judged ground truth reaches 49% in top-10, 63% in top-20, and 68% in top-30 notes. The default cluster window is top-20 — the additional ten notes meaningfully improve coverage at modest context cost.

**Graph traversal and tag intersection: not used.** Spike 4A measured citation-style link traversal and found it degrades retrieval: depth-1 expansion grows clusters from 10 to 53 nodes at 15.6% precision on new nodes. Depth-2 reaches 108 nodes — 36% of the test corpus. The Wikipedia link graph short-circuits through hub articles; tag-based filtering shows zero discriminative signal on missed integration targets (Spike 4D gold set diagnostic). Both mechanisms are eliminated.

**Activation-weighted links: future direction.** The connections the integration LLM judges as relevant are often inferential and cross-domain — 83% of missed gold notes have no link or tag signal. These connections are recoverable via accumulated integration history rather than pre-specified structure. See §3.3 and H-new-A in §11. Not implemented in the initial build.

The cluster is the top-20 notes by combined recency/salience/similarity score. The cluster must fit within the integration LLM's context window.

### 6.3 Phase 3 — Integrate

The editorial pass. The LLM receives the draft note(s) and the full cluster as plain markdown and acts as a Wikipedia editor who has just read a new source: how do the existing articles need to change?

The integration LLM naturally applies the Thousand Brains / predict-calibrate principle without a separate phase: it can see the existing cluster and knows what is already covered. It incorporates only what is genuinely new or in tension with what is already there. Notes confirming existing knowledge without adding nuance generate no revision.

The output is a set of **note operations** applied atomically across the cluster:

| Operation | When |
|---|---|
| `UPDATE` | Draft adds nuance, evidence, or revision to an existing note. The note is *rewritten to synthesise* old and new understanding — not appended to. |
| `CREATE` | Draft covers a topic with no existing note. New note with untyped links to relevant existing notes. |
| `SPLIT` | An existing note has grown to conflate two distinct threads, or incoming material reveals it covers two separable subjects. The note becomes two. This is the expected healthy lifecycle of a maturing note — not an edge case. |
| `MERGE` | *(Deprecated — not in current prompt vocabulary. See `architecture-decisions.md §7a`.)* Two existing notes cover the same topic. Originally conceived as an ingestion-time operation; experimental work showed it destroys the retrieval surface that enables SYNTHESISE, and that EDIT+SPLIT+SYNTHESISE manage corpus cleanliness more effectively. Retained here as historical context. |
| `SYNTHESISE` | The draft reveals a connection between two existing notes that neither captures. A new `structure`-type note is created articulating the bridging principle, citing both notes. |
| `NOTHING` | Draft is already fully covered by the existing cluster. No action. Must be explicit — the integration LLM should not be pressured to integrate everything. |
| `STUB` | Sparse or empty cluster — the draft introduces a topic without an established neighbourhood. The trigger is *semantic isolation* (few or no adjacent notes), not content thinness. A rich, well-developed draft on a topic with no KB neighbourhood is still STUB, not CREATE. A provisional note is created at low confidence; it is promoted to `topic` as inbound links accumulate and corroborate the knowledge — not simply as content grows. |

The `UPDATE` operation deserves emphasis. When new material belongs in an existing note, the note is **rewritten** — the LLM synthesises the old understanding and the new material into a better unified text. The note may get longer, shorter, or the same length. It does not accumulate new paragraphs. It represents the current best understanding, not a log of inputs. Notes grow through successive UPDATE passes and are expected to eventually SPLIT as they accumulate depth on multiple threads.

**Conflicting views are maintained as separate notes, not blended.** When incoming content contradicts an existing note, CREATE a new note for the competing view rather than incorporating "however X argues..." into the existing note. Both views remain fully developed on their own terms. A `contradicts` link (see §7.2) connects them, ensuring both are co-retrieved whenever either is relevant. This is the representation policy that keeps genuine intellectual tension alive rather than collapsing it into a false synthesis.

**Style and voice.** The target document the system is writing towards is not a Platonic ideal — it is the existing notes. Updated and created notes should adopt the vocabulary, level of detail, and typical length of the cluster's established notes. The integration LLM receives the cluster as both content context and implicit style reference.

**Reflections.** When the cluster reveals a pattern across multiple draft notes in the same pass — a generalisation, a synthesis, an emerging principle — the integration LLM may generate a `structure`-type note capturing it, citing the notes it was inferred from.

### 6.4 Consolidation Triggers

Two independent triggers fire consolidation; whichever occurs first runs.

**Scheduled (sleep analogy).** A nightly cron pipeline at 3am processes the previous day's accumulated material. This mirrors CLS sleep consolidation: episodic memory accumulated during the day is integrated into semantic memory overnight.

**Salience threshold.** Each item written to the `history` store carries a `salience` score (LLM-scored 1–10 at write time). When cumulative salience of unprocessed material exceeds a threshold, consolidation fires immediately. Following Generative Agents, this produces organic consolidation proportional to how much significant material has accumulated — a quiet day generates no unnecessary passes; a high-information burst triggers consolidation promptly.

**Lightweight per-write evolution.** Following A-MEM: on each new note written to the Zettelkasten, a fast pass updates the `context` field and tags of top-k neighbours without modifying content. This keeps the embedding index fresh and improves future Gather quality. Full content-level consolidation (UPDATE, SPLIT) is reserved for the triggered batch pass — mirroring the neuroscience distinction between synaptic consolidation (fast local) and systems consolidation (slow global).

### 6.5 Write Atomicity

A single integration pass may produce multiple operations across several notes. These must be applied atomically — a partially-applied integration leaves the graph inconsistent.

SQLite transactions cover the index. Markdown files are written in the same operation, with the index as the write-ahead log and files as the durable record.

---

## 7. The Data Model

### 7.1 Note frontmatter

```yaml
---
id: z20260313-001
type: topic                # topic | stub | structure | procedure | question | refuted
confidence: 0.82           # 0.0–1.0; updated by integration decisions
salience: 0.7              # 0.0–1.0; LLM importance score at write time, fixed thereafter
stable: false              # promoted when confidence > 0.8 AND inbound_links > 3 AND age > 30d
valid_from: 2024-06-01     # optional: when the fact was true (vs created: when we recorded it)
context: >                 # LLM-generated contextual description; updated by evolution pass
  This note situates within a cluster of work on two-speed memory architectures,
  specifically the application of CLS theory to agent memory design.
links:
  - id: z20260312-042
  - id: z20260313-000
    rel: contradicts
    note: "competing claim on retrieval latency"
tags: [memory, consolidation, agents]
sources:
  - arxiv:2502.12110
  - pipeline:researcher/synthesis:2026-03-13T10:00:00Z
created: 2026-03-13T10:00:00Z
updated: 2026-03-13T14:22:00Z
---

Memory consolidation in LLM agents benefits from a two-speed architecture...
```

**Field notes:**
- `salience` is scored once by the LLM at write time ("how significant is this, 1–10?") and never changed. It represents intrinsic importance independent of context or retrieval history.
- `valid_from` captures when a fact was true in the world, distinct from `created` (when it was recorded). Distilled from Zep/Graphiti's bi-temporal edge model, reduced to the single field that survives the Bitter Lesson: let the LLM reason about temporal validity from the representation.
- `last_accessed` is tracked in the SQLite index only, not in frontmatter — it is operational metadata, not content, and would generate spurious git diffs.

### 7.2 Link relation vocabulary

Most links are **untyped** — they encode proximity in the knowledge graph without specifying the nature of the relationship. The LLM reading linked notes can infer the relationship from their content. Over-specifying link types is makework that becomes obsolete as models improve (Bitter Lesson).

One typed link is retained:

| `rel` | Meaning | Why typed |
|---|---|---|
| `contradicts` | This note holds a competing or opposing view to the target | Policy marker for the integration LLM: these are competing views — do not merge, update, or synthesise them away. Encodes the representation policy: conflicting views live as separate notes, fully developed, not blended. Also provides a queryable record of known tensions in the knowledge base. |

Note: `contradicts` does *not* currently change retrieval behaviour. A co-retrieval guarantee (ensuring both contradicting notes enter the cluster whenever either is retrieved) would require Gather(A) to explicitly traverse `contradicts` links — which is unresolved (H9, Spike 4). In practice, notes that genuinely contradict each other on the same topic tend to have high embedding similarity, so similarity-based retrieval is likely to surface both anyway. Whether explicit `contradicts` traversal adds anything over similarity is an empirical question for Spike 4.

**`refuted` is a note status, not a link type.** When an UPDATE comprehensively replaces an old understanding, the old note's `type` is set to `refuted`. Refuted notes are excluded from context by default. A `supersedes` link type is unnecessary: if a refuted note never reaches context, the link has no audience; if both notes are in context, the supersession is evident from reading the content.

The detailed link vocabulary (supports, extends, refines, exemplifies, applies_to, synthesises, supersedes) is deferred to a future spike on the linked data structure and graph-based gather (Spike 4), where the practical value of typed traversal will be evaluated empirically.

### 7.3 Note types

Notes are topic-scoped: one subject per note, covered with whatever depth the accumulated evidence supports. The type reflects the *nature* of the note, not its claim granularity.

| `type` | Meaning |
|---|---|
| `topic` | A developed topic note. One subject; comprehensive on that subject; grows through successive consolidation passes. The primary type. |
| `stub` | A topic note in a sparse or empty neighbourhood. The signal is *semantic isolation* — the knowledge lacks cross-referencing from adjacent notes — not content thinness. A rich draft on a topic with no established KB neighbourhood is still a stub. Promoted to `topic` as inbound links accumulate and corroborate the note, not simply as content grows. The Wikipedia "stub" analogy is partially misleading: the intended meaning is closer to *proposed* — put forward tentatively, pending neighbourhood confirmation. |
| `structure` | A note that bridges or synthesises two or more other topic notes. Captures a relationship or pattern that spans topics; cites the notes it was inferred from. |
| `procedure` | A method or process (how to do something). |
| `question` | An open question or knowledge gap. Created by the `DEFER` integration outcome when material cannot yet be integrated. Revisited in future passes. |
| `refuted` | A note that has been superseded. Retained for provenance; excluded from reasoning context by default. |

### 7.4 The `stable` flag and conservative prior

Notes accrue stability: through repeated confirmation across consolidation passes, through high inbound link degree, and through high confidence. Stable notes are analogous to legal precedent — not overturned lightly.

Provisional `stable` criterion: `confidence > 0.8` AND `inbound_links > 3` AND `age > 30 days`. The integration LLM receives stability status of cluster members as part of its context: stable notes resist casual revision; provisional notes are open to restructuring.

### 7.5 Storage

The markdown files are the **source of truth**. A SQLite index is derived from them:
- Embedding vector lookup (`sqlite-vec`) for similarity search
- `last_accessed` tracking for recency scoring
- Inbound link index (frontmatter stores outbound links only; index maintains both directions)
- Tag, confidence, salience, and stability queries

The index is fully rebuildable from the markdown directory. The knowledge base is genuinely portable — move the directory, reconstruct the index.

---

## 8. Fit with aswarm's Memory Architecture

The Zettelkasten store sits alongside existing memory types as `type: zettelkasten` in the `memory:` or `service:` block:

```yaml
service:
  long-term-knowledge:
    type: zettelkasten
    path: memory/zettelkasten/
    index: memory/zettelkasten.db
```

### 8.1 Read path (enrich)

An agent declaring `enrich: long-term-knowledge` triggers Phase 2 gather: embed the current envelope data, compute combined scores, retrieve the cluster, inject cluster notes into `envelope.context`. The agent sees its relevant long-term knowledge as plain markdown — LLM reads it directly. Same `enrich:` interface as `history` and `document`.

### 8.2 Write path (consolidation pipeline)

Writing to a Zettelkasten is a batch operation over a richer source — a dedicated consolidation pipeline:

```yaml
pipeline: nightly-consolidation

connections:
  trigger:
    type: cron
    schedule: "0 3 * * *"

agents:
  - source: trigger
    type: model
    prompt: |
      Segment yesterday's research history into episodic units.
      For each episode, predict what it would contain given existing knowledge,
      then identify what was surprising — the prediction gap.
      Output candidate notes from the gaps only.
    enrich: [yesterday-history, long-term-knowledge]
    sink: candidates

  - source: candidates
    type: model
    prompt: |
      For each candidate note, read the provided cluster of related Zettels.
      Decide: assimilate into existing / extend / conflict / supersede / synthesise / defer.
      Apply your decision and output the resulting note operations.
    enrich: [long-term-knowledge]
    sink: long-term-knowledge

service:
  yesterday-history:
    type: history
    path: memory/history.db
    session_key: "research:{date}"

  long-term-knowledge:
    type: zettelkasten
    path: memory/zettelkasten/
    index: memory/zettelkasten.db
```

### 8.3 Relationship to existing distillation

The existing `distil:` config on `HistoryStore` extracts facts into a second `history` store — a flat list of text snippets. A Zettelkasten store replaces this with graph-structured memory. The extraction step (Phase 1) is richer; the write step (Phase 3) is fundamentally different.

---

## 9. Experimental Hypotheses

This design contains a number of ideas that have not been validated together in practice. Rather than treating this document as a system specification, it should be treated as a set of **experimental hypotheses** — each with a proposed solution that is worth implementing, evaluating, and potentially discarding. They are listed here explicitly to enable structured experimentation.

---

**H1 — Predict-Calibrate as the write strategy** *(resolved — Spike 3)*

*Hypothesis:* Writing only what was surprising (the prediction gap) produces a higher-quality, lower-noise Zettelkasten than extracting and summarising everything observed.

*Resolution:* The NOTHING operation in the integration decision IS the predict-calibrate filter — the integration LLM sees the existing cluster and knows what is already covered; content that matches existing knowledge generates NOTHING. §6.3 already stated this: "The integration LLM naturally applies the Thousand Brains principle without a separate phase." Spike 3 validates it empirically: NOTHING fired correctly on both pre-emptive cases at confidence 0.95, with 100% consistency. A separate predict-then-compare engineering step adds complexity without adding capability. Resolved as subsumed by the integration decision.

---

**H2 — Event Segmentation for episode boundaries** *(resolved — Spike 1)*

*Hypothesis:* LLM-judged semantic boundaries (topic shift, intent change, temporal marker) produce better-scoped candidate episodes than token-count or turn-count chunking.

*Resolution:* Approach A (Nemori naïve, conf≥0.80) validated. Produced 7 well-scoped episodes from 21 research findings; two large coherent clusters with appropriate singletons between. Def-DTS intent classification adopted as a labelling pass (not a boundary trigger), due to ~15% label drift across runs. Buffer backstop: 8–10 turns.

---

**H3 — Link types as integration-reasoning aids** *(retrieval use eliminated — vocabulary question remains open)*

*Hypothesis:* A closed link vocabulary (supports, extends, refines, contradicts, synthesises, …) produces a more queryable and consistently-labelled graph than untyped links.

*Partial resolution:* Citation-style link traversal for **retrieval** is eliminated by Spike 4A — following links from similarity entry points degrades cluster quality (fan-out to 53 nodes at depth=1, 15.6% precision on new nodes). Link expansion is not used in Phase 2 Gather. Separately, the vocabulary question for **integration reasoning** remains open: does providing explicit `rel:` types on links help the integration LLM reason about the cluster, or does it read note bodies and infer relationships directly? The `contradicts` type is retained as a policy marker (do not merge competing views) regardless of how the vocabulary question resolves.

---

**H4 — Three-component retrieval scoring**

*Hypothesis:* Combining recency (last access), salience (write-time importance), and similarity (current context) produces better cluster selection than similarity alone.

*Proposed solution:* `score = recency + salience + similarity`, equal weights, tunable.

*Evaluate:* Ablate each component. Does last-access recency add value over creation-time recency? Does write-time salience remain meaningful after many consolidation passes?

---

**H5 — The synthesise integration outcome** *(operation validated — Spike 3; knowledge quality longitudinal)*

*Hypothesis:* Creating structure notes that bridge previously unconnected existing notes — when new information reveals their latent relationship — produces emergent knowledge that neither source contained.

*Resolution:* Spike 3 validated that the SYNTHESISE decision fires correctly and consistently (2/2, 100% consistent). The operation is reliable enough to drive automated writes. The deeper quality question — whether synthesised structure notes produce genuinely emergent understanding, get confirmed by subsequent passes, and carry forward — requires longitudinal evaluation on real knowledge base material. Not a blocking concern for the build.

---

**H6 — Dual consolidation triggers**

*Hypothesis:* An importance-sum threshold trigger (fire when enough significant material has accumulated) combined with a nightly schedule produces more timely integration than schedule alone, without the catastrophic interference risk of per-write incremental updates.

*Proposed solution:* Salience-sum threshold + nightly cron, whichever fires first. Lightweight metadata evolution (context, tags) on each write; full content consolidation at trigger.

*Evaluate:* Does the threshold trigger meaningfully change consolidation timing vs. nightly-only? Does the lightweight per-write metadata evolution produce measurably better retrieval (via the `context` field embedding)?

---

**H7 — Conservative prior on stable notes (stare decisis)**

*Hypothesis:* Protecting highly-linked, high-confidence, aged notes from casual revision — requiring stronger evidence to overturn them — produces a more coherent knowledge base over time.

*Proposed solution:* `stable` flag communicated to integration LLM as a signal to require stronger evidence.

*Evaluate:* Does this prevent legitimate corrections (false negative) or does it correctly filter spurious contradictions (true positive)? Is the three-part criterion (`confidence > 0.8`, `inbound_links > 3`, `age > 30d`) well-calibrated?

---

**H8 — Markdown filesystem as source of truth (Bitter Lesson)**

*Hypothesis:* A filesystem of human-readable markdown files that LLMs read directly is more resilient to model improvement than a sophisticated retrieval pipeline. As models improve, the representation quality matters more than retrieval precision.

*Proposed solution:* Markdown files as source of truth; SQLite index as derived operational layer for scoring; LLM reads note content directly in context.

*Evaluate:* As the consolidation system is used with progressively more capable models, does retrieval precision matter less? Does note structure quality matter more? This is a long-horizon hypothesis that requires longitudinal observation.

---

**H9 — Graph traversal augmenting similarity** *(eliminated — Spikes 4A and 4D)*

*Hypothesis:* Following typed links from similarity entry points surfaces related notes that embedding similarity alone misses.

*Resolution:* Eliminated. Spike 4A measured citation-style link traversal on a 300-note corpus: depth-1 expansion grows clusters from 10 to 53 nodes at 15.6% precision on new nodes. Depth-2 reaches 108 nodes. The link graph short-circuits through hub articles. Spike 4D confirmed that 83% of integration-relevant notes missed by body embedding have no link or tag signal at all — the connections the integration LLM makes are inferential and cross-domain, not encoded in citation structure. Citation-style traversal is removed from Phase 2 Gather. See H-new-A for the replacement direction.

---

**H-new-A — Activation-weighted co-retrieval links improve recall for inferential connections** *(open — Spike 5)*

*Hypothesis:* Notes that repeatedly co-activate in integration windows accumulate associative links that encode inferential and cross-domain connections that body embedding cannot surface on first encounter. Blending body similarity with decayed co-activation strength improves cluster recall without expanding cluster size.

*Proposed mechanism:* After each integration event, record co-activation pairs and their timestamp. Score: `α·body_sim + (1-α)·Σ exp(-λ·age)` for past co-activations. Decay rate λ is a tunable parameter; small λ (slow decay) weights historical associations; large λ (fast decay) emphasises recent co-activations. The co-activation graph is expected to develop small-world properties (Watts & Strogatz, 1998): dense local clusters with sparse long-range connections — the topology that makes spreading activation computationally efficient and retrievally precise.

*Evaluate:* Against LLM-judged ground truth (Spike 4D ground truth as held-out baseline): does co-activation scoring lift R@10 above 0.65 after N integration events have accumulated? Spike 5.

---

**H-new-B — Non-acted-on co-retrieved notes add marginal activation signal** *(hypothesis — uncertain)*

*Hypothesis:* Notes co-retrieved in a gather window but receiving NOTHING from the integration LLM (i.e., not acted on) still contain useful co-activation signal and should be weighted at a fractional rate (e.g. 0.3) relative to notes that received a non-NOTHING operation.

*Uncertainty:* It may be the case that non-acted-on notes are caught by body embedding anyway in similar future queries — in which case the fractional weight adds noise rather than signal. The activation-weighted link graph may be cleaner if restricted to confirmed interactions only (non-NOTHING operations). This is explicitly a hypothesis to be tested in Spike 5 rather than assumed. The question maps to whether the 0.3 weight increases or decreases recall precision on the LLM ground truth evaluation set.

---

**H10 — Locate-then-summarise for fuzzy documents** *(eliminated — does not apply to this system)*

*Hypothesis:* Using existing cluster notes as queries against input documents (locating scattered relevant content per existing topic, then synthesising from the located set) produces higher-quality draft updates than theme discovery on the raw document.

*Resolution:* Eliminated on design grounds before Spike 2. The locate step requires iterating existing notes against each incoming document — O(notes × documents) — which does not scale to an unbounded knowledge base. More fundamentally, Form phase operates on the document alone; it is the Integration phase (not Form) that compares draft notes against existing cluster. Spike 2 confirmed that single-shot topic extraction from the document produces correct, scattered-content-aware draft notes without any locate mechanism. H10 confuses the Form/Gather phase boundary and is not applicable to this design.

---

## 10. Open Questions

These remain open pending further experimentation or literature.

**Integration prompt design.** The Phase 3 editorial pass is the most consequential and hardest prompt to write. The operation vocabulary (UPDATE/CREATE/SPLIT/MERGE/LINK/NOTHING) must be clearly conveyed with enough constraint to be consistent but not so much that it becomes a classification task rather than genuine editorial judgment. This is substantial prompt engineering work.

**Evaluation rubric.** ROUGE is a poor proxy for quality in this domain — the clinical NLP and meeting summarisation literature has abandoned it in favour of LLM-as-judge with structured rubrics. For the Zettelkasten, the quality question is "does this updated note say what an expert note-taker would have written after encountering this material?" — a preference evaluation, not string overlap. A rubric adapted from the PDQI9 instrument (Physician Documentation Quality Instrument: accurate, informative, concise, pertinent, cohesive, synthesised, contextually correct, contextually relevant, note-worthy) applied by an LLM judge is the proposed evaluation approach. Cross-note consistency (sequential generation §6.3) is a distinct dimension not captured by per-note rubrics.

**UPDATE synthesis quality.** When existing content is rewritten to incorporate new material, how do we evaluate whether the synthesis is genuinely better — not just longer, not losing important prior content? The rubric above addresses part of this; automated detection of dropped prior content is a further open problem.

**Hallucination in sparse topics.** Clinical NLP research finds that hallucination rate is highest when source content is sparse for a section — the LLM fills the gap with invented content (Cohen et al., 2025). The same failure is expected here: when little source material exists for a topic, the synthesised note risks confabulation. Mitigation: the `stub` type signals sparsity; the integration LLM should be instructed to produce shorter, lower-confidence notes for sparse topics rather than fluent hallucination. Monitoring hallucination rate by note confidence band is a recommended evaluation dimension.

**Cluster size budget.** Spike 4D established top-20 as the default: 49% recall at top-10, 63% at top-20, 68% at top-30. The 63% → 68% gain from 20→30 is smaller than the 49% → 63% gain from 10→20, and the additional 10 notes add integration LLM context cost. Top-20 is the current default; this may be tuned per domain.

**Traversal depth.** Resolved as not applicable: citation-style link traversal is eliminated from Phase 2. The question re-opens if activation-weighted links are implemented (Spike 5) — but the expected small-world topology means depth=1 from confirmed co-activation pairs is likely sufficient.

**Embedding maintenance.** Batch re-embedding at consolidation time vs. incremental on each write. Tradeoff between stale vectors and embedding API cost.

**Knowledge base merge.** Two portable knowledge bases can be merged by running the integration phase at scale — each note in the incoming base treated as a draft, integrated into the target cluster. Link ID collisions require remapping. UUID IDs are collision-safe; timestamp IDs are human-readable. The merge mechanism itself is a natural extension of the consolidation algorithm; the tooling around it is not yet designed.

**Forgetting and archival.** When should notes be archived or removed? The design currently retains `type: refuted` notes indefinitely. Principled forgetting — analogous to Ebbinghaus decay — has not been designed.

---

## 11. Summary

The core argument in six points:

1. **Distillation is insufficient.** Append-only fact extraction produces a knowledge base that cannot improve. Knowledge grows through consolidation — active restructuring in light of new experience — not accumulation.

2. **The architecture is grounded in neuroscience and epistemology.** CLS theory, reconsolidation, spreading activation, Piaget, Popper, coherentism — the design is not invented from first principles but derived from well-validated models of how knowledge actually works.

3. **Human-evolved practices provide validated constraints.** Wikipedia's editorial policies, library science controlled vocabularies, peer review replication standards, legal precedent — these are fitness-tested solutions to exactly the problems the automated system faces.

4. **Topic-scoped notes, not atomic claims.** Notes cover one subject comprehensively — at Wikipedia-article granularity — and evolve through synthesis across consolidation passes. This is how people actually build practical extended memory systems. It is also more Bitter-Lesson-resilient: a capable LLM reasoning from a rich topic note outperforms one assembling context from dozens of atomic fragments.

5. **Three phases: Form → Gather → Integrate.** The central abstraction is *episode as zettel*: incoming material is first synthesised into a draft note (same shape as existing notes), then the relevant cluster is fetched, then a cluster-level editorial pass produces a revised cluster — UPDATE, CREATE, SPLIT, MERGE, LINK, or NOTHING operations applied atomically. The integration LLM acts as a Wikipedia editor: it synthesises, not appends. This symmetry means the same mechanism that integrates a single article can merge two entire knowledge bases at scale.

6. **Eventual coherence over per-pass correctness.** The system does not run in a clean room. Individual passes will produce imperfect integrations. The correctness guarantee is at the cluster level over time — notes converge toward accuracy as more material arrives. This is a design principle (§2.4), not a known limitation: it actively shapes how the integration LLM should behave (write stubs, not refusals) and how the system should be evaluated (cluster convergence over N passes, not single-pass accuracy).
