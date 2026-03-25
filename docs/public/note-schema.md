# Note Schema

Every note is a Markdown file with YAML frontmatter.  The Markdown file is the
**single source of truth**; the SQLite index is a derived cache.

## File naming

```
z{YYYYMMDD}-{seq:03d}.md
```

Examples: `z20240115-001.md`, `z20240115-002.md`.  The date is UTC.  The
sequence resets daily from `001`.

## Frontmatter fields

```yaml
---
id:            z20240115-001       # matches filename stem
type:          permanent           # permanent | stub | refuted | synthesised
confidence:    0.8                 # 0–1; how certain the claim is
salience:      0.5                 # 0–1; relevance / importance
stable:        true                # false = still evolving
created:       2024-01-15T10:00:00+00:00
updated:       2024-01-15T10:00:00+00:00
last_accessed: 2024-01-15T10:00:00+00:00
links:
  - target: z20240115-002
    rel:    supersedes             # contradicts | supersedes | splits-from | merges-into
    note:   "Optional annotation"
sources:
  - https://arxiv.org/abs/2511.05269   # URLs of documents that gave birth to this note
embedding:     <base64 float32 vector>   # omitted when not yet embedded
---
# Note Title

Note body text…
```

## Types

| Type | Meaning |
|------|---------|
| `permanent` | Mature, well-evidenced note |
| `stub` | New topic, low confidence, awaiting elaboration |
| `refuted` | Superseded or contradicted; kept for provenance |
| `synthesised` | Bridges two or more other notes |

## Link relations (epistemic only)

| Rel | Meaning |
|-----|---------|
| `contradicts` | This note disputes the target |
| `supersedes` | This note replaces or extends the target |
| `splits-from` | This note was split from the target |
| `merges-into` | This note was merged into the target |

Semantic / topical relationships are handled by the retrieval signals; they
are **not** stored as links.

## Sources (provenance)

`sources` is a list of document URLs recorded at **note birth** — that is, when
a CREATE, SYNTHESISE, or SPLIT (second note only) operation first creates the
note.  Subsequent UPDATEs and EDITs do not append to this list.

The field is omitted from the YAML when empty.

## Co-activation

The co-activation signal is stored entirely in the SQLite index (not in the
markdown file).  Each integration event that involves a note records which other
notes were co-retrieved, building a small-world activation graph used by the
retrieval pipeline.

## Embedding

The `embedding` field stores a base64-encoded sequence of little-endian
`float32` values (unit-normalised).  It is populated during ingestion and
re-computed whenever the note body changes.  The same value is mirrored in
the SQLite index for fast nearest-neighbour lookup.

## Python dataclass

```python
@dataclass
class ZettelNote:
    id:            str
    title:         str
    body:          str
    type:          Literal["permanent", "stub", "refuted", "synthesised"]
    confidence:    float
    salience:      float
    stable:        bool
    created:       datetime
    updated:       datetime
    last_accessed: datetime
    links:         list[ZettelLink]       = field(default_factory=list)
    sources:       list[str]             = field(default_factory=list)
    embedding:     Optional[np.ndarray]  = field(default=None, compare=False)
```

## Round-trip

```python
note = ZettelNote.from_markdown(path.read_text())
md   = note.to_markdown()
```
