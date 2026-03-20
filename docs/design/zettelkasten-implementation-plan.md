# Zettelkasten Memory: Implementation Plan

*Companion to `zettelkasten-memory.md` — revised 2026-03-16*

---

## 1. Philosophy: Spikes Before Build

The design document enumerates ten experimental hypotheses. Several are well-grounded in literature; all are unvalidated in this specific system and data context. The worst failure mode is spending weeks implementing a full store only to discover that one load-bearing hypothesis (e.g. that predict-calibrate produces better notes than naive extraction, or that the integration LLM makes consistent 6-way decisions) is false in practice.

The spike-first approach isolates the three highest-uncertainty hypotheses into small, throwaway experiments before committing to full implementation. Each spike is designed to produce a go/no-go decision on its hypothesis within a day of work. The spikes are independent; they can run in parallel. The full build begins only after all three return a go.

**What spikes are not:** production code. They live in `spikes/`, use hardcoded paths, skip error handling, and are deleted after they inform the build. The point is fast learning, not clean code.

---

## 2. Spike Outcomes

All spikes are complete. Full detail in `docs/design/spikes/`.

| Spike | Key decision | Detail |
|-------|-------------|--------|
| Spike 1 — Boundary detection | Nemori naïve conf≥0.80; deferred from MVP | [spike1-boundary.md](spikes/spike1-boundary.md) |
| Spike 2 — Form phase | Single-shot wins; CARPAS eliminated | [spike2-form.md](spikes/spike2-form.md) |
| Spike 3 — Integration quality | 85% correct, 100% consistent; two-step selected | [spike3-integration.md](spikes/spike3-integration.md) |
| Spike 4A — Cluster identification | Full body embedding; link traversal eliminated; top-20 window | [spike4-gather.md](spikes/spike4-gather.md) |
| Spike 4B — Stable notes | Parked — needs real event history | [spike4-gather.md](spikes/spike4-gather.md) |
| Spike 4C — Link vocabulary | Epistemic links only (3 types); semantic links and tags dropped | [spike4-gather.md](spikes/spike4-gather.md) |
| Spike 4D — LLM ground truth | R@10=0.512 body-only baseline; 83% of misses have no structural signal | [spike4-gather.md](spikes/spike4-gather.md) |
| Spike 5 — Activation links | R@10=0.640 at α=0.2; small-world structure confirmed; W_null=0.0 | [spike5-activation.md](spikes/spike5-activation.md) |
| Spike 6 / Workbench | 5-signal fusion; R@10=0.667, MRR=0.844 held-out; 93% union coverage | [spike6-retrieval-workbench.md](spikes/spike6-retrieval-workbench.md) |
| Spike E2E | All ingestion operations confirmed; token limits fixed; cold-start works | [spike-e2e.md](spikes/spike-e2e.md) |

### Spike 1 — Episode Boundary Detection ✓
- Nemori naïve with conf≥0.80 selected (7 well-scoped episodes, score 4.0/5)
- ES-Mem two-stage eliminated: word-overlap stays high in domain-coherent streams
- Def-DTS labels useful as metadata annotation, not boundary trigger
- Deferred from MVP — implement only after document-ingestion dynamics are understood

*Full detail: [spike1-boundary.md](spikes/spike1-boundary.md)*

### Spike 2 — Fuzzy Document Form Phase ✓
- Single-shot extraction wins; CARPAS count-first eliminated
- 4 topics extracted matching 4 ground-truth topics; sub-topics absorbed correctly
- Ambiguous boundary content appears in both relevant notes
- Prompt validated; `## [Topic name]` format is load-bearing for parser

*Full detail: [spike2-form.md](spikes/spike2-form.md)*

### Spike 3 — Integration Decision Quality ✓
- 12/14 correct (85%), 14/14 consistent across runs
- STUB criterion: semantic isolation (sparse neighbourhood), not thin content
- MERGE/SYNTHESISE boundary: redundancy vs new unifying principle
- Documented gaps (`**Gap:**`, `**Open question:**`) are strong UPDATE signals
- Two-step design selected: Step 1 classify (Haiku), Step 2 execute (Opus)

*Full detail: [spike3-integration.md](spikes/spike3-integration.md)*

### Spike 4A — Cluster Identification ✓
- Full body embedding beats context field and summaries (R@5=0.274 vs 0.212)
- Citation-style link traversal eliminated: depth-1 grows cluster from 10→53 nodes, only 15.6% are gold targets
- Top-20 cluster window: 63% recall vs 49% at top-10

### Spike 4B — Stable Notes and Reconsolidation (parked)
- Cannot test without real integration events; revisit after ~100 events

### Spike 4C — Link Vocabulary (closed, no spike needed)
- Links are epistemic not semantic: `contradicts`, `supersedes`, `splits-from`/`merges-into` only
- Semantic/topical links are the retrieval signals' job; not stored
- Tags dropped: LLM-generated tags are noisy and add zero retrieval signal

*Full detail: [spike4-gather.md](spikes/spike4-gather.md)*

### Spike 4D — LLM Ground Truth ✓
- Body embedding R@10=0.512 (vs R@5=0.274 on Wikipedia link ground truth)
- 63% of gold notes in top-20; 83% of misses have no structural signal
- Missed connections are inferential and cross-domain — not recoverable from corpus structure

*Full detail: [spike4-gather.md](spikes/spike4-gather.md)*

### Spike 5 — Activation-Weighted Cluster Identification ✓
- R@10=0.640 at α=0.2 (+10.6pp above body baseline)
- H-new-B eliminated: W_null=0.0 (non-acted-on notes add no signal)
- Small-world structure confirmed: CC=0.541 vs ~0.056 for random graph
- Decay λ untested on synthetic data; treat as tunable deployment parameter

*Full detail: [spike5-activation.md](spikes/spike5-activation.md)*

### Spike 6 / Retrieval Workbench ✓
- 36% structural ceiling broken: union coverage 93% at K=20
- 5-signal fusion (body_query, bm25_mugi_stem, activation, step_back, hyde_multi)
- Validated weights: R@10=0.667, MRR=0.844 on held-out test (n=60)
- 7% unreachable is almost entirely contextual (65/100 pairs reach via other events); only 4 truly isolated notes (corpus artefact)
- `bm25_mugi_stem` (+3.4pp), `hyde_multi` (+8.1pp vs single HyDE) are the key upgrades

*Full detail: [spike6-retrieval-workbench.md](spikes/spike6-retrieval-workbench.md)*

### Spike E2E — Form → Gather → Integrate ✓
- CREATE, UPDATE, SYNTHESISE, STUB all confirmed working
- SPLIT mechanically blocked at ingestion: Form separates topics before integration sees them
- MERGE confirmed firing at ingestion at confidence 0.97 (subsequently deprecated — see §4 and architecture-decisions.md §7a)
- Double-loop: UPDATE not NOTHING (enrichment behaviour — net positive)
- Token limit fixed: UPDATE/SYNTHESISE/SPLIT → 4096 tokens; EDIT/CREATE/STUB → 2048
- Activation cold start confirmed working under normalisation

*Full detail: [spike-e2e.md](spikes/spike-e2e.md)*

---

## 3. Key Design Decisions

*Rationale and alternatives considered for each decision are in [`architecture-decisions.md`](architecture-decisions.md). The summaries below are the operative facts for implementation.*

### Retrieval

5-signal weighted fusion, held-out validated (R@10=0.667, MRR=0.844, n=60):

| Signal | Weight | Description |
|--------|--------|-------------|
| `body_query` | 0.450 | Draft embedded with `input_type='query'`; cosine similarity vs corpus body embeddings |
| `bm25_mugi_stem` | 0.270 | BM25 with MuGI pseudo-note expansion (N=3) + Porter stemming |
| `activation` | 0.180 | Co-activation graph: `Σ exp(-λ·age_days)` over past integration events |
| `step_back` | 0.050 | LLM-generated abstract principle; discovery signal |
| `hyde_multi` | 0.050 | Average of 3 hypothetical peer-note embeddings; discovery signal |

- Top-20 cluster window (93.7% union coverage at K=20)
- Asymmetric embedding: query notes use `input_type='query'`, corpus uses `input_type='document'`
- Activation cold start: all 5 signals active from day one; activation scores zero until events accumulate (confirmed safe under min-max normalisation)
- Gather LLM calls (MuGI, step-back, HyDE) run in parallel via `ThreadPoolExecutor`

### Integration

Three-step (step 1.5 fires only when UPDATE targets a large note):

- **Step 1 — Classify** (fast LLM, temperature=0, max_tokens=512): returns `{operation, target_note_ids, reasoning, confidence}` as JSON
- **Step 1.5 — Large-note refinement** (fast LLM, temperature=0, max_tokens=256): if step 1 returns UPDATE and the target note exceeds `NOTE_BODY_LARGE` (8 000 chars), a focused call asks EDIT or SPLIT. Default on parse failure: EDIT.
- **Step 2 — Execute** (main LLM, temperature=0.3, operation-specific max_tokens): rewrites or creates note content

Operations:

| Operation | When | max_tokens | Notes |
|-----------|------|-----------|-------|
| `CREATE` | New topic not in cluster | 2048 | |
| `UPDATE` | Draft extends existing note (note below size ceiling) | 4096 | |
| `EDIT` | Existing note >8 000 chars; compress without adding content | 2048 | Via step 1.5 only; no co-activations added |
| `STUB` | New topic, sparse neighbourhood | 2048 | |
| `SYNTHESISE` | Draft reveals bridging principle | 4096 | |
| `NOTHING` | Draft fully covered | — (no-op) | |
| `SPLIT` | Note conflates two topics | 4096 | Via step 1.5 only |

SPLIT executes at ingestion via step 1.5 when an UPDATE target exceeds the size ceiling and genuinely conflates two distinct topics. MERGE has been deprecated — see §4 and `architecture-decisions.md §7a`.

**EDIT rationale:** notes grow unboundedly through repeated UPDATEs. A note at 21 000 chars fed to a `max_tokens=4096` UPDATE call is silently truncated. EDIT intercepts this: step 1.5 presents the large note with the draft as context and asks the LLM to choose between compression (EDIT) and structural division (SPLIT). EDIT is conservative — it keeps the topic intact, just tighter. SPLIT is chosen only when the draft genuinely clarifies that two distinct topics are conflated.

**See Also wikilinks:** the LLM uses `[[id|title]]` syntax spontaneously in step 2 prompts to express connections. The library parses and stores these.

### Links

Epistemic only — three types, no others:

| Type | Meaning | Created by |
|------|---------|-----------|
| `contradicts` | Conflicting claim; both notes preserved | Integration LLM |
| `supersedes` | Replaces target after revision; target → `type: refuted` | Integration LLM |
| `splits-from` / `merges-into` | Corpus restructuring provenance | Curation agent |

No semantic links (embedding is the job). No tags (redundant with retrieval signals).

### Note identity

- Source of truth: markdown files
- ID format: `z{YYYYMMDD}-{seq:03d}` (e.g. `z20260315-007`)
- Markdown files are the source of truth for intrinsic note content; SQLite holds relational and runtime state
- Embeddings rebuildable from files. Activation edges are runtime state (not in frontmatter) — they warm up from integration history. See [`architecture-decisions.md §1`](architecture-decisions.md#1-note-data-model-intrinsic-vs-runtime)

### Models (tiered)

- **Opus:** Form phase + Integrate step 2 (quality-critical synthesis)
- **Haiku:** Gather LLM signals (MuGI, step-back, HyDE) + Integrate step 1 (structured classification)
- Configured via `fast_llm` parameter; defaults to `llm` if not supplied

---

## 4. Operation Classification: Ingestion vs Curation

*Emerged from the E2E spike.*

Operations divide into two sets with different triggers and timing:

**All operations are ingestion-time** (event-driven, triggered by incoming document):

| Operation | Trigger |
|-----------|---------|
| CREATE | Draft has no strong match in cluster |
| UPDATE | Draft adds to a note already in cluster (note below size ceiling) |
| EDIT | UPDATE target exceeds size ceiling; step 1.5 chooses compression |
| STUB | Draft has no match and cluster is sparse |
| SYNTHESISE | Draft reveals bridging principle between notes in cluster |
| SPLIT | UPDATE target exceeds size ceiling; step 1.5 chooses structural division |
| NOTHING | Draft is fully covered by the existing cluster |

### Why SPLIT fires via step 1.5, not step 1

Form separates topics before integration sees them. A document arguing that a note conflates two things produces two content notes, each targeting the conflated note with UPDATE. SPLIT reaches step 2 only via the step 1.5 path: when an UPDATE target exceeds 8 000 chars, step 1.5 asks whether the note should be compressed (EDIT) or structurally divided (SPLIT).

### MERGE: deprecated

MERGE has been removed from the operation vocabulary. See `architecture-decisions.md §7a` for full rationale. In brief: MERGE was found to destroy the retrieval surface that makes SYNTHESISE valuable, and the pipeline already manages corpus cleanliness through EDIT (compression), SPLIT (separation), and SYNTHESISE (bridging). If duplicate accumulation becomes visible in operational zettels, MERGE can be reintroduced as a scheduled curation pass with human review.

### Curation agent design (future)

If needed: runs on a sleep cycle (nightly or weekly). SPLIT pass: flag notes by high link degree (> 15 in ~300-note corpus), topic incoherence (top-20 neighbours cluster into two distinct groups), or compound signal (long body + incoherent neighbourhood); confirm and execute via LLM with two-cluster context. MERGE, if reintroduced: scan note pairs for cosine similarity > 0.90; confirm each candidate pair via LLM; execute if confirmed.

---

## 5. Build Status

| Phase | Description | Status |
|-------|-------------|--------|
| Data layer | ZettelNote, ZettelIndex, ZettelkastenStore | ✓ Complete |
| Providers | AnthropicLLM, VoyageEmbed, LLMProvider/EmbedProvider protocols | ✓ Complete |
| Form phase | form.py — single-shot fuzzy extraction | ✓ Complete |
| Gather phase | gather.py — 5-signal fusion, parallel LLM calls | ✓ Complete |
| Integrate phase | integrate.py — two-step, 6 ops (MERGE deprecated), See Also wikilinks | ✓ Complete |
| Store pipeline | store.ingest_text — Form→Gather→Integrate, STUB promotion, SPLIT via step 1.5 | ✓ Complete |
| CLI | cli.py — init, ingest, search, serve, rebuild-index, rewrite-notes | ✓ Complete |
| Server | server.py — HTTP ingest server for Chrome extension | ✓ Complete |
| Chrome extension | chrome-extension/ — Manifest V3, port-persisted popup | ✓ Complete |
| Public docs | docs/public/ | In progress |
| Boundary detection | segmenter.py — Nemori naïve, conf≥0.80 | Deferred from MVP |
| Curation pipeline | curator.py — SPLIT candidate detection + execution | Not started |
| Evaluation harness | tests/integration/ quality tests | Not started |
| Context evolution | Per-write context field update (A-MEM style) | Deferred (post 100 events) |
| Fine-tuned embeddings | Spike 6C — Voyage fine-tuning on real event history | Deferred |

---

## 6. Spike-to-Hypothesis Mapping

| Spike | Tests | Design question resolved |
|-------|-------|--------------------------|
| Spike 1 | H2 | Which boundary approach to use; whether episodes are well-scoped |
| Spike 2 | H10 | Locate-then-summarise for fuzzy docs; scattered content collection |
| Spike 3 | H1, H5 | NOTHING as predict-calibrate; integration decision vocabulary reliable |
| Spike 4A | H9 | Citation-style link traversal eliminated; body embedding beats context field |
| Spike 4C (closed, no spike) | H3 | Links are epistemic not semantic; vocabulary fixed at 3 types (contradicts, supersedes, provenance); tags dropped |
| Spike 4D | H9, ground truth | LLM ground truth established; top-20 cluster window; 83% of missed notes unreachable by structure |
| Spike 5 | H-new-A, H-new-B | Activation-weighted links confirmed (R@10=0.640); W_null=0.3 eliminated; decay λ untested; 36% systemic cross-domain miss identified |
| Spike 6 / workbench | H-new-C, H-new-D | BM25+MuGI+stem + step-back + HyDE-multi + activation; union coverage 93.7% at K=20; floor 36%→6.3%; held-out validated R@10=0.667, MRR=0.844 (+12.5pp / +6.9pp vs baseline) |
| Phase 5 | H6 | Whether per-write evolution improves retrieval via context field |
| Post-build | H4, H7 | Three-component scoring ablation; conservative prior calibration |
| Long-horizon | H8 | Bitter Lesson validation; requires months of real use |

---

## 7. What We Are Not Building

Explicitly out of scope for this implementation, per the Bitter Lesson constraint:

- **Multi-stage entity resolution** — we are not deduplicating named entities across notes with NLP pipelines. The LLM's integration decision handles conceptual deduplication.
- **Community detection algorithms** — no graph clustering to discover topics. Tags + links serve this purpose; the LLM reads the structure.
- **Confidence update formulas** — no Bayesian belief networks or formula-driven confidence revision. Confidence is revised by the integration LLM reading the note in context, not by a formula.
- **Automatic re-embedding pipelines** — embeddings are updated at consolidation time only. No incremental re-embedding triggered by every write.
- **Query planning** — no decomposition of complex queries into multi-hop retrieval plans. The LLM reasons across whatever cluster is provided.

These are not decisions against sophistication. They are decisions about where to invest complexity: in the representation (markdown, typed links, note hierarchy) rather than the retrieval machinery.

---

## 8. Reading List

For implementation reference. Papers cited in the design document:

| Paper | Relevance |
|-------|-----------|
| Nan et al. (2025) — Nemori | Boundary detection, FEP adaptation; primary prior work |
| Park et al. (2023) — Generative Agents | 3-component retrieval scoring, importance-sum trigger, reflection tree |
| Xu et al. (2025) — A-MEM | Closest existing Zettelkasten implementation; context field, evolution pass |
| He et al. (2024) — Def-DTS | Intent taxonomy boundary detection; Spike 1 Approach C |
| Zacks et al. (2007) — Event Segmentation | Cognitive science grounding for episode boundaries |
| McClelland et al. (1995) — CLS | Two-speed memory architecture grounding |
| Sutton (2019) — Bitter Lesson | Core design constraint; architecture philosophy |
| Hawkins (2021) — A Thousand Brains | Predict-from-model-update-on-error principle |
| Collins & Loftus (1975) — Spreading Activation | Activation-weighted link graph theoretical grounding |
| Anderson et al. (ACT-R) — Base-level activation | `A = ln(Σ t^(-d))` decay formula for co-activation strength |
| Howard & Kahana (2002) — TCM | Temporal context model: co-activation reinstates shared context |
| Watts & Strogatz (1998) — Small-world networks | Expected topology of co-activation graph; efficient traversal |

**Research passes — papers directly informing design decisions:**

| Paper | arXiv | Design decision informed |
|-------|-------|--------------------------|
| Mao et al. (2025) — CARPAS | 2502.09645 | Count-constrained topic prediction for fuzzy documents (§6.1) |
| Brake & Schaaf (2024) — personalization | 2408.03874 | Style = existing notes; target document is the cluster, not a Platonic ideal (§6.3) |
| Palm et al. (2025) — PDQI9 | 2505.17047 | LLM-as-judge evaluation rubric adapted from physician quality instrument (§10) |
| Cohen et al. (2025) — hallucination | 2506.00448 | Hallucination clusters where source content is sparse → stub type as mitigation (§10) |
| Zhong et al. (2021) — QMSum | 2104.05938 | Locate-then-summarise framing; Spike 2 Approach B |
| Krishna et al. (2020) — Cluster2Sent | 2005.01795 | Validates section-assign architecture; theme-based extraction from conversation |
| Gao et al. (2022) — HyDE | 2212.10496 | Hypothetical Document Embeddings for zero-shot dense retrieval |
| Zhang et al. (2024) — MuGI | 2401.06311 | Multi-text LLM query expansion + BM25; beats trained dense retrievers on BEIR out-of-domain; Spike 6A |
| Zheng, Mishra et al. (2024) — Step-back prompting | 2310.06117 | Abstract principle retrieval; ICLR 2024; +7–27% on abstraction tasks; Spike 6B |
| Trivedi et al. (2023) — IRCoT | 2212.10509 | Iterative retrieval with chain-of-thought; +21pp multi-hop recall; Spike 6D |
| Wang et al. (2023) — Query2doc | 2303.07678 | LLM pseudo-document query expansion for BM25 and dense retrieval; EMNLP 2023 |

---

## 9. Operational Monitoring

See [operational-monitoring.md](operational-monitoring.md) for the full metric wishlist.

The four key ongoing concerns are: **stub orphaning** (stubs that never receive an UPDATE become permanent orphans — monitor `stub_no_update_90d`); **decision distribution drift** (a rising NOTHING rate indicates retrieval degradation; a rising CREATE rate alongside note-pair similarity > 0.90 may signal duplicate accumulation, the condition that would warrant reconsidering MERGE); **retrieval health proxy** (track `mean_cluster_similarity` per-event; run full LOO workbench monthly); and **duplicate detection** (weekly cosine similarity scan for pairs > 0.90, and stub-to-stub pairs > 0.85).
