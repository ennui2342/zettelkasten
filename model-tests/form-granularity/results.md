# Spike 2 Results — Fuzzy Document Form Phase

*Run: 2026-03-14 20:07*
*Model: claude-opus-4-6*

---

## Approach A — Stepped (CARPAS-inspired)

**Topics identified:** 2 (model count) → 2 named

**Topic names:**
- Memory and Learning
- Knowledge Management Tools

---

### A: Memory and Learning

# Memory and Learning: Extracted Content

## Foundational Research and the Forgetting Curve

Hermann Ebbinghaus first plotted forgetting curves in the 1880s, establishing that memory decays over time in a predictable pattern. His work showed that each successful retrieval of a memory flattens the forgetting curve, meaning the next episode of forgetting takes progressively longer to occur.

## The Testing Effect

Allowing memory to partially decay and then retrieving it before it vanishes entirely produces far more durable retention than passive review such as rereading. Studies comparing students who reread material with those who took practice tests on the same content found recall differences of 40–50% after a week or more. The effortful act of pulling information back from memory does something to the underlying memory trace that simple re-exposure cannot replicate.

## Memory as Reconstruction

Retrieval is not a passive readout from a stable substrate. When a memory is retrieved, it is rebuilt from fragments, influenced by whatever else is active in the mind at that moment, and then re-encoded in its reconstructed form. This means successful retrieval does not merely demonstrate that learning happened — it *is* learning. Each retrieval attempt creates additional neural pathways, making subsequent retrieval faster and more reliable. A fact retrieved ten times is stored differently in memory than one merely read ten times, even if both feel equally familiar at the moment.

## Spaced Repetition and the Spacing Effect

Spaced repetition systems apply the spacing insight by timing reviews to arrive just as forgetting is about to overtake retention, thereby forcing the retrieval that consolidation demands. A fact reviewed at optimally timed intervals requires fewer total reviews to reach a given retention target than the same fact reviewed at shorter, more comfortable intervals. Massed practice (cramming) feels more productive because the material remains accessible in short-term memory, but spaced practice feels harder precisely because it demands genuine retrieval — and that difficulty is what makes it effective.

## The Role of Retrieval Difficulty

The spacing interval also changes the qualitative character of recall. Information retrieved after a short delay (e.g., ten minutes) is nearly recognition — the answer surfaces with little effort along a still-warm trace. The same information retrieved after a longer delay (e.g., three days) requires genuine reconstruction: searching for context, associations, and the original circumstances of encoding. This harder reconstruction activates more pathways and reinforces more retrieval routes for future access. The harder the successful retrieval, the more durable the resulting memory.

## Recognition versus Recall

There is an important distinction between recognition (identifying the correct answer when prompted) and recall (generating the correct answer without cues). These are different cognitive operations with different consequences for consolidation. A flashcard system that waits for a button press runs a recognition test; one that forces the user to produce the full answer before revealing it runs a recall test. The difference in long-term retention is substantial. Most users skip the generation step because the friction seems unnecessary, but it is not.

## The Generation Effect

Producing information oneself leads to stronger encoding than passively receiving it. Research on note-taking shows that writing things down in one's own words produces stronger encoding than verbatim transcription. Paraphrasing forces the learner to process what the material means, not just what it says. The act of compression and reformulation is itself a form of retrieval — constructing an account of the material from one's current understanding rather than copying an external source. Closing the book and writing from memory produces better retention than annotating while reading, even when the annotations are detailed.

## Handwriting versus Typing

Research comparing handwritten and typed notes found that typists transcribed more material, often near-verbatim, while handwriters recorded fewer words but processed them more deeply, deciding sentence by sentence what was worth keeping. However, the handwriting advantage largely disappears when typists are instructed to paraphrase rather than transcribe. What the research isolates is not an effect of the physical act of writing but a generation effect: the more the learner must produce and decide, the more robust the encoding. The physical friction of handwriting simply makes generation the default behavior.

## Elaborative Interrogation

Asking oneself questions like "why does this make sense?" or "how does this connect to what I already know?" while encoding new material substantially improves later recall compared to simply reading the same content. Generating explanatory connections triggers the same consolidation pathways as retrieval practice: the existing cognitive structure must reach out and incorporate the new material, and that act of reaching is what creates durable knowledge.

## A Unified Mechanism

The testing effect, spaced retrieval, the generation effect, and elaborative interrogation are often treated as separate findings but converge on a single underlying mechanism. Passive exposure produces weak encoding because nothing is demanded of the learner's existing cognitive structure — the material arrives already decoded, no reconstruction is required, no pathways are strengthened. Active engagement in any form — retrieving, producing, explaining, connecting — requires the cognitive structure to work, and it is that work which leaves a durable trace.

## Fragility of Purely Accumulative Knowledge Systems

A note that is never retrieved does not consolidate. A knowledge base that grows only through capture — adding new material without any mechanism for reconstruction and retrieval — becomes an increasingly comprehensive archive of things once read but not genuinely known. The notes exist but the encoding does not. Reading something into a system is not the same as learning it, regardless of how well the system organizes the result.

## Implications for Tool Design and External Memory

Software optimized for frictionless capture and perfect retrieval is, in a precise sense, optimized against consolidation. Off-loading memory to an external system can free cognitive resources for higher-order work, but only when the off-loading is strategic and the material is later retrieved and reconstructed, not merely stored. A tool that makes everything accessible all the time without ever requiring the user to produce anything from memory substitutes for cognition rather than extending it. The value of an external knowledge system lies not in storing what one knows but in creating conditions under which knowing can deepen — which means the system must sometimes make remembering harder, not easier.

---

### A: Knowledge Management Tools

# Knowledge Management Tools

## The Core Problem with Accumulative Systems

The essay delivers a pointed critique of knowledge management tools that prioritize frictionless capture and perfect retrieval. A note that is never retrieved from memory does not consolidate in the mind. A knowledge base that grows purely through capture — continually adding new material without any mechanism for reconstruction and retrieval — becomes a comprehensive archive of things the user once encountered but does not genuinely know. The notes exist within the system, but the encoding in the user's memory does not. Reading something into a system is fundamentally not the same as learning it, regardless of how well the system organizes the result.

## Software Design and Its Tension with Learning

The essay argues that software optimized for frictionless capture and perfect retrieval is, in a precise sense, optimized *against* the cognitive process of consolidation. Making everything accessible at all times, without ever requiring the user to produce anything from memory, causes the tool to substitute for cognition rather than extend it. Off-loading memory to an external system can free cognitive resources for higher-order thinking, but only when the off-loading is strategic and the stored material is later retrieved and reconstructed rather than merely stored.

## What Effective Knowledge Tools Should Do

The essay contends that the value of an external knowledge system lies not in storing what a person knows, but in creating conditions under which knowing can deepen. This means, counterintuitively, that such a system must sometimes make remembering *harder*, not easier. It should incorporate mechanisms that demand active engagement — retrieval, production, explanation, and connection — rather than offering passive re-exposure to stored content.

## Specific Techniques and Mechanisms Relevant to Tool Design

Several named techniques and phenomena from the essay bear directly on how knowledge tools should function:

- **Spaced repetition systems** are the most direct application of spacing research. They time reviews to arrive just as forgetting is about to occur, forcing the retrieval that consolidation requires. Each successful retrieval flattens the forgetting curve, meaning the next forgetting event takes longer. However, these systems hit a ceiling: a well-tuned flashcard system can maintain a fact in testable form indefinitely while the user has no real understanding of it. This happens because many implementations collapse the distinction between **recognition** (identifying the correct answer when prompted) and **recall** (generating the answer without cues). A system that presents a cue and waits for a button press runs a recognition test; one that forces the user to produce the full answer before revealing it runs a recall test. The difference in long-term retention is substantial, yet most users skip the generation step because the friction seems unnecessary.

- **The generation effect** is relevant to note-taking tools. Writing things down in one's own words produces stronger encoding than verbatim transcription. Paraphrasing forces the user to process material — to decide what it means, not just what it says. Closing a book and writing from memory produces better retention than annotating while reading, even when the annotations are detailed. Research comparing handwritten to typed notes initially seemed to show handwriting was superior, but the real finding is about generation: the handwriting advantage disappears when typists are instructed to paraphrase. What matters is how much the learner must produce and decide, not the physical medium. Handwriting merely makes generation the path of least resistance by introducing physical friction.

- **Elaborative interrogation** — asking "why does this make sense?" or "how does this connect to what I already know?" during encoding — substantially improves later recall. Generating explanatory connections triggers the same consolidation pathways as retrieval practice because the existing cognitive structure must reach out and incorporate new material.

- **The testing effect** demonstrates that practice tests vastly outperform rereading, with recall differences of 40–50% at delays of a week or more. The act of retrieval reconstructs the memory from fragments and re-encodes it, which is itself learning.

## The Underlying Principle for Tool Design

The essay unifies these four phenomena — the testing effect, spaced retrieval, the generation effect, and elaborative interrogation — under a single mechanism. Passive exposure produces weak encoding because nothing is demanded of the user's existing cognitive structure. Active engagement in any form requires the structure to work — to retrieve, produce, explain, and connect — and it is that work which leaves a durable trace. Knowledge management tools, therefore, should be designed to demand this kind of work rather than eliminate it.

---

## Approach B — Single-shot

## Memory, Forgetting, and Retrieval

Since Ebbinghaus first mapped forgetting curves in the 1880s, research has consistently shown that allowing memories to partially decay and then actively retrieving them produces far more durable retention than passive review such as rereading or highlighting. Studies show recall differences of 40–50% favouring practice testing over rereading at delays of a week or more. This is known as the testing effect. Retrieval is not a simple readout from a stable store; it is a reconstructive process in which a memory is rebuilt from fragments, shaped by current context, and then re-encoded in its new form. Each successful retrieval lays down additional pathways, making future access faster and more reliable. A fact retrieved ten times is held differently in memory than one merely read ten times, even if both feel equally familiar. Crucially, retrieval difficulty matters: a word recalled after three days requires deeper reconstruction — searching for context and associations — than one recalled after ten minutes, and that harder reconstruction activates more pathways and reinforces more retrieval routes. The struggle is not incidental friction; it is the mechanism of learning. There is also an important distinction between recognition (identifying a correct answer when prompted) and recall (generating the answer without cues). These are different cognitive operations with different consolidation consequences, and conflating them — as many learning tools do — can produce the illusion of knowledge without genuine retention.

## Spaced Repetition

Spaced repetition systems are the most direct practical application of research on spacing and retrieval. They schedule reviews to arrive just as forgetting is about to succeed, forcing the effortful retrieval that consolidation requires. Ebbinghaus demonstrated that each successful retrieval flattens the forgetting curve, meaning the next bout of forgetting takes longer to arrive. Consequently, a fact reviewed at optimally spaced intervals requires fewer total reviews to reach a given retention target than one reviewed at shorter, massed intervals. Massed practice feels more productive because material remains accessible in short-term memory, but spaced practice feels harder precisely because genuine retrieval — not mere recognition — is demanded. However, these systems hit a ceiling their designers did not always anticipate. A well-tuned flashcard system can maintain a fact in testable form indefinitely while the user has no real understanding of it, particularly when cards function as recognition tests (prompting a button press) rather than recall tests (requiring the user to generate the full answer). Most users skip the generation step because the friction seems unnecessary, but the long-term retention difference between recognition-based and generation-based review is substantial. The broader lesson is that timing alone does not explain the full benefit of spacing; the qualitative character of the retrieval — how much reconstruction is required — matters just as much.

## The Generation Effect and Active Encoding Strategies

A cluster of related findings — the generation effect, elaborative interrogation, and research on note-taking — converge on a single principle: the more a learner must produce, decide, or explain, the more robust the encoding. The generation effect refers to the well-documented advantage of producing material oneself rather than passively receiving it. In note-taking, writing things in one's own words yields stronger encoding than verbatim transcription, because paraphrasing forces the learner to process meaning — to decide what material means, not just what it says. Closing the book and writing from memory outperforms even detailed annotation done while reading. Research comparing handwritten and typed notes initially seemed to show handwriting was inherently superior, since handwriters recorded fewer but more deeply processed words. A more careful reading reveals that the medium shapes default behaviour rather than setting a ceiling: the handwriting advantage largely disappears when typists are instructed to paraphrase. What matters is not the physical act but the degree of generation required. Elaborative interrogation — asking "why does this make sense?" or "how does this connect to what I already know?" — triggers the same consolidation pathways as retrieval practice by forcing existing knowledge structures to reach out and incorporate new material. Together with the testing effect and spaced retrieval, these phenomena are best understood not as separate findings but as expressions of a single mechanism: passive exposure demands nothing of existing cognitive structure, while active engagement — retrieving, producing, explaining, connecting — requires the structure to work, and it is that work which leaves a durable trace.

## Design of Tools for Thinking and External Knowledge Systems

The science of memory consolidation has uncomfortable implications for how knowledge tools are designed. A note that is never retrieved does not consolidate. A knowledge base that grows by capture alone — adding material without any mechanism for reconstruction and retrieval — becomes an archive of things once read but not genuinely known. The notes exist; the encoding does not. Software optimised for frictionless capture and perfect retrieval is, in a precise sense, optimised against consolidation. Off-loading memory to an external system can free cognitive resources for higher-order work, but only when the off-loading is strategic and the material is later retrieved and reconstructed, not merely stored. A tool that makes everything accessible at all times without ever requiring the user to produce anything from memory substitutes for cognition rather than extending it. The real value of an external knowledge system lies not in storing what you know but in creating conditions under which knowing can deepen — which means such a system must sometimes make remembering harder, not easier, deliberately introducing the productive friction that drives retrieval, generation, and genuine learning.

---

## Evaluation notes (run 2)

### Topic identification

Expected 4 topics: (A) testing effect, (B) spaced repetition, (C) generation effect, (D) external tools

**Approach A (stepped):** 2 topics — "Memory and Learning", "Knowledge Management Tools"

Over-corrected. The "broad topic area" wording pushed the model to merge A+B+C into one note and produce a second note that largely duplicates the same content through a tool-design lens. All four topic areas are present as sections within the notes, but the granularity is too coarse — one mega-note covering three distinct subjects is not useful for a topic-scoped knowledge base.

The count step is now confirmed as **unstable**: run 1 returned 8, run 2 returned 2, for the same article with modestly different prompt wording. The count-first approach amplifies sensitivity — whatever number comes out of step 1, steps 2 and 3 faithfully follow it off a cliff in either direction.

**Approach B (single-shot):** 4 topics — Memory, Forgetting, and Retrieval ✓ (A), Spaced Repetition ✓ (B), The Generation Effect and Active Encoding Strategies ✓ (C), Design of Tools for Thinking and External Knowledge Systems ✓ (D)

Hit the expected 4 without being told the count or given examples. Correctly absorbed Elaborative Interrogation as a sub-section within C rather than creating a separate note for it — the exact failure mode that over-split run 1. No scaffolding needed.

---

### Content coverage per topic (Approach B)

**A — Memory, Forgetting, and Retrieval** (expected paras 2, 3, 5 partial, 9 bridge):
✓ Covers the 40–50% statistic, reconstruction mechanism, retrieval difficulty gradient, recognition vs recall distinction. Para 9 bridge ("elaborative interrogation... triggers the same consolidation pathways as retrieval practice") included in the convergence paragraph. Comprehensive.

**B — Spaced Repetition** (expected paras 4, 5, 6 partial):
✓ Covers Ebbinghaus, forgetting curve, massed vs spaced, qualitative difficulty of retrieval after longer gap, flashcard ceiling, recognition vs recall in SR systems. Well-scoped to B territory.

**C — Generation Effect and Active Encoding Strategies** (expected paras 6 partial, 7, 8, 9 bridge):
✓ Covers note-taking research, handwriting vs typing (correctly identifies it as a generation effect, not a medium effect), elaborative interrogation as a sub-case of the same mechanism, convergence paragraph. Para 9 bridge included. Excellent — this is exactly the right handling of the "sub-topic" problem.

**D — Design of Tools for Thinking** (expected paras 8 partial, 11, 12):
✓ Covers accumulation trap, frictionless capture optimised against consolidation, off-loading vs extending cognition, strategic friction. Clean and focused. Para 8 handwriting/typing content correctly landed in C (also has a small presence here, which is correct — it's a D-relevant example).

---

### Ambiguous sentences (Approach B)

**"That reconstruction is itself encoding."** → expected in A and B
- A note: ✓ "Each successful retrieval lays down additional pathways" + reconstruction described throughout
- B note: ✓ "the qualitative character of the retrieval — how much reconstruction is required — matters just as much"

**"This is where spaced repetition systems hit a ceiling..."** → expected in B and C
- B note: ✓ Full ceiling section with recognition vs recall distinction
- C note: ✓ "Most users skip the generation step... the long-term retention difference between recognition-based and generation-based review is substantial" — present within the generation effect framing

**"The explanatory effort triggers the same consolidation pathways as retrieval practice."** → expected in C and A
- C note: ✓ Elaborative interrogation section explicitly bridges to retrieval practice
- A note: ✓ Convergence paragraph: "Together with the testing effect and spaced retrieval, these phenomena are best understood... as expressions of a single mechanism"

All three ambiguous sentences present in both expected topic extractions. ✓

---

### Padding handling

- Para 1 (intro): not present as primary content in any note. ✓
- Para 10 (synthesis/convergence): correctly distributed as a concluding paragraph in multiple notes — A, C, and D all end with the convergence point. This is right behaviour: the synthesis paragraph is relevant to all topics. ✓

---

### Approach comparison (run 1 + run 2 combined)

| | A stepped (run 1) | A stepped (run 2) | B single-shot (run 1) | B single-shot (run 2) |
|--|--|--|--|--|
| Topics found | 8 | 2 | 5 | 4 |
| Expected 4 topics present | ✓ (diluted) | ✓ (merged) | ✓ (Elab. split) | ✓ |
| Right granularity | ✗ too fine | ✗ too coarse | ✗ slight over-split | ✓ |
| Count stability | — | — | N/A | N/A |
| Ambiguous sentences handled | ✓ | N/A (one big note) | ✓ | ✓ |
| Truncation | — | — | ✗ (2048 limit) | ✓ (4096) |

**The verdict is clear.** Approach A (stepped) is **too sensitive to prompt wording** at the count step — swinging from 8 to 2 with modest changes. The count-first architecture amplifies instability rather than constraining it. The CARPAS insight (predict count to prevent over-generation) doesn't hold here because the count prediction itself is the instability. Approach B (single-shot) **converged on the right answer (4 topics) without scaffolding** and handled the hardest case (Elaborative Interrogation absorption) correctly.

The Bitter Lesson applies: the stepped algorithm was solving a problem (count constraint) that the model doesn't actually have when given the right framing.

---

## Go / No-go

[x] **Go — proceed to Spike 3**

Approach B (single-shot) validated. The Form phase for fuzzy documents works: correct topic count, right granularity, scattered content collected from across the article, ambiguous sentences present in both relevant extractions, padding suppressed, no hallucination.

**Decision: use single-shot as the Form phase mechanism. Drop the stepped CARPAS approach for fuzzy documents.**

The count-first constraint adds instability, not quality. A capable model identifies the right number of broad topics naturally when the prompt specifies "broad subject areas" with a "named techniques belong inside a topic, not as separate topics" instruction.

Spike 3 will use the Approach B draft notes as input to test the Integrate phase: given a draft note and an existing cluster, does the integration LLM make consistent, correct editorial decisions?