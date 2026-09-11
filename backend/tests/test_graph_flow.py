"""End-to-end tests of the compiled research graph using fakes.

All tests run fully offline: the LLM provider, search backend, source
fetching and source scoring are faked, and persistence uses an in-memory
checkpointer. This exercises real orchestration and routing logic.
"""

from __future__ import annotations

from app.services.search.base import SearchResult
from tests.conftest import offline_graph, run_graph
from tests.fakes import SAMPLE_REPORT, FakeProvider, FakeSearch

QUESTION = "Compare LangGraph and CrewAI for production AI agents."


class _FailSearch:
    """Search backend that always raises, used to test error handling."""

    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        self.queries.append(query)
        raise RuntimeError("backend is down")


class _OneShotSearch:
    """Serves the same results on the first call, then nothing."""

    def __init__(self) -> None:
        self.queries: list[str] = []
        self.calls = 0

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        self.queries.append(query)
        self.calls += 1
        if self.calls == 1:
            return FakeSearch().batch
        return []


def test_graph_runs_end_to_end(monkeypatch):
    provider = FakeProvider()
    search = FakeSearch()
    graph = offline_graph(provider, search, monkeypatch)
    state = run_graph(graph, QUESTION)

    assert state["research_complete"] is True
    assert state["review_accepted"] is True
    assert "Executive Summary" in state["final_report"]
    assert state["final_report"] == SAMPLE_REPORT
    assert len(state["sources"]) == 2
    assert len(state["fact_checks"]) == 2
    assert len(state["citations"]) >= 1
    assert not state["errors"]
    assert state["research_iteration"] == 1


def test_graph_agent_call_order(monkeypatch):
    provider = FakeProvider()
    search = FakeSearch()
    graph = offline_graph(provider, search, monkeypatch)
    run_graph(graph, QUESTION)

    assert provider.calls == [
        "analyze_query",
        "create_research_plan",
        "analyze_source",
        "analyze_source",
        "fact_check",
        "evaluate_research",
        "generate",  # report_writer
        "review_report",
    ]


def test_critic_keeps_searching_until_iteration_budget(monkeypatch):
    provider = FakeProvider(critic_complete=False)
    search = _OneShotSearch()
    graph = offline_graph(provider, search, monkeypatch, max_report_revisions=1)
    state = run_graph(graph, QUESTION, max_iterations=2)

    assert state["research_iteration"] == 2  # consumed the full search budget
    assert state["research_complete"] is True  # forced at the boundary
    assert provider.calls.count("evaluate_research") == 1  # critic consulted on iter 1
    assert provider.calls.count("generate") == 1  # report written exactly once
    assert bool(state["final_report"])
    assert state["review_accepted"] is True


def test_reviewer_rewrites_report_within_budget(monkeypatch):
    provider = FakeProvider(
        reviewer_acceptable=False, completions=["draft one", "draft two"]
    )
    search = FakeSearch()
    graph = offline_graph(provider, search, monkeypatch, max_report_revisions=1)
    state = run_graph(graph, QUESTION)

    assert provider.calls.count("review_report") == 2  # rejected twice within budget
    assert provider.calls.count("generate") == 2  # initial + one rewrite
    assert state["review_accepted"] is False
    assert state["final_report"] == "draft two"
    assert state["revisions_remaining"] == 0


def test_search_failure_is_recorded_and_graph_survives(monkeypatch):
    provider = FakeProvider()
    failing = _FailSearch()
    graph = offline_graph(provider, failing, monkeypatch)
    state = run_graph(graph, QUESTION)

    assert state["errors"], "expected a recorded search error"
    assert state["errors"][0].startswith("Search failed for")
    # Graph must still terminate with a report.
    assert state["final_report"]


def test_sources_are_deduplicated_across_iterations(monkeypatch):
    provider = FakeProvider(critic_complete=False)
    search = FakeSearch()  # identical batch every call
    graph = offline_graph(provider, search, monkeypatch, max_report_revisions=1)
    state = run_graph(graph, QUESTION)

    urls = [s["url"] for s in state["sources"]]
    assert len(urls) == len(set(urls))  # no URL appears twice
    assert len(state["sources"]) <= 2
