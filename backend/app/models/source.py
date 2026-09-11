"""Source ORM model — stores individual collected sources."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SourceRow(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[str] = mapped_column(String(64), index=True)
    url: Mapped[str] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(Text, default="")
    domain: Mapped[str] = mapped_column(String(256), default="")
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    quality_tier: Mapped[str] = mapped_column(String(64), default="")
    snippet: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
