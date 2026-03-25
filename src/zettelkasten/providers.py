"""LLM and embedding provider protocols + concrete implementations.

The library accepts any object satisfying LLMProvider or EmbedProvider.
Concrete implementations (AnthropicLLM, VoyageEmbed) are provided for
convenience; they require the respective SDKs to be installed.
Mock implementations (MockLLM, MockEmbed) are available for testing.

Tool-using variants (ToolLLMProvider, AnthropicToolLLM, MockToolLLM) support
the agentic navigation loop used by ZettelkastenStore.query().
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, Union, runtime_checkable

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
# Tool-use protocol (for ZettelkastenStore.query navigation)
# ---------------------------------------------------------------------------


@dataclass
class ToolSpec:
    """Specification for a single tool the LLM may call."""

    name: str
    description: str
    parameters: dict  # JSON Schema object


@dataclass
class ToolCall:
    """A single tool invocation returned by the LLM."""

    id: str
    name: str
    input: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ToolLLMProvider(Protocol):
    """Protocol for LLMs that support tool use (function calling).

    ``complete_tools`` performs a single turn of a tool-use conversation.
    Returns ``(answer, [])`` when the LLM has finished and produced a final
    text response, or ``(intermediate_text_or_None, tool_calls)`` when it
    wants to invoke one or more tools before continuing.
    """

    def complete_tools(
        self,
        messages: list[dict],
        tools: list[ToolSpec],
        system: str = "",
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> tuple[str | None, list[ToolCall]]:
        ...


class MockToolLLM:
    """Deterministic tool-use stub for tests.

    Replays a scripted sequence of ``(text, tool_calls)`` tuples in order.
    Raises ``RuntimeError`` if more turns are requested than responses provided.
    """

    def __init__(self, responses: list[tuple[str | None, list[ToolCall]]]) -> None:
        self._responses = list(responses)
        self._idx = 0

    def complete_tools(
        self,
        messages: list[dict],
        tools: list[ToolSpec],
        system: str = "",
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> tuple[str | None, list[ToolCall]]:
        if self._idx >= len(self._responses):
            raise RuntimeError(
                f"MockToolLLM exhausted all {len(self._responses)} scripted responses"
            )
        resp = self._responses[self._idx]
        self._idx += 1
        return resp


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


class AnthropicToolLLM:
    """ToolLLMProvider backed by the Anthropic Messages API with tool use."""

    def __init__(self, model: str, api_key: str) -> None:
        try:
            import anthropic as _anthropic
        except ImportError as e:
            raise ImportError(
                "anthropic package required: pip install zettelkasten[anthropic]"
            ) from e
        self._client = _anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete_tools(
        self,
        messages: list[dict],
        tools: list[ToolSpec],
        system: str = "",
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> tuple[str | None, list[ToolCall]]:
        tool_defs = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]
        kwargs: dict = dict(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tool_defs,
            messages=messages,
        )
        if system:
            kwargs["system"] = system
        resp = self._client.messages.create(**kwargs)

        text: str | None = None
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                text = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, input=dict(block.input))
                )
        return text, tool_calls


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
