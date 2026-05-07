"""Semester CRUD routes under /api/v1/billing/semesters."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.middleware.auth import create_auth_dependency, get_token_service, require_admin
from core.utils.response import Response
from models.account.users import SemesterStatus
from services.billings.semesters import SemesterService

router = APIRouter(prefix="/billing/semesters", tags=["billing"])


@router.get("/")
async def list_semesters(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    semester_status: Optional[SemesterStatus] = Query(None, alias="status"),
    tenant_id: Optional[uuid.UUID] = Query(None),
    current_user=Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    from models.account.users import UserRole

    effective_tenant_id = tenant_id
    if getattr(current_user, "role", None) not in (UserRole.ADMIN, UserRole.SUPERADMIN):
        effective_tenant_id = current_user.tenant_id

    svc = SemesterService(db)
    offset = (page - 1) * per_page
    items, total = await svc.list(
        limit=per_page,
        offset=offset,
        tenant_id=effective_tenant_id,
        status=semester_status,
    )
    return Response(
        success=True,
        message="Semesters retrieved",
        data=[s.to_dict() for s in items],
        page=page,
        per_page=per_page,
        total=total,
        request=request,
    )


@router.get("/{semester_id}")
async def get_semester(
    semester_id: uuid.UUID,
    request: Request,
    current_user=Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    from models.account.users import UserRole

    svc = SemesterService(db)
    tenant_id = None if getattr(current_user, "role", None) in (UserRole.ADMIN, UserRole.SUPERADMIN) else current_user.tenant_id
    semester = await svc.get(semester_id, tenant_id=tenant_id)
    if not semester:
        return Response(success=False, error="Semester not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    return Response(success=True, message="Semester retrieved", data=semester.to_dict(), request=request)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_semester(
    body: dict,
    request: Request,
    current_user=Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    svc = SemesterService(db)
    tenant_id = body.pop("tenant_id", None) or current_user.tenant_id
    semester = await svc.create(body, tenant_id=uuid.UUID(str(tenant_id)), created_by=current_user.id)
    return Response(success=True, message="Semester created", data=semester.to_dict(), request=request, status_code=status.HTTP_201_CREATED)


@router.put("/{semester_id}")
async def update_semester(
    semester_id: uuid.UUID,
    body: dict,
    request: Request,
    current_user=Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    svc = SemesterService(db)
    semester = await svc.get(semester_id)
    if not semester:
        return Response(success=False, error="Semester not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    updated = await svc.update(semester, body, updated_by=current_user.id)
    return Response(success=True, message="Semester updated", data=updated.to_dict(), request=request)


@router.delete("/{semester_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_semester(
    semester_id: uuid.UUID,
    request: Request,
    current_user=Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
):
    svc = SemesterService(db)
    semester = await svc.get(semester_id)
    if not semester:
        return Response(success=False, error="Semester not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    await svc.delete(semester)
    return Response(success=True, message="Semester deleted", request=request, status_code=status.HTTP_204_NO_CONTENT)
