#!/usr/bin/env python3
"""End-to-end test: Form → Gather → Integrate

Tests the full pipeline against a synthetic article designed to trigger all 7
integration operations across the 299-note cognitive science corpus.

Setup (run once before e2e.py):
  cp -r ../spike4a-cluster/corpus ./corpus
  cp ../spike4a-cluster/embeddings_cache.json .
  cp -r ../retrieval-workbench/caches ./caches

Run:
  docker compose run --rm dev python spikes/spike-e2e/e2e.py
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from itertools import combinations
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if "SSL_CERT_FILE" in os.environ and not os.path.exists(os.environ["SSL_CERT_FILE"]):
    del os.environ["SSL_CERT_FILE"]

import numpy as np
import anthropic
import voyageai

E2E_DIR          = Path(__file__).parent
CORPUS_DIR       = E2E_DIR / "corpus"
EMBEDDINGS_CACHE = E2E_DIR / "embeddings_cache.json"
CACHES_DIR       = E2E_DIR / "caches"
RESULTS_DIR      = E2E_DIR / "results"
ARTICLE_PATH     = E2E_DIR / "article.md"

FORM_MODEL       = "claude-opus-4-6"
INTEGRATE_MODEL  = "claude-opus-4-6"
SIGNAL_MODEL     = "claude-haiku-4-5-20251001"
VOYAGE_MODEL     = "voyage-3-lite"

WEIGHTS = {
    "body_query":    0.450,
    "bm25_mugi_stem": 0.270,
    "activation":    0.180,
    "step_back":     0.050,
    "hyde_multi":    0.050,
}
CLUSTER_K = 20

llm   = anthropic.Anthropic()
voyage = voyageai.Client()


# ---------------------------------------------------------------------------
# Data loading  (from workbench/main.py)
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.index("---", 3)
    fm_text = text[3:end].strip()
    body = text[end + 3:].strip()
    meta: dict = {}
    for line in fm_text.splitlines():
        if ":" in line and not line.startswith(" ") and not line.startswith("-"):
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()
    return meta, body


def load_corpus() -> list[dict]:
    notes = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        text = path.read_text()
        meta, body = parse_frontmatter(text)
        if not meta.get("id"):
            continue
        notes.append({"id": meta["id"], "body": body, "path": path, "raw": text})
    return notes


def load_embeddings(notes: list[dict]) -> tuple[list[str], np.ndarray, dict[str, int]]:
    raw = json.loads(EMBEDDINGS_CACHE.read_text())
    id_to_emb = {nid: emb for nid, emb in zip(raw["ids"], raw["body"])}

    # Auto-embed any corpus notes not in the cache (e.g. fabricated test notes)
    uncached = [n for n in notes if n["id"] not in id_to_emb]
    if uncached:
        print(f"  Auto-embedding {len(uncached)} notes not in cache...")
        for n in uncached:
            result = voyage.embed([n["body"]], model=VOYAGE_MODEL, input_type="document")
            id_to_emb[n["id"]] = result.embeddings[0]

    note_id_set = {n["id"] for n in notes}
    ids = [nid for nid in id_to_emb if nid in note_id_set]
    vecs = []
    for nid in ids:
        v = np.array(id_to_emb[nid], dtype=np.float32)
        v /= (np.linalg.norm(v) + 1e-9)
        vecs.append(v)
    body_mat = np.stack(vecs)
    id_to_pos = {nid: i for i, nid in enumerate(ids)}
    return ids, body_mat, id_to_pos


# ---------------------------------------------------------------------------
# Retrieval utilities  (from harness.py)
# ---------------------------------------------------------------------------

def normalise(v: np.ndarray) -> np.ndarray:
    m = v.max()
    return v / m if m > 0 else v


def top_k(scores: np.ndarray, ids: list[str], k: int) -> list[tuple[str, float]]:
    idxs = np.argsort(-scores)[:k]
    return [(ids[i], float(scores[i])) for i in idxs]


# ---------------------------------------------------------------------------
# BM25 + stemming  (from signals/bm25_mugi_stem.py)
# ---------------------------------------------------------------------------

def _stem(word: str) -> str:
    if word.endswith("sses"):    word = word[:-2]
    elif word.endswith("ies"):   word = word[:-2]
    elif word.endswith("ss"):    pass
    elif word.endswith("s"):     word = word[:-1]
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


def build_bm25(notes: list[dict], ids: list[str]):
    from rank_bm25 import BM25Okapi
    id_to_body = {n["id"]: n["body"] for n in notes}
    corpus_tokens = [_tokenize_stem(id_to_body.get(nid, "")) for nid in ids]
    return BM25Okapi(corpus_tokens), id_to_body


# ---------------------------------------------------------------------------
# Activation graph  (from signals/activation.py)
# ---------------------------------------------------------------------------

LAMBDA = 0.05


class ActivationGraph:
    def __init__(self):
        self._w: dict[frozenset, float] = defaultdict(float)

    def add_event(self, qid: str, gold_ids: list[str], age_days: float = 0.0) -> None:
        d = math.exp(-LAMBDA * age_days)
        for gid in gold_ids:
            self._w[frozenset([qid, gid])] += d
        for a, b in combinations(gold_ids, 2):
            self._w[frozenset([a, b])] += d

    def vector(self, qid: str, ids: list[str]) -> np.ndarray:
        return np.array([self._w.get(frozenset([qid, nid]), 0.0) for nid in ids],
                        dtype=np.float32)


# ---------------------------------------------------------------------------
# On-demand signal functions for out-of-corpus draft notes
# New entries cached with "e2e_" prefix files to avoid polluting workbench caches
# ---------------------------------------------------------------------------

def _load_cache(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def _save_cache(path: Path, cache: dict) -> None:
    path.write_text(json.dumps(cache, indent=2))


def embed_query(draft_id: str, body: str) -> np.ndarray:
    """Embed draft body with input_type='query'. Cached per draft_id."""
    cache_path = CACHES_DIR / "e2e_query_embeddings.json"
    cache = _load_cache(cache_path)
    if draft_id not in cache:
        result = voyage.embed([body], model=VOYAGE_MODEL, input_type="query")
        cache[draft_id] = result.embeddings[0]
        _save_cache(cache_path, cache)
    v = np.array(cache[draft_id], dtype=np.float32)
    v /= (np.linalg.norm(v) + 1e-9)
    return v


def get_pseudo_notes(draft_id: str, body: str) -> list[str]:
    """Generate MuGI pseudo-notes for BM25 expansion. Cached per draft_id."""
    cache_path = CACHES_DIR / "e2e_pseudo_notes.json"
    cache = _load_cache(cache_path)
    if draft_id not in cache:
        prompt = (
            f"You are helping expand a knowledge base search query.\n\n"
            f"Below is a note from a cognitive science knowledge base:\n\n"
            f"{body[:2000]}\n\n"
            f"Generate 3 short notes (2-4 sentences each) about DIFFERENT "
            f"but related cognitive science concepts. Each should use the vocabulary "
            f"of that related concept naturally.\n\n"
            f'Return JSON only: {{"pseudo_notes": ["<note1>", "<note2>", "<note3>"]}}'
        )
        resp = llm.messages.create(model=SIGNAL_MODEL, max_tokens=400,
                                   messages=[{"role": "user", "content": prompt}])
        raw = re.sub(r"^```(?:json)?\s*", "", resp.content[0].text.strip())
        raw = re.sub(r"\s*```$", "", raw)
        try:
            cache[draft_id] = json.loads(raw)["pseudo_notes"]
        except (json.JSONDecodeError, KeyError):
            cache[draft_id] = []
        _save_cache(cache_path, cache)
    return cache[draft_id]


def get_step_back_embedding(draft_id: str, body: str) -> np.ndarray:
    """Generate step-back abstraction and embed it. Cached per draft_id."""
    cache_path = CACHES_DIR / "e2e_step_back.json"
    cache = _load_cache(cache_path)
    if draft_id not in cache:
        prompt = (
            f"Below is a note from a cognitive science knowledge base:\n\n"
            f"{body[:2000]}\n\n"
            f"In 1-2 sentences, state the broader principle, theme, or mechanism "
            f"this note exemplifies — at a level of abstraction that would also "
            f"describe related concepts in neighbouring fields.\n\n"
            f'Return JSON only: {{"abstraction": "<principle>"}}'
        )
        resp = llm.messages.create(model=SIGNAL_MODEL, max_tokens=150,
                                   messages=[{"role": "user", "content": prompt}])
        raw = re.sub(r"^```(?:json)?\s*", "", resp.content[0].text.strip())
        raw = re.sub(r"\s*```$", "", raw)
        try:
            abst = json.loads(raw)["abstraction"]
        except (json.JSONDecodeError, KeyError):
            m = re.search(r'"abstraction"\s*:\s*"(.*?)(?:"\s*[,}]|"$)', raw, re.DOTALL)
            abst = m.group(1) if m else body[:200]
        cache[draft_id] = {"abstraction": abst}
        _save_cache(cache_path, cache)

    entry = cache[draft_id]
    if "embedding" not in entry:
        result = voyage.embed([entry["abstraction"]], model=VOYAGE_MODEL, input_type="query")
        entry["embedding"] = result.embeddings[0]
        _save_cache(cache_path, cache)

    v = np.array(entry["embedding"], dtype=np.float32)
    v /= (np.linalg.norm(v) + 1e-9)
    return v


def get_hyde_embedding(draft_id: str, body: str) -> np.ndarray:
    """Generate 3 hypothetical peer-notes and return averaged embedding. Cached."""
    cache_path = CACHES_DIR / "e2e_hyde_multi.json"
    cache = _load_cache(cache_path)
    if draft_id not in cache:
        prompt = (
            f"Below is a note from a cognitive science knowledge base:\n\n"
            f"{body[:2000]}\n\n"
            f"Write 3 short notes (3-5 sentences each) that would plausibly exist "
            f"alongside this one in a cognitive science knowledge base. Each should "
            f"cover a DIFFERENT closely related phenomenon, mechanism, or concept. "
            f"Write them as real knowledge base notes, not descriptions.\n\n"
            f'Return JSON only: {{"hypotheticals": ["<note1>", "<note2>", "<note3>"]}}'
        )
        resp = llm.messages.create(model=SIGNAL_MODEL, max_tokens=600,
                                   messages=[{"role": "user", "content": prompt}])
        raw = re.sub(r"^```(?:json)?\s*", "", resp.content[0].text.strip())
        raw = re.sub(r"\s*```$", "", raw)
        try:
            hyps = json.loads(raw)["hypotheticals"]
            if not isinstance(hyps, list):
                raise ValueError
        except (json.JSONDecodeError, KeyError, ValueError):
            hyps = [body[:400]]
        result = voyage.embed(hyps[:3], model=VOYAGE_MODEL, input_type="document")
        avg_emb = np.mean([e for e in result.embeddings], axis=0).tolist()
        cache[draft_id] = {"hypotheticals": hyps, "embedding": avg_emb}
        _save_cache(cache_path, cache)

    v = np.array(cache[draft_id]["embedding"], dtype=np.float32)
    v /= (np.linalg.norm(v) + 1e-9)
    return v


# ---------------------------------------------------------------------------
# Gather
# ---------------------------------------------------------------------------

def gather(
    draft_id: str,
    draft_body: str,
    ids: list[str],
    body_mat: np.ndarray,
    bm25,
    activation_events: list[dict],
) -> list[tuple[str, float]]:
    """Return top-CLUSTER_K (note_id, blended_score) pairs."""
    scores: dict[str, np.ndarray] = {}

    # body_query: asymmetric embedding
    q_emb = embed_query(draft_id, draft_body)
    scores["body_query"] = body_mat @ q_emb

    # bm25_mugi_stem: BM25 with pseudo-note MuGI expansion + stemming
    pseudo = get_pseudo_notes(draft_id, draft_body)
    tokens = _tokenize_stem(draft_body + " " + " ".join(pseudo))
    scores["bm25_mugi_stem"] = np.array(bm25.get_scores(tokens), dtype=np.float32)

    # activation: co-activation from prior integration events
    graph = ActivationGraph()
    for ev in activation_events:
        graph.add_event(ev["qid"], ev["gold_ids"])
    scores["activation"] = graph.vector(draft_id, ids)

    # step_back: principle-level abstraction embedding
    sb_emb = get_step_back_embedding(draft_id, draft_body)
    scores["step_back"] = body_mat @ sb_emb

    # hyde_multi: averaged hypothetical note embeddings
    hyde_emb = get_hyde_embedding(draft_id, draft_body)
    scores["hyde_multi"] = body_mat @ hyde_emb

    # weighted blend
    blended = sum(WEIGHTS[k] * normalise(scores[k]) for k in WEIGHTS)
    return top_k(blended, ids, CLUSTER_K)


# ---------------------------------------------------------------------------
# Integration  (prompts from spike3/spike.py)
# ---------------------------------------------------------------------------

INTEGRATION_PROMPT = """\
You maintain a knowledge base of topic notes. You have a draft note and a \
cluster of related existing notes.

Draft note:
{draft}

Existing notes in cluster:
{cluster}

Decide what action to take. Choose exactly one:

- UPDATE: the draft adds to an existing note. Rewrite that note to synthesise \
old and new — do not append. Specify which note by its id field.
- CREATE: the draft covers a topic not in the cluster. Create a new note with \
links to relevant existing notes.
- SPLIT: an existing note conflates two distinct topics that the draft \
clarifies should be separate. Specify which note and how to split it.
- MERGE: two existing notes in the cluster cover the same topic. The draft \
confirms they should be one. Specify which notes.
- SYNTHESISE: the draft reveals a connection between two existing notes that \
neither captures. Create a new structure note articulating the bridging \
principle. Specify which notes it bridges.
- NOTHING: the draft is already fully covered by the existing cluster. No \
action needed.
- STUB: the cluster is sparse or empty — this is a new topic without an \
established neighbourhood. Create a provisional note at low confidence.

For UPDATE and CREATE, if the draft contradicts an existing note rather than \
adding to it, use CREATE and add a `contradicts` link to the conflicting \
note — keep competing views as separate notes.

If the cluster is empty, STUB is the appropriate default unless the draft is \
clearly a subtopic of notes in the broader knowledge base.

Output JSON only. Schema:
{{
  "operation": "<one of the seven>",
  "target_note_ids": ["<id>", ...],
  "reasoning": "<one or two sentences>",
  "confidence": <0.0 to 1.0>
}}"""


STEP2_PROMPTS = {
    "UPDATE": """\
Execute an UPDATE operation on the existing note.

Draft note (new content to integrate):
{draft}

Existing note to update:
{targets}

Rewrite the existing note to synthesise old and new content into a single \
coherent note. Do not append — integrate the new material throughout so the \
result reads as a unified topic note. Preserve the frontmatter (id, type, \
confidence, tags, links) from the existing note, updating the `updated` \
timestamp to today and the `context` field if appropriate.

Output the complete updated note (frontmatter + body).""",

    "CREATE": """\
Execute a CREATE operation.

Draft note (content for new note):
{draft}

Related notes in cluster (for linking):
{targets}

Create a new topic note. Use this frontmatter format:
---
id: {new_id}
type: topic
confidence: 0.7
context: >
  <one sentence describing the note's topic>
tags: []
links:
  - id: <related_note_id>
created: {today}
updated: {today}
---

Write the body as a coherent topic note. Include links to the most relevant \
existing notes from the cluster.

Output the complete new note (frontmatter + body).""",

    "SPLIT": """\
Execute a SPLIT operation on the existing note.

Draft note (clarifies the distinction):
{draft}

Existing note to split:
{targets}

Produce TWO separate notes. Separate them with a line containing only \
'---SPLIT---'. The first note should cover the primary topic (keep the \
original id). The second note should cover the distinct topic the draft \
clarifies should be separate (assign a new id by appending '-b' to the \
original). Each note should be complete and coherent on its own.

Output both notes separated by ---SPLIT---.""",

    "MERGE": """\
Execute a MERGE operation on two existing notes.

Draft note (confirms these should be unified):
{draft}

Existing notes to merge:
{targets}

Produce ONE unified note combining both existing notes. Use the id of the \
first (primary) note. Preserve all key content from both. The merged note \
should read as a single coherent topic note, not two notes joined with \
connectives. Update the `updated` timestamp to today.

Output the complete merged note (frontmatter + body).""",

    "SYNTHESISE": """\
Execute a SYNTHESISE operation.

Draft note (reveals the connection):
{draft}

Existing notes being bridged:
{targets}

Create a new structure note that articulates the bridging principle connecting \
the two target notes. This note should express what neither target note \
currently captures — the connecting insight or unifying mechanism. Use this \
frontmatter format:
---
id: {new_id}
type: synthesised
confidence: 0.7
context: >
  <one sentence describing the bridging principle>
tags: []
links:
  - id: <first_target_id>
  - id: <second_target_id>
created: {today}
updated: {today}
---

Output the complete new structure note (frontmatter + body).""",

    "STUB": """\
Execute a STUB operation.

Draft note (new topic without established neighbourhood):
{draft}

Create a minimal stub note. Include: concept title, 1-2 sentence definition, \
and 3-5 synonyms or related terms to make the note retrievable in future. \
Keep it brief but specific. Use this frontmatter format:
---
id: {new_id}
type: stub
confidence: 0.4
context: >
  <one sentence>
tags: []
links: []
created: {today}
updated: {today}
---

Output the complete stub note (frontmatter + body).""",

    "NOTHING": None,  # no step 2
}


def _parse_decision(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"operation": "PARSE_ERROR", "target_note_ids": [],
                "reasoning": raw[:200], "confidence": 0.0}
    json_str = match.group()

    # Attempt 1: clean parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Attempt 2: strip control characters that can break JSON strings
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', json_str)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Attempt 3: extract fields individually via regex
    op_m   = re.search(r'"operation"\s*:\s*"([^"]+)"', json_str)
    ids_m  = re.search(r'"target_note_ids"\s*:\s*(\[[^\]]*\])', json_str)
    reas_m = re.search(r'"reasoning"\s*:\s*"(.*?)"(?:\s*[,}])', json_str, re.DOTALL)
    conf_m = re.search(r'"confidence"\s*:\s*([0-9.]+)', json_str)
    if op_m:
        target_ids: list = []
        if ids_m:
            try:
                target_ids = json.loads(ids_m.group(1))
            except Exception:
                target_ids = re.findall(r'"([^"]+)"', ids_m.group(1))
        return {
            "operation": op_m.group(1),
            "target_note_ids": target_ids,
            "reasoning": reas_m.group(1).replace('\\"', '"') if reas_m else "",
            "confidence": float(conf_m.group(1)) if conf_m else 0.5,
        }

    return {"operation": "PARSE_ERROR", "target_note_ids": [],
            "reasoning": json_str[:200], "confidence": 0.0}


def step1_classify(draft_body: str, cluster_notes: list[dict]) -> dict:
    """Step 1: classify the operation. Returns decision dict."""
    if cluster_notes:
        cluster_text = "\n\n---\n\n".join(n["raw"] for n in cluster_notes)
    else:
        cluster_text = "(empty — no existing notes in cluster)"
    prompt = INTEGRATION_PROMPT.format(draft=draft_body, cluster=cluster_text)
    resp = llm.messages.create(
        model=INTEGRATE_MODEL,
        max_tokens=512,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_decision(resp.content[0].text.strip())


def step2_execute(decision: dict, draft_body: str, target_notes: list[dict],
                  new_id: str) -> str | None:
    """Step 2: execute the operation. Returns new note content or None."""
    op = decision["operation"]
    if op == "NOTHING" or op not in STEP2_PROMPTS:
        return None
    template = STEP2_PROMPTS[op]
    if template is None:
        return None

    targets_text = "\n\n---\n\n".join(n["raw"] for n in target_notes) if target_notes else ""
    today = datetime.now().strftime("%Y-%m-%dT00:00:00Z")
    prompt = template.format(
        draft=draft_body,
        targets=targets_text,
        new_id=new_id,
        today=today,
    )
    # SPLIT/MERGE must rewrite ≥1 full existing note; UPDATE rewrites one.
    # STUB/CREATE are fresh notes, typically shorter.
    max_tok = 4096 if op in ("UPDATE", "SPLIT", "MERGE", "SYNTHESISE") else 2048
    resp = llm.messages.create(
        model=INTEGRATE_MODEL,
        max_tokens=max_tok,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


# ---------------------------------------------------------------------------
# Corpus mutations
# ---------------------------------------------------------------------------

def apply_operation(
    decision: dict,
    content: str,
    notes: list[dict],
    ids: list[str],
    body_mat: np.ndarray,
    id_to_pos: dict[str, int],
    bm25_state: dict,        # mutable: {"bm25": BM25Okapi, "id_to_body": dict}
) -> tuple[list[dict], list[str], np.ndarray, dict[str, int]]:
    """Write content to corpus and update in-memory state for subsequent drafts.
    Returns (updated notes, ids, body_mat, id_to_pos)."""
    op = decision["operation"]
    if not content or op == "NOTHING":
        return notes, ids, body_mat, id_to_pos

    if op in ("UPDATE", "MERGE"):
        primary_id = decision["target_note_ids"][0] if decision["target_note_ids"] else None
        if primary_id:
            note = next((n for n in notes if n["id"] == primary_id), None)
            if note:
                note["path"].write_text(content)
                meta, body = parse_frontmatter(content)
                note["body"] = body
                note["raw"] = content
                bm25_state["id_to_body"][primary_id] = body
                print(f"    → wrote {note['path'].name}")

    elif op in ("CREATE", "SYNTHESISE", "STUB"):
        # Parse id from generated content
        meta, body = parse_frontmatter(content)
        new_id = meta.get("id", decision.get("_new_id", "e2e-unknown"))
        new_path = CORPUS_DIR / f"{new_id}.md"
        new_path.write_text(content)
        new_note = {"id": new_id, "body": body, "path": new_path, "raw": content}
        notes.append(new_note)
        # Embed and extend body_mat
        try:
            result = voyage.embed([body], model=VOYAGE_MODEL, input_type="document")
            v = np.array(result.embeddings[0], dtype=np.float32)
            v /= (np.linalg.norm(v) + 1e-9)
            body_mat = np.vstack([body_mat, v[np.newaxis, :]])
            ids.append(new_id)
            id_to_pos[new_id] = len(ids) - 1
            bm25_state["id_to_body"][new_id] = body
        except Exception as e:
            print(f"    Warning: could not embed new note {new_id}: {e}")
        print(f"    → created {new_path.name}")

    elif op == "SPLIT":
        parts = content.split("---SPLIT---")
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            meta, body = parse_frontmatter(part)
            nid = meta.get("id", f"e2e-split-{i}")
            path = CORPUS_DIR / f"{nid}.md"
            path.write_text(part)
            if i == 0 and decision["target_note_ids"]:
                primary_id = decision["target_note_ids"][0]
                note = next((n for n in notes if n["id"] == primary_id), None)
                if note:
                    note["body"] = body
                    note["raw"] = part
                    bm25_state["id_to_body"][primary_id] = body
            else:
                new_note = {"id": nid, "body": body, "path": path, "raw": part}
                notes.append(new_note)
                ids.append(nid)
                id_to_pos[nid] = len(ids) - 1
                bm25_state["id_to_body"][nid] = body
            print(f"    → wrote {path.name}")

    # Rebuild BM25 with updated corpus
    from rank_bm25 import BM25Okapi
    corpus_tokens = [_tokenize_stem(bm25_state["id_to_body"].get(nid, "")) for nid in ids]
    bm25_state["bm25"] = BM25Okapi(corpus_tokens)

    return notes, ids, body_mat, id_to_pos


# ---------------------------------------------------------------------------
# Form phase  (from spike2/spike.py — Approach B)
# ---------------------------------------------------------------------------

APPROACH_B_PROMPT = """\
The following essay covers several distinct topic areas.
For each broad topic area, produce a topic note.

Guidelines:
- A topic area is broad enough to warrant its own Wikipedia article covering many aspects.
- Named techniques, mechanisms, or specific phenomena within a broader area belong inside \
one note — do not create a separate note for each named concept.
- Draw relevant content from anywhere in the essay — relevant material may be scattered \
across paragraphs, not just adjacent.
- If content sits at the boundary between two topics, include it in both relevant notes.
- Write in your own words.

Format each topic note as:

## [Topic name]

[Content]

Essay:
{article}"""


def run_form(article: str) -> str:
    resp = llm.messages.create(
        model=FORM_MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": APPROACH_B_PROMPT.format(article=article)}],
    )
    return resp.content[0].text.strip()


def parse_draft_notes(form_output: str) -> list[dict]:
    """Parse Approach B output into list of {title, body, id} dicts."""
    # Split on ## headings
    sections = re.split(r"\n(?=## )", form_output)
    notes = []
    for section in sections:
        section = section.strip()
        if not section.startswith("##"):
            continue
        lines = section.split("\n", 1)
        title = lines[0].lstrip("#").strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if title and body:
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            notes.append({"title": title, "body": body, "id": f"e2e-draft-{slug}"})
    return notes


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(
    draft_notes: list[dict],
    results: list[dict],
    ts: str,
) -> Path:
    lines = [
        f"# E2E Test Results — {ts}",
        f"*{len(draft_notes)} draft notes from Form phase*",
        "",
        "---",
        "",
        "## Ground truth comparison",
        "",
        "| Draft note | Expected | Actual | Match |",
        "|---|---|---|---|",
    ]

    # Load ground truth predictions for comparison display
    gt_path = E2E_DIR / "ground_truth.md"
    gt_text = gt_path.read_text() if gt_path.exists() else ""

    for r in results:
        op = r["decision"].get("operation", "?")
        targets = ", ".join(r["decision"].get("target_note_ids", [])) or "—"
        lines.append(f"| {r['title']} | (see ground_truth.md) | {op}: {targets} | — |")

    lines += ["", "---", "", "## Sequential integration log", ""]

    for i, r in enumerate(results, 1):
        lines += [
            f"### {i}. {r['title']}",
            "",
            "**Draft note:**",
            "",
            r["body"],
            "",
            "**Retrieved cluster (top 20):**",
            "",
            "| Rank | Note ID | Score |",
            "|------|---------|-------|",
        ]
        for rank, (nid, score) in enumerate(r["cluster"], 1):
            lines.append(f"| {rank} | {nid} | {score:.4f} |")

        dec = r["decision"]
        lines += [
            "",
            f"**Step 1 decision:** `{dec.get('operation', '?')}` "
            f"(confidence: {dec.get('confidence', 0):.2f})",
            f"*Reasoning: {dec.get('reasoning', '')}*",
            f"*Targets: {', '.join(dec.get('target_note_ids', [])) or 'none'}*",
            "",
        ]

        if r.get("before_states"):
            for nid, before in r["before_states"].items():
                after = r.get("after_states", {}).get(nid, "")
                lines += [
                    f"**{nid} — before:**",
                    "",
                    "```",
                    before,
                    "```",
                    "",
                    f"**{nid} — after:**",
                    "",
                    "```",
                    after,
                    "```",
                    "",
                ]
        elif r.get("new_content"):
            lines += [
                "**New note content:**",
                "",
                "```",
                r["new_content"],
                "```",
                "",
            ]

        lines += ["---", ""]

    path = RESULTS_DIR / f"run-{ts}.md"
    path.write_text("\n".join(lines))
    (RESULTS_DIR / "latest.md").write_text("\n".join(lines))
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_loop(
    loop_num: int,
    article_body: str,
    ts: str,
    notes: list[dict],
    ids: list[str],
    body_mat: np.ndarray,
    id_to_pos: dict[str, int],
    bm25_state: dict,
    activation_events: list[dict],
    new_note_counter: list[int],
) -> tuple[list[dict], list[dict], list[str], np.ndarray, dict[str, int]]:
    """Run one Form → Gather → Integrate pass. Returns (results, notes, ids, body_mat, id_to_pos)."""
    print(f"\n{'='*70}")
    print(f"LOOP {loop_num} — corpus has {len(notes)} notes")
    print(f"{'='*70}")

    print(f"\nRunning Form phase (Approach B)...")
    form_output = run_form(article_body)
    draft_notes = parse_draft_notes(form_output)
    print(f"  Form produced {len(draft_notes)} draft notes:")
    for dn in draft_notes:
        # Suffix IDs with loop number so signal caches stay distinct
        dn["id"] = f"{dn['id']}-l{loop_num}"
        print(f"    - {dn['title']}")

    (RESULTS_DIR / f"form-{ts}-loop{loop_num}.md").write_text(form_output)

    results = []
    for i, dn in enumerate(draft_notes, 1):
        print(f"\n[{i}/{len(draft_notes)}] {dn['title']}")

        # Gather
        print("  Gathering...")
        cluster_pairs = gather(
            draft_id=dn["id"],
            draft_body=dn["body"],
            ids=ids,
            body_mat=body_mat,
            bm25=bm25_state["bm25"],
            activation_events=activation_events,
        )
        top5 = cluster_pairs[:5]
        print(f"  Top 5: {[nid for nid, _ in top5]}")

        # Resolve cluster notes (full objects for top-20)
        cluster_notes = [
            n for n in notes
            if n["id"] in {nid for nid, _ in cluster_pairs}
        ]

        # Step 1: classify
        print("  Step 1: classify...")
        decision = step1_classify(dn["body"], cluster_notes)
        op = decision.get("operation", "?")
        print(f"  → {op} | confidence={decision.get('confidence', 0):.2f}")
        print(f"  → {decision.get('reasoning', '')[:120]}")

        # Capture before states for write operations
        before_states: dict[str, str] = {}
        target_ids = decision.get("target_note_ids", [])
        if op in ("UPDATE", "MERGE", "SPLIT"):
            for tid in target_ids:
                tn = next((n for n in notes if n["id"] == tid), None)
                if tn:
                    before_states[tid] = tn["raw"]

        # Step 2: execute
        new_content = None
        after_states: dict[str, str] = {}
        if op != "NOTHING" and op in STEP2_PROMPTS:
            print("  Step 2: execute...")
            target_notes = [n for n in notes if n["id"] in target_ids]
            new_note_counter[0] += 1
            new_id = f"e2e-new-{new_note_counter[0]:03d}"
            decision["_new_id"] = new_id
            new_content = step2_execute(decision, dn["body"], target_notes, new_id)

            if new_content:
                # Capture after states
                if op in ("UPDATE", "MERGE"):
                    after_states[target_ids[0]] = new_content if target_ids else ""
                elif op == "SPLIT":
                    parts = new_content.split("---SPLIT---")
                    for j, part in enumerate(parts):
                        key = target_ids[0] if j == 0 and target_ids else f"split-{j}"
                        after_states[key] = part.strip()

                # Apply to corpus
                notes, ids, body_mat, id_to_pos = apply_operation(
                    decision, new_content, notes, ids, body_mat, id_to_pos, bm25_state
                )

        # Record activation event for non-NOTHING/STUB decisions
        if op not in ("NOTHING", "STUB", "PARSE_ERROR") and target_ids:
            activation_events.append({"qid": dn["id"], "gold_ids": target_ids})
            print(f"  → activation event recorded: {dn['id']} → {target_ids}")

        results.append({
            "title": dn["title"],
            "body": dn["body"],
            "cluster": cluster_pairs,
            "decision": decision,
            "before_states": before_states,
            "after_states": after_states,
            "new_content": new_content if op not in ("UPDATE", "MERGE", "SPLIT") else None,
        })

    return results, notes, ids, body_mat, id_to_pos


def write_multi_loop_report(
    all_loop_results: list[list[dict]],
    ts: str,
) -> Path:
    lines = [
        f"# E2E Double-Loop Results — {ts}",
        "",
        "---",
        "",
        "## Loop comparison summary",
        "",
        "| Draft note | Loop 1 | Loop 2 |",
        "|---|---|---|",
    ]
    loop1, loop2 = all_loop_results[0], all_loop_results[1]
    for r1, r2 in zip(loop1, loop2):
        op1 = r1["decision"].get("operation", "?")
        op2 = r2["decision"].get("operation", "?")
        t1  = ", ".join(r1["decision"].get("target_note_ids", [])) or "—"
        t2  = ", ".join(r2["decision"].get("target_note_ids", [])) or "—"
        lines.append(f"| {r1['title']} | {op1}: {t1} | {op2}: {t2} |")

    for loop_num, results in enumerate(all_loop_results, 1):
        draft_notes = [{"title": r["title"]} for r in results]
        loop_lines = write_report.__wrapped__ if hasattr(write_report, "__wrapped__") else None
        # Inline the per-loop section
        lines += [
            "", "---", "",
            f"## Loop {loop_num} — sequential integration log", "",
        ]
        for i, r in enumerate(results, 1):
            lines += [
                f"### L{loop_num}.{i}. {r['title']}",
                "",
                "**Draft note:**",
                "",
                r["body"],
                "",
                "**Retrieved cluster (top 20):**",
                "",
                "| Rank | Note ID | Score |",
                "|------|---------|-------|",
            ]
            for rank, (nid, score) in enumerate(r["cluster"], 1):
                lines.append(f"| {rank} | {nid} | {score:.4f} |")

            dec = r["decision"]
            lines += [
                "",
                f"**Step 1 decision:** `{dec.get('operation', '?')}` "
                f"(confidence: {dec.get('confidence', 0):.2f})",
                f"*Reasoning: {dec.get('reasoning', '')}*",
                f"*Targets: {', '.join(dec.get('target_note_ids', [])) or 'none'}*",
                "",
            ]

            if r.get("before_states"):
                for nid, before in r["before_states"].items():
                    after = r.get("after_states", {}).get(nid, "")
                    lines += [
                        f"**{nid} — before:**",
                        "", "```", before, "```", "",
                        f"**{nid} — after:**",
                        "", "```", after, "```", "",
                    ]
            elif r.get("new_content"):
                lines += [
                    "**New note content:**",
                    "", "```", r["new_content"], "```", "",
                ]

            lines += ["---", ""]

    path = RESULTS_DIR / f"double-loop-{ts}.md"
    path.write_text("\n".join(lines))
    (RESULTS_DIR / "latest.md").write_text("\n".join(lines))
    return path


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--loops", type=int, default=1,
                        help="Number of Form→Gather→Integrate passes (default 1)")
    parser.add_argument("--article", type=str, default=None,
                        help="Path to article file (default: article.md)")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")

    print("Loading corpus and embeddings...")
    notes = load_corpus()
    ids, body_mat, id_to_pos = load_embeddings(notes)
    notes = [n for n in notes if n["id"] in id_to_pos]
    print(f"  {len(notes)} notes, body_mat shape={body_mat.shape}")

    print("Building BM25 index...")
    bm25, id_to_body = build_bm25(notes, ids)
    bm25_state = {"bm25": bm25, "id_to_body": id_to_body}

    article_path = Path(args.article) if args.article else ARTICLE_PATH
    article = article_path.read_text()
    article_lines = article.strip().splitlines()
    if article_lines[0].startswith("#"):
        article_lines = article_lines[1:]
    article_body = "\n".join(article_lines).strip()
    print(f"Article: {article_path.name}")

    activation_events: list[dict] = []
    new_note_counter = [0]
    all_loop_results: list[list[dict]] = []

    for loop_num in range(1, args.loops + 1):
        results, notes, ids, body_mat, id_to_pos = run_loop(
            loop_num=loop_num,
            article_body=article_body,
            ts=ts,
            notes=notes,
            ids=ids,
            body_mat=body_mat,
            id_to_pos=id_to_pos,
            bm25_state=bm25_state,
            activation_events=activation_events,
            new_note_counter=new_note_counter,
        )
        all_loop_results.append(results)

        print(f"\n=== LOOP {loop_num} SUMMARY ===")
        for r in results:
            op      = r["decision"].get("operation", "?")
            conf    = r["decision"].get("confidence", 0)
            targets = ", ".join(r["decision"].get("target_note_ids", [])) or "—"
            print(f"  {r['title'][:50]:<50} {op:<12} {conf:.2f}  {targets}")

    print(f"\nWriting report...")
    if args.loops > 1:
        path = write_multi_loop_report(all_loop_results, ts)
    else:
        path = write_report([{"title": r["title"]} for r in all_loop_results[0]],
                            all_loop_results[0], ts)
    print(f"Results written to {path}")


if __name__ == "__main__":
    main()
