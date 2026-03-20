#!/usr/bin/env python3
"""Step 1 prompt iteration spike — MERGE vs SYNTHESISE boundary.

Runs all 5 scenarios against a named prompt variant using cached Form outputs
as the draft (not the raw bridging text). Run cache_form_outputs.py first.

Scenarios:
  s1  Dense Retrieval vs Semantic Search    (expected: MERGE)
  s3  Cosine Similarity duplicate           (expected: MERGE)
  s2  Dropout Regularization vs Bayesian    (expected: SYNTHESISE — anchor)
  s4  Vanishing Gradients vs ResNets        (expected: SYNTHESISE — anchor)
  s5  Stub + Full Note on MoE               (expected: UPDATE — anchor)

Usage:
  uv run --env-file .env python spikes/merge-test/cache_form_outputs.py
  uv run --env-file .env python spikes/merge-test/iterate_prompt.py --variant 0
  uv run --env-file .env python spikes/merge-test/iterate_prompt.py --variant 2
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "src"))

# ---------------------------------------------------------------------------
# Scenarios (subset of merge-test scenarios)
# ---------------------------------------------------------------------------

@dataclass
class Scenario:
    key: str
    name: str
    note_a_title: str
    note_a_body: str
    note_b_title: str
    note_b_body: str
    bridging_text: str
    expected: str


SCENARIOS = [
    Scenario(
        key="s1",
        name="Dense Retrieval vs Semantic Search",
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
    ),

    Scenario(
        key="s3",
        name="Cosine Similarity — Duplicate Accumulation",
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
""",
        expected="MERGE",
    ),

    Scenario(
        key="s4",
        name="Vanishing Gradients vs Residual Connections (SYNTHESISE anchor)",
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
    ),

    Scenario(
        key="s5",
        name="Stub + Full Note on Same Concept (UPDATE anchor)",
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
    ),

    Scenario(
        key="s2",
        name="Dropout: Regularization vs Bayesian (SYNTHESISE anchor)",
        note_a_title="Dropout Regularization in Deep Neural Networks",
        note_a_body="""\
Dropout is a regularization technique that randomly sets a fraction of neuron
activations to zero during training, with probability p (typically 0.1–0.5).
At inference, all neurons are active and weights are scaled by (1-p) to maintain
expected activation magnitude.

Dropout prevents co-adaptation: neurons cannot rely on specific other neurons being
active, so each must develop independent useful features. The effect is similar to
training an ensemble of exponentially many sub-networks that share parameters.
Empirically reduces overfitting across vision and language tasks.""",
        note_b_title="Monte Carlo Dropout as Approximate Bayesian Inference",
        note_b_body="""\
Gal and Ghahramani (2016) showed that a neural network with dropout applied at
every weight layer is equivalent to an approximation to a deep Gaussian process.
Sampling with dropout active at inference time (MC dropout) provides approximate
posterior samples over model weights, enabling uncertainty quantification without
additional training cost.

MC dropout enables predictive uncertainty estimation: running N forward passes with
dropout active and measuring the variance of the outputs gives a cheap proxy for
epistemic uncertainty. Applications include active learning, out-of-distribution
detection, and safety-critical systems.""",
        bridging_text="""\
The Two Lives of Dropout: Regularizer and Bayesian Approximation

Dropout was introduced as a practical regularization heuristic. Gal and Ghahramani
(2016) showed it was something deeper: a neural network with dropout is performing
approximate Bayesian inference. The practical regularizer and the Bayesian
approximation are the same mathematical object, described with different vocabularies.

This duality has practical implications. The regularization framing says switch dropout
off at inference time. The Bayesian framing says keep it on to sample from the
approximate posterior (MC dropout). These give different results and serve different
purposes: off for point predictions, on for uncertainty estimation.

The two framings are not interchangeable — they lead to genuinely different inference
procedures. The Bayesian framing adds content the regularization framing lacks.
""",
        expected="SYNTHESISE",
    ),
]

# ---------------------------------------------------------------------------
# Prompt variants
# Variant 0 = current production prompt (baseline).
# Add new variants below after each iteration.
# ---------------------------------------------------------------------------

_V0 = """\
You maintain a knowledge base of topic notes. You have a draft note and a \
cluster of related existing notes.

Draft note:
{draft}

Existing notes in cluster:
{cluster}

Decide what action to take. Choose exactly one:

- UPDATE: the draft adds to an existing note. Rewrite that note to synthesise \
old and new — do not append.
- CREATE: the draft covers a topic not in the cluster. Create a new note.
- SPLIT: an existing note conflates two distinct topics that the draft \
clarifies should be separate.
- MERGE: two existing notes in the cluster cover the same topic. The draft \
confirms they should be one.
- SYNTHESISE: the draft reveals a connection between two existing notes that \
neither captures. Create a new structure note articulating the bridging \
principle.
- NOTHING: the draft is already fully covered by the existing cluster. No \
action needed.
- STUB: the cluster is sparse or empty — this is a new topic without an \
established neighbourhood. Create a provisional note at low confidence.

If the cluster is empty, STUB is the appropriate default unless the draft is \
clearly a subtopic of notes in the broader knowledge base.

In target_note_ids, list the existing notes that this draft directly \
INTERACTS with — notes whose content this draft meaningfully extends, \
challenges, or bridges. For UPDATE/MERGE/SPLIT the primary operation \
target must be listed first; for CREATE/STUB include the most relevant \
neighbours; for SYNTHESISE include the notes being bridged.

Output JSON only. Schema:
{{
  "operation": "<one of the seven>",
  "target_note_ids": ["<id>", ...],
  "reasoning": "<one or two sentences>",
  "confidence": <0.0 to 1.0>
}}"""

_V1 = """\
You maintain a knowledge base of topic notes. You have a draft note and a \
cluster of related existing notes.

Draft note:
{draft}

Existing notes in cluster:
{cluster}

Decide what action to take. Choose exactly one:

- UPDATE: the draft adds to an existing note. Rewrite that note to synthesise \
old and new — do not append.
- CREATE: the draft covers a topic not in the cluster. Create a new note.
- SPLIT: an existing note conflates two distinct topics that the draft \
clarifies should be separate.
- MERGE: two existing notes in the cluster are redundant — they describe the \
same concept using different vocabulary or framing, and a reader who understood \
both would gain nothing from having them separate. The draft confirms they \
should be collapsed into one. Choose MERGE over SYNTHESISE when a bridge note \
would add no insight that isn't already implicit in either source note.
- SYNTHESISE: the draft reveals a genuine connection between two existing notes \
that produces new insight neither note captures on its own. The bridge note \
must earn its existence — it should say something that cannot be derived from \
reading either source note alone.
- NOTHING: the draft is already fully covered by the existing cluster. No \
action needed.
- STUB: the cluster is sparse or empty — this is a new topic without an \
established neighbourhood. Create a provisional note at low confidence.

If the cluster is empty, STUB is the appropriate default unless the draft is \
clearly a subtopic of notes in the broader knowledge base.

In target_note_ids, list the existing notes that this draft directly \
INTERACTS with — notes whose content this draft meaningfully extends, \
challenges, or bridges. For UPDATE/MERGE/SPLIT the primary operation \
target must be listed first; for CREATE/STUB include the most relevant \
neighbours; for SYNTHESISE include the notes being bridged.

Output JSON only. Schema:
{{
  "operation": "<one of the seven>",
  "target_note_ids": ["<id>", ...],
  "reasoning": "<one or two sentences>",
  "confidence": <0.0 to 1.0>
}}"""

_V2 = """\
You maintain a knowledge base of topic notes. You have a draft note and a \
cluster of related existing notes.

Draft note:
{draft}

Existing notes in cluster:
{cluster}

Decide what action to take. Choose exactly one:

- UPDATE: the draft adds to an existing note. Rewrite that note to synthesise \
old and new — do not append.
- CREATE: the draft covers a topic not in the cluster. Create a new note.
- SPLIT: an existing note conflates two distinct topics that the draft \
clarifies should be separate.
- MERGE: two existing notes are duplicates — they describe the same concept, \
just in different vocabulary or from different disciplines. Collapsing them \
loses nothing. Ask yourself: if you translated both notes into neutral language, \
would they say the same thing? If yes, MERGE. The draft confirms the duplication.
- SYNTHESISE: two existing notes describe genuinely distinct concepts that turn \
out to be related. The connection produces insight neither note contains — the \
bridge note adds something new. If the bridge note would only restate that two \
things are the same, choose MERGE instead.
- NOTHING: the draft is already fully covered by the existing cluster. No \
action needed.
- STUB: the cluster is sparse or empty — this is a new topic without an \
established neighbourhood. Create a provisional note at low confidence.

If the cluster is empty, STUB is the appropriate default unless the draft is \
clearly a subtopic of notes in the broader knowledge base.

In target_note_ids, list the existing notes that this draft directly \
INTERACTS with — notes whose content this draft meaningfully extends, \
challenges, or bridges. For UPDATE/MERGE/SPLIT the primary operation \
target must be listed first; for CREATE/STUB include the most relevant \
neighbours; for SYNTHESISE include the notes being bridged.

Output JSON only. Schema:
{{
  "operation": "<one of the seven>",
  "target_note_ids": ["<id>", ...],
  "reasoning": "<one or two sentences>",
  "confidence": <0.0 to 1.0>
}}"""

_V3 = """\
You maintain a knowledge base of topic notes. You have a draft note and a \
cluster of related existing notes.

Draft note:
{draft}

Existing notes in cluster:
{cluster}

Decide what action to take. Choose exactly one:

- UPDATE: the draft adds to an existing note. Rewrite that note to synthesise \
old and new — do not append.
- CREATE: the draft covers a topic not in the cluster. Create a new note.
- SPLIT: an existing note conflates two distinct topics that the draft \
clarifies should be separate.
- MERGE: two existing notes are duplicates with different names. Use this test: \
could you replace both notes with a single note that loses no knowledge? If yes, \
MERGE. Typical triggers: same mechanism named differently across disciplines, \
same formula described from different angles, same technique with different \
historical origins that converged. The draft confirms the duplication.
- SYNTHESISE: two existing notes cover distinct concepts, and the draft reveals \
a non-obvious relationship between them that produces new knowledge. The bridge \
note must contain an insight absent from both sources. Do not use SYNTHESISE \
merely because two things are related — only when the relationship itself is \
the knowledge. If the draft's main claim is "X and Y are the same thing", \
choose MERGE, not SYNTHESISE.
- NOTHING: the draft is already fully covered by the existing cluster. No \
action needed.
- STUB: the cluster is sparse or empty — this is a new topic without an \
established neighbourhood. Create a provisional note at low confidence.

If the cluster is empty, STUB is the appropriate default unless the draft is \
clearly a subtopic of notes in the broader knowledge base.

In target_note_ids, list the existing notes that this draft directly \
INTERACTS with — notes whose content this draft meaningfully extends, \
challenges, or bridges. For UPDATE/MERGE/SPLIT the primary operation \
target must be listed first; for CREATE/STUB include the most relevant \
neighbours; for SYNTHESISE include the notes being bridged.

Output JSON only. Schema:
{{
  "operation": "<one of the seven>",
  "target_note_ids": ["<id>", ...],
  "reasoning": "<one or two sentences>",
  "confidence": <0.0 to 1.0>
}}"""

_V4 = """\
You maintain a knowledge base of topic notes. You have a draft note and a \
cluster of related existing notes.

Draft note:
{draft}

Existing notes in cluster:
{cluster}

Decide what action to take. Choose exactly one:

- UPDATE: the draft adds to an existing note. Rewrite that note to synthesise \
old and new — do not append.
- CREATE: the draft covers a topic not in the cluster. Create a new note.
- SPLIT: an existing note conflates two distinct topics that the draft \
clarifies should be separate.
- MERGE: two existing notes are duplicates under different names. Apply this \
decision rule: if a single unified note would contain everything both notes \
contain and nothing would be lost, choose MERGE. This typically occurs when \
the same technique, formula, or mechanism has been independently named by \
two communities (IR vs NLP, statistics vs ML, physics vs CS). The draft \
confirms they are the same thing.
- SYNTHESISE: two existing notes cover genuinely different concepts, and the \
draft reveals a structural relationship between them that is itself knowledge. \
The bridge note must contain an insight that cannot be read off from either \
source note alone. Applying SYNTHESISE to duplicates is an error — it produces \
a bridge note that says only "A and B are the same thing", which adds nothing. \
When in doubt between MERGE and SYNTHESISE: if the draft says the two notes \
describe the same thing, choose MERGE; if the draft says the two notes describe \
different things that interact, choose SYNTHESISE.
- NOTHING: the draft is already fully covered by the existing cluster. No \
action needed.
- STUB: the cluster is sparse or empty — this is a new topic without an \
established neighbourhood. Create a provisional note at low confidence.

If the cluster is empty, STUB is the appropriate default unless the draft is \
clearly a subtopic of notes in the broader knowledge base.

In target_note_ids, list the existing notes that this draft directly \
INTERACTS with — notes whose content this draft meaningfully extends, \
challenges, or bridges. For UPDATE/MERGE/SPLIT the primary operation \
target must be listed first; for CREATE/STUB include the most relevant \
neighbours; for SYNTHESISE include the notes being bridged.

Output JSON only. Schema:
{{
  "operation": "<one of the seven>",
  "target_note_ids": ["<id>", ...],
  "reasoning": "<one or two sentences>",
  "confidence": <0.0 to 1.0>
}}"""

PROMPT_VARIANTS: dict[int, str] = {
    0: _V0,
    1: _V1,
    2: _V2,
    3: _V3,
    4: _V4,
}

# ---------------------------------------------------------------------------
# Step 1 runner (inline — no store needed, pure LLM call)
# ---------------------------------------------------------------------------

def _parse_decision(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"operation": "PARSE_ERROR", "target_note_ids": [], "reasoning": raw[:200], "confidence": 0.0}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", match.group())
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"operation": "PARSE_ERROR", "target_note_ids": [], "reasoning": raw[:200], "confidence": 0.0}


def load_form_drafts(scenario: Scenario) -> list[dict]:
    """Load cached Form output for this scenario. Falls back with a warning if missing."""
    cache_path = HERE / "form_cache" / f"{scenario.key}.json"
    if not cache_path.exists():
        raise FileNotFoundError(
            f"No Form cache for {scenario.key!r}. "
            f"Run: uv run --env-file .env python spikes/merge-test/cache_form_outputs.py"
        )
    data = json.loads(cache_path.read_text())
    return data["drafts"]  # list of {"title": str, "body": str}


def run_scenario(scenario: Scenario, prompt_template: str, llm) -> dict:
    """Run step 1 classification using cached Form output as the draft.

    When Form produced multiple drafts, runs step 1 for each and returns
    the result whose operation matches expected (or the first if none match).
    """
    note_a_text = f"id: z20260101-001\n## {scenario.note_a_title}\n\n{scenario.note_a_body}"
    note_b_text = f"id: z20260101-002\n## {scenario.note_b_title}\n\n{scenario.note_b_body}"
    cluster_text = f"{note_a_text}\n\n---\n\n{note_b_text}"

    drafts = load_form_drafts(scenario)

    all_decisions = []
    for draft in drafts:
        draft_text = f"## {draft['title']}\n\n{draft['body']}"
        prompt = prompt_template.format(draft=draft_text, cluster=cluster_text)
        raw = llm.complete(prompt, max_tokens=512, temperature=0.0)
        decision = _parse_decision(raw)
        all_decisions.append((draft["title"], decision))

    # If any draft produced the expected operation, prefer that result
    best_title, best = all_decisions[0]
    for title, d in all_decisions:
        if d.get("operation") == scenario.expected:
            best_title, best = title, d
            break

    multi_note = f" [Form→{len(drafts)} drafts; used: {best_title!r}]" if len(drafts) > 1 else ""

    return {
        "key": scenario.key,
        "name": scenario.name,
        "expected": scenario.expected,
        "operation": best.get("operation", "?"),
        "confidence": best.get("confidence", 0.0),
        "reasoning": best.get("reasoning", ""),
        "match": best.get("operation") == scenario.expected,
        "note": multi_note,
        "all_decisions": [(t, d.get("operation"), d.get("confidence", 0.0))
                          for t, d in all_decisions],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", type=int, required=True,
                        help="Prompt variant index (0=baseline)")
    args = parser.parse_args()

    if args.variant not in PROMPT_VARIANTS:
        print(f"Unknown variant {args.variant}. Available: {sorted(PROMPT_VARIANTS)}")
        sys.exit(1)

    from zettelkasten.config import load_config, build_fast_llm
    cfg = load_config(ROOT / "zettelkasten.toml")
    llm = build_fast_llm(cfg)  # step 1 uses fast LLM

    prompt = PROMPT_VARIANTS[args.variant]

    print(f"\n{'='*65}")
    print(f"PROMPT ITERATION — Variant {args.variant}")
    print(f"{'='*65}")

    results = []
    for scenario in SCENARIOS:
        result = run_scenario(scenario, prompt, llm)
        results.append(result)

        mark = "✓" if result["match"] else "✗"
        print(f"\n[{mark}] {result['key'].upper()} — {result['name']}{result.get('note', '')}")
        print(f"    Expected:  {result['expected']}")
        print(f"    Got:       {result['operation']}  (conf={result['confidence']:.2f})")
        print(f"    Reasoning: {result['reasoning']}")
        if len(result.get("all_decisions", [])) > 1:
            for t, op, conf in result["all_decisions"]:
                print(f"    Draft {t!r}: {op} ({conf:.2f})")

    merge_expected = [r for r in results if r["expected"] == "MERGE"]
    synth_expected = [r for r in results if r["expected"] == "SYNTHESISE"]
    other_expected = [r for r in results if r["expected"] not in ("MERGE", "SYNTHESISE")]
    matches = sum(1 for r in results if r["match"])
    merge_hits = sum(1 for r in merge_expected if r["match"])
    synth_safe = sum(1 for r in synth_expected if r["match"])
    other_safe = sum(1 for r in other_expected if r["match"])

    print(f"\n{'─'*65}")
    print(f"Score: {matches}/{len(results)}  |  "
          f"MERGE: {merge_hits}/{len(merge_expected)}  |  "
          f"SYNTHESISE: {synth_safe}/{len(synth_expected)}  |  "
          f"other: {other_safe}/{len(other_expected)}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
