"""Service layer for CurrentUsage CRUD operations."""
from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.billings.usage import CurrentUsage


class UsageService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, usage_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[CurrentUsage]:
        stmt = select(CurrentUsage).where(CurrentUsage.id == usage_id)
        if tenant_id:
            stmt = stmt.where(CurrentUsage.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_for_tenant(self, tenant_id: UUID) -> Optional[CurrentUsage]:
        """Get the current usage record for a tenant (most recent)."""
        stmt = (
            select(CurrentUsage)
            .where(CurrentUsage.tenant_id == tenant_id)
            .order_by(CurrentUsage.created_at.desc())
            .limit(1)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        tenant_id: Optional[UUID] = None,
    ) -> Tuple[List[CurrentUsage], int]:
        """List usage records with pagination. Returns (items, total_count)."""
        stmt = select(CurrentUsage)
        count_stmt = select(func.count()).select_from(CurrentUsage)

        if tenant_id:
            stmt = stmt.where(CurrentUsage.tenant_id == tenant_id)
            count_stmt = count_stmt.where(CurrentUsage.tenant_id == tenant_id)

        total = int((await self.db.execute(count_stmt)).scalar_one())
        stmt = stmt.order_by(CurrentUsage.created_at.desc()).offset(offset).limit(limit)
        items = (await self.db.execute(stmt)).scalars().all()
        return list(items), total

    async def create(self, data: dict, tenant_id: UUID, created_by: Optional[UUID] = None) -> CurrentUsage:
        usage = CurrentUsage(
            tenant_id=tenant_id,
            created_by=created_by,
            updated_by=created_by,
            **{k: v for k, v in data.items() if k not in ("tenant_id", "created_by", "updated_by")},
        )
        self.db.add(usage)
        await self.db.commit()
        await self.db.refresh(usage)
        return usage

    async def update(self, usage: CurrentUsage, data: dict, updated_by: Optional[UUID] = None) -> CurrentUsage:
        for field, value in data.items():
            if hasattr(usage, field):
                setattr(usage, field, value)
        if updated_by:
            usage.updated_by = updated_by
        self.db.add(usage)
        await self.db.commit()
        await self.db.refresh(usage)
        return usage
