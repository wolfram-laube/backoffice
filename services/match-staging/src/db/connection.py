"""Database connection and session management.

Supports two backends via DATABASE_URL env var:
  - SQLite:     sqlite+aiosqlite:///data/bewerbungen.db  (default)
  - PostgreSQL: postgresql+asyncpg://user:pass@host/db

Switch backends by changing DATABASE_URL — zero code changes needed.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import event

from src.db.models import Base

# Default: SQLite in local data directory
DEFAULT_DB_URL = "sqlite+aiosqlite:///data/bewerbungen.db"


def get_database_url() -> str:
    """Get database URL from env or default to SQLite."""
    url = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
    # Common Heroku/Cloud SQL pattern: postgres:// → postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def _configure_sqlite(engine: AsyncEngine) -> None:
    """Enable WAL mode and foreign keys for SQLite."""
    if "sqlite" in str(engine.url):
        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()


# --- Engine & Session Factory ---

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = get_database_url()
        _engine = create_async_engine(
            url,
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
            # SQLite doesn't support pool_size
            **({"pool_size": 5, "max_overflow": 10}
               if "postgresql" in url else {}),
        )
        _configure_sqlite(_engine)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session with automatic commit/rollback."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables. Safe to call multiple times (IF NOT EXISTS)."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Cleanup on shutdown."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
