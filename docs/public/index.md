# zettelkasten — Developer Documentation

A standalone Python library for knowledge synthesis: incoming documents are
chunked into topic notes (Form), relevant existing notes are retrieved via
multi-signal search (Gather), and an LLM decides how to integrate each draft
into the corpus (Integrate).  The result is a living knowledge graph that
synthesises across sources rather than just storing them.

## Contents

| Document | Description |
|----------|-------------|
| [library.md](library.md) | Python library API and usage |
| [note-schema.md](note-schema.md) | ZettelNote schema and markdown format |
| [pipeline.md](pipeline.md) | Form → Gather → Integrate pipeline in depth |
| [cli.md](cli.md) | Command-line interface reference |
| [monitoring.md](monitoring.md) | Structured logging and observability |

## Quick start

```bash
pip install zettelkasten[anthropic,voyage]

# Initialise a knowledge base
zettelkasten init ./knowledge

# Edit zettelkasten.toml to add your API keys, then:
zettelkasten ingest article.md
zettelkasten search "spaced repetition"
```

## Architecture at a glance

```
ingest_text(text)
    │
    ├── Form phase        LLM single-shot → list[ZettelNote] drafts
    │
    └── for each draft:
          ├── Gather phase   5-signal fusion → top-20 corpus notes
          └── Integrate phase  two-step LLM → write/update notes
```

The library has no hard dependency on any particular LLM or embedding provider.
Callers supply lightweight `LLMProvider` / `EmbedProvider` objects; the library
ships concrete implementations for Anthropic and Voyage AI.
