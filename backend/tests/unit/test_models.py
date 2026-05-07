"""Unit tests for model to_dict(), delete(), restore() methods.

Uses normal model constructors — no DB connection required.
SQLAlchemy models can be instantiated without a session for unit testing.
"""
import uuid
from datetime import datetime, timezone
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Invoice model tests
# ---------------------------------------------------------------------------

class TestInvoiceModel:
    """Tests for Invoice model methods."""

    def _make_invoice(self, **kwargs):
        from models.billings.invoice import Invoice, InvoiceStatus
        return Invoice(
            id=kwargs.get("id", _uuid()),
            tenant_id=kwargs.get("tenant_id", _uuid()),
            semester_id=kwargs.get("semester_id", _uuid()),
            description=kwargs.get("description", "Test Invoice"),
            student_count=kwargs.get("student_count", 100),
            amount_per_student=kwargs.get("amount_per_student", 2000),
            total_amount=kwargs.get("total_amount", 200000),
            status=kwargs.get("status", InvoiceStatus.PENDING),
            payment_reference=kwargs.get("payment_reference", None),
            payment_gateway=kwargs.get("payment_gateway", None),
            paid_at=kwargs.get("paid_at", None),
            payment_url=kwargs.get("payment_url", None),
            created_at=kwargs.get("created_at", _now()),
            updated_at=kwargs.get("updated_at", _now()),
            created_by=kwargs.get("created_by", None),
            updated_by=kwargs.get("updated_by", None),
        )

    def test_to_dict_includes_all_required_fields(self):
        """Test that Invoice.to_dict() includes all required fields."""
        inv = self._make_invoice()
        d = inv.to_dict()

        required_fields = {
            "id", "tenant_id", "semester_id", "description",
            "student_count", "amount_per_student", "total_amount",
            "status", "payment_reference", "payment_gateway",
            "paid_at", "payment_url", "created_at", "updated_at",
        }
        for field in required_fields:
            assert field in d, f"Missing field '{field}' in Invoice.to_dict()"

    def test_to_dict_status_is_string_value(self):
        """Test that status is serialized as its string value."""
        from models.billings.invoice import InvoiceStatus
        inv = self._make_invoice(status=InvoiceStatus.PAID)
        d = inv.to_dict()

        assert d["status"] == "paid"

    def test_to_dict_paid_at_is_isoformat(self):
        """Test that paid_at is serialized as ISO format string."""
        paid_at = _now()
        inv = self._make_invoice(paid_at=paid_at)
        d = inv.to_dict()

        assert d["paid_at"] == paid_at.isoformat()

    def test_to_dict_paid_at_none_when_not_set(self):
        """Test that paid_at is None when not set."""
        inv = self._make_invoice(paid_at=None)
        d = inv.to_dict()

        assert d["paid_at"] is None

    def test_repr_includes_status(self):
        """Test that __repr__ includes status value."""
        inv = self._make_invoice()
        repr_str = repr(inv)

        assert "Invoice" in repr_str
        assert "pending" in repr_str


# ---------------------------------------------------------------------------
# BillingPlan model tests
# ---------------------------------------------------------------------------

class TestBillingPlanModel:
    """Tests for BillingPlan model methods."""

    def _make_plan(self, **kwargs):
        from models.billings.plan import BillingPlan
        return BillingPlan(
            id=kwargs.get("id", _uuid()),
            tenant_id=kwargs.get("tenant_id", _uuid()),
            plan_id=kwargs.get("plan_id", "standard"),
            name=kwargs.get("name", "Standard"),
            description=kwargs.get("description", "Standard plan"),
            price_per_student=kwargs.get("price_per_student", 2000),
            min_students=kwargs.get("min_students", 20),
            features=kwargs.get("features", "Feature A,Feature B,Feature C"),
            is_active=kwargs.get("is_active", True),
            created_at=kwargs.get("created_at", _now()),
            updated_at=kwargs.get("updated_at", _now()),
            created_by=kwargs.get("created_by", None),
            updated_by=kwargs.get("updated_by", None),
        )

    def test_to_dict_includes_is_active(self):
        """Test that BillingPlan.to_dict() includes is_active field."""
        plan = self._make_plan(is_active=True)
        d = plan.to_dict()

        assert "is_active" in d
        assert d["is_active"] is True

    def test_to_dict_features_is_list(self):
        """Test that features is returned as a list."""
        plan = self._make_plan(features="Feature A,Feature B,Feature C")
        d = plan.to_dict()

        assert isinstance(d["features"], list)
        assert len(d["features"]) == 3
        assert "Feature A" in d["features"]

    def test_get_features_list_splits_correctly(self):
        """Test that get_features_list splits comma-separated features."""
        plan = self._make_plan(features="A,B,C")
        features = plan.get_features_list()

        assert features == ["A", "B", "C"]

    def test_get_features_list_strips_whitespace(self):
        """Test that get_features_list strips whitespace from features."""
        plan = self._make_plan(features=" A , B , C ")
        features = plan.get_features_list()

        assert features == ["A", "B", "C"]

    def test_to_dict_all_required_fields(self):
        """Test that BillingPlan.to_dict() includes all required fields."""
        plan = self._make_plan()
        d = plan.to_dict()

        required_fields = {
            "id", "tenant_id", "plan_id", "name", "description",
            "price_per_student", "min_students", "features", "is_active",
            "created_at", "updated_at",
        }
        for field in required_fields:
            assert field in d, f"Missing field '{field}' in BillingPlan.to_dict()"


# ---------------------------------------------------------------------------
# Tenant model tests
# ---------------------------------------------------------------------------

class TestTenantModel:
    """Tests for Tenant model methods."""

    def _make_tenant(self, **kwargs):
        from models.account.tenant import Tenant
        return Tenant(
            id=kwargs.get("id", _uuid()),
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
            created_at=kwargs.get("created_at", _now()),
            updated_at=kwargs.get("updated_at", _now()),
            created_by=kwargs.get("created_by", None),
            updated_by=kwargs.get("updated_by", None),
        )

    def test_to_dict_includes_all_required_fields(self):
        """Test that Tenant.to_dict() includes all required fields."""
        t = self._make_tenant()
        d = t.to_dict()

        required_fields = {
            "id", "name", "domain", "logo_url", "tenant_code",
            "is_active", "is_deleted", "deleted_at",
            "start_date", "end_date",
            "paystack_customer_code", "monnify_account_reference",
            "created_at", "updated_at",
        }
        for field in required_fields:
            assert field in d, f"Missing field '{field}' in Tenant.to_dict()"

    def test_delete_sets_flags(self):
        """Test that delete() sets is_deleted=True, is_active=False, deleted_at."""
        t = self._make_tenant()
        t.delete()

        assert t.is_deleted is True
        assert t.is_active is False
        assert t.deleted_at is not None

    def test_restore_clears_flags(self):
        """Test that restore() clears is_deleted, sets is_active=True, clears deleted_at."""
        t = self._make_tenant(is_deleted=True, is_active=False, deleted_at=_now())
        t.restore()

        assert t.is_deleted is False
        assert t.is_active is True
        assert t.deleted_at is None

    def test_can_be_deleted_with_unpaid_invoices(self):
        """Test that can_be_deleted returns False when there are unpaid invoices."""
        t = self._make_tenant()
        can_delete, reason = t.can_be_deleted(has_unpaid_invoices=True)

        assert can_delete is False
        assert "unpaid invoices" in reason

    def test_can_be_deleted_with_active_semesters(self):
        """Test that can_be_deleted returns False when there are active semesters."""
        t = self._make_tenant()
        can_delete, reason = t.can_be_deleted(has_active_semesters=True)

        assert can_delete is False
        assert "active semesters" in reason

    def test_can_be_deleted_when_clear(self):
        """Test that can_be_deleted returns True when no blockers."""
        t = self._make_tenant()
        can_delete, reason = t.can_be_deleted()

        assert can_delete is True

    def test_full_name_returns_name(self):
        """Test that full_name() returns the tenant name."""
        t = self._make_tenant(name="University of Lagos")
        assert t.full_name() == "University of Lagos"

    def test_to_dict_tenant_code_included(self):
        """Test that tenant_code is included in to_dict output."""
        t = self._make_tenant(tenant_code="XYZ789")
        d = t.to_dict()

        assert d["tenant_code"] == "XYZ789"
