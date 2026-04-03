# Model Test: Form Phase Granularity

*Moved from `spikes/spike2-fuzzy-form/`. See original spike documentation below.*

## The decision

Use **single-shot** Form phase (one prompt: identify and extract all topics simultaneously). The stepped approach (CARPAS-inspired: count topics first, name them, then extract) was eliminated.

**What's model-sensitive:** Single-shot relies on the model holding topic structure in attention across a multi-topic extraction in one pass. Weaker models may benefit from the scaffolding of the stepped approach; stronger models may produce finer-grained topics with neither.

## Baseline

*Run: 2026-03-14 | Model: claude-opus-4-6*

| Approach | Topics produced | Topics correct | Ambiguous handling |
|----------|----------------|---------------|--------------------|
| Stepped (CARPAS) | 2 | Partially (too coarse — conflated topics A+B and C+D) | Poor |
| Single-shot | 4 | ✓ All 4 expected topics | Good |

Ground truth: 4 topics (Testing Effect, Spaced Repetition, Generation Effect, External Tools). See `ground-truth.md`.

## Re-run

```bash
docker compose run --rm dev python eval/form-granularity/spike.py
```

Compare output against `ground-truth.md` — check: (a) number of topics, (b) topic names, (c) that ambiguous sentences appear in the correct note, (d) padding sentences are not duplicated across notes.

## Interpret results

| Outcome | Action |
|---------|--------|
| Single-shot still produces 4 correct topics | No change needed |
| Single-shot collapses to fewer topics | Check if model is over-generalising; consider adding granularity guidance to the prompt |
| Single-shot produces more topics (5+) | Check for over-splitting — named sub-concepts should be inside notes, not separate |
| Stepped now produces equivalent results | Stepped no longer needs scaffolding — but single-shot is still simpler |

---

## Original spike documentation

**What this spike tests:** whether the Form phase of the consolidation algorithm can decompose a fuzzy document (no section headings, topics interwoven throughout) into well-scoped topic-scoped draft notes.

**Hypothesis under test (H10):** two approaches are viable for fuzzy document decomposition — stepped (count → name → extract) and single-shot (one prompt). This spike determines whether they produce equivalent results and whether the stepped scaffolding adds value.

**Scope:** Form phase only. The output is draft notes. Integration of those drafts into the existing knowledge base is Spike 3. The prior notes in `prior-notes/` are reserved for Spike 3 — they are not fed into any prompt here.

---

## Test material

**`article.md`** — a ~1000-word essay ("Forgetting Is Not the Enemy") on memory and learning. Four topics woven throughout without section headings:

| Topic | Subject |
|-------|---------|
| A | Testing effect — retrieving from memory strengthens the trace; recall outperforms re-reading |
| B | Spaced repetition — timing practice to the forgetting curve |
| C | Generation effect — producing information deepens encoding more than passive capture |
| D | External tools and cognitive off-loading — when knowledge systems help vs substitute |

The article has deliberate A-B-A-B interweaving, three sentences that legitimately belong to two topics, and padding content (intro paragraph, synthesis paragraph, transitions) that has no strong topic membership.

**`ground-truth.md`** — the expected output of the Form phase. Consult this when evaluating results:
- Paragraph-level topic annotation (primary and secondary)
- Three flagged ambiguous sentences with expected extraction behaviour
- Expected content per topic extraction
- Padding sentences that should not dominate any extraction

**`prior-notes/`** — four existing knowledge base notes covering topics A, B, D partially. These are **not used in this spike**. They are the existing cluster for Spike 3.

---

## Approach A — Stepped (CARPAS-inspired)

Three sequential prompts. Tests whether the model produces well-granulated topics when given explicit structural scaffolding.

**Step 1 — Count:**
```
The following essay covers several distinct topics.
How many distinct topics does it address, at Wikipedia-article granularity?
A topic is distinct if it would merit its own Wikipedia article.
Do not sub-divide within a topic.
Predict the count as a single integer.

Essay:
{article}
```

**Step 2 — Name:**
```
The essay covers exactly {N} distinct topics at Wikipedia-article granularity.
Name them. Use the name a Wikipedia article would have.
```

**Step 3 — Extract (run once per topic):**
```
Topic: {topic_name}

Extract everything the following essay says about this topic.
Draw from anywhere in the essay — relevant content may appear in any paragraph.
Write in your own words. Do not copy sentences verbatim.
If a piece of content is relevant to this topic and also to another topic, include it here anyway.

Essay:
{article}
```

---

## Approach B — Single-shot

One prompt. Tests whether a capable model can do the same task without scaffolding.

```
The following essay covers several distinct topics.
For each distinct topic, produce a topic note at Wikipedia-article granularity.

A topic note should:
- Cover one subject comprehensively
- Draw relevant content from anywhere in the essay — do not restrict to adjacent passages
- Be written in your own words
- Include content at the boundary of two topics in both relevant notes

Essay:
{article}
```

---

## Evaluation

Evaluate both approaches against `ground-truth.md`. Do not use the prior notes.

**Topic identification:**
- How many topics did the model identify? (Expected: 4, approximately)
- Are they at the right granularity — Wikipedia-article level, not sub-topics or over-broad categories?
- Were all four topics found (A: testing effect, B: spaced repetition, C: generation effect, D: external tools)?

**Content coverage per topic** (check each against the expected paragraphs in ground-truth.md):
- Does the extraction cover the expected paragraphs for that topic?
- Is anything from the wrong topic included (cross-contamination)?
- Is anything hallucinated — content not present in the article?

**Scattered content** (the key fuzzy-document test):
- Does the extraction for each topic pull content from across the article, not just contiguous passages?
- Specifically: does topic A include the retrieval-as-encoding content from paragraph 3 AND the bridging sentence from paragraph 9?

**Ambiguous sentences** (check the three flagged sentences in ground-truth.md):
- Does each appear in both relevant topic extractions, or only one?
- Appearing in both is correct. Appearing in neither is a miss.

**Padding handling:**
- Does the intro paragraph (padding) dominate or inflate any topic extraction?
- Does the synthesis paragraph (para 10) get absorbed wholesale into one topic, or distributed?

**Approach comparison:**
- Did stepped vs single-shot produce materially different topic boundaries?
- Did stepped produce better or worse granularity?
- Which handled the ambiguous sentences better?
- Which was more prone to including padding content?

---

## Recording results

Create `results.md` in this directory. For each approach, record:
- The topics the model identified (names)
- The full extracted content per topic
- Scores against the evaluation criteria above
- Qualitative notes on failure modes

End with a recommendation: stepped or single-shot? Or are they equivalent — suggesting the scaffolding adds no value?

---

## Go criteria

Either approach produces:
- 3–5 topics identified (4 expected)
- Each topic extraction covers ≥ 80% of the expected content from ground-truth.md
- Ambiguous sentences appear in at least one correct extraction (ideally both)
- No significant hallucination

## No-go

Topics are systematically wrong granularity (too fine or too coarse), or extractions consistently miss major expected content, or hallucination is substantial. Iterate prompt design — try variations on the count prompt wording, the extraction instruction, or the granularity definition.
