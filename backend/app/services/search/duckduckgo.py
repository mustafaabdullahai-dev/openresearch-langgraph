"""DuckDuckGo search provider: free, no API key required."""

import asyncio
from typing import Any

from duckduckgo_search import DDGS

from .base import SearchResult
from .errors import SearchError

_SOURCE = "duckduckgo"


def _normalize(raw: dict[str, Any]) -> SearchResult:
    return SearchResult(
        title=raw.get("title") or "",
        url=raw.get("href") or raw.get("url") or "",
        snippet=raw.get("body") or "",
        source=_SOURCE,
    )


class DuckDuckGoSearchProvider:
    """Free-first search provider backed by DuckDuckGo."""

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Search DuckDuckGo, running the sync SDK off the event loop."""

        def _run() -> list[SearchResult]:
            try:
                with DDGS() as ddgs:
                    raw = ddgs.text(query, max_results=max_results) or []
                return [_normalize(item) for item in raw]
            except Exception as exc:
                raise SearchError(f"DuckDuckGo search failed: {exc}") from exc

        return await asyncio.to_thread(_run)


__all__ = ["DuckDuckGoSearchProvider", "_SOURCE"]
