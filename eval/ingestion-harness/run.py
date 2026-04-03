#!/usr/bin/env python3
"""Sequential ingestion workbench — Layer 3 of the integration-quality strategy.

Ingests the 20 development papers one at a time, snapshotting the full store
state after each paper.  Enables rewind-and-replay for debugging accumulation
failures.

Directory layout (relative to this file):
  papers/          20 .txt files, one per paper
  metadata/        20 .json files with title, abstract, url etc.
  papers.json      ordered list of 20 arxiv IDs
  snapshots/       per-paper state (gitignored)
    00_initial/    notes/ + index.db before any papers
    01_2510.04851/ notes/ + index.db + result.json + report.md + paper.log
    ...
    progress.json  which papers have been completed

Usage:
  uv run --env-file .env python eval/ingestion-harness/run.py --status
  uv run --env-file .env python eval/ingestion-harness/run.py --list
  uv run --env-file .env python eval/ingestion-harness/run.py --next
  uv run --env-file .env python eval/ingestion-harness/run.py --paper 3
  uv run --env-file .env python eval/ingestion-harness/run.py --rewind 3
  uv run --env-file .env python eval/ingestion-harness/run.py --context
  uv run --env-file .env python eval/ingestion-harness/run.py --context 5
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
PAPERS_JSON = HERE / "papers.json"
PAPERS_DIR = HERE / "papers"
METADATA_DIR = HERE / "metadata"
SNAPSHOTS_DIR = HERE / "snapshots"
STORE_NOTES_DIR = HERE / "store" / "notes"
STORE_INDEX = HERE / "store" / "index.db"
PROGRESS_FILE = SNAPSHOTS_DIR / "progress.json"

log = logging.getLogger("harness")


# ---------------------------------------------------------------------------
# Pure helpers (importable by tests)
# ---------------------------------------------------------------------------


def _current_position(progress: dict) -> int:
    """Number of papers completed so far."""
    return len(progress.get("completed", []))


def _snapshot_name(n: int, paper_id: str) -> str:
    """Directory name for snapshot N.  e.g. '01_2510.04851'."""
    return f"{n:02d}_{paper_id}"


def _detect_duplicate_titles(
    notes_before: list[tuple[str, str]],
    notes_after: list[tuple[str, str]],
) -> list[str]:
    """Return titles of notes created *after* that share a title with any other note.

    *notes_before* and *notes_after* are lists of (id, title) pairs.
    Only newly created notes (ids not in notes_before) are checked for collisions.
    """
    ids_before = {nid for nid, _ in notes_before}
    titles_all_after = [title for _, title in notes_after]
    title_counts = Counter(titles_all_after)

    new_notes = [(nid, title) for nid, title in notes_after if nid not in ids_before]
    duplicates: list[str] = []
    for _, title in new_notes:
        if title_counts[title] > 1 and title not in duplicates:
            duplicates.append(title)
    return duplicates


def _operation_summary(results: list) -> str:
    """Compact op distribution string.  e.g. 'CREATE×1 SPLIT×2 UPDATE×3'."""
    if not results:
        return "(none)"
    counts = Counter(r.operation for r in results)
    return " ".join(f"{op}×{n}" for op, n in sorted(counts.items()))


def _low_confidence_ops(results: list, threshold: float = 0.7) -> list:
    """Return results whose confidence is below *threshold*."""
    return [r for r in results if r.confidence < threshold]


def _take_snapshot(
    n: int,
    paper_id: str,
    notes_dir: Path,
    index_path: Path,
    snaps_dir: Path,
) -> Path:
    """Copy store state to snapshots/<name>/.  Returns the snapshot directory."""
    snap_dir = snaps_dir / _snapshot_name(n, paper_id)
    snap_dir.mkdir(parents=True, exist_ok=True)
    # Copy notes directory (replace notes/ subtree only; preserve sibling files)
    snap_notes = snap_dir / "notes"
    if snap_notes.exists():
        shutil.rmtree(snap_notes)
    if notes_dir.exists():
        shutil.copytree(notes_dir, snap_notes)
    else:
        snap_notes.mkdir()
    # Copy index
    if index_path.exists():
        shutil.copy2(index_path, snap_dir / "index.db")
    log.debug("Snapshot taken: %s (%d notes)", snap_dir.name,
              len(list(snap_notes.glob("*.md"))))
    return snap_dir


def _restore_snapshot(
    n: int,
    paper_id: str,
    notes_dir: Path,
    index_path: Path,
    snaps_dir: Path,
) -> None:
    """Restore store state from snapshots/<name>/."""
    snap_dir = snaps_dir / _snapshot_name(n, paper_id)
    if not snap_dir.exists():
        raise FileNotFoundError(f"Snapshot not found: {snap_dir}")
    # Restore notes
    if notes_dir.exists():
        shutil.rmtree(notes_dir)
    shutil.copytree(snap_dir / "notes", notes_dir)
    # Restore index
    snap_index = snap_dir / "index.db"
    if snap_index.exists():
        shutil.copy2(snap_index, index_path)
    elif index_path.exists():
        index_path.unlink()
    log.info("Restored snapshot: %s (%d notes)", snap_dir.name,
             len(list(notes_dir.glob("*.md"))))


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------


def _load_progress() -> dict:
    SNAPSHOTS_DIR.mkdir(exist_ok=True)
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {"completed": []}


def _save_progress(progress: dict) -> None:
    SNAPSHOTS_DIR.mkdir(exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


# ---------------------------------------------------------------------------
# Store introspection
# ---------------------------------------------------------------------------


def _load_note_stubs(notes_dir: Path) -> list[tuple[str, str, str, int]]:
    """Return (id, title, type, body_len) for all notes in notes_dir."""
    import frontmatter
    stubs = []
    for p in sorted(notes_dir.glob("*.md")):
        try:
            post = frontmatter.loads(p.read_text(encoding="utf-8"))
            body = post.content.strip()
            # Extract title from first H1 if present
            title = post.get("title", "")
            if not title:
                for line in body.splitlines():
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break
            body_len = len(body)
            stubs.append((post.get("id", p.stem), title, post.get("type", "?"), body_len))
        except Exception:
            pass
    return stubs


def _load_note_embeddings(notes_dir: Path) -> dict[str, "np.ndarray"]:
    """Return {note_id: embedding_vec} for notes that have embeddings."""
    import base64, struct
    import numpy as np
    import frontmatter

    embeddings: dict[str, "np.ndarray"] = {}
    for p in notes_dir.glob("*.md"):
        try:
            post = frontmatter.loads(p.read_text(encoding="utf-8"))
            raw = post.get("embedding")
            if raw:
                data = base64.b64decode(str(raw))
                n = len(data) // 4
                vec = np.array(struct.unpack(f"{n}f", data), dtype=np.float32)
                note_id = post.get("id", p.stem)
                embeddings[note_id] = vec
        except Exception:
            pass
    return embeddings


def _activation_counts(index_path: Path) -> dict[str, int]:
    """Return {note_id: edge_count} from the activation graph in the index."""
    if not index_path.exists():
        return {}
    import sqlite3
    try:
        con = sqlite3.connect(index_path)
        rows = con.execute(
            "SELECT note_id, COUNT(*) FROM activation_edges GROUP BY note_id"
        ).fetchall()
        con.close()
        return {row[0]: row[1] for row in rows}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _generate_report(
    paper_meta: dict,
    results: list,
    notes_before: list[tuple[str, str, str, int]],
    notes_after: list[tuple[str, str, str, int]],
    log_content: str,
    run_at: str,
    elapsed: float,
) -> str:
    from zettelkasten.integrate import IntegrationResult

    ids_before = {nid for nid, _, _, _ in notes_before}
    ids_after = {nid for nid, _, _, _ in notes_after}
    body_len_before = {nid: blen for nid, _, _, blen in notes_before}

    arxiv_id = paper_meta["arxiv_id"]
    title = paper_meta.get("title", arxiv_id)
    abstract = paper_meta.get("abstract", "")
    url = paper_meta.get("url", f"https://arxiv.org/abs/{arxiv_id}")
    categories = ", ".join(paper_meta.get("categories", []))

    lines = [
        f"# {title}",
        f"",
        f"ArXiv: [{arxiv_id}]({url})",
        f"Run at: {run_at}  |  Elapsed: {elapsed:.0f}s",
        f"Categories: {categories}",
        f"",
        f"## Abstract",
        f"",
        abstract,
        f"",
        f"---",
        f"",
        f"## Store State Before ({len(notes_before)} notes)",
        f"",
    ]
    if notes_before:
        lines.append("| ID | Title | Type | Body |")
        lines.append("|----|-------|------|------|")
        for nid, t, typ, blen in notes_before:
            lines.append(f"| {nid} | {t[:50]} | {typ} | {blen} |")
    else:
        lines.append("*(empty corpus)*")
    lines.append("")

    # Hot notes (body > 4000 or high activation)
    hot = [(nid, t, blen) for nid, t, _, blen in notes_before if blen > 4000]
    if hot:
        lines += ["**Hot notes** (body > 4000 chars):", ""]
        for nid, t, blen in hot:
            lines.append(f"- {nid}  {t[:60]}  ({blen} chars)")
        lines.append("")

    lines += [
        "---",
        "",
        "## Integration Results",
        "",
    ]

    for r in results:
        op = r.operation
        lines.append(f"### {r.note_title or r.reasoning[:60] or op}")
        lines.append("")
        lines.append(f"**Operation**: {op}  |  **Confidence**: {r.confidence:.2f}")
        if r.reasoning:
            lines.append(f"**Reasoning**: {r.reasoning}")
        if r.l1_target_ids:
            lines.append(f"**L1 targets**: {', '.join(r.l1_target_ids)}")
        if r.target_ids:
            lines.append(f"**L2 targets**: {', '.join(r.target_ids)}")
        note_id = getattr(r, "note_id", "")
        if note_id:
            before_len = body_len_before.get(note_id)
            after_stub = next((s for s in notes_after if s[0] == note_id), None)
            after_len = after_stub[3] if after_stub else None
            if before_len and after_len:
                delta = after_len - before_len
                sign = "+" if delta >= 0 else ""
                lines.append(f"**Note**: {note_id} | body {before_len} → {after_len} ({sign}{delta})")
            elif after_len:
                lines.append(f"**Note**: {note_id} | body {after_len} chars (new)")
        if op == "SPLIT" and r.split_title:
            lines.append(f'**Split second half**: "{r.split_title}"  ({len(r.split_body)} chars)')
        lines.append("")

    # Store changes summary
    new_ids = ids_after - ids_before
    modified_ids = {
        nid for nid in ids_before & ids_after
        if body_len_before.get(nid, 0) != next((blen for i, _, _, blen in notes_after if i == nid), 0)
    }
    lines += [
        "---",
        "",
        "## Store Changes",
        "",
        f"New notes: {len(new_ids)}",
    ]
    for nid, t, typ, blen in notes_after:
        if nid in new_ids:
            lines.append(f"- {nid}  {t[:60]}  ({blen} chars)")
    lines.append(f"\nModified notes: {len(modified_ids)}")
    for nid, t, typ, blen in notes_after:
        if nid in modified_ids:
            before = body_len_before.get(nid, 0)
            delta = blen - before
            sign = "+" if delta >= 0 else ""
            lines.append(f"- {nid}  {t[:60]}  ({before} → {blen}, {sign}{delta})")
    lines.append("")

    # Operation summary
    lines += [
        "---",
        "",
        "## Operation Summary",
        "",
        _operation_summary(results),
        "",
    ]

    # Duplicate title detection
    before_pairs = [(nid, t) for nid, t, _, _ in notes_before]
    after_pairs = [(nid, t) for nid, t, _, _ in notes_after]
    dups = _detect_duplicate_titles(before_pairs, after_pairs)
    lines += ["## Duplicate Title Check", ""]
    if dups:
        lines.append("⚠️  Duplicate titles detected:")
        for d in dups:
            lines.append(f"  - {d!r}")
    else:
        lines.append("No duplicate titles.")
    lines.append("")

    # Confidence distribution
    confidences = [r.confidence for r in results]
    low_conf = _low_confidence_ops(results)
    if confidences:
        lines += [
            "## Confidence Distribution",
            "",
            f"Min: {min(confidences):.2f}  Mean: {sum(confidences)/len(confidences):.2f}  Max: {max(confidences):.2f}",
        ]
        if low_conf:
            lines.append(f"\nLow confidence (< 0.7):")
            for r in low_conf:
                lines.append(f"  - {r.operation} conf={r.confidence:.2f}  {r.note_title or r.reasoning[:50]}")
        lines.append("")

    # SPLIT details
    splits = [r for r in results if r.operation == "SPLIT" and r.split_title]
    if splits:
        lines += ["## SPLIT Details", ""]
        for r in splits:
            body1_len = len(r.note_body)
            body2_len = len(r.split_body)
            note_id = getattr(r, "note_id", "")
            orig_len = body_len_before.get(note_id, body1_len + body2_len)
            combined = body1_len + body2_len
            ratio = combined / orig_len if orig_len else 0
            lines.append(f"- Source ({note_id}): {orig_len} chars")
            lines.append(f'  First half "{r.note_title}": {body1_len} chars')
            lines.append(f'  Second half "{r.split_title}": {body2_len} chars')
            lines.append(f"  Combined: {combined} chars ({ratio:.0%} of original)")
        lines.append("")

    # §4.7 cosine similarity data from DEBUG log
    cosine_lines = [
        ln for ln in log_content.splitlines()
        if "integrate.cluster_cosine_sims" in ln
    ]
    if cosine_lines:
        lines += ["## Cluster Cosine Similarities (§4.7)", ""]
        for ln in cosine_lines:
            # Extract just the data portion after the logger prefix
            idx = ln.find("integrate.cluster_cosine_sims")
            lines.append(f"    {ln[idx:]}" if idx >= 0 else f"    {ln}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Context output (--context)
# ---------------------------------------------------------------------------


def _generate_context(
    paper_n: int,
    papers: list[str],
    metadata: dict[str, dict],
    notes_before: list[tuple[str, str, str, int]],
    abstract_sims: list[tuple[str, str, float]] | None,
    recent_history: list[dict],
) -> str:
    """Build the pre-ingestion context block for human/Claude review."""
    arxiv_id = papers[paper_n - 1]
    meta = metadata.get(arxiv_id, {})
    title = meta.get("title", arxiv_id)
    abstract = meta.get("abstract", "")
    url = meta.get("url", f"https://arxiv.org/abs/{arxiv_id}")
    categories = ", ".join(meta.get("categories", []))

    lines = [
        f"{'=' * 60}",
        f"CONTEXT: Paper {paper_n}/{len(papers)} — {arxiv_id}",
        f"{'=' * 60}",
        f"",
        f"PAPER",
        f"  Title:    {title}",
        f"  ArXiv:    {url}",
        f"  Category: {categories}",
        f"",
        f"  Abstract:",
    ]
    for para in abstract.split("\n"):
        if para.strip():
            lines.append(f"  {para.strip()}")
    lines.append("")

    lines += [
        f"CURRENT STORE  ({len(notes_before)} notes after paper {paper_n - 1})",
        "",
        f"  {'ID':<16} {'Title':<50} {'Type':<12} {'Body':>6}",
        f"  {'-'*16} {'-'*50} {'-'*12} {'-'*6}",
    ]
    for nid, t, typ, blen in notes_before:
        lines.append(f"  {nid:<16} {t[:50]:<50} {typ:<12} {blen:>6}")
    lines.append("")

    hot = [(nid, t, blen) for nid, t, _, blen in notes_before if blen > 4000]
    if hot:
        lines += ["  HOT NOTES (body > 4000 chars):"]
        for nid, t, blen in hot:
            lines.append(f"    {nid}  {t[:55]}  ({blen} chars)")
        lines.append("")

    if abstract_sims:
        lines += [
            "EMBEDDING SIMILARITY TO PAPER ABSTRACT (body signal, no LLM)",
            "",
            f"  {'ID':<16} {'Title':<50} {'Sim':>6}",
            f"  {'-'*16} {'-'*50} {'-'*6}",
        ]
        for nid, t, sim in abstract_sims[:15]:
            lines.append(f"  {nid:<16} {t[:50]:<50} {sim:>6.3f}")
        lines.append("")

    if recent_history:
        lines += ["OPERATION HISTORY (last papers):", ""]
        for entry in recent_history:
            lines.append(
                f"  Paper {entry['n']:>2}  {entry['arxiv_id']}  {entry['summary']}"
            )
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def _setup_logging(paper_log_path: Path | None = None) -> None:
    fmt = "%(asctime)s %(levelname)-8s %(name)-12s %(message)s"
    datefmt = "%H:%M:%S"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Suppress noisy third-party loggers
    for noisy in ("httpx", "anthropic", "anthropic._base_client", "voyageai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if not root.handlers:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter(fmt, datefmt))
        root.addHandler(ch)

    if paper_log_path is not None:
        paper_log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(paper_log_path, mode="w", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(fmt, datefmt))
        root.addHandler(fh)
        return fh
    return None


def _remove_handler(handler) -> None:
    if handler is not None:
        logging.getLogger().removeHandler(handler)
        handler.close()


# ---------------------------------------------------------------------------
# Ingest runner
# ---------------------------------------------------------------------------


def _run_paper(
    arxiv_id: str,
    notes_dir: Path,
    index_path: Path,
    llm,
    embed,
    fast_llm,
) -> list:
    from zettelkasten.store import ZettelkastenStore
    notes_dir.mkdir(parents=True, exist_ok=True)
    store = ZettelkastenStore(notes_dir=notes_dir, index_path=index_path)
    txt_path = PAPERS_DIR / f"{arxiv_id}.txt"
    text = txt_path.read_text(encoding="utf-8")
    meta = json.loads((METADATA_DIR / f"{arxiv_id}.json").read_text())
    log.info("Ingesting %s  %s  (%d chars)", arxiv_id, meta.get("title", "")[:55], len(text))
    return store.ingest_text(text, llm, embed, source=meta.get("url", arxiv_id), fast_llm=fast_llm)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_status(papers: list[str], progress: dict) -> None:
    pos = _current_position(progress)
    print(f"Position: {pos}/{len(papers)}")
    if pos < len(papers):
        next_id = papers[pos]
        meta = json.loads((METADATA_DIR / f"{next_id}.json").read_text())
        print(f"Next paper: {next_id}  {meta.get('title', '')[:60]}")
    else:
        print("All papers completed.")


def cmd_list(papers: list[str], progress: dict) -> None:
    completed = set(progress.get("completed", []))
    timestamps = progress.get("timestamps", {})
    print(f"{'#':>3}  {'ArXiv ID':<15} {'Status':<10} {'Title'}")
    print(f"{'---':>3}  {'-'*15} {'-'*10} {'-'*50}")
    for i, arxiv_id in enumerate(papers, 1):
        status = "DONE" if arxiv_id in completed else ("NEXT" if i == _current_position(progress) + 1 else "-")
        meta = json.loads((METADATA_DIR / f"{arxiv_id}.json").read_text())
        ts = timestamps.get(arxiv_id, "")
        print(f"{i:>3}  {arxiv_id:<15} {status:<10} {meta.get('title', '')[:55]}")


def cmd_context(paper_n: int, papers: list[str], progress: dict) -> None:
    """Emit the pre-ingestion context block for paper_n (1-indexed)."""
    arxiv_id = papers[paper_n - 1]

    metadata = {
        aid: json.loads((METADATA_DIR / f"{aid}.json").read_text())
        for aid in papers
    }

    notes_before = _load_note_stubs(STORE_NOTES_DIR) if STORE_NOTES_DIR.exists() else []

    # Embedding similarity — one embed call on the paper abstract
    abstract_sims: list[tuple[str, str, float]] | None = None
    if notes_before:
        try:
            import numpy as np
            from zettelkasten.config import load_config, build_embed
            cfg = load_config()
            embed = build_embed(cfg)
            abstract = metadata[arxiv_id].get("abstract", "")
            if abstract:
                q_vec = np.array(embed.embed([abstract], input_type="query")[0], dtype=np.float32)
                q_norm = float(np.linalg.norm(q_vec))
                if q_norm > 1e-9:
                    q_unit = q_vec / q_norm
                    stored_embs = _load_note_embeddings(STORE_NOTES_DIR)
                    id_to_title = {nid: t for nid, t, _, _ in notes_before}
                    sims = []
                    for nid, emb in stored_embs.items():
                        e_norm = float(np.linalg.norm(emb))
                        if e_norm > 1e-9:
                            sim = float(np.dot(emb / e_norm, q_unit))
                            sims.append((nid, id_to_title.get(nid, nid), sim))
                    sims.sort(key=lambda x: -x[2])
                    abstract_sims = sims
        except Exception as exc:
            log.warning("Could not compute embedding similarities: %s", exc)

    # Recent operation history from completed snapshots
    completed = progress.get("completed", [])
    recent_history = []
    for i, cid in enumerate(completed[-5:], start=max(1, len(completed) - 4)):
        snap_dir = SNAPSHOTS_DIR / _snapshot_name(i, cid)
        result_path = snap_dir / "result.json"
        if result_path.exists():
            data = json.loads(result_path.read_text())
            summary = _operation_summary_from_dicts(data)
            recent_history.append({"n": i, "arxiv_id": cid, "summary": summary})

    print(_generate_context(paper_n, papers, metadata, notes_before, abstract_sims, recent_history))


def _operation_summary_from_dicts(results_data: list[dict]) -> str:
    if not results_data:
        return "(none)"
    counts = Counter(r["operation"] for r in results_data)
    return " ".join(f"{op}×{n}" for op, n in sorted(counts.items()))


def cmd_next(papers: list[str], progress: dict) -> None:
    pos = _current_position(progress)
    if pos >= len(papers):
        print("All papers already completed.")
        return

    arxiv_id = papers[pos]
    paper_n = pos + 1
    snap_name = _snapshot_name(paper_n, arxiv_id)
    snap_dir = SNAPSHOTS_DIR / snap_name

    # First run: take initial snapshot of empty store
    if pos == 0:
        initial_snap = SNAPSHOTS_DIR / _snapshot_name(0, "initial")
        if not initial_snap.exists():
            STORE_NOTES_DIR.mkdir(parents=True, exist_ok=True)
            _take_snapshot(0, "initial", STORE_NOTES_DIR, STORE_INDEX, SNAPSHOTS_DIR)
            log.info("Initial snapshot taken.")

    # Set up per-paper file logger
    snap_dir.mkdir(parents=True, exist_ok=True)
    paper_log_path = snap_dir / "paper.log"
    file_handler = _setup_logging(paper_log_path)

    notes_before = _load_note_stubs(STORE_NOTES_DIR) if STORE_NOTES_DIR.exists() else []

    try:
        from zettelkasten.config import load_config, build_llm, build_fast_llm, build_embed
        cfg = load_config()
        llm = build_llm(cfg)
        fast_llm = build_fast_llm(cfg)
        embed = build_embed(cfg)

        t_start = time.monotonic()
        results = _run_paper(arxiv_id, STORE_NOTES_DIR, STORE_INDEX, llm, embed, fast_llm)
        elapsed = time.monotonic() - t_start

        log.info("Paper %d/%d complete in %.0fs — %s",
                 paper_n, len(papers), elapsed, _operation_summary(results))

    except KeyboardInterrupt:
        log.warning("Interrupted — store state may be inconsistent. Consider --rewind %d.", paper_n)
        _remove_handler(file_handler)
        raise
    except Exception:
        log.error("Ingestion failed:\n%s", traceback.format_exc())
        _remove_handler(file_handler)
        raise

    _remove_handler(file_handler)

    notes_after = _load_note_stubs(STORE_NOTES_DIR)

    # Serialize results
    result_data = [
        {
            "operation": r.operation,
            "note_title": r.note_title,
            "split_title": r.split_title,
            "note_id": getattr(r, "note_id", ""),
            "target_ids": r.target_ids,
            "l1_target_ids": r.l1_target_ids,
            "confidence": r.confidence,
            "reasoning": r.reasoning,
        }
        for r in results
    ]
    (snap_dir / "result.json").write_text(json.dumps(result_data, indent=2))

    # Generate report
    log_content = paper_log_path.read_text(encoding="utf-8") if paper_log_path.exists() else ""
    meta = json.loads((METADATA_DIR / f"{arxiv_id}.json").read_text())
    run_at = datetime.now(tz=timezone.utc).isoformat()
    report = _generate_report(meta, results, notes_before, notes_after, log_content, run_at, elapsed)
    (snap_dir / "report.md").write_text(report, encoding="utf-8")

    # Take post-paper snapshot (store state after this paper)
    _take_snapshot(paper_n, arxiv_id, STORE_NOTES_DIR, STORE_INDEX, SNAPSHOTS_DIR)

    # Update progress
    if arxiv_id not in progress["completed"]:
        progress["completed"].append(arxiv_id)
    progress.setdefault("timestamps", {})[arxiv_id] = run_at
    _save_progress(progress)

    print(f"\nPaper {paper_n}/{len(papers)} done: {arxiv_id}")
    print(f"Operations: {_operation_summary(results)}")
    dups = _detect_duplicate_titles(
        [(nid, t) for nid, t, _, _ in notes_before],
        [(nid, t) for nid, t, _, _ in notes_after],
    )
    if dups:
        print(f"⚠️  Duplicate titles: {dups}")
    print(f"Report: {snap_dir / 'report.md'}")


def cmd_rewind(paper_n: int, papers: list[str], progress: dict) -> None:
    """Restore store to the state before paper_n (i.e. after paper_n-1)."""
    pos = _current_position(progress)
    if paper_n < 1 or paper_n > pos:
        print(f"Cannot rewind to {paper_n}: current position is {pos}.")
        return

    target_n = paper_n - 1
    if target_n == 0:
        target_id = "initial"
    else:
        target_id = papers[target_n - 1]

    answer = input(
        f"Rewind to pre-paper-{paper_n} state (snapshot {_snapshot_name(target_n, target_id)})? "
        f"This will overwrite the current store. [y/N] "
    ).strip().lower()
    if answer != "y":
        print("Aborted.")
        return

    _restore_snapshot(target_n, target_id, STORE_NOTES_DIR, STORE_INDEX, SNAPSHOTS_DIR)

    # Trim progress
    progress["completed"] = papers[:target_n]
    _save_progress(progress)
    print(f"Rewound to paper {target_n}. Next paper will be #{paper_n}: {papers[paper_n - 1]}")


def cmd_paper(paper_n: int, papers: list[str], progress: dict) -> None:
    """Run a specific paper, rewinding first if it has already been run."""
    pos = _current_position(progress)
    if paper_n < 1 or paper_n > len(papers):
        print(f"Paper {paper_n} out of range (1–{len(papers)}).")
        return
    if paper_n > pos + 1:
        print(f"Cannot jump to paper {paper_n}: current position is {pos}. Run sequentially.")
        return
    if paper_n <= pos:
        answer = input(
            f"Paper {paper_n} has already been run. Rewind to pre-paper-{paper_n} state and re-run? [y/N] "
        ).strip().lower()
        if answer != "y":
            print("Aborted.")
            return
        # Rewind without asking again
        target_n = paper_n - 1
        target_id = "initial" if target_n == 0 else papers[target_n - 1]
        _restore_snapshot(target_n, target_id, STORE_NOTES_DIR, STORE_INDEX, SNAPSHOTS_DIR)
        progress["completed"] = papers[:target_n]
        _save_progress(progress)
        log.info("Rewound to pre-paper-%d state.", paper_n)

    cmd_next(papers, progress)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sequential ingestion workbench — replay 20 papers one at a time."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--status", action="store_true", help="Show current position")
    group.add_argument("--list", action="store_true", help="List all papers with status")
    group.add_argument("--next", action="store_true", help="Ingest the next paper")
    group.add_argument("--paper", type=int, metavar="N", help="Run paper N (rewinds if needed)")
    group.add_argument("--rewind", type=int, metavar="N", help="Restore store to pre-paper-N state")
    group.add_argument("--context", nargs="?", const=-1, type=int, metavar="N",
                       help="Show pre-ingestion context for paper N (default: next)")
    args = parser.parse_args()

    _setup_logging()

    papers: list[str] = json.loads(PAPERS_JSON.read_text())
    progress = _load_progress()

    if args.status:
        cmd_status(papers, progress)
    elif args.list:
        cmd_list(papers, progress)
    elif args.next:
        cmd_next(papers, progress)
    elif args.paper is not None:
        cmd_paper(args.paper, papers, progress)
    elif args.rewind is not None:
        cmd_rewind(args.rewind, papers, progress)
    elif args.context is not None:
        n = args.context if args.context != -1 else _current_position(progress) + 1
        if n < 1 or n > len(papers):
            print(f"Paper {n} out of range (1–{len(papers)}).")
            sys.exit(1)
        cmd_context(n, papers, progress)


if __name__ == "__main__":
    main()
