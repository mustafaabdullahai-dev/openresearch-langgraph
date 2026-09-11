"""Streaming SSE endpoint for research progress."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.progress import (
    get_events,
    is_complete,
)

router = APIRouter(tags=["research"])


@router.get("/api/research/{thread_id}/stream")
async def stream_research(thread_id: str) -> StreamingResponse:
    """Yield Server-Sent Events as the research workflow executes."""
    seen = 0

    async def generate() -> AsyncIterator[str]:
        nonlocal seen
        while True:
            events = get_events(thread_id)
            for event in events[seen:]:
                yield f"data: {event.model_dump_json()}\n\n"
                seen += 1
            if is_complete(thread_id):
                yield 'data: {"step": "done", "message": "done"}\n\n'
                break
            await asyncio.sleep(0.25)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
