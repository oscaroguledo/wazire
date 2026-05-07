"""Service layer for BillingPlan CRUD operations."""
from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.billings.plan import BillingPlan


class BillingPlanService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, plan_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[BillingPlan]:
        stmt = select(BillingPlan).where(BillingPlan.id == plan_id)
        if tenant_id:
            stmt = stmt.where(BillingPlan.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        tenant_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[BillingPlan], int]:
        """List billing plans with pagination. Returns (items, total_count)."""
        stmt = select(BillingPlan)
        count_stmt = select(func.count()).select_from(BillingPlan)

        if tenant_id:
            stmt = stmt.where(BillingPlan.tenant_id == tenant_id)
            count_stmt = count_stmt.where(BillingPlan.tenant_id == tenant_id)
        if is_active is not None:
            stmt = stmt.where(BillingPlan.is_active == is_active)
            count_stmt = count_stmt.where(BillingPlan.is_active == is_active)

        total = int((await self.db.execute(count_stmt)).scalar_one())
        stmt = stmt.order_by(BillingPlan.created_at.desc()).offset(offset).limit(limit)
        items = (await self.db.execute(stmt)).scalars().all()
        return list(items), total

    async def create(self, data: dict, tenant_id: UUID, created_by: Optional[UUID] = None) -> BillingPlan:
        plan = BillingPlan(
            tenant_id=tenant_id,
            created_by=created_by,
            updated_by=created_by,
            **{k: v for k, v in data.items() if k not in ("tenant_id", "created_by", "updated_by")},
        )
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def update(self, plan: BillingPlan, data: dict, updated_by: Optional[UUID] = None) -> BillingPlan:
        for field, value in data.items():
            if hasattr(plan, field):
                setattr(plan, field, value)
        if updated_by:
            plan.updated_by = updated_by
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def delete(self, plan: BillingPlan) -> None:
        await self.db.delete(plan)
        await self.db.commit()
