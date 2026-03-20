"""Activation signals driven by LLM note-selection prompts (Approaches B and C).

Both approaches simulate what Stage 1 of the integration pipeline would return
as target_note_ids under different prompt designs. For each ground-truth event
(qid), we:
  1. Take the qid note's body as the "incoming note"
  2. Build the top-20 cluster by body-embedding similarity (same as production Gather)
  3. Ask the LLM which cluster notes this incoming note would interact with
  4. Cache the selections — {qid: [selected_note_ids]}

Approach B (prescriptive): explains UPDATE/SYNTHESISE operations, asks for 1-5 notes.
Approach C (permissive): uses open-ended INTERACT framing, no count constraint.

Both use no transitive expansion — the selections are already semantically precise.
"""
from __future__ import annotations
import json
import re
import math
from collections import defaultdict
from pathlib import Path
from itertools import combinations
import numpy as np
from ._base import Signal

CLAUDE_MODEL = "claude-haiku-4-5-20251001"


class ActivationGraph:
    """Lightweight co-occurrence accumulator (no transitive expansion)."""

    def __init__(self, lam: float = 0.0):
        self._w: dict[frozenset, float] = defaultdict(float)
        self._lam = lam

    def add_event(self, qid: str, source_ids: list[str], age_days: float = 0.0) -> None:
        d = math.exp(-self._lam * age_days)
        for sid in source_ids:
            self._w[frozenset([qid, sid])] += d

    def vector(self, qid: str, ids: list[str]) -> np.ndarray:
        return np.array(
            [self._w.get(frozenset([qid, nid]), 0.0) for nid in ids],
            dtype=np.float32,
        )


def _first_sentence(body: str, max_chars: int = 200) -> str:
    """Extract a short description from the note body."""
    text = body.strip()
    end = text.find(". ")
    if 0 < end < max_chars:
        return text[: end + 1]
    return text[:max_chars]


class _ActivationPromptBase(Signal):
    """Base for LLM-prompt-driven activation signals."""

    needs_loo = True
    _cache_filename: str = ""   # subclasses set this

    def _build_prompt(self, qid: str, body: str, cluster: list[tuple[str, str]]) -> str:
        raise NotImplementedError

    def setup(self, notes, ids, body_mat, ground_truth, caches_dir) -> None:
        self._id_to_pos: dict[str, int] = {nid: i for i, nid in enumerate(ids)}
        id_to_body = {n["id"]: n["body"] for n in notes}

        cache_path = caches_dir / self._cache_filename
        selections: dict[str, list[str]] = {}
        if cache_path.exists():
            selections = json.loads(cache_path.read_text())

        query_ids = set(ground_truth.keys())
        needs_gen = [n for n in notes if n["id"] in query_ids and n["id"] not in selections]

        if needs_gen:
            try:
                import anthropic
            except ImportError:
                import subprocess
                subprocess.run(["pip", "install", "anthropic", "-q"], check=True)
                import anthropic

            llm = anthropic.Anthropic()
            print(f"  [{self.name}] Generating selections for {len(needs_gen)} notes...", flush=True)
            for i, note in enumerate(needs_gen):
                qid = note["id"]
                qidx = self._id_to_pos.get(qid)
                if qidx is None:
                    selections[qid] = []
                    continue

                # Build top-20 cluster by body similarity (same as production Gather)
                sims = body_mat @ body_mat[qidx]
                sims[qidx] = -1.0
                top20_idxs = np.argsort(-sims)[:20]
                cluster = [
                    (ids[j], _first_sentence(id_to_body.get(ids[j], "")))
                    for j in top20_idxs
                ]

                prompt = self._build_prompt(qid, note["body"], cluster)
                resp = llm.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=200,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = resp.content[0].text.strip()
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
                try:
                    parsed = json.loads(raw)
                    selected = parsed.get("target_note_ids", [])
                except (json.JSONDecodeError, KeyError):
                    m = re.search(r'"target_note_ids"\s*:\s*\[([^\]]*)\]', raw)
                    if m:
                        selected = re.findall(r'"([^"]+)"', m.group(1))
                    else:
                        selected = []

                # Filter to valid corpus IDs only
                valid = {ids[j] for j in top20_idxs}
                selections[qid] = [s for s in selected if s in valid]
                cache_path.write_text(json.dumps(selections, indent=2))

                if (i + 1) % 20 == 0:
                    print(f"    [{i+1}/{len(needs_gen)}]", flush=True)
        else:
            covered = sum(1 for q in query_ids if q in selections)
            print(f"  [{self.name}] {covered} selections loaded from cache.", flush=True)

        self._selections = selections

    def scores(self, qid, qidx, ids, body_mat, loo_events=None) -> np.ndarray:
        graph = ActivationGraph(lam=0.0)
        for ev in (loo_events or []):
            eq_id = ev["qid"]
            selected = self._selections.get(eq_id, [])
            if selected:
                graph.add_event(eq_id, selected)
        return graph.vector(qid, ids)


class ActivationB(_ActivationPromptBase):
    """Approach B: prescriptive prompt explaining UPDATE/SYNTHESISE operations.

    Asks the LLM which 1-5 cluster notes the incoming note would UPDATE or
    SYNTHESISE with — modelled on the integration Step 1 prompt, but
    rephrased to make target_note_ids mean 'gold note nominations'.
    """
    name = "activation_b"
    _cache_filename = "activation_b.json"

    def _build_prompt(self, qid: str, body: str, cluster: list[tuple[str, str]]) -> str:
        cluster_lines = "\n".join(f"  {nid}: {desc}" for nid, desc in cluster)
        return (
            f"You are deciding which notes in a knowledge base would interact "
            f"with a new incoming note during integration.\n\n"
            f"Incoming note (id={qid}):\n"
            f"{body[:1200]}\n\n"
            f"Related notes in the knowledge base (top-20 by semantic similarity):\n"
            f"{cluster_lines}\n\n"
            f"Which of these notes would the incoming note directly interact with "
            f"during integration? Interaction means:\n"
            f"- UPDATE: the incoming note adds specific new content to an existing note\n"
            f"- SYNTHESISE: the incoming note and an existing note span a shared "
            f"concept worth bridging\n\n"
            f"Return 1-5 note IDs with the strongest interactions.\n"
            f'Return JSON only: {{"target_note_ids": ["id1", "id2", ...]}}'
        )


class ActivationC(_ActivationPromptBase):
    """Approach C: permissive INTERACT prompt — open-ended, no operation guidance.

    Modelled on the gold-notes workbench prompt. Asks the LLM which notes this
    incoming note would INTERACT with, without constraining the count or
    explaining specific operations. Lets the LLM find its own way.
    """
    name = "activation_c"
    _cache_filename = "activation_c.json"

    def _build_prompt(self, qid: str, body: str, cluster: list[tuple[str, str]]) -> str:
        cluster_lines = "\n".join(f"  {nid}: {desc}" for nid, desc in cluster)
        return (
            f"You are reviewing a new note being integrated into a knowledge base.\n\n"
            f"New note (id={qid}):\n"
            f"{body[:1200]}\n\n"
            f"Here are related notes from the knowledge base:\n"
            f"{cluster_lines}\n\n"
            f"Identify which existing notes this new note would INTERACT with "
            f"during integration — notes whose content this note meaningfully "
            f"extends, challenges, or bridges.\n\n"
            f'Return JSON only: {{"target_note_ids": ["id1", "id2", ...]}}'
        )
