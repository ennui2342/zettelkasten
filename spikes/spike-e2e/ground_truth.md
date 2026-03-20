# End-to-End Test — Ground Truth

*Committed before running e2e.py. Predictions based on corpus reconnaissance.*

---

## Expected Form output

Approach B should produce 6–8 draft notes from the article. Expected topics:

1. **Desirable difficulties framework** — Bjork's concept unifying spacing/testing/interleaving/generation under a single mechanism
2. **Spacing and testing as co-instances** — or merged with (1) depending on granularity
3. **Reconstruction: learning vs reliability** — two incompatible applications of reconstructive memory
4. **Generation effect and interleaving** — producing vs receiving information; interleaved vs blocked practice
5. **Context-dependent retrieval / cue-dependent forgetting** — same mechanism, two descriptions
6. **The Feynman Technique** — may merge with (4) under "generation and active encoding" per the Approach B guidelines ("named techniques belong inside a broader topic")
7. **SRS software architecture** — SM-2, FSRS, scheduling engineering; distinct enough from memory science to likely get its own note

---

## Expected integration operations

| Draft note | Expected operation | Target note(s) | Reasoning |
|---|---|---|---|
| Desirable difficulties framework | SYNTHESISE | `wiki-903495-spacing-effect` + `wiki-905659-testing-effect` | Neither note mentions Bjork's desirable difficulties framework; draft creates a bridging note articulating the unifying principle |
| Spacing and testing (if separate note) | UPDATE | `wiki-903495-spacing-effect` | Adds desirable difficulties framing and the explicit link to testing effect |
| Reconstruction: learning vs reliability | SPLIT | `wiki-34658270-reconstructive-memory` | Existing note is entirely about distortion/reliability; draft explicitly argues these are two distinct applications of reconstruction leading to opposite conclusions |
| Generation effect and interleaving | CREATE | (absent) | No note on generation effect in corpus; interleaving also absent; dense enough neighbourhood (encoding, testing effect, memory consolidation) that it should CREATE rather than STUB |
| Context/cue-dependent retrieval | MERGE | `wiki-2367207-cue-dependent-forgetting` → `wiki-21312301-context-dependent-memory` | Draft explicitly argues these are the same mechanism described from opposite outcomes; existing notes are already linked but maintained separately |
| Feynman Technique (if own note) | STUB | (absent) | Named practical technique with no direct corpus note; has semantic neighbours (testing effect, generation effect) but is a distinct procedure, not a cognitive science phenomenon |
| Feynman Technique (if merged into generation effect draft) | Part of CREATE above | — | Likely outcome per Approach B's "named techniques belong inside broader topic" instruction |
| SRS software architecture | STUB | (absent) | Implementation details (SM-2, FSRS, scheduling algorithms) have no corpus notes; `wiki-903495-spacing-effect` and `wiki-30984115-memrise` are the only neighbours, neither covers algorithm design |

---

## Uncertain predictions

- **SYNTHESISE vs UPDATE**: the desirable difficulties draft might trigger UPDATE on both `spacing-effect` and `testing-effect` (adding the framework as context) rather than creating a new bridging note. Depends on how much distinct bridging content the draft note contains.

- **Feynman Technique note**: likely merged into generation effect draft by Form phase. If so, no separate STUB — the generation effect draft CREATEs and Feynman is a section within it.

- **SRS STUB vs CREATE**: the cluster for SRS content will include `wiki-903495-spacing-effect` and `wiki-30984115-memrise`. Whether that's "sparse enough" for STUB or has a clear gap that warrants CREATE is borderline. STUB is more likely given the engineering vs science distinction.

- **NOTHING**: the article briefly restates the forgetting curve finding (Ebbinghaus, 1880s, predictable decay curve). This may surface `wiki-10967-forgetting-curve` in the cluster for the desirable difficulties or spacing/testing draft. The integration LLM may produce NOTHING for any draft whose content is already well-covered. Most likely candidate: a draft note that only restates spacing effect basics would hit NOTHING, but the article's content goes well beyond what's in the existing notes.

---

## What a good result looks like

- SYNTHESISE fires for desirable difficulties and produces a coherent bridging note that neither spacing-effect nor testing-effect currently contains
- SPLIT fires for reconstruction and produces two focused notes (one on reconstruction-as-learning-mechanism, one on reconstruction-as-distortion-source)
- MERGE fires for cue-dependent/context-dependent and the resulting note consolidates without losing content from either
- The SRS draft gets STUB with a note that includes enough vocabulary to be retrievable (per the richer stub prompt design)
- Two-step coherence: step 2's content matches what step 1's reasoning described (the integration decision and the written output are consistent)
