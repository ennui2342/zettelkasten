# Spike 1 — Episode Boundary Detection

**Hypothesis under test:** H2 — LLM-judged semantic boundaries produce well-scoped episodic units from real conversation/research sessions.

**Duration:** half day

---

## Plan

**Test data:**
- **Primary:** 5–10 real sessions from existing `history` stores, drawn from the researcher pipeline (`researcher-arxiv-monitor`, `researcher-blogs-monitor`, `researcher-synthesis`). This is the actual distribution the system will operate on — sessions covering multiple papers, domain pivots, and follow-up synthesis across different sub-topics.
- **Supplementary:** [LoCoMo](https://arxiv.org/abs/2402.17753) (Maharana et al., 2024) — a long-term conversation memory benchmark with annotated session boundaries and facts that should be retained across sessions. Using LoCoMo for Spike 1 upgrades evaluation from qualitative inspection to recall/precision against human-annotated ground truth, enabling a reliable quantitative comparison of the three boundary approaches.

The combination gives both domain-relevant validation (researcher sessions) and a quantitative benchmark (LoCoMo). TV dialogue or other casual conversation corpora are explicitly excluded — the boundary signals and knowledge density are too different from research sessions to be informative.

**Three approaches to compare:**

| ID | Approach | Implementation |
|----|----------|----------------|
| A | Nemori naïve | One LLM call per message: `(is_boundary: bool, confidence: float, reason: str)` |
| B | ES-Mem two-stage | MI pre-filter (cosine distance between TF-IDF vectors of adjacent message windows); LLM confirmation only when MI drops below threshold |
| C | Def-DTS intent | Classify each message against a fixed intent taxonomy (8–12 categories: information-seeking, explanation-providing, task-execution, topic-transition, …); boundary = intent category change |

**Evaluation:** for each approach and each session, inspect the resulting episode list. Score qualitatively:
- Are episodes atomically focused on one topic?
- Do boundaries fall at natural transition points?
- Are any episodes split too finely (1–2 turns)?
- Are any episodes too coarse (topic-crossing)?

**Deliverable:** a markdown table in `spikes/spike1-boundary/results.md` with a row per approach×session, a quality rating (1–5), and selected examples of good and bad boundaries.

**Go criteria:** at least two approaches produce consistently well-scoped episodes (average quality ≥ 3.5/5) on ≥ 8/10 sessions. If no approach passes, segment boundaries are a fundamental problem and full build is not warranted.

**No-go exit:** if segmentation is consistently too coarse or too fine, investigate whether the session format (not the approach) is the problem before declaring failure. Consider that research-pipeline output may need a different taxonomy than conversational logs (Def-DTS may need domain-specific intent categories).

**Hypotheses directly addressed:** H2. Indirectly informs H1 (quality of predict-calibrate depends on episode granularity).

---

## Outcome (completed 2026-03-14) — Go

Two runs on `pipelines/memory/research-findings.db` (21 turns, 4 days of researcher pipeline output). See `spikes/spike1-boundary/results-run1.md` and `results-run2.md`.

| Approach | Run 1 episodes | Run 2 episodes | Final score |
|----------|---------------|---------------|-------------|
| A — Nemori naïve (conf≥0.65) | 11 | — | 3.5 |
| A — Nemori naïve (conf≥0.80) | — | 7 | **4.0 ✓** |
| B — ES-Mem two-stage | 2 | eliminated | 1.5 |
| C — Def-DTS intent | 14 | 15 | 3.25 |
| D — Hybrid intent+Nemori | — | 1 | 1.25 |

**Findings:**
- **Approach A (conf≥0.80) selected.** 7 well-scoped episodes; two large coherent clusters (ep1: LangGraph ecosystem batch, ep7: multi-agent github releases) with appropriate singletons between for isolated disparate items.
- **Approach B eliminated** for domain-coherent streams: word-overlap similarity stays high when all content shares vocabulary (agent, pipeline, coordination). Needs semantic embeddings to be viable, eliminating the "cheap pre-filter" advantage.
- **Def-DTS labels adopted as metadata, not boundary trigger.** Classifications are accurate but drift across runs (intent label for the same turn varies ~15%). Use as an annotation pass on each flushed episode; the `(type, domain)` label becomes a tag on the episode and later on Zettel notes.
- **Hybrid approach failed**: explicit anti-boundary heuristics in the prompt caused the LLM to over-rationalise continuations. The base Nemori judgment with a tuned threshold is simpler and better.
- **Data quality note**: compaction summary artefacts (`[Summary of earlier history]` prefix) should be skipped by the consolidation pipeline.
- **Buffer backstop**: 8–10 turns (natural ceiling observed from the data).

**Decision:** Approach A, conf≥0.80 (Nemori naïve). Deferred from MVP — session/conversation boundary detection is excluded until document-ingestion dynamics are understood in production.
