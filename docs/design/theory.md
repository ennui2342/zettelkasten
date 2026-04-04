# Zettelkasten: Theoretical Foundations

*Companion to [`design-principles.md`](design-principles.md). Contains the neuroscience and epistemological grounding, constraints derived from human knowledge management practice, the algorithm with its theoretical connections, and open design hypotheses.*

---

## 1. Theoretical Grounding

### 1.1 Complementary Learning Systems

The most directly applicable neuroscience framework is **Complementary Learning Systems (CLS) theory** (McClelland, McNaughton, O'Reilly, 1995), which proposes that biological memory requires two structurally different systems operating at different timescales:

- **Hippocampus**: fast learning, stores specific episodes with high fidelity, high plasticity. It can encode a new experience in a single exposure without disrupting what is already stored.
- **Neocortex**: slow learning, extracts statistical regularities across many experiences, low plasticity. It resists rapid change precisely because rapid change would destroy the generalised structure it has built up.
- **Consolidation during sleep**: the hippocampus replays episodic memories to the neocortex, which integrates them gradually into its existing structure. The slow integration avoids "catastrophic interference" — overwriting existing cortical knowledge with new patterns.

The architectural parallel is direct:

| CLS | This system |
|---|---|
| Hippocampus | Fast episodic store (session history) |
| Neocortex | Zettelkasten store (slow, semantic, global) |
| Sleep consolidation | Consolidation pipeline (Form → Gather → Integrate) |
| Replay mechanism | Form phase: decompose documents into draft notes |

The key insight from CLS is that you cannot simply copy episodes into long-term memory — the integration must be slow and careful to avoid destroying existing structure. This justifies a dedicated consolidation pass rather than writing directly from the event stream.

### 1.2 Reconsolidation

A refinement of standard consolidation theory: when a stored memory is *retrieved*, it briefly becomes labile — open to modification — before being re-stabilised. This **reconsolidation window** is the moment at which existing memories can be updated in light of new information.

The Gather+Integrate pass is the direct computational equivalent. Retrieving the cluster of related notes does not just read them — it opens a reconsolidation window. The Integrate pass can then revise, extend, or challenge those notes before they are written back. Retrieval and potential revision are coupled, as they are in biological memory.

**Important naming disambiguation.** A-MEM (§1.7) uses the word "reconsolidation" for something different: after adding a new note, it retrieves the top-k neighbours and runs a lightweight LLM pass to update their `context` field, keywords, and tags. In the neuroscience sense, reconsolidation refers to the lability of the retrieved memory itself, not to housekeeping updates on neighbours:

- **Reconsolidation (neuroscience / this design):** the Gather+Integrate pass opens a window in which retrieved notes can be substantively revised, extended, split, or merged in light of new evidence. This is the primary consolidation mechanism.
- **Context field evolution (A-MEM's usage):** after a note is written, a lightweight pass updates the `context` field of neighbouring notes to keep their semantic positioning current. This is optional housekeeping, not the consolidation event itself.

### 1.3 Spreading Activation and Co-Activation Links

Collins and Loftus (1975) proposed that semantic memory is organised as a network where concepts are nodes and semantic relationships are weighted edges. Activation propagates through links, decaying with distance and time — this is the mechanism underlying priming, spreading retrieval, and associative recall.

**The critical distinction: citation links vs. activation-pattern links.** The original design assumed that wikilinks in the zettelkasten would provide a useful spreading-activation substrate for cluster retrieval. Spike 4A refuted this: citation-style link traversal *degrades* retrieval quality, expanding clusters from 10 to 52 notes (depth=1) at 15.6% precision on new nodes. Spike 4D confirmed via LLM-judged ground truth that 83% of integration-relevant notes missed by embedding have no link or tag signal at all — the connections the LLM makes are inferential and cross-domain, not encoded in the citation graph.

**Co-activation links.** Rather than recording citations, the system records *co-activation events*: which notes were retrieved together in the same integration window. These links encode "was relevant in the same context as" — they emerge from the system's own integration judgements rather than from prior authors' choices.

After each integration event, the notes in the gather cluster co-activated in a reconsolidation window. The strength of co-activation links decays exponentially with time, following the ACT-R base-level activation equation (Anderson et al.):

```
activation_strength(A, B) = Σ_events exp(-λ · age_of_event)
```

where the sum is over all past integration events in which A and B co-activated. This is self-organising and epistemically honest. Inferential and cross-domain connections that embedding misses on first encounter accumulate activation weight as they recur across integration events. The knowledge base grows smarter about its own topology through use.

Validated in Spike 5: pairwise co-activation graph with transitive expansion achieves R@10=0.640 in isolation, contributing as the `activation` signal (weight 0.180) in the five-signal fusion. See [`architecture-decisions.md §4`](architecture-decisions.md#4-activation-pairwise-graph-with-transitive-expansion).

**Network theory.** The co-activation graph built from integration events is expected to exhibit small-world properties (Watts & Strogatz, 1998): high local clustering (notes in the same subdomain repeatedly co-activate) with short path lengths (occasional cross-domain integrations create long-range connections). This contrasts with citation graphs, which tend toward scale-free topology with hub articles that dominate traversal and dilute retrieval precision.

**The Temporal Context Model (TCM)** (Howard & Kahana, 2002) provides a finer-grained theoretical grounding. TCM proposes that retrieved items activate a temporal context vector representing the episode in which they were previously encountered. Retrieving item A reinstates the context that activates other items that shared A's integration window. The decay function on co-activation strength is the computational analogue of TCM's contextual drift.

### 1.4 Piaget: Assimilation and Accommodation

Piaget's distinction between **assimilation** (new information absorbed into an existing schema without changing it) and **accommodation** (the schema is revised to fit information it cannot absorb) applies directly to the integration decision:

- **Assimilation**: the new concept fits an existing note — extend it, strengthen a link, raise confidence. Structure unchanged.
- **Accommodation**: the new concept reveals an existing note was wrong, incomplete, or conflating two ideas. Revise or split. Graph restructured.

Distillation is pure assimilation — it never revises. Consolidation supports both.

### 1.5 Popper: Conjecture and Refutation

Popper's epistemology holds that knowledge grows not by accumulation but by conjecture and refutation. A new observation that contradicts an existing belief is not a problem to be suppressed — it is the mechanism by which the knowledge base improves.

This is a design constraint: when a note is superseded, it should be retained for provenance rather than deleted. Conflicting views should be maintained as separate notes connected by See Also wikilinks, not blended into a false synthesis. The current implementation does not enforce this — superseded notes are simply overwritten; provenance retention is a future concern.

### 1.6 Coherentism

The philosophical tradition of coherentism holds that a belief's epistemic status is determined by how well it coheres with the surrounding belief network. A belief in a dense, mutually supporting web is well-founded; an isolated or tension-generating belief is suspect.

The cluster-based integration decision implements this: "does this new concept cohere with its neighbourhood?" A concept cohering strongly with a dense, consistent cluster is integrated with high confidence. One that introduces tension gets lower confidence and an explicit note in the See Also section acknowledging the tension.

### 1.7 A-MEM: Closest Prior Work

The closest existing system is **A-MEM** (Xu et al., 2025), which explicitly implements a Zettelkasten-inspired memory for LLM agents. A-MEM validates the core approach: 2× performance on multi-hop reasoning, 85–93% token reduction vs. full-history methods. The graph structure genuinely improves reasoning quality.

A-MEM converges on the same fundamentals independently: atomic notes, embedding-based retrieval, LLM-driven linking, link traversal augmenting similarity search. It also implements a form of reconsolidation — when a new note is added, it retrieves top-k neighbours and prompts an LLM to update their contextual descriptions, keywords, and tags.

**Where this design extends A-MEM:** A-MEM updates existing notes' *metadata* (keywords, tags, context description) but not their core content. This design allows full content revision — contradiction, supersession, splitting. A-MEM uses generic links; this design uses See Also wikilinks with LLM-written descriptions. A-MEM's link formation is always new-to-existing; this design adds a SYNTHESISE outcome that creates bridging notes between existing notes.

**What A-MEM contributes:** its note structure includes a contextual description — an LLM-generated field summarising broader context, maintained by the evolution pass, improving embedding quality. Adopted as a deferred feature (context field evolution) for future implementation.

### 1.8 Vannevar Bush: The Memex and Associative Trails

Bush's 1945 essay "As We May Think" proposed a device for storing knowledge and retrieving it via *associative trails* rather than hierarchical indexing. Trails could be shared: "Here is my trail" — packaged knowledge transferable to another person.

The portability of a markdown zettelkasten is the direct realisation of this vision. A directory of linked files can be zipped and shared, committed to git, diffed, and published. The knowledge structure is a legible artefact.

---

## 2. Constraints Derived from Human Practice

When humans have been doing manually — and imperfectly — the very thing we are trying to automate, the practices that survive are not arbitrary conventions. They are **empirically validated solutions** to exactly the problems the automated system will face. The practices evolved under selection pressure: approaches that failed to maintain knowledge quality, coherence, or navigability were abandoned; approaches that worked were codified.

### 2.1 Wikipedia's Editorial Policies

Wikipedia is the most directly analogous system: a large-scale, continuously evolving knowledge base built from messy real-world sources. Its editorial policies evolved specifically to solve the problems of quality, coherence, and navigability at scale.

| Wikipedia policy | Problem it solves | Design constraint |
|---|---|---|
| **Notability** | Don't create articles for things without sufficient evidence | Low-confidence CREATE rather than refusing to integrate uncertain content — an imperfect first representation is better than none |
| **Neutral Point of View** | Don't resolve genuine disputes by picking a side | Conflicting views live as separate notes, both fully developed; See Also wikilinks connect them |
| **Verifiability** | Every claim traceable to its source | The `sources:` field; every note carries its provenance chain |
| **No Original Research** | Distinguish reported facts from editorial synthesis | SYNTHESISE is the only operation that produces bridging notes between existing notes — its output is structurally distinct from a directly-sourced CREATE |
| **Stub vs. Featured Article** | Represent knowledge quality explicitly | The `confidence` field; new notes start at low confidence and accumulate it through repeated confirmation |
| **Article splitting** | A single article can conflate two distinct concepts | The SPLIT operation: a note can divide as the topic matures |
| **Corrections policy** | Don't silently alter the record | A design goal: superseded notes should be retained for provenance, not deleted. Not yet implemented. |

### 2.2 Library Science: Controlled Vocabularies

**Thesauri and controlled vocabularies** were developed to solve consistent relationship labelling across large collections built by many contributors over time. The See Also wikilink convention (`[[id|Title]]` syntax, LLM-written descriptions) is a lightweight version of this — a consistent format that makes connections traversable and human-readable without over-specifying relationship types.

**Faceted classification** (Ranganathan, 1933) rejected hierarchical taxonomies in favour of multiple independent orthogonal facets. Tags implement this: a note is simultaneously in several facets without being forced into a single hierarchy. Tags were eliminated from system-generated notes as redundant with retrieval signals, but the principle remains: resist hierarchical taxonomies imposed in advance.

### 2.3 Academic Peer Review: Replication and Retraction

**Replication as confidence building.** A claim confirmed by multiple independent consolidation passes (from different source documents) earns higher confidence than one seen only once.

**Meta-analysis as synthesis.** A SYNTHESISE note that aggregates multiple existing notes into a generalisation — with See Also links back to the source notes — is the computational equivalent of a meta-analysis.

**Retraction without erasure.** A design goal: superseded notes should be retained for provenance. Not yet implemented — currently superseded notes are overwritten.

### 2.4 Legal Reasoning: Precedent and Burden of Proof

**Stare decisis (precedent):** a design goal — a well-established, highly-activated note should not be casually revised by a single contradicting observation. Not yet implemented; the integration LLM currently has no visibility into a note's activation history when deciding whether to revise it.

**Burden of proof:** a new claim enters at moderate confidence and must accumulate corroboration before promotion.

### 2.5 Organisational Learning: Double-Loop Learning

Argyris and Schön's distinction between **single-loop** (correct errors within existing assumptions) and **double-loop** (question the assumptions themselves) learning maps to the integration decision:

- Single-loop → UPDATE: new information fits the existing structure.
- Double-loop → SPLIT or SYNTHESISE: the existing note structure itself is revised.

Distillation can only single-loop: it appends corrections on top of a potentially flawed model without ever questioning it.

### 2.6 The General Principle

Across these domains, the same patterns recur: **represent uncertainty explicitly**, **record provenance**, **protect stable knowledge from casual revision**, **use consistent formats for relationships**, and **distinguish types of knowledge**. None of these are ML research contributions. They are evolved constraints, tested under selection pressure of real-world knowledge management at scale.

---

## 3. Theory to Implementation

Each phase of the consolidation algorithm maps directly to a theoretical concept:

- **Form** is the CLS hippocampal encoding step (§1.1): incoming material is rapidly encoded into episode-shaped units (draft notes) without disturbing the existing semantic store. One draft per topic; same shape as existing notes so the integration pass is symmetric.

- **Gather** opens the reconsolidation window (§1.2): retrieving the cluster of relevant existing notes makes them labile — open to revision. The five-signal fusion (body embedding, BM25, co-activation, step-back, HyDE) is the mechanism for identifying which memories to open. The co-activation signal (§1.3) is the computational analogue of TCM contextual reinstatement.

- **Integrate** is the Thousand Brains prediction-error update (§2.3 of [`design-principles.md`](design-principles.md)): the LLM sees the existing cluster and incorporates only what is genuinely new or in tension. Notes confirming existing knowledge generate NOTHING. Notes that extend, challenge, or connect generate UPDATE, CREATE, SYNTHESISE, EDIT, or SPLIT.

For full implementation detail see [`docs/pipeline.md`](../pipeline.md). For settled design decisions see [`architecture-decisions.md`](architecture-decisions.md).

### 3.1 Data Model and Write Atomicity

For the note data model — frontmatter fields, note types, file naming, embedding format, See Also syntax — see [`docs/note-schema.md`](../note-schema.md).

Markdown files are the **source of truth**. The SQLite index is derived and fully rebuildable from the markdown directory. A single integration pass may produce multiple operations across several notes; these are applied atomically — SQLite transactions cover the index, markdown files are written in the same operation.

---

## 4. Open Hypotheses

These design questions are theoretically grounded but not yet validated empirically. They require real integration event history to test.

**H4 — Recency as a retrieval signal**

*Hypothesis:* Combining recency (`updated` timestamp) with similarity produces better cluster selection than similarity alone.

*Why not yet tested:* the five-signal fusion already achieves R@10=0.667. Whether update recency adds value over the existing activation signal is unclear — activation history may already capture the same temporal signal.

**H6 — Dual consolidation triggers**

*Hypothesis:* An importance-sum threshold trigger combined with a nightly schedule produces more timely integration than schedule alone, without the catastrophic interference risk of per-write incremental updates.

*Current state:* ingestion is on-demand only (no scheduled trigger). Lightweight metadata evolution (context field update after each write, per A-MEM) is also not yet implemented.

**H7 — Conservative prior on well-established notes**

*Hypothesis:* Exposing a note's activation degree and age to the integration LLM, and instructing it to apply a higher burden of evidence before revising highly-activated, aged notes, produces a more coherent knowledge base over time.

*Current state:* the integration LLM has no visibility into activation history. Whether this matters depends on whether the LLM already behaves conservatively toward well-developed notes based on their body content alone.

**H8 — Markdown filesystem as source of truth (Bitter Lesson)**

*Hypothesis:* A filesystem of human-readable markdown files that LLMs read directly is more resilient to model improvement than a sophisticated retrieval pipeline. As models improve, the representation quality matters more than retrieval precision.

*Evaluate:* as the consolidation system is used with progressively more capable models, does retrieval precision matter less? Does note structure quality matter more? This is a long-horizon hypothesis that requires longitudinal observation.
