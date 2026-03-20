#!/usr/bin/env python3
"""MERGE vs SYNTHESISE behaviour test.

Seeds a fresh zettel with pairs of notes that cover the same underlying
concept from different disciplinary vocabulary, then ingests bridging texts
designed to pull both notes into the cluster. Reports which operation fires
for each scenario.

The core question: given two notes that genuinely cover the same topic,
does Step 1 classify MERGE (unify them) or SYNTHESISE (create a bridge)?

Usage:
  uv run python spikes/merge-test/run_test.py
  uv run python spikes/merge-test/run_test.py --scenario 1   # run one scenario
  uv run python spikes/merge-test/run_test.py --keep         # don't wipe zettel between scenarios
"""
from __future__ import annotations

import argparse
import logging
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "src"))

# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

@dataclass
class Scenario:
    name: str
    description: str
    # Each scenario has two seed notes (title, body)
    note_a_title: str
    note_a_body: str
    note_b_title: str
    note_b_body: str
    # The bridging text to ingest
    bridging_text: str
    # Expected outcome and reasoning
    expected: str  # "MERGE" | "SYNTHESISE" | "UPDATE"
    hypothesis: str


SCENARIOS: list[Scenario] = [
    # ------------------------------------------------------------------
    # Scenario 1: Same mechanism, different vocabulary (IR vs NLP)
    # Hypothesis: MERGE should fire — both notes describe embedding-based
    # similarity search, just using field-specific terminology.
    # ------------------------------------------------------------------
    Scenario(
        name="Dense Retrieval vs Semantic Search",
        description="Same retrieval mechanism named differently in IR vs NLP communities",
        note_a_title="Dense Retrieval via Bi-Encoder Similarity",
        note_a_body="""\
Dense retrieval encodes queries and documents into a shared vector space using a
bi-encoder architecture, then ranks candidates by cosine similarity or dot product.
The key property is that semantic similarity maps to geometric proximity: related
documents cluster together regardless of surface-form lexical overlap.

Widely used in open-domain question answering (DPR) and enterprise search. The
retrieval is approximate in practice, using HNSW or FAISS indices for sub-linear
search. Dense retrieval outperforms sparse methods on out-of-vocabulary queries but
requires large-scale pretraining to capture semantic structure.""",
        note_b_title="Semantic Search via Neural Embedding Spaces",
        note_b_body="""\
Semantic search encodes natural language queries and documents into embedding
vectors that capture meaning rather than surface form. Two texts are considered
similar when their vectors are close under a distance metric such as cosine
similarity. The embedding space is learned from large text corpora and generalises
across paraphrases, synonyms, and domain variants.

Applications include document retrieval, question answering, and recommendation.
Unlike keyword search, semantic search handles vocabulary mismatch: a query about
"car safety" retrieves documents mentioning "vehicle crash protection" because both
map to nearby regions of the embedding space.""",
        bridging_text="""\
Dense Retrieval and Semantic Search: One Technique, Two Names

The information retrieval (IR) community and the natural language processing (NLP)
community developed independently what turned out to be the same technique. IR
researchers called it "dense retrieval" or "bi-encoder retrieval"; NLP researchers
called it "semantic search" or "embedding-based search". Both communities were doing
the same thing: encoding texts into vectors, indexing those vectors for fast similarity
lookup, and ranking candidates by geometric proximity.

The unification became clear with DPR (Dense Passage Retrieval, Karpukhin et al. 2020),
which was simultaneously described in both communities as an embedding approach. The
BEIR benchmark (Thakur et al. 2021) evaluated "dense retrieval" and "semantic search"
systems using the same protocol, treating them as instances of the same approach.

The only substantive difference in terminology is the framing: IR researchers emphasise
the contrast with sparse retrieval (BM25), while NLP researchers emphasise the semantic
rather than syntactic nature of the similarity. The architecture, training objective, and
inference procedure are identical.

This terminological split has caused duplicated research effort: both communities
independently developed techniques for hard negative mining, training efficiency, and
in-batch negatives without citing each other's work. A unified vocabulary would have
accelerated progress.
""",
        expected="MERGE",
        hypothesis="Both notes describe the same retrieval mechanism. The bridging text "
                   "explicitly identifies them as the same technique and argues they should "
                   "be unified. Expecting MERGE; risk is SYNTHESISE if the model focuses "
                   "on the 'bridge' framing rather than the 'duplicate' framing.",
    ),

    # ------------------------------------------------------------------
    # Scenario 2: Same regularization technique, different framings
    # (ML practice vs Bayesian interpretation)
    # Hypothesis: SYNTHESISE more likely — the Bayesian framing genuinely
    # adds something not in the practical framing, even though both describe
    # dropout.
    # ------------------------------------------------------------------
    Scenario(
        name="Dropout as Regularization vs Bayesian Approximation",
        description="Same mechanism (dropout), different interpretations (practical vs Bayesian)",
        note_a_title="Dropout Regularization in Deep Neural Networks",
        note_a_body="""\
Dropout is a regularization technique that randomly sets a fraction of neuron
activations to zero during training, with probability p (typically 0.1–0.5).
At inference, all neurons are active and weights are scaled by (1-p) to maintain
expected activation magnitude.

Dropout prevents co-adaptation: neurons cannot rely on specific other neurons being
active, so each must develop independent useful features. The effect is similar to
training an ensemble of exponentially many sub-networks that share parameters.
Empirically reduces overfitting across vision and language tasks and has become
a standard component of deep learning architectures.""",
        note_b_title="Monte Carlo Dropout as Approximate Bayesian Inference",
        note_b_body="""\
Gal and Ghahramani (2016) showed that a neural network with dropout applied at
every weight layer is equivalent to an approximation to a deep Gaussian process.
Sampling with dropout active at inference time (MC dropout) provides approximate
posterior samples over model weights, enabling uncertainty quantification without
additional training cost.

MC dropout enables predictive uncertainty estimation: running N forward passes with
dropout active and measuring the variance of the outputs gives a cheap proxy for
epistemic uncertainty. This has applications in active learning, out-of-distribution
detection, and safety-critical systems where knowing "I don't know" matters as much
as point predictions.""",
        bridging_text="""\
The Two Lives of Dropout: Regularizer and Bayesian Approximation

Dropout was introduced by Hinton et al. (2012) and Srivastava et al. (2014) as a
practical regularization heuristic — a way to prevent overfitting by adding noise
during training. For two years it was understood purely as a training trick.

Gal and Ghahramani (2016) showed it was something deeper: a neural network with
dropout is performing approximate Bayesian inference. The practical regularizer and
the Bayesian approximation are the same mathematical object, just described with
different vocabularies.

This duality has practical implications. The regularization framing suggests you
should switch dropout off at inference time (which is standard practice). The Bayesian
framing suggests you should keep dropout on at inference time to sample from the
approximate posterior (MC dropout). These give different results and serve different
purposes. Knowing both framings is necessary to use dropout correctly: off for point
predictions, on for uncertainty estimation.

The two framings are not interchangeable descriptions of the same thing — they lead
to genuinely different inference procedures. The Bayesian framing adds content the
regularization framing lacks.
""",
        expected="SYNTHESISE",
        hypothesis="Both notes describe dropout, but they emphasise genuinely different aspects: "
                   "practical regularization vs Bayesian uncertainty. The bridging text explicitly "
                   "says 'the two framings are not interchangeable'. Expecting SYNTHESISE because "
                   "the connection adds content neither note captures alone.",
    ),

    # ------------------------------------------------------------------
    # Scenario 3: Same formula, same name, accumulated in two separate notes
    # (classic duplicate scenario — what MERGE is designed for)
    # Hypothesis: MERGE should fire.
    # ------------------------------------------------------------------
    Scenario(
        name="Cosine Similarity — Duplicate Accumulation",
        description="The same concept has been written up twice under slightly different titles",
        note_a_title="Cosine Similarity as Scale-Invariant Vector Distance",
        note_a_body="""\
Cosine similarity measures the angle between two vectors in a high-dimensional space,
independent of their magnitudes. Defined as the dot product divided by the product
of the norms: sim(A, B) = A·B / (|A| |B|). Ranges from -1 (opposite) to 1 (identical
direction), with 0 indicating orthogonality.

The scale invariance property is critical for text representation: two documents are
similar if they discuss the same topics in the same proportions, regardless of length.
Used extensively in TF-IDF retrieval and neural embedding comparison. When vectors are
L2-normalised before indexing, cosine similarity reduces to a plain dot product,
enabling efficient MIPS (maximum inner product search).""",
        note_b_title="Normalised Dot Product Similarity in Embedding Retrieval",
        note_b_body="""\
When comparing embedding vectors, the dot product alone conflates directional
similarity with magnitude. Dividing by the product of vector norms yields a
normalised similarity score equivalent to the cosine of the angle between vectors.
This normalised dot product (cosine similarity) is the standard metric in dense
retrieval, semantic search, and recommendation systems.

Practically: L2-normalising all embeddings at index time means retrieval can use
plain dot product (which is what FAISS and HNSW optimise for), while preserving
the angular similarity semantics. The two formulations — cosine similarity and
normalised dot product — are mathematically identical and interchangeable.""",
        bridging_text="""\
A Guide to Similarity Metrics in Embedding Systems

When building embedding-based retrieval, the choice of similarity metric matters.
The dominant metric in production systems is cosine similarity, also described as
the normalised dot product: you take the dot product of two vectors and divide by
the product of their L2 norms.

These two descriptions — "cosine similarity" and "normalised dot product" — refer
to exactly the same mathematical operation. There is no distinction. Some frameworks
expose it as cosine similarity (scikit-learn, sentence-transformers); others as a
dot product on pre-normalised vectors (FAISS, OpenAI embeddings API). The computation
is identical.

The practical implication: normalise your embeddings once at index time, then use
plain dot product at search time. This gives you cosine similarity semantics at
maximum SIMD speed. Vector databases (Pinecone, Weaviate, Qdrant) handle this
normalisation automatically when the cosine metric is selected.

Related considerations: inner product similarity (non-normalised) is used when
magnitude matters, such as in recommendation systems where higher-scoring items
should be ranked above lower-scoring items regardless of directional similarity.
""",
        expected="MERGE",
        hypothesis="Both notes describe the same formula (cosine similarity = normalised dot product) "
                   "and acknowledge the equivalence explicitly. These are genuine duplicates. "
                   "The bridging text says 'these two descriptions refer to exactly the same "
                   "mathematical operation'. Strong MERGE candidate.",
    ),

    # ------------------------------------------------------------------
    # Scenario 4: Different levels of abstraction — same phenomenon
    # (gradient vanishing described mechanistically vs architecturally)
    # Hypothesis: UPDATE is more likely — the second note extends the first
    # rather than duplicating it.
    # ------------------------------------------------------------------
    Scenario(
        name="Vanishing Gradients — Mechanism vs Architecture Response",
        description="Same problem described at different levels: signal propagation vs ResNet design",
        note_a_title="Vanishing Gradients in Deep Network Training",
        note_a_body="""\
As gradients flow backward through many layers via backpropagation, repeated
multiplication by weights and activation derivatives causes the gradient magnitude
to diminish exponentially. For sigmoid activations, derivatives are bounded by 0.25,
so a 20-layer network multiplies the gradient by at most 0.25^20 ≈ 10^-12 per
forward pass — gradients reaching early layers are numerically zero.

Consequences: early layers train slowly or not at all; deep networks cannot learn
long-range dependencies; effective depth is limited to what gradients can reach.
Solutions developed over time include: careful weight initialisation (Xavier, He),
activation functions with near-unit derivatives (ReLU, GELU), batch normalisation
to maintain activation statistics, and residual connections to short-circuit the
gradient path.""",
        note_b_title="Residual Connections as a Gradient Highway",
        note_b_body="""\
Residual (skip) connections, introduced by He et al. (2016) in ResNet, add the
input of a block directly to its output: y = F(x) + x. This creates a gradient
highway: during backpropagation, the gradient can flow directly through the skip
connection without passing through the learned transformation F(x).

The key insight is that the skip connection provides a path with gradient magnitude
exactly 1.0, regardless of how many layers are stacked. This prevents vanishing
gradients by giving the signal an unobstructed route. Residual networks train to
hundreds of layers (ResNet-1000+) where equivalent plain networks fail completely.

Beyond depth: residual connections also enable feature reuse. Early features remain
accessible to later layers via the accumulated residual stream, which has been
interpreted as an ensemble of shallower models (Veit et al. 2016).""",
        bridging_text="""\
Why Deep Networks Failed Before Residual Connections

Deep networks — 20+ layers — consistently underperformed shallower networks before
2015. The cause was vanishing gradients: backpropagation through many layers reduced
gradient magnitudes to near-zero before reaching early layers, which consequently
received no useful training signal.

He et al. (2016) solved this with residual connections: adding the input x directly
to the block's output F(x) + x. The skip connection provides a gradient path with
magnitude 1.0 independent of network depth, preventing the exponential attenuation.

These two phenomena — vanishing gradients and residual connections — are directly
linked as problem and solution. Understanding residual connections requires
understanding vanishing gradients; understanding vanishing gradients leads directly
to residual connections as the architectural response. They are not the same topic
but they are inseparable: a note on either is incomplete without reference to the
other.
""",
        expected="SYNTHESISE",
        hypothesis="The two notes cover related but genuinely distinct topics: the problem "
                   "(vanishing gradients) and the solution (residual connections). The bridging "
                   "text explicitly says they are 'not the same topic'. Expecting SYNTHESISE "
                   "or UPDATE on the vanishing gradient note. MERGE would be incorrect here.",
    ),

    # ------------------------------------------------------------------
    # Scenario 5: Stub + fuller note on same concept
    # (a stub was created early; a fuller note appeared later)
    # Hypothesis: UPDATE should fire (promote stub), not MERGE.
    # ------------------------------------------------------------------
    Scenario(
        name="Stub + Full Note on Same Concept",
        description="A stub was created when the topic first appeared; a fuller note was created later",
        note_a_title="Mixture of Experts in Language Models",
        note_a_body="""\
Mixture of Experts (MoE) is a model architecture where different inputs are routed
to different specialised sub-networks ("experts"). Only a subset of experts are
active for each token, enabling much larger total model capacity at similar compute
cost.

Related terms: sparse MoE, conditional computation, expert routing, load balancing.""",
        note_b_title="Sparse Expert Routing and Load Balancing in MoE Transformers",
        note_b_body="""\
In sparse Mixture of Experts (MoE) transformers, a learned router assigns each token
to the top-k of N expert feed-forward networks. Typical configurations use 8–64 experts
with k=2 active per token, enabling 4–8× parameter scaling with equivalent FLOPs.

Load balancing is a key training challenge: without auxiliary losses, the router
collapses to routing everything to a few popular experts, wasting capacity. The standard
fix is an auxiliary load-balancing loss that encourages uniform expert utilisation.
Switch Transformer (Fedus et al. 2021) and GShard (Lepikhin et al. 2021) demonstrated
billion-parameter MoE models; Mixtral-8x7B showed competitive performance at MoE
architecture for open-weight models.

The capacity factor controls the maximum tokens any expert can handle per batch; tokens
routed to a full expert are dropped, creating a tradeoff between load balance and
token coverage.""",
        bridging_text="""\
Mixture of Experts: Architecture, Training, and Scaling

The Mixture of Experts (MoE) architecture has emerged as the dominant approach for
scaling language models beyond the compute budget that dense transformers require.
The key idea: replace each feed-forward network in a transformer with N specialised
expert FFNs, and use a learned router to send each token to the top-k most relevant
experts. Only 2 of 64 experts activate per token, so model capacity scales with N
while FLOPs remain constant.

The routing mechanism is simple: the router computes a softmax over N experts and
selects the top-k. Training the router stably requires auxiliary losses. Without
explicit load-balancing pressure, the router quickly concentrates on 2–3 experts and
ignores the rest. The standard load-balancing loss adds a penalty proportional to the
variance in expert utilisation across the batch.

Expert specialisation emerges naturally: in language MoE models, experts tend to
specialise by token type, syntactic role, or semantic domain. This specialisation is
beneficial but partial — the same expert will handle diverse tokens from the same
broad category.

Open questions include: how many experts is optimal, what is the right capacity factor,
and whether dynamic routing (tokens choosing experts vs experts choosing tokens) matters
in practice.
""",
        expected="UPDATE",
        hypothesis="Note A is a stub; note B is a fuller treatment of the same concept. "
                   "The bridging text adds substantial new content about routing and load "
                   "balancing. Expecting UPDATE on the stub note (which should also trigger "
                   "promotion to permanent). MERGE would also be reasonable but UPDATE is more "
                   "likely since the stub is clearly underdeveloped relative to note B.",
    ),
]


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    fmt = "%(asctime)s %(levelname)-8s %(name)-20s %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt, datefmt="%H:%M:%S")
    # Suppress verbose library logs
    logging.getLogger("zettelkasten").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return logging.getLogger("merge-test")


def run_scenario(
    scenario: Scenario,
    scenario_idx: int,
    work_dir: Path,
    llm,
    fast_llm,
    embed,
    log: logging.Logger,
) -> dict:
    """Run one scenario. Returns a result dict."""
    from zettelkasten.store import ZettelkastenStore
    from zettelkasten.note import ZettelNote

    store_dir = work_dir / f"zettel_s{scenario_idx}"
    index_path = work_dir / f"index_s{scenario_idx}.db"

    # Clean slate
    if store_dir.exists():
        shutil.rmtree(store_dir)
    if index_path.exists():
        index_path.unlink()

    store = ZettelkastenStore(notes_dir=store_dir, index_path=index_path)

    now = datetime.now(tz=timezone.utc)

    # Seed note A
    note_a = ZettelNote(
        id="z20260101-001",
        title=scenario.note_a_title,
        body=scenario.note_a_body,
        type="permanent",
        confidence=0.7,
        salience=0.5,
        stable=False,
        created=now, updated=now, last_accessed=now,
    )
    store.write(note_a)
    vecs_a = embed.embed([note_a.body])
    store._index.upsert_embedding(note_a.id, vecs_a[0])

    # Seed note B — mark A as stub for scenario 5
    note_b_type = "permanent"
    if scenario_idx == 5:
        # Overwrite note A as stub to test stub+full-note scenario
        import dataclasses
        note_a_stub = dataclasses.replace(note_a, type="stub", confidence=0.4)
        store.write(note_a_stub)
        store._index.upsert_embedding(note_a.id, vecs_a[0])

    note_b = ZettelNote(
        id="z20260101-002",
        title=scenario.note_b_title,
        body=scenario.note_b_body,
        type=note_b_type,
        confidence=0.7,
        salience=0.5,
        stable=False,
        created=now, updated=now, last_accessed=now,
    )
    store.write(note_b)
    vecs_b = embed.embed([note_b.body])
    store._index.upsert_embedding(note_b.id, vecs_b[0])

    log.info("Seeded 2 notes — A: %r  B: %r", note_a.id, note_b.id)

    # Ingest bridging text
    results = store.ingest_text(
        scenario.bridging_text,
        llm=llm,
        embed=embed,
        fast_llm=fast_llm,
        source=f"merge-test/scenario-{scenario_idx}",
    )

    ops = [(r.operation, r.confidence, r.note_title or r.reasoning[:60]) for r in results]
    return {
        "scenario": scenario_idx,
        "name": scenario.name,
        "expected": scenario.expected,
        "hypothesis": scenario.hypothesis,
        "operations": ops,
        "match": any(r.operation == scenario.expected for r in results),
    }


def print_report(results: list[dict]) -> None:
    print()
    print("=" * 70)
    print("MERGE TEST RESULTS")
    print("=" * 70)
    for r in results:
        match_str = "MATCH" if r["match"] else "MISS "
        print(f"\n[{match_str}] Scenario {r['scenario']}: {r['name']}")
        print(f"       Expected: {r['expected']}")
        print(f"       Got:      {r['operations']}")
        print(f"       Hypothesis: {r['hypothesis']}")
    print()
    matches = sum(1 for r in results if r["match"])
    print(f"Score: {matches}/{len(results)} scenarios matched expected operation")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="MERGE vs SYNTHESISE behaviour test")
    parser.add_argument(
        "--scenario", type=int, default=None,
        help="Run only this scenario (1-5). Default: all.",
    )
    args = parser.parse_args()

    log = setup_logging()

    # Load providers
    log.info("Loading providers...")
    import sys
    sys.path.insert(0, str(ROOT))
    from zettelkasten.config import load_config, build_llm, build_fast_llm, build_embed
    cfg = load_config(ROOT / "zettelkasten.toml")
    llm = build_llm(cfg)
    fast_llm = build_fast_llm(cfg)
    embed = build_embed(cfg)

    work_dir = HERE / "work"
    work_dir.mkdir(exist_ok=True)

    scenarios = SCENARIOS
    if args.scenario is not None:
        scenarios = [s for i, s in enumerate(SCENARIOS, 1) if i == args.scenario]
        if not scenarios:
            print(f"No scenario {args.scenario} (valid: 1-{len(SCENARIOS)})")
            sys.exit(1)

    all_results = []
    for i, scenario in enumerate(scenarios, 1):
        idx = i if args.scenario is None else args.scenario
        log.info("--- Scenario %d: %s ---", idx, scenario.name)
        try:
            result = run_scenario(scenario, idx, work_dir, llm, fast_llm, embed, log)
            all_results.append(result)
            match = "MATCH" if result["match"] else "MISS"
            log.info(
                "Scenario %d [%s]: expected=%s got=%s",
                idx, match, result["expected"],
                [(op, f"{conf:.2f}") for op, conf, _ in result["operations"]],
            )
        except Exception as e:
            log.error("Scenario %d FAILED: %s", idx, e, exc_info=True)
            all_results.append({
                "scenario": idx,
                "name": scenario.name,
                "expected": scenario.expected,
                "hypothesis": scenario.hypothesis,
                "operations": [("ERROR", 0.0, str(e)[:60])],
                "match": False,
            })

    print_report(all_results)


if __name__ == "__main__":
    main()
