"""Typed LangGraph state for the research workflow.

Every node mutates a slice of this state. Reducers are attached to fields
that accumulate across research iterations (sources, claims, fact checks);
``dedupe_sources`` prevents the same URL from being collected twice.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from app.config.settings import settings


def dedupe_sources(
    existing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge sources, dropping any URL already present in ``existing``."""
    seen = {source["url"] for source in existing if source.get("url")}
    for source in incoming:
        if source.get("url") and source["url"] not in seen:
            seen.add(source["url"])
            existing.append(source)
    return existing


class ResearchState(TypedDict, total=False):
    # --- Conversation identity ---
    thread_id: str

    # --- Question understanding ---
    question: str
    query_analysis: dict[str, Any]
    research_goal: str
    research_type: str  # comparative | exploratory | descriptive | how-to | ...
    entities: list[str]
    sub_questions: list[str]

    # --- Research plan / execution ---
    search_queries: list[str]
    min_sources: int
    research_iteration: int
    max_iterations: int
    research_complete: bool

    # --- Collected evidence ---
    sources: Annotated[list[dict[str, Any]], dedupe_sources]
    analyzed_source_urls: Annotated[list[str], operator.add]
    source_summaries: Annotated[list[dict[str, Any]], operator.add]
    claims: Annotated[list[dict[str, Any]], operator.add]
    fact_checks: Annotated[list[dict[str, Any]], operator.add]
    contradictions: Annotated[list[dict[str, Any]], operator.add]
    research_notes: Annotated[list[str], operator.add]
    gaps: Annotated[list[str], operator.add]

    # --- Report ---
    draft_report: str
    review_accepted: bool
    review_feedback: Annotated[list[str], operator.add]
    revisions_remaining: int
    final_report: str
    citations: Annotated[list[dict[str, Any]], operator.add]

    # --- Failures ---
    errors: Annotated[list[str], operator.add]


def initial_state(question: str, thread_id: str | None = None) -> dict[str, Any]:
    """Return the starting state for a new research session."""
    return {
        "thread_id": thread_id or "",
        "question": question,
        "query_analysis": {},
        "sub_questions": [],
        "entities": [],
        "search_queries": [],
        "sources": [],
        "analyzed_source_urls": [],
        "source_summaries": [],
        "claims": [],
        "fact_checks": [],
        "contradictions": [],
        "research_notes": [],
        "gaps": [],
        "citations": [],
        "review_feedback": [],
        "errors": [],
        "research_iteration": 0,
        "research_complete": False,
        "review_accepted": False,
        "revisions_remaining": settings.MAX_REPORT_REVISIONS,
        "final_report": "",
    }
