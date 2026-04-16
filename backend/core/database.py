from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from core.config import get_settings
from functools import lru_cache

# Global engine and session factory (initialized lazily)
_engine = None
_session_factory = None


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

