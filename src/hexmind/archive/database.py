"""Database engine setup: async session factory and lifecycle."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from hexmind.archive.db_models import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db(database_url: str, *, echo: bool = False) -> None:
    """Initialize the async engine and create tables if needed."""
    global _engine, _session_factory

    _engine = create_async_engine(database_url, echo=echo)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose of the engine."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the configured session factory. Raises if not initialized."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _session_factory


async def get_session():
    """FastAPI dependency: yield an async session.

    Raises HTTPException(503) when the database has not been initialized,
    giving callers a clear signal instead of an opaque 500 error.
    """
    if _session_factory is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Database not configured. Set DATABASE_URL to enable this feature.",
        )
    async with _session_factory() as session:
        yield session
