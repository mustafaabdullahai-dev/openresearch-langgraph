"""Tests for the Hugging Face hosted LLM provider.

These tests never touch a real model: the inference client and the HTTP
transport are replaced with fakes so the suite runs in any environment.
"""

import json
from types import SimpleNamespace

import pytest
from app.services.llm.errors import LLMUnavailableError, StructuredOutputError
from app.services.llm.hf_provider import HFLLMProvider
from app.services.llm.provider import create_provider
from pydantic import BaseModel


class _FakeAnswer(BaseModel):
    text: str
    count: int


class _FakeChatCompletion:
    def __init__(self, content: str) -> None:
        self._content = content

    async def __call__(self, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))]
        )


def _patch_client(provider: HFLLMProvider, content: str) -> None:
    provider._client.chat_completion = _FakeChatCompletion(content)  # type: ignore[method-assign]


async def test_generate_returns_text() -> None:
    provider = HFLLMProvider(token="dummy-token")
    _patch_client(provider, "  hello hf  ")
    result = await provider.generate(system="sys", user="usr")
    assert result == "hello hf"


async def test_generate_structured_valid_json() -> None:
    provider = HFLLMProvider(token="dummy-token")
    _patch_client(provider, json.dumps({"text": "ok", "count": 3}))
    result = await provider.generate_structured(
        schema=_FakeAnswer,
        system="sys",
        user="usr",
    )
    assert result.text == "ok"
    assert result.count == 3


async def test_generate_structured_strips_markdown_fences() -> None:
    provider = HFLLMProvider(token="dummy-token")
    payload = "```json\n" + json.dumps({"text": "ok", "count": 1}) + "\n```"
    _patch_client(provider, payload)
    result = await provider.generate_structured(
        schema=_FakeAnswer,
        system="sys",
        user="usr",
    )
    assert result.count == 1


async def test_generate_structured_invalid_json_raises() -> None:
    provider = HFLLMProvider(token="dummy-token")
    _patch_client(provider, "this is not json")
    with pytest.raises(StructuredOutputError):
        await provider.generate_structured(
            schema=_FakeAnswer,
            system="sys",
            user="usr",
        )


async def test_generate_requires_token() -> None:
    provider = HFLLMProvider(token="")
    with pytest.raises(LLMUnavailableError):
        await provider.generate(system="sys", user="usr")
    with pytest.raises(LLMUnavailableError):
        await provider.check_connection()


async def test_missing_token_raises_clear_error() -> None:
    provider = HFLLMProvider(token="")
    with pytest.raises(LLMUnavailableError, match="HF_TOKEN"):
        await provider.check_connection()


async def test_create_provider_returns_hf() -> None:
    provider = create_provider()
    assert isinstance(provider, HFLLMProvider)
