"""Search provider registry."""

from app.config.settings import settings

from .base import SearchProvider, SearchResult
from .duckduckgo import DuckDuckGoSearchProvider
from .errors import (
    SearchError,
    SearchProviderNotConfiguredError,
)
from .tavily import TavilySearchProvider


def create_search_provider() -> SearchProvider:
    """Return the search backend configured by ``SEARCH_PROVIDER``."""
    provider = settings.SEARCH_PROVIDER.lower()
    if provider == "duckduckgo":
        return DuckDuckGoSearchProvider()
    if provider == "tavily":
        return TavilySearchProvider(api_key=settings.TAVILY_API_KEY)
    raise SearchProviderNotConfiguredError(
        f"Unknown SEARCH_PROVIDER '{provider}'. Use 'duckduckgo' or 'tavily'."
    )


__all__ = [
    "DuckDuckGoSearchProvider",
    "SearchError",
    "SearchProvider",
    "SearchProviderNotConfiguredError",
    "SearchResult",
    "TavilySearchProvider",
    "create_search_provider",
]
