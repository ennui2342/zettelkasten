from __future__ import annotations
import json
import numpy as np
from ._base import Signal

VOYAGE_MODEL = "voyage-3-lite"


class BodyEmbeddingQuery(Signal):
    """Asymmetric body embedding: query side uses input_type='query', corpus uses 'document'.

    The corpus embeddings (body_mat) were built with input_type='document' in spike4a.
    Voyage models are trained for asymmetric retrieval — the query encoder and document
    encoder are different projections of the same backbone. Using 'query' for the query
    note and 'document' for the corpus is the intended usage for retrieval tasks.

    Difference from BodyEmbedding: BodyEmbedding uses body_mat[qidx] (the corpus-side
    'document' embedding of the query note). This signal re-embeds the query note body
    with input_type='query' at evaluation time, using a separate cached embedding.

    Cache: caches_dir/query_embeddings.json — {note_id: [float]}
    """
    name = "body_query"
    needs_loo = False

    def setup(self, notes, ids, body_mat, ground_truth, caches_dir):
        cache_path = caches_dir / "query_embeddings.json"
        cache: dict = {}
        if cache_path.exists():
            cache = json.loads(cache_path.read_text())

        query_ids = set(ground_truth.keys())
        id_to_body = {n["id"]: n["body"] for n in notes}
        needs_embed = [nid for nid in query_ids if nid in id_to_body and nid not in cache]

        if needs_embed:
            try:
                import voyageai
            except ImportError:
                import subprocess
                subprocess.run(["pip", "install", "voyageai", "-q"], check=True)
                import voyageai
            voyage = voyageai.Client()
            batch_size = 128
            print(f"  [body_query] Embedding {len(needs_embed)} query notes with input_type='query'...")
            for start in range(0, len(needs_embed), batch_size):
                batch = needs_embed[start:start + batch_size]
                texts = [id_to_body[nid] for nid in batch]
                result = voyage.embed(texts, model=VOYAGE_MODEL, input_type="query")
                for nid, emb in zip(batch, result.embeddings):
                    cache[nid] = emb
            cache_path.write_text(json.dumps(cache, indent=2))
            print(f"  [body_query] Done.")
        else:
            covered = sum(1 for q in query_ids if q in cache)
            print(f"  [body_query] {covered} query embeddings loaded from cache.")

        self._id_to_emb: dict[str, np.ndarray] = {}
        for nid, emb in cache.items():
            v = np.array(emb, dtype=np.float32)
            v /= (np.linalg.norm(v) + 1e-9)
            self._id_to_emb[nid] = v

    def scores(self, qid, qidx, ids, body_mat, loo_events=None) -> np.ndarray:
        if qid not in self._id_to_emb:
            return np.zeros(len(ids), dtype=np.float32)
        return body_mat @ self._id_to_emb[qid]
