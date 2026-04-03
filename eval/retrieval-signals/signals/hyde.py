from __future__ import annotations
import json
import re
import numpy as np
from pathlib import Path
from ._base import Signal

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
VOYAGE_MODEL = "voyage-3-lite"


class HyDE(Signal):
    """Hypothetical Document Embeddings (Gao et al., 2022 — arXiv 2212.10496).

    Generates a hypothetical note that would plausibly exist alongside the
    query note in the knowledge base, then retrieves using that hypothetical
    note's embedding. Corrects the query-document representational asymmetry:
    the generated note uses document-style vocabulary and sits closer to
    actual corpus notes in embedding space than the original query does.

    Differs from step-back: step-back abstracts UP (to a principle); HyDE
    generates SIDEWAYS (a peer note on a related topic).

    Cache: caches_dir/hyde.json — {note_id: {"hypothetical": str, "embedding": [float]}}
    """
    name = "hyde"
    needs_loo = False

    def setup(self, notes, ids, body_mat, ground_truth, caches_dir):
        self._ids = ids
        cache_path = caches_dir / "hyde.json"
        cache: dict = {}
        if cache_path.exists():
            cache = json.loads(cache_path.read_text())

        query_ids = set(ground_truth.keys())
        needs_hyp = [n for n in notes if n["id"] in query_ids
                     and n["id"] not in cache]

        if needs_hyp:
            try:
                import anthropic
                import voyageai
            except ImportError:
                import subprocess
                subprocess.run(["pip", "install", "anthropic", "voyageai", "-q"], check=True)
                import anthropic
                import voyageai

            llm = anthropic.Anthropic()
            print(f"  [hyde] Generating hypothetical notes for {len(needs_hyp)} notes...")
            for i, note in enumerate(needs_hyp):
                prompt = (
                    f"Below is a note from a cognitive science knowledge base:\n\n"
                    f"{note['body'][:2000]}\n\n"
                    f"Write a short note (3-5 sentences) that would plausibly exist "
                    f"alongside this one in a cognitive science knowledge base — covering "
                    f"a closely related phenomenon, mechanism, or concept that someone "
                    f"integrating this note might also want to update or reference. "
                    f"Write it as a real knowledge base note, not as a description.\n\n"
                    f'Return JSON only: {{"hypothetical": "<note text>"}}'
                )
                resp = llm.messages.create(model=CLAUDE_MODEL, max_tokens=200,
                                           messages=[{"role": "user", "content": prompt}])
                raw = re.sub(r"^```(?:json)?\s*", "", resp.content[0].text.strip())
                raw = re.sub(r"\s*```$", "", raw)
                try:
                    hyp = json.loads(raw)["hypothetical"]
                except (json.JSONDecodeError, KeyError):
                    # Fallback: extract value after "hypothetical":
                    m = re.search(r'"hypothetical"\s*:\s*"(.*?)(?:"\s*[,}]|"$)', raw, re.DOTALL)
                    hyp = m.group(1) if m else raw[:500]
                cache[note["id"]] = {"hypothetical": hyp}
                cache_path.write_text(json.dumps(cache, indent=2))
                if (i + 1) % 20 == 0:
                    print(f"    [{i+1}/{len(needs_hyp)}]")
        else:
            covered = sum(1 for q in query_ids if q in cache)
            print(f"  [hyde] {covered} hypothetical notes loaded from cache.")

        # Embed hypotheticals not yet embedded
        needs_embed = [nid for nid in cache
                       if nid in query_ids and "embedding" not in cache[nid]]
        if needs_embed:
            import voyageai
            voyage = voyageai.Client()
            batch_size = 128
            print(f"  [hyde] Embedding {len(needs_embed)} hypothetical notes...")
            for start in range(0, len(needs_embed), batch_size):
                batch = needs_embed[start:start + batch_size]
                texts = [cache[nid]["hypothetical"] for nid in batch]
                result = voyage.embed(texts, model=VOYAGE_MODEL, input_type="document")
                for nid, emb in zip(batch, result.embeddings):
                    cache[nid]["embedding"] = emb
            cache_path.write_text(json.dumps(cache, indent=2))

        self._id_to_emb: dict[str, np.ndarray] = {}
        for nid, v in cache.items():
            if "embedding" in v:
                vec = np.array(v["embedding"], dtype=np.float32)
                vec /= (np.linalg.norm(vec) + 1e-9)
                self._id_to_emb[nid] = vec

    def scores(self, qid, qidx, ids, body_mat, loo_events=None) -> np.ndarray:
        if qid not in self._id_to_emb:
            return np.zeros(len(ids), dtype=np.float32)
        q_vec = self._id_to_emb[qid]
        return body_mat @ q_vec
