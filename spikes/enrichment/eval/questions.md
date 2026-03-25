# Evaluation Questions

*12 questions across 4 task types. Ground truth notes are the minimum set needed to answer well — a good response may draw on additional notes, but a navigation strategy that misses the ground truth notes has failed.*

*Hub notes = z001, z002, z003, z006, z018 (activation weight > 7%). Island notes = z009, z011, z012, z013, z017, z20260323-003, z20260323-004, z20260323-005 (activation weight < 1%).*

---

## Cross-source synthesis

Questions requiring integration across multiple notes. No single note contains the full answer.

### Q1 — Hub-accessible
**"What are the major approaches to agent memory in multi-agent LLM systems, and what are the tradeoffs between them?"**

Ground truth notes:
- `z20260322-002` — Procedural Memory as the Mechanism That Closes the Learning Loop
- `z20260322-018` — Foundations of LLM-Based Autonomous Agents: Reasoning, Tool Use, and Planning
- `z20260323-012` — Context Engineering as State Compression for Large Language Model Agents
- `z20260323-013` — Knowledge Distillation, Synthetic Data, and Plan-Aware Context Compression

*Hub-accessible: yes (z002 is tier-1 hub; z018 is tier-1.5). A strong co-activation signal should surface these. Tests whether synthesis-from-hubs works.*

---

### Q2 — Island-dependent
**"How do graph-based retrieval approaches compare to standard vector embedding retrieval for knowledge-intensive agent tasks, and what does the literature say about when each performs better?"**

Ground truth notes:
- `z20260322-008` — Retrieval-Augmented Generation and Retrieval Corpus Governance
- `z20260322-009` — Labeled Property Graphs and Graph Query Languages *(island)*
- `z20260322-013` — Knowledge Graph Retrieval Strategies and Graph-Augmented Generation *(island)*

*Hub-accessible: no. Requires navigation to island notes with low activation. Tests whether embedding/BM25 signals are sufficient for retrieval when activation doesn't help.*

---

### Q3 — Island-dependent
**"What does the literature say about how empirical software engineering methods apply to AI agent system development — both the practices used and the gaps?"**

Ground truth notes:
- `z20260323-002` — Software Development Lifecycle for AI Agent Systems
- `z20260323-003` — Empirical Software Engineering Research Methods *(island)*

*Hub-accessible: no. Both notes are late-ingested with low activation. Tests navigation to a very specific peripheral topic.*

---

## Tension identification

Questions requiring the agent to surface contradictions, debates, or unresolved disagreements across the literature.

### Q4 — Hub-accessible
**"What are the fundamental unresolved tensions between centralised and decentralised coordination in LLM multi-agent systems?"**

Ground truth notes:
- `z20260322-001` — Multi-Agent Architectures: Topology, Organization, and Workflow Automation
- `z20260322-003` — The Agent System Trilemma as the Economic Logic Governing Co-design
- `z20260323-006` — Multi-Agent Reasoning Systems: Formal Foundations, Communication-Computation Tradeoffs

*Hub-accessible: yes (z001 and z003 are top-3 hubs). Tests whether the synthesised tension in z003 is surfaced rather than just the raw architectural description in z001.*

---

### Q5 — Mixed activation
**"Where does the literature disagree about when agent communication adds value versus when it creates overhead or degrades performance?"**

Ground truth notes:
- `z20260322-004` — LLM and Agent Routing
- `z20260322-015` — Inter-Agent Communication Protocols, Interoperability Standards
- `z20260322-016` — Multi-Agent Systems with Large Language Models
- `z20260323-006` — Multi-Agent Reasoning Systems: Formal Foundations, Communication-Computation Tradeoffs

*Hub-accessible: partial (z015 and z020260323-006 have moderate activation; z004 and z016 are lower). Tests whether the tension framing draws out the communication-value debate that exists across these notes.*

---

### Q6 — Island-dependent
**"What tensions exist between how AI agent benchmarks are designed and what practitioners need in order to evaluate real-world agent reliability?"**

Ground truth notes:
- `z20260322-006` — Benchmarks and Evaluation for Agentic AI Systems
- `z20260323-009` — Evaluation and Testing of AI Agent Safety and Behavioral Reliability
- `z20260323-011` — Benchmark Suites and Empirical Performance Landscape for Agentic AI *(island)*
- `z20260323-003` — Empirical Software Engineering Research Methods *(island)*

*Hub-accessible: partial (z006 is tier-1.5; z009 is above threshold but late). Tests whether the practitioner-validity tension is surfaced, which requires the island notes.*

---

## Adjacent possible mapping

Questions asking the agent to identify what lies just beyond the boundary of current knowledge — unexplored directions implied by what the corpus does cover.

### Q7 — Hub-accessible
**"Given the agent system trilemma and current architectural patterns, what coordination mechanisms remain unexplored that the literature implicitly points toward?"**

Ground truth notes:
- `z20260322-003` — The Agent System Trilemma as the Economic Logic Governing Co-design
- `z20260322-001` — Multi-Agent Architectures: Topology, Organization, and Workflow Automation
- `z20260322-015` — Inter-Agent Communication Protocols, Interoperability Standards
- `z20260323-006` — Multi-Agent Reasoning Systems: Formal Foundations, Communication-Computation Tradeoffs

*Hub-accessible: yes. Tests whether hub immersion enables genuinely forward-looking synthesis, not just summary.*

---

### Q8 — Island-dependent
**"What does the phase transition analysis of multi-agent communication regimes suggest about where current systems will break down at scale, and what research directions would address this?"**

Ground truth notes:
- `z20260323-007` — Phase Transitions in Hierarchical Aggregation as the Information-Theoretic Foundation
- `z20260323-006` — Multi-Agent Reasoning Systems: Formal Foundations, Communication-Computation Tradeoffs
- `z20260322-001` — Multi-Agent Architectures: Topology, Organization, and Workflow Automation

*Hub-accessible: no for the key note. z20260323-007 is the synthesised note created at paper 16 with only 2.3% activation weight. It's the most conceptually novel note in the store but has low co-activation signal. This is a critical test of whether non-activation retrieval can surface it.*

---

### Q9 — Island-dependent
**"The literature covers automatic workflow optimisation for multi-agent systems — what aspects of the problem remain open and what methods from adjacent fields might address them?"**

Ground truth notes:
- `z20260323-004` — Automatic Workflow Optimization and Search *(island)*
- `z20260322-001` — Multi-Agent Architectures: Topology, Organization, and Workflow Automation
- `z20260322-004` — LLM and Agent Routing

*Hub-accessible: no for the key note. z20260323-004 is an island note. Tests whether a specific peripheral topic can be found when the question names it directly.*

---

## Analogical transfer

Questions asking the agent to identify cross-domain connections — mechanisms from one field applied to another, or connections the literature hasn't yet made.

### Q10 — Hub-accessible
**"What economic or game-theoretic framings have been applied to multi-agent LLM system design, and are there untried analogies from those fields that the current literature hasn't yet explored?"**

Ground truth notes:
- `z20260322-003` — The Agent System Trilemma as the Economic Logic Governing Co-design
- `z20260323-006` — Multi-Agent Reasoning Systems: Formal Foundations, Communication-Computation Tradeoffs
- `z20260322-015` — Inter-Agent Communication Protocols, Interoperability Standards

*Hub-accessible: yes (z003 is explicitly an economic framing). Tests whether the analogical dimension of a synthesised note is surfaced, not just its surface content.*

---

### Q11 — Island-dependent
**"What connections exist between formal computational theory — expressivity limits, complexity classes, formal grammars — and the practical behaviour of multi-agent LLM systems?"**

Ground truth notes:
- `z20260323-005` — Transformer Expressivity and Formal Models of Computation *(island)*
- `z20260323-006` — Multi-Agent Reasoning Systems: Formal Foundations, Communication-Computation Tradeoffs
- `z20260323-007` — Phase Transitions in Hierarchical Aggregation as the Information-Theoretic Foundation

*Hub-accessible: no. z20260323-005 is an island note (very low activation). The formal theory connection is only accessible if the agent can find this note. Tests navigation to low-activation theoretical content.*

---

### Q12 — Island-dependent
**"How have governance and provenance concepts from database systems or institutional accountability frameworks been applied to trust and auditability in AI agent pipelines?"**

Ground truth notes:
- `z20260322-011` — Provenance-Enforced Governance as the Institutional Counterpart *(island)*
- `z20260322-007` — Memory Poisoning, RAG Security, and Defenses for LLM Agents
- `z20260322-008` — Retrieval-Augmented Generation and Retrieval Corpus Governance

*Hub-accessible: no. z011 is an island note despite being a SYNTHESISE-created note — it was created early but covers a niche governance topic that few other papers reinforced. This tests whether the navigational signal in the title alone (without co-activation) is sufficient to reach a conceptually important but topically isolated note.*

---

## Coverage summary

| Q | Type | Hub-accessible | Key island notes |
|---|------|---------------|-----------------|
| Q1 | Synthesis | Yes | — |
| Q2 | Synthesis | No | z009, z013 |
| Q3 | Synthesis | No | z20260323-002, z20260323-003 |
| Q4 | Tension | Yes | — |
| Q5 | Tension | Partial | — |
| Q6 | Tension | Partial | z20260323-011, z20260323-003 |
| Q7 | Adjacent | Yes | — |
| Q8 | Adjacent | No | z20260323-007 |
| Q9 | Adjacent | No | z20260323-004 |
| Q10 | Analogical | Yes | — |
| Q11 | Analogical | No | z20260323-005 |
| Q12 | Analogical | No | z20260322-011 |

4 hub-accessible, 2 partial, 6 island-dependent. Island-dependent questions are the harder test of navigation quality — a skill that only works for hub notes isn't working well enough.
