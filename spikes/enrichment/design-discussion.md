# Enrichment Spike: Agent Interface Design Discussion

*Discussion date: 2026-03-24*
*Status: Complete — Iter 4 skill stable, full 12-question frontier map logged (LOG.md Run 6–7)*

---

## The question this spike addresses

The benchmark plan (`docs/design/benchmark-innovation.md`) defines what to measure and why, but assumes a specific agent architecture: retrieve top-k notes, inject into context, generate response. Before running the benchmark, we need to establish whether that architecture is the right one — or whether it will undermine the very thing we're trying to demonstrate.

This document captures the design discussion that preceded the spike, including the debates, analogies, and reasoning that shaped the experiment plan. The journey matters: some of the wrong turns illuminate the constraints as clearly as the right answers.

---

## The context consumption problem

The benchmark's three conditions (genetic / naive RAG / zettelkasten) assume a flat retrieval interface. The zettelkasten returns top-20 synthesised notes. At 31 notes averaging ~6k chars each, k=20 retrieval costs ~120k tokens before the response. That is the entire context window of a smaller model, and a substantial fraction of a larger one.

This observation opened a question that goes deeper than tuning: **a memory system that consumes all the context to use is of no practical use.** Context efficiency isn't a nice-to-have — it determines whether the system can be deployed at all.

---

## Two architectural responses

### The subagent oracle

If the zettelkasten is implemented as a subagent, the iterative retrieval and synthesis happens inside the subagent's context window. The parent agent asks a question and receives a compact answer — perhaps 500 tokens rather than 120k. The parent's context cost is the answer, not the notes.

The analogy is a web search subagent: the parent doesn't need to know how to crawl and synthesise web pages, it just needs the result. The subagent is a specialist.

The subagent also cleanly separates concerns: the subagent is responsible for *what is known*, the parent is responsible for *what to do with it*.

### The filesystem exploration analogy

The second response came from asking why Claude Code's approach to large codebases works. Claude Code doesn't load the codebase into context — it navigates it. The key insight is that the agent has **lightweight tools for orientation before committing to expensive reads**: `glob` and `grep` cost almost nothing; `read` costs context. The agent builds a map cheaply, then reads surgically.

Applied to zettelkasten, this suggests a two-tier interface:

- **Cheap orientation:** `search → titles + activation weights` (~2k tokens for 20 candidates)
- **Targeted read:** `get_note(id) → full body` (~6k tokens per note)

The agent scans 20 candidates cheaply, selects 3-5, reads those fully. Total cost: ~32k tokens vs 120k for full retrieval. More importantly, the agent is making an informed selection rather than consuming everything and hoping attention falls on the right parts.

**But this is still one-shot or two-shot.** The deeper lesson from Claude Code wasn't the two-tier structure — it was the iteration.

---

## The iteration insight

Claude Code doesn't navigate summaries of files. It navigates filenames and raw content sampled via grep. And crucially: it loops. It doesn't get there in one shot. It iterates — searches, reads, reformulates, searches again — until it has the picture.

The "secret" of this approach is in the repetition. Each individual tool call reads very little, but the *process* of repeated calls builds up the understanding. The agent is exploring, not retrieving.

Applied to zettelkasten, the equivalent pattern would be:

1. Search with initial query → get titles
2. Read 2-3 most promising notes
3. Those notes contain concepts and connections that suggest a better query or adjacent notes
4. Search again, or read a specific note by ID
5. Repeat until coverage is sufficient

Each iteration is cheap. The picture assembles over multiple passes, not from a single large retrieval.

**Note titles are the filename equivalent.** The zettelkasten was designed to have expressive, searchable titles — "Procedural Memory as the Mechanism That Closes the Learning Loop" is a meaningful navigational signal on its own. You don't need a pre-generated summary layer to decide whether to read this note.

This also explains why the dropped frontmatter summary was correctly dropped. It was trying to solve the navigation problem at ingestion time, statically, without knowing what the agent's eventual query would be. The actual navigation signal — the title — was already there. What was missing was the iterative retrieval loop.

---

## The cliff notes framing

At this point in the discussion, a cleaner framing emerged for what the zettelkasten is actually providing:

**The zettelkasten is the AI equivalent of cliff notes.**

Cliff notes work because a knowledgeable person did the synthesis work upfront, so the reader gets maximum conceptual coverage per page. The zettelkasten's EDIT/UPDATE/SYNTHESISE operations are doing exactly that at ingestion time — producing cross-paper cliff notes rather than summaries of individual papers. The 31 notes from 20 papers aren't 31 summaries; they're concept-level syntheses that no individual paper stated.

This framing clarifies two things:

**Where the store helps:** discoverability — not in the factual needle-in-a-haystack sense, but as the foundation for context-efficient reading activity. High conceptual value, low context cost.

**Where the store doesn't help:** if the agent needs the exact wording of a specific claim, or a precise technical detail — the cliff notes have discarded that in favour of synthesised structure. Needle-in-a-haystack retrieval is precisely the wrong task. The benchmark's rejection of NIAH tasks is correct, and now has a sharper justification.

The clean efficiency metric this suggests: **conceptual coverage per token consumed**. How many tokens does the agent need to consume to reach equivalent conceptual coverage? If the zettelkasten gets there in 32k tokens where naive RAG needs 120k, that is a concrete and measurable advantage.

---

## The counter-argument: immersion and creative connection

The subagent oracle and efficient navigation approaches both optimise for context efficiency. But the benchmark is designed to test creative innovation — bisociation, tension identification, adjacent possible mapping. This is where a counter-argument emerged.

**The subagent compresses by answering the question asked. But creative connection often comes from what you encounter while looking for something else.**

Koestler's bisociation — the creative act as the collision of two previously unrelated matrices of thought — requires exposure to both matrices. If the subagent pre-synthesises before the parent sees the notes, the parent is reasoning about a *description of the territory* rather than the territory itself. The unexpected collision between two notes the agent didn't know were related never happens.

The human analogy: humans who make creative breakthroughs are often deeply immersed — they've absorbed huge amounts of material to the point where unexpected connections can emerge. The "aha moment" requires having so much material in working memory that two previously separate things suddenly collide. The subagent, optimising for relevance, filters out exactly that serendipity.

The web search subagent analogy breaks down here for exactly this reason. A human doing creative research doesn't send an assistant to get answers — they read widely, follow tangents, notice the unexpected.

**The counter-counter-argument:** the zettelkasten notes are already synthesised. Putting 20 notes in context isn't putting 20 papers in context. The conceptual density is much higher per token — each note is the distilled essence of multiple papers, with redundancy and raw prose stripped. The EDIT operations throughout the ingestion run were specifically producing this density. So accepting the 120k token cost for innovation tasks may be buying something real: concentrated immersion at a fraction of the original paper cost.

**The resolution (tentative):** the right interface may depend on task type.

- Factual synthesis tasks: subagent oracle is fine, possibly better — the parent doesn't need raw notes to answer a synthesis question
- Innovation tasks (bisociation, tension identification, adjacent possible): notes injected directly into the parent's context — accepting the cost because the cost is buying creative exposure

The benchmark should test this split rather than assuming one architecture for all tasks.

---

## The store is just files

A significant oversight in the orientation discussion: it focused on search APIs and title listings as the navigation primitives, but the zettelkasten store is just markdown files on a filesystem. This means the agent has the full range of filesystem tools available — the same tools that make Claude Code's codebase navigation effective — without any purpose-built interface:

- `grep "^title:" notes/*.md` — all note titles across the entire store in a single pass, zero embedding cost
- `grep -l "phase transition" notes/*.md` — which notes mention a concept, without reading any full body
- `head -30 note.md` — just the frontmatter and opening paragraph, not the full 6k chars
- glob patterns — filter notes by date range, ID range, or any filename convention
- `grep "activation:" notes/*.md` — extract hub weights across the store in one operation

The zettelkasten search API is the equivalent of a language server in Claude Code — useful, but not the only way to navigate. The filesystem *is* the interface. Grep against frontmatter fields, glob for temporal clustering, head for opening paragraphs — these are all available and essentially free. No embeddings, no index, no API call.

This refines the Experiment 1 question. It's not just "are titles sufficient for navigation" — it's "what combination of lightweight filesystem operations gives the agent sufficient orientation before committing to full note reads?" The answer may be richer and cheaper than the two-tier search-API approach suggested earlier.

It also reframes what the retrieval subagent actually is. If exploration is built on grep, glob, and read, there is no Python API to build — the memory subagent is an instruction set. A **skill** that tells the agent how to explore the store using tools it already has: "grep titles for orientation, read 2-3 most relevant notes, identify concepts in those notes that suggest further reads, iterate until coverage is sufficient, then synthesise." That is a skill definition, not library code.

The Python library (`ZettelkastenStore`, `store.search()`) remains the right home for the ingestion pipeline — Form, Gather, Integrate are complex enough to warrant proper library code. But the retrieval interface for agents may simply be: here is a directory of markdown files, here is how to navigate it. The development work for the spike experiments looks like prompt design and iteration, not engineering — and the experiments are runnable immediately against the existing 31-note store with no build work required.

This is also a direct application of the bitter lesson to the retrieval side. The 5-signal fusion pipeline — BM25+MuGI, activation weights, tuned k, step-back and HyDE expansion — encodes our current understanding of what good retrieval looks like. It is doing its job, but it is a hand-crafted system, and the bitter lesson predicts it will eventually be outpaced by general-purpose methods as models improve. A skill-based retrieval interface sidesteps this: a better model navigates the filesystem more effectively without any changes to the store or the skill. The improvement is realised automatically.

The split is therefore clean and load-bearing:

- **Ingestion:** Python library, carefully engineered. The bitter lesson applies — expect to revisit as models improve. This is where the synthesis value lives.
- **Retrieval:** Skill, model-native. Improves for free as the model improves. This is where the navigation happens.

The ingestion synthesis remains the core value proposition — the notes are still the cliff notes, the cross-paper synthesis still happened at ingestion time. But *how the agent navigates to those notes* is left to the model rather than encoded in an algorithm. The store gets better as the model gets better, without changes to either.

---

## The note size ceiling as a coupled variable

A related variable was noted but deliberately parked: the note size ceiling (currently 8k) has not been explored. Running the same ingestion with a 4k ceiling might produce more precise, focused notes that retrieval signals can target more accurately — but would require higher k to achieve equivalent conceptual coverage.

The note size and k are coupled parameters that haven't been swept together. A 4k ceiling would also fire SPLIT operations earlier, potentially producing a healthier graph with less hub accumulation. This is worth knowing but is a separate ingestion run that should follow, not precede, the benchmark architecture questions.

*Parked: revisit after benchmark experiments.*

---

## The ingestion synthesis framing

A broader framing emerged near the end of the discussion. AI capability has been accelerated by:

- Scaling training synthesis (pretraining on larger corpora)
- Scaling RL synthesis (RLHF, constitutional AI)
- Scaling inference synthesis (chain-of-thought, extended thinking)

The zettelkasten proposes a fourth: **ingestion synthesis** — compressing incoming documents into a structured, cross-referenced knowledge graph at the time of ingestion, rather than storing raw content and synthesising at query time.

The hypothesis is that synthesis at ingestion time pays off at query time, in a way that compounds as the corpus grows and that is qualitatively different from what a larger context window alone can substitute for. The benchmark is designed to test this hypothesis directly.

---

## Skill iteration as the development method

A precedent for how to run these experiments comes from Karpathy's autoresearch project — a system for autonomous ML research built on a tight iteration loop: single artifact being modified (`train.py`), clear measurable signal (`val_bpb`), fixed evaluation budget, agent iterates until interrupted.

The parallel to skill design here is direct:

- **Single artifact:** the skill file (a markdown instruction document, analogous to autoresearch's `program.md`)
- **Clear measurable signal:** navigation quality — did the exploration reach the relevant notes, and at what token cost?
- **Fixed evaluation corpus:** the existing 31-note store + a set of test questions authored once
- **Tight loop:** run agent with skill → measure navigation → update skill → repeat

The `program.md as specification` pattern — human intent in Markdown, agent executes using tools it already has — is exactly what a skill is. No code involved on either side of the loop. The skill file describes *how to explore the store*; the agent uses grep, glob, and read to do it.

For the iteration to be fast, the inner-loop metric needs to be deterministic: did the exploration reach the notes that are actually relevant to the question, and how many tokens did it consume? This can be measured without an LLM judge. Pairwise quality comparison is the slower validation gate — run it periodically to confirm that faster navigation is also better navigation, not just cheaper.

This also compresses the experiment plan. Experiments 1-3 are not three separate controlled experiments — they are questions the skill iteration loop answers organically as the skill evolves. The loop produces a logged history of what worked and what didn't, which is itself the design rationale documentation. The spike produces both a working skill and an evidence trail for why it is designed the way it is.

### Skill construction guidance

The official Claude skill best practices (https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices.md) should guide the construction of the memory skill. Key constraints relevant to this spike:

**Conciseness is critical.** The context window is shared. Challenge every piece of instruction — does Claude already know this? The skill should add only what the model doesn't have, not re-explain filesystem navigation to a model that already knows how to use grep and glob.

**Match degrees of freedom to fragility.** Iterative exploration has multiple valid paths (high freedom — text instructions). Specific operations like frontmatter parsing or activation weight extraction may need more precise guidance (medium freedom — pseudocode). Don't over-constrain the exploration strategy; that is the bitter lesson applied to skill design.

**Build evaluations first.** Before writing the skill, run the agent on representative navigation tasks without any skill to establish a baseline and identify the actual gaps. Write minimal instructions that address only those gaps. This is the autoresearch loop: measure first, then modify.

**Progressive disclosure.** Keep the main skill file under 500 lines. If the skill needs to cover both orientation (cheap filesystem ops) and deep reading (full note bodies), consider separating these into referenced files loaded only when needed.

**Iterate with a fresh instance.** After each skill revision, test with a fresh Claude instance (no conversation history) to verify the skill is self-contained and the instructions are not leaning on context that won't exist at runtime.

---

## Experiment plan

Four experiments sequenced to answer one question at a time. Experiments 1-3 run on the existing 31-note store — no new ingestion required.

### Experiment 1: Navigation signal quality
*(Days, near-zero cost)*

**Question:** Are note titles sufficient for an agent to identify relevant notes, or is a summary layer needed?

**Method:** Present the 31-note title listing to an agent with 10-15 test questions. Ask it to predict which notes are relevant before any retrieval. Compare against actual search results.

**Binary output:** Titles are navigable (no summary layer needed) or they aren't (design must include summaries).

**Why this first:** If titles aren't sufficient, the two-tier exploration pattern requires a summary layer built at ingestion time. That changes the store design. Know this before building the agent loop.

---

### Experiment 2: Iterative vs. single-shot retrieval
*(Days, cheap)*

**Question:** Does iterative exploration improve coverage while reducing context waste compared to single-shot top-k injection?

**Method:** Same store, same test questions. Compare:
- (a) Single search → inject all top-k results
- (b) Iterative loop — search, read 2-3 notes, reformulate query, repeat until done

**Metrics:** Context tokens consumed per question, and which notes were actually cited in the final response.

**Why this matters:** If iteration doesn't improve over single-shot, the simpler interface is correct and the agent loop doesn't need to be built. If it does improve, the benchmark must use the iterative interface or it's testing the wrong thing.

---

### Experiment 3: Direct injection vs. subagent oracle for innovation tasks
*(Weeks, moderate)*

**Question:** Does compressing retrieval output to a subagent synthesis stifle creative connection on innovation-type tasks?

**Method:** 6-8 innovation-type questions (synthesis, tension identification, adjacent possible). Three variants:
- (a) Notes injected directly into the parent's context
- (b) Subagent returns a synthesis answer only
- (c) Subagent returns the notes it found, not a synthesis

**Metric:** Pairwise quality comparison on innovation dimensions (novelty of connections, identification of tensions, non-obvious directions).

**The debate this resolves:** Whether the creative immersion argument holds empirically or whether the efficiency gain of the subagent pattern is achievable without sacrificing creative output quality. The result fixes the benchmark architecture.

---

### Experiment 4: Note size ceiling
*(Weeks, ~$20)*

**Question:** Does a 4k note size ceiling produce better retrieval precision at equivalent conceptual coverage compared to the current 8k ceiling?

**Method:** Re-ingest the same 20 papers with a 4k ceiling. Compare store structure (note count, hub concentration, SPLIT frequency) and retrieval quality on the same test questions.

**Why this fourth:** Requires a new ingestion run. Should only run after the interface questions (Experiments 1-3) are answered, so the ceiling experiment uses the correct agent interface for evaluation.

---

### Experiment 5: Full benchmark
*(Months, ~$95)*

Run once. With Experiments 1-4 completed:
- The retrieval interface is settled (two-tier or single-shot, iterative or not)
- The subagent architecture question is resolved for each task type
- The note size ceiling is fixed
- The full corpus can be ingested once, in the right configuration

The benchmark then compares genetic / naive RAG / zettelkasten conditions under the winning design — not under an assumption that may turn out to be wrong.

---

## Dependency structure

```
Exp 1 (titles navigable?)
    → informs whether summary layer needed in Exp 2

Exp 2 (iterate vs. single-shot?)
    → informs agent loop design for Exp 3

Exp 3 (direct vs. subagent for innovation tasks?)
    → fixes benchmark architecture

Exp 4 (4k vs. 8k note ceiling?)
    → fixes store configuration before full corpus ingest

Exp 5 (full benchmark)
    → runs once, with all design questions answered
```

The expensive experiment runs last. Each prior experiment is cheap precisely because it isolates one variable against the existing 31-note store, with no new ingestion required until Experiment 4.

---

## Spike outcomes (2026-03-24)

The spike ran against the existing 31-note store. Results are logged in `eval/LOG.md`. Key findings below.

### Experiments 1 & 2 answered: titles are navigable, iteration beats single-shot

Titles alone are sufficient for orientation — agents correctly identified relevant notes from title scans without reading bodies. The iterative exploration pattern (grep → read → follow See Also → stop when covered) outperformed single-shot injection on every dimension: fewer reads, higher synthesis completion rate, same or better GT hit rate.

Baseline (no skill): 16.1 avg reads, 94% GT hit rate, 42% synthesis completion (rest hit rate limit before synthesising).

Iter 4 skill (stable config): 7.7 avg reads, 82–100% GT hit rate by question type, 100% synthesis completion.

### The stable skill (Iter 4)

Five iterations of the skill, each changing one thing:

| Iter | Change | Key effect |
|------|--------|------------|
| 1 | Stopping criterion | Read count collapsed 16→5. Biggest single win. |
| 2 | See Also guidance | Path-following switched on. Island recovery via link traversal. |
| 3 | Unconditional "radiate outward" | Over-radiated on wide questions (13→18 reads). |
| 4 | Conditional radiation ("if not fully covered") | Fixed over-radiation. Retained island recovery. |
| 5 | Hub note hint | Net negative — inflated reads, no GT improvement. Reverted. |

Iter 4 is the keeper. The See Also graph is the primary navigation structure; stopping criterion is the primary efficiency mechanism. Each is independently valuable and they don't conflict.

### Structural misses are corpus-level, not skill-level

Two notes missed across all runs: z001 (Q8 — vocabulary gap between "phase transition" cluster and "Multi-Agent Architectures") and z004 (Q5 — "routing" not reachable from "communication overhead" framing). These require better See Also links at ingestion time, not skill hints. The skill iteration loop has reached its ceiling on the current corpus.

### Islands are acceptable misses by design

Low-activation notes have low activation because the ingested literature didn't reinforce them. The ingestion synthesis concentrates structure where papers converged. An agent reaching the hub notes efficiently is reaching the high-signal region of the knowledge graph. Missing an island note that only one paper contributed to is the system's prior working correctly, not a retrieval failure. GT hit rate is therefore a slightly wrong metric — hub-accessible question coverage matters more.

### Three-condition comparison: genetic / zettelkasten / oracle RAG

Ran Q7 (unexplored coordination mechanisms) and Q8 (phase transition breakdown) across three conditions:

**Q8 (narrow technical question):**
- *Genetic*: general random-graph theory, semantic drift, Dunbar's number. Wrong specific formula. Directionally correct but not grounded in the actual papers.
- *Oracle RAG* (157k chars of raw papers): recovered the specific formal framework, breakdown modes, synergy condition. Competitive on technical accuracy. Cross-referenced across three papers.
- *Zettelkasten* (4 reads, ~24k chars): most precise on formal detail (chain-relay decay η^L·b₀, linear-time optimal m algorithm). 3–5× more context-efficient than RAG for equivalent accuracy.

**Q7 (synthesis / unexplored mechanisms):**
- *Genetic*: got the trilemma definition wrong (Autonomy/Coordination/Coherence vs Performance/Cost/Efficiency). Proposed classical MAS mechanisms (stigmergy, FIPA commitment) — interesting but different territory.
- *Oracle RAG* (109k chars): got the trilemma right. Found *integration-level* gaps — combining EvoRoute + ACP, combining LEGOMem + ACP. Grounded in seeing the raw seams between papers simultaneously.
- *Zettelkasten* (11 reads, ~66k chars): found *theory-grounded* gaps — runtime ρ management, learned aggregation, message-length as runtime variable. Each derived from a specific formal result in the synthesised notes.

### Experiment 3 resolved: subagent is optional, not necessary

The design discussion framed the subagent oracle as a potential necessity if context cost was prohibitive. The spike answers this: at Iter 4 efficiency (7–11 reads × ~6k chars = ~42–66k chars navigation cost), the zettelkasten fits comfortably within a working parent-agent context. The subagent architecture is not forced by context pressure.

The subagent remains a valid *architectural choice* — reusable across conversations, parallelisable, cleaner separation of concerns — but it is not an architectural *requirement*. A parent agent using the skill directly pays an acceptable context cost and retains full exposure to the notes, preserving the creative immersion argument for innovation tasks.

The counter-argument from the design discussion (subagent compresses by answering the question asked, suppressing serendipitous connection) therefore stands as the reason *not* to use a subagent for innovation tasks specifically. The right default is skill-in-parent; subagent is an optimisation for production contexts where context cost matters more than creative exposure.

For evaluation, subagents remain the right call regardless — clean isolation makes navigation traces attributable and answers comparable across conditions.

### The jagged frontier

The zettelkasten and oracle RAG don't produce the same answers — they produce *different kinds* of synthesis:

- **Zettelkasten**: theory-grounded synthesis. The pre-ingestion integration compresses the design space and surfaces gaps derivable from formal results. Efficient. Frames the problem through the synthesised conceptual structure.
- **Oracle RAG**: integration-level synthesis. Seeing raw papers simultaneously lets the agent notice how systems from different papers could combine. Expensive. Frames the problem through the seams between source documents.

Neither is uniformly better. The benchmark should test both question types to map where the zettelkasten leads and where it doesn't. The "jagged frontier" of relative strength is itself the useful finding — it characterises what the ingestion synthesis buys and what it costs.

---

## Addendum: full 12-question oracle RAG results (2026-03-25)

The Q7/Q8 finding above was confirmed and refined by running oracle RAG across all 12 evaluation questions. Full data in LOG.md Run 7. Key refinements:

### Three distinct zones, not two

The frontier is more nuanced than the Q7/Q8 binary suggested:

1. **Zettelkasten dominates** (Q7, Q8, Q11, Q12) — questions where the answer requires synthesising formal results *across* papers into a structure no individual paper states. The cross-paper chain (UHAT expressivity → DAG formalism → phase transitions → context engineering in Q11; AISAC + security + ACP linked in Q12) emerges from the synthesised notes and is never stated in the raw papers. Synthesis is the answer.

2. **Oracle RAG competitive or stronger** (Q5, Q6, Q10) — questions where the answer lives in each paper's own limitation and related-work sections: explicit disagreements between papers, tensions each paper acknowledges, untried analogies listed in "future work." Coverage beats synthesis; reading raw seams is what matters.

3. **Genetic competitive** (Q6, Q10, Q12 in part) — questions where the topic is dense in LLM training data independently of the corpus. Benchmark design critique, formal database provenance theory, and game theory are all areas where parametric knowledge is deep enough to compete without the corpus.

### Oracle RAG is a ceiling, not a representative implementation

A critical caveat for interpreting zones 2 and 3: the oracle RAG condition used whole-paper injection (65k–195k chars), not chunk-based retrieval. Real-world RAG retrieves top-K chunks on query similarity and almost never sees limitation sections, related-work comparisons, or "what we didn't explore" paragraphs unless the query specifically targets them.

The oracle RAG advantage on Q5, Q6, and Q10 came from reading those sections. A chunk-retrieval query on "when communication adds value" would return results sections, not the sections where papers implicitly contradict each other. Real-world RAG would likely perform worse than oracle RAG on exactly those questions — potentially falling below zettelkasten. The comparison is therefore conservative for zettelkasten: oracle RAG is the best-case ceiling for the RAG condition, and zettelkasten still wins on synthesis-heavy questions against that ceiling.

### Efficiency confirmed at scale

Across all 12 questions, zettelkasten used ~40–70k chars per question (7–12 notes × ~6k avg). Oracle RAG used 65–195k chars. For the ~8 questions where the two conditions are near-equivalent in answer quality, zettelkasten is 2–5× more token-efficient. The context efficiency finding from Q7/Q8 holds across the full question set.
