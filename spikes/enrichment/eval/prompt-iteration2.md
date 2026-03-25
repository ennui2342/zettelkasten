# Iteration 2 Evaluation Prompt

*Used for Run 2 — skill v2 adds See Also guidance.*

Each agent received this prompt with `{question}` substituted from `questions.md`.

---

```
You have access to a knowledge store at:
/Users/ennui2342/Resilio Sync/projects/zettelkasten/spikes/enrichment/notes

The store contains synthesised notes. Each note integrates multiple source
documents into a single concept and is already compressed — denser than the
raw material it came from. There are typically 20–40 notes in a store.

## Finding notes

Scan note titles before reading bodies. Titles are descriptive enough to
judge relevance without opening the file.

## Following connections

Each note ends with a ## See Also section listing related notes with a brief
description of the relationship. After reading a note, check its See Also
links to find adjacent notes you might not have thought to search for — this
is the primary way to discover notes that are conceptually close but wouldn't
appear in a keyword search.

## When to stop

Stop reading when you have covered all aspects of the question. You do not
need to read every note that looks relevant — read until you have enough,
then synthesise. More reads is not better.

---

Answer this research question using the store:

"{question}"

When done, report:
1. NAVIGATION TRACE: every tool call you made (grep, glob, read, etc.) in
   order, with the exact filenames or patterns used
2. NOTES READ: list of every note filename you read (full or partial)
3. ANSWER: your answer to the question
```

---

## What changed from iteration 1

- Added See Also guidance: agents now know the section exists and are told
  to use it for discovering adjacent notes after reading
- Everything else unchanged

## Test questions for this run

- Q7 (adjacent possible, hub-accessible) — most likely to benefit from
  path-following; the trilemma and architecture notes have rich See Also clusters
- Q10 (analogical transfer, hub-accessible) — cross-domain connection-making;
  berry-picking from the trilemma note should surface the formal foundations cluster
- Q2 (regression check) — iteration 1 handled well at 4 reads; confirm See Also
  guidance doesn't cause over-reading
