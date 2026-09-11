"""Tests for the Ollama LLM provider.

These tests never touch a real model: the ChatOllama client and the HTTP
transport are replaced with fakes so the suite runs in any environment.
"""

import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from app.services.llm.errors import LLMUnavailableError, StructuredOutputError
from app.services.llm.ollama_provider import OllamaLLMProvider
from app.services.llm.provider import create_provider
from pydantic import BaseModel


class _FakeAnswer(BaseModel):
    text: str
    count: int


class _FakeChat:
    def __init__(self, content: str) -> None:
        self._content = content

    async def ainvoke(self, messages: list[object]) -> SimpleNamespace:
        return SimpleNamespace(content=self._content)


def _provider(chat: _FakeChat) -> OllamaLLMProvider:
    provider = OllamaLLMProvider(model="qwen3:8b", base_url="http://test:11434")
    provider._build_chat = lambda **_: chat  # type: ignore[method-assign]
    return provider


async def test_generate_returns_text() -> None:
    provider = _provider(_FakeChat("hello world"))
    result = await provider.generate(system="sys", user="usr")
    assert result == "hello world"


async def test_generate_structured_valid_json() -> None:
    payload = json.dumps({"text": "ok", "count": 3})
    provider = _provider(_FakeChat(payload))
    result = await provider.generate_structured(
        schema=_FakeAnswer,
        system="sys",
        user="usr",
    )
    assert result.text == "ok"
    assert result.count == 3


async def test_generate_structured_strips_markdown_fences() -> None:
    payload = "```json\n" + json.dumps({"text": "ok", "count": 1}) + "\n```"
    provider = _provider(_FakeChat(payload))
    result = await provider.generate_structured(
        schema=_FakeAnswer,
        system="sys",
        user="usr",
    )
    assert result.count == 1


async def test_generate_structured_invalid_json_raises() -> None:
    provider = _provider(_FakeChat("this is not json"))
    with pytest.raises(StructuredOutputError):
        await provider.generate_structured(schema=_FakeAnswer, system="sys", user="usr")


async def test_generate_structured_uses_json_mode() -> None:
    captured: dict[str, Any] = {}

    def spy(**kwargs: Any) -> _FakeChat:
        captured.update(kwargs)
        return _FakeChat(json.dumps({"text": "x", "count": 0}))

    provider = OllamaLLMProvider(model="qwen3:8b", base_url="http://test:11434")
    provider._build_chat = spy  # type: ignore[method-assign]
    await provider.generate_structured(schema=_FakeAnswer, system="sys", user="usr")
    assert captured["json_mode"] is True


async def test_generate_connection_error_maps_to_unavailable() -> None:
    def boom(**kwargs: Any) -> Any:
        request = httpx.Request("POST", "http://test:11434/api/chat")
        raise httpx.ConnectError("connect error: connection refused", request=request)

    provider = OllamaLLMProvider(model="qwen3:8b", base_url="http://test:11434")
    provider._build_chat = boom  # type: ignore[method-assign]
    with pytest.raises(LLMUnavailableError):
        await provider.generate(system="sys", user="usr")


class _FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _FakeAsyncClient:
    def __init__(
        self,
        response: _FakeResponse | None = None,
        error: httpx.HTTPError | None = None,
    ) -> None:
        self._response = response
        self._error = error

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, url: str) -> _FakeResponse:
        if self._error is not None:
            raise self._error
        return self._response or _FakeResponse(200)


async def test_check_connection_success(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = _FakeAsyncClient(_FakeResponse(200))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: fake_client)
    provider = OllamaLLMProvider(model="qwen3:8b", base_url="http://test:11434")
    await provider.check_connection()


async def test_check_connection_unavailable_on_connect_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request("GET", "http://test:11434/api/tags")
    connect_error = httpx.ConnectError("connection refused", request=request)
    client = _FakeAsyncClient(error=connect_error)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: client)
    provider = OllamaLLMProvider(model="qwen3:8b", base_url="http://test:11434")
    with pytest.raises(LLMUnavailableError):
        await provider.check_connection()


async def test_create_provider_returns_ollama() -> None:
    provider = create_provider()
    assert isinstance(provider, OllamaLLMProvider)
