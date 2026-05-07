"""Unit tests for auth middleware helpers."""
import uuid
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException

from core.middleware.auth import (
    _role_str,
    invalidate_user_cache,
    require_roles,
    _user_cache,
)
from models.account.users import UserRole
from schemas.account.users import UserRead


def _make_user_read(**kwargs) -> UserRead:
    return UserRead(
        id=kwargs.get("id", uuid.uuid4()),
        first_name=kwargs.get("first_name", "Test"),
        last_name=kwargs.get("last_name", "User"),
        email=kwargs.get("email", "test@example.com"),
        role=kwargs.get("role", UserRole.STUDENT),
        is_active=kwargs.get("is_active", True),
        tenant_id=kwargs.get("tenant_id", uuid.uuid4()),
        created_at=None,
        updated_at=None,
    )


class TestRoleStr:
    def test_enum_role_returns_value(self):
        assert _role_str(UserRole.ADMIN) == "admin"

    def test_string_role_returns_lowercase(self):
        assert _role_str("STUDENT") == "student"

    def test_string_already_lowercase(self):
        assert _role_str("lecturer") == "lecturer"


class TestInvalidateUserCache:
    def test_invalidate_removes_from_cache(self):
        user_id = uuid.uuid4()
        _user_cache[user_id] = (MagicMock(), 9999999999.0)
        invalidate_user_cache(user_id)
        assert user_id not in _user_cache

    def test_invalidate_nonexistent_is_noop(self):
        # Should not raise
        invalidate_user_cache(uuid.uuid4())


class TestRequireRoles:
    async def test_allowed_role_passes(self):
        user = _make_user_read(role=UserRole.ADMIN)

        @require_roles(["admin"])
        async def handler(current_user=None):
            return current_user

        result = await handler(current_user=user)
        assert result is user

    async def test_disallowed_role_raises_403(self):
        user = _make_user_read(role=UserRole.STUDENT)

        @require_roles(["admin"])
        async def handler(current_user=None):
            return current_user

        with pytest.raises(HTTPException) as exc_info:
            await handler(current_user=user)
        assert exc_info.value.status_code == 403

    async def test_no_user_raises_401(self):
        @require_roles(["admin"])
        async def handler(current_user=None):
            return current_user

        with pytest.raises(HTTPException) as exc_info:
            await handler(current_user=None)
        assert exc_info.value.status_code == 401

    async def test_multiple_allowed_roles(self):
        user = _make_user_read(role=UserRole.LECTURER)

        @require_roles(["admin", "lecturer"])
        async def handler(current_user=None):
            return current_user

        result = await handler(current_user=user)
        assert result is user
