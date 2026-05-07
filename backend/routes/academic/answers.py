from __future__ import annotations

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.utils.response import Response
from core.utils.token import TokenService
from core.middleware.auth import get_token_service, create_auth_dependency, require_lecturer_or_admin
from core.utils.kafka.manager import kafka_manager
from services.academic.answers import AnswerService
from services.academic.student_answer import StudentAnswerService
from schemas.academic.answer import AnswerCreate
from schemas.account.users import UserRead


router = APIRouter(prefix="/answers", tags=["answers"])


@router.patch("/{question_id}")
async def upsert_answer(
    question_id: uuid.UUID,
    body: AnswerCreate,
    request: Request,
    current_user: UserRead = Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """Save a student answer via Kafka (optimistic acknowledgement).

    The API emits a UPSERT_STUDENT_ANSWER Kafka event and returns HTTP 200
    immediately without waiting for the DB write.  The worker performs the
    atomic ON CONFLICT DO UPDATE asynchronously, decoupling API latency from
    DB write latency and providing a Kafka-backed buffer during DB pressure.
    """
    tenant_id = str(request.state.tenant_id) if hasattr(request.state, "tenant_id") and request.state.tenant_id else None

    ok = await kafka_manager.emit(
        "UPSERT_STUDENT_ANSWER",
        {
            "student_id": str(current_user.id),
            "exam_id": str(body.exam_id),
            "question_id": str(question_id),
            "answer": body.answer,
            "tenant_id": tenant_id,
        },
        partition_key=str(current_user.id),  # student_id as partition key for UPSERT_STUDENT_ANSWER
    )

    if not ok:
        return Response(
            success=False,
            error="Failed to queue answer — please retry",
            request=request,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Optimistic payload mirrors what the DB row will contain after the worker writes it
    optimistic_data = {
        "student_id": str(current_user.id),
        "exam_id": str(body.exam_id),
        "question_id": str(question_id),
        "answer": body.answer,
    }
    return Response(success=True, message="Answer saved", data=optimistic_data, request=request)


@router.get("/student")
async def list_student_answers(
    request: Request,
    exam_id: Optional[uuid.UUID] = None,
    current_user: UserRead = Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    if not exam_id:
        return Response(success=False, error="exam_id query param required", request=request, status_code=status.HTTP_400_BAD_REQUEST)
    service = StudentAnswerService(db)
    rows = await service.list(current_user.id, exam_id)
    return Response(success=True, message="Answers retrieved", data=[r.to_dict() for r in rows], request=request)


@router.get("/")
async def list_answers(
    request: Request,
    page: int = 1,
    per_page: int = 50,
    current_user: UserRead = Depends(require_lecturer_or_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """List all answer records with offset/limit pagination (lecturer/admin only)."""
    service = AnswerService(db)
    # Calculate offset from page
    offset = (page - 1) * per_page

    # Use offset/limit pagination
    items, total = await service.list(limit=per_page, offset=offset)

    # Calculate total pages
    total_pages = (total + per_page - 1) // per_page

    return Response(
        success=True,
        message="Answers retrieved",
        data=[i.to_dict() for i in items],
        page=page, per_page=per_page, total=total,
        request=request,
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_answer(
    answer_in: AnswerCreate,
    request: Request,
    current_user: UserRead = Depends(require_lecturer_or_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """Create a new answer record (lecturer/admin only)."""
    service = AnswerService(db)
    answer = await service.create(answer_in)
    return Response(success=True, message="Answer created", data=answer.to_dict(), request=request, status_code=status.HTTP_201_CREATED)


@router.get("/{answer_id}")
async def get_answer(
    answer_id: uuid.UUID,
    request: Request,
    current_user: UserRead = Depends(require_lecturer_or_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific answer (lecturer/admin only)."""
    service = AnswerService(db)
    a = await service.get(answer_id)
    if not a:
        return Response(success=False, error="Answer not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    return Response(success=True, message="Answer retrieved", data=a.to_dict(), request=request)


@router.delete("/{answer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_answer(
    answer_id: uuid.UUID,
    request: Request,
    current_user: UserRead = Depends(require_lecturer_or_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    """Delete an answer record (lecturer/admin only)."""
    service = AnswerService(db)
    a = await service.get(answer_id)
    if not a:
        return Response(success=False, error="Answer not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    await service.delete(a)
    return Response(success=True, message="Answer deleted", request=request, status_code=status.HTTP_204_NO_CONTENT)
