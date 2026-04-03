"""Base class for retrieval signals."""
from __future__ import annotations
from pathlib import Path
import numpy as np


class Signal:
    name: str = "unnamed"
    needs_loo: bool = False   # set True if scores depend on which event is held out

    def setup(
        self,
        notes: list[dict],        # [{id, body}, ...]
        ids: list[str],           # ordered note IDs matching embedding matrix rows
        body_mat: np.ndarray,     # (N, D) normalised body embeddings
        ground_truth: dict,       # spike4d ground truth
        caches_dir: Path,
    ) -> None:
        """Called once before the LOO loop. Load/generate any persistent state."""
        pass

    def scores(
        self,
        qid: str,
        qidx: int,
        ids: list[str],
        body_mat: np.ndarray,
        loo_events: list[dict] | None = None,  # all events EXCEPT the current fold
    ) -> np.ndarray:
        """Return a score vector of length len(ids). Higher = more relevant."""
        raise NotImplementedError
