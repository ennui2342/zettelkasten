"""ZettelNote — the core note dataclass with markdown round-trip."""
from __future__ import annotations

import base64
import re
import struct
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import frontmatter
import numpy as np

# ---------------------------------------------------------------------------
# Vocabulary constants
# ---------------------------------------------------------------------------

_ID_RE = re.compile(r"^z\d{8}-\d{3}$")


# ---------------------------------------------------------------------------
# ZettelNote
# ---------------------------------------------------------------------------


@dataclass
class ZettelNote:
    id: str
    title: str
    body: str
    confidence: float
    created: datetime
    updated: datetime
    sources: list[str] = field(default_factory=list)
    # Embedding stored in frontmatter for index rebuild; activation is runtime state in SQLite
    embedding: Optional[np.ndarray] = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if self.id and not _ID_RE.match(self.id):
            raise ValueError(
                f"Invalid id {self.id!r}. Must match z{{YYYYMMDD}}-{{seq:03d}}"
            )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_markdown(self) -> str:
        meta: dict = {
            "id": self.id,
            "title": self.title,
            "confidence": self.confidence,
            "created": _fmt_dt(self.created),
            "updated": _fmt_dt(self.updated),
        }
        if self.sources:
            meta["sources"] = list(self.sources)
        if self.embedding is not None:
            meta["embedding"] = _vec_to_b64(self.embedding)
        post = frontmatter.Post(
            content=f"# {self.title}\n\n{self.body}",
            **meta,
        )
        return frontmatter.dumps(post)

    @classmethod
    def from_markdown(cls, text: str) -> "ZettelNote":
        post = frontmatter.loads(text)
        content = post.content.strip()

        # Extract title from first H1
        title, body = _split_title_body(content)

        sources: list[str] = list(post.get("sources") or [])
        # co_activations was removed in favour of SQLite activation edges — silently ignored
        embedding: Optional[np.ndarray] = None
        raw_emb = post.get("embedding")
        if raw_emb:
            embedding = _b64_to_vec(str(raw_emb))

        return cls(
            id=post["id"],
            title=title,
            body=body,
            confidence=float(post["confidence"]),
            created=_parse_dt(post["created"]),
            updated=_parse_dt(post["updated"]),
            sources=sources,
            embedding=embedding,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _vec_to_b64(vec: np.ndarray) -> str:
    arr = vec.astype(np.float32)
    return base64.b64encode(arr.tobytes()).decode("ascii")


def _b64_to_vec(s: str) -> np.ndarray:
    raw = base64.b64decode(s)
    n = len(raw) // 4
    return np.array(struct.unpack(f"{n}f", raw), dtype=np.float32)


def _fmt_dt(dt: datetime) -> str:
    return dt.isoformat()


def _parse_dt(value: object) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _split_title_body(content: str) -> tuple[str, str]:
    """Extract the first # heading as title; remainder is body."""
    lines = content.split("\n")
    title = ""
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            # skip blank line after heading
            body_start = i + 1
            while body_start < len(lines) and lines[body_start].strip() == "":
                body_start += 1
            break
    body = "\n".join(lines[body_start:]).strip()
    return title, body
