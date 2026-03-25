# Mid-Point Analysis — Paper 10 of 20

**Store state:** 18 notes, 10 papers ingested
**Analysis date:** 2026-03-22
**Framework:** ANALYSIS_GUIDE.md + INSPECTION.md eight-step checklist

---

## Store Inventory

| ID | Title | File size (chars) | Est. body chars | Notes |
|----|-------|-------------------|-----------------|-------|
| z20260322-001 | Multi-Agent Architectures for Workflow Automation | 13,744 | ~11,700 | HOT — L3 threshold exceeded |
| z20260322-002 | Procedural Memory as the Mechanism That Closes the Learning Loop | 17,893 | ~15,900 | HOT — severely above threshold |
| z20260322-003 | The Agent System Trilemma as the Economic Logic... | 11,787 | ~9,800 | SYNTHESISE (L1); HOT |
| z20260322-004 | LLM and Agent Routing | 9,805 | ~7,800 | Near threshold |
| z20260322-005 | Experience-Driven and Self-Evolving AI Systems | 15,151 | ~13,200 | HOT |
| z20260322-006 | Benchmarks and Evaluation for Agentic AI Systems | 12,745 | ~10,700 | HOT |
| z20260322-007 | Memory Poisoning, RAG Security, and Defenses for LLM Agents | 12,390 | ~10,300 | HOT |
| z20260322-008 | Retrieval-Augmented Generation and Retrieval Corpus Governance | 10,245 | ~8,200 | HOT; post-SPLIT note |
| z20260322-009 | Labeled Property Graphs and Graph Query Languages | 9,405 | ~7,400 | Near threshold |
| z20260322-010 | Multi-Agent Systems for AI-Assisted Scientific Reasoning | 15,071 | ~13,100 | HOT |
| z20260322-011 | Provenance-Enforced Governance as the Institutional Counterpart | 13,409 | ~11,400 | SYNTHESISE (L1); HOT |
| z20260322-012 | Multi-Agent Structured Query Generation and Self-Correction | 11,114 | ~9,100 | HOT; post-SPLIT note |
| z20260322-013 | Knowledge Graph Retrieval Strategies and Graph-Augmented Generation | 12,816 | ~10,800 | HOT; post-SPLIT note |
| z20260322-014 | AI Agent Architectures and Multi-Agent Systems | 9,526 | ~7,500 | Near threshold |
| z20260322-015 | Inter-Agent Communication Protocols, Interoperability Standards, and Zero-Trust | 16,337 | ~14,300 | HOT |
| z20260322-016 | Multi-Agent Systems with Large Language Models | 12,266 | ~10,200 | HOT |
| z20260322-017 | Last-Mile Delivery as a Stress Test for Autonomous Disruption Resolution | 11,808 | ~9,800 | Island; HOT |
| z20260322-018 | Foundations of LLM-Based Autonomous Agents: Reasoning, Tool Use, and Planning | 13,186 | ~11,200 | HOT; created paper 10 |

**18 notes / 10 papers = 1.8 notes per paper.** Projected 36 notes at paper 20.

The original over-splitting run projected 65 notes. The original over-editing run was projecting ~35–38. Current trajectory (36) is in that lower band — below the 45–55 "sweet spot" — but meaningfully different from the earlier over-editing pattern because the post-L3-fix notes are larger and more conceptually distinct. The store is not fragmented; it is dense. Whether 36 large, coherent notes is better or worse than 50 smaller, more focused ones is an open question that the second half will help answer.

---

## INSPECTION.md Step 1 — Note Quality

### Sampled notes (five deep reads + three partial)

**z20260322-002 — Procedural Memory...** (deeply read)
Outstanding quality. A true hub note — it has accumulated a rich, unified treatment spanning procedural memory as a learning mechanism, cognitive memory architecture (working/episodic/semantic/procedural), RAG as a memory access layer, retrieval strategies, and the co-design principle. All sections are coherent facets of the same underlying question: how do agents learn from experience? The note makes an argument rather than just cataloguing: procedural memory is the mechanism that closes the loop between execution and improvement. No source-referential language. Density is appropriate for a hub.

**Concern:** At ~15,900 body chars, this note is nearly 2× the L3 threshold. The L3 criterion requires "different problem domains or research traditions" for a SPLIT. The note does contain two plausible split threads — (a) cognitive memory architecture types as a taxonomy and (b) procedural memory as the specific learning mechanism — but whether these are truly different problem domains or facets of the same concept is debatable. The new L3 criterion should handle this correctly: a reader studying "how agents learn from repetition" and a reader studying "memory system taxonomies" arguably have different purposes. Watch for whether L3 fires SPLIT on next contact.

**z20260322-003 — The Agent System Trilemma...** (deeply read)
Best note in the corpus. A textbook SYNTHESISE outcome: articulates a three-way constraint (performance vs. cost vs. efficiency) as the *economic reason* why co-design is non-optional — not just desirable. The trilemma framing appears to be emergent from the corpus rather than imported from training (Pareto-optimal frontier as the co-design metaphor is specifically grounded in the multi-objective routing problem). No genetic memory contamination detectable. Tight thesis, independently useful as a retrieval target.

**z20260322-011 — Provenance-Enforced Governance...** (deeply read)
Excellent synthesised note. The core insight — that role-differentiated execution produces provenance as a byproduct rather than as an additional burden — is genuinely cross-paper. Bridges governance, memory security, and co-design through three specific mechanisms. The "triple coupling" conclusion (governance/security/performance trade-off is structurally equivalent to the trilemma) is genuinely emergent. No detectable genetic memory contamination.

**z20260322-005 — Experience-Driven and Self-Evolving AI Systems** (deeply read)
High quality. Dense, technically precise treatment of Pareto filtration, Thompson sampling, NIG conjugate priors, dual-phase operation, and the self-evolving experience base. The final synthesis paragraph — framing the experience base as an "amortization mechanism" that converts prior exploration expenditure into a reusable asset — is insightful and appears to emerge from the corpus material rather than from generic ML knowledge. See Also links are well-grounded. Notable: the connection between multi-faceted retrieval and ensemble methods is the kind of analogical link that should be retrievable by future papers about ensembles or retrieval diversity.

**z20260322-017 — Last-Mile Delivery as a Stress Test...** (deeply read)
Domain-specific island note. Good content — clear framing of LMD as the right domain for stress-testing autonomous disruption resolution, well-documented failure modes of static rule-based systems. But the See Also links are formulaic: all three connect to foundational corpus notes (001, 005, 003) rather than emerging from genuine conceptual overlap. This is the expected pattern for island notes: the store connects them to what it knows, not necessarily to what the paper uniquely contributes. The note's value is as a future retrieval target for papers about real-world agentic deployment in constrained logistics domains — whether that pays off depends on whether the second half brings any such papers.

**z20260322-018 — Foundations of LLM-Based Autonomous Agents: Reasoning, Tool Use, and Planning** (deeply read)
Well-structured foundational note covering CoT, ReAct, tool use (microservice-oriented), planning and re-planning, observability, human-in-the-loop escalation, and single-agent scaling limitations. This is the corpus's first explicit treatment of *why* multi-agent architectures are needed (the limitations section). Quality is good but the note skews toward survey-register — it covers a lot of ground with appropriate accuracy but the "argument" is more structural (here are the components) than analytical (here is the insight). For retrieval purposes, the note will be most useful for papers about foundational agent reasoning. The content is not genetic memory — it is grounded in specific systems (LangGraph, ReAct, CoT).

**z20260322-001 — Multi-Agent Architectures for Workflow Automation** (deeply read)
Has grown substantially from its paper-1 origins. Now covers hierarchical patterns, orchestration loops, directed conditional graphs, complexity matching, memory augmentation, team composition, and (added paper 10) hierarchical MAS theory and formal learning-efficiency results. Dense and coherent but approaching the SPLIT threshold. The note's identity is still "multi-agent architectures" — the additions are extensions of the same question. However, the hierarchical MAS theory section (formal MARL, coordination policies at abstract sub-task level) feels like a different research tradition from the engineering pattern catalogue that dominates the note. This is a potential L3 SPLIT candidate.

**Overall note quality verdict:** Excellent. The store has produced high-quality notes across all three operations (CREATE, UPDATE, SYNTHESISE). The synthesised notes (003, 011) are genuinely emergent. No note reads primarily as a summary or abstract. The abstraction register is consistent — all notes operate at the level of transferable concepts, not paper-specific claims.

---

## INSPECTION.md Step 2 — UPDATE Quality

UPDATE operations have been the most frequent operation across papers 3–10. The critical quality check is whether UPDATEd notes read as unified treatments or as appended content.

**Assessment (from read notes):** z20260322-001 and z20260322-002 both read as unified treatments despite multiple UPDATE passes. The execute prompt's instruction to "integrate the new material throughout so the result reads as a unified topic note" appears to be working. There is no visible seam from successive UPDATEs — the notes do not read as accumulated paragraphs but as coherent wholes.

**Risk:** As notes approach 16,000+ chars (002, 015, 010 territory), the "unified treatment" requirement becomes harder to enforce in a single LLM call. The model has to hold the entire note in context and rewrite it coherently. No evidence of failure yet, but this is worth watching in the second half.

---

## INSPECTION.md Step 3 — Hub Note Analysis

The activation graph reveals a clear three-tier structure:

### Tier 1: Dominant hubs (co-activation confound active)

| Note | Total weight | Notes |
|------|-------------|-------|
| z20260322-002 | 94.7 | Procedural Memory |
| z20260322-003 | 82.7 | Trilemma |
| z20260322-001 | 60.8 | MAS Architectures |

**The top two notes (002 and 003) each have 9–19× the activation weight of the most recent notes (017, 018).** This is well above the 3–4× threshold that indicates the co-activation confound is active.

The 002↔003 edge (weight 23.8) is the most heavily loaded in the entire graph — nearly 1.4× the second-highest edge (001↔002 = 17.9). These two notes have co-appeared in cluster retrieval for essentially every paper in the corpus.

**Interpretation:** The confound is real but not necessarily harmful. Notes 002 and 003 are genuinely foundational — procedural memory and the trilemma are core concepts that nearly every paper in this domain touches. The question is whether this co-activation weight is enriching or crowding out. At this stage (10 papers), I believe it is enriching: the cluster consistently includes the right foundational context for each new draft. The risk emerges in the second half if the corpus diversifies into sub-domains where 002 and 003 are less relevant, and their accumulated weight continues to pull them into every cluster regardless.

### Tier 2: Secondary hubs (papers 1–6)

| Note | Total weight | Notes |
|------|-------------|-------|
| z20260322-008 | 31.9 | RAG/Corpus Governance (post-SPLIT) |
| z20260322-006 | 24.9 | Benchmarks/Evaluation |
| z20260322-004 | 23.9 | LLM/Agent Routing |
| z20260322-007 | 22.9 | Memory Poisoning/RAG Security |
| z20260322-010 | 20.9 | Multi-Agent Scientific Reasoning |
| z20260322-005 | 19.9 | Experience-Driven Systems |

These notes have accumulated healthy activation weight from 3–7 co-appearances. The RAG note (008) retaining high activation after the SPLIT (31.9) confirms the SPLIT was well-executed: the note remained a strong retrieval attractor in its domain.

### Tier 3: Recent notes (papers 7–10)

| Note | Total weight | Notes |
|------|-------------|-------|
| z20260322-016 | 17.9 | MAS with LLMs |
| z20260322-014 | 13.9 | AI Agent Architectures |
| z20260322-012 | 11.9 | Structured Query Generation |
| z20260322-013 | 10.9 | KG Retrieval |
| z20260322-009 | 10.9 | Property Graphs/Query Languages |
| z20260322-015 | 9.9 | Communication Protocols |
| z20260322-011 | 9.9 | Provenance-Enforced Governance |
| z20260322-018 | 8.9 | Agent Foundations |
| z20260322-017 | 5.0 | Last-Mile Delivery (island) |

The long tail is already forming. Note 017 (island) has only 5.0 total weight and 5 edges — it has appeared in clusters but its co-activation with any specific note is low (all edges are weight 1.0). This is the expected signature of an island: retrieved because of embedding similarity to the general domain, but not yet forming a strong structural relationship with any specific note.

### Top activation edges

The most significant edges confirm expected conceptual relationships:

| Edge | Weight | Assessment |
|------|--------|------------|
| 002 ↔ 003 | 23.9 | Correct: procedural memory and trilemma co-appear in every paper about MAS design |
| 001 ↔ 002 | 17.9 | Correct: architecture and memory are co-design concerns |
| 001 ↔ 003 | 14.9 | Correct: architecture design is constrained by the trilemma |
| 003 ↔ 006 | 7.9 | Plausible: evaluation benchmarks reveal trilemma trade-offs |
| 002 ↔ 007 | 7.0 | Correct: memory poisoning is a direct attack on procedural memory |
| 002 ↔ 008 | 6.9 | Correct: RAG is a memory access mechanism |
| 008 ↔ 009 | 6.0 | Correct: graph query languages are used in RAG pipelines |

No high-weight edges look like co-activation inflation from early breadth alone. Every edge I can verify reflects genuine conceptual coupling. This is a healthy activation graph at paper 10.

---

## INSPECTION.md Step 4 — SYNTHESISE Quality

Two SYNTHESISE notes have been created:

**z20260322-003 (Trilemma):** Emergent from corpus. The specific framing — trilemma as the *economic* reason co-design is non-optional — is not something that could be written from domain knowledge alone. It requires the particular combination of the cost/performance/efficiency framing from one paper and the co-design argument from another. **Verdict: emergent, not genetic.**

**z20260322-011 (Provenance-Enforced Governance):** Emergent from corpus. The three-way coupling between governance structure, memory security, and co-design performance trade-offs is a cross-paper insight. The "role-differentiated execution produces provenance as a byproduct" claim is specific to the corpus. **Verdict: emergent, not genetic.**

Both SYNTHESISE notes are better than the benchmark for emergent vs. genetic: they make claims that could not be derived from either source note alone, and they do so with specificity rather than vague bridge language ("these concepts are related"). This is a strong signal that the SYNTHESISE classifier is firing at the right level of cross-paper insight.

**SYNTHESISE rate:** 2 SYNTHESISE notes in 10 papers (20%). The guide's prediction was that SYNTHESISE notes would become more specific as the corpus grew. Both notes are already highly specific — this may be a floor effect rather than a trajectory. Watch whether SYNTHESISE notes in the second half achieve the same specificity or begin citing 3+ sources (indicating the model is making vaguer connections).

---

## INSPECTION.md Step 5 — Late-Paper Note Quality

Not yet applicable (papers 14–19 are the target window). However, the note created in paper 10 (z20260322-018) provides a useful preview: it is a foundational survey of agent reasoning capabilities. This kind of note would normally be created at paper 1 — its late arrival suggests that the paper's content was partially represented in existing notes (primarily 001, 014, 016) and that the CREATE was triggered because a specific angle (reasoning and tool use foundations) was not yet directly addressed. The note has landed cleanly and its See Also links confirm its integration with the existing graph. This is a positive signal for late-paper CREATE behavior.

---

## INSPECTION.md Step 6 — Epistemic Links

**No `contradicts` or `supersedes` links have appeared in 10 papers.**

The L2 schema includes the `links` field and the extraction logic is implemented. The absence of links is not a code failure — it reflects the genuinely constructive nature of this corpus. All 10 papers appear to be building on each other rather than directly challenging prior claims. This corpus is from a single ML sub-domain (multi-agent LLM systems), and papers in this space tend to be additive rather than adversarial.

**Expectation for second half:** Papers in the benchmark set include empirical comparisons and explicit performance claims. If a paper provides empirical results that challenge a claimed advantage (e.g., a paper showing that procedural memory only works above a certain scale threshold, contradicting the general claim that memory augmentation improves all team sizes), L2 should detect the contradiction. The first `contradicts` link will be a milestone worth documenting.

---

## INSPECTION.md Step 7 — STUB Notes

No STUB notes exist. STUB has been removed from the pipeline (CREATE covers isolated new topics). The island note (017) is the closest thing to a STUB — domain-specific, few connections, low activation weight. But it is a fully formed permanent note, not a placeholder. **Verdict: pass.**

---

## INSPECTION.md Step 8 — Confidence Outliers

All notes showed `confidence: 0.7` in their frontmatter — identified as a bug: `store.py` was hardcoding 0.7 for all CREATE/SYNTHESISE/SPLIT operations rather than passing through `result.confidence`. Fixed and all 18 notes backfilled from log data.

**Corrected confidence distribution:**

| Note | Confidence | Operation |
|------|-----------|-----------|
| z20260322-001 | 0.99 | CREATE |
| z20260322-007, 008, 009, 010, 015, 016 | 0.92 | CREATE |
| z20260322-006 | 0.85 | CREATE |
| z20260322-002 | 0.85 | SYNTHESISE |
| z20260322-014, 017, 018 | 0.82 | CREATE |
| z20260322-011 | 0.78 | SYNTHESISE |
| z20260322-004, 005 | 0.78 | CREATE |
| z20260322-003 | 0.72 | SYNTHESISE |
| z20260322-012, 013 | 0.72 | SPLIT (2nd half) |

**Important caveat on interpreting confidence:** These values reflect how certain the classifier was about the *routing decision* — SYNTHESISE vs. INTEGRATE, CREATE vs. UPDATE — not the quality of the note produced. z20260322-003 (the Trilemma note, the strongest SYNTHESISE in the corpus) came in at 0.72 because L1 was less certain whether the bridging insight warranted SYNTHESISE rather than INTEGRATE. The SPLIT notes (012, 013) are also at 0.72 — L3's confidence in the structural decision, not an assessment of note content. High confidence means the classifier found the decision obvious; low confidence means it was a harder call. These are correlated but not equivalent to note quality.

No notes below 0.7 exist in the current store. The lowest values (0.72) are on the two SYNTHESISE and two SPLIT notes — all cases where the classifier was making a genuinely difficult structural judgement.

---

## Hot Note Trajectory

At paper 10, **16 of 18 notes are above the 8,000-char L3 threshold** (using rough body-size estimates). The entire store is in the EDIT/SPLIT zone. This is a consequence of:

1. **Within-paper accumulation:** A note CREATEd by draft A can be UPDATEd by drafts B and C from the same paper, exceeding the L3 threshold before any L3 evaluation
2. **Cross-paper accumulation:** Notes below the threshold after a paper can exceed it after the next paper's UPDATE

**Implications:**
- L3 will fire on virtually every UPDATE in the second half
- The EDIT/SPLIT balance is now critical: if L3 over-EDITs, the store stagnates into a collection of overstuffed notes; if it over-SPLITs, the fragmentation problem returns
- The new L3 criterion ("different problem domains or research traditions") was designed to address exactly this situation and has been validated on 4 test cases

**Notes most likely to trigger SPLIT next:**
- **z20260322-002** — procedural memory taxonomy vs. procedural memory as learning mechanism (borderline: both facets serve the same reader)
- **z20260322-001** — multi-agent engineering patterns vs. formal MARL theory (plausible SPLIT: different research traditions)
- **z20260322-015** — communication protocols vs. zero-trust security standards (need to read to assess)

---

## Merge Candidate Registry

Three potential merge signals have appeared:

### Candidate 1: 001 × 014 × 016
**Evidence:** Title overlap — "Multi-Agent Architectures for Workflow Automation" (001), "AI Agent Architectures and Multi-Agent Systems" (014), "Multi-Agent Systems with Large Language Models" (016) — three notes covering substantially overlapping conceptual territory. Activation edges: 001↔014 = 2.99, 001↔016 = 3.98, 014↔016 not confirmed. This is a L2 forced arbitration signal: the routing decision between these three for any incoming draft about multi-agent architectures will be a near-coin-flip.

**Severity:** High. If papers 11–20 consistently route to all three, the signal will compound.

### Candidate 2: 002 × 010
**Evidence:** Both cover memory in multi-agent systems, though 002 is about procedural memory specifically and 010 is about multi-agent scientific reasoning (which may include a memory component). Need to read 010 to assess. Activation edge: 002↔010 = 5.99 (moderate; suggests co-retrieval but not necessarily content overlap).

**Severity:** Low until 010 is read.

### Candidate 3: 007 × 008
**Evidence:** Memory Poisoning (007) and RAG Corpus Governance (008) are both in the security/integrity space for memory and retrieval. The 002↔007 (7.0) and 002↔008 (6.9) activation edges are nearly identical, suggesting the routing system treats them similarly. Activation edge 007↔008 not confirmed.

**Severity:** Low — different enough problem frames that an experienced reader would search for them separately.

The strongest case for MERGE infrastructure is Candidate 1. If 001, 014, and 016 continue to co-appear in L1 clusters without a clear routing preference, this is the first case where a scheduled curation MERGE would provide clear value.

---

## Pipeline Decisions: Second-Half Predictions

**Probability distribution for papers 11–20:**

- **Most UPDATEs will trigger L3:** Virtually every UPDATE will target a note above threshold. The EDIT/SPLIT balance in the second half will determine whether the store grows to ~36 notes or ~45+.

- **Expected SPLITs:** 3–5 in the second half, if L3 is correctly calibrated. Primary candidates: 002, 001, 015.

- **Expected CREATEs:** 5–8 new notes from genuinely novel domains or angles not yet represented. Late-paper specificity will be the test.

- **Expected SYNTHESISE:** 1–3 more. With 18 notes to potentially bridge, the probability of a cross-paper synthesis opportunity is high. Watch for SYNTHESISE notes that cite 3+ targets — that would indicate the L1 threshold for SYNTHESISE is too loose.

- **First `contradicts` link:** Possible but not certain. Depends on corpus composition.

---

## Key Observations and Risks

**What's working:**

1. **Note quality is high across the board.** No notes read as mere abstracts or summaries. The `_NO_SOURCE_REFS` guideline is holding.
2. **SYNTHESISE notes are genuinely emergent.** Both 003 and 011 make claims that required cross-paper synthesis.
3. **The L3 re-balancing is working.** Post-paper-6 rewind produced three well-focused notes from what was one bloated one. No bad SPLITs since.
4. **The activation graph is honest.** Every high-weight edge reflects genuine conceptual coupling, not just co-occurrence inflation.
5. **Island notes are landing cleanly** (017, 018) — they integrate with the graph through See Also links even if they don't form strong activation edges.

**Risks to watch:**

1. **Store-wide hot note saturation.** 16/18 notes above L3 threshold means every UPDATE triggers L3. This is a system stress test for the EDIT/SPLIT balance. If L3 over-EDITs throughout the second half, the store will contain 18+ overstuffed notes. If it over-SPLITs, fragmentation returns.

2. **Co-activation confound deepening.** The 002-003-001 triad will continue to dominate every cluster. Once their activation weight is 20–30× the newest notes (possible by paper 15), they become unavoidable attractors regardless of semantic relevance. The benchmark tasks will need to be designed with this in mind — any task that requires retrieving a late-paper note in isolation from the foundational triad will be harder than the embedding distance alone suggests.

3. **Multi-agent architecture note fragmentation** (001, 014, 016). Three notes covering similar ground. L2 will need to make increasingly subtle arbitration decisions between them. Worth reading 014 and 016 carefully in the second half to assess whether these should be merged before the benchmark.

4. **z20260322-002 is at risk of becoming unmanageable.** At ~15,900 body chars, it is the densest note in the corpus. If L3 EDITs it repeatedly rather than SPLITting, it could grow further. The new L3 criterion *should* trigger a SPLIT on next contact — procedural memory as learning mechanism and cognitive memory architecture taxonomy are arguably different enough research traditions. But this is the hardest call in the current corpus.

5. **No `contradicts` links yet.** The feature is implemented but the corpus has not generated conditions for it. If the second half also produces no links, the feature is correct but inert for this corpus. That is not a failure — it is information about corpus character.

---

## Second-Half Watchlist

In priority order:

1. **Next UPDATE to z20260322-002** — does L3 SPLIT correctly? If EDIT, is the note still coherent?
2. **Next UPDATE to z20260322-001** — same question; the MARL theory addition may push toward SPLIT
3. **z20260322-015** (not yet read) — at 16,337 chars, this is the second largest note; need to understand its content before predicting L3 behavior
4. **z20260322-010** (not yet read) — multi-agent scientific reasoning; need to assess whether it overlaps with 002 or 001
5. **Co-appearance of 001, 014, 016** — if all three appear in L1 cluster for the same paper, the merge case is strengthening
6. **First `contradicts` link** — document context carefully when it appears
7. **Papers 14–19** — are CREATEs specific and self-contained, or do they dissolve into existing hub notes?

---

## Summary Judgment at Paper 10

The store is in good health at the halfway point. Pipeline decisions have been correct. Note quality is high. The SYNTHESISE notes are genuinely emergent. The activation graph reflects conceptual reality. The one significant structural intervention (L3 prompt rebalancing at paper 6) appears to have been the right call.

The second half will stress-test three things: (1) whether the store can handle the cascade of L3 decisions as every UPDATE hits an above-threshold note, (2) whether late-paper CREATEs achieve specificity and retrievability independent of the foundational triad, and (3) whether the multi-agent architecture note cluster (001, 014, 016) remains coherent or signals the first genuine need for a MERGE operation.

The benchmark will be hardest on retrieval tasks that require isolating a late-paper concept from early-paper attractors. The activation graph's current structure — a dense early cluster with a long tail of newer notes — is exactly the distribution that tests whether embedding-plus-activation retrieval can surface specific knowledge against high co-activation noise.
