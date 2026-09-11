"""LangGraph workflow construction for the research pipeline.

Flow design (matching the master-prompt loop):

    START
      -> analyze_query
      -> create_research_plan
      -> search_web
      -> analyze_sources
      -> fact_check
      -> evaluate_research        (critic)
            -> enough OR at_iteration_limit -> write_report
            -> not enough                  -> search_web  (loop)
      -> write_report
      -> review_report            (reviewer)
            -> acceptable                 -> finalize
            -> needs revision, attempts left -> write_report (loop)
            -> needs revision, no attempts   -> finalize
      -> finalize
      -> END
"""

from __future__ import annotations

from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from app.config.settings import settings
from app.services.llm import LLMProvider
from app.services.search import create_search_provider

from .nodes import NodeFunction, build_nodes
from .state import ResearchState


def _route_after_critic(state: dict[str, Any]) -> str:
    """Enough evidence, or no budget left to keep searching => report."""
    if state.get("research_complete"):
        return "write_report"
    if state.get("research_iteration", 0) >= state.get(
        "max_iterations", settings.MAX_RESEARCH_ITERATIONS
    ):
        return "write_report"
    if not state.get("search_queries"):
        return "write_report"
    return "search_web"


def _route_after_reviewer(state: dict[str, Any]) -> str:
    """Accepted report, or no revision budget left => finalize."""
    if state.get("review_accepted"):
        return "finalize"
    if state.get("revisions_remaining", 0) > 0:
        return "write_report"
    return "finalize"


def build_research_graph(
    provider: LLMProvider,
    search_provider: Any = None,
    checkpointer: Any = None,
    max_report_revisions: int | None = None,
) -> Any:
    """Compile the research workflow.

    Args:
        provider: the configured LLM provider (Ollama by default).
        search_provider: optional pre-built search provider; built from
            settings when omitted.
        checkpointer: optional LangGraph checkpointer for persistence.
        max_report_revisions: override for the reporter revision budget.
    """
    if search_provider is None:
        search_provider = create_search_provider()

    nodes: dict[str, NodeFunction] = build_nodes(
        provider,
        search_provider,
        max_report_revisions=max_report_revisions,
    )

    builder = StateGraph(ResearchState)
    for name, node in nodes.items():
        builder.add_node(name, cast(Any, node))

    builder.add_edge(START, "analyze_query")
    builder.add_edge("analyze_query", "create_research_plan")
    builder.add_edge("create_research_plan", "search_web")
    builder.add_edge("search_web", "analyze_sources")
    builder.add_edge("analyze_sources", "fact_check")
    builder.add_edge("fact_check", "evaluate_research")
    builder.add_conditional_edges(
        "evaluate_research",
        _route_after_critic,
        {"write_report": "write_report", "search_web": "search_web"},
    )
    builder.add_edge("write_report", "review_report")
    builder.add_conditional_edges(
        "review_report",
        _route_after_reviewer,
        {"finalize": "finalize", "write_report": "write_report"},
    )
    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer)


__all__ = [
    "build_research_graph",
    "_route_after_critic",
    "_route_after_reviewer",
]
