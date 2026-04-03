from __future__ import annotations
import json
import re
import numpy as np
from ._base import Signal

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
VOYAGE_MODEL = "voyage-3-lite"
N_HYPOTHETICAL = 3


class HyDEMulti(Signal):
    """HyDE with N=3 hypothetical notes, embeddings averaged.

    Single hypothetical notes have high variance — a single unlucky generation
    can land in the wrong region of embedding space. Averaging embeddings across
    N independently generated hypotheticals produces a more stable centroid that
    better represents the expected peer-note neighbourhood.

    Cache: caches_dir/hyde_multi.json — {note_id: {"hypotheticals": [...], "embedding": [...]}}
    The embedding stored is already the average of N individual embeddings.
    """
    name = "hyde_multi"
    needs_loo = False

    def setup(self, notes, ids, body_mat, ground_truth, caches_dir):
        cache_path = caches_dir / "hyde_multi.json"
        cache: dict = {}
        if cache_path.exists():
            cache = json.loads(cache_path.read_text())

        query_ids = set(ground_truth.keys())
        needs_hyp = [n for n in notes if n["id"] in query_ids and n["id"] not in cache]

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
            voyage = voyageai.Client()
            print(f"  [hyde_multi] Generating {N_HYPOTHETICAL} hypothetical notes for "
                  f"{len(needs_hyp)} notes...")

            for i, note in enumerate(needs_hyp):
                prompt = (
                    f"Below is a note from a cognitive science knowledge base:\n\n"
                    f"{note['body'][:2000]}\n\n"
                    f"Write {N_HYPOTHETICAL} short notes (3-5 sentences each) that would "
                    f"plausibly exist alongside this one in a cognitive science knowledge base. "
                    f"Each should cover a DIFFERENT closely related phenomenon, mechanism, or "
                    f"concept that someone integrating this note might also want to update or "
                    f"reference. Write them as real knowledge base notes, not descriptions.\n\n"
                    f'Return JSON only: {{"hypotheticals": ["<note1>", "<note2>", "<note3>"]}}'
                )
                resp = llm.messages.create(model=CLAUDE_MODEL, max_tokens=600,
                                           messages=[{"role": "user", "content": prompt}])
                raw = re.sub(r"^```(?:json)?\s*", "", resp.content[0].text.strip())
                raw = re.sub(r"\s*```$", "", raw)
                try:
                    hyps = json.loads(raw)["hypotheticals"]
                    if not isinstance(hyps, list):
                        raise ValueError
                except (json.JSONDecodeError, KeyError, ValueError):
                    m = re.search(r'"hypotheticals"\s*:\s*\[(.+?)\]', raw, re.DOTALL)
                    hyps = [raw[:400]] if not m else [raw[:400]]

                # Embed all N and average
                result = voyage.embed(hyps[:N_HYPOTHETICAL], model=VOYAGE_MODEL,
                                      input_type="document")
                avg_emb = np.mean([e for e in result.embeddings], axis=0).tolist()
                cache[note["id"]] = {"hypotheticals": hyps, "embedding": avg_emb}
                cache_path.write_text(json.dumps(cache, indent=2))
                if (i + 1) % 20 == 0:
                    print(f"    [{i+1}/{len(needs_hyp)}]")
        else:
            covered = sum(1 for q in query_ids if q in cache)
            print(f"  [hyde_multi] {covered} multi-hypothetical embeddings loaded from cache.")

        self._id_to_emb: dict[str, np.ndarray] = {}
        for nid, v in cache.items():
            if "embedding" in v:
                vec = np.array(v["embedding"], dtype=np.float32)
                vec /= (np.linalg.norm(vec) + 1e-9)
                self._id_to_emb[nid] = vec

    def scores(self, qid, qidx, ids, body_mat, loo_events=None) -> np.ndarray:
        if qid not in self._id_to_emb:
            return np.zeros(len(ids), dtype=np.float32)
        return body_mat @ self._id_to_emb[qid]
