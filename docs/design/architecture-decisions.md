# Architecture Decisions

*Companion to `zettelkasten-memory.md` and `zettelkasten-implementation-plan.md`.*

*This document records settled design choices with their rationale. Each decision was made after experimental validation or deliberate elimination of alternatives. Read before changing any of the areas covered here.*

---

## 1. Note data model: intrinsic vs runtime

**Decision:** frontmatter contains only what is intrinsic to the note. The SQLite index is not just a cache — it is the home for relational and runtime state.

The distinction:

| Intrinsic (frontmatter, travels with the file) | Runtime (SQLite only) |
|---|---|
| id, type, confidence, context, body | Embeddings |
| Epistemic links (contradicts, supersedes, curation provenance) | BM25 index |
| created, updated | Activation edges |
| See Also wikilinks (in body) | |

**Why:** if you send a zettel to someone else, they receive the knowledge. They do not receive — and should not receive — your system's learned relationship weights. Activation edges record how *this installation* has used the notes, not what the notes mean. They rebuild organically as the new system processes documents.

The rebuild story: embeddings and BM25 are derived from content and rebuildable from the filesystem. Activation edges warm up over time from new integration events. Losing the SQLite index is recoverable; losing the markdown files is not. The markdown files are the source of truth.

**What this removes from frontmatter:** the `co_activations` list (previously stored per note) moves entirely to a SQLite edge table. See §5 for the new activation data model.

---

## 2. Retrieval: five-signal weighted fusion

**Decision:** five signals, validated weights, top-20 cluster window.

```
body_query:       0.450   dense embedding, asymmetric query/document
bm25_mugi_stem:   0.270   BM25 + MuGI pseudo-note expansion + Porter stemming
activation:       0.180   pairwise co-activation graph (see §5)
step_back:        0.050   LLM step-back abstraction (discovery)
hyde_multi:       0.050   average of 3 hypothetical peer-note embeddings (discovery)
```

Weights tuned on 80% of 299 LLM-judged retrieval events; R@10=0.667, MRR=0.844 on held-out 20%.

**Body-only baseline:** R@10=0.542. The five-signal blend adds +12.5pp R@10 and +6.9pp MRR.

**Why top-20:** 63% gold-note recall vs 49% at top-10. Union coverage 93.7% at K=20.

**Asymmetric embedding:** query notes use `input_type='query'`, corpus notes use `input_type='document'` (Voyage API). The distinction matters.

**Parallel LLM calls:** MuGI, step-back, and HyDE run concurrently via `ThreadPoolExecutor`.

**Important caveat on the activation weight:** the R@10=0.667 figure represents the *ceiling* of the activation signal — what it contributes assuming perfect recording of gold notes at integration time. The four other signals (body_query, bm25, step_back, hyde_multi) are real measurements of production behaviour. Activation's real-world contribution is lower; see §5.

*Detail: `model-tests/retrieval-signals/README.md`*

---

## 3. Links: epistemic only

**Decision:** three link types, no others.

| Type | Meaning | Created by |
|------|---------|-----------|
| `contradicts` | Conflicting claim; both notes preserved | Integration LLM |
| `supersedes` | Replaces target after revision; target → `type: refuted` | Integration LLM |
| `splits-from` / `merges-into` | Corpus restructuring provenance | Curation agent |

No `supports`, `extends`, `related-to`, or any semantic link type.

**Why:** spike 4A showed citation-style link traversal hurts retrieval — it expands clusters to 53 nodes of which only 15.6% are gold targets. Spike 4D confirmed 83% of missed connections have no link or tag signal; they are inferential, not structural. Semantic proximity is the retrieval signals' job. Typed links are reserved for relationships that embeddings cannot capture: claim conflict, revision, and curation provenance.

**See Also wikilinks:** notes may contain an informal `## See Also` section using `[[note-id|Title]]` syntax. These are not epistemic links and are not in the `links:` frontmatter field. During the integrate phase, the LLM persistently generated junk sections ("Recommended Reading", hallucinated tag systems) to express connections it wanted to make. Explicitly permitting a See Also section eliminated all junk output. The link descriptions the LLM writes are high quality. Algorithmic utility of See Also links is undecided — they are not indexed or traversed.

---

## 4. Tags: dropped

**Decision:** no `tags:` field on system-generated notes.

**Why:** tags are a human browsing aid. Retrieval is by embedding + BM25 + activation, none of which uses tags. LLM-generated tags are noisy and add maintenance burden with zero retrieval benefit. Human-authored notes may retain tags for UI navigation.

---

## 5. Activation: pairwise graph with transitive expansion

**Decision:** pairwise co-occurrence graph, transitive expansion enabled, C-style permissive recording prompt, stored in SQLite edge table.

### Why pairwise over scalar

Two architectures were evaluated:

**Scalar model:** each note has a single `activation_strength` value. When activated, the scalar is bumped. At query time, all notes return their scalar — Q-independent. This is a note-popularity signal.

**Pairwise graph:** edge weights stored per *(note_a, note_b)* pair. At query time for Q, only notes with a direct edge to Q score. The signal is Q-specific.

Full grid of results (R@10, held-out n=60):

| Recording | Pairwise | Scalar |
|-----------|----------|--------|
| Gold (ceiling) | 0.666 | 0.607 |
| k20 uniform | 0.603 | 0.590 |
| B prompt (prescriptive) | 0.617 | 0.590 |
| C prompt (permissive) | 0.620 | 0.590 |

Scalar k20/B/C all collapse to 0.590 — in the scalar model, recording strategy is irrelevant because Q-specificity is lost regardless of what was selected. Pairwise gold (0.666) exceeds every scalar variant. **Pairwise wins clearly.**

### Why transitive expansion

When an event records activation for [A, B, C] alongside query Q, transitive expansion also adds edges (A,B), (A,C), (B,C). This creates indirect paths: notes that have been co-retrieved with Q in *other notes' events* can score when Q is the query — not just notes Q directly triggered.

Pairwise gold with transitive: 0.666. Without: 0.630. Real 3.6pp gain. **Keep transitive expansion.**

### Why C-prompt recording over prescriptive B or k20

What gets recorded at integration time determines signal quality. Three realistic options tested against gold ceiling:

- **k20:** record all 20 retrieved notes (pairwise 0.603) — too broad, noisy
- **B (prescriptive):** LLM selects with explicit UPDATE/SYNTHESISE guidance (pairwise 0.617)
- **C (permissive):** LLM selects with open-ended INTERACT framing (pairwise 0.620)

B vs C difference (0.003pp) is within noise on a 60-event test set. C is preferred on design grounds: simpler prompts with less operation guidance are more robust to future operation changes and give the LLM more latitude to find genuine interactions.

**Recording quality gap:** pairwise C (0.620) vs pairwise gold (0.666) — 4.6pp. This is irreducible with Haiku; it reflects the difference between a well-prompted production LLM and human-judged ground truth.

### SQLite edge table design

```sql
CREATE TABLE activation (
    note_a   TEXT NOT NULL,
    note_b   TEXT NOT NULL,
    weight   REAL NOT NULL DEFAULT 0.0,
    updated  TEXT NOT NULL,          -- ISO timestamp of last write
    PRIMARY KEY (note_a, note_b)
);
CREATE INDEX activation_a ON activation(note_a);
CREATE INDEX activation_b ON activation(note_b);
```

**Recording** (when an event fires with `qid` and `selected_ids`):
```python
pairs = [(qid, sid) for sid in selected_ids]
pairs += list(combinations(selected_ids, 2))   # transitive expansion

for a, b in pairs:
    a, b = min(a, b), max(a, b)     # canonical ordering: one row per pair
    row = db.get(a, b)
    if row:
        elapsed_days = (now - row.updated).days
        effective = row.weight * exp(-lam * elapsed_days)  # lazy decay
    else:
        effective = 0.0
    db.upsert(a, b, weight=effective + 1.0, updated=now)
```

**Query** (for a given `qid`):
```python
rows = db.query(
    "SELECT note_a, note_b, weight, updated FROM activation "
    "WHERE note_a = ? OR note_b = ?", qid, qid
)
scores = {}
for row in rows:
    partner = row.note_b if row.note_a == qid else row.note_a
    elapsed_days = (now - row.updated).days
    scores[partner] = row.weight * exp(-lam * elapsed_days)
```

**Properties:**
- No frontmatter pollution — `co_activations` field eliminated entirely
- Lazy decay per edge — no background jobs; decay applied on read and write
- λ is a runtime parameter, not baked into stored values — change without migrating data
- Bounded growth — prune with `DELETE WHERE weight < threshold` periodically
- Canonical edge ordering (`min/max`) ensures one row per pair, no duplicates

**λ tuning:** deferred — requires benchmark ingestion ground truth with real timestamps. Run the activation variant sweep in `model-tests/retrieval-signals/tune_weights.py` Phase 3 once real-event ground truth is available.

**Recording prompt (C-style):**
```
Identify which existing notes this new note would INTERACT with during
integration — notes whose content this note meaningfully extends,
challenges, or bridges.

Return JSON only: {"target_note_ids": ["id1", "id2", ...]}
```

*Detail: `model-tests/retrieval-signals/README.md`*

---

## 6. Integration: three-step pipeline

**Decision:** Step 1 classify → optional Step 1.5 for large notes → Step 2 execute.

- **Step 1** (fast LLM, temperature=0, max_tokens=512): returns `{operation, target_note_ids, reasoning, confidence}` as JSON
- **Step 1.5** (fast LLM, temperature=0, max_tokens=256): fires only when Step 1 returns UPDATE and the target note exceeds `NOTE_BODY_LARGE` (8,000 chars). Asks EDIT or SPLIT. Default on parse failure: EDIT.
- **Step 2** (main LLM, temperature=0.3): executes the operation, writes note content

**Step 1 `target_note_ids` as recording source:** the notes returned in `target_note_ids` are the LLM's gold-note nominations — which existing notes this draft most directly interacts with. These are what the C-prompt activation recording should capture. The field is semantically meaningful across all operation types; the integration prompt should make this explicit.

**EDIT rationale:** notes grow unboundedly through repeated UPDATEs. A 21,000-char note fed to a `max_tokens=4096` UPDATE call is silently truncated. EDIT intercepts this: Step 1.5 presents the large note with the draft and asks the LLM to choose between compression (EDIT) and structural division (SPLIT). EDIT is conservative; SPLIT is chosen only when the draft genuinely clarifies that two distinct topics are conflated.

---

## 7. Operations: ingestion-time vs curation-only

**Decision:** all operations execute at ingestion time. SPLIT fires via step 1.5 only.

| All ingestion-time | Curation-only (none currently) |
|---|---|
| CREATE, UPDATE, EDIT, STUB, SYNTHESISE, SPLIT, NOTHING | — |

SPLIT fires via step 1.5 when a large UPDATE target is found to conflate two distinct topics. It does not fire from step 1 directly — Form separates topics before integration sees them, so a document arguing a note conflates two things produces two content notes that each target the conflated note with UPDATE.

---

## 7a. MERGE: deprecated from the operation vocabulary

**Decision:** MERGE removed from ingestion and the prompt vocabulary. Reintroduce only if duplicate accumulation becomes visible in operational zettels.

**Rationale from experiment** (see `spikes/merge-test/`): MERGE never fired across any scenario in full-pipeline testing. Attempts to force it via prompt engineering revealed a structural reason: Form strips the "these are the same thing" framing from bridging texts before Step 1 sees them. Step 1 sees topic notes, not comparison prose. Even with prompt variants that correctly fired MERGE on raw bridging text, real Form outputs collapsed the win.

**Why the corpus doesn't need MERGE:** the pipeline keeps notes clean through a different set of mechanisms that make collapse redundant:

- **EDIT** continuously compresses notes that accumulate via repeated UPDATEs, preventing the bloat that would make two notes feel like duplicates.
- **SPLIT** separates conflated concepts as the corpus matures, maintaining distinct identity for topics that Form initially merged.
- **SYNTHESISE** handles the case where two notes are closely related — rather than collapsing them, it articulates *what is between them* as a third note expressing the bridging principle. This preserves both retrieval surfaces and creates the relationship as knowledge in its own right.

Two notes covering the same concept from different framings provide two distinct retrieval paths. MERGE collapses these into one. The experiment confirmed that the SYNTHESISE note generated for an apparent MERGE candidate contained genuine insight that a MERGE note did not — because the model was forced to articulate what was actually between the two notes rather than collapsing them. The innovation the system is designed to produce emerges most reliably when notes are kept separate.

**If MERGE is needed in future:** the appropriate trigger is a scheduled curation pass with human review — scanning for cosine similarity > 0.90 pairs and confirming via LLM — not ingestion-time automation. The prompt has been written without MERGE in the vocabulary; if reintroduced, it would be as a curation-only operation.

---

## 8. Stub lifecycle

**Decision:** stubs promote to `permanent` when retrieved into a second cluster.

A stub is a placeholder for a concept the corpus recognises but cannot yet fully articulate. The natural promotion trigger is retrievability: if a stub is retrieved into a second cluster, it has proven it can be found and used, and should become `permanent`.

**Current status:** promotion logic is not yet implemented. A stub that receives multiple UPDATEs remains `type: stub` indefinitely. Flag as a pipeline gap when implementing the store.

**Stub creation quality:** when creating a STUB, include concept title, 1–2 sentence definition, and 3–5 synonyms/related terms. This prevents retrievally-invisible stubs — the main orphan failure mode.

---

## 9. LLM provider abstraction

**Decision:** caller-supplied via protocol; library is not locked to any SDK.

```python
class LLMProvider(Protocol):
    def complete(self, messages: list[dict], model: str,
                 max_tokens: int, temperature: float) -> str: ...
```

Embedding provider follows the same pattern. The `fast_llm` parameter takes a second provider for Gather LLM calls (MuGI, step-back, HyDE) and Step 1 classification. Defaults to `llm` if not supplied.

**Model tier defaults:** Opus for Form and Integrate Step 2 (quality-critical). Haiku for Gather LLM signals and Step 1.

---

## 10. Note schema

```yaml
id: z20260315-007
type: permanent          # permanent | synthesised | stub | refuted
confidence: 0.85
context: >               # 2–3 sentence semantic positioning for retrieval
  ...
created: 2026-03-15T03:16:10+00:00
updated: 2026-03-17T11:04:22+00:00
links:
  - id: z20260310-002
    rel: contradicts
```

ID format: `z{YYYYMMDD}-{seq:03d}`. Body is plain markdown following the frontmatter. Closed link vocabulary enforced at write time.

---

## 11. See-also link accuracy

**Status:** deferred — monitor first, implement if link pollution grows.

Notes written by the execute step contain `[[Title]]` wiki-links to related notes. Two failure modes were observed in the 20-paper ingestion run:

1. **Hallucinated titles** — the LLM writes a plausible-sounding title that never existed (e.g. `[[Retrieval-Augmented Generation, GraphRAG, and Retrieval Corpus Governance]]` when the actual note was titled differently). Frequency: low (1 broken link in 31 notes after 20 papers).

2. **Title drift** — a note's title changes through EDIT or UPDATE, making old links stale. This is structurally unavoidable without active maintenance, since notes are dynamic topics rather than stable concepts. Future splits may also make a link point to only half of what it originally referenced, with no obvious signal that the semantic justification has degraded.

**Deferred approach** (implement if pollution grows): at execute time, provide the execute prompt with the list of note titles already in the retrieved cluster — the top-20 notes the LLM already has in context. This is bounded (always ≤20), free (already in context), and prevents hallucination for in-cluster links, which are the most common and most likely to be hallucinated. It does not solve cross-cluster links or drift.

**Post-processing for drift:** when a note is renamed, a filename-based find-and-replace across all note bodies is straightforward and would handle simple title drift. It does not handle semantic drift caused by SPLIT or accumulation.

**Experimental posture:** leave existing broken/stale links in place and observe over the next papers. The hypothesis is that future EDITs, UPDATEs, and SPLITs will either naturally correct stale links (the execute step rewrites see-also sections) or the broken links will prove harmless. If hallucinated links appear to be feeding false context into L1/L2 classification, implement the cluster-title solution at execute time. See `model-tests/ingestion-harness/ANALYSIS_GUIDE.md` for the monitoring checklist.
