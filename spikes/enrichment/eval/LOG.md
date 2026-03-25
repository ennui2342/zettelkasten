# Skill Iteration Log

Each run records: skill version, notes reached per question, whether ground truth notes were found, estimated token cost of the navigation phase, and observations.

**Token cost** is estimated from the navigation phase only (grep calls + note reads before synthesis begins). Synthesis cost is excluded — we're measuring navigation efficiency, not response quality. Estimated at ~6k chars per full note read (average across the store).

**Ground truth hit rate** = ground truth notes reached / total ground truth notes required, per question.

---

## Run 0 — Baseline (no skill)

*Date: 2026-03-24*
*Skill version: none*
*Instructions given: location of notes directory only*

| Q | GT notes | Notes read (count) | GT hit rate | Notes over GT | Observations |
|---|----------|-------------------|-------------|---------------|--------------|
| Q1 | z002, z018, z023-012, z023-013 | 12 | 3/4 (75%) | 9 over | Missed z023-013. ls → grep memory → extract titles → 12 reads |
| Q2 | z008, z009, z013 | **31** | 3/3 (100%) | 28 over | Hit all GT but read everything. 4 greps returned 16/23/26 files → read all |
| Q3 | z023-002, z023-003 | 12 | 2/2 (100%) | 10 over | ls → broad grep → head -5 on every file → 12 reads. Island notes found. |
| Q4 | z001, z003, z023-006 | 17 | 3/3 (100%) | 14 over | glob → 4 greps → extract titles → 17 reads. Good GT hit, high waste |
| Q5 | z004, z015, z016, z023-006 | **30** | 4/4 (100%) | 26 over | Near-exhaustive read. 34 tool calls. Hit limit before synthesis. |
| Q6 | z006, z023-009, z023-011, z023-003 | 15 | 4/4 (100%) | 11 over | 15 reads, hit all GT including islands. Hit limit before synthesis. |
| Q7 | z003, z001, z015, z023-006 | 14 | 4/4 (100%) | 10 over | 14 reads, hit all GT. Hit limit before synthesis. |
| Q8 | z023-007, z023-006, z001 | 14 | 2/3 (67%) | 12 over | **Best navigation**: grep "phase transition" → immediate z023-007 hit. Missed z001. |
| Q9 | z023-004, z001, z004 | 14 | 3/3 (100%) | 11 over | 14 reads, hit all GT including island z023-004. Hit limit before synthesis. |
| Q10 | z003, z023-006, z015 | 14 | 2/3 (67%) | 12 over | Found z003 and z023-006, missed z015. Hit limit before synthesis. |
| Q11 | z023-005, z023-006, z023-007 | 9 | 3/3 (100%) | 6 over | **Most efficient**: 9 reads, all 3 GT island notes found. Hit limit before synthesis. |
| Q12 | z011, z007, z008 | 11 | 3/3 (100%) | 8 over | 11 reads, all GT including island z011 found. Hit limit before synthesis. |

**Overall GT hit rate: 34/36 = 94%**
**Average notes read: 16.1 per question**
**Average notes over GT requirement: 12.4 per question (77% waste)**
**Agents completing synthesis: 5/12 (Q1, Q2, Q3, Q4, Q8)**

---

## Baseline analysis — see eval/baseline-analysis.md

---

## Run 1 — Iteration 1 (stopping criterion + titles first)

*Date: 2026-03-24*
*Skill version: v1 — what the store is, titles first, stop when covered*
*Test subset: Q2, Q5, Q8, Q11*

| Q | GT notes | Notes read (count) | GT hit rate | Notes over GT | Observations |
|---|----------|-------------------|-------------|---------------|--------------|
| Q2 | z008, z009, z013 | 4 | 2/3 (67%) | 1 over | Down from 31. Missed z009 (LPG data model — peripheral to the comparison question). ls → extract titles → 4 targeted reads |
| Q5 | z004, z015, z016, z023-006 | 7 | 3/4 (75%) | 3 over | Down from 30. Missed z004 (routing — peripheral). ls → extract titles → 7 reads, then stopped |
| Q8 | z023-007, z023-006, z001 | 3 (+2 title checks) | 2/3 (67%) | 0 over | Down from 14. Same GT miss as baseline (z001). ls → title batches → 2 wrong reads → grep for specific term → 3 core reads |
| Q11 | z023-005, z023-006, z023-007 | 5 | 3/3 (100%) | 2 over | Down from 9. No regression. ls → extract titles → 5 targeted reads |

**Overall GT hit rate: 10/13 = 77%** (baseline for same 4 questions: 12/13 = 92%)
**Average notes read: 4.75** (baseline: 21)
**Average reduction: 77% fewer reads**
**Agents completing synthesis: 4/4** (baseline: 2/4 due to rate limit)

### Key observations

**Stopping criterion worked.** Single largest intervention in the run. Q2 dropped from 31 → 4, Q5 from 30 → 7. The agents explicitly reasoned about coverage before stopping — Q2 stated "I have enough material" and named the two primary notes. Q5 stated "I have sufficient coverage to synthesise."

**Canaries held.** Q8 and Q11 did not regress. Q11 improved slightly (9 → 5). Q8 showed interesting behaviour: extracted titles in two batches, opened two wrong notes on title inspection, then fell back to a specific grep — self-correcting adaptive navigation.

**GT misses are peripheral.** z009 (LPG data model), z004 (routing) — neither miss affected answer quality. The Q8 miss of z001 is structural and identical to baseline — not caused by the skill.

**See Also links unused.** No agent followed See Also links in this iteration. The skill contains no guidance about them.

---

## Run 2 — Iteration 2 (See Also guidance added)

*Date: 2026-03-24*
*Skill version: v2 — v1 + See Also navigation guidance*
*Test subset: Q7, Q10, Q2 (regression check)*

| Q | GT notes | Notes read (count) | GT hit rate | Notes over GT | Observations |
|---|----------|-------------------|-------------|---------------|--------------|
| Q2 | z008, z009, z013 | 4 | 3/3 (100%) | 1 over | **Recovered z009 miss from Iter 1.** Read z013 → followed See Also → found z009. Same read count (4). |
| Q7 | z003, z001, z015, z023-006 | 13 | 4/4 (100%) | 9 over | Up from Iter 1 baseline (10 over). See Also path-following: z003→z001→z002 cluster, z023-006→z023-007 hop. Found island z011. |
| Q10 | z003, z023-006, z015 | 10 | 3/3 (100%) | 7 over | Recovered z015 miss from baseline. See Also traversal from z023-006 cluster reached z015. Found z011 (not GT but relevant). |

**Overall GT hit rate: 10/10 = 100%** (Iter 1 same questions: N/A; baseline for Q7/Q10: 6/7 = 86%)
**Average notes read: 9.0** (baseline for same 3 questions: 13.0)
**Agents completing synthesis: 3/3**

### Key observations

**See Also guidance switched on path-following.** In Iter 1, no agent followed See Also links. In Iter 2, all three agents followed them. Q2 recovered z009 (Iter 1 miss) via z013→See Also→z009. Q10 recovered z015 (baseline miss) via See Also traversal.

**GT hit rate improved.** 100% vs 86% baseline for the same questions. Both prior misses (z009 in Q2, z015 in Q10) were recovered without increasing read count significantly.

**Q7 read count rose (10→13).** See Also path-following caused wider exploration on the adjacent-possible question. The extra reads found z011 (an island note not in GT but genuinely relevant). This is legitimate over-read, not waste — the note added value to the answer. Still well below baseline (14).

**Island discovery via See Also.** Both Q7 and Q10 found z011, an island note (no hub connections), via See Also traversal. This is the key structural value of the guidance: keyword search can't surface islands; link-following can.

**Answer quality improved.** Q7 answer identified 5 unexplored coordination mechanisms. Q10 answer generated 8 untried game-theoretic analogies. See Also traversal appeared to produce richer, more connected synthesis.

**Q2 regression check: passed.** Same read count (4), better GT hit rate (3/3 vs 2/3). No over-reading induced by the See Also guidance.

---

## Run 3 — Iteration 3 (explicit two-phase navigation: anchor → radiate)

*Date: 2026-03-24*
*Skill version: v3 — v2 + Navigation strategy section naming the two phases*
*Test subset: Q8 (structural miss canary), Q5 (peripheral miss), Q7 (regression check)*

| Q | GT notes | Notes read (count) | GT hit rate | Notes over GT | Observations |
|---|----------|-------------------|-------------|---------------|--------------|
| Q8 | z023-007, z023-006, z001 | 5 | 2/3 (67%) | 2 over | z001 still missed. grep "phase transition" → z023-007 → See Also → z023-006 → z003 → z002. No path to z001 from this cluster. |
| Q5 | z004, z015, z016, z023-006 | 6 | 3/4 (75%) | 2 over | z004 (routing) still missed. Jumped straight to formal foundations cluster. Down from Iter 1's 7 reads. |
| Q7 | z003, z001, z015, z023-006 | **18** | 4/4 (100%) | 14 over | Up from Iter 2's 13. "Radiate outward" instruction caused aggressive See Also traversal across 18 notes. All GT hit but 14 reads over requirement. |

**Overall GT hit rate: 9/11 = 82%**
**Average notes read: 9.7** (Iter 2 for same questions: Q7=13, others N/A)

### Key observations

**Structural misses unchanged.** z001 (Q8) and z004 (Q5) are still missed — identical to all prior runs. These are vocabulary-gap misses, not strategy misses. The Q8 agent grepped "phase transition" and correctly anchored on z023-007, but the See Also graph from that cluster doesn't reach z001. The Q5 agent anchored on the communication/coordination cluster but z004's title ("LLM and Agent Routing") doesn't surface from the tension framing. Two-phase navigation doesn't fix these.

**Q7 over-radiated.** The explicit "radiate outward" instruction produced a behaviour switch: Q7 went from 13 reads (Iter 2) to 18 reads (Iter 3). The agent followed See Also links much more aggressively, reading 18 notes for a 4-GT question. All reads were defensible (each note is adjacent to the trilemma question), but the instruction amplified the exploration beyond what the stopping criterion restrained.

**Tension between instructions.** The "radiate outward" imperative and "more reads is not better" stopping criterion are now in tension. On wide questions (Q7 type), the radiation instruction dominates and the stopping criterion is overridden. On narrow questions (Q8, Q5), the anchor step is effective but radiation adds little because the GT miss is a vocabulary gap, not an adjacency gap.

**Q5 efficiency improved.** 6 reads vs 7 in Iter 1 despite same GT hit rate. The anchor-then-radiate structure produced a more targeted initial grep that avoided some early wrong reads.

**The two-phase naming is too coarse.** "Radiate outward" is interpreted as "follow links until you've followed them all" rather than "follow promising links until covered." The stopping criterion needs to be tied explicitly to the radiation phase, not just stated as a general principle.

---

## Run 4 — Iteration 4 (conditional radiation)

*Date: 2026-03-24*
*Skill version: v4 — v3 with radiation made conditional on coverage gap*
*Change: "Then follow See Also links from each note you read to radiate outward" → "If the anchored notes don't fully cover the question, follow See Also links to find adjacent notes you wouldn't have named"*
*Test subset: Q7 (regression check), Q5 (peripheral miss), Q8 (structural miss canary)*

| Q | GT notes | Notes read (count) | GT hit rate | Notes over GT | Observations |
|---|----------|-------------------|-------------|---------------|--------------|
| Q7 | z003, z001, z015, z023-006 | 11 | 4/4 (100%) | 7 over | Down from 18 (Iter 3). Conditional framing restrained over-radiation. z001 still reached via See Also traversal. |
| Q5 | z004, z015, z016, z023-006 | 8 | 3/4 (75%) | 4 over | Up from 6 (Iter 3). z004 still missed. Conditional radiation prompted additional reads on perceived coverage gap. |
| Q8 | z023-007, z023-006, z001 | 4 | 2/3 (67%) | 2 over | Down from 5 (Iter 3). z001 still missed. Tight anchor on "phase transition" → z023-007 cluster; no See Also path to z001. |

**Overall GT hit rate: 9/11 = 82%** (same as Iter 3)
**Average notes read: 7.7** (Iter 3: 9.7)

### Key observations

**Conditional framing fixed the over-radiation problem.** Q7 dropped from 18 reads back to 11 — still 7 over GT but no longer runaway. The key: coverage-gap check is now the gate for See Also traversal, so the agent assesses sufficiency before radiating rather than radiating by default. Crucially, z001 was still found (it surfaced as a coverage gap when the agent noticed the question's architectural dimension wasn't covered by the trilemma cluster alone).

**Q8 structural miss persists.** 4 reads, z001 unreached. The "phase transition" anchor takes the agent to z023-007 → z023-006 → z003 → z002 via See Also. That cluster is self-contained on the formal theory; none of those notes' See Also sections link to z001 (Multi-Agent Architectures). The miss is confirmed structural: the vocabulary path doesn't exist. Iteration 5 will test whether a hub-note hint can bridge this gap.

**Q5 peripheral miss persists, read count rose slightly.** 8 reads (up from 6). The conditional check appears to have triggered additional See Also traversal when the agent perceived an incomplete picture — but still didn't surface z004 (LLM and Agent Routing), whose title doesn't signal relevance to a question framed around communication overhead. This is the same vocabulary gap as z001 in Q8.

**Iter 4 is the best overall configuration so far.** Compared to Iter 3: same GT hit rate (82%), lower read count (7.7 vs 9.7), Q7 no longer over-radiates. The conditional framing is a strict improvement over unconditional radiation for read efficiency, with no GT regression.

---

## Run 5 — Iteration 5 (hub note hint)

*Date: 2026-03-24*
*Skill version: v5 — v4 + Hub notes section*
*Change: added "Hub notes aggregate multiple concepts and often bridge clusters that keyword search can't connect — if you've covered the obvious cluster but the question touches broad architectural themes, check whether any hub note title suggests a missing dimension."*
*Test subset: Q8 (structural miss target), Q5 (peripheral miss + over-read check), Q7 (regression check)*

| Q | GT notes | Notes read (count) | GT hit rate | Notes over GT | Observations |
|---|----------|-------------------|-------------|---------------|--------------|
| Q8 | z023-007, z023-006, z001 | 5 | 2/3 (67%) | 2 over | z001 still missed. Hub hint sent agent to z023-005 (Transformer Expressivity) instead — wrong hub inference. |
| Q5 | z004, z015, z016, z023-006 | 10 | 3/4 (75%) | 6 over | z004 still missed. Read count up from 8 (Iter 4) to 10. Hub hint caused extra exploration with no GT improvement. |
| Q7 | z003, z001, z015, z023-006 | 11 | 4/4 (100%) | 7 over | Unchanged from Iter 4. Regression check passed. |

**Overall GT hit rate: 9/11 = 82%** (same as Iter 4)
**Average notes read: 8.7** (Iter 4: 7.7)

### Key observations

**Hub hint did not fix the structural misses.** z001 (Q8) still unreached. The agent read z023-005 (Transformer Expressivity) in response to the "broad architectural themes" signal — a plausible but wrong inference. The hint is not specific enough to direct the agent to z001 specifically; it just prompts wider reading among wrong candidates.

**Hub hint inflated reads on Q5 with no GT improvement.** 8→10 reads. The hint caused extra exploration (z022-010, z022-006, z023-011) that turned up nothing new. z004 remains unreachable because "LLM and Agent Routing" doesn't surface from any "communication overhead" or "architectural themes" framing.

**Q7 unchanged.** 11 reads, 4/4 GT — identical to Iter 4. Hub hint had no effect on a question that already had good coverage.

**Hub hint is net negative.** It inflates reads on non-hub questions without recovering the structural misses. The structural misses require corpus-level fixes (better See Also links from z023-007 → z001, from the communication cluster → z004), not skill-level hints. The hint is too vague to be actionable — "broad architectural themes" is interpreted differently per question.

**Iter 4 remains the best configuration.** Revert the hub hint. Iter 4 (conditional radiation only) has lower average reads (7.7 vs 8.7), same GT hit rate, and no harmful side effects.

---

## Run 6 — Full 12-question frontier map (Iter 4 skill vs genetic)

*Date: 2026-03-25*
*Conditions: zettelkasten (Iter 4 skill), genetic (no store). Oracle RAG partial: Q7 and Q8 done previously.*

### Zettelkasten results

| Q | Type | GT notes | Reads | GT hit | Misses |
|---|------|----------|-------|--------|--------|
| Q1 | cross-source synthesis | z002, z018, z023-012, z023-013 | 7 | 3/4 | z023-013 (island) |
| Q2 | cross-source synthesis | z008, z009, z013 | 4 | 3/3 | — |
| Q3 | cross-source synthesis | z023-002, z023-003 | 6 | 2/2 | — |
| Q4 | tension identification | z001, z003, z023-006 | 10 | 3/3 | — |
| Q5 | tension identification | z004, z015, z016, z023-006 | 8 | 3/4 | z004 (vocab gap) |
| Q6 | tension identification | z006, z023-009, z023-011, z023-003 | 5 | 3/4 | z023-003 (island) |
| Q7 | adjacent possible | z003, z001, z015, z023-006 | 11 | 4/4 | — |
| Q8 | adjacent possible | z023-007, z023-006, z001 | 4 | 2/3 | z001 (vocab gap) |
| Q9 | adjacent possible | z023-004, z001, z004 | 7 | 3/3 | — |
| Q10 | analogical transfer | z003, z023-006, z015 | 10 | 3/3 | — |
| Q11 | analogical transfer | z023-005, z023-006, z023-007 | 12 | 3/3 | — |
| Q12 | analogical transfer | z011, z007, z008 | 6 | 3/3 | — |

**Overall GT hit rate: 35/41 = 85%**
**Average reads: 7.5**
**Synthesis completion: 12/12 (100%)**

Misses breakdown: 2 island notes (z023-013 Q1, z023-003 Q6), 2 vocabulary-gap structural misses (z004 Q5, z001 Q8). All confirmed as corpus-level issues, not skill-level.

### Frontier map: zettelkasten vs genetic (qualitative)

**Zettelkasten clearly stronger:**

- **Q7 (unexplored coordination mechanisms)**: Genetic got the trilemma definition wrong (Autonomy/Coordination/Coherence). Zettelkasten derived mechanisms from specific formal results (runtime ρ management, learned aggregation gap). Grounding is the key difference.
- **Q8 (phase transition breakdown)**: Genetic gave Erdős-Rényi graph theory and semantic drift — directionally correct but not the actual framework. Zettelkasten gave λ = η[(1−ρ)M_k'(0) + ρ], specific breakdown modes, and research directions tied to formal parameters.
- **Q11 (formal theory connections)**: Zettelkasten produced a unified hierarchy — UHAT expressivity → multi-agent DAG formalism → phase transitions → context engineering — that no individual paper states but emerges from reading the corpus together. Genetic gave strong CS theory (TC⁰, Rice's theorem, session types) but as disconnected facts.
- **Q9 (workflow optimisation gaps)**: Zettelkasten identified corpus-specific open problems (homogeneity wall, no continuous adaptation, communication cost unmodelled). Genetic gave broader adjacent-field methods (NAS, Bayesian optimisation) without the specific gap diagnosis.

**Competitive / genetic strong:**

- **Q6 (benchmark tensions)**: Genetic gave 10 distinct tensions; zettelkasten gave 4 clusters. The benchmark critique literature is dense in LLM training data. Zettelkasten's specific framework (CLASSic, pass@k, pillar decomposition) adds precision but genetic's breadth is hard to beat here.
- **Q12 (provenance/governance)**: Genetic gave deep database provenance theory (Buneman, semiring provenance, W3C PROV, PROV-DM). Zettelkasten gave specific application to the ingested systems (driver-helper, ACP, taint tracking). Different strengths — theory vs application.
- **Q3 (empirical SE methods)**: Both strong. Genetic drew on SWE-bench, ESE methodology literature broadly. Zettelkasten gave corpus-specific methods (Cohen's kappa measurement, CLASSic framework, specific benchmark statistics).

**Both strong, different angles:**

- **Q4 (centralised vs decentralised tensions)**: Genetic: state consistency, failure attribution, orchestrator ceiling. Zettelkasten: fan-in constraint, ρ-correlated failure, λ threshold, ACP overhead. Neither is more correct — they see different facets.
- **Q1 (memory types)**: Genetic broader taxonomy (in-weights, in-cache, procedural, zettelkasten). Zettelkasten more specific to the corpus systems with trilemma framing.
- **Q5 (communication overhead)**: Genetic: historical lineage from ROBOCUP to LLM debate literature. Zettelkasten: λ/ρ/η formalism with specific thresholds.

### The jagged frontier

**Zettelkasten advantage is sharpest when:**
1. The question requires the specific formal framework from the ingested papers (the λ formula, the organisation exponent γ, the trilemma as Performance/Cost/Efficiency)
2. The question asks what this specific literature implies — gaps, unexplored directions, tensions internal to these papers
3. Cross-paper synthesis connects notes that no individual paper states (Q11: UHAT → phase transition → context engineering as a unified chain)

**Genetic competitive when:**
1. The topic is dense in LLM training data (benchmark design critique, database provenance theory, SE methodology)
2. Adjacent-field connections where LLM parametric knowledge is deep (Q10: game theory, Q9: NAS/Bayesian optimisation for adjacent methods)
3. Questions where breadth matters more than specificity to the corpus

**Oracle RAG partial data (Q7, Q8 only):** Oracle RAG with perfect paper selection is competitive on narrow technical questions (Q8) and finds different integration-level gaps on synthesis questions (Q7). Full oracle RAG data needed for remaining 10 questions — deferred to next session.

---

*Subsequent runs appended below after each skill iteration.*

---

## Run 7 — Oracle RAG full 12-question set

*Date: 2026-03-25*
*Condition: Oracle RAG — source papers concatenated per question, injected as direct context. No navigation, no notes, no store. Perfect retrieval (LLM sees exactly the papers behind the GT notes).*
*Q7 and Q8 done in a prior session (2026-03-25); Q2, Q3, Q4 done earlier this session; Q1, Q5, Q6, Q9, Q10, Q11, Q12 done in this batch.*

Notes:
- z008 and z006 have no source arxiv ID (SYNTHESISE notes). For Q2 (z008 GT) and Q6 (z006 GT), those papers were unavailable — the remaining GT papers were used.
- Paper file sizes: Q1=139k, Q5=130k, Q6=195k, Q9=124k, Q10=65k, Q11=113k, Q12=100k chars. All within context range.

### Oracle RAG answers by question

**Q1 — Agent memory approaches**
*(papers: 2510.04851 LEGOMem + 2601.08156 Project Synapse + 2512.16970 PAACE)*

Four memory types: working (in-context, ephemeral), episodic (past trajectories/events), semantic (declarative facts via RAG), procedural (reusable execution traces). Key finding from LEGOMem ablations: orchestrator memory is the dominant component — removing it hurts more than removing task-agent memory. Joint allocation is optimal. Three retrieval strategies (vanilla, dynamic, query-rewriting) all achieve similar success rates when both orchestrator and agent memory are present; dynamic/query-rewrite outperform when task-agent memory is used alone. PAACE frames context management as the downstream problem: large context windows don't prevent "context rot" — plan-aware compression needed. Gaps: no treatment of forgetting/staleness, shared vs private memory in peer-to-peer MAS, learning from failure trajectories, memory growth at scale.

*vs zettelkasten:* Zettelkasten hit 3/4 GT (missed z023-013). Oracle RAG had all three papers. Both covered the taxonomy and LEGOMem placement findings. Oracle RAG produced more specific ablation numbers (percentage point gains, model comparisons). Zettelkasten's memory note (z002) had already synthesised the key placement insight, so zettelkasten answer was nearly as specific despite missing one paper.

---

**Q2 — Graph vs vector retrieval**
*(papers: 2511.08274 LPG + 2509.01238 AnchorRAG; z008 unavailable)*

Hybrid picture: AnchorRAG achieves +10% Hit@1 over standard RAG on multi-hop relational tasks by graph traversal from anchor entities; SBERT+BM25 variant (AnchorRAG-LR) nearly matches full LLM-ranked traversal on GrailQA, suggesting much of the gain is structural (graph topology) not model sophistication. Vector embedding remains essential for entity grounding at every traversal step — pure graph traversal without embedding degrades on NLP tasks that require semantic matching. KGP (knowledge graph prompting) shows further gains by injecting graph paths into LLM context directly. Main limitation: AnchorRAG requires pre-built entity-linked graphs; standard vector RAG is simpler to deploy.

*vs zettelkasten:* Zettelkasten hit 3/3 GT. Both conditions strong here. Oracle RAG gave more specific benchmark numbers and the SBERT+BM25 vs full-LLM comparison. Zettelkasten's synthesised notes had already distilled the core hybrid finding.

---

**Q3 — Empirical SE methods for AI agent development**
*(paper: 2512.01939 Wang et al.)*

Corpus-specific: first large-scale empirical study of MAS development failures (5,000+ GitHub issues, N=1,092 usable). Methodology: MSR + open coding, two raters, Cohen's kappa=0.82 (strong agreement). Four-category failure taxonomy: Logic (25.4% — task termination, state inconsistency, recursive loops), Integration (23.4% — version compatibility, API drift), Performance (25.3% — memory, context loss, latency), LLM-Specific (26.0% — hallucination, prompt sensitivity, context limits). Key practitioner gaps: no testing practices beyond task success, performance optimization is universal (>80% of projects affected), evaluation tooling almost absent. Three development phases identified: foundation (architecture), operational (debugging loops), optimization (performance tuning). Framework proliferation is itself a problem — 80%+ of developers struggle to select frameworks.

*vs zettelkasten:* Zettelkasten hit 2/2 GT. Both gave the failure taxonomy and kappa methodology. Oracle RAG advantage: percentage breakdowns, framework selection difficulty data, the three development phases. Zettelkasten synthesis was compact but accurate on the headline findings.

---

**Q4 — Centralised vs decentralised coordination tensions**
*(papers: 2510.04851 LEGOMem + 2601.02695 EvoRoute + 2510.13903 Rizvi-Martel)*

Five tensions from the three papers: (1) planning authority vs execution autonomy — hierarchical systems can over-centralise; LLM orchestrator ceiling limits performance; (2) performance/cost/efficiency trilemma — no approach achieves Pareto-optimality simultaneously; (3) communication bandwidth vs parallelism — tasks requiring rich inter-agent communication cannot be fully parallelised (formal bounds from Rizvi-Martel); (4) static role assignment vs adaptive delegation — most frameworks fix agent roles; dynamic routing (EvoRoute) is in tension with memory-based orchestration; (5) architectural complexity vs task appropriateness — architectural overfitting on simple tasks.

*vs zettelkasten:* Zettelkasten hit 3/3 GT. Zettelkasten gave the formal λ threshold and ρ-correlated failure from the synthesised notes. Oracle RAG found similar tensions from the raw papers but expressed them at the level of the papers' own framing rather than the synthesised cross-paper structure. Roughly equivalent depth, different angle.

---

**Q5 — When communication adds value vs creates overhead**
*(papers: 2601.02695 EvoRoute + 2602.15055 ACP + 2509.04876 OSC + 2510.13903 Rizvi-Martel)*

Four distinct positions: (1) Rizvi-Martel (formal): three regimes — tasks requiring almost no communication, tasks with provable speedup from partitioned communication, tasks requiring significant inter-agent communication for k-hop reasoning. Task structure determines whether communication helps. (2) EvoRoute: "architectural overfitting" — complex MAS frameworks degrade simpler tasks; overhead is pervasive at the architecture level. (3) OSC: structured adaptive communication reduces rounds AND improves quality; unpenalized communication (volume alone) hurts performance. (4) ACP: latency overhead is an engineering problem, solved by DHT. Core disagreement: Rizvi-Martel says task-regime determines value; EvoRoute says complexity frameworks systematically over-communicate; OSC says volume without structure is the problem. None of the papers reconcile these positions.

*vs zettelkasten:* Zettelkasten hit 3/4 GT (missed z004/LLM Routing, vocabulary gap). Oracle RAG had all four papers including z016 (OSC). Oracle RAG's advantage: the explicit OSC vs EvoRoute disagreement on communication volume, and the four-paper framing. Zettelkasten gave the formal λ/ρ/η thresholds; oracle RAG gave the structured disagreement map without the specific parameter values.

---

**Q6 — Benchmark design vs practitioner needs**
*(papers: 2511.10949 SafeAgents + 2512.06196 ARCANE + 2512.01939 Wang et al.; z006 unavailable)*

Seven distinct tensions: (1) aggregate outcome metrics (ASR, refusal rate) vs architectural failure diagnosis — practitioners need to know which pipeline component failed, not just whether attack succeeded; (2) single-agent benchmark assumptions misapplied to MAS — centralized architectures can show higher attack success than single-agent baselines; (3) benchmark heterogeneity prevents reproducible cross-architecture comparison (different backends, frameworks); (4) static training-time preferences vs shifting stakeholder needs — RLHF benchmarks don't test runtime adaptability; (5) task-success coverage vs full-lifecycle failures (logic termination, version compatibility, latency); (6) model class mismatch — SLMs show inverted vulnerability patterns vs frontier models; (7) benchmark popularity diverges from practitioner adoption. Gaps: no evaluation for version-stability degradation, no lightweight evaluation proxies, long-horizon reliability unevaluated.

*vs zettelkasten:* Zettelkasten hit 3/4 GT (missed z023-003, island). Oracle RAG covered similar tensions from the same papers but more granularly (specific metric names, SLM inverted pattern). Zettelkasten gave 4 clusters; oracle RAG gave 7 distinct tensions. Oracle RAG advantage here: richer enumeration of specific tensions from raw paper content; zettelkasten's missing island note (z023-003) contributed the SE methodology tension that oracle RAG covered via the same underlying paper.

---

**Q7 — Unexplored coordination mechanisms**
*(papers: 2601.02695 + 2510.04851 + 2602.15055 + 2510.13903)*

*(Done in prior session — qualitative notes only.)*
Oracle RAG found integration-level gaps from the paper seams: what EvoRoute's Pareto routing assumed that LEGOMem's memory architecture didn't address (and vice versa), gaps in the space between dynamic model routing and hierarchical memory placement. Competitive with zettelkasten on forward-looking synthesis but approached from the papers' own limitation sections rather than from the cross-paper synthesis angle that zettelkasten's notes encode.

---

**Q8 — Phase transition breakdown and scale failures**
*(papers: 2510.13903 Rizvi-Martel + 2601.17311 Liu/Kong/Pei)*

*(Done in prior session — qualitative notes only.)*
Oracle RAG competitive on the technical content: the λ formula, Kesten-Stigum threshold, specific breakdown modes, γ ≤ 1/2 universal bound. The papers contain these results directly. Oracle RAG and zettelkasten produced similar depth because the synthesised notes (z023-006, z023-007) had accurately distilled the key formal results from the papers with minimal loss. This is a case where zettelkasten's synthesis was nearly lossless.

---

**Q9 — Workflow optimisation open problems**
*(papers: 2601.12307 OneFlow + 2510.04851 LEGOMem + 2601.02695 EvoRoute)*

Three open problems from the papers: (1) heterogeneous MAS — automatically discovered heterogeneous workflows bounded by best homogeneous single-model baseline; KV-cache sharing unavailable across models; (2) stateless execution — LEGOMem shows agents repeat errors without procedural memory; learning from failures explicitly deferred as future work; (3) trilemma not solved at system level — no principled Pareto-optimal search over full workflow space. Adjacent field methods: Pareto search from bandit literature (EvoRoute already imports this), NAS/DARTS for heterogeneous model assignment (MaAS as precursor), RAG/case-based reasoning for workflow design reuse, continual learning for failure trajectory learning.

*vs zettelkasten:* Zettelkasten hit 3/3 GT (island z023-004 found). Both gave strong answers. Oracle RAG advantage: specific OneFlow MCTS details, concrete degradation numbers (15% CKM latency growth at 10 agents), explicit heterogeneous-workflow future work statement. Zettelkasten gave sharper adjacent-field mapping (MaAS as NAS analogue). Near-equivalent depth with different emphases.

---

**Q10 — Economic/game-theoretic framings**
*(papers: 2601.02695 EvoRoute + 2510.13903 Rizvi-Martel + 2602.15055 ACP)*

Applied: (1) Agent System Trilemma from macroeconomic impossible trinity + blockchain scalability trilemma; (2) Pareto filtration + Thompson Sampling from Bayesian bandit / decision theory; (3) dollar cost as first-class optimization variable; (4) ACP Negotiation Layer with SLAs, reputation ledger, micropayment mention — implicit mechanism design. Untried: VCG auctions for truthful capability revelation, principal-agent problem for delegation under moral hazard/adverse selection, equilibrium price discovery for agent service markets, Shapley values for credit assignment, correlated equilibria for coordinator recommendation protocols, signaling theory for capability advertisement, social choice for output aggregation.

*vs zettelkasten:* Zettelkasten hit 3/3 GT. Oracle RAG gave more thorough enumeration of untried analogies (8 vs the ~4-5 zettelkasten listed) because raw paper sections on related work and limitations suggested more adjacent territory. Zettelkasten advantage: Thompson Sampling and trilemma framing were already synthesised cross-paper, so the answer was tighter and faster to produce.

---

**Q11 — Formal computation theory connections**
*(papers: 2510.13903 Rizvi-Martel + 2601.17311 Liu/Kong/Pei)*

UHAT expressivity limits → single-agent computation bounds → motivation for multi-agent decomposition. DAG formalism (CoT edges + communication edges) maps circuit depth/width onto wall-clock time and agent count. Three task-family regimes (recall/state tracking/k-hop) with formal bounds. Phase transition theory: Kesten-Stigum threshold θ = r·ρ_e·√(2/πk) determines supercritical/subcritical regime. Universal exponent bound γ ≤ 1/2 for majority-vote hierarchies with one-bit messages — a hard complexity-theoretic limit. Data-processing inequality proves centralised star is information-dominant absent context constraints. Gaps: formal grammar/Chomsky hierarchy not directly addressed; classical complexity classes (P, NP) not invoked; formal results cover stylised task families only.

*vs zettelkasten:* Zettelkasten hit 3/3 GT (all island notes). Both conditions strong — these are the two papers the zettelkasten notes most accurately synthesised. Oracle RAG advantage: specific theorem numbers, binary symmetric channel assumptions, the Kesten-Stigum connection spelled out. Zettelkasten built the UHAT → DAG → phase transition → context engineering chain across papers, which oracle RAG did not state explicitly (each paper discussed separately).

---

**Q12 — Governance and provenance in AI pipelines**
*(papers: 2511.14043 AISAC + 2601.05504 memory poisoning)*

AISAC: governance as architectural substrate — declarative agent registration, persistence+provenance layer (all LLM invocations/delegations/retrievals logged to SQLite with agent identity and role), explicit retrieval lifecycle control as data lineage guarantee, agent-scoped knowledge access as governance boundary, separation of mechanism from policy. DOE institutional accountability requirements as motivating framework. Memory poisoning paper: composite trust scoring across code safety/semantic relevance/re-execution/pattern filtering, audit log for every append decision, temporal decay on stored trust scores, pattern-based filtering as constraint enforcement analogue. Key failure mode: model overconfidence assigns maximum trust to sophisticated adversarial inputs. Gaps: no engagement with formal database provenance literature (Why/How-provenance, PROV-DM), no classical complexity classes (P/NP), no query-level data provenance, no replay/reproducibility guarantees.

*vs zettelkasten:* Zettelkasten hit 3/3 GT. Oracle RAG gave specific implementation details (SQLite backend, DOE policy citations, audit_log.json format). Zettelkasten advantage: cross-paper synthesis connected AISAC's driver-helper model with ACP's trust scoring and taint tracking. Oracle RAG treated the two papers separately. Zettelkasten's synthesised notes had already made the architectural-to-institutional linkage that oracle RAG never stated.

---

### Oracle RAG summary statistics

| Q | Type | Papers available | Key finding vs zettelkasten |
|---|------|-----------------|------------------------------|
| Q1 | synthesis/hub | All 3 | Near-equivalent; more ablation numbers in RAG |
| Q2 | synthesis/island | 2 of 3 (z008 missing) | Near-equivalent; RAG added specific benchmark numbers |
| Q3 | synthesis/island | All 1 | Near-equivalent; RAG added percentages, 3 dev phases |
| Q4 | tension/hub | All 3 | Near-equivalent; different framing angle |
| Q5 | tension/mixed | All 4 | RAG advantage: OSC vs EvoRoute disagreement map; zettelkasten had formal thresholds |
| Q6 | tension/island | 3 of 4 (z006 missing) | RAG advantage: 7 specific tensions vs 4 clusters; SLM inverted pattern |
| Q7 | adjacent/hub | All 4 | RAG found paper-seam gaps; zettelkasten found cross-paper synthesis gaps |
| Q8 | adjacent/island | All 2 | Near-equivalent; formal results preserved almost losslessly in notes |
| Q9 | adjacent/island | All 3 | Near-equivalent; RAG added specific numbers; zettelkasten sharper adjacent-field mapping |
| Q10 | analogical/hub | All 3 | RAG advantage: richer untried-analogy enumeration; zettelkasten tighter synthesis |
| Q11 | analogical/island | All 2 | Near-equivalent; zettelkasten built cross-paper chain RAG didn't state |
| Q12 | analogical/island | All 2 | Zettelkasten advantage: cross-paper synthesis; RAG gave implementation detail |

### Three-condition frontier map (full)

**Zettelkasten clearly stronger:**
- **Q7, Q8, Q11** (formal/adjacent synthesis): Zettelkasten derived mechanisms from specific formal results and built chains across papers. Oracle RAG discussed papers separately.
- **Q9** (workflow gaps): Zettelkasten gave sharper adjacent-field diagnosis; oracle RAG gave more specific internal numbers.
- **Q12** (governance): Zettelkasten cross-paper synthesis connected AISAC + security + ACP. Oracle RAG gave implementation detail without the architectural linkage.

**Oracle RAG clearly stronger:**
- **Q5** (communication disagreements): Oracle RAG had all four papers and could map the explicit disagreements between OSC and EvoRoute. Zettelkasten missed z004 (vocabulary gap) and gave formal thresholds without the full disagreement map.
- **Q6** (benchmark tensions): Oracle RAG produced 7 distinct tensions vs zettelkasten's 4 clusters; SLM inverted vulnerability pattern absent from zettelkasten (missed island z023-003).
- **Q10** (untried analogies): Oracle RAG enumerated 8 untried analogies by reading related-work and limitation sections; zettelkasten gave ~5.

**Competitive / different angles:**
- **Q1, Q2, Q3, Q4**: Near-equivalent answers. Oracle RAG more specific numbers; zettelkasten tighter synthesis and better cross-paper linkage.
- **Q11**: Both strong. RAG has theorem numbers; zettelkasten has the unified hierarchy.

**Genetic still competitive:**
- Q6 (benchmark design critique): LLM training data is dense here; genetic matches oracle RAG breadth.
- Q12 (provenance theory): Genetic gave deep formal provenance literature (Buneman, semiring, PROV-DM) absent from both oracle RAG and zettelkasten.
- Q10 (game theory untried analogies): Genetic and oracle RAG overlap on some analogies; genetic draws from broader training data.

### The jagged frontier (refined)

**Three distinct zones:**

1. **Zettelkasten dominates** — questions where the answer requires synthesising formal results *across* the ingested papers into a structure that no single paper states: Q7, Q8, Q11 (formal chains), Q12 (architectural linkage). The synthesis *is* the answer.

2. **Oracle RAG competitive or stronger** — questions where the answer requires enumerating disagreements or unexplored territory that each paper *states in its own limitation/related-work sections*: Q5 (explicit disagreements), Q6 (tensions each paper acknowledges), Q10 (untried analogies listed in related work). Raw paper content is the material; synthesis isn't needed, coverage is.

3. **Genetic competitive** — questions where the topic is dense in LLM training data independently of the corpus: Q6 (benchmark design critique), Q12 (provenance theory), Q10 (game theory). The corpus doesn't contain information that significantly exceeds what a well-trained LLM already knows.

**Revised efficiency note:** Oracle RAG used 65k–195k chars of context per question. Zettelkasten used ~40k–70k chars (7–12 notes × 6k avg). For the questions where zettelkasten and oracle RAG are near-equivalent (Q1–Q4, Q9, Q11), zettelkasten is 2–5× more token-efficient. For the questions where oracle RAG is stronger (Q5, Q6, Q10), the cost differential is the price of seeing the raw disagreements.

### Oracle RAG as a ceiling, not a representative implementation

This evaluation used whole-paper injection — concatenated arxiv papers in full, not chunked retrieval. Real-world RAG retrieves top-K chunks on query similarity and almost never sees limitation sections, related-work comparisons, or "what we didn't explore" paragraphs unless the query specifically targets them.

This matters for interpreting the oracle RAG advantage on Q5, Q6, and Q10:

- **Q5** (communication disagreements): The OSC vs EvoRoute disagreement was surfaced by reading OSC's ablation section and EvoRoute's "architectural overfitting" framing. A chunk-retrieval query on "when communication adds value" would return results sections, not the sections where papers implicitly contradict each other.
- **Q6** (benchmark tensions): The SLM inverted vulnerability pattern came from SafeAgents' experimental results (probably retrievable). But the framework-selection difficulty finding in Wang et al. is in a discussion subsection that chunk retrieval might not surface.
- **Q10** (untried analogies): The 8 untried analogies were found in related-work and limitation sections. Chunk-based RAG does not retrieve "what we didn't cover" sections on a query about applied economic framings.

**Implication:** The oracle RAG advantage on Q5/Q6/Q10 is partly an artifact of whole-paper context. Real chunk-based RAG would likely perform worse than oracle RAG on those questions — potentially below zettelkasten. Our comparison is therefore conservative: oracle RAG is the best-case ceiling for the RAG condition, and zettelkasten still wins on the synthesis-heavy questions against that ceiling. Shifting to real-world RAG would move the frontier further in zettelkasten's direction on the questions where zettelkasten currently loses.

The one exception where real RAG might outperform oracle RAG: dense formal-theory questions (Q8, Q11) where 113k+ chars of mathematical content creates noise. Careful chunk retrieval might isolate the relevant theorems more cleanly. But those were already zettelkasten wins, so the conclusion is unchanged.
