"""Repository for ResearchSession CRUD."""

from datetime import UTC
from typing import Any

from sqlalchemy import desc, select

from app.database.engine import SessionLocal
from app.models.session import ResearchSession


def create_session(question: str, thread_id: str) -> dict[str, Any]:
    with SessionLocal() as db:
        row = ResearchSession(question=question, thread_id=thread_id, status="running")
        db.add(row)
        db.commit()
        db.refresh(row)
        return {
            "thread_id": row.thread_id,
            "question": row.question,
            "status": row.status,
        }


def get_session(thread_id: str) -> dict[str, Any] | None:
    with SessionLocal() as db:
        row = db.get(ResearchSession, thread_id)
        if not row:
            return None
        return {
            "thread_id": row.thread_id,
            "question": row.question,
            "status": row.status,
            "source_count": row.source_count,
            "iteration_count": row.iteration_count,
            "duration_seconds": row.duration_seconds,
            "success": row.success,
            "created_at": row.created_at.isoformat(),
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }


def list_sessions(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    with SessionLocal() as db:
        stmt = (
            select(ResearchSession)
            .order_by(desc(ResearchSession.created_at))
            .offset(offset)
            .limit(limit)
        )
        rows = db.scalars(stmt).all()
        return [
            {
                "thread_id": r.thread_id,
                "question": r.question,
                "status": r.status,
                "source_count": r.source_count,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]


def update_session(
    thread_id: str,
    *,
    status: str | None = None,
    source_count: int | None = None,
    iteration_count: int | None = None,
    duration_seconds: float | None = None,
    success: bool | None = None,
    error_message: str | None = None,
) -> None:
    with SessionLocal() as db:
        row = db.get(ResearchSession, thread_id)
        if not row:
            return
        if status is not None:
            row.status = status
        if source_count is not None:
            row.source_count = source_count
        if iteration_count is not None:
            row.iteration_count = iteration_count
        if duration_seconds is not None:
            row.duration_seconds = duration_seconds
        if success is not None:
            row.success = success
        if error_message is not None:
            row.error_message = error_message
        if status in ("completed", "failed"):
            from datetime import datetime

            row.completed_at = datetime.now(UTC)
        db.commit()


def delete_session(thread_id: str) -> bool:
    with SessionLocal() as db:
        row = db.get(ResearchSession, thread_id)
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True
