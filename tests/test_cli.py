"""Tests for the zettelkasten CLI."""
from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from zettelkasten.cli import app
from zettelkasten.config import load_config

runner = CliRunner()


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


def test_init_creates_toml(tmp_path):
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "zettelkasten.toml").exists()


def test_init_creates_notes_dir(tmp_path):
    runner.invoke(app, ["init", str(tmp_path)])
    assert (tmp_path / "knowledge").is_dir()


def test_init_toml_is_valid(tmp_path):
    runner.invoke(app, ["init", str(tmp_path)])
    with open(tmp_path / "zettelkasten.toml", "rb") as fh:
        cfg = tomllib.load(fh)
    assert "zettelkasten" in cfg
    assert "llm" in cfg
    assert "embed" in cfg


def test_init_idempotent(tmp_path):
    runner.invoke(app, ["init", str(tmp_path)])
    result = runner.invoke(app, ["init", str(tmp_path)])
    # Second run should succeed without error
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# rebuild-index
# ---------------------------------------------------------------------------


def test_rebuild_index_empty_dir(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    toml = tmp_path / "zettelkasten.toml"
    toml.write_text(
        f'[zettelkasten]\nnotes_dir = "{notes_dir}"\nindex_path = "{tmp_path / "k.db"}"\n'
        '[llm]\nprovider = "anthropic"\nmodel = "x"\napi_key = ""\n'
        '[embed]\nprovider = "voyage"\nmodel = "y"\napi_key = ""\n',
        encoding="utf-8",
    )
    result = runner.invoke(app, ["rebuild-index", "--config", str(toml)])
    assert result.exit_code == 0


def test_rebuild_index_missing_notes_dir(tmp_path):
    toml = tmp_path / "zettelkasten.toml"
    toml.write_text(
        f'[zettelkasten]\nnotes_dir = "{tmp_path / "missing"}"\nindex_path = "{tmp_path / "k.db"}"\n'
        '[llm]\nprovider = "anthropic"\nmodel = "x"\napi_key = ""\n'
        '[embed]\nprovider = "voyage"\nmodel = "y"\napi_key = ""\n',
        encoding="utf-8",
    )
    result = runner.invoke(app, ["rebuild-index", "--config", str(toml)])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# config loading
# ---------------------------------------------------------------------------


def test_load_config_defaults():
    cfg = load_config("/nonexistent/zettelkasten.toml")
    assert cfg["zettelkasten"]["notes_dir"] == "knowledge"
    assert cfg["llm"]["provider"] == "anthropic"
    assert cfg["embed"]["provider"] == "voyage"


def test_load_config_from_file(tmp_path):
    toml = tmp_path / "zettelkasten.toml"
    toml.write_text(
        '[zettelkasten]\nnotes_dir = "my_notes"\nindex_path = "my.db"\n'
        '[llm]\nprovider = "anthropic"\nmodel = "claude-opus-4-6"\napi_key = ""\n'
        '[embed]\nprovider = "voyage"\nmodel = "voyage-3"\napi_key = ""\n',
        encoding="utf-8",
    )
    cfg = load_config(toml)
    assert cfg["zettelkasten"]["notes_dir"] == "my_notes"


def test_load_config_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("ZETTELKASTEN_NOTES_DIR", "/custom/notes")
    cfg = load_config("/nonexistent.toml")
    assert cfg["zettelkasten"]["notes_dir"] == "/custom/notes"


def test_load_config_anthropic_api_key_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
    cfg = load_config("/nonexistent.toml")
    assert cfg["llm"]["api_key"] == "test-key-123"


def test_load_config_voyage_api_key_env(monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "voyage-key-456")
    cfg = load_config("/nonexistent.toml")
    assert cfg["embed"]["api_key"] == "voyage-key-456"


def test_load_config_has_inbox_dir_default():
    cfg = load_config("/nonexistent.toml")
    assert cfg["zettelkasten"]["inbox_dir"] == "inbox"


# ---------------------------------------------------------------------------
# ingest --save-only
# ---------------------------------------------------------------------------


def _make_toml(tmp_path):
    inbox_dir = tmp_path / "inbox"
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    toml = tmp_path / "zettelkasten.toml"
    toml.write_text(
        f'[zettelkasten]\nnotes_dir = "{notes_dir}"\nindex_path = "{tmp_path / "k.db"}"\ninbox_dir = "{inbox_dir}"\n'
        '[llm]\nprovider = "anthropic"\nmodel = "claude-opus-4-6"\napi_key = ""\n'
        '[embed]\nprovider = "voyage"\nmodel = "voyage-3"\napi_key = ""\n',
        encoding="utf-8",
    )
    return toml, inbox_dir


def test_save_only_creates_inbox_file(tmp_path):
    toml, inbox_dir = _make_toml(tmp_path)
    doc = tmp_path / "article.md"
    doc.write_text("# Test\n\nSome content here.", encoding="utf-8")

    result = runner.invoke(app, ["ingest", str(doc), "--config", str(toml), "--save-only"])

    assert result.exit_code == 0
    files = list(inbox_dir.glob("*.md"))
    assert len(files) == 1


def test_save_only_file_has_frontmatter(tmp_path):
    toml, inbox_dir = _make_toml(tmp_path)
    doc = tmp_path / "article.md"
    doc.write_text("# Test\n\nSome content here.", encoding="utf-8")

    runner.invoke(app, ["ingest", str(doc), "--config", str(toml), "--save-only"])

    content = next(inbox_dir.glob("*.md")).read_text()
    assert content.startswith("---")
    assert "saved_at:" in content
    assert "content_length:" in content


def test_save_only_does_not_create_notes(tmp_path):
    toml, inbox_dir = _make_toml(tmp_path)
    notes_dir = tmp_path / "notes"
    doc = tmp_path / "article.md"
    doc.write_text("# Test\n\nSome content here.", encoding="utf-8")

    runner.invoke(app, ["ingest", str(doc), "--config", str(toml), "--save-only"])

    assert len(list(notes_dir.glob("*.md"))) == 0


def test_save_only_prints_path(tmp_path):
    toml, inbox_dir = _make_toml(tmp_path)
    doc = tmp_path / "article.md"
    doc.write_text("# Test\n\nSome content here.", encoding="utf-8")

    result = runner.invoke(app, ["ingest", str(doc), "--config", str(toml), "--save-only"])

    assert "Saved to" in result.output
