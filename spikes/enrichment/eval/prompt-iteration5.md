# Iteration 5 Evaluation Prompt

*Used for Run 5 — skill v5 adds hub note hint.*

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

## Hub notes

Hub notes aggregate multiple concepts and often bridge clusters that keyword
search can't connect — if you've covered the obvious cluster but the question
touches broad architectural themes, check whether any hub note title suggests
a missing dimension.

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

## What changed from iteration 4

- Added Hub notes section: hints that broad architectural questions may need a hub note that bridges clusters
- Everything else unchanged

## Test questions for this run

- Q8 (structural miss) — z001 (Multi-Agent Architectures) is a hub note; the hint should prompt the agent to scan titles for architectural breadth after anchoring on phase transitions
- Q5 (peripheral miss) — z004 (LLM and Agent Routing) is not a hub; test whether the hint causes over-reads on non-hub questions
- Q7 (regression check) — 11 reads in Iter 4; confirm hub hint doesn't inflate reads on already-covered questions
