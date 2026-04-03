"""Retrieval signals for the workbench.

Each signal is a class with:
  name: str          — display name
  needs_loo: bool    — True if the signal changes per LOO fold (e.g. activation)
  setup(corpus, ids, embeddings_cache, ground_truth, caches_dir) → None
  scores(qid, qidx, ids, loo_events=None) → np.ndarray  (length = len(ids))

Score vectors should NOT have the query note zeroed out — the harness handles that.
Score scale doesn't matter — the harness normalises before blending.
"""
from .body import BodyEmbedding
from .body_query import BodyEmbeddingQuery
from .bm25_mugi import BM25MuGI
from .bm25_mugi5 import BM25MuGI5
from .bm25_mugi_stem import BM25MuGIStem
from .bm25_mugi_tfidf import BM25MuGITFIDF
from .bm25_keyword import BM25Keyword
from .activation import Activation, ActivationNoTransitive, ActivationK20
from .activation_prompt import ActivationB, ActivationC
from .activation_scalar import ActivationScalarGold, ActivationScalarK20, ActivationScalarB, ActivationScalarC
from .step_back import StepBack
from .hyde import HyDE
from .hyde_multi import HyDEMulti

ALL_SIGNALS = [
    BodyEmbedding, BodyEmbeddingQuery,
    BM25MuGI, BM25MuGI5, BM25MuGIStem, BM25MuGITFIDF, BM25Keyword,
    Activation, ActivationNoTransitive, ActivationK20,
    ActivationB, ActivationC,
    StepBack, HyDE, HyDEMulti,
]
