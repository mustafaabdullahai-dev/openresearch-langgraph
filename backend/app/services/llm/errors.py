"""Errors raised by LLM providers."""


class LLMProviderError(Exception):
    """Base class for all model provider failures."""


class LLMUnavailableError(LLMProviderError):
    """The model backend cannot be reached (missing token or API down)."""


class LLMGenerationError(LLMProviderError):
    """The model produced no usable output."""


class StructuredOutputError(LLMProviderError):
    """The model output could not be parsed into the requested schema."""
