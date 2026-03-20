from __future__ import annotations
import numpy as np
from ._base import Signal


class BodyEmbedding(Signal):
    """Cosine similarity between query body embedding and all note body embeddings."""
    name = "body"
    needs_loo = False

    def scores(self, qid, qidx, ids, body_mat, loo_events=None) -> np.ndarray:
        return body_mat @ body_mat[qidx]
