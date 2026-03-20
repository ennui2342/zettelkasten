# Pipeline: Form → Gather → Integrate

`store.ingest_text(text, llm, embed, fast_llm=None)` runs three sequential
phases for each document.  Each draft note produced by the Form phase passes
through Gather and Integrate independently.  `fast_llm` is used for the
Gather LLM signals (MuGI, step-back, HyDE); defaults to `llm` if not
supplied.

---

## Phase 1 — Form

**Goal:** extract `n` draft topic notes from a raw document in one LLM call.

**Invocation:**
```python
from zettelkasten.form import form_phase
drafts = form_phase(text, llm)
```

**What happens:**
1. Builds a prompt instructing the LLM to identify distinct broad topic areas.
2. Calls `llm.complete(prompt, max_tokens=4096, temperature=0.0)`.
3. Parses the response: splits on `## ` headings; each section becomes a draft.
4. Returns `list[ZettelNote]` where every note has `id=""`, `type="stub"`,
   `confidence=0.3`, no embedding, no links.

**Prompt guidelines (from spike2 validation):**
- Topic areas must be broad enough to warrant their own Wikipedia article.
- Named sub-concepts belong *inside* a note, not as separate notes.
- Content scattered across paragraphs is gathered into the relevant note.
- Content at a topic boundary appears in both notes.

**Draft format expected from LLM:**
```
## [Topic name]

[Content]

## [Another topic]

[Content]
```
Pre-heading preamble is ignored.  Responses with no `##` headings return `[]`.

---

## Phase 2 — Gather

**Goal:** retrieve the top-20 existing corpus notes most relevant to a draft.

**Invocation:**
```python
from zettelkasten.gather import gather_phase
cluster = gather_phase(draft, corpus, llm, embed, fast_llm=None, top_k=20)
```

**Five signals, validated weights (R@10=0.667, MRR=0.844, held-out n=60):**

| Signal | Weight | Description |
|--------|--------|-------------|
| `body_query` | 0.450 | Draft body embedded with `input_type="query"` → cosine similarity with corpus body embeddings |
| `bm25_mugi_stem` | 0.270 | BM25 retrieval with MuGI pseudo-note expansion (N=3) and Porter stemming |
| `activation` | 0.180 | Co-activation graph: notes that historically appeared together in integration events |
| `step_back` | 0.050 | Principle-level abstraction of the draft (LLM) → embed → cosine similarity |
| `hyde_multi` | 0.050 | Average of 3 hypothetical peer-note embeddings (LLM+embed) |

**Blending:**
```
blended = Σ weight[s] × min_max_normalise(score[s])
```

Min-max normalisation: `v / max(v)` (all-zero signals stay zero — safe with
empty activation graph).

**LLM calls during Gather** (using `fast_llm` if supplied, otherwise `llm`):
- MuGI: 1 call → `{"pseudo_notes": [...]}`
- Step-back: 1 call → `{"abstraction": "..."}`
- HyDE: 1 call → `{"hypotheticals": [...]}`

These three LLM calls run in parallel via `ThreadPoolExecutor`.

**Activation when corpus is empty / notes have no co_activations:** the
activation signal scores are all zero and survive normalisation — confirmed
in the E2E spike.  All 5 signals are active from day one.

---

## Phase 3 — Integrate

**Goal:** decide what to do with the draft given the retrieved cluster, then
execute that decision.

**Invocation:**
```python
from zettelkasten.integrate import integrate_phase
result = integrate_phase(draft, cluster, llm)
```

### Step 1 — Classify (`temperature=0`, `max_tokens=512`)

The LLM receives the draft and the cluster and returns JSON:
```json
{
  "operation":       "UPDATE",
  "target_note_ids": ["z20240101-001"],
  "reasoning":       "Draft adds new mechanism to an existing note.",
  "confidence":      0.85
}
```

**Operations:**

| Operation | When to use | Ingestion? |
|-----------|-------------|-----------|
| `CREATE` | New topic, not in cluster | ✓ |
| `UPDATE` | Draft extends an existing note (note is below size ceiling) | ✓ |
| `EDIT` | Existing note has grown verbose; compress without adding content | ✓ (via step 1.5) |
| `STUB` | New topic, no established neighbourhood | ✓ |
| `SYNTHESISE` | Draft reveals bridging principle between two notes | ✓ |
| `NOTHING` | Draft already fully covered | ✓ (no-op) |
| `SPLIT` | One cluster note conflates two topics | ✓ (via step 1.5) |

`EDIT` is never returned directly by step 1 — it is produced by step 1.5 (see below).
`SPLIT` is produced by step 1.5 when a large UPDATE target genuinely conflates two topics.

### Step 1.5 — Large-note refinement (`temperature=0`, `max_tokens=256`)

After step 1, if the operation is `UPDATE` and the target note exceeds
`NOTE_BODY_LARGE` (8 000 chars), a focused second classification call asks:

> Should this note be **EDIT**ed (same topic, compress) or **SPLIT** (genuinely
> two topics)?

The step 1.5 prompt contains only the large target note and the draft — no
other cluster notes.  The result (`EDIT` or `SPLIT`) replaces the step 1
`UPDATE` decision before step 2 runs.  If the response is unparseable, `EDIT`
is used as the safe default (prefer compression over structural surgery).

This avoids silent truncation: a `max_tokens=4096` UPDATE on a 21 000-char
note would be cut mid-sentence.

### Step 2 — Execute (`temperature=0.3`)

For executable operations, the LLM rewrites or creates the note content.

**Output format (LLM returns only this — no frontmatter):**
```
## Note Title

Note body text…
```

The library assembles the `ZettelNote` (id, timestamps, type, confidence,
salience, links, embedding, co_activations).  The LLM never writes frontmatter.

**max_tokens by operation:**

| Operation | max_tokens | Rationale |
|-----------|-----------|-----------|
| `UPDATE` | 4096 | Rewriting existing note — may be long |
| `EDIT` | 2048 | Reductive — output must be smaller than input |
| `SYNTHESISE` | 4096 | New structure note |
| `SPLIT` | 4096 | Producing two notes |
| `CREATE` | 2048 | Fresh notes are shorter |
| `STUB` | 2048 | Minimal stubs |

### After integration

For `CREATE`, `STUB`, `SYNTHESISE`:
- A new `ZettelNote` is created with a fresh `_next_id()` ID.
- Co-activation events are added linking the new note to `target_ids`.
- The body is embedded and stored (frontmatter + index).

For `UPDATE`:
- The existing note's title and body are replaced.
- Co-activation events are added for the other cluster members in context.
- The embedding is recomputed.

For `EDIT`:
- The existing note's title and body are replaced with the compressed version.
- **No co-activation events are added** — EDIT is a compression pass, not an
  integration event.
- The embedding is recomputed.

For `SPLIT`:
- The original note is rewritten as the primary split topic.
- A new note is created for the secondary topic with a fresh `_next_id()` ID.
- `splits-from` provenance links are added to both resulting notes.

---

## Activation accumulation

After each ingestion event, new `CoActivationEvent` entries are written to
the affected notes.  Over time, the activation graph captures the topology
of the knowledge base: notes that are semantically related appear together
in integration events and accumulate co-activation weights.

Future ingestions about the same topic area benefit from elevated activation
scores, effectively implementing a form of memory for retrieval.

---

## Performance characteristics (spike results)

| Phase | Spike | Key result |
|-------|-------|------------|
| Form | spike2 | Single-shot approach wins; CARPAS count-first eliminated |
| Gather retrieval | retrieval-workbench | R@10=0.667, MRR=0.844 (held-out n=60) |
| Integrate decision | spike3 | 85% correct classification, 100% consistent across runs |
| E2E pipeline | spike-e2e | All ingestion operations confirmed; SPLIT fires via step 1.5 on large notes |
