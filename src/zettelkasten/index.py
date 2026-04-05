"""SQLite index for the zettelkasten — notes, activation."""
from __future__ import annotations

import sqlite3
from itertools import combinations
from pathlib import Path
from typing import Any

from .note import ZettelNote

# Fraction of activation weight retained per ingestion event.
# factor=0.95 → half-life ≈ 14 papers; asymptotic ceiling for a
# constantly-activated note = 1.0 / (1 - factor) = 20.
ACTIVATION_DECAY_FACTOR = 0.95


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
                    confidence    REAL NOT NULL,
                    created       TEXT NOT NULL,
                    updated       TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS meta (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS activation (
                    note_a       TEXT NOT NULL,
                    note_b       TEXT NOT NULL,
                    weight       REAL NOT NULL DEFAULT 0.0,
                    ingestion_at INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (note_a, note_b)
                );

                CREATE INDEX IF NOT EXISTS idx_activation_a ON activation(note_a);
                CREATE INDEX IF NOT EXISTS idx_activation_b ON activation(note_b);

                DROP TABLE IF EXISTS co_activations;
            """)
            # Migrations
            con.execute("DROP TABLE IF EXISTS embeddings")
            for col in ("type", "salience", "stable", "last_accessed"):
                try:
                    con.execute(f"ALTER TABLE notes DROP COLUMN {col}")
                except Exception:
                    pass  # column already absent or SQLite < 3.35
            # Migrate activation table: replace updated (TEXT) with ingestion_at (INTEGER)
            cols = {row[1] for row in con.execute("PRAGMA table_info(activation)").fetchall()}
            if "updated" in cols:
                con.executescript("""
                    ALTER TABLE activation ADD COLUMN ingestion_at INTEGER NOT NULL DEFAULT 0;
                    UPDATE activation SET ingestion_at = 0;
                    ALTER TABLE activation DROP COLUMN updated;
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
                INSERT INTO notes (id, confidence, created, updated)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    confidence    = excluded.confidence,
                    created       = excluded.created,
                    updated       = excluded.updated
                """,
                (
                    note.id,
                    note.confidence,
                    note.created.isoformat(),
                    note.updated.isoformat(),
                ),
            )
        con.close()

    def delete_note(self, note_id: str) -> None:
        """Remove a note and all its associated data from the index."""
        con = self._connect()
        with con:
            con.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            con.execute("DELETE FROM activation WHERE note_a = ? OR note_b = ?", (note_id, note_id))
        con.close()

    def get_note_row(self, note_id: str) -> dict[str, Any] | None:
        con = self._connect()
        row = con.execute(
            "SELECT * FROM notes WHERE id = ?", (note_id,)
        ).fetchone()
        con.close()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Ingestion counter
    # ------------------------------------------------------------------

    def get_ingestion_count(self) -> int:
        """Return the current ingestion event counter."""
        con = self._connect()
        row = con.execute(
            "SELECT value FROM meta WHERE key = 'ingestion_count'"
        ).fetchone()
        con.close()
        return int(row["value"]) if row else 0

    def increment_ingestion_count(self) -> int:
        """Increment the ingestion counter by one and return the new value."""
        new_count = self.get_ingestion_count() + 1
        con = self._connect()
        with con:
            con.execute(
                """
                INSERT INTO meta (key, value) VALUES ('ingestion_count', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(new_count),),
            )
        con.close()
        return new_count

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------

    def record_activation_event(
        self,
        qid: str,
        selected_ids: list[str],
        factor: float = ACTIVATION_DECAY_FACTOR,
    ) -> None:
        """Record a co-activation event with transitive expansion and event-based decay.

        Adds pairwise edges between qid and each note in selected_ids, plus
        transitive edges between all pairs in selected_ids. Existing edge weights
        are decayed by factor^(current_count - ingestion_at) before the new
        increment is added.
        """
        source_ids = [s for s in selected_ids if s != qid]
        if not source_ids:
            return

        current_count = self.get_ingestion_count()
        pairs = [(qid, s) for s in source_ids]
        pairs += list(combinations(source_ids, 2))  # transitive expansion

        con = self._connect()
        with con:
            for a, b in pairs:
                a, b = min(a, b), max(a, b)  # canonical ordering: one row per pair
                row = con.execute(
                    "SELECT weight, ingestion_at FROM activation WHERE note_a = ? AND note_b = ?",
                    (a, b),
                ).fetchone()
                if row:
                    elapsed = current_count - row["ingestion_at"]
                    effective = row["weight"] * (factor ** elapsed)
                else:
                    effective = 0.0
                con.execute(
                    """
                    INSERT INTO activation (note_a, note_b, weight, ingestion_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(note_a, note_b) DO UPDATE SET
                        weight       = excluded.weight,
                        ingestion_at = excluded.ingestion_at
                    """,
                    (a, b, effective + 1.0, current_count),
                )
        con.close()

    def get_activation_scores(
        self,
        qid: str,
        factor: float = ACTIVATION_DECAY_FACTOR,
    ) -> dict[str, float]:
        """Return activation scores for all notes co-activated with qid.

        Applies event-based decay: effective = weight * factor ** (current_count - ingestion_at).
        Returns {note_id: score} for notes with non-zero effective weight.
        """
        current_count = self.get_ingestion_count()
        con = self._connect()
        rows = con.execute(
            "SELECT note_a, note_b, weight, ingestion_at FROM activation "
            "WHERE note_a = ? OR note_b = ?",
            (qid, qid),
        ).fetchall()
        con.close()

        scores: dict[str, float] = {}
        for row in rows:
            partner = row["note_b"] if row["note_a"] == qid else row["note_a"]
            elapsed = current_count - row["ingestion_at"]
            scores[partner] = row["weight"] * (factor ** elapsed)
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
                con.execute("DELETE FROM notes WHERE id = ?", (stale_id,))
        con.close()

        for note in notes:
            self.upsert_note(note)


