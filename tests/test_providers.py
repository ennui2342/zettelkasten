"""Tests for LLMProvider / EmbedProvider protocols and mock implementations."""
import numpy as np
import pytest

from zettelkasten.providers import EmbedProvider, LLMProvider, MockEmbed, MockLLM


# ---------------------------------------------------------------------------
# Protocol compliance — any object with the right methods qualifies
# ---------------------------------------------------------------------------


def test_mock_llm_satisfies_protocol():
    llm: LLMProvider = MockLLM("hello")
    result = llm.complete("say hello", max_tokens=10)
    assert result == "hello"


def test_mock_llm_temperature_accepted():
    llm = MockLLM("hi")
    result = llm.complete("prompt", max_tokens=50, temperature=0.3)
    assert result == "hi"


def test_mock_llm_callable_response():
    """Response can be a callable for dynamic test responses."""
    responses = ["first", "second", "third"]
    idx = iter(responses)
    llm = MockLLM(lambda prompt, **kw: next(idx))
    assert llm.complete("a", max_tokens=10) == "first"
    assert llm.complete("b", max_tokens=10) == "second"


def test_mock_embed_satisfies_protocol():
    embed: EmbedProvider = MockEmbed(dims=4)
    vecs = embed.embed(["hello", "world"])
    assert len(vecs) == 2
    assert vecs[0].shape == (4,)
    assert vecs[0].dtype == np.float32


def test_mock_embed_input_type_accepted():
    embed = MockEmbed(dims=8)
    vecs = embed.embed(["text"], input_type="query")
    assert len(vecs) == 1
    assert vecs[0].shape == (8,)


def test_mock_embed_deterministic_for_same_text():
    embed = MockEmbed(dims=16)
    v1 = embed.embed(["hello"])[0]
    v2 = embed.embed(["hello"])[0]
    assert np.allclose(v1, v2)


def test_mock_embed_different_for_different_text():
    embed = MockEmbed(dims=16)
    v1 = embed.embed(["hello"])[0]
    v2 = embed.embed(["world"])[0]
    # Not guaranteed equal
    assert not np.allclose(v1, v2)


def test_mock_embed_unit_normalised():
    embed = MockEmbed(dims=32)
    v = embed.embed(["any text"])[0]
    assert abs(np.linalg.norm(v) - 1.0) < 1e-5
