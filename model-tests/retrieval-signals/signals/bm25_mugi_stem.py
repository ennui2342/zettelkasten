from __future__ import annotations
import json
import re
import numpy as np
from ._base import Signal

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
N_PSEUDO = 3


def _stem(word: str) -> str:
    """Minimal Porter stemmer — handles the most common English suffixes."""
    # Step 1a
    if word.endswith("sses"):    word = word[:-2]
    elif word.endswith("ies"):   word = word[:-2]
    elif word.endswith("ss"):    pass
    elif word.endswith("s"):     word = word[:-1]
    # Step 1b
    if word.endswith("eed"):
        if len(word) > 4:        word = word[:-1]
    elif word.endswith("ed") and any(c in word[:-2] for c in "aeiou"):
        word = word[:-2]
        if word.endswith("at") or word.endswith("bl") or word.endswith("iz"):
            word += "e"
    elif word.endswith("ing") and any(c in word[:-3] for c in "aeiou"):
        word = word[:-3]
        if word.endswith("at") or word.endswith("bl") or word.endswith("iz"):
            word += "e"
    # Step 1c
    if word.endswith("y") and any(c in word[:-1] for c in "aeiou"):
        word = word[:-1] + "i"
    # Step 2 (most impactful suffixes)
    for suffix, replacement in [
        ("ational", "ate"), ("tional", "tion"), ("enci", "ence"),
        ("anci", "ance"), ("izer", "ize"), ("ising", "ise"),
        ("izing", "ize"), ("alism", "al"), ("ation", "ate"),
        ("ator", "ate"), ("alism", "al"), ("ness", ""),
        ("fulness", "ful"), ("ousness", "ous"),
    ]:
        if word.endswith(suffix) and len(word) - len(suffix) > 2:
            word = word[:-len(suffix)] + replacement
            break
    return word


def _tokenize_stem(text: str) -> list[str]:
    return [_stem(w) for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 3]


class BM25MuGIStem(Signal):
    """BM25 + MuGI with Porter stemming on both corpus and query tokens.

    Stemming reduces surface-form variation: learning/learns/learned all map
    to the same stem, increasing vocabulary overlap between query and corpus.
    Reuses the N=3 pseudo-note cache from BM25MuGI (same LLM generation).
    Rebuilds BM25 index using stemmed tokens.

    Cache: reuses caches_dir/pseudo_notes.json (no new API calls needed)
    """
    name = "bm25_mugi_stem"
    needs_loo = False

    def setup(self, notes, ids, body_mat, ground_truth, caches_dir):
        from rank_bm25 import BM25Okapi
        self._id_to_body = {n["id"]: n["body"] for n in notes}

        # Build stemmed BM25 index
        corpus_tokens = [_tokenize_stem(self._id_to_body.get(nid, "")) for nid in ids]
        self._bm25 = BM25Okapi(corpus_tokens)

        # Reuse existing pseudo-notes cache
        cache_path = caches_dir / "pseudo_notes.json"
        cache: dict = {}
        if cache_path.exists():
            cache = json.loads(cache_path.read_text())
        query_ids = set(ground_truth.keys())
        covered = sum(1 for q in query_ids if q in cache)
        print(f"  [bm25_mugi_stem] {covered} pseudo-note sets loaded from cache "
              f"(stemmed index).")
        self._cache = cache

    def scores(self, qid, qidx, ids, body_mat, loo_events=None) -> np.ndarray:
        body = self._id_to_body.get(qid, "")
        pseudo = self._cache.get(qid, [])
        tokens = _tokenize_stem(body + " " + " ".join(pseudo))
        return np.array(self._bm25.get_scores(tokens), dtype=np.float32)
