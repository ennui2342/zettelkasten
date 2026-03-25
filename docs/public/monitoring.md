# Monitoring and Observability

The zettelkasten library emits structured log messages at every significant
decision point in the pipeline.  All messages use the `zettelkasten` logger.

## Log levels

| Level | Use |
|-------|-----|
| `INFO` | Phase boundaries, operation decisions, write completions |
| `DEBUG` | Per-signal scores, step 2 output details |

## Configuring logging

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
)
```

The CLI enables INFO by default; pass `--verbose` for DEBUG.

---

## Message catalogue

### Store

| Message | Level | Fields |
|---------|-------|--------|
| `store.ingest` | INFO | `source`, `text_len` |
| `store.ingest_complete` | INFO | `results` (count) |
| `store.wrote` | INFO | `op`, `id` |
| `store.update_target_missing` | WARN | `id` |

### Form phase

| Message | Level | Fields |
|---------|-------|--------|
| `form.start` | INFO | `doc_len` |
| `form.complete` | INFO | `drafts` (count) |
| `form.draft` | DEBUG | `title`, `body_len` |

### Gather phase

| Message | Level | Fields |
|---------|-------|--------|
| `gather.start` | INFO | `draft_id`, `corpus_size` |
| `gather.signal` | DEBUG | `name`, `top` (id=score of top note) |
| `gather.complete` | INFO | `results` (count), `top_id` |

### Integrate phase

| Message | Level | Fields |
|---------|-------|--------|
| `integrate.start` | INFO | `draft_title`, `cluster_size` |
| `integrate.step1` | INFO | `operation`, `confidence`, `targets`, `reasoning` |
| `integrate.step2` | DEBUG | `operation`, `title`, `body_len` |
| `integrate.complete` | INFO | `operation`, `title` |
| `integrate.unknown_operation` | WARN | `op` |

---

## Tracing a document through the pipeline

With `--verbose` (DEBUG level) you can follow a document through all three
phases:

```
10:01:02 INFO     zettelkasten store.ingest source='article.md' text_len=4521
10:01:02 INFO     zettelkasten form.start doc_len=4521
10:01:05 INFO     zettelkasten form.complete drafts=3
10:01:05 DEBUG    zettelkasten form.draft title='Testing Effect' body_len=312
10:01:05 DEBUG    zettelkasten form.draft title='Spaced Repetition' body_len=287
10:01:05 DEBUG    zettelkasten form.draft title='Generation Effect' body_len=195

10:01:05 INFO     zettelkasten gather.start draft_id='' corpus_size=42
10:01:06 DEBUG    zettelkasten gather.signal name=body_query top=z20240110-003=0.872
10:01:07 DEBUG    zettelkasten gather.signal name=bm25_mugi_stem top=z20240110-003=12.4
10:01:08 DEBUG    zettelkasten gather.signal name=activation top=none
10:01:09 DEBUG    zettelkasten gather.signal name=step_back top=z20240110-007=0.841
10:01:10 DEBUG    zettelkasten gather.signal name=hyde_multi top=z20240110-003=0.859
10:01:10 INFO     zettelkasten gather.complete results=20 top_id=z20240110-003

10:01:10 INFO     zettelkasten integrate.start draft_title='Testing Effect' cluster_size=20
10:01:11 INFO     zettelkasten integrate.step1 operation=UPDATE confidence=0.85 targets=['z20240110-003'] reasoning='Draft adds the retrieval-strength mechanism...'
10:01:12 DEBUG    zettelkasten integrate.step2 operation=UPDATE title='Testing Effect' body_len=487
10:01:12 INFO     zettelkasten integrate.complete operation=UPDATE title='Testing Effect'
10:01:12 INFO     zettelkasten store.wrote op=UPDATE id=z20240110-003
```

---

## Key observability checkpoints

**Is Form extracting reasonable topics?**
Look for `form.complete drafts=N`.  If N is very high (>10 per document),
the LLM may be splitting sub-concepts instead of broad topics.

**Is Gather finding the right notes?**
`gather.signal name=body_query top=…` shows the highest-scoring note per
signal.  If `activation top=none` appears, the corpus has no co-activation
history yet (normal for a new knowledge base).

**Is Integrate making sensible decisions?**
`integrate.l1` logs the L1 decision (SYNTHESISE/INTEGRATE/NOTHING) and
`integrate.l2` logs the CREATE/UPDATE decision.  Frequent `NOTHING` decisions
may indicate document content is already well covered.

**Curation opportunities?**
`SPLIT` decisions are logged at INFO in `integrate.l3`.  These fire via L3
when a large UPDATE target is found to contain two genuinely separable threads.
