import os
import uuid
import pytest

from core.config import get_settings


@pytest.mark.asyncio
async def test_tenant_isolation(tmp_path):
    # Use a temporary SQLite file for isolation
    db_file = tmp_path / "test_tenant.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_file}"
    # reload settings so core.database picks up new URL
    get_settings(force_reload=True)

    from core.database import init_db, get_session_factory
    from services.account.tenant import TenantService
    from services.academic.course import CourseService
    from schemas.account.tenant import TenantCreate
    from schemas.academic.course import CourseCreate

    await init_db()

    AsyncSessionLocal = get_session_factory()
    async with AsyncSessionLocal() as session:
        tenant_svc = TenantService(session)
        # create two tenants
        t1 = await tenant_svc.create(TenantCreate(name="Tenant A"))
        t2 = await tenant_svc.create(TenantCreate(name="Tenant B"))

        course_svc = CourseService(session)

        # create one course per tenant (lecturer id is a random uuid)
        c1_in = CourseCreate(name="Course 1", description="", course_code="C1", lecturer_id=uuid.uuid4(), tenant_id=t1.id)
        c2_in = CourseCreate(name="Course 2", description="", course_code="C2", lecturer_id=uuid.uuid4(), tenant_id=t2.id)

        c1 = await course_svc.create(c1_in, tenant_id=t1.id)
        c2 = await course_svc.create(c2_in, tenant_id=t2.id)

        # list per-tenant
        t1_courses = await course_svc.list(tenant_id=t1.id)
        t2_courses = await course_svc.list(tenant_id=t2.id)

        assert any(str(c.id) == str(c1.id) for c in t1_courses)
        assert all(str(c.tenant_id) == str(t1.id) for c in t1_courses)
        assert any(str(c.id) == str(c2.id) for c in t2_courses)
        assert all(str(c.tenant_id) == str(t2.id) for c in t2_courses)
