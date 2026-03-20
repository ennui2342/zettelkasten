"""Gather phase: 5-signal retrieval fusion.

Signals and validated weights (retrieval-workbench, R@10=0.667, MRR=0.844):
  body_query     0.450  — asymmetric body embedding (query-side)
  bm25_mugi_stem 0.270  — BM25 with MuGI pseudo-note expansion + Porter stemming
  activation     0.180  — co-activation graph from integration history
  step_back      0.050  — principle-level abstraction embedding
  hyde_multi     0.050  — averaged hypothetical peer-note embeddings
"""
from __future__ import annotations

import json
import logging
import math
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import numpy as np

from .note import ZettelNote
from .providers import EmbedProvider, LLMProvider

log = logging.getLogger("zettelkasten")

# ---------------------------------------------------------------------------
# Weights (validated in retrieval-workbench spike)
# ---------------------------------------------------------------------------

WEIGHTS: dict[str, float] = {
    "body_query":     0.450,
    "bm25_mugi_stem": 0.270,
    "activation":     0.180,
    "step_back":      0.050,
    "hyde_multi":     0.050,
}
N_PSEUDO = 3              # MuGI pseudo-note count
N_HYPOTHETICAL = 3        # HyDE hypothetical note count


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def gather_phase(
    draft: ZettelNote,
    corpus: list[ZettelNote],
    llm: LLMProvider,
    embed: EmbedProvider,
    *,
    top_k: int = 20,
    activation_scores: dict[str, float] | None = None,
) -> list[ZettelNote]:
    """Return up to *top_k* corpus notes most relevant to *draft*.

    Uses a weighted blend of 5 retrieval signals.  Signals that require
    API calls (step-back, HyDE, MuGI) are called via *llm* and *embed*.
    *activation_scores* is a pre-fetched {note_id: score} dict from the
    index (caller's responsibility); defaults to all-zero if not supplied.
    """
    log.info("gather.start draft_id=%r corpus_size=%d", draft.id, len(corpus))

    if not corpus:
        log.info("gather.complete results=0 (empty corpus)")
        return []

    ids = [n.id for n in corpus]
    id_to_note = {n.id: n for n in corpus}

    # Build embedding matrix (only for notes that have embeddings)
    emb_ids: list[str] = []
    emb_vecs: list[np.ndarray] = []
    for n in corpus:
        if n.embedding is not None:
            emb_ids.append(n.id)
            emb_vecs.append(n.embedding.astype(np.float32))
    body_mat = np.stack(emb_vecs) if emb_vecs else None  # shape (E, D) or None

    # Initialise score array — one float per corpus note, keyed by position
    n = len(ids)
    id_to_pos = {nid: i for i, nid in enumerate(ids)}

    # ---- Signal 1: body_query ----
    s_body_query = np.zeros(n, dtype=np.float32)
    if body_mat is not None:
        q_vec = embed.embed([draft.body], input_type="query")[0]
        q_vec = _unit(q_vec)
        sims = body_mat @ q_vec
        for eid, sim in zip(emb_ids, sims):
            s_body_query[id_to_pos[eid]] = sim
    log.debug("gather.signal name=body_query top=%s", _top1(s_body_query, ids))

    # ---- Signals 2, 4, 5: LLM calls — run in parallel ----
    corpus_bodies = [n.body for n in corpus]
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_bm25 = ex.submit(_bm25_mugi_scores, draft.body, ids, corpus_bodies, llm)
        f_sb   = ex.submit(_step_back_embedding, draft.body, llm, embed) if body_mat is not None else None
        f_hyde = ex.submit(_hyde_embedding, draft.body, llm, embed) if body_mat is not None else None

        s_bm25 = f_bm25.result()
        sb_vec   = f_sb.result()   if f_sb   is not None else None
        hyde_vec = f_hyde.result() if f_hyde is not None else None

    log.debug("gather.signal name=bm25_mugi_stem top=%s", _top1(s_bm25, ids))

    # ---- Signal 3: activation ----
    s_activation = _activation_scores(draft.id, ids, activation_scores)
    log.debug("gather.signal name=activation top=%s", _top1(s_activation, ids))

    # ---- Signal 4: step_back ----
    s_step_back = np.zeros(n, dtype=np.float32)
    if body_mat is not None and sb_vec is not None:
        sims = body_mat @ _unit(sb_vec)
        for eid, sim in zip(emb_ids, sims):
            s_step_back[id_to_pos[eid]] = sim
    log.debug("gather.signal name=step_back top=%s", _top1(s_step_back, ids))

    # ---- Signal 5: hyde_multi ----
    s_hyde = np.zeros(n, dtype=np.float32)
    if body_mat is not None and hyde_vec is not None:
        sims = body_mat @ _unit(hyde_vec)
        for eid, sim in zip(emb_ids, sims):
            s_hyde[id_to_pos[eid]] = sim
    log.debug("gather.signal name=hyde_multi top=%s", _top1(s_hyde, ids))

    # ---- Blend ----
    blended = (
        WEIGHTS["body_query"]     * _normalise(s_body_query)
        + WEIGHTS["bm25_mugi_stem"] * _normalise(s_bm25)
        + WEIGHTS["activation"]     * _normalise(s_activation)
        + WEIGHTS["step_back"]      * _normalise(s_step_back)
        + WEIGHTS["hyde_multi"]     * _normalise(s_hyde)
    )

    k = min(top_k, n)
    top_indices = np.argsort(-blended)[:k]
    results = [id_to_note[ids[i]] for i in top_indices]

    log.debug("gather.cluster ids=%s", [r.id for r in results])
    log.info("gather.complete results=%d top_id=%s", len(results), results[0].id if results else None)
    return results


# ---------------------------------------------------------------------------
# Porter stemmer + tokeniser (from retrieval-workbench/signals/bm25_mugi_stem.py)
# ---------------------------------------------------------------------------


def _stem(word: str) -> str:
    """Minimal Porter stemmer — handles the most common English suffixes."""
    if word.endswith("sses"):   word = word[:-2]
    elif word.endswith("ies"):  word = word[:-2]
    elif word.endswith("ss"):   pass
    elif word.endswith("s"):    word = word[:-1]
    if word.endswith("eed"):
        if len(word) > 4:       word = word[:-1]
    elif word.endswith("ed") and any(c in word[:-2] for c in "aeiou"):
        word = word[:-2]
        if word.endswith("at") or word.endswith("bl") or word.endswith("iz"):
            word += "e"
    elif word.endswith("ing") and any(c in word[:-3] for c in "aeiou"):
        word = word[:-3]
        if word.endswith("at") or word.endswith("bl") or word.endswith("iz"):
            word += "e"
    if word.endswith("y") and any(c in word[:-1] for c in "aeiou"):
        word = word[:-1] + "i"
    for suffix, replacement in [
        ("ational", "ate"), ("tional", "tion"), ("enci", "ence"),
        ("anci", "ance"), ("izer", "ize"), ("ising", "ise"),
        ("izing", "ize"), ("alism", "al"), ("ation", "ate"),
        ("ator", "ate"), ("ness", ""), ("fulness", "ful"), ("ousness", "ous"),
    ]:
        if word.endswith(suffix) and len(word) - len(suffix) > 2:
            word = word[:-len(suffix)] + replacement
            break
    return word


def _tokenize_stem(text: str) -> list[str]:
    return [_stem(w) for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 3]


# ---------------------------------------------------------------------------
# Signal helpers
# ---------------------------------------------------------------------------


def _bm25_mugi_scores(
    draft_body: str,
    ids: list[str],
    bodies: list[str],
    llm: LLMProvider,
) -> np.ndarray:
    from rank_bm25 import BM25Okapi

    corpus_tokens = [_tokenize_stem(b) for b in bodies]
    # Guard: BM25Okapi crashes when every document is empty
    if all(len(t) == 0 for t in corpus_tokens):
        return np.zeros(len(ids), dtype=np.float32)
    bm25 = BM25Okapi(corpus_tokens)

    pseudo = _get_pseudo_notes(draft_body, llm)
    query_tokens = _tokenize_stem(draft_body + " " + " ".join(pseudo))
    return np.array(bm25.get_scores(query_tokens), dtype=np.float32)


def _get_pseudo_notes(body: str, llm: LLMProvider) -> list[str]:
    """MuGI: ask LLM to generate N pseudo-notes for BM25 query expansion."""
    prompt = (
        f"You are helping expand a knowledge base search query.\n\n"
        f"Below is a note from a knowledge base:\n\n{body[:2000]}\n\n"
        f"Generate {N_PSEUDO} short notes (2-4 sentences each) about DIFFERENT "
        f"but related concepts. Each should use the vocabulary of that related "
        f"concept naturally.\n\n"
        f'Return JSON only: {{"pseudo_notes": ["<note1>", "<note2>", "<note3>"]}}'
    )
    raw = llm.complete(prompt, max_tokens=400, temperature=0.0)
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)["pseudo_notes"]
    except (json.JSONDecodeError, KeyError):
        return []


def _step_back_embedding(
    body: str, llm: LLMProvider, embed: EmbedProvider
) -> np.ndarray | None:
    """Step-back: abstract principle → embed as query."""
    prompt = (
        f"Below is a note from a knowledge base:\n\n{body[:2000]}\n\n"
        f"In 1-2 sentences, state the broader principle, theme, or mechanism "
        f"this note exemplifies — at a level of abstraction that would also "
        f"describe related concepts in neighbouring fields.\n\n"
        f'Return JSON only: {{"abstraction": "<principle>"}}'
    )
    raw = llm.complete(prompt, max_tokens=150, temperature=0.0)
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    try:
        abstraction = json.loads(raw)["abstraction"]
    except (json.JSONDecodeError, KeyError):
        m = re.search(r'"abstraction"\s*:\s*"(.*?)(?:"\s*[,}]|"$)', raw, re.DOTALL)
        abstraction = m.group(1) if m else body[:200]

    if not abstraction:
        return None
    vecs = embed.embed([abstraction], input_type="query")
    return vecs[0]


def _hyde_embedding(
    body: str, llm: LLMProvider, embed: EmbedProvider
) -> np.ndarray | None:
    """HyDE: generate N hypothetical peer notes → average their embeddings."""
    prompt = (
        f"Below is a note from a knowledge base:\n\n{body[:2000]}\n\n"
        f"Write {N_HYPOTHETICAL} short notes (3-5 sentences each) that would "
        f"plausibly exist alongside this one. Each should cover a DIFFERENT "
        f"closely related phenomenon, mechanism, or concept. "
        f"Write them as real knowledge base notes, not descriptions.\n\n"
        f'Return JSON only: {{"hypotheticals": ["<note1>", "<note2>", "<note3>"]}}'
    )
    raw = llm.complete(prompt, max_tokens=600, temperature=0.0)
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    try:
        hyps = json.loads(raw)["hypotheticals"]
        if not isinstance(hyps, list) or not hyps:
            raise ValueError
    except (json.JSONDecodeError, KeyError, ValueError):
        hyps = [body[:400]]

    vecs = embed.embed(hyps[:N_HYPOTHETICAL], input_type="document")
    avg = np.mean(np.stack(vecs), axis=0).astype(np.float32)
    return avg


def _activation_scores(
    query_id: str,
    ids: list[str],
    activation_scores: dict[str, float] | None,
) -> np.ndarray:
    """Convert pre-fetched activation scores dict to a score vector."""
    if not activation_scores:
        return np.zeros(len(ids), dtype=np.float32)
    return np.array(
        [activation_scores.get(nid, 0.0) for nid in ids],
        dtype=np.float32,
    )


# ---------------------------------------------------------------------------
# Maths helpers
# ---------------------------------------------------------------------------


def _unit(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    return v / norm if norm > 1e-9 else v


def _normalise(v: np.ndarray) -> np.ndarray:
    """Min-max normalise to [0, 1]. All-zero vectors stay zero."""
    m = v.max()
    return v / m if m > 0 else v


def _top1(scores: np.ndarray, ids: list[str]) -> str:
    if len(scores) == 0:
        return "none"
    i = int(np.argmax(scores))
    return f"{ids[i]}={scores[i]:.3f}"
