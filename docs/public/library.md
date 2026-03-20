# Library API

## Installation

```bash
# Core library
pip install zettelkasten

# With Anthropic LLM support
pip install zettelkasten[anthropic]

# With Voyage AI embedding support
pip install zettelkasten[voyage]

# Both (recommended for production)
pip install zettelkasten[anthropic,voyage]
```

## ZettelkastenStore

The main entry point.  All file I/O, indexing, and pipeline orchestration go
through this class.

```python
from zettelkasten import ZettelkastenStore
from zettelkasten.providers import AnthropicLLM, VoyageEmbed

store = ZettelkastenStore(
    notes_dir="./knowledge",
    index_path="./knowledge.db",
)

llm   = AnthropicLLM(model="claude-opus-4-6", api_key="...")
embed = VoyageEmbed(model="voyage-3",         api_key="...")
```

### `ingest_text(text, llm, embed, source=None) → list[IntegrationResult]`

Run the full Form → Gather → Integrate pipeline on a document.

```python
text = Path("article.md").read_text()
results = store.ingest_text(text, llm, embed, source="article.md")

for r in results:
    print(r.operation, r.note_id, r.note_title)
```

Each result corresponds to one draft note extracted from the document.
`operation` is one of `CREATE`, `UPDATE`, `EDIT`, `STUB`, `SYNTHESISE`,
`SPLIT`, `NOTHING`.  All operations write to the corpus at ingestion time
(`NOTHING` is a no-op).

### `search(query, llm, embed, top_k=10) → list[ZettelNote]`

Retrieve notes relevant to a free-text query using the same 5-signal Gather
fusion used during ingestion.

```python
results = store.search("spaced repetition", llm, embed, top_k=10)
for note in results:
    print(note.id, note.title)
```

### `write(note) → str`

Write a `ZettelNote` to disk and index.  Returns the note ID.  Use this for
direct note creation (bypassing the pipeline).

### `update(note_id, **changes) → ZettelNote`

Update one or more fields on an existing note.  Always bumps `updated`.
Raises `KeyError` if the note is not found.

```python
store.update("z20240101-001", confidence=0.9, stable=True)
```

### `mark_refuted(refuted_id, successor_id)`

Mark a note as `type="refuted"` and add a `supersedes` link on the successor.

### `rebuild_index()`

Rebuilds the SQLite index from the notes directory (delegates to
`ZettelIndex.rebuild_from_directory`).  Call after manual file edits.

---

## LLM and Embedding Providers

The library accepts any object satisfying the `LLMProvider` or `EmbedProvider`
protocol.

```python
class LLMProvider(Protocol):
    def complete(self, prompt: str, *, max_tokens: int, temperature: float = 0.0) -> str: ...

class EmbedProvider(Protocol):
    def embed(self, texts: list[str], *, input_type: str = "document") -> list[np.ndarray]: ...
```

### Concrete providers

| Class | Package | Notes |
|-------|---------|-------|
| `AnthropicLLM(model, api_key)` | `anthropic` | Any Claude model |
| `VoyageEmbed(model, api_key)` | `voyageai` | Validated on `voyage-3` / `voyage-3-lite` |

### Mock providers (testing)

```python
from zettelkasten.providers import MockLLM, MockEmbed

# Fixed response
llm = MockLLM("## Topic\n\nSome body text.")

# Dynamic response
llm = MockLLM(lambda prompt, **kw: "response based on prompt")

# Deterministic unit-normalised embeddings, SHA-256 seeded
embed = MockEmbed(dims=1024)
```

---

## IntegrationResult

Returned by `ingest_text` — one per draft note.

```python
@dataclass
class IntegrationResult:
    operation:   str        # CREATE | UPDATE | EDIT | STUB | SYNTHESISE | SPLIT | NOTHING
    reasoning:   str        # LLM's one-sentence rationale
    confidence:  float      # 0–1
    target_ids:  list[str]  # IDs of existing notes acted on
    note_title:  str        # title of created/updated note (empty if NOTHING)
    note_body:   str        # body  of created/updated note
    is_curation: bool       # retained for compatibility; always False
    note_id:     str        # ID assigned by store (empty if NOTHING)
```

---

## `save_to_inbox`

Archive a document to a staging directory without running the pipeline.
This is the function backing the `--save-only` flag on `ingest` and `serve`.

```python
from zettelkasten.inbox import save_to_inbox
from pathlib import Path

path = save_to_inbox(
    inbox_dir="./inbox",
    text=Path("article.md").read_text(),
    source="article.md",
)
# Returns the Path of the written file, e.g. ./inbox/20260316-120000-article.md
```

Each file is a Markdown document with YAML frontmatter:

```
---
source: article.md
saved_at: 2026-03-16T12:00:00+00:00
content_length: 3421
---

[extracted text body]
```

**Signature:** `save_to_inbox(inbox_dir, text, source=None, **extra_meta) → Path`

- `inbox_dir` — directory to write into (created automatically if absent)
- `text` — plain text content to archive
- `source` — file path or URL used as the frontmatter `source` field and to derive the filename slug
- `**extra_meta` — any additional key/value pairs written as extra frontmatter fields (`None` values are skipped)

---

## Using phase functions directly

The pipeline phases are also importable as standalone functions:

```python
from zettelkasten.form      import form_phase
from zettelkasten.gather    import gather_phase
from zettelkasten.integrate import integrate_phase

# Form: extract draft notes from a document
drafts = form_phase(text, llm)

# Gather: retrieve relevant corpus notes for one draft
cluster = gather_phase(draft, corpus, llm, embed, top_k=20)

# Integrate: decide and execute
result = integrate_phase(draft, cluster, llm)
```

---

## ZettelIndex

Low-level SQLite index.  Use `ZettelkastenStore` in normal usage; use
`ZettelIndex` directly only when you need fine-grained control.

```python
from zettelkasten.index import ZettelIndex

index = ZettelIndex("knowledge.db")
index.initialise()
index.upsert_note(note)
row = index.get_note_row("z20240101-001")
index.rebuild_from_directory("./knowledge")
```
