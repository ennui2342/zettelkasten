# Benchmarking the Zettelkasten Store: Innovation and Generative Research Tasks

*Design document — drafted 2026-03-17 following first real-data production deployments*

---

## 1. Why a Benchmark, and Why Now

The retrieval workbench built during the spike phase served its purpose: it let us measure and tune the multi-signal fusion that underlies Gather. But the workbench is a proxy measure. It tells us whether the right notes come back when asked for; it says nothing about whether those notes make the agent that uses them more capable.

Now that the system is running against real production data, the question shifts. We are no longer designing in the abstract. The question is whether the system is actually delivering value — and *what kind* of value, relative to alternatives a developer could reach for instead.

The answer to that question is not visible by inspecting the store. A zettelkasten note graph that looks coherent and well-synthesised might still fail to improve agent performance. Conversely, a store that looks rough by inspection might be doing exactly the right thing for the agent's actual tasks. The only way to know is to test the agent doing its tasks.

This document captures the design of a benchmark for doing that — including the reasoning that shaped it, the literature it draws on, and the tradeoffs involved in building it without a research lab.

---

## 2. The Value Hypothesis

Before designing a benchmark, it is worth being precise about what the zettelkasten store claims to do that simpler alternatives do not.

Three memory modes are available to any agent running on a frontier LLM:

**Genetic memory** — knowledge distilled into the model's weights at training time. For a general-purpose frontier model, this is vast and often underestimated. A model trained on the full public internet through mid-2025 knows an enormous amount about machine learning, multi-agent systems, and adjacent fields. This is free at inference time, always available, and often sufficient for tasks that don't require recent or domain-specific knowledge.

**Inference-time memory** — context injected at the start of a query: retrieved chunks (naive RAG), full documents, conversation history. As context windows expand, the naive approach becomes increasingly viable. "Just stuff the relevant documents in" is a real competitor, not a strawman. Its failure modes are well-understood: it scales linearly with corpus size, surfaces conflicting information without reconciling it, and carries no structure that helps the model reason across sources.

**Curated long-term memory** — what the zettelkasten store provides. Documents are not stored raw; they are synthesised into notes during ingestion, with contradictions surfaced, superseded views updated, and connections between ideas made explicit. The corpus grows in *quality* rather than quantity. When the agent retrieves, it gets a distilled, internally coherent representation rather than raw chunks.

The zettelkasten store's claim is specific: **synthesis at ingestion time pays off at retrieval time**, in a way that compounds as the corpus grows and that is qualitatively different from what a larger context window can substitute for.

This claim is testable. The benchmark tests it directly.

---

## 3. Choosing the Right Test

The hardest question in benchmark design is not "how do we measure?" but "measure *what*?"

Early candidate approaches were rejected deliberately:

**Needle-in-a-haystack retrieval** — can the agent find a specific fact buried in a large corpus? This is the dominant paradigm of long-context LLM benchmarks (RULER, HELMET, and their descendants). It is not the right test for a zettelkasten store, because haystack retrieval is a problem the store was never designed to solve. It is, if anything, a task where naive RAG or full-context injection may outperform synthesis — because the answer to a fact-lookup question is most precisely stated in the original document, not in a note that synthesised it with others.

**Conversational memory** — can the agent recall what was discussed last Tuesday? This is the domain of LoCoMo, LongMemEval, and the MemGPT family of benchmarks. Again, not the right test. Session memory is a different design problem; its workloads are different; its evaluation methodology is different.

**General creativity** — is the agent's output more creative? Too broad. Creativity is not a single thing. A benchmark designed around "is this output more creative?" would measure style as much as capability, and would be nearly impossible to evaluate consistently.

The right test came from asking what the store was actually built for. The first consumer of the zettelkasten store is the aswarm research agent — a system designed to ingest streams of papers, blog posts, and technical content nightly, and to support tasks like brainstorming, system design, and identifying research directions. These are **generative tasks that require synthesising across sources** — exactly the tasks that a well-integrated knowledge store should enable better than raw retrieval from raw chunks.

The benchmark should therefore test: *given a corpus of documents on a fast-moving topic, does an agent backed by a zettelkasten store perform better on generative research and innovation tasks than one backed by naive RAG or by training knowledge alone?*

---

## 4. The Innovation Frame

Narrowing from "generative tasks" to **innovation tasks** specifically is both a practical and a principled choice.

Practically: there is a substantial scientific literature on what innovation looks like, how to operationalise it, and how to measure it. This literature gives us vocabulary and validated instruments, rather than requiring us to invent evaluation criteria from scratch.

Principally: innovation is where the zettelkasten value claim is strongest. The store's core mechanisms — cross-source synthesis, contradiction resolution, epistemic linking — are exactly the mechanisms that should enable the *non-obvious connections* and *synthesis of conflicting views* that innovative thinking requires.

The relevant theoretical grounding comes from several converging traditions:

### 4.1 Bisociation (Koestler, 1964)

Arthur Koestler's theory of creative insight — developed in *The Act of Creation* — defines the creative act as **bisociation**: the collision of two previously unrelated "matrices of thought" that, when brought together, produce a moment of recognition that neither matrix alone could generate. This is not gradual synthesis; it is sudden connection.

A zettelkasten note graph, if it is working correctly, is a physical implementation of bisociation potential. When notes from two unrelated streams of literature are connected during integration — because an LLM recognised that a mechanism from one domain addresses a gap in another — the store has done the work of making the bisociation available to the agent. When naive RAG returns chunks from each stream independently, the agent must do that work itself, in context, from raw material.

The benchmark should test whether the store enables bisociative connections that the agent would not make from chunks alone.

### 4.2 The Adjacent Possible (Kauffman; Johnson, 2010)

Stuart Kauffman's concept of the *adjacent possible* — developed by Steven Johnson in *Where Good Ideas Come From* — describes the set of next steps made reachable by the current state of knowledge. Innovation rarely leaps across vast distances; it more commonly takes the step that becomes visible once you are standing at the edge of what is already known.

A synthesised knowledge store should provide a richer map of the adjacent possible than a pile of raw documents. A note that integrates three papers on a topic implicitly marks the boundary of what is known on that topic — and therefore makes it easier to see what lies just beyond. The CREATE benchmark (Schopf et al., 2026) implements this directly, testing whether a system can find non-obvious connecting paths between concepts; their empirical finding confirms the SciMuse result: **less ubiquitous, boundary-positioned concepts are rated more interesting by domain experts**.

### 4.3 Recombinant Innovation (Schumpeter; Weitzman, 1998)

Schumpeter's account of innovation as "new combinations" of existing factors, formalised by Weitzman, provides the economic grounding for why synthesis matters. Value is created not by discovering wholly new things but by combining existing things in ways that have not been tried. A memory store that makes combinations explicit — by integrating ideas at ingestion time — should produce more and better recombinant proposals than one that leaves raw material unstructured.

### 4.4 Divergent Thinking (Guilford, 1967; Torrance, 1966)

J. P. Guilford's taxonomy of divergent thinking — **fluency** (many ideas), **flexibility** (many distinct categories of ideas), **originality** (rare, non-obvious ideas), **elaboration** (developed in sufficient detail to be actionable) — provides the most operationally precise framework for measuring innovation quality. Torrance extended this into validated assessment instruments; Organisciak et al. (2023) subsequently showed these dimensions can be scored reliably by LLMs, with r=0.81 correlation with human raters, via the Ocsai scoring system.

Treating the agent's output like an essay submitted by a graduate student in an innovation programme means asking: is this fluent, flexible, original, and elaborated? These dimensions map directly to the MLR-Judge rubric (Novelty, Significance, Soundness, Feasibility, Clarity) validated against domain experts in the MLR-Bench study.

---

## 5. Corpus and Conditions

### 5.1 Domain

**Multi-agent systems** — specifically the sub-field of LLM-based multi-agent architectures, coordination protocols, memory systems for agents, and emergent agent behaviour. This domain is:

- Fast-moving (new significant papers monthly, genuine open problems)
- Directly relevant to the first consumer (aswarm)
- Well-represented in training data, making the genetic memory baseline strong rather than trivially weak
- Clearly bounded (arxiv `cs.MA`, `cs.AI`, `cs.LG` with multi-agent keywords)

The strength of genetic memory in this domain is a feature, not a problem. If the zettelkasten store cannot improve on a model's training knowledge in a domain the model knows well, that is important signal — it suggests the store's value may only appear for niche or rapidly-moving topics where training coverage is thin.

### 5.2 Temporal Scope

Papers published **after the evaluation model's training cutoff** (August 2025 for Claude Sonnet 4.6) form the corpus. This is the cleanest possible separation:

- Genetic memory condition: the model cannot know these papers
- Naive RAG condition: the model receives chunks from these papers
- Zettelkasten condition: the model receives synthesised notes derived from these papers

A window of approximately six months (September 2025 through February 2026) is expected to yield 50–100 relevant papers — sufficient for meaningful synthesis without overwhelming the ingestion pipeline.

### 5.3 The Three Conditions

| Condition | What the agent has access to |
|-----------|------------------------------|
| **Genetic** | No additional context. Model's training knowledge only. |
| **Naive RAG** | Top-k chunks retrieved from the raw corpus via BM25 + dense embedding (fixed chunk size 512 tokens, k=10, reranked). |
| **Zettelkasten** | Top-20 notes retrieved via the production multi-signal fusion (body_query=0.450, bm25_mugi=0.270, activation=0.180, step_back=0.050, hyde_multi=0.050). |

The naive RAG baseline is defined precisely and held constant. "We beat naive RAG" is only meaningful if the baseline is not a strawman. The baseline uses reranking, not just raw BM25, and is parameterised to be competitive.

The same base model runs all three conditions. The same prompt template is used. Memory mode is the only variable.

### 5.4 Structural Confounds Within the Zettelkasten Condition

The zettelkasten condition has an internal confound that the benchmark design must account for: **ingestion order determines co-activation weight**. Notes created early in a sequential ingestion run appear in more retrieval clusters than notes created later, accumulating co-activation signal that compounds their retrieval score across the entire run. A note created during paper 1 has been a candidate in every cluster formed since; a note created during paper 20 has not. This is not a tuning problem — it is structural.

The dynamic mirrors citation networks. Foundational papers accumulate citations not because they remain the most definitive treatment of a concept but because they named it first and the domain's vocabulary radiates outward from them. In the zettelkasten store, early notes serve the same function: they establish the conceptual vocabulary that later notes extend, and co-activation makes them the default retrieval attractor regardless of whether a later, more specific note would better serve a given query.

Empirically confirmed in the first ingestion run: the "Multi-Agent LLM Systems" note — created from paper 1 — received cross-paper updates from four distinct papers spanning the full run. Some of this reflects genuine semantic breadth; the note was created in an empty store where Form had no existing neighbourhood to refine against, so early drafts are forced to be broad and foundational. Some of it may reflect co-activation inflation. The two signals cannot be cleanly separated in a single sequential run.

The practical consequence for benchmark interpretation: the zettelkasten condition may perform well on tasks where foundational synthesis is sufficient, and underperform its potential on tasks where the best answer lives in late-ingested, specific notes that co-activation has not yet elevated. Task design should account for this — see §6.5.

### 5.5 Corpus Sizing and Cost Model

The benchmark is designed to be run frequently — after significant changes to the integration phase — not just at major milestones. This constraint shapes corpus sizing directly: a run that costs $150 will not happen often; a run that costs $20 will.

**Pipeline cost per paper (Opus-4.6 for LLM, Haiku-4.5 for gather, Voyage-3 for embed):**

| Phase | Calls/paper | Avg input tokens | Avg output tokens |
|-------|------------|------------------|-------------------|
| Form (1× per paper) | 1 | ~11,500 | ~2,000 |
| Gather LLM: step-back + HyDE + MuGI (per draft) | 3× drafts | ~500 each | ~150 each |
| Integrate Step 1 — classify (per draft) | 1× drafts | ~5,000 | ~300 |
| Integrate Step 2 — execute (per draft) | 1× drafts | ~1,700 | ~1,500 |

With ~5 draft notes per paper on average: **~62,500 input / ~13,250 output tokens per paper**. Voyage-3 embeddings are negligible (~$0.06/MTok).

Key lever: routing the 15 gather calls per paper (step-back, HyDE, MuGI) to a fast model rather than Opus saves ~$50–80 on a full corpus run. The first dev subset run used `claude-opus-4-6` for everything and cost ~$13 for 20 papers — consistent with the model above.

**Corpus tier ladder:**

| Corpus size | Approx cost | Use case |
|-------------|-------------|----------|
| 10 papers | ~$10 | Smoke test — does the pipeline run at all? |
| 20 papers | ~$20 | **Development benchmark** — run after each significant change to the integration phase |
| 50 papers | ~$50 | Integration milestone — meaningful synthesis starting, more cross-paper signal |
| 91 papers | ~$95 | Major release benchmark — publishable results |

**The dev subset (20 papers, fixed):** The corpus and task questions are frozen together. Once 24–30 questions are authored against a fixed 20-paper set, every subsequent run is reingest + rerun with a directly comparable score. The subset was deliberately composed for topical overlap and internal tension:

- Memory systems (LEGOMem, EvoRoute) vs. Memory Poisoning — memory as asset vs. attack surface
- OptAgent (optimise communication) vs. Benefits and Limitations of Communication + Rethinking Multi-Agent Workflow — communication value is contested
- ACP unified protocol standard vs. Empirical Developer Practices — standardisation vs. observed practice
- Phase Transition (multi-agent helps only in certain regimes) vs. optimistic framework papers

These tensions are what the tension identification task type needs. The synthesis behaviour (UPDATE, SYNTHESISE) started firing by paper 5, confirming the corpus has enough thematic density.

**Milestone runs** use the full corpus. The download cost is sunk; reingest is the only ongoing expense.

---

## 6. Task Taxonomy

Four task types, selected to map onto the innovation behaviours identified in §4.

### 6.1 Cross-Source Synthesis

The agent is given a design or research question that cannot be answered from any single paper. A good response integrates multiple distinct approaches coherently.

*What it tests:* Whether the zettelkasten store's integration of sources at ingestion time reduces the synthesis work required at query time — and whether the resulting response draws on a wider range of the corpus than raw chunk retrieval.

*Example:* "What are the major approaches to memory in multi-agent systems, and what are the trade-offs between them?"

### 6.2 Tension Identification

The agent is asked to identify unresolved tensions, contradictions, or open questions in the current state of the field.

*What it tests:* Whether the store's explicit handling of contradictions (via `contradicts`/`supersedes` links and UPDATE/SYNTHESISE operations) surfaces tensions that naive RAG would either miss or present as two unreconciled chunks.

*Example:* "What are the fundamental unresolved tensions between centralised and decentralised coordination in LLM agent systems?"

### 6.3 Adjacent Possible Mapping

The agent is asked to identify the most promising unexplored directions given the current trajectory of the field.

*What it tests:* Whether the store provides a richer map of the boundary of current knowledge — enabling the agent to identify the adjacent possible more precisely. Can be partially validated retrospectively: directions suggested by the system may appear as actual papers published after the evaluation window.

*Example:* "Given the current state of multi-agent coordination research, what are the most promising directions that have not yet been substantially explored?"

### 6.4 Analogical Transfer

The agent is asked to apply a mechanism or insight from one area to a problem in another.

*What it tests:* Bisociation potential — whether the store's cross-domain synthesis has made connections between previously unrelated streams visible to the agent.

*Example:* "What mechanisms from the biological or social sciences literature have been applied to multi-agent coordination, and are there other mechanisms that have not yet been tried?"

### 6.5 Task Set Size

First benchmark pass: **24–30 tasks**, 6–8 per type. Tasks authored by prompting an LLM to generate candidate questions from the corpus, filtered by the project author for realism and specificity. Tasks should represent questions a practitioner would actually want answered — not synthetic test items.

Task authoring should deliberately include questions that can only be answered from **late-ingested, specific notes** — not just questions where foundational cross-source synthesis is sufficient. Without this, the benchmark probes only whether the store's early hub notes are useful, which co-activation bias ensures regardless of synthesis quality (see §5.4). Concretely: at least one-third of tasks should target concepts introduced in the second half of the ingestion run, where co-activation weight is low and retrieval must rely on body similarity and BM25 signals rather than accumulated activation.

---

## 7. Evaluation Methodology

### 7.1 The Calibration Problem

A key finding from the RINoBench study (Schopf & Färber, 2026) is that **current LLMs are not well-calibrated absolute novelty judges** — their predicted novelty scores diverge significantly from human gold standards. This is the primary constraint on AI-only evaluation.

The mitigation is to use **blind pairwise comparison** rather than absolute scoring. "Which of these two responses shows better synthesis of the current literature?" is reliably answerable by an LLM judge even when "rate this novelty 1–5" is not. This is the same methodology used by LMSYS Chatbot Arena, and is well-validated for comparative evaluation.

A secondary concern is positivity bias: LLM judges consistently rate LLM-generated outputs higher than human experts do (documented in ICED 2025 CAT study). Pairwise comparison partially mitigates this, since the bias applies equally to both responses being compared. The project author reviews ~20 pairwise judgments to validate that judge reasoning is sensible — not to grade quality, just to catch systematic failure modes.

### 7.2 The Evaluation Stack

**Layer 1 — Automated, reference-free:**

- **Semantic entropy**: sample multiple responses from the same condition; measure semantic cluster diversity across responses. High entropy means the condition produces diverse, non-redundant outputs; low entropy suggests homogenisation (a known failure mode of naive RAG, documented in CHI 2025).
- **CREATE quality × diversity**: embedding-based metrics for bisociative connection quality and diversity, from Schopf et al. (2026). Reference-free; no LLM judge required.

**Layer 2 — LLM-as-judge, pairwise:**

Blind pairwise comparison across the five MLR-Judge dimensions (validated against ML domain experts, no statistically significant difference from human distributions):

1. **Novelty** — does this go beyond what any single source says?
2. **Significance** — does this advance understanding in a meaningful way?
3. **Soundness** — is the reasoning coherent and well-grounded?
4. **Feasibility** — are the proposals or directions actionable?
5. **Clarity** — is the response well-structured and unambiguous?

Judge model: GPT-4o (different from the model under test). Comparison format: present both responses, blinded, ask for each dimension independently. Win rate across pairwise comparisons (Bradley-Terry) is the primary aggregate metric.

**Layer 3 — Project author review:**

Spot-check ~20 pairwise comparison pairs to validate judge reasoning. Not quality grading — just sanity-checking that the judge is engaging with the right things. Particularly important for Novelty, where LLM judge calibration is weakest.

### 7.3 Primary Metrics

| Metric | Type | Layer |
|--------|------|-------|
| Pairwise win rate (overall) | Comparative | 2 |
| Pairwise win rate (by dimension) | Comparative | 2 |
| Pairwise win rate (by task type) | Comparative | 2 |
| Semantic entropy | Absolute | 1 |
| CREATE quality × diversity | Absolute | 1 |

Win rates broken down by task type are the most informative output. If zettelkasten wins on Synthesis and Tension tasks but is indistinguishable from naive RAG on Adjacent Possible tasks, that is specific, actionable signal — it tells us what the store is and is not delivering.

---

## 8. Related Benchmarks

These existing benchmarks are not adopted wholesale but inform the design and serve as sanity-check floors:

| Benchmark | What it tests | Relationship to this work |
|-----------|---------------|---------------------------|
| **MemoryAgentBench** (ICLR 2026) | Architecture comparison across 4 competencies; FactConsolidation tests update/supersedes handling | Run as a floor test — confirms we are not regressing on factual tasks |
| **FRAMES** (Google/Harvard, 2025) | Multi-document synthesis, 2–15 sources, human-authored | Run as a floor test — synthesis quality on a standard dataset |
| **LiveIdeaBench** (Nature Comms, 2026) | Guilford 5-factor scientific ideation, LLM judge panel | Evaluation instrument adopted for our judge rubric |
| **RINoBench** (TU Dresden, 2026) | Novelty judgment rubric + hallucination detection | Rubric and calibration warnings directly adopted |
| **CREATE** (2026) | Bisociative associative creativity metrics | Automated metrics adopted for Layer 1 |
| **MLR-Bench / MLR-Judge** (2025) | Research quality rubric, human-validated | Primary judge rubric adopted |

---

## 9. What Success Looks Like

A positive result is not "zettelkasten beats genetic memory on all dimensions." The model's training knowledge of multi-agent systems is deep; on many tasks it will be sufficient. That is not a failure of the store — it is a baseline confirmation that frontier models are already capable.

A positive result is:

1. **Zettelkasten wins convincingly on Synthesis and Tension tasks** — the two task types most directly dependent on cross-source integration. If it does not win here, the core value hypothesis is not supported.

2. **Zettelkasten wins on temporal accuracy** — responses from the zettelkasten condition reflect developments from after the model's training cutoff that the genetic condition cannot know. This is the cleanest signal available.

3. **Zettelkasten shows higher semantic entropy than naive RAG** — responses are more diverse, suggesting the store introduces distinctive connections rather than converging on the most-retrieved chunks.

4. **Naive RAG wins on nothing important** — if naive RAG consistently outperforms zettelkasten on task types where synthesis matters, that is important signal that the integration overhead is not paying off and the system design should be revisited.

A negative result is also a success, if it tells us clearly what is not working. The benchmark is not a marketing exercise; it is a diagnostic tool.

---

## 10. Benchmark Evolution

This document describes the first pass — deliberately narrow, designed to be buildable by one person without a research lab. As the project matures, several extensions are natural:

- **Expand the corpus window** to 12+ months, testing whether synthesis value compounds with corpus size (the sub-linear growth hypothesis)
- **Add a fine-tuning condition** — if genetic memory + fine-tuning on the corpus outperforms zettelkasten, that is important to know and changes the value proposition
- **Expand to other domains** — test whether the benchmark results generalise beyond multi-agent systems
- **Retrospective validation of Adjacent Possible tasks** — check whether directions the system proposed in 2026 appear as actual papers by 2027

---

## Appendix: Literature Referenced

**Innovation theory**
- Koestler, A. (1964). *The Act of Creation*. Hutchinson. — bisociation
- Guilford, J. P. (1967). *The Nature of Human Intelligence*. McGraw-Hill. — divergent thinking dimensions
- Torrance, E. P. (1966). *Torrance Tests of Creative Thinking*. — standardised assessment
- Kauffman, S. (1993). *The Origins of Order*. Oxford University Press. — adjacent possible (biological origin)
- Johnson, S. (2010). *Where Good Ideas Come From*. Riverhead Books. — adjacent possible (applied)
- Schumpeter, J. A. (1934). *The Theory of Economic Development*. — new combinations
- Weitzman, M. L. (1998). "Recombinant growth." *Quarterly Journal of Economics*, 113(2). — formalisation of recombinant innovation

**Divergent thinking measurement**
- Organisciak, P. et al. (2023). "Beyond Semantic Distance: Automated Scoring of Divergent Thinking Greatly Improves with LLMs." *Thinking Skills and Creativity*. — r=0.81 LLM scoring validation; Ocsai system
- Guzik, E. et al. (2023). "The Originality of Machines: AI Takes the Torrance Test." *Journal of Creativity*, 33. — GPT-4 in top 1% on TTCT
- Stevenson, C. et al. (2022). "Putting GPT-3's Creativity to the (Alternative Uses) Test." ICCC 2022.
- Nature Human Behaviour (2025). "A Large-Scale Comparison of Divergent Creativity in Humans and Large Language Models." — 100K humans; LLMs exceed average but not top-decile humans
- CHI (2025). arXiv:2410.03703. "Human Creativity in the Age of LLMs." — LLM assistance homogenises outputs
- arXiv:2601.20546 (2026). "Beyond Divergent Creativity: CDAT." — novelty conditional on appropriateness; automated scoring

**Innovation benchmarks for LLMs**
- LiveIdeaBench, arXiv:2412.17596 (Nature Comms, 2026). — Guilford 5-factor, LLM judge panel, 1,180 keywords, 41 models
- IdeaBench, arXiv:2411.02429 (KDD 2025). — ranking vs. real papers; feasibility consistently < 0.5
- SciMuse, arXiv:2405.17044. — 100 expert group leaders; low-PageRank concepts rated more interesting
- ResearchBench, arXiv:2503.21248 (2025). — inspiration retrieval + hypothesis composition; 2024 papers only
- InnovatorBench, arXiv:2510.27598 (2025). — runnable code artifacts; frontier models need 11+ hours

**Research quality evaluation**
- MLR-Bench / MLR-Judge, arXiv:2505.19955 (2025). — 9-dim rubric, human-validated, no statistically significant difference from expert distributions
- RINoBench, arXiv:2603.10303 (TU Dresden, 2026). — 1–5 novelty rubric; LLMs not calibrated absolute novelty judges
- arXiv:2601.09714 (2026). "Evaluating Novelty in AI-Generated Research Plans." — Novelty/Feasibility/Interestingness rubric
- AI Scientist, arXiv:2408.06292 (Sakana AI). — automated peer review pipeline; `perform_review.py`

**Associative / bisociation benchmarks**
- CREATE, arXiv:2603.09970 (2026). — associative creativity metrics; quality × diversity × distinctiveness
- ICED (2025). "Exploring the Use of LLMs to Evaluate Design Creativity." — CAT via LLM; positivity bias documented
- G-Eval, arXiv:2303.16634 (EMNLP 2023). — chain-of-thought rubric generation for NLG evaluation

**Memory architecture benchmarks**
- MemoryAgentBench, arXiv:2507.05257 (ICLR 2026). — 4-competency architecture comparison; FactConsolidation
- LoCoMo, arXiv:2402.17753 (ACL 2024). — long-term conversational memory; de-facto leaderboard
- LongMemEval, arXiv:2410.10813 (ICLR 2025). — knowledge updates task category
- FRAMES, arXiv:2409.12941 (2025). — 824 multi-document synthesis questions, human-authored
- GraphRAG-Bench (ICLR 2026). — structured vs. flat RAG comparison

**Caution: Letta filesystem result.** On the LoCoMo benchmark, a simple flat-file system with grep + semantic search (74.0%) outperforms Mem0 graph memory (68.5%) and OpenAI Memory (52.9%). This challenges the assumption that structured memory always outperforms simpler approaches on conversational tasks. The benchmark design in this document specifically targets generative innovation tasks — where the Letta result does not generalise — but the finding should be kept in view when interpreting results.
