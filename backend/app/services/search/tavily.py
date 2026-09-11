"""Optional Tavily search provider.

Tavily requires an API key and is strictly optional: the application runs
fully on DuckDuckGo when no key is configured.
"""

import httpx

from .base import SearchResult
from .errors import SearchError, SearchProviderNotConfiguredError

_API_URL = "https://api.tavily.com/search"
_SOURCE = "tavily"


class TavilySearchProvider:
    """Paid, higher-quality search provider used only when an API key exists."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise SearchProviderNotConfiguredError(
                "TavilySearchProvider requires a TAVILY_API_KEY."
            )
        self._api_key = api_key

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Search Tavily and normalize the response."""
        payload = {
            "api_key": self._api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": False,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(_API_URL, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise SearchError(f"Tavily search failed: {exc}") from exc
        results: list[SearchResult] = []
        for item in data.get("results", []):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    source=_SOURCE,
                )
            )
        return results
