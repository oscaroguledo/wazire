"""Service layer for PaymentMethod CRUD operations."""
from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.billings.payment import PaymentMethod


class PaymentMethodService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, method_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[PaymentMethod]:
        stmt = select(PaymentMethod).where(PaymentMethod.id == method_id)
        if tenant_id:
            stmt = stmt.where(PaymentMethod.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        tenant_id: Optional[UUID] = None,
    ) -> Tuple[List[PaymentMethod], int]:
        """List payment methods with pagination. Returns (items, total_count)."""
        stmt = select(PaymentMethod)
        count_stmt = select(func.count()).select_from(PaymentMethod)

        if tenant_id:
            stmt = stmt.where(PaymentMethod.tenant_id == tenant_id)
            count_stmt = count_stmt.where(PaymentMethod.tenant_id == tenant_id)

        total = int((await self.db.execute(count_stmt)).scalar_one())
        stmt = stmt.order_by(PaymentMethod.created_at.desc()).offset(offset).limit(limit)
        items = (await self.db.execute(stmt)).scalars().all()
        return list(items), total

    async def create(self, data: dict, tenant_id: UUID, created_by: Optional[UUID] = None) -> PaymentMethod:
        method = PaymentMethod(
            tenant_id=tenant_id,
            created_by=created_by,
            updated_by=created_by,
            **{k: v for k, v in data.items() if k not in ("tenant_id", "created_by", "updated_by")},
        )
        self.db.add(method)
        await self.db.commit()
        await self.db.refresh(method)
        return method

    async def update(self, method: PaymentMethod, data: dict, updated_by: Optional[UUID] = None) -> PaymentMethod:
        for field, value in data.items():
            if hasattr(method, field):
                setattr(method, field, value)
        if updated_by:
            method.updated_by = updated_by
        self.db.add(method)
        await self.db.commit()
        await self.db.refresh(method)
        return method

    async def delete(self, method: PaymentMethod) -> None:
        await self.db.delete(method)
        await self.db.commit()

    async def set_default(self, method_id: UUID, tenant_id: UUID) -> Optional[PaymentMethod]:
        """Set a payment method as default, clearing any existing default."""
        # Clear existing default
        existing_stmt = select(PaymentMethod).where(
            PaymentMethod.tenant_id == tenant_id,
            PaymentMethod.is_default.is_(True),
        )
        existing = (await self.db.execute(existing_stmt)).scalars().all()
        for m in existing:
            m.is_default = False
            self.db.add(m)

        # Set new default
        method = await self.get(method_id, tenant_id)
        if not method:
            return None
        method.is_default = True
        self.db.add(method)
        await self.db.commit()
        await self.db.refresh(method)
        return method
