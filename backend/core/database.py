from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy import create_engine

from core.config import get_settings
from functools import lru_cache

# Global engine and session factory (initialized lazily)
_engine = None
_session_factory = None
_sync_engine = None
_sync_session_factory = None


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=1)
def get_engine():
    """Get or create the async engine singleton with proper connection pooling."""
    global _engine
    if _engine is None:
        settings = get_settings()
        database_url = settings.SQLALCHEMY_DATABASE_URI or settings.DATABASE_URL

        # Configure connection pool for production (optimized for Supabase)
        _engine = create_async_engine(
            database_url,
            echo=bool(settings.DEBUG),
            pool_size=20,  # Increased from 10 to keep more connections ready
            max_overflow=30,  # Increased from 20 for more burst capacity
            pool_pre_ping=True,  # Test connections before using (reliability)
            pool_recycle=1800,  # Reduced from 3600 to 30 minutes (faster recycling)
            pool_timeout=30,  # Timeout after 30 seconds if no connection available
            connect_args={
                "command_timeout": 60,  # Command timeout in seconds
                "server_settings": {"application_name": "wazire"},  # Identify connection in Supabase
            },
        )
    return _engine


@lru_cache(maxsize=1)
def get_sync_engine():
    """Get or create the synchronous engine singleton for Celery tasks."""
    global _sync_engine
    if _sync_engine is None:
        settings = get_settings()
        database_url = settings.SQLALCHEMY_DATABASE_URI or settings.DATABASE_URL

        # Convert async URL to sync URL for Celery
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        sync_url = sync_url.replace("sqlite+aiosqlite://", "sqlite://")

        _sync_engine = create_engine(
            sync_url,
            echo=bool(settings.DEBUG),
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_timeout=30,
        )
    return _sync_engine


def get_sync_db():
    """Get synchronous database session for Celery tasks."""
    global _sync_session_factory
    if _sync_session_factory is None:
        engine = get_sync_engine()
        _sync_session_factory = sessionmaker(
            bind=engine,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
    session = _sync_session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def get_db() -> AsyncSession:
    """Get database session (merged with session factory creation).

    Usage in FastAPI:
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    
    Usage in Celery/tasks:
        async with get_db() as db:
            # use AsyncSession `db`
    """
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
    session = _session_factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def close_db() -> None:
    """Dispose the async engine and clear the session factory.

    Intended for use during application shutdown to close all pooled
    connections cleanly.
    """
    global _engine, _session_factory
    # Clear session factory reference
    _session_factory = None

    # Dispose engine if initialized
    if _engine is not None:
        try:
            await _engine.dispose()
        except Exception:
            # Best-effort dispose; ignore errors during shutdown
            pass
        _engine = None

