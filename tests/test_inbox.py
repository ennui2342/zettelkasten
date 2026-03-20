"""Tests for inbox document archiving."""
from __future__ import annotations

from pathlib import Path

import pytest

from zettelkasten.inbox import _slug, _yaml_str, save_to_inbox


# ---------------------------------------------------------------------------
# save_to_inbox
# ---------------------------------------------------------------------------


def test_save_creates_file(tmp_path):
    path = save_to_inbox(tmp_path, "Hello world", source="https://example.com/article")
    assert path.exists()


def test_save_creates_inbox_dir(tmp_path):
    inbox = tmp_path / "inbox"
    assert not inbox.exists()
    save_to_inbox(inbox, "text")
    assert inbox.is_dir()


def test_save_filename_includes_timestamp_and_slug(tmp_path):
    path = save_to_inbox(tmp_path, "text", source="https://example.com/my-article")
    # e.g. 20260316-120000-example-com-my-article.md (dots become dashes)
    assert path.suffix == ".md"
    assert "example" in path.stem
    assert "my-article" in path.stem


def test_save_filename_no_source(tmp_path):
    path = save_to_inbox(tmp_path, "text")
    assert "document" in path.stem


def test_save_frontmatter_source(tmp_path):
    path = save_to_inbox(tmp_path, "body text", source="https://example.com/page")
    content = path.read_text()
    assert "source:" in content
    assert "example.com" in content


def test_save_frontmatter_saved_at(tmp_path):
    path = save_to_inbox(tmp_path, "body text")
    content = path.read_text()
    assert "saved_at:" in content


def test_save_frontmatter_content_length(tmp_path):
    text = "Hello world"
    path = save_to_inbox(tmp_path, text)
    content = path.read_text()
    assert f"content_length: {len(text)}" in content


def test_save_body_follows_frontmatter(tmp_path):
    path = save_to_inbox(tmp_path, "The actual article text.")
    content = path.read_text()
    # Body appears after closing ---
    parts = content.split("---\n", maxsplit=2)
    assert len(parts) == 3
    assert "The actual article text." in parts[2]


def test_save_extra_metadata(tmp_path):
    path = save_to_inbox(tmp_path, "text", title="My Page")
    content = path.read_text()
    assert "title: My Page" in content


def test_save_extra_metadata_none_skipped(tmp_path):
    path = save_to_inbox(tmp_path, "text", optional_field=None)
    content = path.read_text()
    assert "optional_field" not in content


def test_save_url_with_special_chars(tmp_path):
    url = "https://example.com/path?q=hello&lang=en#section"
    path = save_to_inbox(tmp_path, "text", source=url)
    assert path.exists()
    content = path.read_text()
    assert "source:" in content


# ---------------------------------------------------------------------------
# _slug
# ---------------------------------------------------------------------------


def test_slug_from_url():
    slug = _slug("https://example.com/article/test")
    assert "example" in slug  # dots become dashes: example-com
    assert len(slug) <= 60


def test_slug_from_file_path():
    slug = _slug("/home/user/my-document.md")
    assert slug == "my-document"


def test_slug_from_url_no_path():
    slug = _slug("https://example.com")
    assert "example" in slug


def test_slug_max_length():
    long_url = "https://" + "a" * 200 + ".com/very/long/path/here"
    slug = _slug(long_url)
    assert len(slug) <= 60


def test_slug_safe_chars_only():
    slug = _slug("https://example.com/path with spaces/")
    assert " " not in slug


# ---------------------------------------------------------------------------
# _yaml_str
# ---------------------------------------------------------------------------


def test_yaml_str_plain_value():
    assert _yaml_str("simple") == "simple"


def test_yaml_str_quotes_url():
    # URLs contain : which breaks bare YAML scalars
    result = _yaml_str("https://example.com/path")
    assert result.startswith('"') and result.endswith('"')


def test_yaml_str_quotes_hash():
    result = _yaml_str("value # comment")
    assert result.startswith('"')
