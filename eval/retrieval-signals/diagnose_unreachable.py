#!/usr/bin/env python3
"""Diagnose the 7% of gold notes unreachable by any signal at K=20.

Identifies which notes are never in any signal's top-20, then profiles them:
  - Body length (short notes may lack enough signal)
  - Number of incoming links in the corpus
  - Number of outgoing links
  - Tags
  - How many events they appear as gold in
  - Comparison of body content vs the query note that missed them

Run:
  docker compose run --rm dev python spikes/retrieval-workbench/diagnose_unreachable.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if "SSL_CERT_FILE" in os.environ and not os.path.exists(os.environ["SSL_CERT_FILE"]):
    del os.environ["SSL_CERT_FILE"]

import numpy as np

WORKBENCH_DIR = Path(__file__).parent
SPIKE4A_DIR   = WORKBENCH_DIR.parent / "spike4a-cluster"
SPIKE4D_DIR   = WORKBENCH_DIR.parent / "spike4d-llm-ground-truth"
CORPUS_DIR    = SPIKE4A_DIR / "corpus"
EMBEDDINGS_CACHE   = SPIKE4A_DIR / "embeddings_cache.json"
GROUND_TRUTH_CACHE = SPIKE4D_DIR / "ground_truth_cache.json"
CACHES_DIR    = WORKBENCH_DIR / "caches"

K_DIAG = 20
TOP_EXAMPLES = 8   # how many unreachable (query, gold) pairs to print in detail


# ---------------------------------------------------------------------------
# Data loading (shared with main.py)
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
        # Also capture links and tags from frontmatter
        links_out = []
        tags = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("- [[") and "]]" in line:
                target = line[4:line.index("]]")]
                links_out.append(target)
            elif line.startswith("tags:"):
                tags = [t.strip() for t in line[5:].split(",") if t.strip()]
        # Also find wiki-style links in body
        body_links = re.findall(r"\[\[([^\]]+)\]\]", body)
        links_out.extend(body_links)
        notes.append({
            "id": meta["id"],
            "body": body,
            "links_out": list(set(links_out)),
            "tags": tags,
            "full_text": text,
        })
    return notes


def load_embeddings(notes: list[dict]) -> tuple[list[str], np.ndarray, dict[str, int]]:
    raw = json.loads(EMBEDDINGS_CACHE.read_text())
    id_to_emb = {nid: emb for nid, emb in zip(raw["ids"], raw["body"])}
    note_id_set = {n["id"] for n in notes}
    ids = [nid for nid in raw["ids"] if nid in note_id_set]
    vecs = [np.array(id_to_emb[nid], dtype=np.float32) for nid in ids]
    for v in vecs:
        v /= (np.linalg.norm(v) + 1e-9)
    body_mat = np.stack(vecs)
    id_to_pos = {nid: i for i, nid in enumerate(ids)}
    return ids, body_mat, id_to_pos


def load_events(ids: list[str]) -> list[dict]:
    id_set = set(ids)
    gt = json.loads(GROUND_TRUTH_CACHE.read_text())
    events = []
    for qid, interactions in gt.items():
        gold = [item["id"] for item in interactions
                if isinstance(item, dict) and item.get("id") in id_set]
        if gold and qid in id_set:
            events.append({"qid": qid, "gold_ids": gold})
    return events


# ---------------------------------------------------------------------------
# Signal scoring (inline — avoids re-running full setup)
# ---------------------------------------------------------------------------

def top_k(scores: np.ndarray, ids: list[str], exclude: str, k: int) -> list[str]:
    s = scores.copy()
    if exclude in ids:
        s[ids.index(exclude)] = -1.0
    return [ids[i] for i in np.argsort(-s)[:k]]


def bm25_scores(qid: str, id_to_body: dict, bm25) -> np.ndarray:
    from rank_bm25 import BM25Okapi
    tokens = re.findall(r"[a-z]+", id_to_body.get(qid, "").lower())
    return np.array(bm25.get_scores(tokens), dtype=np.float32)


def mugi_scores(qid: str, id_to_body: dict, cache: dict, bm25) -> np.ndarray:
    body = id_to_body.get(qid, "")
    pseudo = cache.get(qid, [])
    tokens = re.findall(r"[a-z]+", (body + " " + " ".join(pseudo)).lower())
    return np.array(bm25.get_scores(tokens), dtype=np.float32)


def hyde_scores(qid: str, ids: list, body_mat: np.ndarray, hyde_cache: dict) -> np.ndarray:
    if qid not in hyde_cache or "embedding" not in hyde_cache[qid]:
        return np.zeros(len(ids), dtype=np.float32)
    v = np.array(hyde_cache[qid]["embedding"], dtype=np.float32)
    v /= (np.linalg.norm(v) + 1e-9)
    return body_mat @ v


def step_back_scores(qid: str, ids: list, body_mat: np.ndarray, sb_cache: dict) -> np.ndarray:
    if qid not in sb_cache or "embedding" not in sb_cache[qid]:
        return np.zeros(len(ids), dtype=np.float32)
    v = np.array(sb_cache[qid]["embedding"], dtype=np.float32)
    v /= (np.linalg.norm(v) + 1e-9)
    return body_mat @ v


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    sys.path.insert(0, str(WORKBENCH_DIR))

    print("Loading data...")
    notes = load_corpus()
    ids, body_mat, id_to_pos = load_embeddings(notes)
    notes = [n for n in notes if n["id"] in id_to_pos]
    events = load_events(ids)

    id_to_note = {n["id"]: n for n in notes}

    # Build link index
    links_in: dict[str, list[str]] = defaultdict(list)
    for n in notes:
        for target in n["links_out"]:
            links_in[target].append(n["id"])

    # BM25 index
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        import subprocess
        subprocess.run(["pip", "install", "rank-bm25", "-q"], check=True)
        from rank_bm25 import BM25Okapi

    id_to_body = {n["id"]: n["body"] for n in notes}
    corpus_tokens = [re.findall(r"[a-z]+", id_to_body.get(nid, "").lower()) for nid in ids]
    bm25 = BM25Okapi(corpus_tokens)

    # Load LLM caches
    pseudo_cache: dict = {}
    if (CACHES_DIR / "pseudo_notes.json").exists():
        pseudo_cache = json.loads((CACHES_DIR / "pseudo_notes.json").read_text())

    hyde_cache: dict = {}
    if (CACHES_DIR / "hyde.json").exists():
        hyde_cache = json.loads((CACHES_DIR / "hyde.json").read_text())

    sb_cache: dict = {}
    if (CACHES_DIR / "step_back.json").exists():
        sb_cache = json.loads((CACHES_DIR / "step_back.json").read_text())

    print(f"Identifying unreachable notes across {len(events)} events at K={K_DIAG}...")

    # Track per (query, gold) pairs whether each signal reaches the gold note
    unreachable_pairs: list[tuple[str, str]] = []   # (qid, gold_id) never reached by any signal
    gold_reach: dict[str, dict[str, bool]] = {}     # gold_id -> {signal: reached_at_least_once}

    for i, event in enumerate(events):
        qid = event["qid"]
        gold_ids = [g for g in event["gold_ids"] if g in id_to_pos]
        if not gold_ids or qid not in id_to_pos:
            continue
        qidx = id_to_pos[qid]

        # Score vectors
        s_body  = body_mat @ body_mat[qidx]
        s_mugi  = mugi_scores(qid, id_to_body, pseudo_cache, bm25)
        s_bm25k = np.array(bm25.get_scores(re.findall(r"[a-z]+", id_to_body.get(qid,"").lower())), dtype=np.float32)
        s_hyde  = hyde_scores(qid, ids, body_mat, hyde_cache)
        s_sb    = step_back_scores(qid, ids, body_mat, sb_cache)

        # LOO activation
        import itertools
        act_w: dict[frozenset, float] = defaultdict(float)
        for j, ev in enumerate(events):
            if j == i:
                continue
            for gid in ev["gold_ids"]:
                act_w[frozenset([ev["qid"], gid])] += 1.0
            for a, b in itertools.combinations(ev["gold_ids"], 2):
                act_w[frozenset([a, b])] += 1.0
        s_act = np.array([act_w.get(frozenset([qid, nid]), 0.0) for nid in ids], dtype=np.float32)

        tops = {
            "body":       set(top_k(s_body,  ids, qid, K_DIAG)),
            "bm25_mugi":  set(top_k(s_mugi,  ids, qid, K_DIAG)),
            "bm25_kw":    set(top_k(s_bm25k, ids, qid, K_DIAG)),
            "activation": set(top_k(s_act,   ids, qid, K_DIAG)),
            "hyde":       set(top_k(s_hyde,   ids, qid, K_DIAG)),
            "step_back":  set(top_k(s_sb,     ids, qid, K_DIAG)),
        }
        union = set().union(*tops.values())

        for gid in gold_ids:
            if gid not in gold_reach:
                gold_reach[gid] = {s: False for s in tops}
            for sig, top_set in tops.items():
                if gid in top_set:
                    gold_reach[gid][sig] = True
            if gid not in union:
                unreachable_pairs.append((qid, gid))

    # Notes that were never reached by any signal in any query where they were gold
    always_unreachable: set[str] = set()
    for gid, reach in gold_reach.items():
        if not any(reach.values()):
            always_unreachable.add(gid)

    print(f"\n{'─'*70}")
    print(f"UNREACHABLE GOLD NOTES ANALYSIS")
    print(f"{'─'*70}")
    print(f"Total (query, gold) pairs evaluated: {sum(len(e['gold_ids']) for e in events)}")
    print(f"Unreachable pairs (missed by all signals at K={K_DIAG}): {len(unreachable_pairs)}")
    print(f"Unique gold notes never reached in any event: {len(always_unreachable)}")
    print(f"Gold notes reached by at least one signal in at least one event: "
          f"{len([g for g, r in gold_reach.items() if any(r.values())])}")

    # Profile unreachable notes
    unreachable_notes = [id_to_note[gid] for gid in always_unreachable if gid in id_to_note]
    all_notes = [id_to_note[gid] for gid in gold_reach if gid in id_to_note]

    def profile(notes_list):
        body_lens = [len(n["body"]) for n in notes_list]
        links_out_counts = [len(n["links_out"]) for n in notes_list]
        links_in_counts = [len(links_in.get(n["id"], [])) for n in notes_list]
        tagged = sum(1 for n in notes_list if n["tags"])
        return {
            "count": len(notes_list),
            "avg_body_len": int(np.mean(body_lens)) if body_lens else 0,
            "med_body_len": int(np.median(body_lens)) if body_lens else 0,
            "avg_links_out": round(np.mean(links_out_counts), 1) if links_out_counts else 0,
            "avg_links_in": round(np.mean(links_in_counts), 1) if links_in_counts else 0,
            "pct_tagged": round(100 * tagged / len(notes_list), 1) if notes_list else 0,
        }

    ur_prof = profile(unreachable_notes)
    all_prof = profile(all_notes)

    print(f"\n{'─'*70}")
    print(f"STRUCTURAL PROFILE COMPARISON")
    print(f"{'─'*70}")
    print(f"{'Metric':<30} {'Unreachable':>14} {'All gold':>14}")
    print(f"  {'─'*60}")
    metrics = [
        ("Count", "count", ""),
        ("Avg body length (chars)", "avg_body_len", ""),
        ("Median body length (chars)", "med_body_len", ""),
        ("Avg outgoing links", "avg_links_out", ""),
        ("Avg incoming links", "avg_links_in", ""),
        ("% with tags", "pct_tagged", "%"),
    ]
    for label, key, suffix in metrics:
        print(f"  {label:<28} {str(ur_prof[key])+suffix:>14} {str(all_prof[key])+suffix:>14}")

    # Signal breakdown for pairs that are reachable-by-some
    sometimes_unreachable = [(qid, gid) for qid, gid in unreachable_pairs
                             if gid not in always_unreachable]
    print(f"\n  Notes missed in some events but reached in others: "
          f"{len(set(gid for _, gid in sometimes_unreachable))}")

    # Sample unreachable pairs for qualitative inspection
    print(f"\n{'─'*70}")
    print(f"SAMPLE UNREACHABLE PAIRS (query → gold note never found)")
    print(f"{'─'*70}")

    sampled = unreachable_pairs[:TOP_EXAMPLES]
    for qid, gid in sampled:
        qnote = id_to_note.get(qid, {})
        gnote = id_to_note.get(gid, {})
        q_body = qnote.get("body", "")[:300].replace("\n", " ")
        g_body = gnote.get("body", "")[:300].replace("\n", " ")
        g_links_in = len(links_in.get(gid, []))
        g_links_out = len(gnote.get("links_out", []))

        # Body embedding similarity between query and gold
        if qid in id_to_pos and gid in id_to_pos:
            sim = float(body_mat[id_to_pos[qid]] @ body_mat[id_to_pos[gid]])
        else:
            sim = 0.0

        print(f"\n  QUERY: {qid}")
        print(f"    {q_body}...")
        print(f"  GOLD:  {gid}  (links_in={g_links_in}, links_out={g_links_out}, body_sim={sim:.3f})")
        print(f"    {g_body}...")

    # Word overlap analysis
    print(f"\n{'─'*70}")
    print(f"VOCABULARY OVERLAP (query vs unreachable gold)")
    print(f"{'─'*70}")
    overlaps = []
    for qid, gid in unreachable_pairs[:50]:
        q_words = set(re.findall(r"[a-z]{4,}", id_to_body.get(qid, "").lower()))
        g_words = set(re.findall(r"[a-z]{4,}", id_to_body.get(gid, "").lower()))
        if q_words and g_words:
            jaccard = len(q_words & g_words) / len(q_words | g_words)
            overlaps.append(jaccard)
    if overlaps:
        print(f"  Median Jaccard (4+ char words, first 50 pairs): {np.median(overlaps):.3f}")
        print(f"  Mean Jaccard: {np.mean(overlaps):.3f}")
        print(f"  Pairs with Jaccard=0 (zero shared vocabulary): "
              f"{sum(1 for j in overlaps if j == 0)} / {len(overlaps)}")


if __name__ == "__main__":
    main()
