from __future__ import annotations

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.utils.response import Response
from core.utils.token import TokenService
from core.dependencies.common import get_token_service, lecturer_or_admin_dep, authenticated_dep
from services.academic.answer import AnswerService
from services.academic.student_answer import StudentAnswerService
from schemas.academic.answer import AnswerCreate
from schemas.academic.student_answer import StudentAnswerRead
from schemas.account.users import UserRead
from schemas.academic.answer import UpsertPayload


router = APIRouter(prefix="/answers", tags=["answers"])


@router.put("/{question_id}")
async def upsert_answer(
    question_id: uuid.UUID,
    body: UpsertPayload,
    request: Request,
    current_user: UserRead = authenticated_dep,
    db: AsyncSession = Depends(get_db),
):
    service = StudentAnswerService(db)
    try:
        sa = await service.upsert(current_user.id, body.exam_id, question_id, body.answer)
    except ValueError as e:
        return Response(success=False, error=str(e), request=request, status_code=status.HTTP_400_BAD_REQUEST)

    return Response(success=True, message="Answer saved", data=StudentAnswerRead.model_validate(sa), request=request)


@router.get("/student")
async def list_student_answers(
    request: Request,
    exam_id: Optional[uuid.UUID] = None,
    current_user: UserRead = authenticated_dep,
    db: AsyncSession = Depends(get_db),
):
    service = StudentAnswerService(db)
    if not exam_id:
        return Response(success=False, error="exam_id query param required", request=request, status_code=status.HTTP_400_BAD_REQUEST)
    rows = await service.list_for_student_exam(current_user.id, exam_id)
    return Response(success=True, message="Answers retrieved", data=[StudentAnswerRead.model_validate(r) for r in rows], request=request)


@router.get("/")
async def list_answers(
    request: Request,
    page: int = 1,
    per_page: int = 50,
    current_user: UserRead = lecturer_or_admin_dep,
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
        pagination={
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        },
        request=request
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_answer(
    answer_in: AnswerCreate,
    request: Request,
    current_user: UserRead = lecturer_or_admin_dep,
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
    current_user: UserRead = lecturer_or_admin_dep,
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
    current_user: UserRead = lecturer_or_admin_dep,
    db: AsyncSession = Depends(get_db),
):
    """Delete an answer record (lecturer/admin only)."""
    service = AnswerService(db)
    a = await service.get(answer_id)
    if not a:
        return Response(success=False, error="Answer not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    await service.delete(a)
    return Response(success=True, message="Answer deleted", request=request, status_code=status.HTTP_204_NO_CONTENT)
