# Iteration 4 Evaluation Prompt

*Used for Run 4 — skill v4 softens radiation to conditional.*

Each agent received this prompt with `{question}` substituted from `questions.md`.

---

```
You have access to a knowledge store at:
/Users/ennui2342/Resilio Sync/projects/zettelkasten/spikes/enrichment/notes

The store contains synthesised notes. Each note integrates multiple source
documents into a single concept and is already compressed — denser than the
raw material it came from. There are typically 20–40 notes in a store.

## Navigation strategy

Start with grep to anchor on relevant notes. If the anchored notes don't
fully cover the question, follow See Also links to find adjacent notes you
wouldn't have named. Grep finds what you can name; See Also finds what's
adjacent but unnamed.

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

## What changed from iteration 3

- Navigation strategy: "Then follow See Also links from each note you read to radiate outward" → "If the anchored notes don't fully cover the question, follow See Also links to find adjacent notes you wouldn't have named"
- Radiation is now conditional on a coverage gap, not the default next step

## Test questions for this run

- Q7 (regression check) — 18 reads in Iter 3; should come back down if conditional framing restrains over-radiation
- Q5 (peripheral miss canary) — z004 still missed; no change expected, but confirming radiation restraint doesn't hurt coverage
- Q8 (structural miss canary) — z001 still missed; same expectation
