from __future__ import annotations

from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.account.users import User, UserRole
from core.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User entity operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email address."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_email_and_tenant(self, email: str, tenant_id: UUID) -> Optional[User]:
        """Get a user by email and tenant ID."""
        stmt = select(User).where(
            and_(User.email == email, User.tenant_id == tenant_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_role(self, role: UserRole, skip: int = 0, limit: int = 100) -> List[User]:
        """Get users by role with pagination."""
        stmt = select(User).where(User.role == role).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_tenant(
        self, 
        tenant_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        """Get users by tenant ID with pagination."""
        stmt = select(User).where(User.tenant_id == tenant_id).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get only active users with pagination."""
        stmt = select(User).where(User.is_active == True).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def email_exists(self, email: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if email exists (optionally excluding a specific user ID)."""
        stmt = select(User).where(User.email == email)
        if exclude_id:
            stmt = stmt.where(User.id != exclude_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
