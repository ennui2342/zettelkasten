# Ground Truth Annotation

## Topic definitions

| ID | Topic | Core claim |
|----|-------|------------|
| A | Testing effect | Retrieving from memory strengthens the memory trace; active recall outperforms re-reading |
| B | Spaced repetition | Timing practice to coincide with forgetting produces more durable retention than massed practice |
| C | Generation effect | Producing information (paraphrasing, explaining, writing from memory) deepens encoding more than passive capture |
| D | External tools and off-loading | How knowledge systems and recording media shape cognition; when off-loading helps vs substitutes |

Padding = introductory framing, transitions, or conclusions with no strong single-topic content.

---

## Paragraph-level annotation

| Para | First words | Primary | Secondary | Notes |
|------|-------------|---------|-----------|-------|
| 1 | "There is a persistent intuition..." | Padding | A, B (implicit) | Sets up the argument; no topic-specific claims yet |
| 2 | "The evidence accumulated since..." | A | — | Core testing-effect paragraph: retrieval > re-reading, 40–50% difference |
| 3 | "What it does, specifically, is reconstruction..." | A | — | Mechanism of retrieval: reconstruction = re-encoding, pathway reinforcement |
| 4 | "Spaced repetition systems are..." | B | — | Core spaced repetition paragraph: Ebbinghaus, forgetting curve, massed vs spaced |
| 5 | "But timing alone does not explain..." | A+B | — | **Boundary paragraph**: spacing changes *quality* of retrieval, not just timing; reconstruction-as-encoding belongs to A, but the context is entirely B |
| 6 | "This is where spaced repetition systems..." | B+C | — | **Boundary paragraph**: flashcard ceiling is a B context but the insight (recognition vs recall, generation step) is C |
| 7 | "The generation effect is broader..." | C | — | Core generation-effect paragraph: note-taking, paraphrasing, writing from memory |
| 8 | "The question of medium became..." | C | D | Handwriting research: medium shapes default behaviour; isolates generation from physical act |
| 9 | "The same consolidation mechanism surfaces..." | C | A | **Boundary sentence**: "triggers the same consolidation pathways as retrieval practice" — explicit bridge between C and A |
| 10 | "These four phenomena..." | Padding/synthesis | A, B, C | Synthesis paragraph: named convergence on single mechanism; passive exposure is weak encoding |
| 11 | "Understanding this, the fragility..." | D | B | Off-loading without retrieval = storage not memory; B context (spaced retrieval) gives the contrast |
| 12 | "The implication for how we design..." | D | A, B, C | Conclusion: design implications; system must demand reconstruction, not just store |

---

## Deliberately ambiguous sentences

These sentences were written to legitimately belong to two topics. The spike should surface them in both extractions or in neither — but not confidently in only one.

1. **Para 5, sentence 3**: *"That reconstruction is itself encoding."*
   - Belongs to A (retrieval = reconstruction = encoding mechanism)
   - Belongs to B (this is why the spacing interval matters — longer gap → harder reconstruction → more encoding)
   - **Expected**: appears in both A and B extractions

2. **Para 6, sentence 1**: *"This is where spaced repetition systems hit a ceiling their designers did not always anticipate."*
   - Belongs to B (subject is spaced repetition systems)
   - Belongs to C (the ceiling is the missing generation step)
   - **Expected**: extracted into B or C; acceptable in both

3. **Para 9, sentence 3**: *"The explanatory effort triggers the same consolidation pathways as retrieval practice."*
   - Belongs to C (elaborative interrogation is the subject)
   - Belongs to A (explicitly bridges to the testing effect)
   - **Expected**: appears in both A and C extractions

4. **Para 8, sentences 4–5**: *"The handwriting advantage largely disappears when typists are instructed to paraphrase... What the research isolates is not an effect of the physical act of writing but a generation effect."*
   - Belongs to C (generation effect is the finding)
   - Belongs to D (medium is the context; handwriting vs typing is a D topic)
   - **Expected**: appears in both C and D extractions

---

## Padding content

These sentences carry no topic-specific claims and should not dominate any topic extraction:

- Para 1: entirely padding (sets up the argument)
- Para 10 first sentence: "These four phenomena — the testing effect, spaced retrieval, the generation effect, elaborative interrogation — are often treated as separate findings with separate practical implications."
- Para 10 last sentence: "Active engagement, in any of its forms, requires the cognitive structure to work..."

---

## Expected topic extractions (bootstrapping case — no prior notes)

If the LLM correctly identifies the four topics and extracts per topic, each extraction should contain roughly:

**Topic A (testing effect):**
Paras 2, 3 (full); para 5 sentences 2–3; para 9 sentence 3; para 10 (partial)

**Topic B (spaced repetition):**
Para 4 (full); para 5 (full, with para 5 sentence 3 shared with A); para 6 sentences 1–2; para 11 (partial)

**Topic C (generation effect):**
Para 6 sentences 3–6; para 7 (full); para 8 (full); para 9 (full, with sentence 3 shared with A)

**Topic D (external tools):**
Para 8 sentences 4–5 (shared with C); para 11 (full); para 12 (full)

---

## Expected notes from seeded prior notes (non-bootstrapping case)

Given the four seeded prior notes, the article should produce:

| Prior note | Expected update | New content added |
|------------|----------------|-------------------|
| `spaced-repetition.md` | UPDATE | Para 4 confirms and extends; para 5 adds the quality-of-retrieval insight (longer gap → harder reconstruction → more encoding) |
| `testing-effect.md` | UPDATE | Paras 2–3 confirm; para 9 adds elaborative interrogation as equivalent mechanism |
| `external-memory-systems.md` | UPDATE | Paras 11–12 add the accumulation trap and the "sometimes harder is better" design implication |
| `encoding-and-memory-formation.md` | UPDATE | Para 10 synthesis adds passive exposure as the common failure mode |
| *(none)* | CREATE: generation-effect | Paras 6–8 introduce a topic not present in any prior note |
