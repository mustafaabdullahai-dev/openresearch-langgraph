"""LangGraph singleton factory — compiled once, reused across requests."""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from app.services.llm import OllamaLLMProvider

_checkpointer = InMemorySaver()
_provider = OllamaLLMProvider()

_graph = None


def get_research_graph() -> Any:
    """Return the compiled research graph, building it on first call."""
    global _graph  # noqa: PLW0603
    if _graph is None:
        from app.graph.workflow import build_research_graph

        _graph = build_research_graph(
            provider=_provider,
            checkpointer=_checkpointer,
        )
    return _graph


def rebuild_graph() -> Any:
    """Force a fresh graph build (used after settings change)."""
    global _graph  # noqa: PLW0603
    from app.graph.workflow import build_research_graph

    _graph = build_research_graph(provider=_provider, checkpointer=_checkpointer)
    return _graph
