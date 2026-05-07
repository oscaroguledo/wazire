from __future__ import annotations

from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from core.config import get_settings
from functools import lru_cache

from redis.asyncio import Redis


class Base(DeclarativeBase):
    pass


class PostgresDB:
    """Class-based manager for PostgreSQL (async) engines and sessions.

    Encapsulates async engine/session creation and provides `get_db()`.
    """

    _instance = None

    def __init__(self):
        self._engine = None
        self._session_factory = None

    @classmethod
    def instance(cls) -> "PostgresDB":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _database_url(self) -> Optional[str]:
        settings = get_settings()
        return settings.SQLALCHEMY_DATABASE_URI or settings.DATABASE_URL

    def engine(self):
        if self._engine is None:
            settings = get_settings()
            database_url = self._database_url()

            # When using pgbouncer in transaction pooling mode, connection
            # pooling on the client side must be minimal. The settings are
            # conservative by default but can be tuned via environment.
            pool_size = int(getattr(settings, "DB_POOL_SIZE", 10))
            max_overflow = int(getattr(settings, "DB_MAX_OVERFLOW", 20))

            self._engine = create_async_engine(
                database_url,
                echo=bool(settings.DEBUG),
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True,
                pool_recycle=int(getattr(settings, "DB_POOL_RECYCLE", 1800)),
                pool_timeout=int(getattr(settings, "DB_POOL_TIMEOUT", 30)),
                connect_args={
                    "command_timeout": int(getattr(settings, "DB_COMMAND_TIMEOUT", 60)),
                    "server_settings": {"application_name": settings.APP_NAME},
                },
            )
        return self._engine

    async def get_db(self) -> AsyncGenerator[AsyncSession, None]:
        if self._session_factory is None:
            engine = self.engine()
            self._session_factory = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
        session = self._session_factory()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def close(self) -> None:
        # Clear session factory reference
        self._session_factory = None
        # Dispose engine if initialized
        if self._engine is not None:
            try:
                await self._engine.dispose()
            except Exception:
                pass
            self._engine = None


class RedisClient:
    """Simple async Redis client manager (using redis-py asyncio)."""

    _instance = None

    def __init__(self):
        self._client: Optional[Redis] = None

    @classmethod
    def instance(cls) -> "RedisClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def client(self) -> Optional[Redis]:
        if self._client is None:
            settings = get_settings()
            redis_url = settings.REDIS_URL
            if not redis_url:
                return None
            # If password is provided separately, include it in the URL
            password = settings.REDIS_PASSWORD
            if password and "@" not in redis_url:
                # naive: prepend password if missing
                # e.g. redis://:password@host:port/0
                if redis_url.startswith("redis://"):
                    redis_url = redis_url.replace("redis://", f"redis://:{password}@", 1)
            self._client = Redis.from_url(redis_url, decode_responses=False)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:
                pass
            self._client = None


@lru_cache(maxsize=1)
def get_postgres_db() -> PostgresDB:
    return PostgresDB.instance()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    pg = get_postgres_db()
    async for s in pg.get_db():
        yield s


async def close_db() -> None:
    pg = get_postgres_db()
    await pg.close()


@lru_cache(maxsize=1)
def get_redis_client() -> Optional[Redis]:
    return RedisClient.instance().client()


async def close_redis() -> None:
    rc = RedisClient.instance()
    await rc.close()

