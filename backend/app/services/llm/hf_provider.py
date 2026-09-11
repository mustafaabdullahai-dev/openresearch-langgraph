"""Hugging Face-backed implementation of the LLM provider abstraction.

Uses Hugging Face's inference servers (serverless ``api-inference`` or your
own ``HF_BASE_URL`` endpoint) via ``AsyncInferenceClient``, so no local GPU
or model download is required. Model and token come from settings; if serving
is cold Hugging Face returns a 503 and we surface a clear error instead.
"""

from __future__ import annotations

import json
from typing import TypeVar

from huggingface_hub import AsyncInferenceClient, InferenceTimeoutError
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


class HFLLMProvider:
    """LLM provider backed by Hugging Face hosted inference."""

    def __init__(
        self,
        *,
        model: str | None = None,
        token: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.2,
    ) -> None:
        self.model = model or settings.HF_MODEL
        self.token = token if token is not None else settings.HF_TOKEN
        self.temperature = temperature
        self._client = AsyncInferenceClient(
            token=self.token or None,
            model=self.model,
            base_url=base_url,
            timeout=180,
        )

    async def generate(self, *, system: str, user: str, json_mode: bool = False) -> str:
        """Generate a free-form completion via HF chat completion."""
        if not self.token:
            raise LLMUnavailableError(
                "Hugging Face inference is configured but HF_TOKEN is empty. "
                "Set HF_TOKEN in your environment to use hosted models."
            )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        try:
            result = await self._client.chat_completion(
                messages=messages,
                temperature=self.temperature,
                max_tokens=4096,
            )
        except Exception as exc:
            raise self._translate_error(exc) from exc

        try:
            content = result.choices[0].message.content or ""
        except (AttributeError, IndexError, KeyError) as exc:
            raise LLMGenerationError(
                f"Unexpected response shape from Hugging Face for {self.model}."
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
        """Raise :class:`LLMUnavailableError` if HF inference is unreachable."""
        if not self.token:
            raise LLMUnavailableError(
                "Hugging Face is configured as the LLM provider but HF_TOKEN is "
                "empty. Create a token at https://huggingface.co/settings/tokens "
                "and set HF_TOKEN."
            )
        try:
            await self.generate(
                system="You are a helpful assistant.",
                user="Reply with exactly: ok",
            )
        except LLMProviderError as exc:
            if isinstance(exc, LLMUnavailableError):
                raise
            raise LLMUnavailableError(str(exc)) from exc

    def _translate_error(self, exc: Exception) -> LLMProviderError:
        """Map inference-server errors to stable, user-actionable messages."""
        if isinstance(exc, LLMProviderError):
            return exc

        status = getattr(exc, "status_code", None)
        message = str(exc)

        if status == 401 or "authorization" in message.lower():
            return LLMUnavailableError(
                "Hugging Face rejected the token. Check that HF_TOKEN is valid "
                "for model " + self.model + " (you may need to accept its terms)."
            )
        if status == 404 or (
            "not found" in message.lower() and "model" in message.lower()
        ):
            return LLMUnavailableError(
                f"Model {self.model!r} is not available on Hugging Face inference. "
                "Check the model id (e.g. Qwen/Qwen3-8B or "
                "Qwen/Qwen2.5-7B-Instruct)."
            )
        if status == 503 or "model is loading" in message.lower():
            return LLMUnavailableError(
                f"Hugging Face is warming up {self.model} for first request. "
                "Retry in a few seconds."
            )
        if isinstance(exc, InferenceTimeoutError) or "timeout" in message.lower():
            return LLMGenerationError(
                f"Inference for {self.model} timed out. The serverless instance "
                "may be cold; retry."
            )
        return LLMGenerationError(
            f"Hugging Face generation failed for model {self.model}: {exc}"
        )
