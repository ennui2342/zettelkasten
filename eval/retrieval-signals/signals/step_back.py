from __future__ import annotations
import json
import re
import numpy as np
from pathlib import Path
from ._base import Signal

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
VOYAGE_MODEL = "voyage-3-lite"


class StepBack(Signal):
    """Step-back prompting (Zheng et al., Google DeepMind — ICLR 2024).

    Before retrieval, asks an LLM: 'What broader principle or theme does this
    note exemplify?' Embeds the abstract answer and retrieves against it.

    Targets principle-level inferential gaps: notes connected through a shared
    abstract principle that neither expresses explicitly (e.g. Zeigarnik and
    Gestalt both instantiate 'incompleteness drives sustained cognitive
    engagement', but neither states it).

    Cache: caches_dir/step_back.json — {note_id: {"abstraction": str, "embedding": [float]}}
    """
    name = "step_back"
    needs_loo = False

    def setup(self, notes, ids, body_mat, ground_truth, caches_dir):
        self._ids = ids
        cache_path = caches_dir / "step_back.json"
        cache: dict = {}
        if cache_path.exists():
            cache = json.loads(cache_path.read_text())

        id_to_body = {n["id"]: n["body"] for n in notes}
        query_ids = set(ground_truth.keys())
        needs_abstraction = [n for n in notes if n["id"] in query_ids
                             and n["id"] not in cache]

        if needs_abstraction:
            try:
                import anthropic
                import voyageai
            except ImportError:
                import subprocess
                subprocess.run(["pip", "install", "anthropic", "voyageai", "-q"], check=True)
                import anthropic
                import voyageai

            llm = anthropic.Anthropic()
            print(f"  [step_back] Generating abstractions for {len(needs_abstraction)} notes...")
            for i, note in enumerate(needs_abstraction):
                prompt = (
                    f"Below is a note from a cognitive science knowledge base:\n\n"
                    f"{note['body'][:2000]}\n\n"
                    f"In 1-2 sentences, state the broader principle, theme, or mechanism "
                    f"this note exemplifies — at a level of abstraction that would also "
                    f"describe related concepts in neighbouring fields.\n\n"
                    f'Return JSON only: {{"abstraction": "<principle>"}}'
                )
                resp = llm.messages.create(model=CLAUDE_MODEL, max_tokens=150,
                                           messages=[{"role": "user", "content": prompt}])
                raw = re.sub(r"^```(?:json)?\s*", "", resp.content[0].text.strip())
                raw = re.sub(r"\s*```$", "", raw)
                try:
                    abst = json.loads(raw)["abstraction"]
                except (json.JSONDecodeError, KeyError):
                    m = re.search(r'"abstraction"\s*:\s*"(.*?)(?:"\s*[,}]|"$)', raw, re.DOTALL)
                    abst = m.group(1) if m else raw[:300]
                cache[note["id"]] = {"abstraction": abst}
                cache_path.write_text(json.dumps(cache, indent=2))
                if (i + 1) % 20 == 0:
                    print(f"    [{i+1}/{len(needs_abstraction)}]")
        else:
            covered = sum(1 for q in query_ids if q in cache)
            print(f"  [step_back] {covered} abstractions loaded from cache.")

        # Embed abstractions not yet embedded
        needs_embed = [nid for nid in cache
                       if nid in query_ids and "embedding" not in cache[nid]]
        if needs_embed:
            import voyageai
            voyage = voyageai.Client()
            batch_size = 128
            print(f"  [step_back] Embedding {len(needs_embed)} abstractions...")
            for start in range(0, len(needs_embed), batch_size):
                batch = needs_embed[start:start + batch_size]
                texts = [cache[nid]["abstraction"] for nid in batch]
                result = voyage.embed(texts, model=VOYAGE_MODEL, input_type="query")
                for nid, emb in zip(batch, result.embeddings):
                    cache[nid]["embedding"] = emb
            cache_path.write_text(json.dumps(cache, indent=2))

        self._cache = cache

        # Build embedding matrix aligned with ids (for candidate side)
        # Step-back uses abstraction as QUERY, body embeddings as CANDIDATES
        # (same as how spike4d used summary as query against body_mat)
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
        # Query: step-back abstraction embedding; Candidates: body embeddings
        return body_mat @ q_vec
