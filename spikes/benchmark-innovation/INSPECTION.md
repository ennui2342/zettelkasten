# Zettel Inspection Approach

Before authoring benchmark tasks, the ingested zettel must be inspected as a quality gate. This document defines the inspection checklist and its rationale. Run it after every significant pipeline change, before any task authoring work begins.

The inspection is not a celebration of the run — it is a test of whether the zettel's content is trustworthy enough to anchor benchmark questions to. If notes have drifted from their titles, synthesis is superficial, or late-paper notes are too weak to retrieve, benchmark tasks will have poor validity regardless of evaluation methodology.

---

## Step 1 — Note Quality

Does Form produce stable integration targets?

- **Title scoping:** titles should name a transferable concept, not a paper, method, or system. "Memory Poisoning Attacks on LLM Agents" is right; "AnchorRAG: Multi-Agent Collaboration for Open-World Knowledge Graph Question Answering" is not. Survey-section headings ("Environments and Applications of LLM-Based Agents") are also failures — too broad to be stable retrieval targets.
- **Content vs. extraction:** notes should synthesise and abstract, not quote or paraphrase source text. A note that reads like a well-written abstract has failed to generalise. Look for whether the note makes an argument that isn't present in any single source.
- **Granularity consistency:** are all notes at roughly the same level of abstraction, or do some cover a single paper's formal model while others cover an entire research domain? Large granularity spread degrades retrieval precision and makes benchmark anchoring unreliable.

**Pass criterion:** the majority of notes have concept-naming titles, contain genuine synthesis beyond any single source, and are within roughly 2× of each other in scope. System-named notes and survey-level notes should be rare exceptions, not a pattern.

---

## Step 2 — UPDATE Quality

Does integration actually integrate?

- Pick 3–4 notes with multiple cross-paper updates and read the full content. The question is whether the note reads as a unified treatment of the concept, or as clearly-delineated sections appended one at a time.
- Look for explicit handling of tension: where two papers said different things about the same mechanism, does the note say so, or does it silently adopt the later view?
- Check whether UPDATE preserved the note's conceptual identity — did the subject matter drift, or does the note remain coherent around its original concept?

**Pass criterion:** hub notes read as unified treatments, not accretion stacks. At least one note should show explicit tension handling.

---

## Step 3 — Hub Note Analysis

Genuine breadth vs. retrieval inflation?

The hub notes (notes with the most cross-paper updates) need to be read carefully with the co-activation confound in mind (see `docs/design/benchmark-innovation.md` §5.4). Notes created early in an empty zettel are forced to be broad and foundational; later co-activation weight compounds this into over-retrieval.

- Is the hub note's content genuinely foundational, or an unfocused accumulation that grew large because it was always retrieved?
- A healthy hub note has a clear thesis and clear structure. A pathological one reads like a flat dump.
- Can you articulate *why* retrieval kept routing to this note? If the answer is "it's the closest general treatment of the topic," that's healthy. If it's "it got big and stayed vague," that's a retrieval failure mode.

**Pass criterion:** hub notes have identifiable theses and structural organisation. You can state in one sentence what each hub note is *about* and why it belongs at the centre of the graph.

---

## Step 4 — SYNTHESISE Note Quality

Are bridges genuine?

- Does the bridging note identify a specific relationship between the two source notes, or just assert that two things are related?
- Is the bridge title doing work — naming the relationship, not just listing the topics?
- Does reading the bridge note give you something you couldn't get from reading the source notes separately?
- Sample mid-quality examples, not just the best-looking ones from the run report.

**Pass criterion:** the majority of sampled SYNTHESISE notes name a specific relationship (not "X and Y are related") and add inferential content not present in either source note.

---

## Step 5 — Late-Paper Notes

Specificity and retrievability for benchmark validity.

This is critical for benchmark validity. At least a third of benchmark tasks should target late-ingested concepts where co-activation weight is low (see `docs/design/benchmark-innovation.md` §6.5).

- Read 4–5 notes first created in papers 14–19. Are they specific and well-scoped?
- Does their content depend on post-cutoff work specifically, or could the same note have been written from pre-cutoff training knowledge? (If the latter, they're weak anchors for temporal accuracy tasks.)
- Are they self-contained enough to serve as retrieval targets for benchmark questions?

**Pass criterion:** late notes are specific, corpus-grounded, and cannot be plausibly answered from model training knowledge alone.

---

## Step 6 — Epistemic Links

Are `contradicts`/`supersedes` links present and correct?

These links are the mechanism for tension identification tasks (task type 6.2 in the benchmark taxonomy). If they're absent or sparse:

- Are there actual contradictions in the corpus that the pipeline silently flattened?
- Or is the corpus genuinely non-contradictory?

Either answer is useful, but it must be known before authoring tension identification tasks. The corpus was deliberately composed with internal tensions (memory-as-asset vs. memory-as-attack-surface; communication-topology papers with contested value claims). If the pipeline didn't surface these as links, the tension identification task type has no valid anchors.

**Pass criterion:** at least one `contradicts` or `supersedes` link exists. If zero links: audit two known-tension pairs manually and determine whether the pipeline missed them or the notes were merged in a way that absorbed the tension.

---

## Step 7 — STUB Notes

Were stubs legitimate incompletions?

Stubs are supposed to be placeholders pending more evidence. If they look like under-confidence rather than genuine incompleteness, that's a pipeline quality issue.

- Read all stub notes.
- Were they cases where Form produced a concept the pipeline genuinely couldn't resolve yet?
- Or are they cases that should have been CREATE but misfired (low confidence, poor retrieval match)?

**Pass criterion:** stubs look like genuine conceptual placeholders — concepts named but not yet grounded — rather than failed CREATEs.

---

## Step 8 — Confidence Outliers

What does the low-confidence operation look like by inspection?

Confidence is a quality signal, not an execution gate. Low-confidence operations still execute. Read the target note for any operation with confidence < 0.5 and assess whether the integration looks wrong by inspection, or whether the low confidence was overcautious.

**Pass criterion:** the integration in low-confidence operations is either (a) acceptably correct despite the low score, or (b) visibly wrong in a way that explains the score — no silent failures.

---

## Reports

Inspection findings are written up in `reports/` after each ingestion run:

- `ingest_YYYYMMDD_HHMMSS_report.md` — auto-generated run statistics (moved from `logs/`); corresponds to `zettel_YYYYMMDD_HHMMSS/`
- `inspect_YYYYMMDD_step{N}_{topic}.md` — one file per completed inspection step

The inspection is considered complete when steps 1–8 all have reports and all pass criteria are met or exceptions are documented.
