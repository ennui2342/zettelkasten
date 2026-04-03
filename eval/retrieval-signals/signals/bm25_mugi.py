from __future__ import annotations
import json
import re
from pathlib import Path
import numpy as np
from ._base import Signal

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
N_PSEUDO = 3


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


class BM25MuGI(Signal):
    """BM25 retrieval with MuGI query expansion.

    Generates N pseudo-notes from the query note via an LLM, concatenates
    them with the original body to form an expanded BM25 query. Recovers
    notes that share vocabulary with conceptual neighbours of the query even
    when the query itself doesn't use that vocabulary.

    Cache: caches_dir/pseudo_notes.json — incremental, safe to restart.
    """
    name = "bm25_mugi"
    needs_loo = False

    def setup(self, notes, ids, body_mat, ground_truth, caches_dir):
        from rank_bm25 import BM25Okapi
        self._id_to_body = {n["id"]: n["body"] for n in notes}
        corpus_tokens = [_tokenize(self._id_to_body.get(nid, "")) for nid in ids]
        self._bm25 = BM25Okapi(corpus_tokens)
        self._ids = ids

        cache_path = caches_dir / "pseudo_notes.json"
        cache: dict = {}
        if cache_path.exists():
            cache = json.loads(cache_path.read_text())

        query_ids = {qid for qid in ground_truth}
        needs = [n for n in notes if n["id"] in query_ids and n["id"] not in cache]
        if needs:
            try:
                import anthropic
            except ImportError:
                import subprocess
                subprocess.run(["pip", "install", "anthropic", "-q"], check=True)
                import anthropic
            llm = anthropic.Anthropic()
            print(f"  [bm25_mugi] Generating pseudo-notes for {len(needs)} notes...")
            for i, note in enumerate(needs):
                prompt = (
                    f"You are helping expand a knowledge base search query.\n\n"
                    f"Below is a note from a cognitive science knowledge base:\n\n"
                    f"{note['body'][:2000]}\n\n"
                    f"Generate {N_PSEUDO} short notes (2-4 sentences each) about DIFFERENT "
                    f"but related cognitive science concepts. Each should use the vocabulary "
                    f"of that related concept naturally.\n\n"
                    f'Return JSON only: {{"pseudo_notes": ["<note1>", "<note2>", "<note3>"]}}'
                )
                resp = llm.messages.create(model=CLAUDE_MODEL, max_tokens=400,
                                           messages=[{"role": "user", "content": prompt}])
                raw = re.sub(r"^```(?:json)?\s*", "", resp.content[0].text.strip())
                raw = re.sub(r"\s*```$", "", raw)
                cache[note["id"]] = json.loads(raw)["pseudo_notes"]
                cache_path.write_text(json.dumps(cache, indent=2))
                if (i + 1) % 20 == 0:
                    print(f"    [{i+1}/{len(needs)}]")
        else:
            covered = sum(1 for q in query_ids if q in cache)
            print(f"  [bm25_mugi] {covered} pseudo-note sets loaded from cache.")

        self._cache = cache

    def scores(self, qid, qidx, ids, body_mat, loo_events=None) -> np.ndarray:
        body = self._id_to_body.get(qid, "")
        pseudo = self._cache.get(qid, [])
        tokens = _tokenize(body + " " + " ".join(pseudo))
        return np.array(self._bm25.get_scores(tokens), dtype=np.float32)
