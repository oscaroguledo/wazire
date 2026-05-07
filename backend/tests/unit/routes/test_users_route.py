"""Unit tests for /api/v1/auth routes — mocked DB and services."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx

from main import app
from core.database import get_db
from models.account.users import User, UserRole


def _make_user(**kwargs) -> User:
    return User(
        id=kwargs.get("id", uuid.uuid4()),
        first_name=kwargs.get("first_name", "Test"),
        last_name=kwargs.get("last_name", "User"),
        email=kwargs.get("email", "test@example.com"),
        password=kwargs.get("password", "pbkdf2_sha256$200000$abc$def"),
        role=kwargs.get("role", UserRole.STUDENT),
        tenant_id=kwargs.get("tenant_id", uuid.uuid4()),
        is_active=kwargs.get("is_active", True),
        is_deleted=kwargs.get("is_deleted", False),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _mock_db_session():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


async def _get_test_client(db_session=None):
    if db_session is None:
        db_session = _mock_db_session()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    )
    return client, db_session


class TestRegisterEndpoint:
    async def test_register_superadmin_blocked(self):
        client, db = await _get_test_client()
        async with client:
            resp = await client.post("/api/v1/auth/register", json={
                "first_name": "Super",
                "last_name": "Admin",
                "email": "super@test.com",
                "password": "SecurePass123!",
                "role": "superadmin",
            })
        app.dependency_overrides.clear()
        assert resp.status_code == 403

    async def test_register_student_without_tenant_code_fails(self):
        client, db = await _get_test_client()
        async with client:
            resp = await client.post("/api/v1/auth/register", json={
                "first_name": "Alice",
                "last_name": "Smith",
                "email": "alice@test.com",
                "password": "SecurePass123!",
                "role": "student",
            })
        app.dependency_overrides.clear()
        assert resp.status_code == 400

    async def test_register_duplicate_email_fails(self):
        db = _mock_db_session()
        existing_user = _make_user(email="existing@test.com")
        # The register route for admin role: first checks existing user by email
        found_user = MagicMock()
        found_user.scalar_one_or_none.return_value = existing_user
        db.execute.return_value = found_user

        client, _ = await _get_test_client(db)
        async with client:
            resp = await client.post("/api/v1/auth/register", json={
                "first_name": "Alice",
                "last_name": "Smith",
                "email": "existing@test.com",
                "password": "SecurePass123!",
                "role": "admin",
            })
        app.dependency_overrides.clear()
        assert resp.status_code == 400


class TestLoginEndpoint:
    async def test_login_missing_email_fails(self):
        client, db = await _get_test_client()
        async with client:
            resp = await client.post("/api/v1/auth/login", json={
                "password": "password123",
            })
        app.dependency_overrides.clear()
        assert resp.status_code == 422  # Pydantic validation error

    async def test_login_invalid_credentials_returns_401(self):
        db = _mock_db_session()
        # User not found
        not_found = MagicMock()
        not_found.scalar_one_or_none.return_value = None
        db.execute.return_value = not_found

        client, _ = await _get_test_client(db)
        async with client:
            resp = await client.post("/api/v1/auth/login", json={
                "email": "nobody@test.com",
                "password": "wrongpass",
            })
        app.dependency_overrides.clear()
        assert resp.status_code in (401, 400)

    async def test_login_success_returns_tokens(self):
        from core.utils.encryption import EncryptionService
        enc = EncryptionService()
        hashed = enc.hash_password("SecurePass123!")
        user = _make_user(password=hashed, role=UserRole.ADMIN)

        db = _mock_db_session()
        found = MagicMock()
        found.scalar_one_or_none.return_value = user
        db.execute.return_value = found

        client, _ = await _get_test_client(db)
        async with client:
            resp = await client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "SecurePass123!",
            })
        app.dependency_overrides.clear()
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "data" in body


class TestMeEndpoint:
    async def test_me_without_token_returns_403(self):
        client, db = await _get_test_client()
        async with client:
            resp = await client.get("/api/v1/auth/me")
        app.dependency_overrides.clear()
        assert resp.status_code == 403

    async def test_me_with_invalid_token_returns_403(self):
        client, db = await _get_test_client()
        async with client:
            resp = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer invalid.token.here"},
            )
        app.dependency_overrides.clear()
        assert resp.status_code in (401, 403)


class TestRefreshEndpoint:
    async def test_refresh_without_token_fails(self):
        client, db = await _get_test_client()
        async with client:
            resp = await client.post("/api/v1/auth/refresh", json={})
        app.dependency_overrides.clear()
        assert resp.status_code in (400, 422)

    async def test_refresh_with_invalid_token_fails(self):
        db = _mock_db_session()
        client, _ = await _get_test_client(db)
        async with client:
            resp = await client.post("/api/v1/auth/refresh", json={
                "refresh_token": "invalid.token.here",
            })
        app.dependency_overrides.clear()
        assert resp.status_code in (400, 401)
