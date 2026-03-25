# Ingestion Harness

**Layer 3 of the integration-quality strategy** — sequential trajectory
validation for the Form → Gather → Integrate pipeline.

---

## Purpose

The baseline tests (Layer 2) exercise individual papers against a fixed corpus
snapshot.  They cannot detect failures that only emerge from accumulation
dynamics — notes that grow problematically large through multiple sequential
updates, or duplicate notes that form because a SPLIT second-half later
receives further updates that mask the original failure.

This harness addresses that gap.  It ingests the 20 development papers one at
a time, in the original order, snapshotting the complete store state after each
paper.  The primary value is:

- **Accumulation observation** — watch note state evolve paper by paper;
  identify exactly when a note reaches criticality or when a duplicate first
  appears
- **Rewind and replay** — restore to any checkpoint, modify a prompt or
  algorithm, and replay forward to observe the changed trajectory
- **Regression detection** — after fixing paper N's behaviour, confirm that
  papers 1–(N−1) are unaffected by replaying from the start

The 20 papers were originally run in the 2026-03-18 benchmark run that
produced the known failure cases (bad SPLITs at papers 8, 10, 13).  Rerunning
them with the current codebase reveals whether those failures are resolved
and whether any new failures have been introduced.

---

## Directory layout

```
ingestion-harness/
  run.py            main harness script
  papers.json       ordered list of 20 arxiv IDs
  papers/           paper text files (2510.04851.txt etc.)
  metadata/         paper metadata JSONs (title, abstract, url, categories)
  store/
    notes/          live notes directory (gitignored — rebuilt by harness)
    index.db        live SQLite index    (gitignored — rebuilt by harness)
  snapshots/        per-paper snapshots  (gitignored — large, local only)
    progress.json   which papers have been completed
    00_initial/     notes/ + index.db before any papers
    01_2510.04851/  notes/ + index.db + result.json + report.md + paper.log
    02_2601.02695/
    ...
```

The `store/` directory is the live working store.  Commands operate on it
directly.  Snapshots are independent copies taken before and after each paper.

---

## The 20 development papers (in order)

| # | ArXiv ID | Title |
|---|----------|-------|
| 1 | 2510.04851 | LEGOMem: Modular Procedural Memory for Multi-agent LLM Systems |
| 2 | 2601.02695 | EvoRoute: Experience-Driven Self-Routing LLM Agent Systems |
| 3 | 2601.05504 | Memory Poisoning Attack and Defense on Memory Based LLM-Agents |
| 4 | 2511.08274 | Multi-Agent GraphRAG: A Text-to-Cypher Framework |
| 5 | 2511.14043 | AISAC: An Integrated Multi-agent System for Transparent RAG |
| 6 | 2509.01238 | Towards Open-World Retrieval-Augmented Generation on Knowledge Graphs |
| 7 | 2602.15055 | Beyond Context Sharing: A Unified Agent Communication Protocol |
| 8 | 2509.10769 | AgentArch: A Comprehensive Benchmark to Evaluate Agent Architectures |
| 9 | 2509.04876 | OSC: Cognitive Orchestration through Dynamic Knowledge Alignment |
| 10 | 2601.08156 | Project Synapse: A Hierarchical Multi-Agent Framework |
| 11 | 2512.01939 | An Empirical Study of Agent Developer Practices in AI Agent Frameworks |
| 12 | 2601.12307 | Rethinking the Value of Multi-Agent Workflow: A Strong Single Agent |
| 13 | 2510.13903 | Benefits and Limitations of Communication in Multi-Agent Reasoning |
| 14 | 2510.18032 | OPTAGENT: Optimizing Multi-Agent LLM Interactions Through Verbal Feedback |
| 15 | 2601.12560 | Agentic AI: Architectures, Taxonomies, and Challenges |
| 16 | 2601.17311 | Phase Transition for Budgeted Multi-Agent Synergy |
| 17 | 2511.10949 | Exposing Weak Links in Multi-Agent Systems under Adversarial Prompts |
| 18 | 2512.12791 | Beyond Task Completion: An Assessment Framework for Evaluating Agents |
| 19 | 2512.06196 | ARCANE: A Multi-Agent Framework for Interpretable Configuration |
| 20 | 2512.16970 | PAACE: A Plan-Aware Automated Agent Context Engineering Framework |

Papers 9, 10, and 13 are the known failure cases from the original benchmark
run — OSC, Project Synapse, and the multi-agent communication paper
respectively triggered the bad SPLIT cascades.

---

## CLI reference

All commands are run from the repository root:

```
uv run --env-file .env python model-tests/ingestion-harness/run.py <command>
```

### `--status`

Show current position and the next paper to run.

```
$ run.py --status
Position: 4/20
Next paper: 2511.14043  AISAC: An Integrated multi-agent System for...
```

### `--list`

Table of all 20 papers with completion status.

```
$ run.py --list
  #  ArXiv ID        Status     Title
---  --------------- ---------- --------------------------------------------------
  1  2510.04851      DONE       LEGOMem: Modular Procedural Memory for...
  2  2601.02695      DONE       EvoRoute: Experience-Driven Self-Routing...
  3  2601.05504      DONE       Memory Poisoning Attack and Defense...
  4  2511.08274      DONE       Multi-Agent GraphRAG: A Text-to-Cypher...
  5  2511.14043      NEXT       AISAC: An Integrated multi-agent System...
  6  2509.01238      -          Towards Open-World Retrieval-Augmented...
  ...
```

### `--context [N]`

Output a structured context block for paper N (defaults to the next paper).
This is designed to be run before `--next` so that you can discuss the
expected behaviour with Claude before committing to the ingestion.

The context block contains:
- Paper title, abstract, arxiv URL, and categories
- Current store state: every note with its ID, title, type, and body length
- Hot notes: any note with body > 4000 chars (likely SPLIT/EDIT candidates)
- Embedding similarity ranking: the paper abstract is embedded and
  dot-producted against all stored note embeddings to predict which notes
  will appear in the cluster (one embed API call, no LLM calls)
- Recent operation history: the operation summary of the last 5 papers

This command is intentionally cheap.  Use it in a Claude conversation:

```bash
$ run.py --context | cat
# paste the output into a Claude conversation and ask:
# "Given this context, what do you predict will happen when paper 5 is ingested?"
```

### `--next`

Ingest the next paper in the sequence.

1. Takes an initial snapshot (`00_initial`) if this is the first paper
2. Sets up a per-paper DEBUG log file in `snapshots/NN_<id>/paper.log`
3. Records store state before ingestion
4. Calls `store.ingest_text` with the paper text and source URL
5. Saves `result.json` (structured IntegrationResult data)
6. Generates `report.md` (per-paper analysis — see below)
7. Takes a post-paper snapshot
8. Updates `progress.json`

Console output is INFO level.  The `paper.log` file captures full DEBUG
output including the `integrate.cluster_cosine_sims` lines added for §4.7
analysis.

### `--paper N`

Run a specific paper by its 1-based position.  If N ≤ current position, asks
for confirmation before rewinding to the pre-paper-N state and re-running.
If N > current position + 1, errors (cannot jump ahead).

```bash
# Re-run paper 9 after changing the L2 prompt:
$ run.py --paper 9
Paper 9 has already been run. Rewind to pre-paper-9 state and re-run? [y/N] y
```

After confirmation the store is restored to snapshot `08_2509.10769` (i.e.
the state after paper 8), then paper 9 is ingested as normal.

### `--rewind N`

Restore the store to its state immediately before paper N, without ingesting
anything.  Asks for confirmation before overwriting the current store.

```bash
# Restore to pre-paper-9 state to inspect it before re-running:
$ run.py --rewind 9
Rewind to pre-paper-9 state (snapshot 08_2509.10769)? [y/N] y
Restored snapshot: 08_2509.10769 (8 notes)
```

After rewinding, `--status` will show paper 9 as next.  Progress is
trimmed to reflect the rewound position.

---

## Snapshot layout

Each per-paper snapshot directory contains:

| File | Contents |
|------|----------|
| `notes/` | Complete copy of the notes directory after ingesting this paper |
| `index.db` | Complete copy of the SQLite activation/embedding index |
| `result.json` | List of IntegrationResult dicts: operation, note_id, title, confidence, reasoning, target_ids, l1_target_ids |
| `report.md` | Human-readable per-paper analysis (see below) |
| `paper.log` | Full DEBUG log for this paper's ingestion only |

The `00_initial/` snapshot captures the empty store before any papers.
`--rewind 1` therefore restores to a clean slate.

---

## Per-paper report structure

`report.md` is generated automatically after each ingestion.  Sections:

1. **Header** — paper title, arxiv ID, run timestamp, elapsed time
2. **Abstract**
3. **Store State Before** — full note table (ID, title, type, body length);
   hot notes (body > 4000 chars) called out explicitly
4. **Integration Results** — per-draft trace: L1 targets and reasoning, L2
   targets and reasoning, final operation, note ID, body length before/after
   with delta, SPLIT second-half title and length
5. **Store Changes** — new notes and body-length deltas for modified notes
6. **Operation Summary** — `CREATE×N UPDATE×N SPLIT×N` etc.
7. **Duplicate Title Check** — flags any newly created note whose title
   matches an existing note (the primary signal of a bad SPLIT)
8. **Confidence Distribution** — min/mean/max; lists any operations below 0.7
9. **SPLIT Details** — for each SPLIT: source body length, first half, second
   half, combined ratio to original (> 120% suggests bloat)
10. **Cluster Cosine Similarities (§4.7)** — the `integrate.cluster_cosine_sims`
    lines from `paper.log`, showing which cluster notes were and weren't
    selected by L1 (T/F markers) alongside their cosine similarity to the draft

---

## Recommended workflow

### First run (clean replay)

```bash
# Check nothing is in progress
run.py --status

# Work through papers one at a time
run.py --context          # review predicted cluster and store state
# discuss with Claude, then:
run.py --next             # ingest paper 1
run.py --context          # review before paper 2
run.py --next             # ingest paper 2
# ...continue through all 20
```

### Fixing a known failure (e.g. paper 9)

```bash
# 1. Review what happened
open snapshots/09_2509.04876/report.md

# 2. Check the full debug log
grep "integrate\." snapshots/09_2509.04876/paper.log

# 3. Modify the relevant prompt or algorithm

# 4. Rewind and re-run
run.py --paper 9

# 5. Check the new report
open snapshots/09_2509.04876/report.md

# 6. If the fix is good, continue forward
run.py --next   # paper 10
run.py --next   # paper 11
# ...
```

### Path dependency

Fixing paper N creates a different store state for papers N+1 onwards.  A
note that would have been created by paper N with the old code may instead
be routed to UPDATE with the fixed code, changing which notes are available
as targets for paper N+1.

After any fix, replay papers N+1 through 20 before declaring the fix
complete.  Do not compare isolated per-paper results across trajectories —
only compare full-sequence outcomes.

### Checking for accumulation failures

The primary signal is the **Duplicate Title Check** section in each report.
If a new note shares a title with an existing note, a bad SPLIT has occurred.
This appears immediately in the report for the paper that produced the
duplicate, not deferred to the end.

Secondary signals:
- **SPLIT Details**: combined ratio consistently above 120% suggests the
  execute phase is adding content rather than partitioning existing content
- **Confidence distribution**: operations with confidence < 0.7 at L1 or L2
  warrant manual inspection of the notes produced
- **Hot notes in `--context`**: a note that appears as hot across many
  consecutive `--context` outputs is accumulating without being split

---

## §4.7 cosine similarity analysis

The `paper.log` for each INTEGRATE-routing paper contains lines of the form:

```
integrate.cluster_cosine_sims draft='<title>' <id>=T:0.847 <id>=F:0.634 ...
```

`T` = note selected by L1 as a target; `F` = in cluster but not selected.
Values are cosine similarities between the draft body embedding and the note
body embedding.

This data feeds the evaluation of §4.7 (embedding-space pre-filtering for
CREATE/UPDATE).  The question: do T notes consistently sit at noticeably higher
similarities than F notes?  If there is a clean gap, a cosine threshold could
pre-filter the cluster before L1/L2 classification, reducing noise.

The `report.md` §4.7 section collects all these lines for the paper.  To
analyse across a full run:

```bash
grep "cluster_cosine_sims" snapshots/*/paper.log | less
```

---

## What this harness does not do

- **Quality judgement** — the reports are quantitative and structural.
  Assessing whether a note's content is good requires reading it.  Use the
  report to identify candidates for manual review, then read the notes
  directly.

- **Expected-outcome assertions** — there are no hard assertions against
  expected operations.  The harness records what happened; evaluation is a
  conversation.  Before running a paper, use `--context` to form predictions,
  then compare those predictions to `report.md` after the run.

- **Automated baseline promotion** — when a full replay produces a
  qualitatively better store, the baseline in `model-tests/baseline/` should
  be updated.  This is a deliberate manual step: promotion invalidates
  existing baseline test intuitions and requires reviewing the new store
  against the INSPECTION.md criteria first.

---

## Tests

The helper functions in `run.py` are tested in `tests/test_ingestion_harness.py`
and run as part of the main test suite:

```bash
uv run --env-file .env pytest tests/test_ingestion_harness.py
```

Tests cover: position tracking, snapshot naming, snapshot round-trip,
duplicate title detection, operation summary, and low-confidence filtering.
