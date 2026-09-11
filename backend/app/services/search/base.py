"""Search abstraction.

Front-ends must not know where results come from. Every provider returns
normalized :class:`SearchResult` objects with URL deduplication handled by
the caller, so DuckDuckGo and Tavily stay interchangeable.
"""

from typing import Protocol

from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source: str


class SearchProvider(Protocol):
    """Contract implemented by every search backend."""

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Return normalized results for ``query``."""
