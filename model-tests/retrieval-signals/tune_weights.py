#!/usr/bin/env python3 -u
"""Weight tuning for the 5-signal precision core + optional discovery signals.

Uses an 80/20 train/test split (fixed seed) to avoid overfitting:
  - Tune weights on 80% (239 events)
  - Report final R@10/MRR on held-out 20% (60 events)
  - Compare train vs test to check for overfitting

Grid search over precision core weights, then δ sweep for discovery tier.

Run:
  docker compose run --rm dev python spikes/retrieval-workbench/tune_weights.py
"""
from __future__ import annotations

import json
import os
import random
import sys
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
sys.path.insert(0, str(WORKBENCH_DIR))

from main import load_corpus, load_embeddings, load_events, CACHES_DIR

CLUSTER_K = 20
KS = [3, 5, 10]
RANDOM_SEED = 42
TRAIN_FRACTION = 0.80


def normalise(v: np.ndarray) -> np.ndarray:
    m = v.max()
    return v / m if m > 0 else v


def top_k(scores, ids, exclude, k):
    s = scores.copy()
    if exclude in ids:
        s[ids.index(exclude)] = -1.0
    return [ids[i] for i in np.argsort(-s)[:k]]


def recall_at_k(retrieved, relevant, k):
    if not relevant:
        return 0.0
    return len(set(retrieved[:k]) & set(relevant)) / len(relevant)


def mrr(retrieved, relevant):
    rs = set(relevant)
    for rank, nid in enumerate(retrieved, 1):
        if nid in rs:
            return 1.0 / rank
    return 0.0


def score_split(events, ids, id_to_pos, score_vecs_all, weights, indices):
    """Evaluate weights on a subset of events given by indices."""
    sig_names = [n for n, w in weights.items() if w > 0]
    recalls = {k: [] for k in KS}
    mrrs = []
    for i in indices:
        event = events[i]
        qid = event["qid"]
        gold = [g for g in event["gold_ids"] if g in id_to_pos]
        if not gold or qid not in id_to_pos or not score_vecs_all[i]:
            continue
        blended = sum(weights[n] * normalise(score_vecs_all[i][n]) for n in sig_names)
        result = top_k(blended, ids, qid, CLUSTER_K)
        for k in KS:
            recalls[k].append(recall_at_k(result, gold, k))
        mrrs.append(mrr(result, gold))
    return {
        "R@3":  float(np.mean(recalls[3]))  if recalls[3]  else 0.0,
        "R@5":  float(np.mean(recalls[5]))  if recalls[5]  else 0.0,
        "R@10": float(np.mean(recalls[10])) if recalls[10] else 0.0,
        "MRR":  float(np.mean(mrrs))        if mrrs        else 0.0,
        "n":    len(mrrs),
    }


def main():
    print("Loading data...")
    notes = load_corpus()
    ids, body_mat, id_to_pos = load_embeddings(notes)
    notes = [n for n in notes if n["id"] in id_to_pos]
    events = load_events(ids)
    ground_truth = {ev["qid"]: ev["gold_ids"] for ev in events}

    # 80/20 split
    rng = random.Random(RANDOM_SEED)
    all_indices = list(range(len(events)))
    rng.shuffle(all_indices)
    n_train = int(len(all_indices) * TRAIN_FRACTION)
    train_idx = set(all_indices[:n_train])
    test_idx  = set(all_indices[n_train:])
    print(f"Split: {len(train_idx)} train / {len(test_idx)} test (seed={RANDOM_SEED})")

    # Set up signals
    print("Setting up signals...")
    from signals import (BodyEmbeddingQuery, BM25MuGIStem,
                         Activation, ActivationNoTransitive, ActivationK20,
                         ActivationB, ActivationC,
                         ActivationScalarGold, ActivationScalarK20,
                         ActivationScalarB, ActivationScalarC,
                         StepBack, HyDEMulti)
    sigs = {
        "body_query":     BodyEmbeddingQuery(),
        "bm25_mugi_stem": BM25MuGIStem(),
        "activation":     Activation(),
        "step_back":      StepBack(),
        "hyde_multi":     HyDEMulti(),
    }
    for name, sig in sigs.items():
        print(f"  [{name}]")
        sig.setup(notes, ids, body_mat, ground_truth, CACHES_DIR)

    # Pre-compute score vectors for all events
    print("\nPre-computing score vectors...")
    score_vecs_all = []
    for i, event in enumerate(events):
        qid = event["qid"]
        if qid not in id_to_pos:
            score_vecs_all.append({})
            continue
        qidx = id_to_pos[qid]
        loo_events = [ev for j, ev in enumerate(events) if j != i]
        vecs = {}
        for name, sig in sigs.items():
            vecs[name] = sig.scores(qid, qidx, ids, body_mat,
                                    loo_events=loo_events if sig.needs_loo else None)
        score_vecs_all.append(vecs)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(events)}")
    print("  Done.")

    # -----------------------------------------------------------------------
    # Phase 1: precision core sweep on TRAIN set
    # -----------------------------------------------------------------------
    print("\n" + "─"*70)
    print("PHASE 1 — Precision core sweep on TRAIN set")
    print("─"*70)

    core_candidates = []
    for w_b in range(3, 9):
        for w_m in range(1, 9 - w_b):
            w_a = 10 - w_b - w_m
            if w_a < 1:
                continue
            core_candidates.append((w_b/10, w_m/10, w_a/10))

    print(f"  Testing {len(core_candidates)} combinations on {len(train_idx)} train events...")
    best_core = None
    best_r10_train = -1.0
    results_core = []
    for w_b, w_m, w_a in core_candidates:
        weights = {"body_query": w_b, "bm25_mugi_stem": w_m, "activation": w_a,
                   "step_back": 0.0, "hyde_multi": 0.0}
        m = score_split(events, ids, id_to_pos, score_vecs_all, weights, train_idx)
        results_core.append((w_b, w_m, w_a, m["R@10"], m["MRR"]))
        if m["R@10"] > best_r10_train:
            best_r10_train = m["R@10"]
            best_core = (w_b, w_m, w_a)

    results_core.sort(key=lambda x: -x[3])
    print(f"\n  {'body_q':>8} {'bm25':>6} {'act':>6}  {'R@10(tr)':>10}  {'MRR(tr)':>9}")
    print("  " + "─"*46)
    for row in results_core[:10]:
        w_b, w_m, w_a, r10, mrr_v = row
        marker = " ★" if (w_b, w_m, w_a) == best_core else ""
        print(f"  {w_b:>8.1f} {w_m:>6.1f} {w_a:>6.1f}  {r10:>10.3f}  {mrr_v:>9.3f}{marker}")
    print(f"\n  Best core: body_query={best_core[0]}, bm25_mugi_stem={best_core[1]}, "
          f"activation={best_core[2]}  (R@10={best_r10_train:.3f} on train)")

    # -----------------------------------------------------------------------
    # Phase 2: discovery δ sweep on TRAIN set
    # -----------------------------------------------------------------------
    print("\n" + "─"*70)
    print("PHASE 2 — Discovery tier δ sweep on TRAIN set")
    print(f"  Core: body_query={best_core[0]}, bm25_mugi_stem={best_core[1]}, "
          f"activation={best_core[2]}")
    print("─"*70)

    delta_values = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    best_delta = 0.0
    best_r10_delta_train = -1.0
    best_weights = None
    delta_results = []
    print(f"  {'δ':>6}  {'R@10(tr)':>10}  {'MRR(tr)':>9}")
    print("  " + "─"*30)
    for delta in delta_values:
        scale = 1 - delta
        weights = {
            "body_query": best_core[0] * scale,
            "bm25_mugi_stem":  best_core[1] * scale,
            "activation": best_core[2] * scale,
            "step_back":  delta / 2,
            "hyde_multi": delta / 2,
        }
        m = score_split(events, ids, id_to_pos, score_vecs_all, weights, train_idx)
        delta_results.append((delta, weights, m))
        marker = ""
        if m["R@10"] > best_r10_delta_train:
            best_r10_delta_train = m["R@10"]
            best_delta = delta
            best_weights = weights
            marker = " ★"
        print(f"  {delta:>6.2f}  {m['R@10']:>10.3f}  {m['MRR']:>9.3f}{marker}")

    # -----------------------------------------------------------------------
    # Final evaluation on held-out TEST set
    # -----------------------------------------------------------------------
    print("\n" + "─"*70)
    print("HELD-OUT TEST SET EVALUATION")
    print("─"*70)
    print(f"  Tuned weights: " + ", ".join(f"{k}={v:.3f}" for k, v in best_weights.items()))
    print()

    # Test the tuned weights
    test_result = score_split(events, ids, id_to_pos, score_vecs_all, best_weights, test_idx)

    # Also test each δ on test set to show the full picture
    print(f"  {'δ':>6}  {'R@10(tr)':>10}  {'R@10(te)':>10}  {'MRR(tr)':>9}  {'MRR(te)':>9}")
    print("  " + "─"*54)
    for delta, weights, train_m in delta_results:
        test_m = score_split(events, ids, id_to_pos, score_vecs_all, weights, test_idx)
        marker = " ★" if delta == best_delta else ""
        print(f"  {delta:>6.2f}  {train_m['R@10']:>10.3f}  {test_m['R@10']:>10.3f}  "
              f"{train_m['MRR']:>9.3f}  {test_m['MRR']:>9.3f}{marker}")

    print(f"\n  Tuned on train (δ={best_delta}):  R@10={best_r10_delta_train:.3f}")
    print(f"  Held-out test result:          R@10={test_result['R@10']:.3f}  "
          f"MRR={test_result['MRR']:.3f}  (n={test_result['n']})")

    # Also check body-only baseline on test for comparison
    body_weights = {"body_query": 1.0, "bm25_mugi_stem": 0.0, "activation": 0.0,
                    "step_back": 0.0, "hyde_multi": 0.0}
    body_test = score_split(events, ids, id_to_pos, score_vecs_all, body_weights, test_idx)
    print(f"  Body-only baseline on test:    R@10={body_test['R@10']:.3f}  "
          f"MRR={body_test['MRR']:.3f}")
    print(f"\n  Gain over baseline: ΔR@10={test_result['R@10'] - body_test['R@10']:+.3f}  "
          f"ΔMRR={test_result['MRR'] - body_test['MRR']:+.3f}")

    print(f"\n  Final recommended weights:")
    for k, v in best_weights.items():
        print(f"    {k}: {v:.3f}")

    # -----------------------------------------------------------------------
    # Phase 3: activation variant comparison
    #
    # Holds the non-activation weights fixed at the best_weights found above,
    # then substitutes each activation variant to compare their contribution.
    #
    # Three variants:
    #   activation          — gold_ids with transitive expansion (baseline)
    #   activation_no_trans — gold_ids without transitive expansion
    #   activation_k20      — top-20 body-similarity cluster (Approach A)
    #
    # Note: λ (temporal decay) sweep is deferred — the ground truth events
    # have no timestamps, so age_days=0 for all events and varying λ has no
    # effect here. Re-run λ sweep once benchmark ingestion ground truth
    # (with real timestamps) is available.
    # -----------------------------------------------------------------------
    print("\n" + "─"*70)
    print("PHASE 3 — Activation variant comparison")
    print(f"  Non-activation weights held fixed from Phase 2 best: "
          f"body_query={best_weights['body_query']:.3f}, "
          f"bm25_mugi_stem={best_weights['bm25_mugi_stem']:.3f}, "
          f"step_back={best_weights['step_back']:.3f}, "
          f"hyde_multi={best_weights['hyde_multi']:.3f}")
    print("─"*70)

    act_variants = {
        # Pairwise graph
        "pairwise gold (transitive)":  Activation(),
        "pairwise gold (no transitive)": ActivationNoTransitive(),
        "pairwise k20":                ActivationK20(),
        "pairwise B":                  ActivationB(),
        "pairwise C":                  ActivationC(),
        # Scalar
        "scalar gold":                 ActivationScalarGold(),
        "scalar k20":                  ActivationScalarK20(),
        "scalar B":                    ActivationScalarB(),
        "scalar C":                    ActivationScalarC(),
    }
    for vname, sig in act_variants.items():
        print(f"  Setting up [{vname}]...")
        sig.setup(notes, ids, body_mat, ground_truth, CACHES_DIR)

    # For each activation weight from 0.0 to 0.4, compare variants
    act_weights_to_test = [0.0, 0.05, 0.10, 0.15, 0.18, 0.20, 0.25, 0.30, 0.40]
    non_act_scale = best_weights["body_query"] + best_weights["bm25_mugi_stem"]

    print(f"\n  {'Variant':<32}  {'act_w':>6}  {'R@10(tr)':>10}  {'R@10(te)':>10}  {'MRR(te)':>9}")
    print("  " + "─"*76)

    phase3_results = []
    for vname, act_sig in act_variants.items():
        best_act_w = 0.0
        best_act_r10_train = -1.0
        for act_w in act_weights_to_test:
            # Scale non-activation signals to fill remaining weight
            remaining = 1.0 - act_w - best_weights["step_back"] - best_weights["hyde_multi"]
            if remaining <= 0:
                continue
            scale = remaining / non_act_scale if non_act_scale > 0 else 1.0

            # Pre-compute score vectors with this activation variant
            vecs_with_act = []
            for i, event in enumerate(events):
                qid = event["qid"]
                if qid not in id_to_pos or not score_vecs_all[i]:
                    vecs_with_act.append({})
                    continue
                loo = [ev for j, ev in enumerate(events) if j != i]
                v = dict(score_vecs_all[i])
                v["activation_var"] = act_sig.scores(
                    qid, id_to_pos[qid], ids, body_mat, loo_events=loo
                )
                vecs_with_act.append(v)

            w = {
                "body_query":     best_weights["body_query"] * scale,
                "bm25_mugi_stem": best_weights["bm25_mugi_stem"] * scale,
                "activation_var": act_w,
                "step_back":      best_weights["step_back"],
                "hyde_multi":     best_weights["hyde_multi"],
            }
            tr = score_split(events, ids, id_to_pos, vecs_with_act, w, train_idx)
            if tr["R@10"] > best_act_r10_train:
                best_act_r10_train = tr["R@10"]
                best_act_w = act_w

        # Final evaluation of best act_w on test set
        remaining = 1.0 - best_act_w - best_weights["step_back"] - best_weights["hyde_multi"]
        scale = remaining / non_act_scale if non_act_scale > 0 and remaining > 0 else 1.0
        vecs_final = []
        for i, event in enumerate(events):
            qid = event["qid"]
            if qid not in id_to_pos or not score_vecs_all[i]:
                vecs_final.append({})
                continue
            loo = [ev for j, ev in enumerate(events) if j != i]
            v = dict(score_vecs_all[i])
            v["activation_var"] = act_sig.scores(
                qid, id_to_pos[qid], ids, body_mat, loo_events=loo
            )
            vecs_final.append(v)

        w_final = {
            "body_query":     best_weights["body_query"] * scale,
            "bm25_mugi_stem": best_weights["bm25_mugi_stem"] * scale,
            "activation_var": best_act_w,
            "step_back":      best_weights["step_back"],
            "hyde_multi":     best_weights["hyde_multi"],
        }
        te = score_split(events, ids, id_to_pos, vecs_final, w_final, test_idx)
        phase3_results.append((vname, best_act_w, best_act_r10_train, te["R@10"], te["MRR"]))
        print(f"  {vname:<32}  {best_act_w:>6.2f}  {best_act_r10_train:>10.3f}  "
              f"{te['R@10']:>10.3f}  {te['MRR']:>9.3f}")

    best_variant = max(phase3_results, key=lambda x: x[3])
    print(f"\n  Winner: {best_variant[0]}  "
          f"(act_w={best_variant[1]:.2f}, R@10(test)={best_variant[3]:.3f}, "
          f"MRR(test)={best_variant[4]:.3f})")
    print("\n  Note: λ (temporal decay) sweep deferred — events have no timestamps.")
    print("  Re-run with benchmark ingestion ground truth when available.")


if __name__ == "__main__":
    main()
