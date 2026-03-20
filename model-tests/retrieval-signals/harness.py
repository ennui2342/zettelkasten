"""Retrieval workbench harness.

Runs LOO evaluation across any set of signals and reports:
  1. Coverage diagnostic  — oracle Venn diagram: what fraction of gold notes
                            is reachable by each signal at K=20/50/100/200?
  2. Per-signal retrieval metrics — R@3, R@5, R@10, MRR
  3. Fusion results       — RRF and weighted blend across all active signals

Three areas of improvement, each informed by different outputs:
  Coverage   → add new signals; watch 'All signals' and 'Neither' rows
  Ranking    → embedding fine-tuning, BM25 query improvements; watch per-signal R@10
  Fusion     → blend weights, RRF; watch combined R@10 vs coverage ceiling
"""
from __future__ import annotations

import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

DIAG_K_VALUES = [20, 50, 100, 200]
CLUSTER_K = 20
RRF_K = 60


# ---------------------------------------------------------------------------
# Retrieval utilities
# ---------------------------------------------------------------------------

def normalise(v: np.ndarray) -> np.ndarray:
    m = v.max()
    return v / m if m > 0 else v


def top_k(scores: np.ndarray, ids: list[str], exclude: str, k: int) -> list[str]:
    s = scores.copy()
    if exclude in ids:
        s[ids.index(exclude)] = -1.0
    return [ids[i] for i in np.argsort(-s)[:k]]


def rrf_fuse(ranked_lists: list[list[str]], k: int = RRF_K) -> list[str]:
    scores: dict[str, float] = defaultdict(float)
    for ranked in ranked_lists:
        for rank, nid in enumerate(ranked, 1):
            scores[nid] += 1.0 / (k + rank)
    return sorted(scores, key=lambda x: -scores[x])


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


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

def run(
    events: list[dict],
    ids: list[str],
    body_mat: np.ndarray,
    id_to_pos: dict[str, int],
    signals: list,            # instantiated Signal objects
    results_dir: Path,
    reranker=None,            # optional CrossEncoderReranker; applied after blend fusion
) -> None:
    ks = [3, 5, 10]
    sig_names = [s.name for s in signals]
    loo_signals = [s for s in signals if s.needs_loo]
    static_signals = [s for s in signals if not s.needs_loo]

    # Metrics accumulators
    recall: dict[str, dict[int, list[float]]] = {n: {k: [] for k in ks} for n in sig_names}
    mrr: dict[str, list[float]] = {n: [] for n in sig_names}

    # Coverage accumulators — individual signals + all unions
    diag_indiv: dict[str, dict[int, int]] = {n: {K: 0 for K in DIAG_K_VALUES}
                                              for n in sig_names}
    diag_union_all: dict[int, int] = {K: 0 for K in DIAG_K_VALUES}
    diag_neither:   dict[int, int] = {K: 0 for K in DIAG_K_VALUES}
    diag_unique:    dict[str, dict[int, int]] = {n: {K: 0 for K in DIAG_K_VALUES}
                                                 for n in sig_names}
    total_gold = 0

    # Fusion accumulators
    fuse_rrf_recall:      dict[int, list[float]] = {k: [] for k in ks}
    fuse_rrf_mrr:         list[float] = []
    fuse_blend_recall:    dict[int, list[float]] = {k: [] for k in ks}
    fuse_blend_mrr:       list[float] = []
    fuse_rerank_recall:   dict[int, list[float]] = {k: [] for k in ks}
    fuse_rerank_mrr:      list[float] = []

    print(f"Running LOO evaluation over {len(events)} events...")
    for i, event in enumerate(events):
        qid = event["qid"]
        gold = [g for g in event["gold_ids"] if g in id_to_pos]
        if not gold or qid not in id_to_pos:
            continue
        gold_set = set(gold)
        total_gold += len(gold_set)
        qidx = id_to_pos[qid]

        # Build loo_events for needs_loo signals
        loo_events = [ev for j, ev in enumerate(events) if j != i]

        # Compute score vectors for all signals
        score_vecs: dict[str, np.ndarray] = {}
        for sig in signals:
            score_vecs[sig.name] = sig.scores(
                qid, qidx, ids, body_mat,
                loo_events=loo_events if sig.needs_loo else None
            )

        # Per-signal metrics
        ranked: dict[str, list[str]] = {}
        for sig in signals:
            r = top_k(score_vecs[sig.name], ids, qid, len(ids))
            ranked[sig.name] = r
            ret = r[:CLUSTER_K]
            for k in ks:
                recall[sig.name][k].append(recall_at_k(ret, gold, k))
            mrr[sig.name].append(reciprocal_rank(ret, gold))

        # Coverage diagnostic
        tops: dict[str, set[str]] = {}
        for K in DIAG_K_VALUES:
            for sig in signals:
                tops[sig.name] = set(top_k(score_vecs[sig.name], ids, qid, K))
            union_all = set().union(*tops.values())
            diag_union_all[K] += len(gold_set & union_all)
            diag_neither[K]   += len(gold_set - union_all)
            for sig in signals:
                diag_indiv[sig.name][K] += len(gold_set & tops[sig.name])
                others = set().union(*(tops[s.name] for s in signals if s.name != sig.name))
                diag_unique[sig.name][K] += len(gold_set & (tops[sig.name] - others))

        # Fusion: RRF across all signals
        rrf_result = rrf_fuse([ranked[n] for n in sig_names])[:CLUSTER_K]
        for k in ks:
            fuse_rrf_recall[k].append(recall_at_k(rrf_result, gold, k))
        fuse_rrf_mrr.append(reciprocal_rank(rrf_result, gold))

        # Fusion: weighted blend (equal weights as starting point)
        n_sigs = len(signals)
        blended = sum(normalise(score_vecs[sig.name]) for sig in signals) / n_sigs
        blended_result = top_k(blended, ids, qid, CLUSTER_K)
        for k in ks:
            fuse_blend_recall[k].append(recall_at_k(blended_result, gold, k))
        fuse_blend_mrr.append(reciprocal_rank(blended_result, gold))

        # Optional: cross-encoder reranking of blend result
        if reranker is not None:
            reranked_result = reranker.rerank(qid, blended_result)
            for k in ks:
                fuse_rerank_recall[k].append(recall_at_k(reranked_result, gold, k))
            fuse_rerank_mrr.append(reciprocal_rank(reranked_result, gold))

    # Compute means
    def mean_results(rec_d, mrr_l):
        return {
            "recall": {k: float(np.mean(rec_d[k])) if rec_d[k] else 0.0 for k in ks},
            "mrr": float(np.mean(mrr_l)) if mrr_l else 0.0,
        }

    sig_results = {n: mean_results(recall[n], mrr[n]) for n in sig_names}
    rrf_results = mean_results(fuse_rrf_recall, fuse_rrf_mrr)
    blend_results = mean_results(fuse_blend_recall, fuse_blend_mrr)
    rerank_results = mean_results(fuse_rerank_recall, fuse_rerank_mrr) if reranker else None
    n_eval = len(fuse_rrf_mrr)

    # Print coverage diagnostic
    _print_coverage(sig_names, diag_indiv, diag_unique, diag_union_all,
                    diag_neither, total_gold)

    # Print metrics
    _print_metrics(sig_names, sig_results, rrf_results, blend_results, n_eval,
                   rerank_results)

    # Write results
    _write_results(sig_names, sig_results, rrf_results, blend_results,
                   diag_indiv, diag_unique, diag_union_all, diag_neither,
                   total_gold, n_eval, results_dir, rerank_results)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _print_coverage(sig_names, diag_indiv, diag_unique, union_all, neither,
                    total_gold) -> None:
    print(f"\n{'─'*76}")
    print(f"COVERAGE DIAGNOSTIC  (total gold notes: {total_gold})")
    print(f"{'─'*76}")
    header = f"  {'Signal':<28}" + "".join(f"  K={K:>3}" for K in DIAG_K_VALUES)
    print(header)
    print("  " + "─" * 74)

    def pct(n, total=total_gold):
        return f"{n/total*100:>5.1f}%"

    for name in sig_names:
        cols = "".join(f"  {pct(diag_indiv[name][K])}" for K in DIAG_K_VALUES)
        print(f"  {name:<28}{cols}")
    print("  " + "─" * 74)
    cols = "".join(f"  {pct(union_all[K])}" for K in DIAG_K_VALUES)
    print(f"  {'All signals (union)':<28}{cols}")
    cols = "".join(f"  {pct(neither[K])}" for K in DIAG_K_VALUES)
    print(f"  {'Neither — unreachable':<28}{cols}")
    print("  " + "─" * 74)
    print("  Unique coverage (gold notes only this signal finds at K=20):")
    for name in sig_names:
        u = diag_unique[name][20]
        print(f"    {name:<26}  {pct(u)}  ({u} notes)")
    print()
    print(f"  Fusion ceiling at K=20: {union_all[20]/total_gold*100:.1f}%")
    print(f"  True floor (neither):   {neither[20]/total_gold*100:.1f}%")


def _print_metrics(sig_names, sig_results, rrf_results, blend_results,
                   n_eval, rerank_results=None) -> None:
    print(f"\n{'─'*70}")
    print(f"PER-SIGNAL RETRIEVAL  (N={n_eval} events, top-{CLUSTER_K})")
    print(f"  {'Signal':<28} {'R@3':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
    print("  " + "─" * 68)
    for name in sig_names:
        r = sig_results[name]
        print(f"  {name:<28} {r['recall'][3]:>6.3f} {r['recall'][5]:>6.3f} "
              f"{r['recall'][10]:>6.3f} {r['mrr']:>6.3f}")

    print(f"\n{'─'*70}")
    print("FUSION")
    print(f"  {'Strategy':<28} {'R@3':>6} {'R@5':>6} {'R@10':>6} {'MRR':>6}")
    print("  " + "─" * 68)
    rows = [("RRF (all signals)", rrf_results),
            ("Equal blend (all signals)", blend_results)]
    if rerank_results:
        rows.append(("Cross-encoder rerank", rerank_results))
    for label, r in rows:
        print(f"  {label:<28} {r['recall'][3]:>6.3f} {r['recall'][5]:>6.3f} "
              f"{r['recall'][10]:>6.3f} {r['mrr']:>6.3f}")


def _write_results(sig_names, sig_results, rrf_results, blend_results,
                   diag_indiv, diag_unique, union_all, neither,
                   total_gold, n_eval, results_dir: Path,
                   rerank_results=None) -> None:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    path = results_dir / f"run-{ts}.md"

    def pct(n):
        return f"{n/total_gold*100:.1f}%"

    lines = [
        f"# Retrieval Workbench — {ts}",
        f"*{n_eval} events, top-{CLUSTER_K}, signals: {', '.join(sig_names)}*",
        "",
        "---", "",
        "## Coverage diagnostic",
        "",
        "| Signal | K=20 | K=50 | K=100 | K=200 | Unique@20 |",
        "|--------|------|------|-------|-------|-----------|",
    ]
    for name in sig_names:
        u = diag_unique[name][20]
        lines.append(
            f"| {name} | {pct(diag_indiv[name][20])} | {pct(diag_indiv[name][50])} | "
            f"{pct(diag_indiv[name][100])} | {pct(diag_indiv[name][200])} | "
            f"{pct(u)} ({u}) |"
        )
    lines += [
        f"| **All signals** | **{pct(union_all[20])}** | **{pct(union_all[50])}** | "
        f"**{pct(union_all[100])}** | **{pct(union_all[200])}** | — |",
        f"| *Neither* | *{pct(neither[20])}* | *{pct(neither[50])}* | "
        f"*{pct(neither[100])}* | *{pct(neither[200])}* | — |",
        "",
        "---", "",
        "## Per-signal retrieval metrics",
        "",
        "| Signal | R@3 | R@5 | R@10 | MRR |",
        "|--------|-----|-----|------|-----|",
    ]
    for name in sig_names:
        r = sig_results[name]
        lines.append(f"| {name} | {r['recall'][3]:.3f} | {r['recall'][5]:.3f} | "
                     f"{r['recall'][10]:.3f} | {r['mrr']:.3f} |")
    lines += [
        "",
        "---", "",
        "## Fusion",
        "",
        "| Strategy | R@3 | R@5 | R@10 | MRR |",
        "|----------|-----|-----|------|-----|",
        f"| RRF (all signals) | {rrf_results['recall'][3]:.3f} | "
        f"{rrf_results['recall'][5]:.3f} | {rrf_results['recall'][10]:.3f} | "
        f"{rrf_results['mrr']:.3f} |",
        f"| Equal blend | {blend_results['recall'][3]:.3f} | "
        f"{blend_results['recall'][5]:.3f} | {blend_results['recall'][10]:.3f} | "
        f"{blend_results['mrr']:.3f} |",
    ]
    if rerank_results:
        lines.append(
            f"| Cross-encoder rerank | {rerank_results['recall'][3]:.3f} | "
            f"{rerank_results['recall'][5]:.3f} | {rerank_results['recall'][10]:.3f} | "
            f"{rerank_results['mrr']:.3f} |"
        )

    path.write_text("\n".join(lines))
    # Also write latest.md
    (results_dir / "latest.md").write_text("\n".join(lines))
    print(f"\nResults written to {path}")
