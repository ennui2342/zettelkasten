#!/usr/bin/env python3
"""Spike 5 — Activation-Weighted Cluster Identification (Extended)

Tests H-new-A: does blending body embedding similarity with a co-activation
link signal improve cluster recall beyond body embedding alone?

Also tests:
  - Summary embeddings (Haiku-generated, Voyage-embedded) vs body embeddings
  - Alpha sweep [0.1 .. 0.8]: optimal blend weight
  - Top-k activation: sparse activation signal (only strongest k edges)
  - Summary + activation blend

Mechanism
---------
Each Spike 4D integration event (query Q acted on gold notes G1..Gn) is
treated as a past co-activation event. Activation links are recorded between:
  - Q ↔ Gi  (weight=1.0, confirmed interaction)
  - Gi ↔ Gj (weight=1.0, co-appeared in same integration window)

W_null=0.3 (including co-retrieved-but-NOTHING) was eliminated by prior run.

Scoring:
  score(query, candidate) = (1-α)·embed_sim + α·activation_strength

Run:
  docker compose run --rm dev python spikes/spike5-activation-links/spike.py
  docker compose run --rm dev python spikes/spike5-activation-links/spike.py --no-summaries
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
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

try:
    import numpy as np
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "numpy", "-q"], check=True)
    import numpy as np

SPIKE4A_DIR = Path(__file__).parent.parent / "spike4a-cluster"
SPIKE4D_DIR = Path(__file__).parent.parent / "spike4d-llm-ground-truth"
SPIKE5_DIR = Path(__file__).parent
EMBEDDINGS_CACHE = SPIKE4A_DIR / "embeddings_cache.json"
SUMMARIES_CACHE = SPIKE4A_DIR / "summaries_cache.json"
CORPUS_DIR = SPIKE4A_DIR / "corpus"
GROUND_TRUTH_CACHE = SPIKE4D_DIR / "ground_truth_cache.json"
RESULTS_PATH = SPIKE5_DIR / "results.md"

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
VOYAGE_MODEL = "voyage-3-lite"
LAMBDA = 0.05   # decay rate; all events at age=0 → decay=1.0
CLUSTER_K = 20  # retrieval window

ALPHA_VALUES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
TOPK_VALUES = [5, 10, 20, 50]   # top-k neighbours in activation graph; None=all

SKIP_SUMMARIES = "--no-summaries" in sys.argv


# ---------------------------------------------------------------------------
# Corpus loading
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
    return meta, body


def load_corpus() -> list[dict]:
    notes = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        text = path.read_text()
        meta, body = parse_frontmatter(text)
        if not meta.get("id"):
            continue
        notes.append({"id": meta["id"], "body": body, "links": meta["_links"]})
    return notes


# ---------------------------------------------------------------------------
# Summary generation (all 300 notes, incremental)
# ---------------------------------------------------------------------------

def generate_all_summaries(notes: list[dict]) -> dict:
    """Generate Haiku summaries + Voyage embeddings for all corpus notes.

    Incremental: skips notes already in SUMMARIES_CACHE.
    Returns {note_id: {"summary": str, "tags": list, "embedding": list[float]}}.
    """
    try:
        import anthropic
        import voyageai
    except ImportError:
        import subprocess
        subprocess.run(["pip", "install", "anthropic", "voyageai", "-q"], check=True)
        import anthropic
        import voyageai

    cache: dict = {}
    if SUMMARIES_CACHE.exists():
        cache = json.loads(SUMMARIES_CACHE.read_text())

    # Phase 1: LLM summaries for notes not yet cached
    needs_summary = [n for n in notes if n["id"] not in cache]
    if needs_summary:
        llm = anthropic.Anthropic()
        print(f"Generating summaries for {len(needs_summary)} notes (Haiku)...")
        for i, note in enumerate(needs_summary):
            prompt = (
                "Analyse this cognitive science note. Return JSON only, no prose.\n\n"
                f"Note body:\n{note['body'][:3000]}\n\n"
                'Return: {"summary": "<2-3 sentences capturing key concepts, mechanisms, '
                'and relationships to other memory/learning phenomena>", '
                '"tags": ["<5-8 specific semantic tags>"]}'
            )
            response = llm.messages.create(
                model=CLAUDE_MODEL, max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            parsed = json.loads(raw)
            cache[note["id"]] = {"summary": parsed["summary"], "tags": parsed["tags"]}
            SUMMARIES_CACHE.write_text(json.dumps(cache, indent=2))
            if (i + 1) % 10 == 0 or i == len(needs_summary) - 1:
                print(f"  [{i+1}/{len(needs_summary)}] done")
    else:
        print(f"  All {len(cache)} summaries already cached.")

    # Phase 2: Voyage embeddings for notes without embeddings
    needs_embed = [n for n in notes if n["id"] in cache and "embedding" not in cache[n["id"]]]
    if needs_embed:
        voyage = voyageai.Client()
        batch_size = 128
        print(f"Embedding {len(needs_embed)} summaries with Voyage...")
        for start in range(0, len(needs_embed), batch_size):
            batch = needs_embed[start:start + batch_size]
            texts = [cache[n["id"]]["summary"] for n in batch]
            result = voyage.embed(texts, model=VOYAGE_MODEL, input_type="document")
            for note, emb in zip(batch, result.embeddings):
                cache[note["id"]]["embedding"] = emb
            SUMMARIES_CACHE.write_text(json.dumps(cache, indent=2))
            print(f"  [{min(start+batch_size, len(needs_embed))}/{len(needs_embed)}] embedded")
    else:
        print(f"  All embeddings already cached.")

    return {nid: v for nid, v in cache.items() if "embedding" in v}


# ---------------------------------------------------------------------------
# Activation graph
# ---------------------------------------------------------------------------

class ActivationGraph:
    def __init__(self):
        self._weights: dict[frozenset, float] = defaultdict(float)

    def add_event(self, query_id: str, gold_ids: list[str], age_days: float = 0.0) -> None:
        decay = math.exp(-LAMBDA * age_days)
        for gid in gold_ids:
            self._weights[frozenset([query_id, gid])] += 1.0 * decay
        for a, b in combinations(gold_ids, 2):
            self._weights[frozenset([a, b])] += 1.0 * decay

    def strength(self, a: str, b: str) -> float:
        return self._weights.get(frozenset([a, b]), 0.0)

    def activation_vector(self, query_id: str, all_ids: list[str], topk: int | None = None) -> np.ndarray:
        vec = np.array([self.strength(query_id, nid) for nid in all_ids], dtype=np.float32)
        if topk is not None and topk < len(vec):
            threshold = np.sort(vec)[-topk]
            vec[vec < threshold] = 0.0
        return vec

    def network_stats(self, all_ids: list[str]) -> dict:
        id_set = set(all_ids)
        degrees: dict[str, int] = defaultdict(int)
        adj: dict[str, set[str]] = defaultdict(set)
        for pair, w in self._weights.items():
            if w > 0:
                a, b = list(pair)
                if a in id_set and b in id_set:
                    degrees[a] += 1
                    degrees[b] += 1
                    adj[a].add(b)
                    adj[b].add(a)
        connected = [nid for nid in all_ids if degrees[nid] > 0]
        deg_vals = [degrees[nid] for nid in connected]
        cc_vals = []
        for nid in connected:
            neighbours = list(adj[nid])
            k = len(neighbours)
            if k < 2:
                continue
            links_between = sum(
                1 for i in range(k) for j in range(i+1, k)
                if neighbours[j] in adj[neighbours[i]]
            )
            cc_vals.append(2 * links_between / (k * (k - 1)))
        n_edges = len([w for w in self._weights.values() if w > 0])
        return {
            "n_nodes": len(connected),
            "n_edges": n_edges,
            "mean_degree": float(np.mean(deg_vals)) if deg_vals else 0.0,
            "mean_cc": float(np.mean(cc_vals)) if cc_vals else 0.0,
        }


# ---------------------------------------------------------------------------
# Retrieval helpers
# ---------------------------------------------------------------------------

def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(retrieved[:k]) & set(relevant)) / len(relevant)


def reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
    rs = set(relevant)
    for rank, nid in enumerate(retrieved, 1):
        if nid in rs:
            return 1.0 / rank
    return 0.0


def top_k_ids(scores: np.ndarray, ids: list[str], exclude: str, k: int) -> list[str]:
    if exclude in ids:
        scores = scores.copy()
        scores[ids.index(exclude)] = -1.0
    return [ids[i] for i in np.argsort(-scores)[:k]]


def blend_scores(
    embed_scores: np.ndarray,
    act_scores: np.ndarray,
    alpha: float,
) -> np.ndarray:
    max_act = act_scores.max()
    if max_act > 0:
        act_scores = act_scores / max_act
    return (1 - alpha) * embed_scores + alpha * act_scores


# ---------------------------------------------------------------------------
# Leave-one-out evaluation
# ---------------------------------------------------------------------------

def loo_evaluate(
    events: list[dict],
    ids: list[str],
    body_mat: np.ndarray,
    id_to_pos: dict[str, int],
    sum_mat: np.ndarray | None,       # normalised summary matrix (same id order as ids)
    sum_id_to_pos: dict[str, int] | None,
) -> dict:
    """Run LOO evaluation for all strategy variants.

    Returns nested dict:
      results[strategy_key] = {"recall": {3: float, 5: float, 10: float}, "mrr": float}
    """
    ks = [3, 5, 10]
    have_summaries = sum_mat is not None and sum_id_to_pos is not None

    # Build strategy keys
    body_alpha_keys = [f"body_act_a{int(a*10):02d}" for a in ALPHA_VALUES]
    body_topk_keys = [f"body_act_topk{k}" for k in TOPK_VALUES]
    sum_alpha_keys = [f"sum_act_a{int(a*10):02d}" for a in ALPHA_VALUES] if have_summaries else []
    all_keys = (
        ["body_sim"]
        + (["sum_sim"] if have_summaries else [])
        + body_alpha_keys
        + body_topk_keys
        + sum_alpha_keys
    )

    recall: dict[str, dict[int, list[float]]] = {s: {k: [] for k in ks} for s in all_keys}
    mrr: dict[str, list[float]] = {s: [] for s in all_keys}

    for i, test_event in enumerate(events):
        qid = test_event["qid"]
        gold = [g for g in test_event["gold_ids"] if g in id_to_pos]
        if not gold:
            continue

        # Build activation graph from all other events
        graph = ActivationGraph()
        for j, ev in enumerate(events):
            if j != i:
                graph.add_event(ev["qid"], ev["gold_ids"])

        qidx = id_to_pos[qid]
        body_vec = body_mat[qidx]
        body_scores = body_mat @ body_vec

        act_vec_full = graph.activation_vector(qid, ids)

        retrieved: dict[str, list[str]] = {}

        # body_sim baseline
        retrieved["body_sim"] = top_k_ids(body_scores, ids, qid, CLUSTER_K)

        # summary_sim baseline
        if have_summaries and qid in sum_id_to_pos:
            si = sum_id_to_pos[qid]
            sum_vec = sum_mat[si]
            sum_scores = sum_mat @ sum_vec
            retrieved["sum_sim"] = top_k_ids(sum_scores, ids, qid, CLUSTER_K)

        # body + activation alpha sweep
        for alpha, key in zip(ALPHA_VALUES, body_alpha_keys):
            combined = blend_scores(body_scores.copy(), act_vec_full.copy(), alpha)
            retrieved[key] = top_k_ids(combined, ids, qid, CLUSTER_K)

        # body + activation top-k sweep (at alpha=0.3 — best from prior run)
        for topk, key in zip(TOPK_VALUES, body_topk_keys):
            act_sparse = graph.activation_vector(qid, ids, topk=topk)
            combined = blend_scores(body_scores.copy(), act_sparse.copy(), 0.3)
            retrieved[key] = top_k_ids(combined, ids, qid, CLUSTER_K)

        # summary + activation alpha sweep
        if have_summaries and qid in sum_id_to_pos:
            si = sum_id_to_pos[qid]
            sum_vec = sum_mat[si]
            sum_scores_norm = sum_mat @ sum_vec  # already normalised
            for alpha, key in zip(ALPHA_VALUES, sum_alpha_keys):
                combined = blend_scores(sum_scores_norm.copy(), act_vec_full.copy(), alpha)
                retrieved[key] = top_k_ids(combined, ids, qid, CLUSTER_K)

        for s in all_keys:
            if s not in retrieved:
                continue
            r = retrieved[s]
            for k in ks:
                recall[s][k].append(recall_at_k(r, gold, k))
            mrr[s].append(reciprocal_rank(r, gold))

    results: dict = {}
    for s in all_keys:
        if not recall[s][10]:
            continue
        results[s] = {
            "recall": {k: float(np.mean(recall[s][k])) for k in ks},
            "mrr": float(np.mean(mrr[s])),
            "n": len(recall[s][10]),
        }
    return results


# ---------------------------------------------------------------------------
# Results writer
# ---------------------------------------------------------------------------

def write_results(results: dict, net_stats: dict, n_events: int) -> None:
    if RESULTS_PATH.exists():
        runs = sorted(SPIKE5_DIR.glob("results-run*.md"))
        shutil.copy(RESULTS_PATH, SPIKE5_DIR / f"results-run{len(runs)+1}.md")

    have_summaries = any(k.startswith("sum_") for k in results)

    def row(key: str, label: str) -> str:
        if key not in results:
            return ""
        r = results[key]
        return f"| {label} | {r['recall'][3]:.3f} | {r['recall'][5]:.3f} | {r['recall'][10]:.3f} | {r['mrr']:.3f} |"

    # Find best alpha for body+act and sum+act
    best_body_alpha = max(ALPHA_VALUES, key=lambda a: results.get(f"body_act_a{int(a*10):02d}", {}).get("recall", {}).get(10, 0))
    best_sum_alpha = max(ALPHA_VALUES, key=lambda a: results.get(f"sum_act_a{int(a*10):02d}", {}).get("recall", {}).get(10, 0)) if have_summaries else None

    lines = [
        "# Spike 5 Results — Extended Sweep",
        "",
        f"*Run: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        f"*Leave-one-out over {n_events} events, cluster window top-{CLUSTER_K}*",
        "",
        "---",
        "",
        "## Baselines",
        "",
        "| Strategy | R@3 | R@5 | R@10 | MRR |",
        "|----------|-----|-----|------|-----|",
        row("body_sim", "Body embedding"),
    ]
    if have_summaries:
        lines.append(row("sum_sim", "Summary embedding"))
    lines += ["", "---", "", "## Alpha sweep — Body + Activation", ""]
    lines += [
        "| Alpha | R@3 | R@5 | R@10 | MRR |",
        "|-------|-----|-----|------|-----|",
    ]
    for a in ALPHA_VALUES:
        key = f"body_act_a{int(a*10):02d}"
        marker = " ★" if a == best_body_alpha else ""
        lines.append(row(key, f"α={a}{marker}"))
    lines = [l for l in lines if l]  # remove empty rows from missing keys

    lines += ["", "---", "", "## Top-k activation (body embedding, α=0.3)", ""]
    lines += [
        "| Top-k | R@3 | R@5 | R@10 | MRR |",
        "|-------|-----|-----|------|-----|",
        row("body_act_a03", "All edges (baseline α=0.3)"),
    ]
    for k in TOPK_VALUES:
        lines.append(row(f"body_act_topk{k}", f"Top-{k} neighbours"))

    if have_summaries:
        lines += ["", "---", "", "## Alpha sweep — Summary + Activation", ""]
        lines += [
            "| Alpha | R@3 | R@5 | R@10 | MRR |",
            "|-------|-----|-----|------|-----|",
        ]
        for a in ALPHA_VALUES:
            key = f"sum_act_a{int(a*10):02d}"
            marker = " ★" if a == best_sum_alpha else ""
            lines.append(row(key, f"α={a}{marker}"))

    lines += [
        "", "---", "",
        "## Network diagnostics (full activation graph, W_null=0.0)",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Nodes with activation links | {net_stats['n_nodes']} |",
        f"| Edges | {net_stats['n_edges']} |",
        f"| Mean degree | {net_stats['mean_degree']:.1f} |",
        f"| Mean clustering coefficient | {net_stats['mean_cc']:.3f} |",
    ]

    RESULTS_PATH.write_text("\n".join(lines))
    print(f"Results written to {RESULTS_PATH}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    for p, name in [
        (EMBEDDINGS_CACHE, "Embeddings cache (run spike4a first)"),
        (GROUND_TRUTH_CACHE, "Ground truth cache (run spike4d first)"),
        (CORPUS_DIR, "Corpus directory"),
    ]:
        if not p.exists():
            print(f"Missing: {name}\n  Expected at: {p}")
            return

    print("Loading embeddings...")
    ec = json.loads(EMBEDDINGS_CACHE.read_text())
    ids: list[str] = ec["ids"]
    id_to_pos = {nid: i for i, nid in enumerate(ids)}
    body_mat = np.array(ec["body"], dtype=np.float32)
    body_mat /= np.linalg.norm(body_mat, axis=1, keepdims=True) + 1e-9
    print(f"  {len(ids)} notes, dim={body_mat.shape[1]}")

    # Summary embeddings
    sum_mat: np.ndarray | None = None
    sum_id_to_pos: dict[str, int] | None = None
    if not SKIP_SUMMARIES:
        notes = load_corpus()
        print(f"\nLoaded {len(notes)} corpus notes for summary generation")
        print("Generating/loading summaries for all notes...")
        summaries = generate_all_summaries(notes)
        print(f"  {len(summaries)} notes with summary embeddings")

        # Build full summary matrix aligned with ids list
        sum_vecs = []
        sum_ids = []
        for nid in ids:
            if nid in summaries:
                sum_vecs.append(summaries[nid]["embedding"])
                sum_ids.append(nid)
        if sum_ids:
            sum_arr = np.array(sum_vecs, dtype=np.float32)
            sum_arr /= np.linalg.norm(sum_arr, axis=1, keepdims=True) + 1e-9
            sum_mat = sum_arr
            sum_id_to_pos = {nid: i for i, nid in enumerate(sum_ids)}
            print(f"  Summary matrix: {sum_mat.shape}")
    else:
        print("\nSkipping summary generation (--no-summaries)")

    print("\nLoading Spike 4D ground truth...")
    ground_truth = json.loads(GROUND_TRUTH_CACHE.read_text())
    print(f"  {len(ground_truth)} query notes")

    events: list[dict] = []
    for qid, interactions in ground_truth.items():
        gold_ids = [
            x["id"] for x in interactions
            if x["id"] in id_to_pos and x.get("operation", "NOTHING") != "NOTHING"
        ]
        if not gold_ids or qid not in id_to_pos:
            continue
        events.append({"qid": qid, "gold_ids": gold_ids})

    print(f"  {len(events)} events with ≥1 confirmed interaction")
    mean_gold = np.mean([len(e["gold_ids"]) for e in events])
    print(f"  Mean gold per event: {mean_gold:.1f}")

    # Network diagnostics on full graph
    print("\nBuilding full activation graph...")
    full_graph = ActivationGraph()
    for ev in events:
        full_graph.add_event(ev["qid"], ev["gold_ids"])
    net_stats = full_graph.network_stats(ids)
    print(f"  {net_stats['n_nodes']} nodes, {net_stats['n_edges']} edges, "
          f"mean degree={net_stats['mean_degree']:.1f}, CC={net_stats['mean_cc']:.3f}")

    print("\nRunning leave-one-out evaluation...")
    results = loo_evaluate(events, ids, body_mat, id_to_pos, sum_mat, sum_id_to_pos)

    # Print results
    have_summaries = any(k.startswith("sum_") for k in results)
    n_sum = results.get("sum_sim", {}).get("n", 0)

    print(f"\n{'─'*68}")
    print(f"BASELINES  (N={results['body_sim']['n']} events)")
    print(f"{'Strategy':<35} {'R@3':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
    print("─" * 68)
    for key, label in [("body_sim", "Body embedding"), ("sum_sim", f"Summary embedding (N={n_sum})")]:
        if key in results:
            r = results[key]
            print(f"  {label:<33} {r['recall'][3]:>6.3f} {r['recall'][5]:>6.3f} {r['recall'][10]:>6.3f} {r['mrr']:>6.3f}")

    print(f"\n{'─'*68}")
    print("ALPHA SWEEP — Body + Activation")
    print(f"{'Alpha':<35} {'R@3':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
    print("─" * 68)
    best_body_r10 = 0.0
    best_body_alpha = 0.3
    for a in ALPHA_VALUES:
        key = f"body_act_a{int(a*10):02d}"
        if key not in results:
            continue
        r = results[key]
        marker = " ★" if r["recall"][10] > best_body_r10 else ""
        if r["recall"][10] > best_body_r10:
            best_body_r10 = r["recall"][10]
            best_body_alpha = a
        print(f"  α={a:<32} {r['recall'][3]:>6.3f} {r['recall'][5]:>6.3f} {r['recall'][10]:>6.3f} {r['mrr']:>6.3f}{marker}")

    print(f"\n{'─'*68}")
    print(f"TOP-K ACTIVATION (body embedding, α=0.3)")
    print(f"{'Config':<35} {'R@3':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
    print("─" * 68)
    base_key = "body_act_a03"
    if base_key in results:
        r = results[base_key]
        print(f"  {'All edges':<33} {r['recall'][3]:>6.3f} {r['recall'][5]:>6.3f} {r['recall'][10]:>6.3f} {r['mrr']:>6.3f}")
    for topk in TOPK_VALUES:
        key = f"body_act_topk{topk}"
        if key not in results:
            continue
        r = results[key]
        print(f"  {'Top-'+str(topk)+' neighbours':<33} {r['recall'][3]:>6.3f} {r['recall'][5]:>6.3f} {r['recall'][10]:>6.3f} {r['mrr']:>6.3f}")

    if have_summaries:
        print(f"\n{'─'*68}")
        print(f"ALPHA SWEEP — Summary + Activation  (N={n_sum} events with summaries)")
        print(f"{'Alpha':<35} {'R@3':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
        print("─" * 68)
        best_sum_r10 = 0.0
        for a in ALPHA_VALUES:
            key = f"sum_act_a{int(a*10):02d}"
            if key not in results:
                continue
            r = results[key]
            marker = " ★" if r["recall"][10] > best_sum_r10 else ""
            if r["recall"][10] > best_sum_r10:
                best_sum_r10 = r["recall"][10]
            print(f"  α={a:<32} {r['recall'][3]:>6.3f} {r['recall'][5]:>6.3f} {r['recall'][10]:>6.3f} {r['mrr']:>6.3f}{marker}")

    write_results(results, net_stats, len(events))
    print("\nDone.")


if __name__ == "__main__":
    main()
