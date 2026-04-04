# zettelkasten

Feed it documents — papers, articles, repos, anything. It extracts the key ideas, finds where they connect to what you already know, and integrates them into a growing graph of topic notes. The corpus is a directory of plain `.md` files, compatible with Obsidian, portable, and human-readable. Ask it a question and an agentic loop navigates the graph to synthesise an answer.

## The core idea: spend tokens at ingestion, not at query time

The naive approach to a personal knowledge base is to retrieve raw documents at query time and ask the LLM to reason over them. This is expensive, slow, and degrades as the corpus grows.

This library inverts that. Tokens are spent at ingestion — the LLM reads every new document in the context of the existing knowledge graph and decides how to integrate it. The output is a set of high-quality, LLM-maintained `.md` notes, each covering one topic, synthesised across all sources seen so far. At query time, the LLM is reading well-structured notes about topics it needs, not raw documents.

The better the ingestion, the less work query time requires.

## Ingestion: Form → Gather → Integrate

Every document passes through three phases:

**Form** — one LLM call extracts `n` topic drafts from the document. Each covers a distinct subject. Content relevant to multiple topics appears in both drafts.

**Gather** — for each draft, five signals are fused to retrieve the top-20 most relevant existing notes from the corpus. This is the most expensive part of ingestion, and deliberately so: getting the right context in front of the integration LLM is what determines whether the next step produces a good note or a mediocre one.

| Signal | Weight | Description |
|--------|--------|-------------|
| Dense embedding | 0.45 | Asymmetric query/document similarity (Voyage) |
| BM25 + MuGI | 0.27 | Lexical retrieval with pseudo-note query expansion |
| Co-activation graph | 0.18 | Notes that historically appeared together in integration events |
| Step-back abstraction | 0.05 | LLM-generated principle-level query |
| Hypothetical peer notes | 0.05 | LLM-generated example notes (HyDE) |

Validated at **R@10=0.667, MRR=0.844** on a 60-event held-out set.

**Integrate** — the LLM sees the draft and its retrieved cluster and acts as a Wikipedia editor. It does not append. It decides:

| Operation | When |
|-----------|------|
| `CREATE` | Draft introduces a genuinely new topic |
| `UPDATE` | Draft extends an existing note — full rewrite, not append |
| `EDIT` | Target note has grown large — compress and integrate |
| `SPLIT` | Note is conflating two separable concepts |
| `SYNTHESISE` | Draft reveals a bridging concept spanning multiple notes |
| `NOTHING` | Content is already covered — no write |

Each note represents current best understanding. Notes are never appended to — they are rewritten as understanding improves. Conflicting views become separate notes connected by See Also wikilinks, not blended into false synthesis.

## Search and query

At query time, the corpus is a directory of well-structured markdown notes. Two interfaces:

**`search`** returns the top-k notes most semantically similar to a query — useful for exploration and navigation.

**`query`** runs an agentic loop. The LLM is given tools — `list_notes`, `grep_notes`, `read_note`, `find_related` — and a question, and it navigates the graph to build an answer. This works better than retrieval-augmented generation for complex questions because:

- The notes are already synthesised. The LLM is reading a coherent article about a topic, not fragments of raw documents.
- Multi-hop questions require following connections across notes. The agentic loop can traverse See Also wikilinks, read related notes, and build up a picture across multiple reads.
- As models improve, reading good markdown directly outperforms retrieval pipeline engineering. The notes are the leverage point.

The agentic approach costs more per query than a search engine, but the notes it reads were built to be read this way.

## Gets smarter with use

Every integration event records which notes were retrieved together as co-activation edges in a SQLite graph. These edges decay exponentially with time but accumulate across events. Notes in the same domain repeatedly co-activate and develop strong edges. Occasional cross-domain integrations create long-range connections.

The co-activation signal contributes 18% of the retrieval weight and improves as the corpus grows. New ingestions about familiar topics benefit from this accumulated context — the system develops an increasingly accurate model of its own topology.

## Plain markdown throughout

Source of truth is a directory of `.md` files with YAML frontmatter. Works with Obsidian. Git-diffable. Portable — zip and share. The SQLite index is a derived cache, fully rebuildable from the markdown directory.

## Quick start

```bash
git clone https://github.com/ennui2342/zettelkasten
cd zettelkasten
make install          # uv sync with all extras

uv run zettelkasten init ./my-knowledge-base
cd my-knowledge-base
# edit zettelkasten.toml to add your API keys, then:
uv run zettelkasten ingest article.md
uv run zettelkasten search "spaced repetition"
uv run zettelkasten query "How does spaced repetition work?"
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

## Documentation

See [`docs/index.md`](docs/index.md).
