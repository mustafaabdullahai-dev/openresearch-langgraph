"""Tests for source scoring, URL safety, and text chunking."""

from __future__ import annotations

import pytest
from app.services.sources.processor import (
    chunk_text,
    extract_domain,
    is_blocked_host,
    is_safe_url,
    score_source,
)


def test_is_safe_url_accepts_http_and_https():
    assert is_safe_url("https://example.org/path")
    assert is_safe_url("http://example.org")


def test_is_safe_url_rejects_other_schemes():
    assert not is_safe_url("ftp://example.org")
    assert not is_safe_url("javascript:alert(1)")
    assert not is_safe_url("example.org/no-scheme")


def test_extract_domain_normalises_host():
    assert extract_domain("https://www.Example.org/path") == "example.org"
    assert extract_domain("https://docs.python.org/3/") == "docs.python.org"


def test_score_source_tiers():
    assert score_source("https://github.com/org/repo")[1] == "primary"
    assert score_source("https://edu.gov/research")[1] == "government"
    assert score_source("https://docs.rust-lang.org/book")[1] == (
        "official_documentation"
    )
    assert score_source("https://en.wikipedia.org/wiki/X")[1] == "community"
    assert score_source("https://www.reddit.com/r/ai")[1] == "community"
    assert score_source("https://example.org/anything")[1] == "reputable"


def test_score_source_returns_float_in_unit_interval():
    score, _tier = score_source("https://example.org/anything")
    assert 0.0 <= score <= 1.0


def test_chunk_text_single_chunk_for_short_text():
    text = "Short but meaningful paragraph."
    assert chunk_text(text) == [text]


def test_chunk_text_splits_long_text_with_overlap():
    body = "Paragraph number {i} about the research topic."
    text = "\n\n".join(body.format(i=i) for i in range(60))
    chunks = chunk_text(text, chunk_size=120, overlap=20)
    assert len(chunks) > 1
    assert all(len(c) <= 120 + 40 for c in chunks)
    assert all(c.strip() for c in chunks)


def test_chunk_text_returns_empty_for_blank():
    assert chunk_text("   ") == []


@pytest.mark.asyncio
async def test_is_blocked_host_flags_loopback_and_private():
    assert await is_blocked_host("http://127.0.0.1/x")
    assert await is_blocked_host("http://10.0.0.1/x")
    assert await is_blocked_host("http://localhost/x")
