"""Tests for the LLM providers (OpenAI-compatible + Hugging Face).

These tests never touch a real model: the inference client and the HTTP
transport are replaced with fakes so the suite runs in any environment.
"""

import json
from types import SimpleNamespace

import httpx
import pytest
from app.services.llm.errors import LLMUnavailableError, StructuredOutputError
from app.services.llm.hf_provider import HFLLMProvider
from app.services.llm.openai_provider import OpenAICompatLLMProvider
from app.services.llm.provider import create_provider
from pydantic import BaseModel


class _FakeAnswer(BaseModel):
    text: str
    count: int


async def _chat_response(provider: OpenAICompatLLMProvider, content: str) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": content}}]},
        )

    provider._client = httpx.AsyncClient(  # type: ignore[assignment]
        transport=httpx.MockTransport(handler)
    )


# ---- OpenAI-compatible provider (Groq by default) ----


async def test_openai_generate_returns_text() -> None:
    provider = OpenAICompatLLMProvider(api_key="dummy")
    await _chat_response(provider, "  hello groq  ")
    result = await provider.generate(system="sys", user="usr")
    assert result == "hello groq"


async def test_openai_generate_strips_thinking_blocks() -> None:
    provider = OpenAICompatLLMProvider(api_key="dummy")
    raw = (
        "\n<thinking>\nHere's a thinking process for the task:\n"
        "1. Consider the question\n2. Draft plan\n</thinking>\n\n"
        "The answer to the question is yes."
    )
    await _chat_response(provider, raw)
    result = await provider.generate(system="sys", user="usr")
    assert "<thinking>" not in result
    assert "The answer to the question is yes." in result


async def test_openai_generate_structured_strips_thinking_before_parse() -> None:
    provider = OpenAICompatLLMProvider(api_key="dummy")
    raw = "<thinking>reasoning here</thinking>\n" + json.dumps(
        {"text": "ok", "count": 2}
    )
    await _chat_response(provider, raw)
    result = await provider.generate_structured(
        schema=_FakeAnswer,
        system="sys",
        user="usr",
    )
    assert result.text == "ok"
    assert result.count == 2


async def test_openai_generate_requires_key() -> None:
    provider = OpenAICompatLLMProvider(api_key="")
    with pytest.raises(LLMUnavailableError):
        await provider.generate(system="sys", user="usr")
    with pytest.raises(LLMUnavailableError):
        await provider.check_connection()


async def test_openai_generate_structured_parses_json() -> None:
    provider = OpenAICompatLLMProvider(api_key="dummy")
    await _chat_response(provider, json.dumps({"text": "ok", "count": 2}))
    result = await provider.generate_structured(
        schema=_FakeAnswer,
        system="sys",
        user="usr",
    )
    assert result.text == "ok"
    assert result.count == 2


async def test_openai_generate_structured_invalid_json_raises() -> None:
    provider = OpenAICompatLLMProvider(api_key="dummy")
    await _chat_response(provider, "this is not json")
    with pytest.raises(StructuredOutputError):
        await provider.generate_structured(
            schema=_FakeAnswer,
            system="sys",
            user="usr",
        )


async def test_openai_generate_retries_on_429() -> None:
    provider = OpenAICompatLLMProvider(api_key="dummy")
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                429,
                # retry-after header takes precedence for the wait time
                headers={"retry-after": "0"},
                json={"error": {"message": "Rate limited"}},
            )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "after retry"}}]},
        )

    provider._client = httpx.AsyncClient(  # type: ignore[assignment]
        transport=httpx.MockTransport(handler)
    )
    result = await provider.generate(system="sys", user="usr")
    assert result == "after retry"
    assert calls["n"] == 2


async def test_openai_backend_error_maps_to_unavailable() -> None:
    provider = OpenAICompatLLMProvider(api_key="bad")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"error": {"message": "Invalid API key"}},
        )

    provider._client = httpx.AsyncClient(  # type: ignore[assignment]
        transport=httpx.MockTransport(handler)
    )
    with pytest.raises(LLMUnavailableError, match="401"):
        await provider.generate(system="sys", user="usr")


async def test_openai_check_connection_success() -> None:
    provider = OpenAICompatLLMProvider(api_key="dummy")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/models")
        return httpx.Response(200, json={"data": [{"id": "qwen/qwen3.6-27b"}]})

    provider._client = httpx.AsyncClient(  # type: ignore[assignment]
        transport=httpx.MockTransport(handler)
    )
    await provider.check_connection()


async def test_openai_check_connection_connect_error() -> None:
    provider = OpenAICompatLLMProvider(api_key="dummy")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider._client = httpx.AsyncClient(  # type: ignore[assignment]
        transport=httpx.MockTransport(handler)
    )
    with pytest.raises(LLMUnavailableError, match="Cannot reach"):
        await provider.check_connection()


async def test_create_provider_returns_openai_by_default() -> None:
    provider = create_provider()
    assert isinstance(provider, OpenAICompatLLMProvider)


# ---- Hugging Face provider ----


class _FakeChatCompletion:
    def __init__(self, content: str) -> None:
        self._content = content

    async def __call__(self, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))]
        )


def _patch_hf(provider: HFLLMProvider, content: str) -> None:
    provider._client.chat_completion = _FakeChatCompletion(content)  # type: ignore[method-assign]


async def test_hf_generate_returns_text() -> None:
    provider = HFLLMProvider(token="dummy-token")
    _patch_hf(provider, "  hello hf  ")
    result = await provider.generate(system="sys", user="usr")
    assert result == "hello hf"


async def test_hf_generate_structured_parses_json() -> None:
    provider = HFLLMProvider(token="dummy-token")
    _patch_hf(provider, json.dumps({"text": "ok", "count": 2}))
    result = await provider.generate_structured(
        schema=_FakeAnswer,
        system="sys",
        user="usr",
    )
    assert result.text == "ok"
    assert result.count == 2


async def test_hf_requires_token() -> None:
    provider = HFLLMProvider(token="")
    with pytest.raises(LLMUnavailableError):
        await provider.generate(system="sys", user="usr")
    with pytest.raises(LLMUnavailableError, match="HF_TOKEN"):
        await provider.check_connection()


async def test_hf_generate_structured_invalid_json_raises() -> None:
    provider = HFLLMProvider(token="dummy-token")
    _patch_hf(provider, "this is not json")
    with pytest.raises(StructuredOutputError):
        await provider.generate_structured(
            schema=_FakeAnswer,
            system="sys",
            user="usr",
        )
