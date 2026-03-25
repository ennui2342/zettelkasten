# Baseline Evaluation Prompt

*Used for Run 0 — no skill, no navigation guidance.*

Each agent received this prompt with `{question}` substituted from `questions.md`.

---

```
You have access to a knowledge store at:
/Users/ennui2342/Resilio Sync/projects/zettelkasten/spikes/enrichment/notes

The store contains markdown files. Each file is a synthesised note on a topic.

Answer this research question as best you can using the store:

"{question}"

When done, report:
1. NAVIGATION TRACE: every tool call you made (grep, glob, read, etc.) in order,
   with the exact filenames or patterns used
2. NOTES READ: list of every note filename you read (full or partial)
3. ANSWER: your answer to the question

Do not use any external knowledge or search. Use only what is in the notes directory.
```

---

## Notes on this prompt

- No mention of note structure, frontmatter fields, or See Also sections
- No navigation strategy guidance
- No stopping criterion
- The reporting requirement (NAVIGATION TRACE, NOTES READ) was added to make
  the navigation behaviour observable — it may have slightly influenced behaviour
  by making the agent more self-conscious about tool use
- 7/12 agents hit the session rate limit before completing synthesis, because all
  12 were run in parallel. Future runs: sequential or small batches of 3-4.
