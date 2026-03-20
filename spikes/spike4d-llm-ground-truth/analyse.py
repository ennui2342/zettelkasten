#!/usr/bin/env python3
"""Spike 4D: Gold Set Diagnostic Analysis

For each query note, the integration LLM identified a gold set of ~4.7 notes
that would be acted on. Body embedding finds ~50% of them (R@10=0.512).

This script asks: what do the *missed* gold notes have in common with the query
that embedding missed? Specifically:

  1. Link signal — does a missed gold note link to the query, or vice versa?
     (bidirectional link presence)
  2. Tag signal — do they share extracted semantic tags?
     (from spike4a summaries_cache, available for 30 notes)
  3. Internal cohesion — do the gold notes link to *each other*?
     (tests whether the gold set forms a cluster in link space)

If links or tags recover a meaningful fraction of the missed gold notes,
they're worth incorporating. If not, body embedding is essentially the ceiling
and we should focus on improving the embedding model or prompt.

Run:
  docker compose run --rm dev python spikes/spike4d-llm-ground-truth/analyse.py
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if "SSL_CERT_FILE" in os.environ and not os.path.exists(os.environ["SSL_CERT_FILE"]):
    del os.environ["SSL_CERT_FILE"]

try:
    import numpy as np
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "numpy", "-q"], check=True)
    import numpy as np

SPIKE4A_DIR = Path(__file__).parent.parent / "spike4a-cluster"
SPIKE4D_DIR = Path(__file__).parent
CORPUS_DIR = SPIKE4A_DIR / "corpus"
EMBEDDINGS_CACHE = SPIKE4A_DIR / "embeddings_cache.json"
SUMMARIES_CACHE = SPIKE4A_DIR / "summaries_cache.json"
GROUND_TRUTH_CACHE = SPIKE4D_DIR / "ground_truth_cache.json"


# ---------------------------------------------------------------------------
# Corpus loading (minimal)
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
    links: list[str] = []
    in_links = False
    for line in fm_text.splitlines():
        if line.strip() == "links:":
            in_links = True
            continue
        if in_links:
            if line.startswith(" ") or line.startswith("\t"):
                m = re.search(r"id:\s*(\S+)", line)
                if m:
                    links.append(m.group(1))
            else:
                in_links = False
    meta["_links"] = links
    context_match = re.search(r"context:\s*>\s*\n((?:[ \t]+[^\n]*\n?)+)", fm_text)
    if context_match:
        meta["context"] = context_match.group(1).strip()
    return meta, body


def load_corpus() -> list[dict]:
    notes = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        text = path.read_text()
        meta, body = parse_frontmatter(text)
        if not meta.get("id"):
            continue
        notes.append({
            "id": meta["id"],
            "body": body,
            "context": meta.get("context", body[:200]),
            "links": meta["_links"],
        })
    return notes


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def main() -> None:
    for p, name in [
        (CORPUS_DIR, "Corpus"),
        (EMBEDDINGS_CACHE, "Embeddings cache"),
        (GROUND_TRUTH_CACHE, "Ground truth cache"),
    ]:
        if not p.exists():
            print(f"{name} not found at {p}. Run spike4a and spike4d first.")
            return

    notes = load_corpus()
    id_to_note = {n["id"]: n for n in notes}
    id_set = set(id_to_note.keys())
    print(f"Loaded {len(notes)} notes")

    embeddings_cache = json.loads(EMBEDDINGS_CACHE.read_text())
    ids = embeddings_cache["ids"]
    id_to_pos = {nid: i for i, nid in enumerate(ids)}
    body_mat = np.array(embeddings_cache["body"], dtype=np.float32)
    body_mat /= np.linalg.norm(body_mat, axis=1, keepdims=True) + 1e-9

    ground_truth = json.loads(GROUND_TRUTH_CACHE.read_text())

    summaries: dict = {}
    if SUMMARIES_CACHE.exists():
        summaries = json.loads(SUMMARIES_CACHE.read_text())
        print(f"Loaded summaries/tags for {len(summaries)} notes")

    # Build adjacency (forward and backward)
    forward: dict[str, set[str]] = defaultdict(set)   # note → notes it links to
    backward: dict[str, set[str]] = defaultdict(set)  # note → notes that link to it
    for note in notes:
        for lid in note["links"]:
            if lid in id_set:
                forward[note["id"]].add(lid)
                backward[lid].add(note["id"])

    # Build tag index
    tags_for: dict[str, set[str]] = {}
    for nid, v in summaries.items():
        if "tags" in v:
            tags_for[nid] = set(v["tags"])

    print("\n" + "=" * 70)
    print("GOLD SET DIAGNOSTIC")
    print("=" * 70)

    # Per-query analysis
    # For each query note, find where each gold note ranks in body embedding,
    # and for missed gold notes (rank > 10), check link and tag signals.

    rank_buckets = {3: 0, 5: 0, 10: 0, 20: 0, 30: 0, 999: 0}
    total_gold = 0

    missed_with_forward_link = 0   # Q → G_i exists
    missed_with_backward_link = 0  # G_i → Q exists
    missed_with_any_link = 0
    missed_with_shared_tag = 0
    missed_with_link_or_tag = 0
    missed_total = 0
    missed_with_nothing = 0

    # Gold-set internal cohesion
    gold_pair_count = 0
    gold_pairs_linked = 0

    query_rows: list[dict] = []

    for qid, interactions in ground_truth.items():
        gold_ids = [x["id"] for x in interactions if x["id"] in id_to_pos]
        if not gold_ids:
            continue

        total_gold += len(gold_ids)
        qidx = id_to_pos.get(qid)
        if qidx is None:
            continue

        # Rank all notes by body embedding for this query
        scores = body_mat @ body_mat[qidx]
        scores[qidx] = -1.0
        ranked = [ids[i] for i in np.argsort(-scores)]
        rank_of = {nid: rank + 1 for rank, nid in enumerate(ranked)}

        in_top = {k: 0 for k in rank_buckets}
        missed = []
        for gid in gold_ids:
            rank = rank_of.get(gid, 9999)
            for k in sorted(rank_buckets.keys()):
                if rank <= k:
                    in_top[k] += 1
            if rank > 10:
                missed.append((gid, rank))

        for k in rank_buckets:
            rank_buckets[k] += in_top[k]

        # Analyse missed gold notes
        query_tags = tags_for.get(qid, set())
        for gid, rank in missed:
            missed_total += 1
            has_fwd = gid in forward.get(qid, set())
            has_bwd = gid in backward.get(qid, set())  # gid links to qid
            gold_tags = tags_for.get(gid, set())
            shared_tags = query_tags & gold_tags

            if has_fwd:
                missed_with_forward_link += 1
            if has_bwd:
                missed_with_backward_link += 1
            if has_fwd or has_bwd:
                missed_with_any_link += 1
            if shared_tags:
                missed_with_shared_tag += 1
            if (has_fwd or has_bwd) or shared_tags:
                missed_with_link_or_tag += 1
            if not (has_fwd or has_bwd) and not shared_tags:
                missed_with_nothing += 1

        # Internal cohesion: how many gold-gold pairs share a link?
        for i, a in enumerate(gold_ids):
            for b in gold_ids[i+1:]:
                gold_pair_count += 1
                if b in forward.get(a, set()) or a in forward.get(b, set()):
                    gold_pairs_linked += 1

        query_rows.append({
            "qid": qid,
            "gold_n": len(gold_ids),
            "missed_n": len(missed),
            "top3": in_top[3],
            "top5": in_top[5],
            "top10": in_top[10],
        })

    n_queries = len(query_rows)
    print(f"\n{n_queries} query notes, {total_gold} total gold notes, "
          f"{missed_total} missed by body top-10\n")

    # Recall@k breakdown across gold notes
    print("─── Gold note rank distribution ───────────────────────────────────")
    for k in sorted(rank_buckets.keys()):
        label = f"top-{k}" if k < 999 else "rank > 30"
        pct = rank_buckets[k] / total_gold * 100
        bar = "█" * int(pct / 2)
        print(f"  Found in {label:<8}: {rank_buckets[k]:>3}/{total_gold}  ({pct:5.1f}%)  {bar}")

    # Link and tag signal on missed notes
    print(f"\n─── Signal on missed gold notes (rank > 10) ────────────────────────")
    print(f"  Missed total: {missed_total}")
    if missed_total > 0:
        def pct(n: int) -> str:
            return f"{n}/{missed_total} ({n/missed_total*100:.0f}%)"
        print(f"  Q → G (forward link exists):  {pct(missed_with_forward_link)}")
        print(f"  G → Q (backward link exists): {pct(missed_with_backward_link)}")
        print(f"  Either link direction:         {pct(missed_with_any_link)}")
        if tags_for:
            print(f"  Shared semantic tag:           {pct(missed_with_shared_tag)}")
            print(f"  Link OR shared tag:            {pct(missed_with_link_or_tag)}")
        print(f"  No signal (embedding is only hope): {pct(missed_with_nothing)}")

    # Gold set internal cohesion
    print(f"\n─── Gold set internal cohesion ─────────────────────────────────────")
    if gold_pair_count > 0:
        cohesion_pct = gold_pairs_linked / gold_pair_count * 100
        print(f"  Gold-gold pairs: {gold_pair_count}")
        print(f"  Pairs sharing a link: {gold_pairs_linked} ({cohesion_pct:.1f}%)")
        print(f"  → {'Gold notes form a linked cluster' if cohesion_pct > 30 else 'Gold notes are mostly disconnected in link space'}")
    else:
        print("  No gold pairs to analyse.")

    # Per-query summary table
    print(f"\n─── Per-query breakdown ────────────────────────────────────────────")
    print(f"  {'Query ID':<16} {'Gold':>4} {'Miss':>4} {'@3':>4} {'@5':>4} {'@10':>4}")
    print(f"  {'─'*16} {'─'*4} {'─'*4} {'─'*4} {'─'*4} {'─'*4}")
    for row in sorted(query_rows, key=lambda r: -r["missed_n"]):
        print(f"  {row['qid']:<16} {row['gold_n']:>4} {row['missed_n']:>4} "
              f"{row['top3']:>4} {row['top5']:>4} {row['top10']:>4}")

    # Headline conclusion
    print(f"\n{'=' * 70}")
    print("CONCLUSION")
    print("=" * 70)
    if missed_total > 0:
        link_pct = missed_with_any_link / missed_total * 100
        nothing_pct = missed_with_nothing / missed_total * 100
        print(f"\n  Body embedding finds {rank_buckets[10]/total_gold*100:.0f}% of gold notes in top-10.")
        print(f"  Of the {missed_total} missed: {link_pct:.0f}% have a link signal, "
              f"{nothing_pct:.0f}% have no link or tag signal.")
        if link_pct > 30:
            print(f"  → Links recover a meaningful fraction — worth adding as a secondary signal.")
        else:
            print(f"  → Links recover few missed notes — not worth the added complexity.")
        if tags_for:
            lt_pct = missed_with_link_or_tag / missed_total * 100
            print(f"  → Link OR tag covers {lt_pct:.0f}% of missed notes.")


if __name__ == "__main__":
    main()
