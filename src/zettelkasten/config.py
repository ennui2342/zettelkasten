"""Configuration loading for the zettelkasten CLI.

Reads zettelkasten.toml from the current directory (or the path given by
--config).  Values can be overridden by environment variables:

  ZETTELKASTEN_NOTES_DIR      → zettelkasten.notes_dir
  ZETTELKASTEN_INDEX_PATH     → zettelkasten.index_path
  ANTHROPIC_API_KEY           → llm.api_key  (when provider = "anthropic")
  VOYAGE_API_KEY              → embed.api_key (when provider = "voyage")

A zettelkasten.toml skeleton:

  [zettelkasten]
  notes_dir  = "knowledge"
  index_path = "knowledge.db"

  [llm]
  provider = "anthropic"
  model    = "claude-opus-4-6"
  api_key  = ""          # set ANTHROPIC_API_KEY env var instead

  [embed]
  provider = "voyage"
  model    = "voyage-3"
  api_key  = ""          # set VOYAGE_API_KEY env var instead
"""
from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

_DEFAULTS: dict[str, Any] = {
    "zettelkasten": {
        "notes_dir": "knowledge",
        "index_path": "knowledge.db",
        "inbox_dir": "inbox",
    },
    "llm": {
        "provider": "anthropic",
        "model": "claude-opus-4-6",
        "fast_model": "claude-haiku-4-5-20251001",
        "api_key": "",
    },
    "embed": {
        "provider": "voyage",
        "model": "voyage-3",
        "api_key": "",
    },
}

_TOML_SKELETON = """\
[zettelkasten]
notes_dir  = "knowledge"
index_path = "knowledge.db"
inbox_dir  = "inbox"

[llm]
provider = "anthropic"
model    = "claude-opus-4-6"
api_key  = ""          # set ANTHROPIC_API_KEY env var instead

[embed]
provider = "voyage"
model    = "voyage-3"
api_key  = ""          # set VOYAGE_API_KEY env var instead
"""


def load_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """Load configuration from *config_path* (defaults to ``zettelkasten.toml``).

    Returns a merged config dict with defaults filled in.
    """
    cfg: dict[str, Any] = {
        section: dict(values)
        for section, values in _DEFAULTS.items()
    }

    if config_path is None:
        config_path = Path("zettelkasten.toml")
    else:
        config_path = Path(config_path).expanduser()

    if config_path.exists():
        with open(config_path, "rb") as fh:
            file_cfg = tomllib.load(fh)
        for section, values in file_cfg.items():
            if section in cfg:
                cfg[section].update(values)
            else:
                cfg[section] = values

    # Environment variable overrides
    if v := os.environ.get("ZETTELKASTEN_NOTES_DIR"):
        cfg["zettelkasten"]["notes_dir"] = v
    if v := os.environ.get("ZETTELKASTEN_INDEX_PATH"):
        cfg["zettelkasten"]["index_path"] = v
    if v := os.environ.get("ANTHROPIC_API_KEY"):
        if cfg["llm"]["provider"] == "anthropic":
            cfg["llm"]["api_key"] = v
    if v := os.environ.get("VOYAGE_API_KEY"):
        if cfg["embed"]["provider"] == "voyage":
            cfg["embed"]["api_key"] = v

    return cfg


def build_store(cfg: dict[str, Any]):
    """Instantiate a :class:`~zettelkasten.store.ZettelkastenStore` from *cfg*."""
    from .store import ZettelkastenStore
    zk = cfg["zettelkasten"]
    return ZettelkastenStore(
        notes_dir=Path(zk["notes_dir"]).expanduser(),
        index_path=Path(zk["index_path"]).expanduser(),
    )


def build_llm(cfg: dict[str, Any]):
    """Instantiate an LLMProvider from *cfg*."""
    llm_cfg = cfg["llm"]
    provider = llm_cfg.get("provider", "anthropic")
    if provider == "anthropic":
        from .providers import AnthropicLLM
        return AnthropicLLM(model=llm_cfg["model"], api_key=llm_cfg["api_key"])
    raise ValueError(f"Unknown LLM provider {provider!r}")


def build_fast_llm(cfg: dict[str, Any]):
    """Instantiate a fast (Haiku) LLMProvider from *cfg*."""
    llm_cfg = cfg["llm"]
    provider = llm_cfg.get("provider", "anthropic")
    if provider == "anthropic":
        from .providers import AnthropicLLM
        return AnthropicLLM(model=llm_cfg["fast_model"], api_key=llm_cfg["api_key"])
    raise ValueError(f"Unknown LLM provider {provider!r}")


def build_embed(cfg: dict[str, Any]):
    """Instantiate an EmbedProvider from *cfg*."""
    embed_cfg = cfg["embed"]
    provider = embed_cfg.get("provider", "voyage")
    if provider == "voyage":
        from .providers import VoyageEmbed
        return VoyageEmbed(model=embed_cfg["model"], api_key=embed_cfg["api_key"])
    raise ValueError(f"Unknown embed provider {provider!r}")


def write_skeleton(path: Path) -> None:
    """Write a zettelkasten.toml skeleton to *path*."""
    path.write_text(_TOML_SKELETON, encoding="utf-8")
