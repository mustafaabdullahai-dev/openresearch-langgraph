"""FastAPI dependency providers."""

from app.services.llm import LLMProvider, create_provider


def get_llm_provider() -> LLMProvider:
    """Provide the configured LLM provider to request handlers."""
    return create_provider()
