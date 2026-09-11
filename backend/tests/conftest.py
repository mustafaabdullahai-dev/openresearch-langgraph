"""Pytest configuration and shared helpers.

Environment variables are set *before* any ``app.*`` module is imported,
because settings are read once at import time.  They redirect the database
and vector store into a temporary directory so tests never touch real data.
The default search provider is DuckDuckGo and the LLM provider is fixed to
an OpenAI-compatible endpoint with an empty key so that any code that
unexpectedly reaches for a live model fails fast instead of hanging.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any

_TEST_DATA = tempfile.mkdtemp(prefix="openresearch-test-")

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DATA}/test.db"
os.environ["VECTOR_DB_PATH"] = f"{_TEST_DATA}/chroma"
os.environ["SEARCH_PROVIDER"] = "duckduckgo"
os.environ["LLM_PROVIDER"] = "openai"
os.environ["OPENAI_API_KEY"] = ""
# Fixed research-loop budget so tests stay deterministic no matter what
# settings/.env defaults are in play (runtime default favors speed: 1/1).
os.environ["MAX_RESEARCH_ITERATIONS"] = "3"
os.environ["MAX_REPORT_REVISIONS"] = "2"

from app.graph.state import initial_state  # noqa: E402
from app.graph.workflow import build_research_graph  # noqa: E402
from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from tests.fakes import (  # noqa: E402
    FakeProvider,
    FakeSearch,
    fake_fetch_source,
    fake_score_source,
)


def offline_graph(
    provider: FakeProvider,
    search: FakeSearch,
    monkeypatch_in,
    *,
    max_report_revisions: int | None = None,
) -> Any:
    """Compile a fully offline research graph wired to fakes.

    ``monkeypatch_in`` should be the :class:`pytest.MonkeyPatch` instance of
    the calling test.  ``fetch_source`` / ``score_source`` are aliased inside
    ``app.graph.nodes`` at import time, so patching the module attribute is
    all that is required.
    """
    monkeypatch_in.setattr("app.graph.nodes.fetch_source", fake_fetch_source)
    monkeypatch_in.setattr("app.graph.nodes.score_source", fake_score_source)
    return build_research_graph(
        provider,
        search,
        checkpointer=InMemorySaver(),
        max_report_revisions=max_report_revisions,
    )


def run_graph(
    graph: Any,
    question: str,
    thread_id: str = "test-thread",
    *,
    max_iterations: int | None = None,
) -> dict[str, Any]:
    """Invoke the compiled graph synchronously via ``asyncio.run``."""
    import asyncio

    state = initial_state(question, thread_id)
    if max_iterations is not None:
        state["max_iterations"] = max_iterations
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 60}
    return asyncio.run(graph.ainvoke(state, config))


__all__ = ["offline_graph", "run_graph"]
