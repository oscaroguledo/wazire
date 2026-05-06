from __future__ import annotations

import uuid
from typing import Optional
from fastapi import APIRouter, Request, Depends, Query, status
from core.utils.logger import logger
from sqlalchemy.ext.asyncio import AsyncSession
import traceback

from core.database import get_db
from core.utils.response import Response, offset
from core.utils.encryption import EncryptionService
from core.utils.token import TokenService
from core.middleware.auth import get_token_service, create_auth_dependency, require_admin, require_lecturer_or_admin
from services.account.user import UserService
from schemas.account.auth import AuthCreate, AuthUpdate, AuthRead
from schemas.account.users import UserCreate, UserUpdate, UserRead

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    encryption = EncryptionService()
    service = UserService(db, encryption=encryption, token_service=token_service)
    if getattr(request.state, "tenant_id", None):
        user_in.tenant_id = request.state.tenant_id
    if await service.get(email=user_in.email):
        return Response(success=False, error="Email already registered", request=request, status_code=status.HTTP_400_BAD_REQUEST)
    user = await service.create(user_in)
    return Response(success=True, message="Registered successfully", data=user.to_dict(), request=request, status_code=status.HTTP_201_CREATED)


@router.post("/login")
async def login(
    login_data: AuthCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    encryption = EncryptionService()
    service = UserService(db, encryption=encryption, token_service=token_service)
    tenant_id = getattr(request.state, "tenant_id", None)
    user = await service.authenticate(login_data.email, login_data.password, tenant_id=tenant_id)
    if not user:
        return Response(success=False, error="Invalid email or password", request=request, status_code=status.HTTP_401_UNAUTHORIZED)
    tokens = await service.generate_auth_tokens(user)
    return Response(success=True, message="Login successful", data=AuthRead(user=user.to_dict(), **tokens), request=request)


@router.post("/refresh")
async def refresh_token(
    body: AuthUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    encryption = EncryptionService()
    service = UserService(db, encryption=encryption, token_service=token_service)
    tenant_id = getattr(request.state, "tenant_id", None)
    result = await service.refresh_access_token(body.refresh_token, tenant_id=tenant_id)
    if not result:
        return Response(success=False, error="Invalid or expired refresh token", request=request, status_code=status.HTTP_401_UNAUTHORIZED)
    return Response(success=True, message="Token refreshed", data={"access_token": result["access_token"], "token_type": result["token_type"]}, request=request)


@router.get("/me")
async def me(
    request: Request,
    current_user: UserRead = Depends(create_auth_dependency(get_token_service())),
):
    return Response(success=True, message="Profile retrieved", data=current_user, request=request)


@router.put("/me")
async def update_me(
    user_in: UserUpdate,
    request: Request,
    current_user: UserRead = Depends(create_auth_dependency(get_token_service())),
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    encryption = EncryptionService()
    service = UserService(db, encryption=encryption, token_service=token_service)
    user = await service.get(user_id=current_user.id)
    if not user:
        return Response(success=False, error="User not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    updated = await service.update(user, user_in)
    return Response(success=True, message="Profile updated", data=updated.to_dict(), request=request)


@router.get("/")
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    is_active: Optional[bool] = None,
    tenant_id: Optional[uuid.UUID] = Query(None),
    current_user: UserRead = Depends(require_lecturer_or_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    try:
        encryption = EncryptionService()
        service = UserService(db, encryption=encryption, token_service=token_service)
        users, total = await service.list(
            limit=per_page, offset=offset(page, per_page),
            tenant_id=tenant_id, is_active=is_active,
        )
        return Response(success=True, message="Users retrieved", data=[u.to_dict() for u in users], page=page, per_page=per_page, total=total, request=request)
    except Exception as e:
        logger.error(f"list_users failed: {e}\n{traceback.format_exc()}")
        return Response(success=False, error=str(e), request=request, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/{user_id}")
async def get_user(
    user_id: uuid.UUID,
    request: Request,
    current_user: UserRead = Depends(require_lecturer_or_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    encryption = EncryptionService()
    service = UserService(db, encryption=encryption, token_service=token_service)
    tenant_id = None if current_user.role in ("admin", "superadmin") else current_user.tenant_id
    user = await service.get(user_id=user_id, tenant_id=tenant_id)
    if not user:
        return Response(success=False, error="User not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    return Response(success=True, message="User retrieved", data=user.to_dict(), request=request)


@router.put("/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    request: Request,
    current_user: UserRead = Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    encryption = EncryptionService()
    service = UserService(db, encryption=encryption, token_service=token_service)
    user = await service.get(user_id=user_id)
    if not user:
        return Response(success=False, error="User not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    updated = await service.update(user, user_in)
    return Response(success=True, message="User updated", data=updated.to_dict(), request=request)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    request: Request,
    current_user: UserRead = Depends(require_admin(get_token_service())),
    db: AsyncSession = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
):
    if user_id == current_user.id:
        return Response(success=False, error="Cannot delete your own account", request=request, status_code=status.HTTP_400_BAD_REQUEST)
    encryption = EncryptionService()
    service = UserService(db, encryption=encryption, token_service=token_service)
    user = await service.get(user_id=user_id)
    if not user:
        return Response(success=False, error="User not found", request=request, status_code=status.HTTP_404_NOT_FOUND)
    await service.delete(user)
    return Response(success=True, message="User deleted successfully", request=request)
