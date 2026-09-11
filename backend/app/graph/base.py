"""Simplest LangGraph skeleton: START -> one node -> END.

Used to verify that the graph compiles and executes with the typed state
before the full agent workflow is attached in later phases.
"""

from __future__ import annotations

from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from .state import ResearchState

_NODE = "ping"


def _ping(state: dict) -> dict:
    """Baseline node: records that the graph executed."""
    return {"research_notes": ["graph skeleton executed"]}


def build_base_graph() -> Any:
    """Compile the trivial skeleton graph used to smoke-test tooling."""
    builder = StateGraph(ResearchState)
    builder.add_node(_NODE, cast(Any, _ping))
    builder.add_edge(START, _NODE)
    builder.add_edge(_NODE, END)
    return builder.compile()


graph = build_base_graph()
