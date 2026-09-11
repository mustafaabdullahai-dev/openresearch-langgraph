"""LangGraph node implementations for the research workflow.

Nodes are pure functions of ``ResearchState`` that return a partial state
dict. ``build_nodes`` binds the LLM and search providers once at graph-build
time, so nodes stay stateless with respect to external dependencies. Every
node is wrapped with :func:`_safe`, which records failures in
``state["errors"]`` rather than crashing the whole graph.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from app.agents import (
    analyze_query,
    analyze_sources_batch,
    create_research_plan,
    evaluate_research,
    fact_check,
    review_report,
)
from app.agents import report_writer as report_writer_agent
from app.config.settings import settings
from app.services.llm import LLMProvider, LLMProviderError
from app.services.search import SearchProvider
from app.services.sources import SourceFetchError, fetch_source, score_source

CallableNode = Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]
NodeFunction = CallableNode


def _safe(
    name: str,
) -> Callable[[CallableNode], NodeFunction]:
    """Wrap a node so any exception becomes an error entry, not a crash."""

    def decorate(run: CallableNode) -> NodeFunction:
        async def wrapper(state: dict[str, Any]) -> dict[str, Any]:
            try:
                return await run(state)
            except (LLMProviderError, SourceFetchError, TimeoutError) as exc:
                return {"errors": [f"{name} failed: {exc}"]}

        return wrapper

    return decorate


def build_nodes(
    provider: LLMProvider,
    search_provider: SearchProvider,
    max_report_revisions: int | None = None,
) -> dict[str, NodeFunction]:
    """Construct the node set for the research graph."""
    max_revisions = (
        max_report_revisions
        if max_report_revisions is not None
        else settings.MAX_REPORT_REVISIONS
    )
    state_max_iterations = settings.MAX_RESEARCH_ITERATIONS

    @_safe("analyze_query")
    async def analyze_query_node(state: dict[str, Any]) -> dict[str, Any]:
        result = await analyze_query(provider, state["question"])
        return {
            "query_analysis": result.model_dump(),
            "research_goal": result.research_goal,
            "research_type": result.research_type,
            "entities": result.entities,
            "sub_questions": result.sub_questions,
        }

    @_safe("create_research_plan")
    async def create_research_plan_node(state: dict[str, Any]) -> dict[str, Any]:
        from app.agents.schemas import QueryAnalysis

        analysis_data = state.get("query_analysis") or {}
        analysis = QueryAnalysis(
            research_goal=state.get("research_goal", state["question"]),
            research_type=analysis_data.get("research_type") or "exploratory",
            entities=state.get("entities", []) or [],
            sub_questions=state.get("sub_questions", []) or [state["question"]],
        )
        plan = await create_research_plan(provider, state["question"], analysis)
        return {
            "search_queries": plan.search_queries,
            "min_sources": plan.min_sources,
            "max_iterations": state.get("max_iterations") or state_max_iterations,
            "research_notes": [f"Plan: {plan.objective}"],
        }

    @_safe("search_web")
    async def search_web_node(state: dict[str, Any]) -> dict[str, Any]:
        queries = state.get("search_queries", [])
        max_results = settings.MAX_SEARCH_RESULTS
        known_urls = {s.get("url") for s in state.get("sources", [])}
        new_sources: list[dict[str, Any]] = []
        errors: list[str] = []

        if queries:
            # Space out DuckDuckGo calls: it rate-limits/returns junk when
            # hammered with concurrent requests from one IP.
            results_per_query: list[Any] = [None] * len(queries)
            for index, query in enumerate(queries):
                try:
                    results_per_query[index] = await search_provider.search(
                        query, max_results=max_results
                    )
                except BaseException as exc:  # noqa: BLE001 - recorded, not fatal
                    results_per_query[index] = exc
            for query, batch in zip(queries, results_per_query, strict=False):
                if isinstance(batch, BaseException):
                    errors.append(f"Search failed for '{query}': {batch}")
                    continue
                for item in batch:
                    url = item.url
                    if not url or url in known_urls:
                        continue
                    known_urls.add(url)
                    new_sources.append(
                        {
                            "url": url,
                            "title": item.title or url,
                            "domain": "",
                            "snippet": item.snippet,
                            "source": item.source,
                        }
                    )

        patch: dict[str, Any] = {
            "research_iteration": state.get("research_iteration", 0) + 1,
            "sources": new_sources,
        }
        if errors:
            patch["errors"] = errors
        patch.setdefault("research_notes", []).append(
            f"Found {len(new_sources)} new source(s) in iteration "
            f"{state.get('research_iteration', 0) + 1}."
        )
        return patch

    @_safe("analyze_sources")
    async def analyze_sources_node(state: dict[str, Any]) -> dict[str, Any]:
        sources = state.get("sources", [])
        already = set(state.get("analyzed_source_urls", []))
        pending = [s for s in sources if s.get("url") not in already]

        summaries: list[dict[str, Any]] = []
        claims: list[dict[str, Any]] = []
        errors: list[str] = []

        # Fetch + score every pending source concurrently, then run ONE batched
        # LLM analysis call so N sources cost a single round-trip to the model.
        if pending:
            fetched_tasks = [
                fetch_source(s["url"], snippet=s.get("snippet", "")) for s in pending
            ]
            fetched = await asyncio.gather(*fetched_tasks, return_exceptions=True)
            ready: list[dict[str, Any]] = []
            for source, result in zip(pending, fetched, strict=False):
                if isinstance(result, BaseException):
                    errors.append(f"Could not fetch {source['url']}: {result}")
                    continue
                score, tier = score_source(source["url"], result.get("title", ""))
                source.update(result)
                source["quality_score"] = score
                source["quality_tier"] = tier
                ready.append(source)

            if ready:
                ready = ready[: settings.MAX_SOURCES_ANALYZED]
                parsed_items = await analyze_sources_batch(
                    provider, state["question"], ready
                )
                for source, parsed in zip(ready, parsed_items, strict=False):
                    summaries.append(
                        {
                            "source_url": parsed.source_url,
                            "key_facts": parsed.key_facts,
                            "relevance": parsed.relevance,
                            "credibility_notes": parsed.credibility_notes,
                        }
                    )
                    claims.extend(
                        {
                            "claim_text": fact,
                            "source_url": source["url"],
                            "source_title": source.get("title", ""),
                        }
                        for fact in parsed.key_facts
                    )

        patch: dict[str, Any] = {
            "analyzed_source_urls": [s["url"] for s in pending],
            "source_summaries": summaries,
            "claims": claims,
            "research_notes": [f"Analyzed {len(pending)} source(s)."],
        }
        if errors:
            patch["errors"] = errors
        return patch

    @_safe("fact_check")
    async def fact_check_node(state: dict[str, Any]) -> dict[str, Any]:
        claims = state.get("claims", [])
        if not claims:
            return {"fact_checks": [], "contradictions": []}

        summary_by_url = {
            s.get("source_url"): s for s in state.get("source_summaries", [])
        }
        enriched = [
            {
                "claim_text": claim.get("claim_text", ""),
                "source_urls": [claim.get("source_url", "")],
                "evidence_excerpt": summary_by_url.get(
                    claim.get("source_url", ""), {}
                ).get("relevance", ""),
            }
            for claim in claims
        ]
        items = await fact_check(provider, state["question"], enriched)

        fact_checks: list[dict[str, Any]] = []
        contradictions: list[dict[str, Any]] = []
        for item in items:
            fact_checks.append(
                {
                    "claim": item.claim,
                    "status": item.status,
                    "evidence_urls": item.evidence_urls,
                    "confidence": item.confidence,
                    "rationale": item.rationale,
                }
            )
            if item.status == "contradicted":
                contradictions.append(
                    {
                        "claim": item.claim,
                        "description": (
                            f"'{item.claim}' is contradicted by collected evidence."
                        ),
                        "evidence_urls": item.evidence_urls,
                    }
                )
        return {"fact_checks": fact_checks, "contradictions": contradictions}

    @_safe("evaluate_research")
    async def evaluate_research_node(state: dict[str, Any]) -> dict[str, Any]:
        iteration = state.get("research_iteration", 0)
        max_iterations = state.get("max_iterations") or settings.MAX_RESEARCH_ITERATIONS
        if iteration >= max_iterations:
            return {
                "research_complete": True,
                "gaps": ["Maximum research iterations reached."],
                "research_notes": [
                    "Iteration limit reached; proceeding with best evidence."
                ],
            }

        evaluation = await evaluate_research(
            provider,
            state["question"],
            state.get("sub_questions", []),
            state.get("sources", []),
            state.get("gaps", []),
            state.get("contradictions", []),
            iteration,
            max_iterations,
        )
        patch: dict[str, Any] = {
            "research_complete": evaluation.complete,
            "gaps": evaluation.missing_topics,
            "research_notes": [f"Critic: {evaluation.reason}"],
        }
        if not evaluation.complete and evaluation.additional_queries:
            patch["search_queries"] = evaluation.additional_queries
        return patch

    @_safe("write_report")
    async def write_report_node(state: dict[str, Any]) -> dict[str, Any]:
        sources = state.get("sources", [])
        summary_by_url = {
            s.get("source_url"): s for s in state.get("source_summaries", [])
        }
        evidence_sources = [
            dict(s, **summary_by_url.get(s.get("url"), {})) for s in sources
        ]
        feedback = state.get("review_feedback", [])
        revision_feedback = feedback[-1] if feedback else None
        previous_draft = state.get("draft_report") if revision_feedback else None

        draft = await report_writer_agent.write_report(
            provider,
            state["question"],
            state.get("sub_questions", []) or [state["question"]],
            evidence_sources,
            state.get("fact_checks", []),
            revision_feedback=revision_feedback,
            previous_draft=previous_draft,
        )
        return {
            "draft_report": draft,
            "research_notes": [
                f"Report {'revised' if revision_feedback else 'drafted'}."
            ],
        }

    @_safe("review_report")
    async def review_report_node(state: dict[str, Any]) -> dict[str, Any]:
        if not state.get("draft_report"):
            return {"review_accepted": True, "final_report": ""}
        result = await review_report(
            provider,
            state["question"],
            state["draft_report"],
            state.get("contradictions", []),
        )
        patch: dict[str, Any] = {
            "review_accepted": bool(result.acceptable),
            "research_notes": [
                "Reviewer: accepted"
                if result.acceptable
                else "Reviewer: revisions needed"
            ],
        }
        if not result.acceptable:
            patch["review_feedback"] = [result.feedback] if result.feedback else []
            patch["revisions_remaining"] = max(
                0, int(state.get("revisions_remaining", max_revisions)) - 1
            )
        return patch

    @_safe("finalize")
    async def finalize_node(state: dict[str, Any]) -> dict[str, Any]:
        sources = state.get("sources", [])
        citations = [
            {
                "id": f"S{index}",
                "title": source.get("title", "Untitled"),
                "url": source.get("url", ""),
                "domain": source.get("domain", ""),
            }
            for index, source in enumerate(sources, start=1)
        ]
        return {
            "research_complete": True,
            "final_report": state.get("draft_report", ""),
            "citations": citations,
        }

    return {
        "analyze_query": analyze_query_node,
        "create_research_plan": create_research_plan_node,
        "search_web": search_web_node,
        "analyze_sources": analyze_sources_node,
        "fact_check": fact_check_node,
        "evaluate_research": evaluate_research_node,
        "write_report": write_report_node,
        "review_report": review_report_node,
        "finalize": finalize_node,
    }


__all__ = ["build_nodes", "NodeFunction"]
