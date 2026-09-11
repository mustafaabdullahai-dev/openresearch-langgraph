"""Research API: start a research run, stream progress, and fetch results."""

from __future__ import annotations

import asyncio
import time
import uuid

from fastapi import APIRouter, HTTPException, Request

from app.graph import get_research_graph
from app.graph.state import initial_state
from app.schemas.research import (
    ResearchRequest,
    ResearchResponse,
    ResearchResultResponse,
)
from app.services.llm import LLMProviderError
from app.services.progress import (
    append_event,
    mark_complete,
    mark_error,
)
from app.services.sessions import repository as sessions

router = APIRouter(tags=["research"])

EVENT_STEP_MAP = {
    "analyze_query": "analyzing",
    "create_research_plan": "planning",
    "search_web": "searching",
    "analyze_sources": "sources",
    "fact_check": "fact-checking",
    "evaluate_research": "evaluating",
    "write_report": "reporting",
    "review_report": "reviewing",
    "finalize": "finalizing",
}


async def _run_research(thread_id: str, question: str) -> None:
    graph = get_research_graph()
    start = time.monotonic()
    try:
        initial = initial_state(question, thread_id)
        append_event(thread_id, "analyzing", "Analyzing question…")
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 60}
        # Run the graph.  As a simplification we invoke ainvoke which blocks
        # until the full graph completes.  Progress events are injected by
        # wrapping node functions (see build_nodes wrappers).
        final_state = await graph.ainvoke(initial, config)
        elapsed = time.monotonic() - start

        errors = list(final_state.get("errors", []))
        report = final_state.get("final_report", "")
        if errors and not report:
            sessions.update_session(
                thread_id,
                status="failed",
                success=False,
                error_message=errors[0],
            )
            append_event(thread_id, "error", errors[0])
            mark_error(thread_id, errors[0])
            return

        sources = final_state.get("sources", [])
        sessions.update_session(
            thread_id,
            status="completed",
            source_count=len(sources),
            iteration_count=final_state.get("research_iteration", 0),
            duration_seconds=elapsed,
            success=True,
        )
        # Store sources as rows for dashboard analytics.
        _persist_sources(thread_id, sources)

        append_event(
            thread_id, "complete", f"Research completed in {elapsed:.1f}s.", done=True
        )
        mark_complete(thread_id)
    except (LLMProviderError, Exception) as exc:
        sessions.update_session(
            thread_id, status="failed", success=False, error_message=str(exc)
        )
        mark_error(thread_id, str(exc))


def _persist_sources(thread_id: str, sources: list[dict]) -> None:
    try:
        from app.database.engine import SessionLocal
        from app.models.source import SourceRow

        with SessionLocal() as db:
            for s in sources:
                row = SourceRow(
                    thread_id=thread_id,
                    url=s.get("url", ""),
                    title=s.get("title", ""),
                    domain=s.get("domain", ""),
                    quality_score=float(s.get("quality_score", 0)),
                    quality_tier=s.get("quality_tier", ""),
                    snippet=s.get("snippet", ""),
                )
                db.add(row)
            db.commit()
    except Exception:
        pass  # non-critical analytics failure


@router.post("/api/research", response_model=ResearchResponse)
async def start_research(req: ResearchRequest, request: Request) -> ResearchResponse:
    """Start a research session and stream progress via SSE."""
    thread_id = uuid.uuid4().hex
    sessions.create_session(req.question, thread_id)
    append_event(thread_id, "started", "Research session created.")

    # fire-and-forget: streaming endpoint reads progress while this runs
    asyncio.ensure_future(_run_research(thread_id, req.question))

    return ResearchResponse(
        thread_id=thread_id,
        question=req.question,
        status="running",
        message=f"Stream at GET /api/research/{thread_id}/stream",
    )


@router.get("/api/research/{thread_id}")
async def get_research_result(thread_id: str) -> ResearchResultResponse:
    """Retrieve the final result of a completed research session."""
    session = sessions.get_session(thread_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    # Load sources from DB
    sources = _load_sources(thread_id)
    # Load final state from graph checkpointer
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = get_research_graph().get_state(config)
        values = state.values if state else {}
    except Exception:
        values = {}
    return ResearchResultResponse(
        thread_id=thread_id,
        question=session["question"],
        status=session["status"],
        final_report=values.get("final_report", ""),
        sources=sources,
        citations=values.get("citations", []),
        iterations=session.get("iteration_count", 0),
        duration_seconds=session.get("duration_seconds", 0),
    )


@router.get("/api/research/{thread_id}/sources")
async def get_sources(thread_id: str) -> list[dict]:
    return _load_sources(thread_id)


def _load_sources(thread_id: str) -> list[dict]:
    try:
        from app.database.engine import SessionLocal
        from app.models.source import SourceRow

        with SessionLocal() as db:
            rows = db.query(SourceRow).filter(SourceRow.thread_id == thread_id).all()
            return [
                {
                    "url": r.url,
                    "title": r.title,
                    "domain": r.domain,
                    "quality_score": r.quality_score,
                    "quality_tier": r.quality_tier,
                    "snippet": r.snippet,
                }
                for r in rows
            ]
    except Exception:
        return []


@router.delete("/api/research/{thread_id}")
async def delete_research(thread_id: str) -> dict:
    ok = sessions.delete_session(thread_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"status": "deleted", "thread_id": thread_id}
