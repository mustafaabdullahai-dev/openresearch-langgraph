"""Web source processing: fetch, extract, score, and chunk.

Web content is untrusted. We (a) only admit http/https URLs, (b) refuse
private/loopback IP addresses to blunt SSRF, (c) cap response size, and
(d) never let one broken page abort the research workflow — callers are
expected to catch :class:`SourceFetchError` and continue.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .errors import SourceFetchError

MAX_CONTENT_BYTES = 2_000_000
FETCH_TIMEOUT = httpx.Timeout(10.0)
_USER_AGENT = (
    "OpenResearch/0.1 (research assistant; +https://github.com/openresearch-langgraph)"
)

_OFFICIAL_DOCS = (
    "docs.",
    ".readthedocs.io",
    "learn.microsoft.com",
    "developer.mozilla.org",
    "aws.amazon.com",
    "cloud.google.com",
    "kubernetes.io",
    "docs.python.org",
    "platform.openai.com/docs",
    "arxiv.org/pdf",
)

_PRIMARY_HINTS = (
    "arxiv.org",
    "github.com",
    "gitlab.com",
    "pubmed.ncbi.nlm.nih.gov",
    "sciencedirect.com",
    "aclanthology.org",
    "neurips.cc",
    "openreview.net",
    "dl.acm.org",
    "ieeexplore.ieee.org",
)


def is_safe_url(url: str) -> bool:
    """Return True when the URL is http(s) and does not target a private host."""
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.hostname)


def _is_loopback_or_private(ip_text: str) -> bool:
    try:
        address = ipaddress.ip_address(ip_text)
    except ValueError:
        return True  # unparsable IP => refuse
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
    )


async def is_blocked_host(url: str) -> bool:
    """Return True if the URL targets a private/loopback host (SSRF guard)."""
    hostname = urlparse(url).hostname
    if not hostname:
        return True
    try:
        infos = await asyncio.to_thread(
            socket.getaddrinfo, hostname, None, socket.AF_INET
        )
    except socket.gaierror:
        return True  # unresolvable => refuse to attempt a request
    return any(_is_loopback_or_private(str(info[4][0])) for info in infos)


def extract_domain(url: str) -> str:
    """Return the lowercased registrable-looking hostname without www."""
    hostname = (urlparse(url).hostname or "").lower()
    return hostname.removeprefix("www.")


def score_source(url: str, title: str = "") -> tuple[float, str]:
    """Heuristic quality score in [0, 1] plus a tier label."""
    domain = extract_domain(url)
    full = f"{domain} {title}".lower()

    # Primary / code repos
    if domain in ("github.com", "gitlab.com"):
        return 0.85, "primary"

    # Academic / peer-reviewed
    if any(hint in domain for hint in _PRIMARY_HINTS):
        return 0.95, "academic"

    # Government
    if domain.startswith("gov.") or domain.endswith(".gov"):
        return 1.0, "government"

    # Official documentation
    if any(domain.startswith(p) for p in ("docs.",)) or any(
        s in domain for s in _OFFICIAL_DOCS
    ):
        return 0.92, "official_documentation"

    # Community / discussion
    if "stackoverflow.com" in domain or "en.wikipedia.org" in domain:
        return 0.7, "community"
    if any(hint in full for hint in ("reddit", "/r/", "forum", "discussion")):
        return 0.4, "community"

    # Default tier
    return 0.5, "reputable"


async def fetch_source(url: str, snippet: str = "") -> dict[str, Any]:
    """Fetch and extract readable text from ``url``.

    Raises :class:`SourceFetchError` on any failure; never returns None
    obscurely. The snippet is preserved even when content extraction fails.
    """
    if not is_safe_url(url):
        raise SourceFetchError(f"Blocked URL (must be http/https): {url}")
    if await is_blocked_host(url):
        raise SourceFetchError(f"Blocked URL (private/loopback target): {url}")

    headers = {"User-Agent": _USER_AGENT}
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=FETCH_TIMEOUT
        ) as client:
            response = await client.get(url, headers=headers)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise SourceFetchError(f"Failed to fetch {url}: {exc}") from exc

    if len(response.content) > MAX_CONTENT_BYTES:
        raise SourceFetchError(f"Content too large at {url}")

    content = response.text
    if not content.strip():
        raise SourceFetchError(f"Empty page at {url}")

    try:
        extracted = __extract_text_trafilatura(content)
    except Exception:
        extracted = ""

    if not extracted:
        extracted = __extract_text_fallback(content)

    return {
        "url": url,
        "title": __extract_title(content),
        "domain": extract_domain(url),
        "snippet": snippet,
        "content": extracted,
        "published_at": "",
        "retrieved_at": datetime.now(UTC).isoformat(),
    }


def __extract_text_trafilatura(html: str) -> str:
    from trafilatura import extract

    return extract(html, include_comments=False, include_tables=True) or ""


def __extract_text_fallback(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())


def __extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        return " ".join(soup.title.string.split())
    meta = soup.find("meta", attrs={"property": "og:title"})
    if meta and meta.get("content"):
        return str(meta["content"]).strip()
    return ""


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    """Split long text into overlapping chunks on paragraph boundaries."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        while len(paragraph) > chunk_size:
            if current:
                chunks.append(current)
            current = paragraph[:chunk_size]
            paragraph = paragraph[chunk_size - overlap :]
        candidate = (current + "\n\n" + paragraph) if current else paragraph
        if len(candidate) > chunk_size and current:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current.strip():
        chunks.append(current)
    return chunks


__all__ = [
    "MAX_CONTENT_BYTES",
    "SourceFetchError",
    "chunk_text",
    "extract_domain",
    "fetch_source",
    "is_blocked_host",
    "is_safe_url",
    "score_source",
]
