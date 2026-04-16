import os
import uuid
import pytest

from core.config import get_settings


@pytest.mark.asyncio
async def test_question_exam_linking(tmp_path):
    db_file = tmp_path / "test_qe.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_file}"
    get_settings(force_reload=True)

    from core.database import init_db, get_session_factory
    from services.account.tenant import TenantService
    from services.academic.course import CourseService
    from services.academic.exam import ExamService
    from services.academic.question import QuestionService
    from schemas.account.tenant import TenantCreate
    from schemas.academic.course import CourseCreate
    from schemas.academic.exam import ExamCreate
    from schemas.academic.question import QuestionCreate

    await init_db()

    AsyncSessionLocal = get_session_factory()
    async with AsyncSessionLocal() as session:
        tenant_svc = TenantService(session)
        t = await tenant_svc.create(TenantCreate(name="T1"))

        course_svc = CourseService(session)
        c_in = CourseCreate(name="C1", description="", course_code="C1", lecturer_id=uuid.uuid4(), tenant_id=t.id)
        c = await course_svc.create(c_in, tenant_id=t.id)

        exam_svc = ExamService(session)
        e_in = ExamCreate(title="Exam 1", duration=60, course_id=c.id, tenant_id=t.id)
        e = await exam_svc.create(e_in, tenant_id=t.id)

        question_svc = QuestionService(session)
        q_in = QuestionCreate(number="1", text="What?", image_url=None, parent_id=None, tenant_id=t.id, exam_ids=[e.id])
        q = await question_svc.create(q_in, tenant_id=t.id)

        # reload via services (they use selectinload)
        e2 = await exam_svc.get(e.id, tenant_id=t.id)
        q2 = await question_svc.get(q.id, tenant_id=t.id)

        assert e2 is not None
        assert q2 is not None
        assert any(str(q.id) == str(qi.id) for qi in e2.questions)
        assert any(str(e.id) == str(ei.id) for ei in q2.exams)
