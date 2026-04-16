from __future__ import annotations

import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, status, Request, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.utils.response import Response
from core.utils.token import TokenService
from core.dependencies.common import get_token_service, lecturer_or_admin_dep, authenticated_dep, student_only_dep
from services.academic.submission import SubmissionService
# StudentAnswerService is used in services and grading; not required at route-level
from services.analytics.dashboard import refresh_dashboard_bg_sync
from services.engine.answer_sheet_extractor import AnswerSheetParser
from models.academic.question import Question as QuestionModel
from models.academic.exam import Exam as ExamModel
from models.academic.course import Course
from models.account.users import User as UserModel
from schemas.academic.submission import (
    ExamSubmit, ExamSubmitResponse,
    SubmissionRead, SubmissionWithAttemptsRead, SubmissionAttemptRead,
    AttemptGrade,
)
from schemas.account.users import UserRead

router = APIRouter(prefix="/submissions", tags=["submissions"])




async def _enrich_submission(s, db) -> dict:
    """Add student_name, exam_title, course_id, and status to a submission dict."""
    data = SubmissionRead.model_validate(s).model_dump()
    data['id'] = str(data['id'])
    data['student_id'] = str(data['student_id'])
    data['exam_id'] = str(data['exam_id'])
    # Compute status based on graded_at and latest_score
    if s.graded_at and s.latest_score is not None:
        data['status'] = 'graded'
    elif s.attempts_count > 0:
        data['status'] = 'submitted'
    else:
        data['status'] = 'pending'
    # Fetch student name
    student = (await db.execute(select(UserModel).where(UserModel.id == s.student_id))).scalar_one_or_none()
    if student:
        data['student_name'] = student.full_name()
    # Fetch exam and course info
    exam = (await db.execute(select(ExamModel).where(ExamModel.id == s.exam_id))).scalar_one_or_none()
    if exam:
        data['exam_title'] = exam.title
        if exam.course_id:
            data['course_id'] = str(exam.course_id)
    return data


class ScanSubmit(BaseModel):
    """Payload for scanning a student's paper answer sheet."""
    exam_id: uuid.UUID
    student_id: uuid.UUID
    pages: List[str]       # base64 images — read by AI parser
    page_urls: List[str]   # storage URLs already uploaded by frontend — stored for audit




def _tenant(user: UserRead) -> Optional[uuid.UUID]:
    return None if user.role in ("admin", "superadmin") else user.tenant_id


# ---------------------------------------------------------------------------
# POST /  — student submits a digital exam attempt
# ---------------------------------------------------------------------------

@router.post("/", status_code=status.HTTP_201_CREATED)
async def submit_exam(
    body: ExamSubmit,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: UserRead = student_only_dep,
    db: AsyncSession = Depends(get_db),
):
    service = SubmissionService(db)
    """Submit an exam attempt. Returns immediately; grading runs in background."""
    if not current_user.tenant_id and current_user.role not in ("admin", "superadmin"):
        return Response(success=False, error="No tenant assigned to your account", request=request, status_code=status.HTTP_403_FORBIDDEN)

    try:
        # Answers are stored per-question in the student_answers table by the autosave flow.
        # Final submit does not need raw answers supplied in the request body.
        submission, attempt = await service.submit_exam(
            exam_id=body.exam_id,
            student_id=current_user.id,
            tenant_id=_tenant(current_user),
        )
    except ValueError as e:
        return Response(success=False, error=str(e), request=request, status_code=status.HTTP_400_BAD_REQUEST)

    # Grade in background using FastAPI BackgroundTasks
    background_tasks.add_task(
        service.grade_attempt_background,
        str(attempt.id),
        str(body.exam_id)
    )

    # Refresh dashboards in background after submission
    # Refresh student dashboard in background
    background_tasks.add_task(refresh_dashboard_bg_sync, current_user.id)
    # Get exam to find lecturer for background refresh
    exam_stmt = select(ExamModel).where(ExamModel.id == body.exam_id)
    exam_result = await service.db.execute(exam_stmt)
    exam = exam_result.scalar_one_or_none()
    # Refresh lecturer dashboard in background if exam has a course with lecturer
    if exam and exam.course_id:
        course_stmt = select(Course).where(Course.id == exam.course_id)
        course_result = await service.db.execute(course_stmt)
        course = course_result.scalar_one_or_none()
        if course and course.lecturer_id:
            background_tasks.add_task(refresh_dashboard_bg_sync, course.lecturer_id)

    # Lightweight task: log submission activity
    background_tasks.add_task(
        lambda student_id, exam_id, attempt_number: print(f"[log] Student {student_id} submitted exam {exam_id}, attempt #{attempt_number}"),
        str(current_user.id),
        str(body.exam_id),
        attempt.attempt_number
    )

    return Response(
        success=True,
        message=f"Attempt #{attempt.attempt_number} submitted — grading in progress",
        data=ExamSubmitResponse(
            submission=SubmissionRead.model_validate(submission),
            attempt=SubmissionAttemptRead.model_validate(attempt),
        ),
        request=request,
        status_code=status.HTTP_201_CREATED,
    )


class StartExamRequest(BaseModel):
    exam_id: uuid.UUID


@router.post("/start", status_code=status.HTTP_201_CREATED)
async def start_submission(
    body: StartExamRequest,
    request: Request,
    current_user: UserRead = student_only_dep,
    db: AsyncSession = Depends(get_db),
):
    service = SubmissionService(db)
    """Create a Submission record (no attempt) when the student clicks Start Exam."""
    if not current_user.tenant_id and current_user.role not in ("admin", "superadmin"):
        return Response(success=False, error="No tenant assigned to your account", request=request, status_code=status.HTTP_403_FORBIDDEN)

    try:
        submission = await service.create_submission(body.exam_id, current_user.id)
    except ValueError as e:
        return Response(success=False, error=str(e), request=request, status_code=status.HTTP_400_BAD_REQUEST)

    return Response(
        success=True,
        message="Submission started",
        data=SubmissionRead.model_validate(submission),
        request=request,
        status_code=status.HTTP_201_CREATED,
    )

# ---------------------------------------------------------------------------
# GET /exam/{exam_id}/students  — lecturer sees all students + their submissions
# ---------------------------------------------------------------------------

@router.get("/exam/{exam_id}/students")
async def list_students_with_submissions(
    exam_id: uuid.UUID,
    request: Request,
    page: int = 1,
    per_page: int = 50,
    current_user: UserRead = lecturer_or_admin_dep,
    db: AsyncSession = Depends(get_db),
):
    service = SubmissionService(db)
    """All students and their full submission + attempt history for a specific exam in the caller's tenant."""
    try:
        offset = (page - 1) * per_page
        results, total = await service.list_students_with_submissions(
            exam_id=exam_id,
            tenant_id=_tenant(current_user),
            limit=per_page,
            offset=offset,
        )
        
        total_pages = (total + per_page - 1) // per_page
        
        return Response(
            success=True,
            message="Students and submissions retrieved",
            data=results,
            pagination={
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            request=request,
        )
    except ValueError as e:
        return Response(success=False, error=str(e), request=request, status_code=status.HTTP_404_NOT_FOUND)

# ---------------------------------------------------------------------------
# GET /?exam_id=  — lecturer sees all submissions for an exam
# ---------------------------------------------------------------------------

@router.get("/")
async def list_submissions(
    request: Request,
    exam_id: uuid.UUID,
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    current_user: UserRead = lecturer_or_admin_dep,
    db: AsyncSession = Depends(get_db),
):
    service = SubmissionService(db)
    """List submissions with offset/limit pagination."""
    # Calculate offset from page
    offset = (page - 1) * per_page
    
    # Get submissions
    items = await service.list_for_exam(exam_id=exam_id, tenant_id=_tenant(current_user), status=status, limit=per_page, offset=offset)
    
    # Get total count for pagination
    total_count = await service.count_for_exam(exam_id=exam_id, tenant_id=_tenant(current_user), status=status)
    
    # Calculate total pages
    total_pages = (total_count + per_page - 1) // per_page
    
    return Response(
        success=True, 
        message="Submissions retrieved", 
        data=[SubmissionRead.model_validate(s) for s in items], 
        pagination={
            "page": page,
            "per_page": per_page,
            "total": total_count,
            "pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }, 
        request=request
    )


# ---------------------------------------------------------------------------
# GET /lecturer - lecturer sees all submissions for their exams
# ---------------------------------------------------------------------------

@router.get("/lecturer")
async def list_lecturer_submissions(
    request: Request,
    page: int = 1,
    per_page: int = 50,
    current_user: UserRead = lecturer_or_admin_dep,
    db: AsyncSession = Depends(get_db),
):
    service = SubmissionService(db)
    """All submissions for exams the lecturer teaches, or all submissions for admins."""
    offset = (page - 1) * per_page
    tenant_id = _tenant(current_user)

    # Admins see all submissions in their tenant; lecturers see only their courses
    if current_user.role in ("admin", "superadmin"):
        items = await service.list_for_tenant(tenant_id=tenant_id, limit=per_page, offset=offset)
        total_count = await service.count_for_tenant(tenant_id=tenant_id)
    else:
        items = await service.list_for_lecturer(
            lecturer_id=current_user.id,
            tenant_id=tenant_id,
            limit=per_page,
            offset=offset,
        )
        total_count = await service.count_for_lecturer(
            lecturer_id=current_user.id,
            tenant_id=tenant_id,
        )

    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

    return Response(
        success=True,
        message="Submissions retrieved",
        data=[await _enrich_submission(s, service.db) for s in items],
        pagination={
            "page": page,
            "per_page": per_page,
            "total": total_count,
            "pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
        request=request,
    )


# ---------------------------------------------------------------------------
# GET /mine?exam_id=  — student sees their own submission + all attempts
# ---------------------------------------------------------------------------

@router.get("/mine")
async def my_submission(
    request: Request,
    exam_id: Optional[uuid.UUID] = None,
    current_user: UserRead = student_only_dep,
    db: AsyncSession = Depends(get_db),
):
    service = SubmissionService(db)
    if exam_id:
        # Get submission for specific exam
        submission = await service.get_my_submission(student_id=current_user.id, exam_id=exam_id)
        if not submission:
            # Return success with null data instead of 404 - student hasn't submitted yet
            return Response(
                success=True, 
                message="No submission found for this exam", 
                data=None,
                request=request,
            )

        attempts = await service.get_attempts(submission.id)
        return Response(
            success=True,
            message="Your submission retrieved",
            data=SubmissionWithAttemptsRead(
                **SubmissionRead.model_validate(submission).model_dump(),
                attempts=[SubmissionAttemptRead.model_validate(a) for a in attempts],
            ),
            request=request,
        )
    else:
        # Get all submissions for this student
        submissions = await service.get_all_my_submissions(student_id=current_user.id, tenant_id=_tenant(current_user))
        return Response(
            success=True,
            message="All your submissions retrieved",
            data=submissions,
            request=request,
        )


# Note: draft endpoint removed — autosave writes directly to student_answers.


# ---------------------------------------------------------------------------
# GET /mine/all  — student sees all their submissions (explicit endpoint)
# ---------------------------------------------------------------------------

@router.get("/mine/all")
async def all_my_submissions(
    request: Request,
    current_user: UserRead = student_only_dep,
    db: AsyncSession = Depends(get_db),
):
    service = SubmissionService(db)
    """Get all submissions for the current student across all exams."""
    submissions = await service.get_all_my_submissions(student_id=current_user.id, tenant_id=_tenant(current_user))
    return Response(
        success=True,
        message="All your submissions retrieved",
        data=submissions,
        request=request,
    )

async def get_attempts(
    submission_id: uuid.UUID,
    request: Request,
    current_user: UserRead = lecturer_or_admin_dep,
    db: AsyncSession = Depends(get_db),
):
    service = SubmissionService(db)
    submission = await service.get(submission_id, tenant_id=_tenant(current_user))
    if not submission:
        return Response(success=False, error="Submission not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    attempts = await service.get_attempts(submission_id)
    return Response(success=True, message="Attempts retrieved", data=[SubmissionAttemptRead.model_validate(a) for a in attempts], request=request)


# ... (rest of the code remains the same)

# ---------------------------------------------------------------------------
# POST /scan/  — lecturer scans a student's paper answer sheet
# ---------------------------------------------------------------------------

@router.post("/scan/", status_code=status.HTTP_201_CREATED)
async def scan_answer_sheet(
    body: ScanSubmit,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: UserRead = lecturer_or_admin_dep,
    db: AsyncSession = Depends(get_db),
):
    service = SubmissionService(db)
    """Parse scanned answer sheet pages, map to questions, grade in background."""
    if not body.pages:
        return Response(success=False, error="No pages provided", request=request, status_code=status.HTTP_400_BAD_REQUEST)

    # 1. Load exam questions
    questions = (await db.execute(
        select(QuestionModel).where(QuestionModel.exams.any(ExamModel.id == body.exam_id))
    )).scalars().all()
    if not questions:
        return Response(success=False, error="No questions found for this exam", request=request, status_code=status.HTTP_404_NOT_FOUND)

    # 2. Parse answer sheet pages (fast — just vision extraction, no DB writes)
    question_index = [
        {"number": q.number, "qtype": q.qtype, "options": q.get_options() if q.qtype == "multiple_choice" else []}
        for q in questions
    ]
    number_to_id = {q.number: str(q.id) for q in questions}

    try:
        parser = AnswerSheetParser()
        extracted = parser.parse(pages=body.pages, question_index=question_index)
    except RuntimeError as e:
        return Response(success=False, error=str(e), request=request, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    # 3. Map question numbers → question IDs
    answers: dict = {}
    for number, answer_value in extracted.items():
        qid = number_to_id.get(str(number))
        if not qid or answer_value is None:
            continue
        q = next((q for q in questions if q.number == str(number)), None)
        if q and q.qtype == "multiple_choice":
            answers[qid] = {"option": str(answer_value).strip().lower()}
        elif q:
            answers[qid] = {"text": str(answer_value).strip()}

    # 4. Save attempt immediately (score=None), enqueue grading
    try:
        submission, attempt = await service.submit_exam(
            exam_id=body.exam_id,
            student_id=body.student_id,
            answers=answers,
            tenant_id=_tenant(current_user),
            scan_pages=body.page_urls,
        )
    except ValueError as e:
        return Response(success=False, error=str(e), request=request, status_code=status.HTTP_400_BAD_REQUEST)

    # Grade scanned attempt in background using FastAPI BackgroundTasks
    background_tasks.add_task(
        service.grade_attempt_background,
        str(attempt.id),
        str(body.exam_id)
    )

    # Refresh dashboards in background after scan submission
    # Refresh student dashboard in background
    background_tasks.add_task(refresh_dashboard_bg_sync, body.student_id)
    # Get exam to find lecturer for background refresh
    exam_stmt = select(ExamModel).where(ExamModel.id == body.exam_id)
    exam_result = await db.execute(exam_stmt)
    exam = exam_result.scalar_one_or_none()
    # Refresh lecturer dashboard in background if exam has a course with lecturer
    if exam and exam.course_id:
        course_stmt = select(Course).where(Course.id == exam.course_id)
        course_result = await db.execute(course_stmt)
        course = course_result.scalar_one_or_none()
        if course and course.lecturer_id:
            background_tasks.add_task(refresh_dashboard_bg_sync, course.lecturer_id)

    return Response(
        success=True,
        message=f"Answer sheet scanned. Attempt #{attempt.attempt_number} — grading in progress",
        data=ExamSubmitResponse(
            submission=SubmissionRead.model_validate(submission),
            attempt=SubmissionAttemptRead.model_validate(attempt),
        ),
        request=request,
        status_code=status.HTTP_201_CREATED,
    )
