#!/usr/bin/env python3
"""Spike 6A — BM25 + MuGI: Extended (RRF, Three-Way Blend, Coverage Diagnostic)

Extends the initial run with:
  - Coverage diagnostic: how many gold notes are reachable by each method?
    (oracle analysis — answers whether fusion can help before tuning ranking)
  - RRF fusion (Reciprocal Rank Fusion) as alternative to weighted sum
  - Three-way blend: body + activation + BM25_MuGI
  - Keyword BM25: TF-IDF top-K terms as query instead of full body
    (contextual BM25 — reduces query noise, increases lexical discrimination)

Fusion methods compared
-----------------------
  Weighted sum: (1-β)·body_sim + β·normalise(bm25_score)
    - Sensitive to score distribution mismatch across retrieval methods
    - Simple; one tunable parameter β

  RRF: Σ 1/(k + rank_i) across retrieval lanes
    - Rank-based; immune to score scale mismatch
    - Standard choice for heterogeneous retrieval fusion
    - k=60 is the standard default (Cormack et al. 2009)

Coverage diagnostic
-------------------
For each event, checks how many gold notes appear in body top-K and
BM25+MuGI top-K at K=20, 50, 100, 200. Categorises each missed gold note
as: body-only, bm25-only, both, neither (unreachable by either).
"Neither" notes cannot be recovered by any ranking/fusion — they require
a fundamentally different retrieval mechanism. This bounds the ceiling
before any fusion tuning.

Run:
  docker compose run --rm dev python spikes/spike6a-bm25-mugi/spike.py
  docker compose run --rm dev python spikes/spike6a-bm25-mugi/spike.py --no-api
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

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "rank-bm25", "-q"], check=True)
    from rank_bm25 import BM25Okapi

SPIKE4A_DIR = Path(__file__).parent.parent / "spike4a-cluster"
SPIKE4D_DIR = Path(__file__).parent.parent / "spike4d-llm-ground-truth"
SPIKE6A_DIR = Path(__file__).parent
EMBEDDINGS_CACHE = SPIKE4A_DIR / "embeddings_cache.json"
GROUND_TRUTH_CACHE = SPIKE4D_DIR / "ground_truth_cache.json"
CORPUS_DIR = SPIKE4A_DIR / "corpus"
PSEUDO_CACHE = SPIKE6A_DIR / "pseudo_notes_cache.json"
RESULTS_PATH = SPIKE6A_DIR / "results.md"

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
N_PSEUDO = 3
BETA_VALUES = [0.1, 0.2, 0.3, 0.4, 0.5]
RRF_K = 60          # standard Cormack et al. 2009 default
CLUSTER_K = 20
KW_TOP_K = 25       # top-K TF-IDF keywords to use as BM25 query
LAMBDA = 0.05       # activation decay (all events at age=0 → decay=1.0)
SKIP_API = "--no-api" in sys.argv
DIAG_K_VALUES = [20, 50, 100, 200]


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
    return meta, body


def load_corpus() -> list[dict]:
    notes = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        text = path.read_text()
        meta, body = parse_frontmatter(text)
        if not meta.get("id"):
            continue
        notes.append({"id": meta["id"], "body": body})
    return notes


# ---------------------------------------------------------------------------
# BM25 + TF-IDF keyword extraction
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


def compute_idf(notes: list[dict]) -> dict[str, float]:
    """Compute IDF over the corpus for keyword extraction."""
    N = len(notes)
    df: dict[str, int] = defaultdict(int)
    for note in notes:
        for tok in set(tokenize(note["body"])):
            df[tok] += 1
    return {tok: math.log((N + 1) / (count + 1)) for tok, count in df.items()}


def extract_keywords(body: str, idf: dict[str, float], top_k: int = KW_TOP_K) -> list[str]:
    """TF-IDF top-K keyword extraction for contextual BM25 query."""
    tokens = tokenize(body)
    if not tokens:
        return tokens
    tf: dict[str, int] = defaultdict(int)
    for t in tokens:
        tf[t] += 1
    scores = {t: tf[t] * idf.get(t, 0.0) for t in tf}
    ranked = sorted(scores, key=lambda x: -scores[x])
    return ranked[:top_k]


def build_bm25(notes: list[dict], ids: list[str]) -> BM25Okapi:
    id_to_body = {n["id"]: n["body"] for n in notes}
    corpus_tokens = [tokenize(id_to_body.get(nid, "")) for nid in ids]
    return BM25Okapi(corpus_tokens)


def bm25_score_vec(bm25: BM25Okapi, query_tokens: list[str], ids: list[str],
                   exclude_id: str) -> np.ndarray:
    scores = np.array(bm25.get_scores(query_tokens), dtype=np.float32)
    if exclude_id in ids:
        scores[ids.index(exclude_id)] = -1.0
    return scores


# ---------------------------------------------------------------------------
# Activation graph (from Spike 5)
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

    def activation_vector(self, query_id: str, all_ids: list[str]) -> np.ndarray:
        return np.array([self._weights.get(frozenset([query_id, nid]), 0.0)
                         for nid in all_ids], dtype=np.float32)


# ---------------------------------------------------------------------------
# Pseudo-note generation (incremental cache)
# ---------------------------------------------------------------------------

def generate_pseudo_notes(notes: list[dict], query_ids: set[str]) -> dict[str, list[str]]:
    cache: dict = {}
    if PSEUDO_CACHE.exists():
        cache = json.loads(PSEUDO_CACHE.read_text())

    needs = [n for n in notes if n["id"] in query_ids and n["id"] not in cache]
    if not needs:
        covered = sum(1 for q in query_ids if q in cache)
        print(f"  All {covered} pseudo-note sets loaded from cache.")
        return cache

    try:
        import anthropic
    except ImportError:
        import subprocess
        subprocess.run(["pip", "install", "anthropic", "-q"], check=True)
        import anthropic

    llm = anthropic.Anthropic()
    print(f"Generating pseudo-notes for {len(needs)} query notes (Haiku)...")

    for i, note in enumerate(needs):
        prompt = (
            f"You are helping expand a knowledge base search query.\n\n"
            f"Below is a note from a cognitive science knowledge base:\n\n"
            f"{note['body'][:2000]}\n\n"
            f"Generate {N_PSEUDO} short notes (2-4 sentences each) about DIFFERENT but related "
            f"cognitive science concepts that would likely appear alongside this note in a knowledge "
            f"base. Each pseudo-note should:\n"
            f"- Cover a distinct related concept (not the same topic)\n"
            f"- Use the vocabulary of that related concept naturally\n"
            f"- Be plausible as a real knowledge base note\n\n"
            f"Return JSON only: {{\"pseudo_notes\": [\"<note1>\", \"<note2>\", \"<note3>\"]}}"
        )
        response = llm.messages.create(
            model=CLAUDE_MODEL, max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        parsed = json.loads(raw)
        cache[note["id"]] = parsed["pseudo_notes"]
        PSEUDO_CACHE.write_text(json.dumps(cache, indent=2))
        if (i + 1) % 20 == 0 or i == len(needs) - 1:
            print(f"  [{i+1}/{len(needs)}] done")

    return cache


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
    s = scores.copy()
    if exclude in ids:
        s[ids.index(exclude)] = -1.0
    return [ids[i] for i in np.argsort(-s)[:k]]


def normalise(scores: np.ndarray) -> np.ndarray:
    m = scores.max()
    return scores / m if m > 0 else scores


def rrf_fuse(ranked_lists: list[list[str]], k: int = RRF_K) -> list[str]:
    """Reciprocal Rank Fusion over multiple ranked lists."""
    scores: dict[str, float] = defaultdict(float)
    for ranked in ranked_lists:
        for rank, nid in enumerate(ranked, 1):
            scores[nid] += 1.0 / (k + rank)
    return sorted(scores, key=lambda x: -scores[x])


# ---------------------------------------------------------------------------
# Coverage diagnostic (runs inside the LOO loop — activation is LOO-accurate)
# ---------------------------------------------------------------------------

def print_coverage(diag: dict, total_gold: int, have_mugi: bool) -> None:
    print(f"\n{'─'*72}")
    print(f"COVERAGE DIAGNOSTIC — oracle analysis (total gold notes: {total_gold})")
    print(f"  Activation: LOO (built from other 298 events per fold)")
    print(f"  BM25 query: MuGI-expanded {'(active)' if have_mugi else '(unavailable)'}")
    print(f"{'─'*72}")
    header = f"  {'Signal':<32}" + "".join(f"  K={k:>3}" for k in DIAG_K_VALUES)
    print(header)
    print("  " + "─" * 74)

    def row(label: str, key: str) -> None:
        cols = "".join(f"  {diag[key][k]/total_gold*100:>5.1f}%" for k in DIAG_K_VALUES)
        print(f"  {label:<32}{cols}")

    row("Body embedding",                  "body")
    row("BM25 + MuGI",                     "bm25")
    row("Activation (LOO)",                "act")
    print("  " + "─" * 74)
    row("Body ∪ BM25+MuGI",               "body_or_bm25")
    row("Body ∪ Activation",               "body_or_act")
    row("BM25 ∪ Activation",               "bm25_or_act")
    row("All three (body ∪ BM25 ∪ act)",   "all_three")
    print("  " + "─" * 74)
    row("BM25 only (body+act miss)",        "bm25_only")
    row("Activation only (body+BM25 miss)", "act_only")
    row("Neither — truly unreachable",      "neither")
    print()
    print(f"  'All three' is the fusion ceiling at each K.")
    print(f"  'Neither' notes require a fundamentally different retrieval mechanism.")


# ---------------------------------------------------------------------------
# Full evaluation (LOO — also collects coverage diagnostic in same pass)
# ---------------------------------------------------------------------------

def evaluate(
    events: list[dict],
    ids: list[str],
    body_mat: np.ndarray,
    id_to_pos: dict[str, int],
    bm25_index: BM25Okapi,
    id_to_body: dict[str, str],
    pseudo_cache: dict[str, list[str]],
    idf: dict[str, float],
) -> tuple[dict, dict, int]:
    ks = [3, 5, 10]
    have_mugi = bool(pseudo_cache)

    # Strategy keys
    beta_plain_keys = [f"body_bm25_b{int(b*10):02d}" for b in BETA_VALUES]
    beta_mugi_keys  = [f"body_mugi_b{int(b*10):02d}" for b in BETA_VALUES]
    beta_kw_keys    = [f"body_kw_b{int(b*10):02d}" for b in BETA_VALUES]

    all_keys = (
        ["body_sim", "bm25_plain", "bm25_mugi", "bm25_keyword"]
        + beta_plain_keys + beta_mugi_keys + beta_kw_keys
        + ["rrf_body_plain", "rrf_body_mugi", "rrf_body_kw"]
        + ["rrf_3way", "blend_3way_b02", "blend_3way_b03"]
    )

    recall: dict[str, dict[int, list[float]]] = {s: {k: [] for k in ks} for s in all_keys}
    mrr_scores: dict[str, list[float]] = {s: [] for s in all_keys}

    # Coverage diagnostic accumulators (Venn diagram across all three signals)
    diag_keys = ["body", "bm25", "act", "body_or_bm25", "body_or_act",
                 "bm25_or_act", "all_three", "bm25_only", "act_only", "neither"]
    diag: dict[str, dict[int, int]] = {k: {K: 0 for K in DIAG_K_VALUES} for k in diag_keys}
    total_gold = 0

    for i, event in enumerate(events):
        qid = event["qid"]
        gold = [g for g in event["gold_ids"] if g in id_to_pos]
        if not gold or qid not in id_to_pos:
            continue

        # Body + BM25 scores
        qidx = id_to_pos[qid]
        body_scores = body_mat @ body_mat[qidx]

        plain_tokens = tokenize(id_to_body.get(qid, ""))
        kw_tokens    = extract_keywords(id_to_body.get(qid, ""), idf)
        bm25_plain_s = bm25_score_vec(bm25_index, plain_tokens, ids, qid)
        bm25_kw_s    = bm25_score_vec(bm25_index, kw_tokens, ids, qid)

        if have_mugi and qid in pseudo_cache:
            expanded = id_to_body.get(qid, "") + " " + " ".join(pseudo_cache[qid])
            bm25_mugi_s = bm25_score_vec(bm25_index, tokenize(expanded), ids, qid)
        else:
            bm25_mugi_s = bm25_plain_s

        # Activation graph (LOO)
        graph = ActivationGraph()
        for j, ev in enumerate(events):
            if j != i:
                graph.add_event(ev["qid"], ev["gold_ids"])
        act_scores = graph.activation_vector(qid, ids)
        act_scores_norm = normalise(act_scores.copy())

        # Coverage diagnostic — Venn diagram at each K (uses LOO activation)
        gold_set = set(gold)
        total_gold += len(gold_set)
        for K in DIAG_K_VALUES:
            body_top = set(top_k_ids(body_scores, ids, qid, K))
            bm25_top = set(top_k_ids(bm25_mugi_s, ids, qid, K))
            act_top  = set(top_k_ids(act_scores, ids, qid, K))
            union_all = body_top | bm25_top | act_top
            diag["body"][K]        += len(gold_set & body_top)
            diag["bm25"][K]        += len(gold_set & bm25_top)
            diag["act"][K]         += len(gold_set & act_top)
            diag["body_or_bm25"][K]+= len(gold_set & (body_top | bm25_top))
            diag["body_or_act"][K] += len(gold_set & (body_top | act_top))
            diag["bm25_or_act"][K] += len(gold_set & (bm25_top | act_top))
            diag["all_three"][K]   += len(gold_set & union_all)
            diag["bm25_only"][K]   += len(gold_set & (bm25_top - body_top - act_top))
            diag["act_only"][K]    += len(gold_set & (act_top - body_top - bm25_top))
            diag["neither"][K]     += len(gold_set - union_all)

        # Ranked lists for RRF
        body_ranked  = top_k_ids(body_scores, ids, qid, len(ids))
        plain_ranked = top_k_ids(bm25_plain_s, ids, qid, len(ids))
        mugi_ranked  = top_k_ids(bm25_mugi_s, ids, qid, len(ids))
        kw_ranked    = top_k_ids(bm25_kw_s, ids, qid, len(ids))
        act_ranked   = top_k_ids(act_scores, ids, qid, len(ids))

        retrieved: dict[str, list[str]] = {}

        # Baselines
        retrieved["body_sim"]     = body_ranked[:CLUSTER_K]
        retrieved["bm25_plain"]   = plain_ranked[:CLUSTER_K]
        retrieved["bm25_mugi"]    = mugi_ranked[:CLUSTER_K]
        retrieved["bm25_keyword"] = kw_ranked[:CLUSTER_K]

        # Weighted sum sweeps
        for b, key in zip(BETA_VALUES, beta_plain_keys):
            s = (1-b) * body_scores + b * normalise(bm25_plain_s)
            retrieved[key] = top_k_ids(s, ids, qid, CLUSTER_K)
        for b, key in zip(BETA_VALUES, beta_mugi_keys):
            s = (1-b) * body_scores + b * normalise(bm25_mugi_s)
            retrieved[key] = top_k_ids(s, ids, qid, CLUSTER_K)
        for b, key in zip(BETA_VALUES, beta_kw_keys):
            s = (1-b) * body_scores + b * normalise(bm25_kw_s)
            retrieved[key] = top_k_ids(s, ids, qid, CLUSTER_K)

        # RRF two-way
        retrieved["rrf_body_plain"] = rrf_fuse([body_ranked, plain_ranked])[:CLUSTER_K]
        retrieved["rrf_body_mugi"]  = rrf_fuse([body_ranked, mugi_ranked])[:CLUSTER_K]
        retrieved["rrf_body_kw"]    = rrf_fuse([body_ranked, kw_ranked])[:CLUSTER_K]

        # Three-way: body + BM25 MuGI + activation
        retrieved["rrf_3way"]       = rrf_fuse([body_ranked, mugi_ranked, act_ranked])[:CLUSTER_K]
        # Weighted three-way: equal thirds as starting point, then tuned
        s3a = 0.6 * body_scores + 0.2 * normalise(bm25_mugi_s) + 0.2 * act_scores_norm
        s3b = 0.5 * body_scores + 0.3 * normalise(bm25_mugi_s) + 0.2 * act_scores_norm
        retrieved["blend_3way_b02"] = top_k_ids(s3a, ids, qid, CLUSTER_K)
        retrieved["blend_3way_b03"] = top_k_ids(s3b, ids, qid, CLUSTER_K)

        for s in all_keys:
            if s not in retrieved:
                continue
            r = retrieved[s]
            for k in ks:
                recall[s][k].append(recall_at_k(r, gold, k))
            mrr_scores[s].append(reciprocal_rank(r, gold))

    results: dict = {}
    for s in all_keys:
        if not recall[s][10]:
            continue
        results[s] = {
            "recall": {k: float(np.mean(recall[s][k])) for k in ks},
            "mrr": float(np.mean(mrr_scores[s])),
            "n": len(recall[s][10]),
        }
    return results, diag, total_gold


# ---------------------------------------------------------------------------
# Results writer
# ---------------------------------------------------------------------------

def write_results(results: dict, n_events: int) -> None:
    if RESULTS_PATH.exists():
        runs = sorted(SPIKE6A_DIR.glob("results-run*.md"))
        shutil.copy(RESULTS_PATH, SPIKE6A_DIR / f"results-run{len(runs)+1}.md")

    def row(key: str, label: str) -> str:
        if key not in results:
            return ""
        r = results[key]
        return f"| {label} | {r['recall'][3]:.3f} | {r['recall'][5]:.3f} | {r['recall'][10]:.3f} | {r['mrr']:.3f} |"

    lines = [
        "# Spike 6A Results — BM25 + MuGI Extended (RRF, Three-Way, Coverage)",
        "",
        f"*Run: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        f"*{n_events} events, cluster window top-{CLUSTER_K}, {N_PSEUDO} pseudo-notes, RRF k={RRF_K}*",
        "",
        "Reference: body baseline R@10=0.534 | body+activation R@10=0.640 | target R@10≥0.700",
        "",
        "---", "",
        "## Baselines",
        "", "| Strategy | R@3 | R@5 | R@10 | MRR |", "|----------|-----|-----|------|-----|",
        row("body_sim",     "Body embedding"),
        row("bm25_plain",   "BM25 plain (full body)"),
        row("bm25_mugi",    "BM25 MuGI (expanded)"),
        row("bm25_keyword", "BM25 keyword TF-IDF"),
        "",
        "---", "",
        "## Weighted sum — Body + BM25 variant",
        "", "| β | BM25 plain R@10 | BM25 MuGI R@10 | BM25 keyword R@10 |",
        "|---|----------------|----------------|-------------------|",
    ]
    for b in BETA_VALUES:
        p  = results.get(f"body_bm25_b{int(b*10):02d}", {}).get("recall", {}).get(10, 0)
        m  = results.get(f"body_mugi_b{int(b*10):02d}", {}).get("recall", {}).get(10, 0)
        kw = results.get(f"body_kw_b{int(b*10):02d}", {}).get("recall", {}).get(10, 0)
        lines.append(f"| β={b} | {p:.3f} | {m:.3f} | {kw:.3f} |")

    lines += [
        "", "---", "",
        "## RRF fusion",
        "", "| Strategy | R@3 | R@5 | R@10 | MRR |", "|----------|-----|-----|------|-----|",
        row("rrf_body_plain", "RRF: body + BM25 plain"),
        row("rrf_body_mugi",  "RRF: body + BM25 MuGI"),
        row("rrf_body_kw",    "RRF: body + BM25 keyword"),
        "",
        "---", "",
        "## Three-way: body + BM25 MuGI + activation",
        "", "| Strategy | R@3 | R@5 | R@10 | MRR |", "|----------|-----|-----|------|-----|",
        row("body_sim",         "Body only (reference)"),
        row("rrf_3way",         "RRF 3-way (body + MuGI + activation)"),
        row("blend_3way_b02",   "Blend 3-way (0.6 body + 0.2 MuGI + 0.2 act)"),
        row("blend_3way_b03",   "Blend 3-way (0.5 body + 0.3 MuGI + 0.2 act)"),
        "",
        "---", "",
        "## Go / No-go",
        "", "Success criterion: R@10 ≥ 0.70 (vs 0.640 body+activation ceiling)",
        "", "[ ] Go — R@10 ≥ 0.70",
        "[ ] Partial — meaningful improvement, below threshold",
        "[ ] No-go — coverage diagnostic shows insufficient reachable gold notes",
    ]

    RESULTS_PATH.write_text("\n".join(l for l in lines if l is not None))
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

    print("Loading corpus...")
    notes = load_corpus()
    id_to_body = {n["id"]: n["body"] for n in notes}
    print(f"  {len(notes)} notes")

    print("Loading embeddings...")
    ec = json.loads(EMBEDDINGS_CACHE.read_text())
    ids: list[str] = ec["ids"]
    id_to_pos = {nid: i for i, nid in enumerate(ids)}
    body_mat = np.array(ec["body"], dtype=np.float32)
    body_mat /= np.linalg.norm(body_mat, axis=1, keepdims=True) + 1e-9
    print(f"  {len(ids)} notes, dim={body_mat.shape[1]}")

    print("Building BM25 index and IDF table...")
    bm25_index = build_bm25(notes, ids)
    idf = compute_idf(notes)
    print(f"  Done ({len(idf)} unique terms)")

    print("Loading Spike 4D ground truth...")
    ground_truth = json.loads(GROUND_TRUTH_CACHE.read_text())
    events: list[dict] = []
    for qid, interactions in ground_truth.items():
        gold_ids = [
            x["id"] for x in interactions
            if x["id"] in id_to_pos and x.get("operation", "NOTHING") != "NOTHING"
        ]
        if gold_ids and qid in id_to_pos:
            events.append({"qid": qid, "gold_ids": gold_ids})
    print(f"  {len(events)} events with ≥1 confirmed interaction")

    pseudo_cache: dict = {}
    if not SKIP_API:
        query_ids = {e["qid"] for e in events}
        pseudo_cache = generate_pseudo_notes(notes, query_ids)
        covered = sum(1 for e in events if e["qid"] in pseudo_cache)
        print(f"  Pseudo-notes available for {covered}/{len(events)} query notes")
    else:
        print("  --no-api: BM25-plain and keyword only, no MuGI")

    print("\nRunning evaluation + coverage diagnostic (LOO activation per fold)...")
    print("  (building 299 activation graphs — a few minutes)")
    results, diag, total_gold = evaluate(events, ids, body_mat, id_to_pos,
                                         bm25_index, id_to_body, pseudo_cache, idf)
    print_coverage(diag, total_gold, bool(pseudo_cache))

    # Print summary
    print(f"\n{'─'*70}")
    print("BASELINES")
    print(f"  {'Strategy':<36} {'R@3':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
    print("─" * 70)
    for key, label in [
        ("body_sim",     "Body embedding"),
        ("bm25_plain",   "BM25 plain"),
        ("bm25_mugi",    "BM25 MuGI"),
        ("bm25_keyword", "BM25 keyword TF-IDF"),
    ]:
        if key in results:
            r = results[key]
            print(f"  {label:<36} {r['recall'][3]:>6.3f} {r['recall'][5]:>6.3f} {r['recall'][10]:>6.3f} {r['mrr']:>6.3f}")

    print(f"\n{'─'*70}")
    print("RRF FUSION")
    print(f"  {'Strategy':<36} {'R@3':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
    print("─" * 70)
    for key, label in [
        ("rrf_body_plain", "RRF: body + BM25 plain"),
        ("rrf_body_mugi",  "RRF: body + BM25 MuGI"),
        ("rrf_body_kw",    "RRF: body + BM25 keyword"),
    ]:
        if key in results:
            r = results[key]
            print(f"  {label:<36} {r['recall'][3]:>6.3f} {r['recall'][5]:>6.3f} {r['recall'][10]:>6.3f} {r['mrr']:>6.3f}")

    print(f"\n{'─'*70}")
    print("THREE-WAY: BODY + BM25 MuGI + ACTIVATION")
    print(f"  {'Strategy':<36} {'R@3':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
    print("─" * 70)
    for key, label in [
        ("rrf_3way",       "RRF 3-way"),
        ("blend_3way_b02", "Blend: 0.6/0.2/0.2"),
        ("blend_3way_b03", "Blend: 0.5/0.3/0.2"),
    ]:
        if key in results:
            r = results[key]
            print(f"  {label:<36} {r['recall'][3]:>6.3f} {r['recall'][5]:>6.3f} {r['recall'][10]:>6.3f} {r['mrr']:>6.3f}")

    print(f"\n{'─'*70}")
    print("SUMMARY vs references")
    body_r10 = results.get("body_sim", {}).get("recall", {}).get(10, 0)
    best_rrf = max((results.get(k, {}).get("recall", {}).get(10, 0)
                    for k in ["rrf_body_plain", "rrf_body_mugi", "rrf_body_kw"]), default=0)
    best_3way = max((results.get(k, {}).get("recall", {}).get(10, 0)
                     for k in ["rrf_3way", "blend_3way_b02", "blend_3way_b03"]), default=0)
    print(f"  Body baseline:              R@10={body_r10:.3f}")
    print(f"  Best RRF (2-way):           R@10={best_rrf:.3f}")
    print(f"  Best 3-way:                 R@10={best_3way:.3f}")
    print(f"  Spike 5 body+activation:    R@10=0.640  (reference)")
    print(f"  Target:                     R@10≥0.700")

    write_results(results, len(events))
    print("\nDone.")


if __name__ == "__main__":
    main()
