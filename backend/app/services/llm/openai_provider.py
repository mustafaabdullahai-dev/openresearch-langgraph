"""OpenAI-compatible LLM provider (e.g. Groq, Together, vLLM, LM Studio).

Talks to any HTTP endpoint that implements the OpenAI ``/chat/completions``
contract, using ``httpx`` directly so no extra dependency is needed. The
defaults point at Groq's free tier with a Qwen chat model, but everything is
driven by the ``OPENAI_*`` settings so any OpenAI-compatible provider works.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config.settings import settings

from ._parsing import extract_json_object
from .errors import (
    LLMGenerationError,
    LLMProviderError,
    LLMUnavailableError,
    StructuredOutputError,
)

T = TypeVar("T", bound=BaseModel)

_JSON_INSTRUCTION = (
    "Return a single JSON object conforming exactly to the schema below.\n"
    "Do not include prose, code fences, or any text outside the JSON object.\n"
    "Schema:\n{schema_json}"
)

_MAX_429_RETRIES = 4


class OpenAICompatLLMProvider:
    """LLM provider backed by an OpenAI-compatible chat completions API."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.2,
    ) -> None:
        self.model = model or settings.OPENAI_MODEL
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.base_url = (base_url or settings.OPENAI_BASE_URL).rstrip("/")
        self.max_tokens = max_tokens or settings.OPENAI_MAX_TOKENS
        self.temperature = temperature
        self._client = httpx.AsyncClient(timeout=180)
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _retry_wait_from(self, response: httpx.Response) -> float:
        """Seconds to wait before retrying a rate-limited request."""
        header = response.headers.get("retry-after")
        if header:
            try:
                return max(0.0, float(header))
            except ValueError:
                pass
        match = re.search(r"in (\d+(?:\.\d+)?)s", response.text)
        if match:
            return max(0.0, float(match.group(1)))
        return 10.0

    async def _post_chat(self, payload: dict[str, Any]) -> httpx.Response:
        url = f"{self.base_url}/chat/completions"
        last: httpx.Response | None = None
        for attempt in range(_MAX_429_RETRIES + 1):
            try:
                response = await self._client.post(
                    url, headers=self._headers, json=payload
                )
            except httpx.HTTPError as exc:
                raise self._translate_error(exc) from exc
            if response.status_code != 429:
                return response
            if attempt < _MAX_429_RETRIES:
                await asyncio.sleep(self._retry_wait_from(response))
            last = response
        assert last is not None
        return last

    async def generate(self, *, system: str, user: str, json_mode: bool = False) -> str:
        """Generate a free-form completion via the OpenAI chat contract."""
        if not self.api_key:
            raise LLMUnavailableError(
                "OpenAI-compatible inference is configured but OPENAI_API_KEY is "
                "empty. Set OPENAI_API_KEY in your environment."
            )
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        response = await self._post_chat(payload)

        if response.status_code != 200:
            detail = self._extract_error_detail(response)
            raise self._translate_error(
                LLMUnavailableError(
                    f"{self.base_url} returned HTTP {response.status_code}: {detail}"
                )
            )
        try:
            content = response.json()["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMGenerationError(
                f"Unexpected response shape from {self.base_url} for {self.model}."
            ) from exc
        return str(content).strip()

    async def generate_structured(
        self,
        *,
        schema: type[T],
        system: str,
        user: str,
    ) -> T:
        """Generate output validated against a Pydantic schema."""
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        raw = await self.generate(
            system=system,
            user=f"{user}\n\n{_JSON_INSTRUCTION.format(schema_json=schema_json)}",
            json_mode=True,
        )
        try:
            data = extract_json_object(raw)
            return schema.model_validate(data)
        except ValidationError as exc:
            errors_summary = list(exc.errors())[:3]
            raise StructuredOutputError(
                f"Model output did not match schema {schema.__name__}: {errors_summary}"
            ) from exc

    async def check_connection(self) -> None:
        """Raise :class:`LLMUnavailableError` if the endpoint is unreachable."""
        if not self.api_key:
            raise LLMUnavailableError(
                "OpenAI-compatible inference is configured but OPENAI_API_KEY is "
                "empty. Set OPENAI_API_KEY to use hosted models."
            )
        try:
            response = await self._client.get(
                f"{self.base_url}/models",
                headers=self._headers,
            )
        except httpx.HTTPError as exc:
            raise self._translate_error(exc) from exc
        if response.status_code != 200:
            detail = self._extract_error_detail(response)
            raise LLMUnavailableError(
                f"{self.base_url} returned HTTP {response.status_code}: {detail}"
            )

    async def aclose(self) -> None:
        """Release the underlying HTTP client."""
        await self._client.aclose()

    def _extract_error_detail(self, response: httpx.Response) -> str:
        try:
            message = response.json().get("error", {}).get("message")
            if message:
                return str(message)
        except ValueError:
            pass
        return response.text[:300]

    def _translate_error(self, exc: Exception) -> LLMProviderError:
        """Map HTTP/transport errors to stable, user-actionable messages."""
        if isinstance(exc, LLMProviderError):
            return exc
        message = str(exc)
        if isinstance(exc, httpx.ConnectError) or "connect" in message.lower():
            return LLMUnavailableError(
                f"Cannot reach {self.base_url}. Check the endpoint and network "
                "connectivity."
            )
        if "timed out" in message.lower() or "timeout" in message.lower():
            return LLMGenerationError(f"Generation for {self.model} timed out. Retry.")
        return LLMGenerationError(
            f"OpenAI-compatible generation failed for model {self.model}: {exc}"
        )
