"""Session list endpoint for the dashboard."""

from fastapi import APIRouter

from app.services.sessions import repository as sessions

router = APIRouter(tags=["sessions"])


@router.get("/api/research")
async def list_sessions(limit: int = 20, offset: int = 0) -> list[dict]:
    return sessions.list_sessions(limit=limit, offset=offset)
