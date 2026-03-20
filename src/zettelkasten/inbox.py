"""Inbox: archive source documents with YAML frontmatter metadata.

Each saved file is a markdown document with a frontmatter header:

  ---
  source: https://example.com/article
  saved_at: 2026-03-16T12:00:00+00:00
  content_length: 3421
  ---

  [extracted text body]

Filenames are timestamped and slug-derived from the source:
  20260316-120000-example.com-article.md
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


def save_to_inbox(
    inbox_dir: Path | str,
    text: str,
    source: str | None = None,
    **extra_meta: str,
) -> Path:
    """Save *text* to *inbox_dir* with YAML frontmatter metadata.

    Returns the path of the saved file.  Creates *inbox_dir* if it does
    not exist.  Extra keyword arguments are written as additional frontmatter
    fields (values are coerced to str; ``None`` values are skipped).
    """
    inbox_dir = Path(inbox_dir)
    inbox_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(tz=timezone.utc)
    ts = now.strftime("%Y%m%d-%H%M%S")
    slug = _slug(source) if source else "document"
    path = inbox_dir / f"{ts}-{slug}.md"

    lines: list[str] = ["---"]
    if source:
        lines.append(f"source: {_yaml_str(source)}")
    lines.append(f"saved_at: {now.isoformat()}")
    lines.append(f"content_length: {len(text)}")
    for key, value in extra_meta.items():
        if value is not None:
            lines.append(f"{key}: {_yaml_str(str(value))}")
    lines += ["---", "", text]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slug(source: str) -> str:
    """Derive a short filesystem-safe slug from a URL or file path."""
    try:
        parsed = urlparse(source)
        if parsed.scheme in ("http", "https"):
            parts = [parsed.netloc] + [p for p in parsed.path.split("/") if p]
            raw = "-".join(parts)
        else:
            raw = Path(source).stem
    except Exception:
        raw = source
    slug = re.sub(r"[^\w-]", "-", raw)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:60] or "document"


def _yaml_str(value: str) -> str:
    """Quote a YAML string value when it contains characters that would break bare scalars."""
    if any(c in value for c in (':', '#', '[', ']', '{', '}', ',', '"', "'")):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value
