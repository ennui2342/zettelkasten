#!/usr/bin/env python3
"""Retrieval workbench — entry point.

Loads corpus, embeddings, and ground truth from the spike4 directories,
instantiates the requested signals, runs LOO evaluation via harness.run(),
and writes timestamped results to results/.

Usage:
  # All signals:
  docker compose run --rm dev python spikes/retrieval-workbench/main.py

  # Subset of signals:
  docker compose run --rm dev python spikes/retrieval-workbench/main.py body bm25_mugi activation

  # Skip API calls (use caches only, skip signals that need generation):
  docker compose run --rm dev python spikes/retrieval-workbench/main.py --no-api

Available signal names: body, bm25_mugi, bm25_keyword, activation, step_back, hyde
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# SSL cert workaround (Docker environment)
if "SSL_CERT_FILE" in os.environ and not os.path.exists(os.environ["SSL_CERT_FILE"]):
    del os.environ["SSL_CERT_FILE"]

try:
    import numpy as np
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "numpy", "-q"], check=True)
    import numpy as np

# ---------------------------------------------------------------------------
# Paths — relative to spike4 directories which hold the data
# ---------------------------------------------------------------------------

WORKBENCH_DIR = Path(__file__).parent
DATA_DIR           = WORKBENCH_DIR / "data"
EMBEDDINGS_CACHE   = DATA_DIR / "embeddings_cache.json"
GROUND_TRUTH_CACHE = DATA_DIR / "ground_truth_cache.json"
CORPUS_DIR         = DATA_DIR / "corpus"
CACHES_DIR         = WORKBENCH_DIR / "caches"
RESULTS_DIR        = WORKBENCH_DIR / "results"


# ---------------------------------------------------------------------------
# Corpus + embedding loading
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.index("---", 3)
    fm_text = text[3:end].strip()
    body = text[end + 3:].strip()
    meta: dict = {}
    for line in fm_text.splitlines():
        if ":" in line and not line.startswith(" ") and not line.startswith("-"):
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()
    return meta, body


def load_corpus() -> list[dict]:
    notes = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        text = path.read_text()
        meta, body = parse_frontmatter(text)
        if not meta.get("id"):
            continue
        notes.append({"id": meta["id"], "body": body})
    return notes


def load_embeddings(notes: list[dict]) -> tuple[list[str], np.ndarray, dict[str, int]]:
    """Returns (ids, body_mat, id_to_pos) — body_mat rows are L2-normalised.

    Cache format: {"ids": [...], "body": [[...], ...], ...}
    """
    raw = json.loads(EMBEDDINGS_CACHE.read_text())
    id_to_emb = {nid: emb for nid, emb in zip(raw["ids"], raw["body"])}

    note_id_set = {n["id"] for n in notes}
    ids = [nid for nid in raw["ids"] if nid in note_id_set]
    vecs = []
    for nid in ids:
        v = np.array(id_to_emb[nid], dtype=np.float32)
        v /= (np.linalg.norm(v) + 1e-9)
        vecs.append(v)
    body_mat = np.stack(vecs)
    id_to_pos = {nid: i for i, nid in enumerate(ids)}
    return ids, body_mat, id_to_pos


def load_events(ids: list[str]) -> list[dict]:
    """Load ground truth events, filtering to notes present in corpus.

    Cache format: {qid: [{id, operation, reason}, ...]}
    """
    id_set = set(ids)
    gt = json.loads(GROUND_TRUTH_CACHE.read_text())
    events = []
    for qid, interactions in gt.items():
        # interactions is a list of dicts with 'id', 'operation', 'reason'
        gold = [item["id"] for item in interactions
                if isinstance(item, dict) and item.get("id") in id_set]
        if gold and qid in id_set:
            events.append({"qid": qid, "gold_ids": gold})
    return events


# ---------------------------------------------------------------------------
# Signal selection
# ---------------------------------------------------------------------------

def select_signals(requested: list[str], no_api: bool):
    from signals import ALL_SIGNALS
    by_name = {cls.name: cls for cls in ALL_SIGNALS}

    if not requested:
        names = list(by_name.keys())
    else:
        names = requested

    unknown = [n for n in names if n not in by_name]
    if unknown:
        print(f"Unknown signal(s): {unknown}")
        print(f"Available: {list(by_name.keys())}")
        sys.exit(1)

    return [by_name[n]() for n in names]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    no_api   = "--no-api"   in sys.argv
    rerank   = "--rerank"   in sys.argv

    CACHES_DIR.mkdir(exist_ok=True)
    RESULTS_DIR.mkdir(exist_ok=True)

    print("Loading corpus...")
    notes = load_corpus()
    print(f"  {len(notes)} notes loaded from {CORPUS_DIR}")

    print("Loading embeddings...")
    ids, body_mat, id_to_pos = load_embeddings(notes)
    print(f"  {len(ids)} notes have embeddings; body_mat shape={body_mat.shape}")

    print("Loading ground truth events...")
    events = load_events(ids)
    ground_truth = {ev["qid"]: ev["gold_ids"] for ev in events}
    print(f"  {len(events)} events loaded")

    # Filter notes to those with embeddings
    notes = [n for n in notes if n["id"] in id_to_pos]

    print("\nSelecting signals...")
    sys.path.insert(0, str(WORKBENCH_DIR))
    signals = select_signals(args, no_api)
    print(f"  Signals: {[s.name for s in signals]}")

    print("\nSetting up signals...")
    for sig in signals:
        print(f"  [{sig.name}]")
        sig.setup(notes, ids, body_mat, ground_truth, CACHES_DIR)

    reranker = None
    if rerank:
        print("Setting up cross-encoder reranker...")
        import reranker as reranker_mod
        reranker = reranker_mod.CrossEncoderReranker()
        reranker.setup(notes, CACHES_DIR)

    print()
    import harness
    harness.run(events, ids, body_mat, id_to_pos, signals, RESULTS_DIR,
                reranker=reranker)


if __name__ == "__main__":
    main()
