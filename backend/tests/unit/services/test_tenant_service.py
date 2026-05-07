"""Unit tests for TenantService — all DB calls mocked."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException

from services.account.tenants import TenantService
from models.account.tenant import Tenant
from schemas.account.tenant import TenantCreate, TenantUpdate, TenantDelete


def _make_tenant(**kwargs) -> Tenant:
    return Tenant(
        id=kwargs.get("id", uuid.uuid4()),
        name=kwargs.get("name", "Test University"),
        domain=kwargs.get("domain", "test.edu"),
        logo_url=kwargs.get("logo_url", None),
        tenant_code=kwargs.get("tenant_code", "ABC123"),
        is_active=kwargs.get("is_active", True),
        is_deleted=kwargs.get("is_deleted", False),
        deleted_at=kwargs.get("deleted_at", None),
        start_date=kwargs.get("start_date", None),
        end_date=kwargs.get("end_date", None),
        paystack_customer_code=kwargs.get("paystack_customer_code", None),
        monnify_account_reference=kwargs.get("monnify_account_reference", None),
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
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    db.get = AsyncMock()
    return db


def _mock_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalar_one.return_value = value if value is not None else 0
    result.scalars.return_value.all.return_value = [value] if value else []
    result.all.return_value = []
    return result


class TestTenantServiceGet:
    async def test_get_returns_tenant(self):
        tenant = _make_tenant()
        db = _mock_db()
        db.execute.return_value = _mock_result(tenant)
        svc = TenantService(db)
        result = await svc.get(tenant_id=tenant.id)
        assert result is tenant

    async def test_get_not_found_returns_none(self):
        db = _mock_db()
        db.execute.return_value = _mock_result(None)
        svc = TenantService(db)
        result = await svc.get(tenant_id=uuid.uuid4())
        assert result is None


class TestTenantServiceList:
    async def test_list_returns_items_and_total(self):
        tenant = _make_tenant()
        db = _mock_db()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = [tenant]
        db.execute.side_effect = [count_result, items_result]
        svc = TenantService(db)
        items, total = await svc.list()
        assert total == 1
        assert len(items) == 1

    async def test_list_empty(self):
        db = _mock_db()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        items_result = MagicMock()
        items_result.scalars.return_value.all.return_value = []
        db.execute.side_effect = [count_result, items_result]
        svc = TenantService(db)
        items, total = await svc.list()
        assert total == 0
        assert items == []


class TestTenantServiceCreate:
    async def test_create_generates_tenant_code(self):
        db = _mock_db()
        # No existing tenant with same name/domain
        no_existing = MagicMock()
        no_existing.all.return_value = []
        # No existing tenant_code collision
        no_code = MagicMock()
        no_code.scalar_one_or_none.return_value = None
        db.execute.side_effect = [no_existing, no_code]
        db.refresh.side_effect = lambda t: None

        tenant_in = TenantCreate(name="New University", domain="new.edu", created_by=uuid.uuid4())
        svc = TenantService(db)
        result = await svc.create(tenant_in)
        # tenant_code should be a 6-char uppercase alphanumeric string
        assert result.tenant_code is not None
        assert len(result.tenant_code) == 6
        db.add.assert_called()
        db.commit.assert_called()

    async def test_create_raises_on_duplicate_name(self):
        db = _mock_db()
        existing_row = MagicMock()
        existing_row.name = "test university"
        existing_row.domain = "test.edu"
        existing = MagicMock()
        existing.all.return_value = [existing_row]
        db.execute.return_value = existing

        tenant_in = TenantCreate(name="Test University", domain="other.edu", created_by=uuid.uuid4())
        svc = TenantService(db)
        with pytest.raises(HTTPException) as exc_info:
            await svc.create(tenant_in)
        assert exc_info.value.status_code == 400


class TestTenantServiceUpdate:
    async def test_update_modifies_fields(self):
        tenant = _make_tenant(name="old name")
        db = _mock_db()
        db.get.return_value = tenant
        db.execute.return_value = _mock_result(None)  # no domain conflict
        db.refresh.side_effect = lambda t: None
        svc = TenantService(db)
        update = TenantUpdate(id=tenant.id, name="new name")
        result = await svc.update(update)
        assert result.name == "new name"

    async def test_update_not_found_raises(self):
        db = _mock_db()
        db.get.return_value = None
        svc = TenantService(db)
        update = TenantUpdate(id=uuid.uuid4(), name="Unknown University")
        with pytest.raises(HTTPException) as exc_info:
            await svc.update(update)
        assert exc_info.value.status_code == 404


class TestTenantServiceDelete:
    async def test_delete_soft_deletes(self):
        tenant = _make_tenant()
        db = _mock_db()
        db.get.return_value = tenant
        svc = TenantService(db)
        delete_in = TenantDelete(id=tenant.id, updated_by=uuid.uuid4())
        await svc.delete(delete_in)
        assert tenant.is_deleted is True
        db.commit.assert_called_once()

    async def test_delete_not_found_raises(self):
        db = _mock_db()
        db.get.return_value = None
        svc = TenantService(db)
        with pytest.raises(HTTPException) as exc_info:
            await svc.delete(TenantDelete(id=uuid.uuid4(), updated_by=uuid.uuid4()))
        assert exc_info.value.status_code == 404

    async def test_restore_reactivates_tenant(self):
        tenant = _make_tenant(is_deleted=True, is_active=False)
        db = _mock_db()
        db.get.return_value = tenant
        db.refresh.side_effect = lambda t: None
        svc = TenantService(db)
        result = await svc.restore(TenantDelete(id=tenant.id, updated_by=uuid.uuid4()))
        assert result.is_deleted is False
        assert result.is_active is True

    async def test_hard_delete_removes_tenant(self):
        tenant = _make_tenant()
        db = _mock_db()
        db.get.return_value = tenant
        svc = TenantService(db)
        await svc.hard_delete(tenant.id)
        db.delete.assert_called_once_with(tenant)
        db.commit.assert_called_once()
