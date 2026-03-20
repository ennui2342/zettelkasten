"""Scalar activation signals — Q-independent note popularity.

In the scalar model each note has a single activation value (how often it has
been activated, regardless of which query triggered it). When scoring for query
Q, every note's scalar is returned directly — there is no Q-specific edge lookup.

This is the query-time architecture alternative to the pairwise graph. The same
four recording strategies are tested:
  - ScalarGold:  gold_ids (ceiling)
  - ScalarK20:   top-20 by body similarity
  - ScalarB:     B-prompt selections (reuses activation_b cache)
  - ScalarC:     C-prompt selections (reuses activation_c cache)
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from ._base import Signal


class _ScalarBase(Signal):
    needs_loo = True

    def _activated_notes(self, ev: dict, ids: list[str], body_mat: np.ndarray) -> list[str]:
        raise NotImplementedError

    def scores(self, qid, qidx, ids, body_mat, loo_events=None) -> np.ndarray:
        counts: dict[str, float] = defaultdict(float)
        for ev in (loo_events or []):
            for nid in self._activated_notes(ev, ids, body_mat):
                counts[nid] += 1.0
        return np.array([counts.get(nid, 0.0) for nid in ids], dtype=np.float32)


class ActivationScalarGold(_ScalarBase):
    """Scalar ceiling: counts how often each note appeared as a gold note."""
    name = "scalar_gold"

    def _activated_notes(self, ev, ids, body_mat):
        return ev.get("gold_ids", [])


class ActivationScalarK20(_ScalarBase):
    """Scalar k20: counts how often each note appeared in a top-20 cluster."""
    name = "scalar_k20"

    def setup(self, notes, ids, body_mat, ground_truth, caches_dir) -> None:
        self._id_to_pos: dict[str, int] = {nid: i for i, nid in enumerate(ids)}

    def _activated_notes(self, ev, ids, body_mat):
        eq_id = ev["qid"]
        if eq_id not in self._id_to_pos:
            return []
        eq_idx = self._id_to_pos[eq_id]
        sims = body_mat @ body_mat[eq_idx]
        sims[eq_idx] = -1.0
        return [ids[i] for i in np.argsort(-sims)[:20]]


class ActivationScalarB(_ScalarBase):
    """Scalar B: counts activations using cached B-prompt selections."""
    name = "scalar_b"

    def setup(self, notes, ids, body_mat, ground_truth, caches_dir) -> None:
        cache_path = caches_dir / "activation_b.json"
        if not cache_path.exists():
            raise FileNotFoundError(
                "activation_b.json cache not found — run activation_b signal first."
            )
        self._selections: dict[str, list[str]] = json.loads(cache_path.read_text())
        print(f"  [{self.name}] {len(self._selections)} selections loaded from activation_b cache.")

    def _activated_notes(self, ev, ids, body_mat):
        return self._selections.get(ev["qid"], [])


class ActivationScalarC(_ScalarBase):
    """Scalar C: counts activations using cached C-prompt selections."""
    name = "scalar_c"

    def setup(self, notes, ids, body_mat, ground_truth, caches_dir) -> None:
        cache_path = caches_dir / "activation_c.json"
        if not cache_path.exists():
            raise FileNotFoundError(
                "activation_c.json cache not found — run activation_c signal first."
            )
        self._selections: dict[str, list[str]] = json.loads(cache_path.read_text())
        print(f"  [{self.name}] {len(self._selections)} selections loaded from activation_c cache.")

    def _activated_notes(self, ev, ids, body_mat):
        return self._selections.get(ev["qid"], [])
