"""Health-check endpoint for liveness probes and service status."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check() -> dict[str, str]:
    """Return a simple liveness response."""
    return {"status": "ok"}
