# Inspection Step 1 — Note Quality

**Run:** `ingest_20260317_022556` (20 papers, dev subset)
**Date:** 2026-03-18
**Store:** `zettel_20260317_022556/` (34 notes)
**Verdict:** CONDITIONAL PASS — majority of notes are good; two structural failure patterns identified

**Note:** This corpus was ingested before recent MERGE/SPLIT and activation fixes. A fresh ingest is recommended before task authoring. This report is a quality baseline and a dry run of the inspection methodology.

---

## Sample

Seven notes read in full spanning early creates, mid-run, and late-paper notes:

| Note | Created | Type |
|------|---------|------|
| z001 — Multi-Agent LLM Systems: Architecture, Memory, and Collaborative Reasoning | paper 1 | stub* |
| z003 — Model Routing as Memory-Conditioned Policy | paper 1–2 | SYNTHESISE |
| z007 — Digital Construction and BIM: AI-Driven Access to Structured Engineering Data | paper 3 | CREATE |
| z009 — AnchorRAG: Multi-Agent Collaboration for Open-World KG Question Answering | paper 4 | CREATE |
| z018 — LLM-as-a-Judge: Automated Evaluation of Generative Agent Systems | paper 7 | CREATE |
| z025 — Prompt Engineering for LLM Reasoning: From Chain-of-Thought to Structured Thought Topologies | paper 11 | CREATE |
| z028 — Environments and Applications of LLM-Based Agents | paper 15 | CREATE |
| z031 — Modeling Shared Failures and Communication Losses in Agent Ensembles | paper 16 | CREATE |

*z001 has `type: stub` in frontmatter despite being the largest hub note. See anomaly note below.

---

## Title Scoping

**Result: mostly good, two failures.**

Notes that pass — titles name transferable concepts, not papers or systems:

- *Prompt Engineering for LLM Reasoning: From Chain-of-Thought to Structured Thought Topologies* — names a concept landscape, stable
- *Modeling Shared Failures and Communication Losses in Agent Ensembles* — names a mechanism pair, well-scoped
- *LLM-as-a-Judge: Automated Evaluation of Generative Agent Systems* — names a paradigm, acceptable
- *Model Routing as Memory-Conditioned Policy* — names the relationship, correct for a SYNTHESISE note

**Failures:**

**z009 — `AnchorRAG: Multi-Agent Collaboration for...`**
Names a specific system. This is a paper proxy. The transferable concept lives elsewhere — something like *structure-aware entity disambiguation as a hedge against surface-form unreliability in KG retrieval* — but the note doesn't name it. Benchmark questions cannot anchor to this note without testing paper recall rather than synthesis.

**z028 — `Environments and Applications of LLM-Based Agents`**
A survey section heading. Covers digital agents, embodied agents, and specialised domains in a single note. Too broad to be a stable retrieval target — it will be retrieved for many questions where it adds only marginal signal, pulling answers toward breadth rather than synthesis.

---

## Content vs. Extraction

**Result: roughly half genuine synthesis, half extraction-heavy.**

**Strong synthesis** — the note makes arguments not present in any single source:

- **z003** (Model Routing as Memory-Conditioned Policy): The opening paragraph identifies that routing and procedural memory literature "address the same problem from opposite directions" and that the connection has been missed by both fields. That framing is not in any paper — it is constructed by reading across sources. The "Open Questions" section extends it further. This is the target quality level.

- **z018** (LLM-as-Judge): Works through biases systematically (position, verbosity, self-preference), names cross-family evaluation design as a structural intervention — not just a technique — and arrives at the meta-evaluation circularity problem as a conceptual insight. The structure is argumentative, not enumerative.

- **z025** (Prompt Engineering): The final section — "Implications for Multi-Agent and Routing Architectures" — frames CoT expressivity limits as *demand signals* for model routing. That argument is assembled across the note's trajectory and connects forward into the routing literature. Not extractable from any single source.

**Moderate** — single-source but well-organised, with some synthesis value:

- **z007** (Digital Construction / BIM): Appropriate scoping, correctly situates one paper's evaluation in a broader context of digital twins and IFC schemas, identifies open challenges. But coverage is almost entirely one paper. Synthesis lies in the framing sections, which are thin.

- **z001** (Multi-Agent LLM Systems): Long and well-structured, draws on many sources. But reads more like a detailed survey chapter than a note with a thesis. The key finding — "collaborative reasoning is most effective for step-by-step logical deduction rather than factual recall or procedural planning" — is buried at the end without structural prominence. No clear thesis statement.

**Extraction-heavy** — primarily rendering source material:

- **z009** (AnchorRAG): Three sections describing three agents with their mechanisms, followed by empirical results (numbers, ablation findings, hyperparameter analysis). This is an annotated abstract. The transferable insights — structural disambiguation is more robust than surface-form matching; parallel multi-anchor exploration hedges against grounding failures — are present but submerged.

- **z028** (Environments and Applications): Organised catalogue of systems by domain. The closing observation about the benchmark-to-deployment gap is good, but it arrives after a tour through named systems (Mind2Web, WebVoyager, OSWorld, Voyager, SayCan, Agent-Driver) without deeply synthesising any of them. The body is organised extraction.

- **z031** (Shared Failures and Communication Losses): Technically detailed rendering of a formal model (ρ-shared model, λ gain expressions, binary symmetric channel). Well-organised, but primarily one source. The "Diagnostic Use" section lifts it somewhat — it frames ρ and η as interventions to pull, which is a practical synthesis. But the bulk is faithful explication.

---

## Granularity Consistency

**Result: significant spread, larger than acceptable.**

| Note | Scope |
|------|-------|
| z031 — Shared Failures / Communication Losses | Single formal model, one paper's framework |
| z009 — AnchorRAG | Single system, one paper |
| z003 — Model Routing as Memory-Conditioned Policy | Bridging concept across two subfields |
| z018 — LLM-as-a-Judge | Evaluation paradigm with known variants and biases |
| z025 — Prompt Engineering / CoT | Technique family with implications |
| z007 — Digital Construction / BIM | Domain + one paper's evaluation |
| z001 — Multi-Agent LLM Systems | All of multi-agent architecture and memory |
| z028 — Environments and Applications | All LLM agent deployment environments |

The sweet-spot notes (z003, z018, z025) are at a medium level: broad enough to be retrieved across papers, specific enough to give focused answers. The two extremes — single-paper formal model (z031) vs. all-of-a-domain (z028) — are outside that range by roughly 3×.

The spread likely reflects corpus composition: at least one paper appears to be a broad survey (z028's source), and at least one is a tightly-scoped theoretical paper (z031's source). Better MERGE and SPLIT should help compress the top end and expand the bottom, but the survey-paper problem may persist regardless.

---

## Anomaly: z001 `type: stub`

The primary hub note — *Multi-Agent LLM Systems: Architecture, Memory, and Collaborative Reasoning* — has `type: stub` in its frontmatter, despite being the largest and most-updated note in the store. All other permanent notes have `type: permanent`.

Possible explanations:
1. The pipeline changed the note's type during a SPLIT or EDIT operation and the type field was set incorrectly
2. A STUB operation targeted this note rather than creating a new note
3. The type field is being used for something other than permanent/stub classification

This should be investigated before relying on z001 as a benchmark anchor. A note typed as stub implies it's a placeholder pending more evidence — which is inconsistent with its actual size and hub status.

---

## Overall Verdict

**CONDITIONAL PASS.**

The store has a usable core of synthesis-quality notes that would anchor benchmark questions well. Roughly half the sampled notes (z003, z018, z025, z007) meet the quality bar. The failure patterns are:

1. **System-named notes** (z009 pattern): paper proxies that test recall, not synthesis. Check full title list for other system-named notes.
2. **Survey-level notes** (z028 pattern): too broad for reliable retrieval targeting. Check for others.
3. **Granularity spread**: ~3× range is too wide. MERGE/SPLIT improvements should address this.
4. **z001 type anomaly**: investigate before using as hub anchor.

Given that the pipeline has since changed (MERGE/SPLIT improvements, activation fix), these issues may resolve on re-ingest. The step 1 analysis here serves as a baseline and a dry run of the methodology. **A fresh ingest is required before task authoring proceeds.**
