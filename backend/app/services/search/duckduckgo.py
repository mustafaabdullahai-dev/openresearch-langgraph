"""DuckDuckGo search provider: free, no API key required."""

import asyncio
from dataclasses import asdict
from typing import Any

from ddgs import DDGS

from .base import SearchResult
from .errors import SearchError

_SOURCE = "duckduckgo"


def _normalize(row: Any) -> SearchResult:
    data = row if isinstance(row, dict) else asdict(row)
    return SearchResult(
        title=data.get("title") or data.get("name") or "",
        url=data.get("href") or data.get("url") or "",
        snippet=data.get("body") or data.get("content") or "",
        source=_SOURCE,
    )


class DuckDuckGoSearchProvider:
    """Free-first search provider backed by DuckDuckGo (``ddgs``)."""

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
