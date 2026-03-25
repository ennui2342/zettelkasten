# Iteration 3 Evaluation Prompt

*Used for Run 3 — skill v3 adds explicit two-phase navigation (anchor → radiate).*

Each agent received this prompt with `{question}` substituted from `questions.md`.

---

```
You have access to a knowledge store at:
/Users/ennui2342/Resilio Sync/projects/zettelkasten/spikes/enrichment/notes

The store contains synthesised notes. Each note integrates multiple source
documents into a single concept and is already compressed — denser than the
raw material it came from. There are typically 20–40 notes in a store.

## Navigation strategy

Start with grep to anchor on relevant notes. Then follow See Also links from
each note you read to radiate outward. Grep finds what you can name; See Also
finds what's adjacent but unnamed.

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

## What changed from iteration 2

- Added Navigation strategy section: names the two phases explicitly — grep to anchor, See Also to radiate
- Everything else unchanged

## Test questions for this run

- Q8 (structural miss canary) — z001 still unreached across all runs; explicit grep-first framing may or may not help since the miss is a vocabulary gap (phase transitions → complex systems), not a strategy gap
- Q5 (peripheral miss) — z004 missed in Iter 1 (7 reads, stopped early); two-phase framing may push the agent to radiate further before stopping
- Q7 (regression check) — 13 reads in Iter 2; confirm two-phase framing doesn't inflate reads further
