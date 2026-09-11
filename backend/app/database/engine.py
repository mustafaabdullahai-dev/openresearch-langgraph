"""SQLAlchemy engine and session management.

Uses synchronous SQLite for simplicity; swap engine + sessionmaker to
``create_async_engine`` for PostgreSQL later.
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings

_engine_url = settings.DATABASE_URL
_db_path = _engine_url.split("sqlite:///")[-1]

engine = create_engine(
    _engine_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in _engine_url else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables if they do not exist yet."""
    Path(_db_path).parent.mkdir(parents=True, exist_ok=True)
    from app.models.base import Base  # noqa: F811
    from app.models.document import Document  # noqa: F401
    from app.models.message import Message  # noqa: F401
    from app.models.session import ResearchSession  # noqa: F401
    from app.models.source import SourceRow  # noqa: F401

    Base.metadata.create_all(bind=engine)
