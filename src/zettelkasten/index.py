"""SQLite index for the zettelkasten — notes, links, embeddings, activation."""
from __future__ import annotations

import math
import sqlite3
import struct
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np

from .note import ZettelNote

# Temporal decay constant: activation half-life ≈ 14 days.
# Tuned against retrieval ground truth once real-event timestamps are available.
ACTIVATION_LAMBDA = 0.05


class ZettelIndex:
    """Thin wrapper around a SQLite database that indexes note metadata."""

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = Path(db_path)

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self._db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        return con

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def initialise(self) -> None:
        """Create tables if they do not exist. Safe to call multiple times."""
        con = self._connect()
        with con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS notes (
                    id            TEXT PRIMARY KEY,
                    type          TEXT NOT NULL,
                    confidence    REAL NOT NULL,
                    salience      REAL NOT NULL,
                    stable        INTEGER NOT NULL DEFAULT 0,
                    created       TEXT NOT NULL,
                    updated       TEXT NOT NULL,
                    last_accessed TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS embeddings (
                    note_id TEXT PRIMARY KEY,
                    vector  BLOB NOT NULL
                );

                CREATE TABLE IF NOT EXISTS activation (
                    note_a   TEXT NOT NULL,
                    note_b   TEXT NOT NULL,
                    weight   REAL NOT NULL DEFAULT 0.0,
                    updated  TEXT NOT NULL,
                    PRIMARY KEY (note_a, note_b)
                );

                CREATE INDEX IF NOT EXISTS idx_activation_a ON activation(note_a);
                CREATE INDEX IF NOT EXISTS idx_activation_b ON activation(note_b);

                DROP TABLE IF EXISTS co_activations;
            """)
        con.close()

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    def upsert_note(self, note: ZettelNote) -> None:
        con = self._connect()
        with con:
            con.execute(
                """
                INSERT INTO notes (id, type, confidence, salience, stable, created, updated, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    type          = excluded.type,
                    confidence    = excluded.confidence,
                    salience      = excluded.salience,
                    stable        = excluded.stable,
                    created       = excluded.created,
                    updated       = excluded.updated,
                    last_accessed = excluded.last_accessed
                """,
                (
                    note.id,
                    note.type,
                    note.confidence,
                    note.salience,
                    1 if note.stable else 0,
                    note.created.isoformat(),
                    note.updated.isoformat(),
                    note.last_accessed.isoformat(),
                ),
            )
        con.close()

    def delete_note(self, note_id: str) -> None:
        """Remove a note and all its associated data from the index."""
        con = self._connect()
        with con:
            con.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            con.execute("DELETE FROM embeddings WHERE note_id = ?", (note_id,))
            con.execute("DELETE FROM activation WHERE note_a = ? OR note_b = ?", (note_id, note_id))
        con.close()

    def get_note_row(self, note_id: str) -> dict[str, Any] | None:
        con = self._connect()
        row = con.execute(
            "SELECT * FROM notes WHERE id = ?", (note_id,)
        ).fetchone()
        con.close()
        return dict(row) if row else None

    def touch_accessed(self, note_id: str, ts: datetime) -> None:
        con = self._connect()
        with con:
            con.execute(
                "UPDATE notes SET last_accessed = ? WHERE id = ?",
                (ts.isoformat(), note_id),
            )
        con.close()

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    def upsert_embedding(self, note_id: str, vector: np.ndarray) -> None:
        blob = _vec_to_blob(vector)
        con = self._connect()
        with con:
            con.execute(
                """
                INSERT INTO embeddings (note_id, vector) VALUES (?, ?)
                ON CONFLICT(note_id) DO UPDATE SET vector = excluded.vector
                """,
                (note_id, blob),
            )
        con.close()

    def get_embedding(self, note_id: str) -> np.ndarray | None:
        con = self._connect()
        row = con.execute(
            "SELECT vector FROM embeddings WHERE note_id = ?", (note_id,)
        ).fetchone()
        con.close()
        if row is None:
            return None
        return _blob_to_vec(row["vector"])

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------

    def record_activation_event(
        self,
        qid: str,
        selected_ids: list[str],
        lam: float = ACTIVATION_LAMBDA,
    ) -> None:
        """Record a co-activation event with transitive expansion and lazy decay.

        Adds pairwise edges between qid and each note in selected_ids, plus
        transitive edges between all pairs in selected_ids. Existing edge weights
        are decayed before the new increment is added.
        """
        source_ids = [s for s in selected_ids if s != qid]
        if not source_ids:
            return

        now = datetime.now(tz=timezone.utc)
        pairs = [(qid, s) for s in source_ids]
        pairs += list(combinations(source_ids, 2))  # transitive expansion

        con = self._connect()
        with con:
            for a, b in pairs:
                a, b = min(a, b), max(a, b)  # canonical ordering: one row per pair
                row = con.execute(
                    "SELECT weight, updated FROM activation WHERE note_a = ? AND note_b = ?",
                    (a, b),
                ).fetchone()
                if row:
                    elapsed_days = (now - datetime.fromisoformat(row["updated"])).total_seconds() / 86400
                    effective = row["weight"] * math.exp(-lam * elapsed_days)
                else:
                    effective = 0.0
                con.execute(
                    """
                    INSERT INTO activation (note_a, note_b, weight, updated)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(note_a, note_b) DO UPDATE SET
                        weight  = excluded.weight,
                        updated = excluded.updated
                    """,
                    (a, b, effective + 1.0, now.isoformat()),
                )
        con.close()

    def get_activation_scores(
        self,
        qid: str,
        lam: float = ACTIVATION_LAMBDA,
    ) -> dict[str, float]:
        """Return activation scores for all notes co-activated with qid.

        Applies lazy temporal decay: effective = weight * exp(-λ * elapsed_days).
        Returns {note_id: score} for notes with non-zero activation weight.
        """
        now = datetime.now(tz=timezone.utc)
        con = self._connect()
        rows = con.execute(
            "SELECT note_a, note_b, weight, updated FROM activation "
            "WHERE note_a = ? OR note_b = ?",
            (qid, qid),
        ).fetchall()
        con.close()

        scores: dict[str, float] = {}
        for row in rows:
            partner = row["note_b"] if row["note_a"] == qid else row["note_a"]
            elapsed_days = (now - datetime.fromisoformat(row["updated"])).total_seconds() / 86400
            scores[partner] = row["weight"] * math.exp(-lam * elapsed_days)
        return scores

    # ------------------------------------------------------------------
    # Rebuild
    # ------------------------------------------------------------------

    def rebuild_from_directory(self, notes_dir: Path | str) -> None:
        """Scan all .md files in notes_dir, rebuild the index from scratch.

        Note: activation edges are runtime state and are NOT rebuilt from files.
        They accumulate from integration events going forward.
        """
        notes_dir = Path(notes_dir)
        self.initialise()

        notes: list[ZettelNote] = []
        for md_file in notes_dir.glob("*.md"):
            text = md_file.read_text(encoding="utf-8")
            note = ZettelNote.from_markdown(text)
            notes.append(note)

        present_ids = {n.id for n in notes}

        con = self._connect()
        with con:
            existing_ids = {
                row[0]
                for row in con.execute("SELECT id FROM notes").fetchall()
            }
            for stale_id in existing_ids - present_ids:
                con.execute("DELETE FROM embeddings WHERE note_id = ?", (stale_id,))
                con.execute("DELETE FROM notes WHERE id = ?", (stale_id,))
        con.close()

        for note in notes:
            self.upsert_note(note)
            if note.embedding is not None:
                self.upsert_embedding(note.id, note.embedding)


# ---------------------------------------------------------------------------
# Binary helpers for vector storage
# ---------------------------------------------------------------------------


def _vec_to_blob(vec: np.ndarray) -> bytes:
    arr = vec.astype(np.float32)
    return struct.pack(f"{len(arr)}f", *arr)


def _blob_to_vec(blob: bytes) -> np.ndarray:
    n = len(blob) // 4
    return np.array(struct.unpack(f"{n}f", blob), dtype=np.float32)
