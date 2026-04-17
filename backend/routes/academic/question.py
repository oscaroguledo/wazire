from __future__ import annotations

from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.utils.response import Response
from core.utils.logger import logger
from core.utils.token import TokenService
from core.dependencies.common import get_token_service, lecturer_or_admin_dep, authenticated_dep
from services.academic.question import QuestionService
from tasks.question import detect_answer_task, parse_and_create_task
from services.engine.exam_extractor import ExamParser
from schemas.academic.question import (
    QuestionCreate,
    QuestionUpdate,
)
from models.academic.question import Industry
from schemas.account.users import UserRead


router = APIRouter(prefix="/questions", tags=["questions"])


class ExamUpload(BaseModel):
    """Payload for exam paper upload."""
    pages: List[str]                        # base64 image strings, one per page
    exam_id: uuid.UUID                      # exam to link all extracted questions to
    industry: Industry                      # subject area
    mark_per_question: Optional[float] = None  # fallback mark when not printed on paper


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_question(
    question_in: QuestionCreate,
    request: Request,
    current_user: UserRead = lecturer_or_admin_dep,
    db: AsyncSession = Depends(get_db),
):
    service = QuestionService(db)
    # Questions may optionally include a tenant_id; non-admins cannot set a tenant different from their own
    if current_user.role != "admin":
        # enforce non-admins cannot set tenant_id
        if getattr(question_in, "tenant_id", None):
            # ignore provided tenant_id and use user's tenant if present
            tenant_id = current_user.tenant_id
        else:
            tenant_id = current_user.tenant_id
    else:
        tenant_id = getattr(question_in, "tenant_id", None)

    try:
        q = await service.create(question_in, tenant_id=tenant_id)
        # If MCQ with no answer provided, detect it in the background
        if q.qtype == "multiple_choice" and not q.answer_id:
            # Enqueue MCQ answer detection to Celery worker
            detect_answer_task.delay(str(q.id))
        return Response(success=True, message="Question created", data=q.to_dict(), request=request, status_code=status.HTTP_201_CREATED)
    except ValueError as e:
        return Response(success=False, error=str(e), request=request, status_code=status.HTTP_400_BAD_REQUEST)


@router.get("/")
async def list_questions(
    request: Request,
    exam_id: Optional[uuid.UUID] = None,
    current_user: UserRead = authenticated_dep,
    db: AsyncSession = Depends(get_db),
):
    service = QuestionService(db)
    """List all questions."""
    # Questions are global (not tenant-scoped); still enforce role

    items = await service.list(exam_id=exam_id)

    return Response(
        success=True,
        message="Questions retrieved",
        data=[item.to_dict() for item in items],
        request=request
    )


@router.get("/exam/{exam_id}")
async def get_exam_questions(
    exam_id: uuid.UUID,
    request: Request,
    current_user: UserRead = authenticated_dep,
    db: AsyncSession = Depends(get_db),
):
    """Get questions for exam."""
    service = QuestionService(db)
    questions = await service.list_for_exam(exam_id)
    return Response(
        success=True,
        message="Exam questions retrieved",
        data=[q.to_dict() for q in questions],
        request=request
    )


@router.get("/{question_id}")
async def get_question(
    question_id: uuid.UUID,
    request: Request,
    current_user: UserRead = authenticated_dep,
    db: AsyncSession = Depends(get_db),
):
    service = QuestionService(db)
    # tenant-free; just fetch by id
    q = await service.get(question_id)
    if not q:
        return Response(success=False, error="Question not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    return Response(success=True, message="Question retrieved", data=q.to_dict(), request=request)


@router.put("/{question_id}")
async def update_question(
    question_id: uuid.UUID,
    question_in: QuestionUpdate,
    request: Request,
    current_user: UserRead = lecturer_or_admin_dep,
    db: AsyncSession = Depends(get_db),
):
    service = QuestionService(db)
    # tenant-free: fetch by id only
    q = await service.get(question_id)
    if not q:
        return Response(success=False, error="Question not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    try:
        updated = await service.update(q, question_in)
        return Response(success=True, message="Question updated", data=updated.to_dict(), request=request)
    except ValueError as e:
        logger.error(f"[update_question] ValueError: {e}")
        return Response(success=False, error=str(e), request=request, status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"[update_question] Unexpected error: {type(e).__name__}: {e}")
        return Response(success=False, error=f"Update failed: {str(e)}", request=request, status_code=status.HTTP_400_BAD_REQUEST)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: uuid.UUID,
    request: Request,
    current_user: UserRead = lecturer_or_admin_dep,
    db: AsyncSession = Depends(get_db),
):
    service = QuestionService(db)
    tenant_id = None if current_user.role == "admin" else current_user.tenant_id
    q = await service.get(question_id, tenant_id=tenant_id)
    if not q:
        return Response(success=False, error="Question not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    await service.delete(q)
    return Response(success=True, message="Question deleted", request=request, status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# POST /upload  — lecturer uploads exam paper pages as base64 images
# ---------------------------------------------------------------------------

@router.post("/upload-exam-paper", status_code=status.HTTP_201_CREATED)
async def upload_exam_paper(
    body: ExamUpload,
    request: Request,
    current_user: UserRead = lecturer_or_admin_dep,
    db: AsyncSession = Depends(get_db),
):
    service = QuestionService(db)
    """Parse a typed/scanned exam paper and bulk-create questions in the background.

    Returns immediately with 202. Questions are created asynchronously.
    The client receives a WebSocket push when done:
      { "job_id": "<exam_id>", "status": "done", "created": N, "errors": [...] }
    """
    if not body.pages:
        return Response(success=False, error="No pages provided", request=request, status_code=status.HTTP_400_BAD_REQUEST)

    tenant_id = None if current_user.role == "admin" else str(current_user.tenant_id)

    # Enqueue exam parsing and question-creation to Celery worker
    parse_and_create_task.delay(body.pages, body.industry.value, str(body.exam_id), body.mark_per_question, tenant_id)

    return Response(
        success=True,
        message="Exam paper upload started — questions will be created in the background",
        data={"job_id": str(body.exam_id)},
        request=request,
        status_code=status.HTTP_202_ACCEPTED,
    )
