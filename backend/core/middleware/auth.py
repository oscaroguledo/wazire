from __future__ import annotations

from typing import Optional, List, Callable
from functools import wraps
import uuid
import time
import logging

from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.utils.token import TokenService
from core.config import get_settings
from services.account.user import UserService
from schemas.account.users import UserRead
from models.account.users import UserRole

logger = logging.getLogger(__name__)

security = HTTPBearer()


def get_token_service() -> TokenService:
    """Get TokenService instance with secret from settings."""
    settings = get_settings()
    return TokenService(settings.SECRET_KEY.get_secret_value() if settings.SECRET_KEY else None)

# In-memory cache for authenticated users
# Format: {user_id: (UserRead, expiry_timestamp)}
_user_cache: dict[uuid.UUID, tuple[UserRead, float]] = {}
CACHE_TTL = 300  # 5 minutes cache TTL


def _role_str(role) -> str:
    """Normalize a role value (enum or string) to lowercase."""
    if hasattr(role, 'value'):
        return role.value.lower()
    return str(role).lower()


def invalidate_user_cache(user_id: uuid.UUID) -> None:
    """Invalidate cache for a specific user (call after user updates)."""
    if user_id in _user_cache:
        del _user_cache[user_id]
        logger.info(f"[AUTH] Cache invalidated for user {user_id}")


class AuthMiddleware:
    def __init__(self, token_service: TokenService):
        self.token_service = token_service

    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db),
        request: Request = None,
    ) -> UserRead:
        import time
        start = time.time()
        
        try:
            payload = self.token_service.verify_jwt(credentials.credentials)

            if payload.get("token_type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            token_tenant = payload.get("tenant_id")

            raw_user_id = payload.get("user_id")
            if not raw_user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user_id"
                )
            try:
                user_uuid = uuid.UUID(str(raw_user_id))
            except (ValueError, AttributeError):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: malformed user_id"
                )

            after_jwt = time.time()
            logger.debug(f"[AUTH] JWT verification: {(after_jwt - start) * 1000:.2f}ms")

            # Check cache first
            current_time = time.time()
            cached_user, expiry = _user_cache.get(user_uuid, (None, 0))
            if cached_user and expiry > current_time:
                after_cache = time.time()
                logger.debug(f"[AUTH] Cache hit: {(after_cache - after_jwt) * 1000:.2f}ms")
                logger.debug(f"[AUTH] Total (cached): {(after_cache - start) * 1000:.2f}ms")
                return cached_user

            # Cache miss - query database
            user_service = UserService(db, token_service=self.token_service)
            user = await user_service.get(user_uuid)

            after_db = time.time()
            logger.debug(f"[AUTH] DB query: {(after_db - after_jwt) * 1000:.2f}ms")

            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )

            # Cache the user
            user_read = UserRead.model_validate(user)
            _user_cache[user_uuid] = (user_read, current_time + CACHE_TTL)

            # Prefer enum comparison on ORM `user.role` when possible
            if getattr(user, 'role', None) not in (UserRole.ADMIN, UserRole.SUPERADMIN):
                if token_tenant and user.tenant_id:
                    if str(user.tenant_id) != str(token_tenant):
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token tenant does not match user tenant"
                        )

            if request is not None:
                req_tid = getattr(request.state, "tenant_id", None)
                if req_tid and getattr(user, 'role', None) not in (UserRole.ADMIN, UserRole.SUPERADMIN):
                    if str(req_tid) != str(token_tenant):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Request tenant does not match token tenant"
                        )

            after_validation = time.time()
            print(f"[AUTH] Validation: {(after_validation - after_db) * 1000:.2f}ms")
            print(f"[AUTH] Total (DB): {(after_validation - start) * 1000:.2f}ms")

            return user_read

        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not validate credentials: {str(e)}"
            )

    async def get_optional_user(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: AsyncSession = Depends(get_db),
        request: Request = None,
    ) -> Optional[UserRead]:
        if not credentials:
            return None
        try:
            return await self.get_current_user(credentials, db, request)
        except HTTPException:
            return None


def create_auth_dependency(token_service: TokenService):
    auth_middleware = AuthMiddleware(token_service)
    return auth_middleware.get_current_user


def create_optional_auth_dependency(token_service: TokenService):
    auth_middleware = AuthMiddleware(token_service)
    return auth_middleware.get_optional_user


def require_admin(token_service: TokenService):
    async def admin_dependency(
        current_user: UserRead = Depends(create_auth_dependency(token_service))
    ) -> UserRead:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return current_user
    return admin_dependency


def require_superadmin(token_service: TokenService):
    async def superadmin_dependency(
        current_user: UserRead = Depends(create_auth_dependency(token_service))
    ) -> UserRead:
        if current_user.role != UserRole.SUPERADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superadmin access required"
            )
        return current_user
    return superadmin_dependency


def require_admin_or_superadmin(token_service: TokenService):
    async def admin_superadmin_dependency(
        current_user: UserRead = Depends(create_auth_dependency(token_service))
    ) -> UserRead:
        if current_user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or superadmin access required"
            )
        return current_user
    return admin_superadmin_dependency
def require_lecturer(token_service: TokenService):
    async def lecturer_dependency(
        current_user: UserRead = Depends(create_auth_dependency(token_service))
    ) -> UserRead:
        if current_user.role != UserRole.LECTURER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Lecturer access required"
            )
        return current_user
    return lecturer_dependency

def require_lecturer_or_admin(token_service: TokenService):
    async def lecturer_admin_dependency(
        current_user: UserRead = Depends(create_auth_dependency(token_service))
    ) -> UserRead:
        if current_user.role not in (UserRole.LECTURER, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Lecturer or admin access required"
            )
        return current_user
    return lecturer_admin_dependency


def require_student(token_service: TokenService):
    async def student_dependency(
        current_user: UserRead = Depends(create_auth_dependency(token_service))
    ) -> UserRead:
        if current_user.role != UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student access required"
            )
        return current_user
    return student_dependency


def require_student_or_above(token_service: TokenService):
    async def student_above_dependency(
        current_user: UserRead = Depends(create_auth_dependency(token_service))
    ) -> UserRead:
        if current_user.role not in (UserRole.STUDENT, UserRole.LECTURER, UserRole.ADMIN, UserRole.SUPERADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student access or higher required"
            )
        return current_user
    return student_above_dependency


def require_lecturer_or_admin_or_superadmin(token_service: TokenService):
    async def lecturer_admin_superadmin_dependency(
        current_user: UserRead = Depends(create_auth_dependency(token_service))
    ) -> UserRead:
        if current_user.role not in (UserRole.LECTURER, UserRole.ADMIN, UserRole.SUPERADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Lecturer, admin, or superadmin access required"
            )
        return current_user
    return lecturer_admin_superadmin_dependency


def require_same_tenant(token_service: TokenService):
    async def same_tenant_dependency(
        tenant_id: uuid.UUID,
        current_user: UserRead = Depends(create_auth_dependency(token_service))
    ) -> UserRead:
        if current_user.role == UserRole.ADMIN:
            return current_user
        if current_user.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Different tenant"
            )
        return current_user
    return same_tenant_dependency


def require_own_resource_or_admin(token_service: TokenService):
    async def own_resource_admin_dependency(
        user_id: uuid.UUID,
        current_user: UserRead = Depends(create_auth_dependency(token_service))
    ) -> UserRead:
        if current_user.role == UserRole.ADMIN:
            return current_user
        if current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Not your resource"
            )
        return current_user
    return own_resource_admin_dependency


def require_roles(allowed_roles: List[str]):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            # Normalize allowed_roles to UserRole enums for comparison
            normalized = set()
            for r in allowed_roles:
                try:
                    if isinstance(r, UserRole):
                        normalized.add(r)
                    else:
                        normalized.add(UserRole(str(r).lower()))
                except Exception:
                    # skip invalid role entries
                    continue
            if current_user.role not in normalized:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required roles: {', '.join([r.value for r in normalized])}"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_tenant_access(func: Callable):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        current_user = kwargs.get('current_user')
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        return await func(*args, **kwargs)
    return wrapper
