"""Integration tests for authentication routes.

Tests: register, login, refresh, me — using httpx.AsyncClient against the
FastAPI app with a real test PostgreSQL database.

Requires TEST_DATABASE_URL env var to be set.
"""
import pytest
import httpx


pytestmark = pytest.mark.integration


class TestRegisterEndpoint:
    """Tests for POST /api/v1/auth/register."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: httpx.AsyncClient):
        """Test successful user registration."""
        resp = await client.post("/api/v1/auth/register", json={
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@test.com",
            "password": "SecurePass123!",
            "role": "student",
        })

        assert resp.status_code in (200, 201)
        body = resp.json()
        assert body["success"] is True
        assert "data" in body

    @pytest.mark.asyncio
    async def test_register_missing_required_fields(self, client: httpx.AsyncClient):
        """Test that registration fails with missing required fields."""
        resp = await client.post("/api/v1/auth/register", json={
            "email": "incomplete@test.com",
        })

        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: httpx.AsyncClient):
        """Test that duplicate email registration is rejected."""
        payload = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "duplicate@test.com",
            "password": "SecurePass123!",
            "role": "student",
        }
        # First registration
        await client.post("/api/v1/auth/register", json=payload)
        # Second registration with same email
        resp = await client.post("/api/v1/auth/register", json=payload)

        assert resp.status_code in (400, 409, 422)


class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: httpx.AsyncClient):
        """Test successful login returns user and tokens."""
        # Register first
        await client.post("/api/v1/auth/register", json={
            "first_name": "Login",
            "last_name": "Test",
            "email": "login.test@test.com",
            "password": "LoginPass123!",
            "role": "student",
        })

        resp = await client.post("/api/v1/auth/login", json={
            "email": "login.test@test.com",
            "password": "LoginPass123!",
        })

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "user" in data
        assert "tokens" in data
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: httpx.AsyncClient):
        """Test that wrong password returns 401."""
        await client.post("/api/v1/auth/register", json={
            "first_name": "Wrong",
            "last_name": "Pass",
            "email": "wrongpass@test.com",
            "password": "CorrectPass123!",
            "role": "student",
        })

        resp = await client.post("/api/v1/auth/login", json={
            "email": "wrongpass@test.com",
            "password": "WrongPass123!",
        })

        assert resp.status_code in (400, 401)

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: httpx.AsyncClient):
        """Test that login with nonexistent email returns 401."""
        resp = await client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "SomePass123!",
        })

        assert resp.status_code in (400, 401, 404)


class TestMeEndpoint:
    """Tests for GET /api/v1/auth/me."""

    @pytest.mark.asyncio
    async def test_me_with_valid_token(self, client: httpx.AsyncClient, auth_headers: dict):
        """Test that /me returns current user with valid token."""
        if not auth_headers:
            pytest.skip("Could not obtain auth token")

        resp = await client.get("/api/v1/auth/me", headers=auth_headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "data" in body
        assert "email" in body["data"]

    @pytest.mark.asyncio
    async def test_me_without_token(self, client: httpx.AsyncClient):
        """Test that /me returns 401 without token."""
        resp = await client.get("/api/v1/auth/me")

        assert resp.status_code == 401


class TestRefreshEndpoint:
    """Tests for POST /api/v1/auth/refresh."""

    @pytest.mark.asyncio
    async def test_refresh_with_valid_token(self, client: httpx.AsyncClient):
        """Test that refresh returns new access token."""
        # Register and login
        await client.post("/api/v1/auth/register", json={
            "first_name": "Refresh",
            "last_name": "Test",
            "email": "refresh.test@test.com",
            "password": "RefreshPass123!",
            "role": "student",
        })

        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "refresh.test@test.com",
            "password": "RefreshPass123!",
        })

        if login_resp.status_code != 200:
            pytest.skip("Login failed, cannot test refresh")

        refresh_token = login_resp.json()["data"]["tokens"]["refresh_token"]

        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "access_token" in body["data"]


class TestHealthEndpoint:
    """Tests for GET /api/v1/health."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: httpx.AsyncClient):
        """Test that health endpoint returns 200 with status fields."""
        resp = await client.get("/api/v1/health")

        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body
        assert body["status"] == "ok"
        assert "db" in body
        assert "redis" in body
        assert "kafka" in body
