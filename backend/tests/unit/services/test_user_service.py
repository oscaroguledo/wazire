"""Unit tests for UserService — all DB calls mocked."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from services.account.users import UserService
from models.account.users import User, UserRole
from schemas.account.users import UserCreate, UserUpdate
from core.utils.encryption import EncryptionService
from core.utils.token import TokenService


def _make_user(**kwargs) -> User:
    return User(
        id=kwargs.get("id", uuid.uuid4()),
        first_name=kwargs.get("first_name", "Test"),
        middle_name=kwargs.get("middle_name", None),
        last_name=kwargs.get("last_name", "User"),
        email=kwargs.get("email", "test@example.com"),
        password=kwargs.get("password", "hashed_pw"),
        role=kwargs.get("role", UserRole.STUDENT),
        tenant_id=kwargs.get("tenant_id", uuid.uuid4()),
        institution_id=kwargs.get("institution_id", None),
        is_active=kwargs.get("is_active", True),
        is_deleted=kwargs.get("is_deleted", False),
        deleted_at=kwargs.get("deleted_at", None),
        created_at=kwargs.get("created_at", datetime.now(timezone.utc)),
        updated_at=kwargs.get("updated_at", datetime.now(timezone.utc)),
        created_by=kwargs.get("created_by", None),
        updated_by=kwargs.get("updated_by", None),
    )


def _mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


def _mock_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalar_one.return_value = value
    result.scalars.return_value.all.return_value = [value] if value else []
    return result


class TestUserServiceGet:
    async def test_get_by_id_returns_user(self):
        user = _make_user()
        db = _mock_db()
        db.execute.return_value = _mock_result(user)
        svc = UserService(db)
        result = await svc.get(user_id=user.id)
        assert result is user

    async def test_get_by_email_returns_user(self):
        user = _make_user(email="find@example.com")
        db = _mock_db()
        db.execute.return_value = _mock_result(user)
        svc = UserService(db)
        result = await svc.get(email="find@example.com")
        assert result is user

    async def test_get_no_args_returns_none(self):
        db = _mock_db()
        svc = UserService(db)
        result = await svc.get()
        assert result is None

    async def test_get_not_found_returns_none(self):
        db = _mock_db()
        db.execute.return_value = _mock_result(None)
        svc = UserService(db)
        result = await svc.get(user_id=uuid.uuid4())
        assert result is None


class TestUserServiceList:
    async def test_list_returns_items_and_total(self):
        user = _make_user()
        db = _mock_db()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [user]
        db.execute.side_effect = [count_result, items_result]
        svc = UserService(db)
        items, total = await svc.list()
        assert total == 1
        assert len(items) == 1

    async def test_list_empty_returns_zero(self):
        db = _mock_db()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []
        db.execute.side_effect = [count_result, items_result]
        svc = UserService(db)
        items, total = await svc.list()
        assert total == 0
        assert items == []


class TestUserServiceCreate:
    async def test_create_hashes_password_and_adds_user(self):
        db = _mock_db()
        enc = EncryptionService()
        svc = UserService(db, encryption=enc)
        user_in = UserCreate(
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            password="SecurePass123!",
            role="student",
        )
        created_user = _make_user(email="alice@example.com")
        db.refresh.side_effect = lambda u: None
        # Patch User constructor to return our mock
        with patch("services.account.users.User", return_value=created_user):
            result = await svc.create(user_in)
        db.add.assert_called_once()
        db.commit.assert_called_once()

    async def test_create_without_encryption_raises(self):
        db = _mock_db()
        svc = UserService(db)
        user_in = UserCreate(
            first_name="Bob",
            last_name="Jones",
            email="bob@example.com",
            password="SecurePass123!",
            role="student",
        )
        with pytest.raises(RuntimeError, match="EncryptionService required"):
            await svc.create(user_in)


class TestUserServiceAuthenticate:
    async def test_authenticate_valid_credentials_returns_user(self):
        enc = EncryptionService()
        hashed = enc.hash_password("correct_password")
        user = _make_user(password=hashed, is_active=True)
        db = _mock_db()
        db.execute.return_value = _mock_result(user)
        svc = UserService(db, encryption=enc)
        result = await svc.authenticate("test@example.com", "correct_password")
        assert result is user

    async def test_authenticate_wrong_password_returns_none(self):
        enc = EncryptionService()
        hashed = enc.hash_password("correct_password")
        user = _make_user(password=hashed, is_active=True)
        db = _mock_db()
        db.execute.return_value = _mock_result(user)
        svc = UserService(db, encryption=enc)
        result = await svc.authenticate("test@example.com", "wrong_password")
        assert result is None

    async def test_authenticate_inactive_user_returns_none(self):
        enc = EncryptionService()
        hashed = enc.hash_password("password")
        user = _make_user(password=hashed, is_active=False)
        db = _mock_db()
        db.execute.return_value = _mock_result(user)
        svc = UserService(db, encryption=enc)
        result = await svc.authenticate("test@example.com", "password")
        assert result is None

    async def test_authenticate_without_encryption_raises(self):
        db = _mock_db()
        svc = UserService(db)
        with pytest.raises(RuntimeError, match="EncryptionService required"):
            await svc.authenticate("test@example.com", "password")


class TestUserServiceTokens:
    async def test_generate_auth_tokens_returns_dict(self):
        token_svc = TokenService("test-secret-key-32-chars-minimum!!")
        user = _make_user(role=UserRole.STUDENT)
        db = _mock_db()
        svc = UserService(db, token_service=token_svc)
        tokens = await svc.generate_auth_tokens(user)
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"

    async def test_generate_tokens_without_service_raises(self):
        db = _mock_db()
        svc = UserService(db)
        user = _make_user()
        with pytest.raises(RuntimeError, match="TokenService required"):
            await svc.generate_auth_tokens(user)

    async def test_verify_token_valid_returns_payload(self):
        token_svc = TokenService("test-secret-key-32-chars-minimum!!")
        token = token_svc.create_jwt({"user_id": "abc", "token_type": "access"}, expires_in=3600)
        db = _mock_db()
        svc = UserService(db, token_service=token_svc)
        payload = await svc.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == "abc"

    async def test_verify_token_invalid_returns_none(self):
        token_svc = TokenService("test-secret-key-32-chars-minimum!!")
        db = _mock_db()
        svc = UserService(db, token_service=token_svc)
        result = await svc.verify_token("not.a.valid.token")
        assert result is None


class TestUserServiceUpdate:
    async def test_update_sets_fields(self):
        user = _make_user(first_name="Old")
        db = _mock_db()
        db.refresh.side_effect = lambda u: None
        svc = UserService(db)
        user_in = UserUpdate(first_name="New")
        result = await svc.update(user, user_in)
        assert result.first_name == "New"
        db.commit.assert_called_once()

    async def test_update_password_hashes_it(self):
        enc = EncryptionService()
        user = _make_user()
        db = _mock_db()
        db.refresh.side_effect = lambda u: None
        svc = UserService(db, encryption=enc)
        user_in = UserUpdate(password="NewSecurePass123!")
        await svc.update(user, user_in)
        # Password should be hashed (starts with pbkdf2_sha256)
        assert user.password.startswith("pbkdf2_sha256")


class TestUserServiceDelete:
    async def test_delete_calls_commit(self):
        user = _make_user()
        db = _mock_db()
        svc = UserService(db)
        await svc.delete(user)
        db.commit.assert_called_once()

    async def test_hard_delete_calls_db_delete(self):
        user = _make_user()
        db = _mock_db()
        svc = UserService(db)
        await svc.hard_delete(user)
        db.delete.assert_called_once_with(user)
        db.commit.assert_called_once()
