# CLI Reference

The `zettelkasten` command-line tool wraps the library for day-to-day use.

## Installation

```bash
pip install zettelkasten[anthropic,voyage]
```

`trafilatura` is a core dependency and is installed automatically.

## Configuration — `zettelkasten.toml`

All commands look for `zettelkasten.toml` in the current directory (or the
path given by `--config`).  A skeleton is created by `zettelkasten init`.

```toml
[zettelkasten]
notes_dir  = "knowledge"    # directory of .md note files
index_path = "knowledge.db" # SQLite index (cache, always rebuildable)
inbox_dir  = "inbox"        # directory for --save-only staging (created on demand)

[llm]
provider = "anthropic"
model    = "claude-opus-4-6"
api_key  = ""               # set ANTHROPIC_API_KEY env var instead

[embed]
provider = "voyage"
model    = "voyage-3"
api_key  = ""               # set VOYAGE_API_KEY env var instead
```

**Environment variable overrides:**

| Variable | Config key |
|----------|-----------|
| `ANTHROPIC_API_KEY` | `llm.api_key` (when provider = anthropic) |
| `VOYAGE_API_KEY` | `embed.api_key` (when provider = voyage) |
| `ZETTELKASTEN_NOTES_DIR` | `zettelkasten.notes_dir` |
| `ZETTELKASTEN_INDEX_PATH` | `zettelkasten.index_path` |

---

## Commands

### `zettelkasten init [DIRECTORY]`

Initialise a new zettelkasten in DIRECTORY (default: current directory).

Creates:
- `zettelkasten.toml` (config skeleton)
- `knowledge/` (notes directory)

```bash
zettelkasten init ./my-knowledge-base
```

---

### `zettelkasten ingest SOURCE`

Ingest a document through the Form → Gather → Integrate pipeline.
SOURCE can be a local file path or an `http(s)://` URL.  URLs are fetched
and the main article text is extracted automatically using
[trafilatura](https://trafilatura.readthedocs.io/) (strips navigation, ads,
and boilerplate).

```bash
# Local file
zettelkasten ingest article.md

# URL
zettelkasten ingest https://example.com/article

zettelkasten ingest --config /path/to/zettelkasten.toml article.md
zettelkasten ingest --verbose https://example.com/article

# Save to inbox without running the pipeline
zettelkasten ingest --save-only article.md
```

**`--save-only`** skips the Form → Gather → Integrate pipeline entirely and writes
the document to `inbox_dir` as a timestamped Markdown file with YAML frontmatter
(`source`, `saved_at`).  Useful for bulk-staging content to process later.
`inbox_dir` must be set in `zettelkasten.toml` (default: `inbox`).

Prints a table of operations performed:

```
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Operation ┃ Note ID          ┃ Title                     ┃ Confidence ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ CREATE    │ z20240115-003    │ Testing Effect            │ 0.90       │
│ UPDATE    │ z20240115-001    │ Spaced Repetition         │ 0.85       │
│ NOTHING   │                  │                           │ 0.95       │
└───────────┴──────────────────┴───────────────────────────┴────────────┘
```

---

### `zettelkasten search QUERY`

Search the knowledge base using the 5-signal Gather fusion.

```bash
zettelkasten search "spaced repetition"
zettelkasten search "memory consolidation" --top-k 5
```

Options:
- `--top-k N` — number of results (default: 10)
- `--config PATH`
- `--verbose`

---

### `zettelkasten serve`

Start a local HTTP server that accepts rendered page HTML from the Chrome
extension (or bookmarklet) and runs the full ingest pipeline.

```bash
zettelkasten serve
zettelkasten serve --port 7842 --config zettelkasten.toml

# Accept documents but only archive them — do not run the pipeline
zettelkasten serve --save-only
```

Options:
- `--port N` — port to listen on (default: 7842)
- `--host ADDR` — interface to bind (default: 127.0.0.1)
- `--save-only` — archive received documents to `inbox_dir` without running the pipeline
- `--config PATH`
- `--verbose`

The server exposes two endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Returns `{"status": "ok"}` |
| `/ingest` | POST | JSON body `{"html": "...", "url": "..."}` |

All responses include CORS headers so any browser origin can call it.

---

## Chrome Extension

The bookmarklet approach (`javascript:` URLs) is blocked by the Content-Security-Policy
on pages like X/Twitter.  Use the **Chrome extension** instead — it runs in a
privileged context that bypasses CSP entirely.

### Installation

1. Start the server: `zettelkasten serve`
2. Open Chrome → `chrome://extensions`
3. Enable **Developer mode** (top-right toggle)
4. Click **Load unpacked** and select the `chrome-extension/` directory in this
   repo
5. The "Ingest → zettelkasten" icon appears in the toolbar

### Usage

Navigate to any page, click the extension icon, then click **Ingest this page**.
The extension:

1. Captures the fully-rendered page HTML (including JavaScript-rendered content
   — works on X/Twitter, Single-Page Apps, etc.)
2. POSTs it to `http://127.0.0.1:7842/ingest`
3. Displays the operation results inline in the popup

The **Server port** field defaults to `7842` and is persisted across sessions.

---

### `zettelkasten bookmarklet`

Print the bookmarklet JavaScript without starting the server.  Works on most
pages, but **will be blocked by strict CSP pages** (X/Twitter, GitHub, etc.) —
use the Chrome extension for those.

```bash
zettelkasten bookmarklet
zettelkasten bookmarklet --port 9000
```

---

### `zettelkasten query QUESTION`

Answer a question by navigating the knowledge base using the Iter 4 agentic
skill.  An LLM calls `grep_notes`, `read_note`, and `list_notes` in a loop,
following `## See Also` links until it can synthesise a complete answer.

```bash
zettelkasten query "What are the trade-offs between different retrieval strategies?"
zettelkasten query "How does activation accumulation work?" --verbose
zettelkasten query "..." --max-rounds 30
```

Options:
- `--max-rounds N` — maximum agentic loop iterations before raising an error (default: 20)
- `--config PATH`
- `--verbose` — logs each tool call (`enrich.tool round=N name=... input=...`) so you can follow the navigation trace

Uses `llm.model` from `zettelkasten.toml` (the same model as ingest, not `fast_model`).

---

### `zettelkasten curate`

Show pending curation recommendations (SPLIT decisions logged during
ingestion).  Automated curation execution is not yet implemented; use
`--verbose` during `ingest` to see SPLIT recommendations as they occur.

```bash
zettelkasten curate
```

---

### `zettelkasten rebuild-index`

Rebuild the SQLite index from the notes directory.  Safe to run after manual
edits to note files; the index is always derivable from the markdown files.

```bash
zettelkasten rebuild-index
zettelkasten rebuild-index --config /path/to/zettelkasten.toml
```

---

## Global options

| Option | Description |
|--------|-------------|
| `--config PATH` | Path to `zettelkasten.toml` |
| `--verbose / -v` | Enable DEBUG logging |
| `--help` | Show help |

---

## Development — Makefile targets

```bash
make install     # uv sync --extra dev,anthropic,voyage (create .venv, install all deps)
make test        # run full test suite via uv run pytest
make test-fast   # pytest -x -q (stop on first failure)
make shell       # open a Python REPL in the project environment
```
