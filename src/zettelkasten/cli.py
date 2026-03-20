"""zettelkasten CLI — init / ingest / search / curate / rebuild-index."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="zettelkasten",
    help="Knowledge synthesis — Form → Gather → Integrate pipeline.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@app.command()
def init(
    directory: Path = typer.Argument(
        Path("."),
        help="Directory to initialise (defaults to current directory).",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Initialise a new zettelkasten in DIRECTORY."""
    _configure_logging(verbose)

    from .config import write_skeleton

    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)

    toml_path = directory / "zettelkasten.toml"
    if toml_path.exists():
        console.print(f"[yellow]zettelkasten.toml already exists at {toml_path}[/yellow]")
    else:
        write_skeleton(toml_path)
        console.print(f"[green]✓[/green] Created {toml_path}")

    # Create default notes directory
    notes_dir = directory / "knowledge"
    notes_dir.mkdir(exist_ok=True)
    console.print(f"[green]✓[/green] Notes directory: {notes_dir}")
    console.print("\nNext steps:")
    console.print("  1. Edit zettelkasten.toml and set your API keys")
    console.print("  2. Run: zettelkasten ingest <document.md>")


# ---------------------------------------------------------------------------
# Source fetching (file or URL)
# ---------------------------------------------------------------------------


def _fetch_source(source: str) -> tuple[str, str]:
    """Return (text, display_label) for a file path or URL."""
    if source.startswith("http://") or source.startswith("https://"):
        return _fetch_url(source), source
    path = Path(source)
    if not path.exists():
        err_console.print(f"[red]Error: file not found: {path}[/red]")
        raise typer.Exit(1)
    return path.read_text(encoding="utf-8"), path.name


def _fetch_url(url: str) -> str:
    import trafilatura

    raw = trafilatura.fetch_url(url)
    if raw is None:
        err_console.print(f"[red]Error: could not fetch {url}[/red]")
        raise typer.Exit(1)

    text = trafilatura.extract(raw, include_comments=False, include_tables=False)
    if not text:
        err_console.print(f"[red]Error: no content extracted from {url}[/red]")
        raise typer.Exit(1)

    return text


# ---------------------------------------------------------------------------
# ingest
# ---------------------------------------------------------------------------


@app.command()
def ingest(
    source: str = typer.Argument(..., help="File path or URL to ingest."),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to zettelkasten.toml"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    save_only: bool = typer.Option(False, help="Save to inbox without running the pipeline."),
) -> None:
    """Ingest a document (file path or URL) through the Form → Gather → Integrate pipeline."""
    _configure_logging(verbose)

    text, label = _fetch_source(source)

    from .config import load_config

    cfg = load_config(config)

    if save_only:
        from .inbox import save_to_inbox

        inbox_dir = Path(cfg["zettelkasten"]["inbox_dir"]).expanduser()
        saved = save_to_inbox(inbox_dir, text, source=source)
        console.print(f"[green]✓[/green] Saved to {saved}")
        return

    from .config import build_embed, build_fast_llm, build_llm, build_store

    store = build_store(cfg)
    llm = build_llm(cfg)
    fast_llm = build_fast_llm(cfg)
    embed = build_embed(cfg)

    console.print(f"Ingesting [bold]{label}[/bold] ({len(text)} chars)…")

    results = store.ingest_text(text, llm, embed, source=source, fast_llm=fast_llm)

    table = Table("Operation", "Note ID", "Title", "Confidence")
    for r in results:
        note_id = getattr(r, "note_id", "") or ""
        table.add_row(r.operation, note_id, r.note_title[:50], f"{r.confidence:.2f}")
    console.print(table)
    console.print(f"\n[green]Done.[/green] {len(results)} draft(s) processed.")


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query."),
    top_k: int = typer.Option(10, "--top-k", "-k", help="Number of results."),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Search the knowledge base."""
    _configure_logging(verbose)

    from .config import build_embed, build_llm, build_store, load_config

    cfg = load_config(config)
    store = build_store(cfg)
    llm = build_llm(cfg)
    embed = build_embed(cfg)

    results = store.search(query, llm, embed, top_k=top_k)
    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    table = Table("#", "ID", "Title", "Type", "Confidence")
    for i, note in enumerate(results, 1):
        table.add_row(str(i), note.id, note.title[:60], note.type, f"{note.confidence:.2f}")
    console.print(table)


# ---------------------------------------------------------------------------
# curate
# ---------------------------------------------------------------------------


@app.command()
def curate(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Show pending curation recommendations (SPLIT)."""
    _configure_logging(verbose)

    from .config import load_config
    from .index import ZettelIndex

    cfg = load_config(config)
    zk = cfg["zettelkasten"]
    index = ZettelIndex(zk["index_path"])

    console.print("[yellow]Curation is not yet automated.[/yellow]")
    console.print("SPLIT recommendations are logged during ingest.")
    console.print("Run with --verbose to see them in the ingest output.")


# ---------------------------------------------------------------------------
# rebuild-index
# ---------------------------------------------------------------------------


@app.command(name="rewrite-notes")
def rewrite_notes(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Rewrite all note files to pick up frontmatter schema changes."""
    _configure_logging(verbose)

    from .config import load_config
    from .note import ZettelNote

    cfg = load_config(config)
    notes_dir = Path(cfg["zettelkasten"]["notes_dir"]).expanduser()

    if not notes_dir.exists():
        err_console.print(f"[red]Notes directory not found: {notes_dir}[/red]")
        raise typer.Exit(1)

    paths = sorted(notes_dir.glob("*.md"))
    for p in paths:
        note = ZettelNote.from_markdown(p.read_text(encoding="utf-8"))
        p.write_text(note.to_markdown(), encoding="utf-8")

    console.print(f"[green]✓[/green] Rewrote {len(paths)} notes in {notes_dir}")


@app.command(name="rebuild-index")
def rebuild_index(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Rebuild the SQLite index from the markdown notes directory."""
    _configure_logging(verbose)

    from .config import load_config
    from .index import ZettelIndex

    cfg = load_config(config)
    zk = cfg["zettelkasten"]
    notes_dir = Path(zk["notes_dir"])
    index_path = Path(zk["index_path"])

    if not notes_dir.exists():
        err_console.print(f"[red]Notes directory not found: {notes_dir}[/red]")
        raise typer.Exit(1)

    console.print(f"Rebuilding index from [bold]{notes_dir}[/bold]…")
    index = ZettelIndex(index_path)
    index.rebuild_from_directory(notes_dir)
    n = len(list(notes_dir.glob("*.md")))
    console.print(f"[green]✓[/green] Indexed {n} notes → {index_path}")


# ---------------------------------------------------------------------------
# serve
# ---------------------------------------------------------------------------


@app.command()
def serve(
    port: int = typer.Option(7842, "--port", "-p", help="Port to listen on."),
    host: str = typer.Option("127.0.0.1", "--host", help="Interface to bind."),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    save_only: bool = typer.Option(False, help="Save documents to inbox without running the pipeline."),
) -> None:
    """Start a local ingest server for the Chrome extension."""
    _configure_logging(verbose)

    from .config import build_embed, build_fast_llm, build_llm, build_store, load_config
    from .server import make_server

    cfg = load_config(config)
    store = build_store(cfg)
    llm = build_llm(cfg)
    fast_llm = build_fast_llm(cfg)
    embed = build_embed(cfg)
    inbox_dir = Path(cfg["zettelkasten"]["inbox_dir"]).expanduser()

    console.print(f"[green]✓[/green] Listening on http://{host}:{port}  (Ctrl+C to stop)")
    console.print(f"[green]✓[/green] Saving documents to {inbox_dir}")
    if save_only:
        console.print("[yellow]Save-only mode: documents will be archived but not processed.[/yellow]")

    server = make_server(store, llm, embed, host=host, port=port, fast_llm=fast_llm, inbox_dir=inbox_dir, save_only=save_only)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped.[/yellow]")
        server.server_close()


# ---------------------------------------------------------------------------
# bookmarklet
# ---------------------------------------------------------------------------


@app.command()
def bookmarklet(
    port: int = typer.Option(7842, "--port", "-p", help="Port the server listens on."),
) -> None:
    """Print the bookmarklet JavaScript for the given server port."""
    from .server import bookmarklet_js

    console.print(bookmarklet_js(port))
