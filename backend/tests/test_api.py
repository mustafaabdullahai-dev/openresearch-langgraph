"""API tests using FastAPI's TestClient and backend fakes.

The research graph is swapped in via monkeypatch so no live model is ever
contacted, except for the dedicated degraded-mode tests that assert the
system fails gracefully when the HF inference backend is unreachable
(empty HF_TOKEN in the test environment).
"""

from __future__ import annotations

import time

import pytest
from app.main import app
from app.services.progress import append_event, mark_complete
from fastapi.testclient import TestClient
from tests.conftest import offline_graph
from tests.fakes import FakeProvider, FakeSearch

QUESTION = "Compare LangGraph and CrewAI for production AI agents."
GRADED_QUESTION = "How do OLED panels age over time?"


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def offline_graph_patch(monkeypatch):
    """Point every graph consumer at a single offline graph instance."""
    graph = offline_graph(
        FakeProvider(), FakeSearch(), monkeypatch, max_report_revisions=1
    )
    monkeypatch.setattr("app.api.routes.research.get_research_graph", lambda: graph)
    monkeypatch.setattr("app.graph.get_research_graph", lambda: graph)
    monkeypatch.setattr("app.api.routes.chat.answer_follow_up", _fake_follow_up)


async def _fake_follow_up(provider, question, report, sources, message) -> str:
    return f"Follow-up answer for: {message}"


def test_health(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_model_status_reports_unavailable_when_hf_token_missing(client) -> None:
    # Test env has an empty HF_TOKEN, so the HF provider raises on connect.
    response = client.get("/api/models/status")
    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is False
    assert body["provider"] == "hf"


def _wait_for_status(client: TestClient, thread_id: str, statuses: set[str]) -> str:
    for _ in range(60):
        response = client.get(f"/api/research/{thread_id}")
        assert response.status_code == 200
        body = response.json()
        if body["status"] in statuses:
            return body["status"]
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for status in {statuses}")


def test_research_lifecycle(client, offline_graph_patch) -> None:
    response = client.post("/api/research", json={"question": QUESTION})
    assert response.status_code == 200
    thread_id = response.json()["thread_id"]
    assert response.json()["status"] == "running"

    status = _wait_for_status(client, thread_id, {"completed", "failed"})
    assert status == "completed"

    result = client.get(f"/api/research/{thread_id}").json()
    assert "Executive Summary" in result["final_report"]
    assert result["status"] == "completed"
    assert len(result["sources"]) == 2
    assert result["iterations"] == 1


def test_research_sources_endpoint(client, offline_graph_patch) -> None:
    response = client.post("/api/research", json={"question": QUESTION})
    thread_id = response.json()["thread_id"]
    _wait_for_status(client, thread_id, {"completed", "failed"})

    sources = client.get(f"/api/research/{thread_id}/sources").json()
    assert isinstance(sources, list)
    assert len(sources) == 2
    assert all(s["quality_score"] > 0 for s in sources)


def test_chat_follow_up_on_completed_research(client, offline_graph_patch) -> None:
    response = client.post("/api/research", json={"question": QUESTION})
    thread_id = response.json()["thread_id"]
    _wait_for_status(client, thread_id, {"completed", "failed"})

    chat = client.post(
        f"/api/research/{thread_id}/chat", json={"message": "Expand on state?"}
    )
    assert chat.status_code == 200
    assert chat.json()["response"] == "Follow-up answer for: Expand on state?"


def test_chat_flow_uses_real_provider_and_returns_503(
    client, offline_graph_patch, monkeypatch
) -> None:
    import app.api.routes.chat as chat_routes

    async def _raise_unavailable(provider, question, report, sources, message) -> str:
        from app.services.llm import LLMUnavailableError

        raise LLMUnavailableError("simulated down")

    monkeypatch.setattr(chat_routes, "answer_follow_up", _raise_unavailable)
    response = client.post("/api/research", json={"question": QUESTION})
    thread_id = response.json()["thread_id"]
    _wait_for_status(client, thread_id, {"completed", "failed"})

    chat = client.post(
        f"/api/research/{thread_id}/chat", json={"message": "Any follow up"}
    )
    assert chat.status_code == 503


def test_delete_research(client, offline_graph_patch) -> None:
    response = client.post("/api/research", json={"question": QUESTION})
    thread_id = response.json()["thread_id"]
    _wait_for_status(client, thread_id, {"completed", "failed"})

    deleted = client.delete(f"/api/research/{thread_id}")
    assert deleted.status_code == 200
    response = client.delete(f"/api/research/{thread_id}")
    assert response.status_code == 404


def test_research_sse_stream(client) -> None:
    thread_id = "sse-progress"
    append_event(thread_id, "analyzing", "Analyzing question…")
    append_event(thread_id, "searching", "Searching web…")
    mark_complete(thread_id)

    with client.stream("GET", f"/api/research/{thread_id}/stream") as stream:
        assert stream.status_code == 200
        data = stream.iter_lines()
        lines = [line for line in data if line.startswith("data: ")]
    payloads = [line[len("data: ") :] for line in lines]
    concat = "|".join(payloads)
    assert '"step":"analyzing"' in concat
    assert '"step":"searching"' in concat
    assert '"step": "done"' in concat


def test_sessions_listing(client, offline_graph_patch) -> None:
    client.post("/api/research", json={"question": QUESTION})
    client.post("/api/research", json={"question": "Second question"})

    listed = client.get("/api/research").json()
    assert isinstance(listed, list)
    assert len(listed) >= 2
    assert all("thread_id" in row for row in listed)


def test_degraded_research_marks_session_failed_when_model_unavailable(
    client, monkeypatch
) -> None:
    class _DownProvider:
        async def generate(self, **kwargs) -> str:
            from app.services.llm import LLMUnavailableError

            raise LLMUnavailableError("model is down")

        async def generate_structured(self, **kwargs) -> object:
            from app.services.llm import LLMUnavailableError

            raise LLMUnavailableError("model is down")

    graph = offline_graph(
        _DownProvider(), FakeSearch(), monkeypatch, max_report_revisions=1
    )
    monkeypatch.setattr("app.api.routes.research.get_research_graph", lambda: graph)
    monkeypatch.setattr("app.graph.get_research_graph", lambda: graph)

    response = client.post("/api/research", json={"question": GRADED_QUESTION})
    thread_id = response.json()["thread_id"]

    status = _wait_for_status(client, thread_id, {"completed", "failed"})
    assert status == "failed"
    result = client.get(f"/api/research/{thread_id}").json()
    assert result["status"] == "failed"
    assert result["final_report"] == ""
