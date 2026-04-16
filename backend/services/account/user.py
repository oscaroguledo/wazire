from __future__ import annotations

from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models.account.users import User as UserModel
from schemas.account.users import UserCreate, UserUpdate
from core.utils.encryption import EncryptionService
from core.utils.token import TokenService
from core.repositories.account import UserRepository


class UserService:
    def __init__(self, db: AsyncSession, encryption: Optional[EncryptionService] = None, token_service: Optional[TokenService] = None):
        self.db = db
        self.encryption = encryption
        self.token_service = token_service
        self.user_repo = UserRepository(db)

    async def get_by_email(self, email: str, tenant_id: Optional[UUID] = None) -> Optional[UserModel]:
        if tenant_id:
            return await self.user_repo.get_by_email_and_tenant(email, tenant_id)
        return await self.user_repo.get_by_email(email)

    async def get(self, user_id, tenant_id: Optional[UUID] = None) -> Optional[UserModel]:
        user = await self.user_repo.get_by_id(user_id)
        if tenant_id and user and user.tenant_id != tenant_id:
            return None
        return user

    async def create(self, user_in: UserCreate, tenant_id: Optional[UUID] = None) -> UserModel:
        if not self.encryption:
            raise RuntimeError("EncryptionService required to create users")
        hashed = self.encryption.hash_password(user_in.password)
        user = UserModel(
            first_name=user_in.first_name,
            middle_name=user_in.middle_name,
            last_name=user_in.last_name,
            email=user_in.email,
            password=hashed,
            role=user_in.role,
            tenant_id=tenant_id or user_in.tenant_id,
            institution_id=user_in.institution_id,
            is_active=True,
        )
        return await self.user_repo.create(user)

    async def authenticate(self, email: str, password: str, tenant_id: Optional[UUID] = None) -> Optional[UserModel]:
        """Authenticate user with email and password."""
        if not self.encryption:
            raise RuntimeError("EncryptionService required for authentication")

        user = await self.get_by_email(email, tenant_id=tenant_id)
        if not user or not user.is_active:
            return None

        if self.encryption.verify_password(user.password, password):
            return user
        return None
    
    async def generate_auth_tokens(self, user: UserModel) -> Dict[str, str]:
        """Generate authentication tokens for user."""
        if not self.token_service:
            raise RuntimeError("TokenService required for token generation")
        
        # Normalize role to lowercase string for consistent JWT claims
        role_value = user.role.value if hasattr(user.role, 'value') else str(user.role)
        role_value = role_value.lower()

        # JWT access token (short-lived)
        access_payload = {
            "user_id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": role_value,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "is_active": user.is_active,
            "token_type": "access"
        }
        access_token = self.token_service.create_jwt(
            payload=access_payload,
            expires_in=3600  # 1 hour
        )
        
        # JWT refresh token (long-lived)
        refresh_payload = {
            "user_id": str(user.id),
            "token_type": "refresh",
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        }
        refresh_token = self.token_service.create_jwt(
            payload=refresh_payload,
            expires_in=86400 * 7  # 7 days
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        if not self.token_service:
            raise RuntimeError("TokenService required for token verification")
        
        try:
            payload = self.token_service.verify_jwt(token)
            return payload
        except ValueError:
            return None
    
    async def refresh_access_token(self, refresh_token: str, tenant_id: Optional[UUID] = None) -> Optional[Dict[str, str]]:
        """Generate new access token from refresh token."""
        if not self.token_service:
            raise RuntimeError("TokenService required for token refresh")

        try:
            payload = self.token_service.verify_jwt(refresh_token)
            if payload.get("token_type") != "refresh":
                return None

            user_id = payload.get("user_id")
            token_tenant = payload.get("tenant_id")
            user = await self.get(user_id, tenant_id=tenant_id)
            if not user or not user.is_active:
                return None

            # Ensure refresh token tenant matches user tenant for non-admins
            role_str = user.role.value.lower() if hasattr(user.role, 'value') else str(user.role).lower()
            if role_str not in ("admin", "superadmin"):
                if not token_tenant or str(token_tenant) != str(user.tenant_id):
                    return None

            # Generate new access token
            role_value = user.role.value if hasattr(user.role, 'value') else str(user.role)
            role_value = role_value.lower()
            access_payload = {
                "user_id": str(user.id),
                "email": user.email,
                "role": role_value,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                "token_type": "access"
            }
            new_access_token = self.token_service.create_jwt(
                payload=access_payload,
                expires_in=3600  # 1 hour
            )

            return {
                "access_token": new_access_token,
                "token_type": "bearer"
            }
        except ValueError:
            return None
    async def update(self, user: UserModel, user_in: UserUpdate) -> UserModel:
        data = user_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            if field == 'password' and value:
                if not self.encryption:
                    raise RuntimeError("EncryptionService required to update passwords")
                value = self.encryption.hash_password(value)
            setattr(user, field, value)
        return await self.user_repo.update(user)

    async def delete(self, user: UserModel) -> None:
        await self.db.delete(user)
        await self.db.commit()

    async def list(self, limit: int = 50, offset: int = 0, tenant_id: Optional[UUID] = None, is_active: Optional[bool] = None) -> List[UserModel]:
        """List users with offset/limit pagination."""
        if tenant_id:
            users = await self.user_repo.get_by_tenant(tenant_id, skip=offset, limit=limit)
        elif is_active:
            users = await self.user_repo.get_active_users(skip=offset, limit=limit)
        else:
            users = await self.user_repo.get_all(skip=offset, limit=limit)
        
        # Filter by is_active if needed (repository doesn't support combined filters)
        if is_active is not None and tenant_id:
            users = [u for u in users if u.is_active == is_active]
        
        # Sort by created_at desc, id desc
        users.sort(key=lambda u: (u.created_at or 0, u.id), reverse=True)
        return users

    async def count(self, tenant_id: Optional[UUID] = None, is_active: Optional[bool] = None) -> int:
        if tenant_id:
            users = await self.user_repo.get_by_tenant(tenant_id)
        elif is_active:
            users = await self.user_repo.get_active_users()
        else:
            return await self.user_repo.count()
        
        # Filter by is_active if needed
        if is_active is not None and tenant_id:
            users = [u for u in users if u.is_active == is_active]
        
        return len(users)
