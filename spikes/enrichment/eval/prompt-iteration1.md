# Iteration 1 Evaluation Prompt

*Used for Run 1 — skill v1 injected (stopping criterion + titles first).*

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

## What changed from baseline

- Skill body injected before the question
- Single intervention: stopping criterion + titles-first guidance
- No mention of See Also links, berry-picking, or convergent/divergent modes

## Test questions for this run

Q2, Q5, Q8, Q11 — selected to measure the stopping criterion:
- Q2 and Q5 were the worst offenders (31 and 30 reads, GT needed 3 and 4)
- Q8 was the best baseline navigator (14 reads, immediate grep hit) — regression canary
- Q11 was the most efficient (9 reads, all GT found) — regression canary
