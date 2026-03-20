"""Cross-encoder reranker — post-fusion LLM re-ranking of the top-K cluster.

Separate from the Signal interface: operates after fusion on the top-CLUSTER_K
candidates rather than scoring all notes. Called by harness.run() if a reranker
is passed.

Cache: caches_dir/reranker_{config_hash}.json
  Key: "{qid}:{sorted_candidate_ids}" → ranked list of IDs
  Invalidated if the fusion configuration changes (different top-K input).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
BATCH_SIZE = 20   # candidates per LLM call — equals CLUSTER_K


class CrossEncoderReranker:
    """Re-ranks a fused top-K candidate list using a Haiku LLM call.

    Prompt: given the query note body and N candidate note bodies,
    return the candidate IDs ranked by relevance to potential integration
    operations (UPDATE, SYNTHESISE, SPLIT, MERGE).

    One Haiku call per event. ~$0.001 per event, ~$0.30 for 299 events.
    """
    name = "cross_encoder"

    def __init__(self):
        self._cache: dict = {}
        self._cache_path: Path | None = None

    def setup(self, notes, caches_dir: Path):
        self._id_to_body = {n["id"]: n["body"] for n in notes}
        self._cache_path = caches_dir / "reranker.json"
        if self._cache_path.exists():
            self._cache = json.loads(self._cache_path.read_text())

        try:
            import anthropic
        except ImportError:
            import subprocess
            subprocess.run(["pip", "install", "anthropic", "-q"], check=True)
            import anthropic
        self._llm = anthropic.Anthropic()
        covered = len(self._cache)
        print(f"  [cross_encoder] {covered} reranked clusters loaded from cache.")

    def _cache_key(self, qid: str, candidate_ids: list[str]) -> str:
        return f"{qid}::{','.join(sorted(candidate_ids))}"

    def rerank(self, qid: str, candidate_ids: list[str]) -> list[str]:
        """Return candidate_ids re-ordered by LLM relevance score."""
        key = self._cache_key(qid, candidate_ids)
        if key in self._cache:
            return self._cache[key]

        query_body = self._id_to_body.get(qid, "")[:1500]
        candidates_text = "\n\n".join(
            f"[{i+1}] ID={nid}\n{self._id_to_body.get(nid,'')[:400]}"
            for i, nid in enumerate(candidate_ids)
        )

        prompt = (
            f"You are ranking notes from a cognitive science knowledge base for "
            f"relevance to an integration operation.\n\n"
            f"QUERY NOTE:\n{query_body}\n\n"
            f"CANDIDATE NOTES (score each 1-5 for relevance to UPDATE, SYNTHESISE, "
            f"SPLIT, or MERGE with the query note; 5=highly relevant, 1=not relevant):\n\n"
            f"{candidates_text}\n\n"
            f"Return JSON only: {{\"ranked_ids\": [\"<id_most_relevant>\", ..., "
            f"\"<id_least_relevant>\"]}}\n"
            f"Include all {len(candidate_ids)} IDs."
        )

        resp = self._llm.messages.create(
            model=CLAUDE_MODEL, max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = re.sub(r"^```(?:json)?\s*", "", resp.content[0].text.strip())
        raw = re.sub(r"\s*```$", "", raw)
        try:
            ranked = json.loads(raw)["ranked_ids"]
            # Validate — keep only IDs that were in the input, append any missing
            valid = [r for r in ranked if r in set(candidate_ids)]
            missing = [c for c in candidate_ids if c not in set(valid)]
            result = valid + missing
        except (json.JSONDecodeError, KeyError):
            result = candidate_ids   # fallback: return original order

        self._cache[key] = result
        self._cache_path.write_text(json.dumps(self._cache, indent=2))
        return result
