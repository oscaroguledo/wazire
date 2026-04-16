from __future__ import annotations

from typing import TypeVar, Type, Generic, Optional, List
from uuid import UUID
from contextlib import asynccontextmanager

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseRepository(Generic[ModelType]):
    """Base repository for common database operations."""
    
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions."""
        try:
            yield self
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
    
    async def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """Get entity by ID."""
        stmt = select(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all entities with pagination."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def create(self, entity: ModelType) -> ModelType:
        """Create entity."""
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity
    
    async def update(self, entity: ModelType) -> ModelType:
        """Update entity."""
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity
    
    async def delete(self, id: UUID) -> bool:
        """Delete entity by ID."""
        entity = await self.get_by_id(id)
        if not entity:
            return False
        await self.db.delete(entity)
        await self.db.commit()
        return True
    
    async def count(self) -> int:
        """Count total entities."""
        stmt = select(func.count()).select_from(self.model)
        result = await self.db.execute(stmt)
        return result.scalar()
    
    async def exists(self, id: UUID) -> bool:
        """Check if entity exists."""
        stmt = select(func.count()).where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar() > 0
