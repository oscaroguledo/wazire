from __future__ import annotations

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy import select, func as sqlfunc
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

    async def get(self, tenant_id: UUID) -> Optional[TenantModel]:
        stmt = select(TenantModel).options(
            selectinload(TenantModel.admins),
            selectinload(TenantModel.invoices),
            selectinload(TenantModel.usage),
            selectinload(TenantModel.payment_methods)
        ).where(TenantModel.id == tenant_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[TenantModel]:
        stmt = select(TenantModel).options(
            selectinload(TenantModel.admins),
            selectinload(TenantModel.invoices),
            selectinload(TenantModel.usage),
            selectinload(TenantModel.payment_methods)
        ).where(TenantModel.name == name)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_domain(self, domain: str) -> Optional[TenantModel]:
        stmt = select(TenantModel).options(
            selectinload(TenantModel.admins),
            selectinload(TenantModel.invoices),
            selectinload(TenantModel.usage),
            selectinload(TenantModel.payment_methods)
        ).where(TenantModel.domain == domain)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_for_admin(self, admin_user_id: UUID, limit: int = 50, cursor: Optional[str] = None) -> Tuple[List[TenantModel], Optional[str]]:
        """Get all tenants where the user is an admin using keyset pagination."""
        import base64
        from datetime import datetime as _dt
        
        # Get all tenants where user is admin
        all_tenants_stmt = select(TenantModel).options(
            selectinload(TenantModel.admins),
            selectinload(TenantModel.invoices),
            selectinload(TenantModel.usage),
            selectinload(TenantModel.payment_methods)
        )
        all_tenants_res = await self.db.execute(all_tenants_stmt)
        all_tenants = all_tenants_res.scalars().all()
        
        # Filter by admin user
        user_tenants = []
        for tenant in all_tenants:
            admin_ids = [str(admin.id) for admin in tenant.admins]
            if str(admin_user_id) in admin_ids:
                user_tenants.append(tenant)
        
        # Apply keyset pagination
        if cursor:
            try:
                raw = base64.urlsafe_b64decode(cursor.encode()).decode()
                ts, idstr = raw.split("|", 1)
                created_before, id_before = _dt.fromisoformat(ts), UUID(idstr)
            except Exception:
                raise ValueError("Invalid cursor")
            
            # Filter the already filtered list
            user_tenants = [
                t for t in user_tenants 
                if (t.created_at < created_before) or 
                   (t.created_at == created_before and t.id < id_before)
            ]
        
        # Sort by created_at desc, id desc
        user_tenants.sort(key=lambda t: (t.created_at, t.id), reverse=True)
        
        # Apply limit and generate next cursor
        next_cursor = None
        if len(user_tenants) > limit:
            last = user_tenants[limit]
            user_tenants = user_tenants[:limit]
            raw_next = f"{last.created_at.isoformat()}|{str(last.id)}"
            next_cursor = base64.urlsafe_b64encode(raw_next.encode()).decode()

        return user_tenants, next_cursor

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

    async def list(self, limit: int = 50, offset: int = 0, cursor: Optional[str] = None) -> Tuple[List[TenantModel], Optional[str]]:
        import base64
        from datetime import datetime as _dt
        if cursor:
            try:
                raw = base64.urlsafe_b64decode(cursor.encode()).decode()
                ts, idstr = raw.split("|", 1)
                created_before, id_before = _dt.fromisoformat(ts), UUID(idstr)
            except Exception:
                raise ValueError("Invalid cursor")
            stmt = select(TenantModel).options(
                selectinload(TenantModel.admins)
            ).where(
                (TenantModel.created_at < created_before)
                | ((TenantModel.created_at == created_before) & (TenantModel.id < id_before))
            ).order_by(TenantModel.created_at.desc(), TenantModel.id.desc()).limit(limit + 1)
        else:
            stmt = select(TenantModel).options(
                selectinload(TenantModel.admins)
            ).order_by(
                TenantModel.created_at.desc(), TenantModel.id.desc()
            ).offset(offset).limit(limit + 1)

        items = (await self.db.execute(stmt)).scalars().all()
        next_cursor = None
        if len(items) > limit:
            last = items[limit]
            items = items[:limit]
            raw_next = f"{last.created_at.isoformat()}|{str(last.id)}"
            next_cursor = base64.urlsafe_b64encode(raw_next.encode()).decode()

        return list(items), next_cursor

    async def delete(self, tenant: TenantModel) -> None:
        await self.db.delete(tenant)
        await self.db.commit()

    async def get_tenant_users(self, tenant_id: UUID, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get users in a tenant with their details."""
        
        stmt = select(UserModel).where(UserModel.tenant_id == tenant_id).offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        users = res.scalars().all()
        
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
        ]

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
