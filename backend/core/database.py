from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from functools import lru_cache

from core.config import get_settings

# Global engine and session factory (initialized lazily)
_engine = None
_AsyncSessionLocal = None


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


def get_session_factory():
    """Get or create the async session factory."""
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        engine = get_engine()
        _AsyncSessionLocal = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
    return _AsyncSessionLocal


async def get_db() -> AsyncSession:
    """Async session dependency for FastAPI endpoints.

    Usage in FastAPI:
        async def endpoint(db: AsyncSession = Depends(get_db)):
            async with db.begin():
                ...
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()


async def init_db() -> None:
    """Create database tables (run on startup if needed)."""
    # Ensure all model modules are imported so SQLAlchemy has registered them
    # before creating tables. Importing here avoids requiring other modules
    # to eagerly import models just for metadata registration.
    try:
        import importlib

        importlib.import_module("models.account.users")
        importlib.import_module("models.account.tenant")
        importlib.import_module("models.account.oauth")
        importlib.import_module("models.billings.invoice")
        importlib.import_module("models.billings.usage")
        importlib.import_module("models.billings.paymentmethod")
        importlib.import_module("models.academic.course")
        importlib.import_module("models.academic.enrollment")
        importlib.import_module("models.academic.exam")
        importlib.import_module("models.academic.question")
        importlib.import_module("models.academic.submission")
        importlib.import_module("models.academic.student_answer")
        importlib.import_module("models.analytics.dashboard")
    except Exception:
        pass

    engine = get_engine()

    # For SQLite, SQLAlchemy table schemas (e.g. 'auth') are not supported
    # — strip schema names so tables are created without schema prefix.
    dialect_name = engine.dialect.name

    if dialect_name == "sqlite":
        for tbl in list(Base.metadata.tables.values()):
            if getattr(tbl, "schema", None):
                tbl.schema = None

    async with engine.begin() as conn:
        # For PostgreSQL-like databases, ensure schemas exist before create_all
        if dialect_name in ("postgresql", "postgres"):
            schemas = {t.schema for t in Base.metadata.tables.values() if t.schema}
            for schema in schemas:
                if schema:
                    await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))

        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections (for graceful shutdown)."""
    global _engine, _AsyncSessionLocal
    if _engine:
        await _engine.dispose()
        _engine = None
        _AsyncSessionLocal = None