# zettelkasten

A Python library that turns documents into a self-organising, queryable knowledge graph.

You feed it articles, papers, or any text — it extracts the key ideas, finds where they connect to what you've already read, and integrates them into a growing corpus of topic notes. Ask it a question and it navigates the graph to synthesise an answer.

The corpus is a directory of plain markdown files. Each note covers one topic, written and rewritten by an LLM as understanding accumulates across sources. Notes link to each other with `[[id|Title]]` wikilinks. The whole thing is human-readable, portable, and gets smarter the more you use it.

## Quick start

```bash
pip install zettelkasten[anthropic,voyage]

# Initialise a knowledge base
zettelkasten init ./my-knowledge-base

# Edit zettelkasten.toml to add your API keys, then:
zettelkasten ingest article.md
zettelkasten search "spaced repetition"
zettelkasten query "How does spaced repetition work?"
```

Or via the Python API:

```python
from zettelkasten import ZettelkastenStore
from zettelkasten.providers import AnthropicLLM, AnthropicToolLLM, VoyageEmbed

store    = ZettelkastenStore(notes_dir="./knowledge", index_path="./knowledge.db")
llm      = AnthropicLLM(model="claude-opus-4-6", api_key="...")
tool_llm = AnthropicToolLLM(model="claude-sonnet-4-6", api_key="...")
embed    = VoyageEmbed(model="voyage-3", api_key="...")

store.ingest_text(Path("paper.md").read_text(), llm, embed)
answer = store.query("What are the tradeoffs between centralised and decentralised coordination?", tool_llm)
notes  = store.search("spaced repetition", llm, embed)
```

## How it works

Ingestion runs three phases for each document:

- **Form** — extracts topic notes from the document (one per distinct subject)
- **Gather** — retrieves the most relevant existing notes using a five-signal weighted fusion (dense embedding, BM25 + query expansion, co-activation history, step-back abstraction, hypothetical peer notes); validated at R@10=0.667, MRR=0.844
- **Integrate** — an LLM acts as a Wikipedia editor, deciding how the corpus needs to change: CREATE, UPDATE, EDIT, SPLIT, SYNTHESISE, or NOTHING

Notes grow through successive passes and are never simply appended to — the corpus stays coherent rather than growing into a log.

## Documentation

- [`docs/library.md`](docs/library.md) — Python API reference
- [`docs/cli.md`](docs/cli.md) — CLI reference
- [`docs/pipeline.md`](docs/pipeline.md) — pipeline detail (Form → Gather → Integrate)
- [`docs/enrichment.md`](docs/enrichment.md) — query and enrichment (how `store.query()` works)
- [`docs/note-schema.md`](docs/note-schema.md) — note format
- [`docs/design/design-principles.md`](docs/design/design-principles.md) — design rationale
