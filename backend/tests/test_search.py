"""Tests for search provider factory and construction-time behavior."""

from __future__ import annotations

import pytest
from app.services.search import (
    DuckDuckGoSearchProvider,
    SearchProviderNotConfiguredError,
    TavilySearchProvider,
    create_search_provider,
)
from app.services.search.base import SearchResult


def test_factory_returns_duckduckgo_by_default(monkeypatch):
    monkeypatch.setattr("app.services.search.settings.SEARCH_PROVIDER", "duckduckgo")
    provider = create_search_provider()
    assert isinstance(provider, DuckDuckGoSearchProvider)


def test_factory_rejects_unknown_provider(monkeypatch):
    monkeypatch.setattr("app.services.search.settings.SEARCH_PROVIDER", "bing")
    with pytest.raises(SearchProviderNotConfiguredError):
        create_search_provider()


def test_tavily_requires_api_key():
    with pytest.raises(SearchProviderNotConfiguredError):
        TavilySearchProvider(api_key="")


def test_search_result_model_roundtrip():
    item = SearchResult(title="T", url="https://example.org", snippet="s", source="ddg")
    assert item.url == "https://example.org"
    assert item.title == "T"
    assert item.snippet == "s"


def test_factory_returns_tavily_when_configured(monkeypatch):
    monkeypatch.setattr("app.services.search.settings.SEARCH_PROVIDER", "tavily")
    monkeypatch.setattr("app.services.search.settings.TAVILY_API_KEY", "test-key")
    provider = create_search_provider()
    assert isinstance(provider, TavilySearchProvider)
