# Ingestion Harness — Analysis Guide

This guide describes how to get the most analytical value out of the per-paper conversation workflow. The README covers the mechanics; this document covers the thinking.

---

## Why this work is structured this way

The ingestion harness is not a validation exercise — it is an exploration. The pipeline design is mostly settled, but the *dynamics* of the store as it grows are not understood yet, and cannot be understood without running it. This is complex-domain work in the Cynefin sense: the patterns emerge from doing, not from upfront analysis. The harness is the probe.

The per-paper conversation is how that exploration is made legible. It builds a running mental model of the store's behaviour — which kinds of notes accumulate healthily, which fragment, how retrieval changes as the corpus grows, what the activation graph actually looks like under pressure. That model is the primary output. The notes themselves are secondary.

**What is deliberately deferred.** How an agent will use this store in practice is an open question. That is intentional. Designing the agent retrieval interface before understanding the store's dynamics would be premature — it would foreclose discoveries that the store's structure might make available. The right time to design the agent interface is after the store has revealed its shape, not before.

**The abstraction register problem.** The store generates dense, formally framed notes in the register of academic CS research. That framing captures the research community's conceptual vocabulary but may not be the vocabulary most useful to the person building and using the system. The real test of any SYNTHESISE note is not whether its title is impressively abstract but whether, when retrieved in the context of a future design problem, its content gives actual traction. A note that reads like someone else's PhD thesis has failed its retrieval purpose regardless of how sophisticated the synthesis is. Keep this in mind when evaluating note quality — legibility and retrievability matter as much as conceptual depth.

**What "interesting" looks like.** The innovation benchmark (see `docs/design/benchmark-innovation.md`) is testing whether the store enables bisociative connections — unexpected juxtapositions across domain boundaries that neither the papers nor the reader would have produced alone. These connections tend to emerge at the edges: when a late-ingested paper from a different angle retrieves an early note and the combination produces something neither anticipated. The 20 development papers are all from the same domain, so domain-boundary bisociation is a later-phase problem. For now, the interesting signal is whether cross-paper synthesis within the domain is happening at the right level of abstraction — specific enough to be useful, general enough to transfer.

---

## What the conversation is for

The `--context` / `--next` workflow creates two natural moments for analysis:

1. **Before `--next`**: form predictions about what will happen
2. **After `--next`**: compare predictions to `report.md` and evaluate note quality

Both matter. Prediction-making forces explicit reasoning about the store's current state and the paper's content. The comparison reveals whether the pipeline's decisions align with those expectations — and where they don't, that divergence is the thing to investigate.

The conversation is not a quality-control pass. It is a way of building a mental model of the store as it grows.

---

## Phase 1 — Pre-ingestion (from `--context` output)

### Questions to form predictions

**About the paper:**
- What is this paper's core contribution — a new system, a taxonomy, empirical results, a formalisation?
- Is this primarily about a concept already represented in the store, or does it introduce something orthogonal?
- Does it have a strong thesis that could become a synthesised note, or is it mainly incremental evidence for an existing concept?

**About the predicted cluster:**
- Which notes are predicted to appear in the cluster by embedding similarity?
- Do those notes look like the right retrieval targets, given what the paper is about?
- Are there notes that *should* be in the cluster but appear to be missing from the similarity ranking?

**About hot notes:**
- Are any notes already hot (>4000 chars) that are likely to be L1 targets for this paper?
- If so, expect a step 1.5 EDIT or SPLIT decision. Which direction is more likely, and why?

**Predict the operations:**
Explicitly state what you expect: `CREATE×N UPDATE×N SYNTHESISE×N`. Then record *why*. A wrong prediction is more informative than a right one.

---

## Phase 2 — Post-ingestion (from `report.md`)

### First pass: structural checks

Before reading note content, check the structural signals in the report:

- **Duplicate Title Check**: if a new note has the same title as an existing one, a bad SPLIT has occurred — investigate immediately
- **SPLIT Details**: combined ratio > 120% suggests the execute prompt added content rather than partitioning; read both halves
- **Confidence distribution**: any operation below 0.7 warrants reading the note produced — low confidence is a signal the model was uncertain about the right action, not just execution quality
- **Operation count**: does the number of new notes make sense for the paper's content? A paper introducing 5 independent concepts that produces 1 CREATE is probably under-integrating. One that produces 6 CREATEs is probably over-fragmenting.

### Second pass: compare predictions to actuals

For each divergence from your prediction, determine which of these explains it:

1. **Good divergence** — the model made the right call and your prediction was wrong; update your model
2. **Failure divergence** — the model made a wrong call; investigate the reasoning in the report and the note content
3. **Ambiguous divergence** — both the prediction and the model's decision are defensible; note the ambiguity rather than forcing a verdict

The L1/L2 reasoning in the report is the primary diagnostic. If the reasoning sounds plausible but the operation feels wrong, read the target note before deciding.

### Third pass: note content

For each new or modified note:

**Title quality:**
- Does it name a transferable concept, or is it a paper title / system name / survey heading?
- Could this title serve as a retrieval target for a future paper about a related concept?

**Content quality:**
- Does the note make an argument, or does it read like a well-structured abstract?
- If it's a SYNTHESISE note: does it identify a specific *relationship* between the source notes, or just assert they are related?
- If it's an UPDATE: does the updated note read as a unified treatment, or is the new content clearly appended?
- Is there anything in the note that goes beyond the paper's stated claims? Is that extension justified or is it genetic memory leaking in?

**Granularity:**
- Is this note at roughly the same level of abstraction as the other notes in the store?
- Is it more narrow (single-paper result) or more broad (entire domain) than its peers?

---

## Ongoing accumulation monitoring

These signals compound across papers and are the primary value of the sequential harness:

### Hot note trajectory
Track which notes are hot (`--context` shows notes >4000 chars before each paper). A note that stays hot across multiple consecutive `--context` outputs without being split is accumulating without resolution. Ask:
- Is this note getting large because it's genuinely the most foundational concept in the corpus?
- Or is it large because it was the broadest early note and kept getting routed to by default?

### Co-activation confound (§5.4)
Notes created early in an empty corpus are forced to be broad and foundational (the first paper has nothing to SYNTHESISE with). They then accumulate co-activation weight that makes them dominant retrieval attractors for all subsequent papers, regardless of whether they are the most semantically relevant note.

Watch for this pattern: after ~5 papers, the same 1–2 notes appearing in every cluster. This is the structural confound — not necessarily wrong, but worth tracking. The activation graph in `index.db` makes this auditable:

```sql
SELECT note_id, SUM(weight) as total_outbound
FROM activation
GROUP BY note_id
ORDER BY total_outbound DESC;
```

If the top 2 notes have 3-4× the outbound weight of notes created at papers 8-12, the confound is active.

### Topic attractor pattern
A topic attractor is a note whose scope is defined at exactly the granularity where every paper in a domain has *something* to add. It is distinct from a hub note: a hub note is broad because it was created first; a topic attractor is broad because its topic is genuinely cross-cutting. The difference matters because the fix is different.

Signals:
- The note has been SPLIT at least once and the original note grew back to threshold within a few papers
- The note's See Also section contains links to notes that were split *from* it
- Multiple papers at varying confidence (0.78–0.92) consistently route to this note
- The note's title names a process or methodology (e.g. "Benchmarks and Evaluation") rather than a concept or principle

A topic attractor will continue accumulating regardless of how many times it is split. Each SPLIT creates a child note with a more specific scope, but the parent retains the core methodology framing that every subsequent paper will update. This is not a pipeline failure — it reflects genuine structure in the domain. But it does mean EDIT compression cycles on the parent will be more frequent and each cycle carries higher degradation risk.

**What to watch:** If a note has been both SPLIT and EDIT-compressed in the same 10-paper window, it is a topic attractor under pressure. Read the parent note's body after each EDIT to confirm the core framing is surviving compression.

### Stranded specialist pattern
A stranded specialist is a note created from a topic-specific paper that falls outside the corpus's subsequent trajectory. It accumulates no activation weight because no later paper retrieves it as a target, but its embedding is accurate and it will surface correctly if a relevant paper arrives.

Signals:
- Never updated since creation (body size unchanged across all subsequent `--context` outputs)
- Total activation weight close to zero despite large body size
- Created from a paper covering standards, protocols, identity, governance, or other infrastructure topics in a corpus otherwise focused on architecture/algorithms

These notes are not broken. The activation signal correctly reports that they have not been habitual co-retrieval partners for other notes. The embedding will retrieve them when the topic recurs.

**No active intervention is available.** The `context:` field was removed from the data model (body embedding alone outperformed body + context). Retrieval for a stranded specialist depends entirely on body embedding and BM25. If the note's body uses specialist vocabulary that future papers don't share (e.g. a protocols note that uses "DIDs/VCs/PoI" when future papers say "federated agent identity"), the note may be missed. There is no lever to pull except waiting for the corpus to reach the topic area. Document the note as a stranded specialist and note its vocabulary profile as a future retrieval risk.

### Synthesis quality trajectory
The first SYNTHESISE note in a corpus by definition bridges two papers and has no existing synthesis to build on. Bridging quality typically improves as the corpus accumulates more notes with clear conceptual identities. Track whether SYNTHESISE notes become more specific (naming a precise relationship) or more generic (citing an increasing number of targets) as the corpus grows.

---

## Evaluating SYNTHESISE notes specifically

This deserves special attention because SYNTHESISE is the operation most susceptible to the genetic memory problem: the model produces a bridge that draws heavily on its training knowledge rather than on what is specifically in the two source notes.

Ask for each SYNTHESISE note:
1. **Is this emergent or genetic?** Could this note have been written without having read either paper — just from knowing the general domain? If yes, the synthesis is primarily genetic memory, not emergent from the corpus.
2. **Is genetic memory here valuable or contaminating?** A SYNTHESISE note that imports an established framework from training knowledge (e.g. Koestler's bisociation, or a known taxonomy) can be genuinely useful — it provides a conceptual scaffold that neither paper offers. This is comparable to an experienced researcher connecting a new finding to their broader knowledge base. The question is whether it *adds* inferential reach or *replaces* content from the actual papers.
3. **Does the bridge have traction?** Will a future paper about a related concept retrieve this note and find it useful — or will the retrieved note be noise?

**Cross-note pattern to watch for:** If multiple SYNTHESISE notes independently derive variants of the same structural insight (e.g. "this constraint reshapes the feasible region rather than adding a dimension"), the corpus is accumulating a coherent perspective — not just storing facts. This is a positive signal that SYNTHESISE is operating at the right level of abstraction. Conversely, if SYNTHESISE notes are citing increasing numbers of targets without naming a specific relationship, quality is degrading toward survey mode.

---

## Evaluating the activation graph

After every few papers, it is worth checking whether the activation graph reflects the retrieval decisions you would expect. The activation graph should encode *which notes habitually appear together in retrieval*, not which notes are semantically most similar (that's the embedding). The two should be related but not identical.

Check:
- Are the highest-weight edges between notes that are genuinely conceptually linked?
- Are there missing edges that should exist (two notes that are closely related but never co-retrieved)?
- Are there high-weight edges that look like co-activation inflation — notes that appear together because they're both broad and early, not because they're truly related?

The decay mechanism (currently absent as of paper 2) will matter more as the corpus grows. Once implemented, notes that stop being retrieved should have their edges decay — but the decay rate needs to be checked against the temporal distribution of retrievals to avoid premature decay of genuinely foundational notes.

---

## Watching for merge candidates

The system has no MERGE operation (deprecated — see `docs/design/architecture-decisions.md §7a`). When two notes accumulate overlapping content, the pipeline has no way to consolidate them. Identifying merge candidates during the harness run builds the case for adding MERGE back as a curation operation.

The signals that indicate two notes should be merged:

1. **NOTHING citing both**: A draft routes as NOTHING with reasoning like "already covered by z-xxx and z-yyy combined" — the pipeline is implicitly treating two notes as one conceptual unit. This is the clearest signal.

2. **L2 forced arbitration**: L2 must choose between two equally valid UPDATE targets and the reasoning is essentially a coin flip — the draft belongs equally in both. If this happens for the same pair of notes across multiple papers, they are functionally one note.

3. **Consistent L1 co-appearance**: The same pair of notes appears together in L1 targets across many papers, suggesting the retrieval system treats them as inseparable. Check the activation graph — a high-weight edge between two notes combined with similar embedding positions is a structural merge signal.

4. **Title overlap**: Two notes whose titles name the same concept from slightly different angles (e.g. "Multi-Agent Architectures for Workflow Automation" and "AI Agent Architectures and Multi-Agent Systems") are candidates if their content has converged through separate UPDATE paths.

When any of these signals appear consistently, document the pair. The case for MERGE as a scheduled curation operation strengthens when: one note has become a conceptual subset of another through accumulation, or the store contains two notes that any retrieval query for their topic would return together.

---

## Monitoring EDIT compression quality

EDIT compresses large notes by distilling accumulated content. It can either improve a note (forcing structural clarity) or degrade it (losing explanatory framing in favour of encyclopaedic coverage). These are not always distinguishable from body size alone — read the note.

**Signs of compression-as-improvement:**
- The note has been restructured into a more principled taxonomy or argument hierarchy
- Verbose implementation specifics have been dropped while the structural claims are sharper
- The note feels more transferable — less tied to specific papers or tools

**Signs of compression-as-degradation (the 018 pattern):**
- The opening section has been flattened from an explanatory narrative ("why this shift happened") to a definitional framing ("here is the POMDP loop")
- New content from later papers has been appended or merged into sections that now cover a wider scope than the note's original title implies
- The note contains content that would function as noise for the most likely retrieval queries (e.g. robotics content in a note titled "Foundations of Autonomous Agents: Reasoning and Planning")

**Proactive SPLIT signal:** A note that shows the 018 pattern — explanatory framing compressed away, scope expanded by accumulation — may need a proactive SPLIT *before* the 8,000-char threshold triggers another EDIT. Waiting for the threshold will produce further compression of an already over-broad note rather than a clean structural split. The signal to watch: after an EDIT, re-read the note title and check whether the body is still answering the question the title asks. If not, the split point is wherever the note stopped answering that question.

**EDIT cycle count:** Track how many times each note has been EDIT-compressed. A note compressed once is likely improved. A note compressed twice has exhausted most of the easy gains and is at risk on the next cycle. A note compressed three or more times is probably losing structural quality with each pass. The `updated` timestamp in frontmatter advances on every operation; use the snapshot history or `git log` on the note file to count EDIT operations.

Notes with 2+ EDITs warrant reading after each subsequent EDIT to verify the core argument survives. If the note passes through another EDIT and the opening paragraph has changed from an explanatory claim to a definition or a list, the argument is being compressed away.

**The NOTHING/EDIT interaction:** Every borderline UPDATE on an already-compressed note carries a hidden cost. If the marginal content causes the note to grow back past the threshold, EDIT will fire again — compressing content that predated the marginal addition. The first EDIT on a note typically improves it (removes verbose scaffolding, sharpens structure). The second and third EDIT on an already-optimised note degrades it (compresses structural insights, flattens principled argument into coverage). Watch for notes that have been EDIT-compressed once and are accumulating UPDATEs at conf ≤ 0.78 — these are the candidates where NOTHING would have been the better call in retrospect.

---

## Monitoring corpus saturation

The healthy end state for a mature corpus is not one where most operations are UPDATE — it is one where NOTHING is increasingly common, SYNTHESISE still fires for genuinely novel cross-domain connections, and UPDATE is reserved for papers that add specific new evidence to an established note. The UPDATE/EDIT cycle that dominates a young corpus should gradually yield to a NOTHING/SYNTHESISE balance as topic areas saturate.

### The saturation trajectory

A young corpus (< 30 papers in a specific domain) will produce:
- High CREATE rate — many new topics introduced
- Moderate UPDATE rate — existing notes deepened
- Low NOTHING rate — most content is still genuinely novel
- EDIT/SPLIT firing occasionally as hub notes grow

A maturing corpus (30–100 papers) should show:
- CREATE rate declining — most major topics are represented
- UPDATE rate declining — hub notes are comprehensive, marginal additions fewer
- NOTHING rate rising — overview papers and incremental papers hit saturated notes
- EDIT/SPLIT still firing — topic attractors accumulate regardless

A saturated corpus (100+ papers in a narrow domain) should show:
- NOTHING dominant for most papers
- UPDATE firing only for empirically significant new results or paradigm shifts
- SYNTHESISE firing at domain boundaries or when late-arriving papers bridge established threads in new ways
- EDIT rare — notes are not growing much because UPDATE/NOTHING balance has shifted

If the corpus reaches 50 papers and NOTHING rate is still below 5%, one of two things is true: (1) the paper selection continues to introduce genuinely new content, or (2) the UPDATE threshold is too permissive and marginal additions are being accepted when NOTHING would be correct.

### Measuring saturation

**NOTHING rate per 10-paper window.** Calculate NOTHING / total operations for each decade of papers. An increasing NOTHING rate is the saturation signal. A flat or declining NOTHING rate after paper 30 indicates the UPDATE threshold needs review.

**New note rate per 10-paper window.** Count CREATE operations per decade. In a saturating corpus, new notes should become rarer (most topics already exist as notes). If CREATE is still firing at the same rate at paper 50 as at paper 10, the corpus is not saturating — it is still exploring new topic territory.

**Hub note stability.** In a saturated corpus, hub notes should stop growing between EDIT cycles (because NOTHING is absorbing content that would otherwise update them). A hub note whose body grows by more than 1,000 chars between consecutive `--context` reads is still in accumulation mode, not saturation.

```sql
-- Track operations over time (if operation type is logged)
-- Alternatively: count report.md entries per snapshot window
```

### The compression degradation risk at scale

The concern with the UPDATE/EDIT cycle dominating a long corpus is compounding degradation: each EDIT pass on a hub note risks losing explanatory structure. If the cycle runs 5–6 times on the same note over 100 papers, the note may end as a dense reference list rather than an argument — comprehensive but not retrievable in the conceptual sense.

The saturation transition is the natural defence against this: as NOTHING rises, hub notes stop growing, EDIT stops firing, and the quality of the compressed-but-stable notes becomes the permanent quality. The question is whether the corpus reaches saturation before the notes degrade past usefulness.

**Trigger for concern:** a hub note with 3+ EDIT cycles, declining NOTHING rate at paper 40+, and confidence on UPDATE operations averaging ≤ 0.80. This combination suggests the UPDATE threshold is not self-correcting and may need explicit adjustment (raising the minimum delta required for UPDATE to fire on notes that have been compressed 2+ times).

---

## Monitoring L1 context window size

L1 receives the full body of all 20 cluster notes plus the draft with no truncation
(`_format_cluster` in `integrate.py`). This is intentional — L1's routing quality
has been standout and the full context appears to be load-bearing. **Do not truncate
preemptively.**

What to watch for as the corpus grows:

- **Total L1 input size**: `--context` shows note body sizes. Sum the top-20 retrieval
  candidates' body lengths and add the draft length. Above ~150k chars, token limits
  become a real risk depending on provider. Above ~300k chars, even Sonnet/Opus are
  at their limits.
- **L1 reasoning quality**: If L1 starts producing vague, hedged, or structurally
  thin reasoning (compared to the confident, specific reasoning in papers 1–15),
  context saturation may be the cause. Compare reasoning verbosity and specificity
  paper-over-paper.
- **L1 target count inflation**: If L1 starts nominating 10+ notes as targets where
  it previously nominated 3–7, this may indicate loss of discrimination from context
  overload rather than genuine cluster relevance.

**Trigger for action**: any two of the above signals appearing in the same paper.
At that point, a per-note body truncation in `_format_cluster` (e.g. 1,500–2,000
chars per note) is the minimum intervention. See `analysis/activation_k20_slots.md`
for the broader context on cluster composition.

---

## Things that require immediate investigation

Stop and investigate before continuing to the next paper if:

- A duplicate title appears in the Duplicate Title Check
- A SPLIT produces a second-half title that matches an existing note
- A SYNTHESISE note's reasoning cites notes that don't appear to be semantically related to the paper
- A hot note (>6000 chars after 10+ papers) is still being targeted for UPDATE rather than SPLIT
- Confidence is below 0.5 on a CREATE or SYNTHESISE (this usually means the model found the draft ambiguous relative to the existing notes, which warrants reading the draft and the cluster to verify the decision made sense)

---

## Long-horizon checks (papers 14–19)

The benchmark design requires that late-ingested notes are retrievable despite low co-activation weight. From around paper 14 onwards, start tracking:

- Are new notes specific and self-contained enough to serve as retrieval targets?
- Do they depend on post-cutoff content specifically (temporal accuracy anchor), or could they have been written from pre-cutoff training knowledge?
- Are they being routed to CREATE, or are they being merged into early hub notes via UPDATE (which would make them invisible as distinct retrieval targets)?

A store where papers 14–19 all route to UPDATE against notes created in papers 1–5 is a failure mode for the benchmark — it means late-paper concepts have no discrete representation.

---

## Monitoring see-also link integrity

**Background:** The 20-paper run ended with 1 hallucinated link and 2 bare-title links
that resolve correctly but aren't ID-anchored. Known broken link as of paper 20:
`[[Retrieval-Augmented Generation, GraphRAG, and Retrieval Corpus Governance]]` in
z20260322-012 — a title that never existed.

These are left in place deliberately as a controlled observation. The hypothesis is
that future EDITs, UPDATEs, and SPLITs will either naturally repair stale links (the
execute step rewrites see-also sections) or leave them harmless. The concern is that
hallucinated link titles bleed into L1/L2 context as false claims about the corpus
structure.

**Check periodically** (every ~5 papers):

```bash
# Count bare and broken links
cd model-tests/ingestion-harness
python3 -c "
import os, re
notes_dir = 'store/notes'
note_titles = {}
for f in os.listdir(notes_dir):
    if f.endswith('.md'):
        text = open(os.path.join(notes_dir, f)).read()
        title = next((l[2:] for l in text.split('\n') if l.startswith('# ')), None)
        if title: note_titles[title] = f.replace('.md','')
for f in os.listdir(notes_dir):
    if not f.endswith('.md'): continue
    text = open(os.path.join(notes_dir, f)).read()
    for m in re.finditer(r'\[\[([^\]|]+)\]\]', text):
        title = m.group(1)
        status = 'OK' if title in note_titles else 'BROKEN'
        if status == 'BROKEN':
            print('%s BROKEN: [[%s]]' % (f.replace('.md',''), title[:60]))
"
```

**What to watch for:**

- **Broken link count growing** — suggests the execute step is hallucinating titles
  more frequently as the corpus grows. Trigger: >3 broken links after the next 10
  papers. Action: implement cluster-title provision at execute time (see
  `docs/design/architecture-decisions.md §11`).

- **Broken links being repaired** — an EDIT or UPDATE rewrites the see-also section
  of a note and the broken link disappears. This would validate the self-cleaning
  hypothesis.

- **Broken link title appearing in L1/L2 reasoning** — if the model cites a
  non-existent note by its hallucinated title in routing reasoning, the false context
  is actively polluting decisions. This is the failure mode that warrants immediate
  action.

---

## Integration with the INSPECTION.md criteria

The INSPECTION.md eight-step checklist is the full quality gate before authoring benchmark tasks. The per-paper analysis in these conversations is the incremental version — accumulating evidence toward that gate. By the time all 20 papers are ingested:

- Step 1 (Note Quality) should be answerable from the notes examined per-paper
- Step 2 (UPDATE Quality) should be answerable from the UPDATE notes tracked
- Step 3 (Hub Note Analysis) needs the final activation graph and hub note reads
- Step 4 (SYNTHESISE Quality) should be answered from the ongoing SYNTHESISE tracking
- Step 5 (Late-Paper Notes) requires deliberate attention at papers 14–19
- Step 6 (Epistemic Links) — first `contradicts`/`supersedes` link is a milestone; track when it first appears
- Step 7 (STUB Notes) — STUB is removed from the pipeline; if any STUBs appear, treat as a failure
- Step 8 (Confidence Outliers) — track and document as they occur, not at the end
