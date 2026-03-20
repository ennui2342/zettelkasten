#!/usr/bin/env python3
"""Spike 4A: Cluster Identification — Retrieval Strategy Comparison

Validates H3 (link traversal augments similarity), H9 (optimal traversal depth),
and the embedding target question (body vs context field).

Given a corpus of Wikipedia cognitive science articles converted to zettelkasten
notes, evaluates four retrieval strategies against a ground truth derived from
Wikipedia's own inter-article link structure: if article A links to article B,
a query built from A's content should retrieve B in the top-k cluster.

Strategies compared:
  1. Body embedding, similarity only
  2. Context-field embedding, similarity only
  3. Body embedding + link traversal depth=1
  4. Body embedding + link traversal depth=2

Metrics: Recall@k (k=3,5,10) and MRR across all notes with ≥1 in-corpus link.

Prerequisites:
  pip install voyageai numpy
  VOYAGE_API_KEY in environment or .env

Run:
  docker compose run --rm dev python spikes/spike4a-cluster/spike.py
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if "SSL_CERT_FILE" in os.environ and not os.path.exists(os.environ["SSL_CERT_FILE"]):
    del os.environ["SSL_CERT_FILE"]

try:
    import anthropic
    import numpy as np
    import voyageai
except ImportError:
    import subprocess
    print("Installing voyageai, numpy, anthropic...")
    subprocess.run(["pip", "install", "voyageai", "numpy", "anthropic", "-q"], check=True)
    import anthropic
    import numpy as np
    import voyageai

SPIKE_DIR = Path(__file__).parent
CORPUS_DIR = SPIKE_DIR / "corpus"
EMBEDDINGS_CACHE = SPIKE_DIR / "embeddings_cache.json"
RESULTS_PATH = SPIKE_DIR / "results.md"

VOYAGE_MODEL = "voyage-3-lite"  # cheapest; upgrade to voyage-3 for higher quality
EMBED_BATCH_SIZE = 50  # well under the 128 limit; reduces token-per-request load
EMBED_BATCH_DELAY = 0.3  # seconds between batches (increase if rate-limited)

SUMMARIES_CACHE = SPIKE_DIR / "summaries_cache.json"
SUMMARY_SAMPLE_SIZE = 30
CLAUDE_MODEL = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Note loading
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body. Returns (meta dict, body str)."""
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

    # Parse links block — extract `id:` values
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

    # Parse context field (may span multiple lines with ">")
    context_match = re.search(r"context:\s*>\s*\n((?:[ \t]+[^\n]*\n?)+)", fm_text)
    if context_match:
        meta["context"] = context_match.group(1).strip()

    return meta, body


def load_corpus() -> list[dict]:
    """Load all notes from corpus directory. Returns list of note dicts."""
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
            "salience": float(meta.get("salience", 0.5)),
            "links": meta["_links"],
            "path": str(path),
        })
    return notes


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def load_or_build_embeddings(notes: list[dict]) -> dict:
    """Load embeddings from cache, or build incrementally and cache them.

    The cache stores partial results keyed by note ID so a failed run resumes
    from the last completed batch rather than restarting from scratch.
    """
    ids = [n["id"] for n in notes]
    id_to_note = {n["id"]: n for n in notes}

    # Load existing partial or complete cache
    cache: dict = {"model": VOYAGE_MODEL, "ids": [], "body": [], "context": []}
    if EMBEDDINGS_CACHE.exists():
        loaded = json.loads(EMBEDDINGS_CACHE.read_text())
        if loaded.get("model") == VOYAGE_MODEL:
            cache = loaded

    already_done = set(cache["ids"])
    remaining = [nid for nid in ids if nid not in already_done]

    if not remaining:
        print("Loading embeddings from cache (complete)...")
        return cache

    if already_done:
        print(f"Resuming embeddings: {len(already_done)} cached, "
              f"{len(remaining)} remaining...")
    else:
        print(f"Building embeddings with Voyage AI ({len(remaining)} notes)...")

    client = voyageai.Client()

    for i in range(0, len(remaining), EMBED_BATCH_SIZE):
        batch_ids = remaining[i : i + EMBED_BATCH_SIZE]
        batch_bodies = [id_to_note[nid]["body"] for nid in batch_ids]
        batch_contexts = [id_to_note[nid]["context"] for nid in batch_ids]

        print(f"  Batch {i // EMBED_BATCH_SIZE + 1}: embedding {len(batch_ids)} notes "
              f"(body)...", end=" ", flush=True)
        body_result = client.embed(batch_bodies, model=VOYAGE_MODEL, input_type="document")
        time.sleep(EMBED_BATCH_DELAY)

        print("(context)...", end=" ", flush=True)
        ctx_result = client.embed(batch_contexts, model=VOYAGE_MODEL, input_type="document")

        # Append to cache and save incrementally
        cache["ids"].extend(batch_ids)
        cache["body"].extend(body_result.embeddings)
        cache["context"].extend(ctx_result.embeddings)
        EMBEDDINGS_CACHE.write_text(json.dumps(cache))
        print(f"saved ({len(cache['ids'])}/{len(notes)} total)")

        if i + EMBED_BATCH_SIZE < len(remaining):
            time.sleep(EMBED_BATCH_DELAY)

    print(f"  All embeddings cached to {EMBEDDINGS_CACHE}")

    # Return in corpus order (cache may have different order if resuming)
    id_to_pos = {nid: i for i, nid in enumerate(cache["ids"])}
    ordered_body = [cache["body"][id_to_pos[nid]] for nid in ids]
    ordered_ctx = [cache["context"][id_to_pos[nid]] for nid in ids]
    return {
        "model": cache["model"],
        "ids": ids,
        "body": ordered_body,
        "context": ordered_ctx,
    }


# ---------------------------------------------------------------------------
# Summary + tag generation
# ---------------------------------------------------------------------------

def generate_summaries_and_tags(notes: list[dict], eval_notes: list[dict]) -> dict:
    """Generate LLM summaries and semantic tags for the 30 most-connected eval notes.

    Single Haiku call per note yields both. Cache is incremental.
    Then embeds summaries with Voyage (also cached inline).

    Returns {note_id: {"summary": str, "tags": list[str], "embedding": list[float]}}.
    Only returns notes that have all three fields.
    """
    # Pick the most-connected eval notes — highest link density gives best eval signal
    sample = sorted(eval_notes, key=lambda n: -len(n["links"]))[:SUMMARY_SAMPLE_SIZE]
    sample_ids = {n["id"] for n in sample}
    id_to_note = {n["id"]: n for n in notes}

    # Load partial cache
    cache: dict = {}
    if SUMMARIES_CACHE.exists():
        cache = json.loads(SUMMARIES_CACHE.read_text())

    # Phase 1: generate summaries + tags for notes not yet in cache
    needs_summary = [n for n in sample if n["id"] not in cache]
    if needs_summary:
        llm = anthropic.Anthropic()
        print(f"Generating summaries+tags for {len(needs_summary)} notes (Haiku)...")
        for i, note in enumerate(needs_summary):
            prompt = (
                "Analyse this cognitive science note. Return JSON only, no prose.\n\n"
                f"Note body:\n{note['body'][:3000]}\n\n"
                'Return: {"summary": "<2-3 sentences capturing key concepts, mechanisms, '
                'and relationships to other memory/learning phenomena>", '
                '"tags": ["<5-8 specific semantic tags, e.g. spaced-repetition, working-memory, '
                'retrieval-practice — lowercase hyphenated phrases, no generic words>"]}'
            )
            response = llm.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            parsed = json.loads(raw)
            cache[note["id"]] = {"summary": parsed["summary"], "tags": parsed["tags"]}
            SUMMARIES_CACHE.write_text(json.dumps(cache, indent=2))
            print(f"  [{i+1}/{len(needs_summary)}] {note['id']}: {parsed['tags'][:3]}")
    else:
        in_sample = sum(1 for k in cache if k in sample_ids)
        print(f"Loaded {in_sample} summaries+tags from cache.")

    # Phase 2: generate Voyage embeddings for summaries not yet embedded
    needs_embed = [n for n in sample if n["id"] in cache and "embedding" not in cache[n["id"]]]
    if needs_embed:
        voyage = voyageai.Client()
        texts = [cache[n["id"]]["summary"] for n in needs_embed]
        print(f"Embedding {len(needs_embed)} summaries with Voyage...")
        result = voyage.embed(texts, model=VOYAGE_MODEL, input_type="document")
        for note, emb in zip(needs_embed, result.embeddings):
            cache[note["id"]]["embedding"] = emb
        SUMMARIES_CACHE.write_text(json.dumps(cache, indent=2))
        print("  Summary embeddings cached.")

    return {nid: v for nid, v in cache.items() if nid in sample_ids and "embedding" in v}


# ---------------------------------------------------------------------------
# Retrieval strategies
# ---------------------------------------------------------------------------

def build_matrices(embeddings_cache: dict) -> tuple[np.ndarray, np.ndarray, list[str]]:
    ids = embeddings_cache["ids"]
    body_mat = np.array(embeddings_cache["body"], dtype=np.float32)
    ctx_mat = np.array(embeddings_cache["context"], dtype=np.float32)
    # L2-normalise for dot-product cosine similarity
    body_mat /= np.linalg.norm(body_mat, axis=1, keepdims=True) + 1e-9
    ctx_mat /= np.linalg.norm(ctx_mat, axis=1, keepdims=True) + 1e-9
    return body_mat, ctx_mat, ids


def similarity_retrieval(
    query_vec: np.ndarray,
    matrix: np.ndarray,
    ids: list[str],
    exclude_id: str,
    k: int,
) -> list[str]:
    """Return top-k note IDs by cosine similarity, excluding query note itself."""
    scores = matrix @ query_vec
    # Zero out self-match
    if exclude_id in ids:
        idx = ids.index(exclude_id)
        scores[idx] = -1.0
    top_k = np.argsort(-scores)[:k].tolist()
    return [ids[i] for i in top_k]


def link_expand(
    retrieved: list[str],
    adj: dict[str, list[str]],
    depth: int,
) -> list[str]:
    """Expand a retrieved set by following links to given depth.
    Preserves original order; appended neighbours are unordered."""
    seen = set(retrieved)
    frontier = list(retrieved)
    for _ in range(depth):
        next_frontier = []
        for nid in frontier:
            for neighbour in adj.get(nid, []):
                if neighbour not in seen:
                    seen.add(neighbour)
                    next_frontier.append(neighbour)
        frontier = next_frontier
    return list(seen)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    retrieved_k = set(retrieved[:k])
    return len(retrieved_k & set(relevant)) / len(relevant)


def reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
    relevant_set = set(relevant)
    for rank, nid in enumerate(retrieved, start=1):
        if nid in relevant_set:
            return 1.0 / rank
    return 0.0


def evaluate(notes: list[dict], embeddings_cache: dict, summaries: dict | None = None) -> dict:
    body_mat, ctx_mat, ids = build_matrices(embeddings_cache)
    id_to_idx = {nid: i for i, nid in enumerate(ids)}

    # Build adjacency list from note links
    adj: dict[str, list[str]] = defaultdict(list)
    for note in notes:
        for linked_id in note["links"]:
            if linked_id in id_to_idx:  # in-corpus only
                adj[note["id"]].append(linked_id)

    # Only evaluate notes that have ≥1 in-corpus link (our ground truth)
    eval_notes = [n for n in notes if adj[n["id"]]]
    print(f"\nEvaluating {len(eval_notes)} notes with in-corpus links "
          f"(out of {len(notes)} total)")

    ks = [3, 5, 10]
    base_strategies = ["body_sim", "ctx_sim", "body_link1", "body_link2"]
    recall: dict[str, dict[int, list[float]]] = {s: {k: [] for k in ks} for s in base_strategies}
    mrr: dict[str, list[float]] = {s: [] for s in base_strategies}

    # Fan-out diagnostic: how many nodes link expansion draws in and how precise
    fanout_d1_sizes: list[int] = []
    fanout_d2_sizes: list[int] = []
    fanout_d1_new_precision: list[float] = []

    base_k = 30

    for note in eval_notes:
        nid = note["id"]
        relevant = adj[nid]
        relevant_set = set(relevant)
        idx = id_to_idx[nid]

        query_body = body_mat[idx]
        query_ctx = ctx_mat[idx]

        body_top = similarity_retrieval(query_body, body_mat, ids, nid, base_k)
        ctx_top = similarity_retrieval(query_ctx, ctx_mat, ids, nid, base_k)

        body_link1_raw = link_expand(body_top[:10], adj, depth=1)
        body_link2_raw = link_expand(body_top[:10], adj, depth=2)
        body_link1 = [x for x in body_link1_raw if x != nid]
        body_link2 = [x for x in body_link2_raw if x != nid]

        # Fan-out: new nodes added beyond the initial top-10
        new_at_d1 = set(body_link1) - set(body_top[:10])
        fanout_d1_sizes.append(len(body_link1))
        fanout_d2_sizes.append(len(body_link2))
        if new_at_d1:
            fanout_d1_new_precision.append(len(new_at_d1 & relevant_set) / len(new_at_d1))

        retrieved = {
            "body_sim": body_top,
            "ctx_sim": ctx_top,
            "body_link1": body_link1,
            "body_link2": body_link2,
        }

        for s in base_strategies:
            r = retrieved[s]
            for k in ks:
                recall[s][k].append(recall_at_k(r, relevant, k))
            mrr[s].append(reciprocal_rank(r, relevant))

    # Aggregate base strategies
    results: dict = {}
    for s in base_strategies:
        results[s] = {
            "recall": {k: float(np.mean(recall[s][k])) for k in ks},
            "mrr": float(np.mean(mrr[s])),
        }

    # Fan-out summary
    fanout = {
        "mean_depth1_cluster_size": float(np.mean(fanout_d1_sizes)),
        "max_depth1_cluster_size": int(np.max(fanout_d1_sizes)),
        "mean_depth2_cluster_size": float(np.mean(fanout_d2_sizes)),
        "max_depth2_cluster_size": int(np.max(fanout_d2_sizes)),
        # Precision of the *new* nodes added by expansion (not the top-10 anchor)
        "mean_d1_new_node_precision": float(np.mean(fanout_d1_new_precision)) if fanout_d1_new_precision else 0.0,
    }

    # Summary + tag strategies — evaluated on the 30-note subset only
    if summaries:
        summary_notes = [n for n in eval_notes if n["id"] in summaries]
        print(f"Evaluating summary/tag strategies on {len(summary_notes)}-note subset...")

        # Build normalised summary embedding matrix (for use as query vectors)
        sum_ids = [n["id"] for n in summary_notes]
        sum_mat = np.array([summaries[nid]["embedding"] for nid in sum_ids], dtype=np.float32)
        sum_mat /= np.linalg.norm(sum_mat, axis=1, keepdims=True) + 1e-9

        # Pre-build lowercase bodies for tag keyword search
        note_bodies_lower = [n["body"].lower() for n in notes]

        sub_strategies = ["body_sim_sub", "summary_sim", "tag_keyword", "tag_body_combined"]
        sub_recall: dict[str, dict[int, list[float]]] = {s: {k: [] for k in ks} for s in sub_strategies}
        sub_mrr: dict[str, list[float]] = {s: [] for s in sub_strategies}

        for si, note in enumerate(summary_notes):
            nid = note["id"]
            relevant = adj[nid]
            if not relevant:
                continue
            idx = id_to_idx[nid]

            # body_sim_sub: body embedding on this subset (baseline for fair comparison)
            body_top_sub = similarity_retrieval(body_mat[idx], body_mat, ids, nid, base_k)

            # summary_sim: query with summary embedding, search body_mat
            summary_top = similarity_retrieval(sum_mat[si], body_mat, ids, nid, base_k)

            # tag_keyword: count how many of query's semantic tags appear in each target body
            tags = summaries[nid]["tags"]
            tag_scores = np.array([
                sum(
                    tag.replace("-", " ") in body or tag in body
                    for tag in tags
                )
                for body in note_bodies_lower
            ], dtype=float)
            tag_scores[idx] = -1.0  # exclude self
            tag_top = [ids[i] for i in np.argsort(-tag_scores)[:base_k]]

            # tag_body_combined: 50/50 blend of normalised tag score and body cosine sim
            body_scores = body_mat @ body_mat[idx]
            body_scores[idx] = -1.0
            max_tag = tag_scores.max()
            norm_tag = tag_scores / max_tag if max_tag > 0 else tag_scores
            combined = 0.5 * body_scores + 0.5 * norm_tag
            combined[idx] = -1.0
            combined_top = [ids[i] for i in np.argsort(-combined)[:base_k]]

            retrieved_sub = {
                "body_sim_sub": body_top_sub,
                "summary_sim": summary_top,
                "tag_keyword": tag_top,
                "tag_body_combined": combined_top,
            }
            for s in sub_strategies:
                r = retrieved_sub[s]
                for k in ks:
                    sub_recall[s][k].append(recall_at_k(r, relevant, k))
                sub_mrr[s].append(reciprocal_rank(r, relevant))

        n_sub = len(summary_notes)
        for s in sub_strategies:
            n = len(sub_mrr[s])
            results[s] = {
                "recall": {k: float(np.mean(sub_recall[s][k])) if sub_recall[s][k] else 0.0 for k in ks},
                "mrr": float(np.mean(sub_mrr[s])) if sub_mrr[s] else 0.0,
                "n": n,
            }
        results["_meta_sub"] = {"n_summary_notes": n_sub}

    results["_meta"] = {
        "n_eval_notes": len(eval_notes),
        "n_total_notes": len(notes),
        "model": VOYAGE_MODEL,
        "fanout": fanout,
    }
    return results


# ---------------------------------------------------------------------------
# Results writer
# ---------------------------------------------------------------------------

def write_results(results: dict) -> None:
    if RESULTS_PATH.exists():
        runs = sorted(SPIKE_DIR.glob("results-run*.md"))
        next_run = len(runs) + 1
        shutil.copy(RESULTS_PATH, SPIKE_DIR / f"results-run{next_run}.md")

    meta = results["_meta"]
    fanout = meta.get("fanout", {})
    base_strategies = ["body_sim", "ctx_sim", "body_link1", "body_link2"]
    base_labels = {
        "body_sim":   "Body embedding, similarity only",
        "ctx_sim":    "Context field (first sentence) embedding",
        "body_link1": "Body embedding + link traversal depth=1",
        "body_link2": "Body embedding + link traversal depth=2",
    }
    sub_strategies = ["body_sim_sub", "summary_sim", "tag_keyword", "tag_body_combined"]
    sub_labels = {
        "body_sim_sub":      "Body embedding (subset baseline)",
        "summary_sim":       "LLM summary embedding",
        "tag_keyword":       "Tag keyword count",
        "tag_body_combined": "Tag keyword + body embedding (50/50)",
    }
    has_sub = "summary_sim" in results

    lines = [
        "# Spike 4A Results — Cluster Identification",
        "",
        f"*Run: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        f"*Model: {meta['model']}*",
        f"*Eval notes (with in-corpus links): {meta['n_eval_notes']} / {meta['n_total_notes']}*",
        "",
        "Ground truth: Wikipedia inter-article links. If note A links to note B, a query "
        "built from A's content should retrieve B in the top-k cluster.",
        "",
        "---",
        "",
        "## Base retrieval strategies (N=226)",
        "",
        "| Strategy | R@3 | R@5 | R@10 | MRR |",
        "|----------|-----|-----|------|-----|",
    ]
    for s in base_strategies:
        r = results[s]["recall"]
        lines.append(
            f"| {base_labels[s]} | {r[3]:.3f} | {r[5]:.3f} | {r[10]:.3f} | {results[s]['mrr']:.3f} |"
        )

    if has_sub:
        n_sub = results.get("_meta_sub", {}).get("n_summary_notes", "?")
        lines += [
            "",
            f"## Summary and tag strategies (N={n_sub})",
            "",
            "Evaluated on the 30 most-connected notes only (those with LLM-generated summaries/tags).",
            "Query: LLM summary embedding or extracted tags. Retrieval pool: all 300 note bodies.",
            "",
            "| Strategy | R@3 | R@5 | R@10 | MRR |",
            "|----------|-----|-----|------|-----|",
        ]
        for s in sub_strategies:
            r = results[s]["recall"]
            lines.append(
                f"| {sub_labels[s]} | {r[3]:.3f} | {r[5]:.3f} | {r[10]:.3f} | {results[s]['mrr']:.3f} |"
            )

    if fanout:
        lines += [
            "",
            "## Link expansion fan-out diagnostic",
            "",
            "How many notes does depth-1 link expansion draw into the cluster, and what "
            "fraction of the *newly added* nodes (beyond the top-10 similarity anchor) are "
            "actually in the ground truth?",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Mean cluster size — top-10 only | 10 |",
            f"| Mean cluster size — depth=1 expanded | {fanout['mean_depth1_cluster_size']:.1f} |",
            f"| Max cluster size — depth=1 expanded | {fanout['max_depth1_cluster_size']} |",
            f"| Mean cluster size — depth=2 expanded | {fanout['mean_depth2_cluster_size']:.1f} |",
            f"| Max cluster size — depth=2 expanded | {fanout['max_depth2_cluster_size']} |",
            f"| Precision of new nodes added at depth=1 | {fanout['mean_d1_new_node_precision']:.3f} |",
            "",
            "Precision of new nodes: what fraction of the nodes *added* by link expansion "
            "(not already in the top-10) are ground-truth targets. Low precision means "
            "expansion is drawing in noise.",
        ]

    lines += [
        "",
        "---",
        "",
        "## Evaluation notes",
        "",
        "*(Fill in after reviewing output)*",
        "",
        "### Embedding target (body vs context field vs LLM summary)",
        "- Body vs context field: [fill in]",
        "- Body vs LLM summary: [fill in]",
        "- Does context field evolution pass matter for retrieval? [fill in]",
        "",
        "### Tag-based retrieval",
        "- Tag keyword vs body embedding: [fill in]",
        "- Does tag+body blend beat either alone? [fill in]",
        "",
        "### Link traversal (H3)",
        "- Fan-out diagnostic: does expansion pull in mostly noise? [fill in]",
        "- Should link traversal be used in production? [fill in]",
        "",
        "### Ground truth quality",
        "- Wikipedia links as proxy for 'notes worth integrating': [fill in]",
        "- What a better ground truth would look like: [fill in]",
        "",
        "## Go / No-go",
        "",
        "[ ] Go — best strategy R@5 ≥ 0.40; embedding target question answered",
        "[ ] Conditional — similarity workable but tag/summary improvement worth pursuing",
        "[ ] No-go — similarity too weak; rethink embedding strategy",
        "",
        "**Recommendation:** [fill in]",
    ]

    RESULTS_PATH.write_text("\n".join(lines))
    print(f"Results written to {RESULTS_PATH}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    notes = load_corpus()
    if not notes:
        print(f"No notes found in {CORPUS_DIR}. Run build_corpus.py first.")
        return
    print(f"Loaded {len(notes)} notes from corpus")

    embeddings_cache = load_or_build_embeddings(notes)

    # Identify eval notes (≥1 in-corpus link) for summary sampling
    from collections import defaultdict as _dd
    _adj: dict[str, list[str]] = _dd(list)
    id_set = {n["id"] for n in notes}
    for n in notes:
        for lid in n["links"]:
            if lid in id_set:
                _adj[n["id"]].append(lid)
    eval_notes = [n for n in notes if _adj[n["id"]]]

    summaries = generate_summaries_and_tags(notes, eval_notes)

    print("\nRunning retrieval evaluation...")
    results = evaluate(notes, embeddings_cache, summaries=summaries)

    meta = results["_meta"]
    fanout = meta.get("fanout", {})

    print(f"\n{'Strategy':<45} {'R@3':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
    print("-" * 70)
    base_labels = {
        "body_sim":   "Body sim only",
        "ctx_sim":    "Context field sim only",
        "body_link1": "Body sim + links depth=1",
        "body_link2": "Body sim + links depth=2",
    }
    for s in ["body_sim", "ctx_sim", "body_link1", "body_link2"]:
        r = results[s]
        print(f"{base_labels[s]:<45} {r['recall'][3]:>6.3f} {r['recall'][5]:>6.3f} "
              f"{r['recall'][10]:>6.3f} {r['mrr']:>6.3f}")

    if "summary_sim" in results:
        n_sub = results.get("_meta_sub", {}).get("n_summary_notes", "?")
        print(f"\n{'  [30-note subset]':<45} {'R@3':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
        print("  " + "-" * 68)
        sub_labels = {
            "body_sim_sub":      "  Body sim (subset baseline)",
            "summary_sim":       "  LLM summary embedding",
            "tag_keyword":       "  Tag keyword count",
            "tag_body_combined": "  Tag keyword + body (50/50)",
        }
        for s in ["body_sim_sub", "summary_sim", "tag_keyword", "tag_body_combined"]:
            r = results[s]
            print(f"{sub_labels[s]:<45} {r['recall'][3]:>6.3f} {r['recall'][5]:>6.3f} "
                  f"{r['recall'][10]:>6.3f} {r['mrr']:>6.3f}")

    if fanout:
        print(f"\nFan-out diagnostic (depth=1 expansion):")
        print(f"  Mean cluster size: top-10 → {fanout['mean_depth1_cluster_size']:.1f} (max {fanout['max_depth1_cluster_size']})")
        print(f"  Mean cluster size depth=2: {fanout['mean_depth2_cluster_size']:.1f} (max {fanout['max_depth2_cluster_size']})")
        print(f"  Precision of new nodes added at depth=1: {fanout['mean_d1_new_node_precision']:.3f}")

    write_results(results)
    print("\nDone. Review results.md and fill in evaluation notes.")


if __name__ == "__main__":
    main()
