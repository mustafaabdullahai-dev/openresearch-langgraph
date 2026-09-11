"""OpenResearch — FastAPI entrypoint.

Wires routers, initialises the database on startup, and enables CORS
so the React frontend can reach the API in development.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    chat,
    documents,
    health,
    models,
    research,
    sessions,
    stream,
)
from app.config.settings import settings
from app.database.engine import init_db


def _cors_origins() -> list[str]:
    """Parse the allowed-origins list from settings (no wildcard with cookies)."""
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    return origins or ["http://localhost:5173"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(
    title="OpenResearch API",
    description=(
        "Backend for OpenResearch, an open-source multi-agent AI research "
        "assistant built with LangGraph and local LLMs."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(models.router)
app.include_router(research.router)
app.include_router(sessions.router)
app.include_router(stream.router)
app.include_router(chat.router)
app.include_router(documents.router)
