"""Unit tests for the health check endpoint."""
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock


async def _get_client():
    """Create a test client for the FastAPI app with mocked dependencies."""
    from main import app
    from core.database import get_db

    async def mock_get_db():
        db = AsyncMock()
        db.execute = AsyncMock()
        yield db

    app.dependency_overrides[get_db] = mock_get_db

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


class TestHealthEndpoint:
    async def test_health_returns_200(self):
        """GET /api/v1/health always returns HTTP 200."""
        from main import app
        from core.database import get_db

        async def mock_get_db():
            db = AsyncMock()
            db.execute = AsyncMock()
            yield db

        app.dependency_overrides[get_db] = mock_get_db

        with patch("routes.health.get_db", mock_get_db):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/v1/health")

        app.dependency_overrides.clear()
        assert resp.status_code == 200

    async def test_health_response_has_required_keys(self):
        """Health response includes status, db, redis, kafka keys."""
        from main import app
        from core.database import get_db

        async def mock_get_db():
            db = AsyncMock()
            db.execute = AsyncMock()
            yield db

        app.dependency_overrides[get_db] = mock_get_db

        with patch("routes.health.get_db", mock_get_db):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/v1/health")

        app.dependency_overrides.clear()
        body = resp.json()
        assert "status" in body
        assert "db" in body
        assert "redis" in body
        assert "kafka" in body
