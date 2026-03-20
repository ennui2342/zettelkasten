#!/usr/bin/env python3
"""Spike 4D: LLM-Derived Ground Truth for Retrieval Evaluation

The Wikipedia inter-article link ground truth used in Spike 4A measures
citation-style relatedness, not integration-action relatedness. This spike
generates a proper ground truth by asking the integration LLM directly:
"Given this incoming note, which existing notes would you take an action on?"

For each of 20 query notes, the LLM receives:
  - The full query note body
  - A condensed list of all other corpus notes (id + context sentence)
  - The instruction to identify notes triggering UPDATE/MERGE/SPLIT/SYNTHESISE

The gold set for each query = note IDs with a non-NOTHING decision.

Retrieval strategies then evaluated against this gold set:
  - body_sim: body embedding cosine similarity
  - ctx_sim: context field embedding cosine similarity
  - summary_sim: LLM summary embedding (if spike4a summaries cache exists)

If body_sim recall is high against LLM ground truth, link traversal and
tag-based expansion are confirmed as noise and can be dropped from the design.

Run:
  docker compose run --rm dev python spikes/spike4d-llm-ground-truth/spike.py
"""

from __future__ import annotations

import json
import os
import re
import random
import shutil
import sys
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
    print("Installing dependencies...")
    subprocess.run(["pip", "install", "anthropic", "voyageai", "numpy", "-q"], check=True)
    import anthropic
    import numpy as np
    import voyageai

SPIKE_DIR = Path(__file__).parent
SPIKE4A_DIR = SPIKE_DIR.parent / "spike4a-cluster"
CORPUS_DIR = SPIKE4A_DIR / "corpus"
EMBEDDINGS_CACHE = SPIKE4A_DIR / "embeddings_cache.json"
SUMMARIES_CACHE = SPIKE4A_DIR / "summaries_cache.json"
GROUND_TRUTH_CACHE = SPIKE_DIR / "ground_truth_cache.json"
RESULTS_PATH = SPIKE_DIR / "results.md"

CLAUDE_MODEL = "claude-sonnet-4-6"   # needs quality integration judgement
VOYAGE_MODEL = "voyage-3-lite"
N_QUERY_NOTES = 20
RANDOM_SEED = 42


# ---------------------------------------------------------------------------
# Corpus loading (duplicated from spike4a for self-containment)
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
            "path": str(path),
        })
    return notes


# ---------------------------------------------------------------------------
# Query note selection
# ---------------------------------------------------------------------------

def select_query_notes(notes: list[dict], id_set: set[str], n: int, all_notes: bool = False) -> list[dict]:
    """Pick query notes.

    all_notes=True: use all 300 corpus notes (for activation graph training).
    all_notes=False: pick N mid-connectivity notes (1-8 in-corpus links).
    """
    for note in notes:
        note["_in_corpus_links"] = [lid for lid in note["links"] if lid in id_set]

    if all_notes:
        return list(notes)

    candidates = [n for n in notes if 1 <= len(n["_in_corpus_links"]) <= 8]
    rng = random.Random(RANDOM_SEED)
    return rng.sample(candidates, min(n, len(candidates)))


# ---------------------------------------------------------------------------
# LLM ground truth generation
# ---------------------------------------------------------------------------

INTEGRATION_PROMPT = """\
You are maintaining a knowledge base of cognitive science notes. A new note has arrived.

Your task: identify which existing notes this new note would INTERACT with during integration.
An interaction means you would take one of these actions:
- UPDATE: the new note adds detail, evidence, or nuance to an existing note
- MERGE: the new note covers the same phenomenon from a different angle
- SPLIT: the new note reveals that an existing note conflates two distinct concepts
- SYNTHESISE: the new note bridges a gap between two existing notes

Ignore notes where no meaningful integration action would occur (NOTHING).

--- INCOMING NOTE ---
{query_body}
--- END NOTE ---

Existing knowledge base (ID and one-sentence summary):
{corpus_list}

Return JSON only. Aim for 2-6 interactions — be selective, not exhaustive.
Schema: {{"interactions": [{{"id": "wiki-xxx", "operation": "UPDATE|MERGE|SPLIT|SYNTHESISE", "reason": "one sentence"}}]}}"""


def build_corpus_list(notes: list[dict], exclude_id: str) -> str:
    lines = []
    for i, note in enumerate(notes, 1):
        if note["id"] == exclude_id:
            continue
        ctx = note["context"][:120].replace("\n", " ")
        lines.append(f"{i}. [{note['id']}] {ctx}")
    return "\n".join(lines)


def generate_ground_truth(notes: list[dict], query_notes: list[dict]) -> dict:
    """Run integration LLM for each query note against the full corpus.

    Cache is incremental — saved after each query note completes.
    Returns {query_id: [{"id": note_id, "operation": str, "reason": str}, ...]}.
    """
    cache: dict = {}
    if GROUND_TRUTH_CACHE.exists():
        cache = json.loads(GROUND_TRUTH_CACHE.read_text())

    needs_gt = [n for n in query_notes if n["id"] not in cache]
    if not needs_gt:
        print(f"Ground truth loaded from cache ({len(cache)} query notes).")
        return cache

    if cache:
        print(f"Resuming ground truth: {len(cache)} cached, {len(needs_gt)} remaining...")
    else:
        print(f"Generating LLM ground truth for {len(needs_gt)} query notes ({CLAUDE_MODEL})...")

    llm = anthropic.Anthropic()

    for i, query_note in enumerate(needs_gt):
        qid = query_note["id"]
        corpus_list = build_corpus_list(notes, exclude_id=qid)
        prompt = INTEGRATION_PROMPT.format(
            query_body=query_note["body"][:3000],
            corpus_list=corpus_list,
        )

        response = llm.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        # Extract first complete JSON object in case model appended extra text
        brace_start = raw.index("{")
        depth, end = 0, brace_start
        for i, ch in enumerate(raw[brace_start:], brace_start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        parsed = json.loads(raw[brace_start:end + 1])
        interactions = parsed.get("interactions", [])

        cache[qid] = interactions
        GROUND_TRUTH_CACHE.write_text(json.dumps(cache, indent=2))

        ops = [x["operation"] for x in interactions]
        print(f"  [{i+1}/{len(needs_gt)}] {qid}: {len(interactions)} interactions {ops}")

    return cache


# ---------------------------------------------------------------------------
# Retrieval evaluation
# ---------------------------------------------------------------------------

def cosine_similarity_retrieval(
    query_vec: np.ndarray,
    matrix: np.ndarray,
    ids: list[str],
    exclude_id: str,
    k: int,
) -> list[str]:
    scores = matrix @ query_vec
    if exclude_id in ids:
        scores[ids.index(exclude_id)] = -1.0
    top_k = np.argsort(-scores)[:k].tolist()
    return [ids[i] for i in top_k]


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(retrieved[:k]) & set(relevant)) / len(relevant)


def reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
    relevant_set = set(relevant)
    for rank, nid in enumerate(retrieved, start=1):
        if nid in relevant_set:
            return 1.0 / rank
    return 0.0


def evaluate(
    notes: list[dict],
    embeddings_cache: dict,
    ground_truth: dict,
    query_notes: list[dict],
    summaries: dict | None,
) -> dict:
    ids = embeddings_cache["ids"]
    id_to_pos = {nid: i for i, nid in enumerate(ids)}

    body_mat = np.array(embeddings_cache["body"], dtype=np.float32)
    ctx_mat = np.array(embeddings_cache["context"], dtype=np.float32)
    body_mat /= np.linalg.norm(body_mat, axis=1, keepdims=True) + 1e-9
    ctx_mat /= np.linalg.norm(ctx_mat, axis=1, keepdims=True) + 1e-9

    # Build summary matrix if available
    sum_mat: np.ndarray | None = None
    sum_id_to_pos: dict = {}
    if summaries:
        sum_ids = [n["id"] for n in query_notes if n["id"] in summaries]
        if sum_ids:
            sum_vecs = np.array([summaries[nid]["embedding"] for nid in sum_ids], dtype=np.float32)
            sum_vecs /= np.linalg.norm(sum_vecs, axis=1, keepdims=True) + 1e-9
            sum_mat = sum_vecs
            sum_id_to_pos = {nid: i for i, nid in enumerate(sum_ids)}

    ks = [3, 5, 10]
    strategies = ["body_sim", "ctx_sim"]
    if sum_mat is not None:
        strategies.append("summary_sim")

    recall: dict[str, dict[int, list[float]]] = {s: {k: [] for k in ks} for s in strategies}
    mrr: dict[str, list[float]] = {s: [] for s in strategies}
    gold_sizes: list[int] = []
    skipped = 0

    base_k = 30

    for query_note in query_notes:
        qid = query_note["id"]
        interactions = ground_truth.get(qid, [])
        gold = [x["id"] for x in interactions if x["id"] in id_to_pos]

        if not gold:
            # STUB: LLM found no interactions — exclude from retrieval eval
            skipped += 1
            continue

        gold_sizes.append(len(gold))
        idx = id_to_pos.get(qid)
        if idx is None:
            continue

        body_top = cosine_similarity_retrieval(body_mat[idx], body_mat, ids, qid, base_k)
        ctx_top = cosine_similarity_retrieval(ctx_mat[idx], ctx_mat, ids, qid, base_k)

        retrieved = {"body_sim": body_top, "ctx_sim": ctx_top}

        if sum_mat is not None and qid in sum_id_to_pos:
            si = sum_id_to_pos[qid]
            sum_top = cosine_similarity_retrieval(sum_mat[si], body_mat, ids, qid, base_k)
            retrieved["summary_sim"] = sum_top

        for s in strategies:
            if s not in retrieved:
                continue
            r = retrieved[s]
            for k in ks:
                recall[s][k].append(recall_at_k(r, gold, k))
            mrr[s].append(reciprocal_rank(r, gold))

    n_eval = len(query_notes) - skipped
    results: dict = {}
    for s in strategies:
        n = len(mrr[s])
        results[s] = {
            "recall": {k: float(np.mean(recall[s][k])) if recall[s][k] else 0.0 for k in ks},
            "mrr": float(np.mean(mrr[s])) if mrr[s] else 0.0,
        }
    results["_meta"] = {
        "n_query_notes": len(query_notes),
        "n_eval_notes": n_eval,
        "n_stub_notes": skipped,
        "mean_gold_set_size": float(np.mean(gold_sizes)) if gold_sizes else 0.0,
        "model_gt": CLAUDE_MODEL,
        "model_embed": VOYAGE_MODEL,
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
    strategies = [s for s in ["body_sim", "ctx_sim", "summary_sim"] if s in results]
    labels = {
        "body_sim":    "Body embedding, similarity only",
        "ctx_sim":     "Context field (first sentence) embedding",
        "summary_sim": "LLM summary embedding",
    }

    lines = [
        "# Spike 4D Results — LLM Ground Truth Retrieval Evaluation",
        "",
        f"*Run: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        f"*Ground truth model: {meta['model_gt']}*",
        f"*Embedding model: {meta['model_embed']}*",
        f"*Query notes: {meta['n_query_notes']} total, "
        f"{meta['n_eval_notes']} with interactions, "
        f"{meta['n_stub_notes']} STUB (no interactions — excluded)*",
        f"*Mean gold set size: {meta['mean_gold_set_size']:.1f} notes per query*",
        "",
        "Ground truth: for each query note, the integration LLM identified which existing",
        "notes would trigger UPDATE, MERGE, SPLIT, or SYNTHESISE. Retrieval strategies are",
        "evaluated on whether they surface those notes in the top-k cluster.",
        "",
        "---",
        "",
        "## Retrieval strategy comparison",
        "",
        "| Strategy | R@3 | R@5 | R@10 | MRR |",
        "|----------|-----|-----|------|-----|",
    ]
    for s in strategies:
        r = results[s]["recall"]
        lines.append(
            f"| {labels[s]} | {r[3]:.3f} | {r[5]:.3f} | {r[10]:.3f} | {results[s]['mrr']:.3f} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Interpretation",
        "",
        "If body_sim R@5 ≥ 0.60 against this ground truth:",
        "  → Body embedding alone reliably surfaces the notes worth integrating.",
        "  → Link traversal and tag-based expansion are confirmed noise — drop them.",
        "  → Context field vs body question answered by comparing rows 1 and 2.",
        "",
        "If body_sim R@5 < 0.40:",
        "  → Pure similarity is insufficient; cluster identification needs rethinking.",
        "",
        "---",
        "",
        "## Evaluation notes",
        "",
        "*(Fill in after reviewing output)*",
        "",
        "### Body embedding verdict",
        "- R@5 against LLM ground truth: [fill in]",
        "- Verdict — sufficient for production cluster? [fill in]",
        "",
        "### Link traversal and tags (H3)",
        "- If body_sim sufficient: confirmed noise, eliminate from design [fill in]",
        "",
        "### Embedding target",
        "- Body vs context field vs LLM summary: [fill in]",
        "",
        "## Go / No-go",
        "",
        "[ ] Go — body_sim R@5 ≥ 0.60 against LLM ground truth",
        "[ ] Marginal — R@5 0.40–0.60, may need hybrid approach",
        "[ ] No-go — R@5 < 0.40, rethink cluster strategy",
        "",
        "**Recommendation:** [fill in]",
    ]

    RESULTS_PATH.write_text("\n".join(lines))
    print(f"Results written to {RESULTS_PATH}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not CORPUS_DIR.exists():
        print(f"Corpus not found at {CORPUS_DIR}. Run spike4a build_corpus.py first.")
        return
    if not EMBEDDINGS_CACHE.exists():
        print(f"Embeddings cache not found at {EMBEDDINGS_CACHE}. Run spike4a spike.py first.")
        return

    notes = load_corpus()
    print(f"Loaded {len(notes)} notes from corpus")

    embeddings_cache = json.loads(EMBEDDINGS_CACHE.read_text())
    print("Loaded embeddings from spike4a cache")

    summaries: dict | None = None
    if SUMMARIES_CACHE.exists():
        summaries = json.loads(SUMMARIES_CACHE.read_text())
        n_with_emb = sum(1 for v in summaries.values() if "embedding" in v)
        print(f"Loaded spike4a summaries ({n_with_emb} with embeddings)")

    full_sweep = "--all" in sys.argv
    id_set = {n["id"] for n in notes}
    query_notes = select_query_notes(notes, id_set, N_QUERY_NOTES, all_notes=full_sweep)
    mode = "all notes (full sweep)" if full_sweep else f"mid-connectivity sample (seed={RANDOM_SEED})"
    print(f"Selected {len(query_notes)} query notes — {mode}")
    for qn in query_notes:
        print(f"  {qn['id']}: {len(qn['_in_corpus_links'])} in-corpus links")

    ground_truth = generate_ground_truth(notes, query_notes)

    # Summary of what LLM found
    total_interactions = sum(len(v) for v in ground_truth.values())
    stub_count = sum(1 for v in ground_truth.values() if not v)
    print(f"\nGround truth summary: {total_interactions} total interactions across "
          f"{len(ground_truth) - stub_count} notes ({stub_count} STUB — no interactions)")

    print("\nRunning retrieval evaluation...")
    results = evaluate(notes, embeddings_cache, ground_truth, query_notes, summaries)

    meta = results["_meta"]
    print(f"\n{'Strategy':<45} {'R@3':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
    print("-" * 70)
    labels = {
        "body_sim":    "Body sim only",
        "ctx_sim":     "Context field sim only",
        "summary_sim": "LLM summary sim",
    }
    for s in ["body_sim", "ctx_sim", "summary_sim"]:
        if s not in results:
            continue
        r = results[s]
        print(f"{labels[s]:<45} {r['recall'][3]:>6.3f} {r['recall'][5]:>6.3f} "
              f"{r['recall'][10]:>6.3f} {r['mrr']:>6.3f}")
    print(f"\n(N={meta['n_eval_notes']} query notes with interactions, "
          f"mean gold set size={meta['mean_gold_set_size']:.1f})")

    write_results(results)
    print("\nDone. Review results.md and fill in evaluation notes.")


if __name__ == "__main__":
    main()
