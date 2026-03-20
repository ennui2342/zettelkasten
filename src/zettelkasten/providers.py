"""LLM and embedding provider protocols + concrete implementations.

The library accepts any object satisfying LLMProvider or EmbedProvider.
Concrete implementations (AnthropicLLM, VoyageEmbed) are provided for
convenience; they require the respective SDKs to be installed.
Mock implementations (MockLLM, MockEmbed) are available for testing.
"""
from __future__ import annotations

import hashlib
from typing import Callable, Protocol, Union, runtime_checkable

import numpy as np


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class LLMProvider(Protocol):
    def complete(self, prompt: str, *, max_tokens: int, temperature: float = 0.0) -> str:
        """Send a prompt; return the text response."""
        ...


@runtime_checkable
class EmbedProvider(Protocol):
    def embed(self, texts: list[str], *, input_type: str = "document") -> list[np.ndarray]:
        """Embed a list of texts; return one float32 unit-normalised vector per text."""
        ...


# ---------------------------------------------------------------------------
# Mock implementations (for testing)
# ---------------------------------------------------------------------------


class MockLLM:
    """Deterministic LLM stub for tests.

    Pass a fixed string response, or a callable ``(prompt, **kwargs) -> str``
    for dynamic behaviour.
    """

    def __init__(self, response: Union[str, Callable]) -> None:
        self._response = response

    def complete(self, prompt: str, *, max_tokens: int, temperature: float = 0.0) -> str:
        if callable(self._response):
            return self._response(prompt, max_tokens=max_tokens, temperature=temperature)
        return self._response


class MockEmbed:
    """Deterministic embedding stub for tests.

    Produces unit-normalised float32 vectors of ``dims`` dimensions, derived
    deterministically from the text content via SHA-256 so that:
    - the same text always returns the same vector
    - different texts (almost certainly) return different vectors
    """

    def __init__(self, dims: int = 1024) -> None:
        self._dims = dims

    def embed(self, texts: list[str], *, input_type: str = "document") -> list[np.ndarray]:
        results = []
        for text in texts:
            seed = int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2**32)
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(self._dims).astype(np.float32)
            norm = np.linalg.norm(vec)
            results.append(vec / norm if norm > 0 else vec)
        return results


# ---------------------------------------------------------------------------
# Concrete: Anthropic
# ---------------------------------------------------------------------------


class AnthropicLLM:
    """LLMProvider backed by the Anthropic Messages API."""

    def __init__(self, model: str, api_key: str) -> None:
        try:
            import anthropic as _anthropic
        except ImportError as e:
            raise ImportError(
                "anthropic package required: pip install zettelkasten[anthropic]"
            ) from e
        self._client = _anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, prompt: str, *, max_tokens: int, temperature: float = 0.0) -> str:
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text


# ---------------------------------------------------------------------------
# Concrete: Voyage
# ---------------------------------------------------------------------------


class VoyageEmbed:
    """EmbedProvider backed by the Voyage AI embedding API."""

    def __init__(self, model: str, api_key: str) -> None:
        try:
            import voyageai as _voyage
        except ImportError as e:
            raise ImportError(
                "voyageai package required: pip install zettelkasten[voyage]"
            ) from e
        self._client = _voyage.Client(api_key=api_key)
        self._model = model

    def embed(self, texts: list[str], *, input_type: str = "document") -> list[np.ndarray]:
        result = self._client.embed(texts, model=self._model, input_type=input_type)
        return [np.array(v, dtype=np.float32) for v in result.embeddings]
