"""Service layer for Semester CRUD operations and billing lifecycle."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.account.users import Semester, SemesterStatus


class SemesterService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, semester_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[Semester]:
        stmt = select(Semester).where(Semester.id == semester_id)
        if tenant_id:
            stmt = stmt.where(Semester.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        tenant_id: Optional[UUID] = None,
        status: Optional[SemesterStatus] = None,
    ) -> Tuple[List[Semester], int]:
        """List semesters with pagination. Returns (items, total_count)."""
        stmt = select(Semester)
        count_stmt = select(func.count()).select_from(Semester)

        if tenant_id:
            stmt = stmt.where(Semester.tenant_id == tenant_id)
            count_stmt = count_stmt.where(Semester.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(Semester.status == status)
            count_stmt = count_stmt.where(Semester.status == status)

        total = int((await self.db.execute(count_stmt)).scalar_one())
        stmt = stmt.order_by(Semester.start_date.desc()).offset(offset).limit(limit)
        items = (await self.db.execute(stmt)).scalars().all()
        return list(items), total

    async def create(self, data: dict, tenant_id: UUID, created_by: Optional[UUID] = None) -> Semester:
        semester = Semester(
            tenant_id=tenant_id,
            created_by=created_by,
            updated_by=created_by,
            **{k: v for k, v in data.items() if k not in ("tenant_id", "created_by", "updated_by")},
        )
        self.db.add(semester)
        await self.db.commit()
        await self.db.refresh(semester)
        return semester

    async def update(self, semester: Semester, data: dict, updated_by: Optional[UUID] = None) -> Semester:
        for field, value in data.items():
            if hasattr(semester, field):
                setattr(semester, field, value)
        if updated_by:
            semester.updated_by = updated_by
        self.db.add(semester)
        await self.db.commit()
        await self.db.refresh(semester)
        return semester

    async def delete(self, semester: Semester) -> None:
        await self.db.delete(semester)
        await self.db.commit()

    async def mark_billed(self, semester_id: UUID, billed_at: Optional[datetime] = None) -> Optional[Semester]:
        """Mark a semester as billed.

        Sets ``is_billed = True`` and ``billed_at`` atomically.
        This is called by the webhook handler after payment confirmation so that
        the invoice status update and semester billing flag are committed together
        in the same DB transaction.

        Args:
            semester_id: The UUID of the semester to mark as billed.
            billed_at: The UTC timestamp of the confirmed payment. Defaults to now().

        Returns:
            The updated Semester record, or None if not found.
        """
        semester = await self.get(semester_id)
        if not semester:
            return None

        semester.is_billed = True
        semester.billed_at = billed_at or datetime.now(timezone.utc)
        self.db.add(semester)
        # Caller is responsible for committing — this allows atomic commit with
        # the invoice status update in the webhook handler.
        return semester

    async def get_unbilled_ended(self, tenant_id: Optional[UUID] = None) -> List[Semester]:
        """Return ended semesters that have not yet been billed.

        Used by the scheduler billing job to detect semesters that need invoicing.
        """
        now = datetime.now(timezone.utc)
        stmt = select(Semester).where(
            Semester.end_date <= now,
            Semester.is_billed.is_(False),
            Semester.status == SemesterStatus.ENDED,
        )
        if tenant_id:
            stmt = stmt.where(Semester.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
