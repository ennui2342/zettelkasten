from __future__ import annotations
import math
import re
from collections import defaultdict
from pathlib import Path
import numpy as np
from ._base import Signal

KW_TOP_K = 25


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


class BM25Keyword(Signal):
    """BM25 with TF-IDF keyword extraction as query (contextual BM25).

    Uses the top-K most discriminative terms from the query note body as the
    BM25 query, rather than the full body. Reduces query noise from common
    words; increases weight on distinctive terminology.
    """
    name = "bm25_keyword"
    needs_loo = False

    def setup(self, notes, ids, body_mat, ground_truth, caches_dir):
        from rank_bm25 import BM25Okapi
        self._id_to_body = {n["id"]: n["body"] for n in notes}
        corpus_tokens = [_tokenize(self._id_to_body.get(nid, "")) for nid in ids]
        self._bm25 = BM25Okapi(corpus_tokens)

        # Compute IDF over corpus
        N = len(notes)
        df: dict[str, int] = defaultdict(int)
        for note in notes:
            for tok in set(_tokenize(note["body"])):
                df[tok] += 1
        self._idf = {tok: math.log((N + 1) / (count + 1)) for tok, count in df.items()}

    def scores(self, qid, qidx, ids, body_mat, loo_events=None) -> np.ndarray:
        body = self._id_to_body.get(qid, "")
        tokens = _tokenize(body)
        tf: dict[str, int] = defaultdict(int)
        for t in tokens:
            tf[t] += 1
        kw_scores = {t: tf[t] * self._idf.get(t, 0.0) for t in tf}
        keywords = sorted(kw_scores, key=lambda x: -kw_scores[x])[:KW_TOP_K]
        return np.array(self._bm25.get_scores(keywords), dtype=np.float32)
