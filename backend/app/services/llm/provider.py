"""Model provider abstraction.

High-level contract for the LLM backend — Hugging Face hosted inference by
default. Agents and graph nodes depend only on this protocol rather than a
concrete implementation, so the runtime model can be swapped without touching
agent or graph code.
"""

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):
    """Contract implemented by every supported LLM backend."""

    async def generate(self, *, system: str, user: str, json_mode: bool = False) -> str:
        """Generate a free-form text completion."""

    async def generate_structured(
        self,
        *,
        schema: type[T],
        system: str,
        user: str,
    ) -> T:
        """Generate output validated against a Pydantic schema."""

    async def check_connection(self) -> None:
        """Raise :class:`LLMUnavailableError` if the backend is unreachable."""


def create_provider() -> LLMProvider:
    """Return the provider configured for the current environment.

    ``settings.LLM_PROVIDER`` selects the backend: ``"openai"`` for any
    OpenAI-compatible endpoint (Groq by default) or ``"hf"`` for Hugging
    Face hosted inference.
    """
    from app.config.settings import settings

    from .hf_provider import HFLLMProvider
    from .openai_provider import OpenAICompatLLMProvider

    if settings.LLM_PROVIDER == "hf":
        return HFLLMProvider()
    return OpenAICompatLLMProvider()
