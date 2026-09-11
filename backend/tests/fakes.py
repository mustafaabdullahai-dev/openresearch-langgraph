"""Shared fakes for deterministic, offline tests (no LLM, no network).

``FakeProvider`` answers every agent call from canned fixtures and records
every call, so tests can assert on orchestration order. ``FakeSearch``
returns fabricated results. Network-dependent internals (source fetching,
scoring) are faked separately where the graph itself is exercised.
"""

from __future__ import annotations

from typing import Any

from app.agents.schemas import (
    FactCheckItem,
    FactCheckResult,
    QueryAnalysis,
    ReportReview,
    ResearchEvaluation,
    ResearchPlan,
    SourceSummary,
    SourceSummaryList,
)
from app.services.search.base import SearchResult
from app.services.sources.processor import chunk_text as _chunk_text

SAMPLE_REPORT = (
    "# Executive Summary\n\nBoth frameworks support production usage.[S1]\n\n"
    "# Key Findings\n\n- LangGraph provides graph orchestration.[S1]\n"
    "- CrewAI provides role-based agents.[S2]\n\n"
    "# Detailed Analysis\n\n## Architecture\nContent here.[S1]\n\n"
    "# Limitation\n\nSingle source of evidence.[S1]\n\n"
    "# Conclusion\n\nTenative conclusion based on available evidence.[S1]"
)


def _query_analysis() -> QueryAnalysis:
    return QueryAnalysis(
        research_goal="Compare LangGraph and CrewAI for production AI agents.",
        research_type="comparative",
        entities=["LangGraph", "CrewAI"],
        sub_questions=[
            "How does each framework manage state?",
            "How scalable are the frameworks?",
        ],
    )


def _research_plan() -> ResearchPlan:
    return ResearchPlan(
        objective="Compare LangGraph and CrewAI for production.",
        sub_questions=[
            "How does each framework manage state?",
            "How scalable are the frameworks?",
        ],
        search_queries=[
            "LangGraph alternatives CrewAI producer",
            "CrewAI speed limit differences production",
        ],
        min_sources=2,
    )


def _source_summary() -> SourceSummary:
    return SourceSummary(
        source_url="https://example.org/langgraph-docs",
        key_facts=[
            "LangGraph supports persistent graph state.",
            "LangGraph is designed for production agent workflows.",
        ],
        relevance="Directly describes LangGraph features.",
        credibility_notes="Official documentation.",
    )


def _fact_check_result() -> FactCheckResult:
    return FactCheckResult(
        items=[
            FactCheckItem(
                claim="LangGraph supports persistent graph state.",
                status="supported",
                evidence_urls=["https://example.org/langgraph-docs"],
                confidence=0.9,
                rationale="Confirmed by collected documentation.",
            ),
            FactCheckItem(
                claim="CrewAI ships with an orchestrator.",
                status="partially_supported",
                evidence_urls=[],
                confidence=0.5,
                rationale="Not fully covered by collected sources.",
            ),
        ]
    )


def _research_evaluation(complete: bool) -> ResearchEvaluation:
    additional = [] if complete else ["more queries about CrewAI state"]
    return ResearchEvaluation(
        complete=complete,
        coverage=1.0 if complete else 0.5,
        source_quality=0.9,
        missing_topics=[] if complete else ["CrewAI state management"],
        additional_queries=additional,
        reason="Sufficient evidence collected." if complete else "Need more evidence.",
    )


def _report_review(acceptable: bool) -> ReportReview:
    return ReportReview(
        acceptable=acceptable,
        issues=(
            [] if acceptable else ["Add missing citation for claims without sources."]
        ),
        feedback="",
    )


class FakeProvider:
    """Canned, scriptable LLM provider."""

    def __init__(
        self,
        completions: list[str] | None = None,
        *,
        critic_complete: bool = True,
        reviewer_acceptable: bool = True,
    ) -> None:
        self.completions = list(completions or [])
        self.calls: list[str] = []
        self.critic_complete = critic_complete
        self.reviewer_acceptable = reviewer_acceptable

    async def generate(self, *, system: str, user: str, json_mode: bool = False) -> str:
        self.calls.append("generate")
        if self.completions:
            return self.completions.pop(0)
        return SAMPLE_REPORT

    async def generate_structured(
        self,
        *,
        schema: type[Any],
        system: str,
        user: str,
    ) -> Any:
        if schema is QueryAnalysis:
            self.calls.append("analyze_query")
            return _query_analysis()
        if schema is ResearchPlan:
            self.calls.append("create_research_plan")
            return _research_plan()
        if schema is SourceSummary:
            self.calls.append("analyze_source")
            return _source_summary()
        if schema is SourceSummaryList:
            self.calls.append("analyze_source_batch")
            return SourceSummaryList(summaries=[_source_summary(), _source_summary()])
        if schema is FactCheckResult:
            self.calls.append("fact_check")
            return _fact_check_result()
        if schema is ResearchEvaluation:
            self.calls.append("evaluate_research")
            return _research_evaluation(self.critic_complete)
        if schema is ReportReview:
            self.calls.append("review_report")
            return _report_review(self.reviewer_acceptable)
        raise AssertionError(f"Unexpected schema: {schema}")


class FakeSearch:
    """Returns fabricated results and records queries."""

    def __init__(self, batch: list[SearchResult] | None = None) -> None:
        self.queries: list[str] = []
        self.batch = batch or [
            SearchResult(
                title="LangGraph Docs",
                url="https://example.org/langgraph-docs",
                snippet="LangGraph concepts and API.",
                source="fake",
            ),
            SearchResult(
                title="CrewAI Guide",
                url="https://example.org/crewai-guide",
                snippet="CrewAI multi-agent roles.",
                source="fake",
            ),
        ]

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        self.queries.append(query)
        return self.batch


async def fake_fetch_source(url: str, snippet: str = "") -> dict[str, Any]:
    """Stand-in for the network fetch used by graph tests."""
    return {
        "url": url,
        "title": f"Documentation: {url}",
        "domain": "example.org",
        "snippet": snippet,
        "content": "Important factual content about the research topic.",
        "published_at": "",
        "retrieved_at": "2026-01-01T00:00:00+00:00",
    }


def fake_score_source(url: str, title: str = "") -> tuple[float, str]:
    return 0.92, "official_documentation"


__all__ = [
    "SAMPLE_REPORT",
    "FakeProvider",
    "FakeSearch",
    "fake_fetch_source",
    "fake_score_source",
    "_chunk_text",
]
