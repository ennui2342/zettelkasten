from __future__ import annotations
import math
from collections import defaultdict
from itertools import combinations
from pathlib import Path
import numpy as np
from ._base import Signal


class ActivationGraph:
    """Weighted co-occurrence graph with optional decay and transitive expansion."""

    def __init__(self, lam: float = 0.0, transitive: bool = True):
        self._w: dict[frozenset, float] = defaultdict(float)
        self._lam = lam
        self._transitive = transitive

    def add_event(self, qid: str, source_ids: list[str], age_days: float = 0.0) -> None:
        d = math.exp(-self._lam * age_days)
        for sid in source_ids:
            self._w[frozenset([qid, sid])] += d
        if self._transitive:
            for a, b in combinations(source_ids, 2):
                self._w[frozenset([a, b])] += d

    def vector(self, qid: str, ids: list[str]) -> np.ndarray:
        return np.array(
            [self._w.get(frozenset([qid, nid]), 0.0) for nid in ids],
            dtype=np.float32,
        )


class Activation(Signal):
    """Baseline: co-activation using ground-truth gold_ids (LOO).

    Uses LLM-judged gold notes as activation sources — the closest proxy to
    what the integration Stage 1 INTERACT prompt would return (Approach B/C).
    Includes transitive expansion: notes co-listed in the same event gain
    mutual weight via combinations(gold_ids, 2).
    """
    name = "activation"
    needs_loo = True

    def scores(self, qid, qidx, ids, body_mat, loo_events=None) -> np.ndarray:
        graph = ActivationGraph(lam=0.0, transitive=True)
        for ev in (loo_events or []):
            graph.add_event(ev["qid"], ev["gold_ids"])
        return graph.vector(qid, ids)


class ActivationNoTransitive(Signal):
    """Gold_ids activation without transitive expansion.

    Same source as Activation (LLM gold notes) but drops the combinations()
    expansion that adds mutual weight between all co-listed notes. Tests
    whether transitive expansion helps or amplifies hub-note dominance.
    """
    name = "activation_no_trans"
    needs_loo = True

    def scores(self, qid, qidx, ids, body_mat, loo_events=None) -> np.ndarray:
        graph = ActivationGraph(lam=0.0, transitive=False)
        for ev in (loo_events or []):
            graph.add_event(ev["qid"], ev["gold_ids"])
        return graph.vector(qid, ids)


class ActivationK20(Signal):
    """Approach A: co-activation using k=20 body-similarity cluster.

    For each LOO event, activates the top-20 notes by cosine similarity to the
    event's source note — regardless of whether they're gold notes. Simulates
    the production UPDATE path where the full retrieval cluster is activated.
    No transitive expansion (k=20 already broad; transitive would be explosive).
    """
    name = "activation_k20"
    needs_loo = True

    def setup(self, notes, ids, body_mat, ground_truth, caches_dir) -> None:
        self._id_to_pos: dict[str, int] = {nid: i for i, nid in enumerate(ids)}

    def scores(self, qid, qidx, ids, body_mat, loo_events=None) -> np.ndarray:
        graph = ActivationGraph(lam=0.0, transitive=False)
        for ev in (loo_events or []):
            eq_id = ev["qid"]
            if eq_id not in self._id_to_pos:
                continue
            eq_idx = self._id_to_pos[eq_id]
            sims = body_mat @ body_mat[eq_idx]
            sims[eq_idx] = -1.0  # exclude self
            top20_ids = [ids[i] for i in np.argsort(-sims)[:20]]
            graph.add_event(eq_id, top20_ids)
        return graph.vector(qid, ids)
