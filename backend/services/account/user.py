from __future__ import annotations

from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID

from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from models.account.users import User
from schemas.account.users import UserCreate, UserUpdate
from core.utils.encryption import EncryptionService
from core.utils.token import TokenService


class UserService:
    def __init__(
        self,
        db: AsyncSession,
        encryption: Optional[EncryptionService] = None,
        token_service: Optional[TokenService] = None,
    ):
        self.db = db
        self.encryption = encryption
        self.token_service = token_service


    async def get(
        self,
        user_id: Optional[UUID] = None,
        email: Optional[str] = None,
        tenant_id: Optional[UUID] = None,
    ) -> Optional[User]:
        """Fetch a single user by id or email, optionally scoped to a tenant."""
        if not user_id and not email:
            return None
        stmt = select(User)
        if user_id:
            stmt = stmt.where(User.id == user_id)
        if email:
            stmt = stmt.where(User.email == email)
        if tenant_id:
            stmt = stmt.where(User.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        tenant_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[User], int]:
        """List users with pagination. Returns (items, total_count)."""
        stmt = select(User)

        if tenant_id:
            stmt = stmt.where(User.tenant_id == tenant_id)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)

        count_stmt = select(sqlfunc.count()).select_from(stmt.order_by(None).subquery())
        total = int((await self.db.execute(count_stmt)).scalar_one())

        stmt = stmt.order_by(User.created_at.desc(), User.id.desc()).offset(offset).limit(limit)
        items = (await self.db.execute(stmt)).scalars().all()

        return list(items), total

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    async def create(self, user_in: UserCreate, tenant_id: Optional[UUID] = None) -> User:
        if not self.encryption:
            raise RuntimeError("EncryptionService required to create users")
        hashed = self.encryption.hash_password(user_in.password)
        user = User(
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
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    async def update(self, user: User, user_in: UserUpdate) -> User:
        data = user_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            if field == "password" and value:
                if not self.encryption:
                    raise RuntimeError("EncryptionService required to update passwords")
                value = self.encryption.hash_password(value)
            setattr(user, field, value)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    async def delete(self, user: User) -> None:
        user.delete()
        user.updated_by = user.id  # Assuming self-deletion, otherwise pass in deleter ID
        self.db.add(user)
        await self.db.commit()
    
    async def hard_delete(self, user: User) -> None:
        """Permanently delete a user from the database."""
        await self.db.delete(user)
        await self.db.commit()

    # ------------------------------------------------------------------
    # AUTH
    # ------------------------------------------------------------------

    async def authenticate(self, email: str, password: str, tenant_id: Optional[UUID] = None) -> Optional[User]:
        if not self.encryption:
            raise RuntimeError("EncryptionService required for authentication")
        user = await self.get(email=email, tenant_id=tenant_id)
        if not user or not user.is_active:
            return None
        if self.encryption.verify_password(user.password, password):
            return user
        return None

    async def generate_auth_tokens(self, user: User) -> Dict[str, str]:
        if not self.token_service:
            raise RuntimeError("TokenService required for token generation")

        role_value = user.role.value if hasattr(user.role, "value") else str(user.role)
        role_value = role_value.lower()

        access_payload = {
            "user_id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": role_value,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "is_active": user.is_active,
            "token_type": "access",
        }
        access_token = self.token_service.create_jwt(payload=access_payload, expires_in=3600)

        refresh_payload = {
            "user_id": str(user.id),
            "token_type": "refresh",
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        }
        refresh_token = self.token_service.create_jwt(payload=refresh_payload, expires_in=86400 * 7)

        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not self.token_service:
            raise RuntimeError("TokenService required for token verification")
        try:
            return self.token_service.verify_jwt(token)
        except ValueError:
            return None

    async def refresh_access_token(self, refresh_token: str, tenant_id: Optional[UUID] = None) -> Optional[Dict[str, str]]:
        if not self.token_service:
            raise RuntimeError("TokenService required for token refresh")
        try:
            payload = self.token_service.verify_jwt(refresh_token)
            if payload.get("token_type") != "refresh":
                return None

            user_id = payload.get("user_id")
            token_tenant = payload.get("tenant_id")
            user = await self.get(user_id=user_id, tenant_id=tenant_id)
            if not user or not user.is_active:
                return None

            role_str = user.role.value.lower() if hasattr(user.role, "value") else str(user.role).lower()
            if role_str not in ("admin", "superadmin"):
                if not token_tenant or str(token_tenant) != str(user.tenant_id):
                    return None

            role_value = user.role.value if hasattr(user.role, "value") else str(user.role)
            access_payload = {
                "user_id": str(user.id),
                "email": user.email,
                "role": role_value.lower(),
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                "token_type": "access",
            }
            new_access_token = self.token_service.create_jwt(payload=access_payload, expires_in=3600)
            return {"access_token": new_access_token, "token_type": "bearer"}
        except ValueError:
            return None
