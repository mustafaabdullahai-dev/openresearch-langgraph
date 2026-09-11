"""Ollama-backed implementation of the LLM provider abstraction.

Uses langchain-ollama's :class:`ChatOllama` wrapper to talk to a local
Ollama server. The model name and server address come from settings, so no
provider code changes when a different open-weight model is used.
"""

import json
from typing import Any, TypeVar

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, ValidationError

from app.config.settings import settings

from .errors import (
    LLMGenerationError,
    LLMProviderError,
    LLMUnavailableError,
    StructuredOutputError,
)

T = TypeVar("T", bound=BaseModel)


def _strip_code_fences(text: str) -> str:
    """Remove leading/trailing markdown fences and surrounding whitespace."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :].strip()
        text = text.removeprefix("```").strip()
    if text.endswith("```"):
        text = text[: -len("```")].rstrip()
    return text.strip()


def _extract_json_object(text: str) -> dict[str, Any]:
    """Leniently extract a JSON object from model output.

    Models sometimes wrap JSON in prose or markdown fences. Try a direct
    parse first, then fall back to slicing between the outermost braces.
    """
    text = _strip_code_fences(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError as exc:
                raise StructuredOutputError("Model returned invalid JSON.") from exc
        raise StructuredOutputError(
            "Model output did not contain a JSON object."
        ) from None


class OllamaLLMProvider:
    """LLM provider backed by a local Ollama server."""

    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.2,
        num_ctx: int = 8192,
    ) -> None:
        self.model = model or settings.OLLAMA_MODEL
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.temperature = temperature
        self.num_ctx = num_ctx

    def _build_chat(self, *, json_mode: bool = False) -> ChatOllama:
        return ChatOllama(
            model=self.model,
            base_url=self.base_url,
            temperature=self.temperature,
            num_ctx=self.num_ctx,
            format="json" if json_mode else None,
        )

    async def generate(self, *, system: str, user: str, json_mode: bool = False) -> str:
        """Generate a completion from the local model."""
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=user),
        ]
        try:
            chat = self._build_chat(json_mode=json_mode)
            response = await chat.ainvoke(messages)
        except Exception as exc:
            raise self._translate_error(exc) from exc
        content = response.content
        if isinstance(content, list):
            content = "\n".join(
                str(part.get("text", "")) for part in content if isinstance(part, dict)
            )
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
        instruction = (
            "Return a single JSON object conforming exactly to the schema below.\n"
            "Do not include prose, code fences, or any text outside the JSON object.\n"
            f"Schema:\n{schema_json}"
        )
        raw = await self.generate(
            system=system,
            user=f"{user}\n\n{instruction}",
            json_mode=True,
        )
        try:
            data = _extract_json_object(raw)
            return schema.model_validate(data)
        except ValidationError as exc:
            errors_summary = list(exc.errors())[:3]
            raise StructuredOutputError(
                f"Model output did not match schema {schema.__name__}: {errors_summary}"
            ) from exc

    async def check_connection(self) -> None:
        """Raise :class:`LLMUnavailableError` if Ollama cannot be reached."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(
                f"Cannot reach Ollama at {self.base_url}. "
                "Ensure it is running with `ollama serve`."
            ) from exc
        if response.status_code >= 400:
            raise LLMUnavailableError(
                f"Ollama at {self.base_url} returned HTTP {response.status_code}."
            )

    def _translate_error(self, exc: Exception) -> LLMProviderError:
        """Map low-level client errors to stable, user-actionable provider errors."""
        if isinstance(exc, LLMProviderError):
            return exc
        message = str(exc).lower()
        if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)) or any(
            token in message
            for token in (
                "connection refused",
                "connect error",
                "could not connect",
                "failed to connect",
            )
        ):
            return LLMUnavailableError(
                f"Cannot reach Ollama at {self.base_url}. "
                f"Ensure it is running (`ollama serve`) and the model `{self.model}` "
                f"is available (`ollama pull {self.model}`)."
            )
        if "model" in message and "not found" in message:
            return LLMUnavailableError(
                f"The model `{self.model}` is not installed in Ollama. "
                f"Install it with `ollama pull {self.model}`."
            )
        return LLMGenerationError(
            f"LLM generation failed for model {self.model}: {exc}"
        )
