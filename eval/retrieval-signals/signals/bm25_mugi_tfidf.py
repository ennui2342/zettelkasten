from __future__ import annotations
import json
import math
import re
from collections import defaultdict
import numpy as np
from ._base import Signal

KW_TOP_K = 30   # top discriminative tokens from pseudo-notes to use as BM25 query


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


class BM25MuGITFIDF(Signal):
    """BM25 + MuGI with TF-IDF weighted query tokens from pseudo-notes.

    Standard MuGI concatenates all pseudo-note tokens equally as the BM25 query.
    This variant instead:
      1. Concatenates original body + pseudo-notes
      2. Computes TF-IDF score for each token in that concatenated text
      3. Takes the top-K most discriminative tokens as the BM25 query

    This reduces noise from common words in pseudo-notes (articles, prepositions,
    generic cognitive science vocabulary like "cognitive", "mental", "process")
    and emphasises the distinctive terminology that BM25 can match precisely.

    Reuses the N=3 pseudo-note cache from BM25MuGI. No new API calls.

    Cache: reuses caches_dir/pseudo_notes.json
    """
    name = "bm25_mugi_tfidf"
    needs_loo = False

    def setup(self, notes, ids, body_mat, ground_truth, caches_dir):
        from rank_bm25 import BM25Okapi
        self._id_to_body = {n["id"]: n["body"] for n in notes}

        # Build BM25 index
        corpus_tokens = [_tokenize(self._id_to_body.get(nid, "")) for nid in ids]
        self._bm25 = BM25Okapi(corpus_tokens)

        # Compute corpus IDF
        N = len(notes)
        df: dict[str, int] = defaultdict(int)
        for note in notes:
            for tok in set(_tokenize(note["body"])):
                df[tok] += 1
        self._idf = {tok: math.log((N + 1) / (count + 1)) for tok, count in df.items()}

        # Load pseudo-notes cache
        cache_path = caches_dir / "pseudo_notes.json"
        cache: dict = {}
        if cache_path.exists():
            cache = json.loads(cache_path.read_text())
        query_ids = set(ground_truth.keys())
        covered = sum(1 for q in query_ids if q in cache)
        print(f"  [bm25_mugi_tfidf] {covered} pseudo-note sets loaded from cache "
              f"(TF-IDF weighted query).")
        self._cache = cache

    def scores(self, qid, qidx, ids, body_mat, loo_events=None) -> np.ndarray:
        body = self._id_to_body.get(qid, "")
        pseudo = self._cache.get(qid, [])
        combined = body + " " + " ".join(pseudo)
        tokens = _tokenize(combined)

        # TF-IDF scoring over combined text
        tf: dict[str, int] = defaultdict(int)
        for t in tokens:
            tf[t] += 1
        kw_scores = {t: tf[t] * self._idf.get(t, 0.0) for t in tf}
        keywords = sorted(kw_scores, key=lambda x: -kw_scores[x])[:KW_TOP_K]
        return np.array(self._bm25.get_scores(keywords), dtype=np.float32)
