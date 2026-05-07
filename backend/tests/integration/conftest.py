"""
Integration test fixtures.

Uses httpx.AsyncClient against the FastAPI app with a real test PostgreSQL
database (TEST_DATABASE_URL env var) and mocked Kafka/Redis.

Set TEST_DATABASE_URL in your environment before running integration tests:
  export TEST_DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/wazire_test"
"""
from __future__ import annotations

import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

# ---------------------------------------------------------------------------
# Test database setup
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/wazire_test",
)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine():
    """Create a test database engine (session-scoped)."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def db_session(test_engine):
    """Provide a transactional DB session that rolls back after each test."""
    async with test_engine.connect() as conn:
        await conn.begin()
        session_factory = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with session_factory() as session:
            yield session
            await session.rollback()


# ---------------------------------------------------------------------------
# Mock Kafka producer (prevents real Kafka connections in tests)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_kafka_producer():
    """Mock the Kafka producer so tests don't need a real Kafka broker."""
    mock_producer = AsyncMock()
    mock_producer.publish_safe = AsyncMock(return_value=True)
    mock_producer.start = AsyncMock()
    mock_producer.stop = AsyncMock()

    with patch("core.utils.kafka.producer_service", mock_producer):
        with patch("core.utils.kafka.manager.kafka_manager") as mock_manager:
            mock_manager.emit = AsyncMock(return_value=True)
            yield mock_producer


# ---------------------------------------------------------------------------
# Mock Redis (prevents real Redis connections in tests)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_redis():
    """Mock Redis client so tests don't need a real Redis instance."""
    mock_redis_client = AsyncMock()
    mock_redis_client.get = AsyncMock(return_value=None)
    mock_redis_client.set = AsyncMock(return_value=True)
    mock_redis_client.exists = AsyncMock(return_value=0)
    mock_redis_client.delete = AsyncMock(return_value=1)

    with patch("core.database.get_redis_client", return_value=mock_redis_client):
        yield mock_redis_client


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def client(db_session) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an httpx.AsyncClient against the FastAPI app with test DB."""
    from main import app
    from core.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def auth_headers(client: httpx.AsyncClient) -> dict:
    """Register and login a test user, return Authorization headers."""
    # Register
    register_resp = await client.post("/api/v1/auth/register", json={
        "first_name": "Test",
        "last_name": "User",
        "email": "testuser@integration.test",
        "password": "TestPass123!",
        "role": "student",
    })

    # Login
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "testuser@integration.test",
        "password": "TestPass123!",
    })

    if login_resp.status_code == 200:
        data = login_resp.json()
        token = data.get("data", {}).get("tokens", {}).get("access_token", "")
        return {"Authorization": f"Bearer {token}"}

    return {}


@pytest_asyncio.fixture
async def admin_auth_headers(client: httpx.AsyncClient) -> dict:
    """Register and login an admin user, return Authorization headers."""
    register_resp = await client.post("/api/v1/auth/register", json={
        "first_name": "Admin",
        "last_name": "User",
        "email": "admin@integration.test",
        "password": "AdminPass123!",
        "role": "admin",
    })

    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@integration.test",
        "password": "AdminPass123!",
    })

    if login_resp.status_code == 200:
        data = login_resp.json()
        token = data.get("data", {}).get("tokens", {}).get("access_token", "")
        return {"Authorization": f"Bearer {token}"}

    return {}
