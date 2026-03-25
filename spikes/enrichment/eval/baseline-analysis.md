# Baseline Analysis — Run 0

*2026-03-24 — no skill, notes directory location only*

---

## What the baseline got right

**GT hit rate was surprisingly high: 94% (34/36).** The agent found the relevant notes in almost every case, including island notes with low activation weight. Notable:

- z023-007 (Phase Transitions) — found immediately by Q8 via `grep "phase transition"` — a perfectly specific keyword
- z023-005 (Transformer Expressivity) — found by Q11 in 9 reads
- z023-011 (Benchmark Suites) — found by Q6
- z023-004 (Workflow Optimization) — found by Q9
- z023-003 (Empirical SE Research) — found by Q3
- z011 (Provenance Governance) — found by Q12

**The title-extraction heuristic emerged naturally.** Multiple agents independently ran `head -5` or extracted `title:` fields from every file before reading, using titles as a cheap orientation step. This validates the design assumption.

**Keyword grep is effective when the query contains a specific named concept.** Q8's immediate hit on z023-007 via "phase transition" is the clearest example. The filesystem search advantage is real for precise conceptual keywords.

---

## What the baseline got wrong

### Problem 1: No stopping criterion — the primary failure mode

Agents read far more notes than needed. Average 16.1 notes read vs. average GT requirement of ~3.5 notes. **77% of reads were waste.**

The worst cases:
- Q2: read all 31 notes (GT required 3)
- Q5: read 30 notes (GT required 4)

The agents have no mechanism to decide "I have enough." They grep broadly, get many matches, and read everything that matched. Without a stopping rule, the natural behaviour is exhaustive.

### Problem 2: Broad grep returns too many files

Common patterns: `memory|Memory` → 28 files, `agent|Agent|multi-agent` → 31 files, `RAG|retrieval` → 23 files. These are not useful filters — they match almost everything in a store where all notes are about agents. Agents then either read all matches (Q2, Q5) or apply a secondary filter (Q8's specific term). Broad grep is worse than no grep for orientation; it creates a false sense of having narrowed.

### Problem 3: Synthesis hit the rate limit for 7/12 agents

Running 12 agents in parallel exhausted the session rate limit. The navigation completed successfully for most of them, but they couldn't produce answers. This is a test harness problem, not a navigation problem — run sequentially or in smaller batches in future iterations.

### Problem 4: Over-reading is correlated with query type

Questions with diffuse keywords (communication, coordination, tensions) produced the highest read counts (Q4: 17, Q5: 30). Questions with specific named concepts produced the lowest (Q8: 14 with an immediate grep hit, Q11: 9). The skill needs to guide towards specificity.

---

## Navigation strategy patterns observed

Four distinct strategies appeared, ordered from best to worst efficiency:

**Strategy A — Specific keyword → targeted reads (Q8)**
grep for named concept → immediate hit → read that note + 3-4 related → done
*Cost: ~84k chars. Precision: high.*

**Strategy B — Title extraction → selective reads (Q1, Q11, Q12)**
ls → extract all titles → read the 9-12 most relevant → done
*Cost: ~54-72k chars. Precision: moderate.*

**Strategy C — Multi-grep + title extraction → moderate reads (Q3, Q4, Q6, Q7, Q9, Q10)**
ls → 2-4 greps → extract titles → read 12-17 notes
*Cost: ~72-102k chars. Precision: low — reads many tangentially related notes.*

**Strategy D — Multi-grep → exhaustive reads (Q2, Q5)**
ls → multiple broad greps → read everything that matched → read everything
*Cost: ~180k+ chars. Precision: none — equivalent to full injection.*

The goal of the skill is to push agents from D/C toward A/B.

---

## Gaps the skill must address

Ordered by impact:

**Gap 1: No stopping criterion**
The skill must instruct: once you have notes covering all aspects of the question, stop. Don't read more because more is available. The signal to stop is when additional reads are not adding new conceptual territory.

**Gap 2: Specificity of keywords**
The skill must guide toward narrow, distinctive terms rather than broad category words. "Phase transition" > "communication". "Provenance" > "governance". "Transformer expressivity" > "formal". The question itself usually contains the specific term — use it.

**Gap 3: Iterative assess-then-continue**
Read 3-4 notes, assess coverage, decide whether to continue. Current behaviour reads in one batch. The skill should introduce a checkpoint: "After reading each batch of 3-4 notes, assess what's still missing before reading more."

**Gap 4: Title scan is already emerging — reinforce it**
Agents naturally extract titles before reading. The skill should make this explicit and canonical: always scan titles first, read selectively based on titles, not on grep match count.

---

## Navigation paradigm analysis

### The link graph is effectively empty

28/31 notes have `links: []`. Only 3 links exist — all `supersedes`. The design removed topical/semantic links on the grounds that retrieval signals handle proximity. This was correct for the retrieval system but means **explicit link-following navigation is not viable on the current store**.

### Two navigation strategies and what supports them

**Broadcast-then-narrow** (what glob and grep serve): cast a wide net, filter by specificity, read what matched. The natural default — every baseline agent started this way. Failure mode confirmed: broad terms return 20+ files and agents read everything.

**Anchor-and-radiate / berry-picking** (Bates, 1989): find one relevant note, read it, extract the distinctive coined terms it introduces, grep for those in the rest of the store, find adjacent notes not in the original query. Each note read reshapes what you look for next. The note body is a navigation artifact as well as a knowledge artifact. **Completely absent from the baseline** — no agent extracted terms from a note they'd read and used them as a follow-up search.

The zettelkasten structure suits berry-picking well: notes are dense with distinctive vocabulary ("Agent System Trilemma", "Kesten-Stigum boundary", "phase transition threshold") that doesn't appear in the user's question but appears in the notes themselves.

### Other navigable axes not used in baseline

- **Faceted browsing via frontmatter**: `grep "^created: '2026-03-23"` (temporal cluster), `grep "^stable: true"` (stable vs. provisional notes), `grep "^type:"` — entirely unused
- **Chronological traversal**: note IDs encode creation date; reading z20260322-* vs z20260323-* separates early-ingested from late-ingested notes
- **Source overlap**: notes sharing arxiv sources are topically related — readable from frontmatter

### Implications for skill design

The skill should describe two modes:

**Convergent mode** (synthesis, factual questions): targeted keyword from the question → title scan → selective reads → stop when covered. Broadcast-then-narrow with a stopping criterion.

**Divergent mode** (innovation, tension identification, adjacent possible): anchor note → extract distinctive coined terms from its body → search for those in the store → harvest the conceptual neighbourhood → repeat. This is the mode that enables serendipitous connection-making and is currently completely missing from the baseline. It is also the mode most relevant to the benchmark's innovation task types.

---

## What the skill should NOT do

- Specify which grep patterns to use (brittle, task-dependent)
- List specific note names to read (static, will break as the store evolves)
- Set a hard maximum number of reads (the right number varies by question complexity)
- Over-explain filesystem navigation to a capable model

---

## Implications for first skill draft

The skill body should be short — probably 15-25 lines. It needs to establish:

1. What the store is (synthesised notes, one concept per note, already compressed)
2. The navigation sequence: titles first, then selective reads
3. The stopping criterion: enough coverage, not exhaustive coverage
4. Keyword specificity guidance: use the distinctive terms in the question, not broad categories

The most important single instruction is the stopping criterion. Everything else the agents are already doing adequately without guidance.
