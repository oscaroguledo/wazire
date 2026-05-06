from __future__ import annotations

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy import select, func as sqlfunc, table, column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.account.tenant import Tenant as TenantModel
from models.account.users import User as UserModel
from models.academic.course import Course as CourseModel
from models.academic.exam import Exam as ExamModel
from schemas.account.tenant import TenantCreate, TenantUpdate


class TenantService:
    def __init__(self, db: AsyncSession, token_service=None):
        self.db = db
        self.token_service = token_service

    async def get(self, tenant_id: UUID, name: Optional[str] = None,domain: Optional[str] = None) -> Optional[TenantModel]:
        stmt = select(TenantModel).options(
            selectinload(TenantModel.admins),
            selectinload(TenantModel.invoices),
            selectinload(TenantModel.usage),
            selectinload(TenantModel.payment_methods)
        ).where(TenantModel.id == tenant_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_for_admin(self, admin_user_id: UUID, limit: int = 50, offset: int = 0) -> Tuple[List[TenantModel], int]:
        """Get tenants where the user is an admin using offset pagination.

        Returns a tuple of (items, total_count).
        """
        # Build a subquery selecting tenant_ids from the tenant_admins association table
        tenant_admins = table("tenant_admins", column("tenant_id"), column("user_id"))

        tenant_ids_stmt = select(tenant_admins.c.tenant_id).where(tenant_admins.c.user_id == str(admin_user_id))

        # Query tenants matching the tenant_ids
        stmt = select(TenantModel).options(
            selectinload(TenantModel.invoices),
            selectinload(TenantModel.usage),
            selectinload(TenantModel.payment_methods)
        ).where(TenantModel.id.in_(tenant_ids_stmt)).order_by(TenantModel.created_at.desc(), TenantModel.id.desc()).offset(offset).limit(limit)

        res = await self.db.execute(stmt)
        items = res.scalars().all()

        # total count
        count_stmt = select(sqlfunc.count()).select_from(TenantModel).where(TenantModel.id.in_(tenant_ids_stmt))
        total = int((await self.db.execute(count_stmt)).scalar_one())

        return items, total

    async def create(self, tenant_in: TenantCreate) -> TenantModel:
        # Create tenant first
        tenant = TenantModel(
            name=tenant_in.name,
            domain=tenant_in.domain,
            logo_url=tenant_in.logo_url,
            is_active=True,
        )
        self.db.add(tenant)
        await self.db.flush()

        # If initial admin user ids provided, link them via the association table
        # and update their tenant_id foreign key
        if getattr(tenant_in, 'admin_user_ids', None):
            stmt = select(TenantModel).options(
                selectinload(TenantModel.admins),
                selectinload(TenantModel.invoices),
                selectinload(TenantModel.usage),
                selectinload(TenantModel.payment_methods)
            ).where(TenantModel.id == tenant.id)
            res = await self.db.execute(stmt)
            tenant = res.scalar_one()

            user_stmt = select(UserModel).where(UserModel.id.in_(tenant_in.admin_user_ids))
            user_res = await self.db.execute(user_stmt)
            users = user_res.scalars().all()
            tenant.admins = users

            # Also set tenant_id on each admin user so /auth/me returns it
            for u in users:
                u.tenant_id = tenant.id
                self.db.add(u)

        await self.db.commit()
        await self.db.refresh(tenant)

        # Re-load with all relationships for Pydantic serialization
        stmt = select(TenantModel).options(
            selectinload(TenantModel.admins),
            selectinload(TenantModel.invoices),
            selectinload(TenantModel.usage),
            selectinload(TenantModel.payment_methods)
        ).where(TenantModel.id == tenant.id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def update(self, tenant: TenantModel, tenant_in: TenantUpdate) -> TenantModel:
        data = tenant_in.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(tenant, field, value)
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def list(self, limit: int = 50, offset: int = 0) -> Tuple[List[TenantModel], int]:
        """List tenants with offset pagination, returning items and total count."""
        stmt = select(TenantModel).options(selectinload(TenantModel.admins)).order_by(TenantModel.created_at.desc(), TenantModel.id.desc()).offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        items = res.scalars().all()

        count_stmt = select(sqlfunc.count()).select_from(TenantModel)
        total = int((await self.db.execute(count_stmt)).scalar_one())

        return list(items), total

    async def delete(self, tenant: TenantModel) -> None:
        await self.db.delete(tenant)
        await self.db.commit()

    async def get_tenant_users(self, tenant_id: UUID, limit: int = 50, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """Get users in a tenant with their details and total count."""
        stmt = select(UserModel).where(UserModel.tenant_id == tenant_id).order_by(UserModel.created_at.desc()).offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        users = res.scalars().all()

        count_stmt = select(sqlfunc.count()).select_from(UserModel).where(UserModel.tenant_id == tenant_id)
        total = int((await self.db.execute(count_stmt)).scalar_one())

        return [
            {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at
            }
            for user in users
        ], total

    async def get_tenant_stats(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get tenant statistics."""

        # Count users by role
        user_stmt = select(UserModel).where(UserModel.tenant_id == tenant_id)
        user_res = await self.db.execute(user_stmt)
        all_users = user_res.scalars().all()

        total_users = len(all_users)
        total_students = len([u for u in all_users if str(u.role).lower() in ('student', 'userrole.student')])
        total_lecturers = len([u for u in all_users if str(u.role).lower() in ('lecturer', 'userrole.lecturer')])

        # Count courses
        course_count_stmt = select(sqlfunc.count()).select_from(CourseModel).where(CourseModel.tenant_id == tenant_id)
        course_count_res = await self.db.execute(course_count_stmt)
        total_courses = int(course_count_res.scalar_one())

        # Count exams
        exam_count_stmt = select(sqlfunc.count()).select_from(ExamModel).where(ExamModel.tenant_id == tenant_id)
        exam_count_res = await self.db.execute(exam_count_stmt)
        total_exams = int(exam_count_res.scalar_one())

        return {
            "tenant_id": str(tenant_id),
            "total_users": total_users,
            "total_students": total_students,
            "total_lecturers": total_lecturers,
            "total_courses": total_courses,
            "total_exams": total_exams,
        }
