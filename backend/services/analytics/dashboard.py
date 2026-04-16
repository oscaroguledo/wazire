from __future__ import annotations

import uuid
from typing import Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.analytics.dashboard import LecturerDashboard, AdminDashboard, StudentDashboard
from models.account.users import User, UserRole
from schemas.analytics.dashboard import (
    LecturerDashboardResponse,
    AdminDashboardResponse,
    StudentDashboardResponse,
)


class DashboardService:
    """Service for managing dashboard analytics (auto-updated by database triggers)."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # -------------------------------------------------------------------------
    # Lecturer Dashboard
    # -------------------------------------------------------------------------
    
    async def get_or_create_lecturer_dashboard(self, lecturer_id: uuid.UUID) -> LecturerDashboard:
        """Get existing or create new lecturer dashboard."""
        import time
        start = time.time()
        
        stmt = select(LecturerDashboard).where(LecturerDashboard.lecturer_id == lecturer_id)
        result = await self.db.execute(stmt)
        dashboard = result.scalar_one_or_none()
        
        query_time = (time.time() - start) * 1000
        logger.debug(f"[DASHBOARD] Query time: {query_time:.2f}ms")
        
        if not dashboard:
            create_start = time.time()
            dashboard = LecturerDashboard(
                lecturer_id=lecturer_id,
                total_courses=0,
                total_exams=0,
                total_students=0,
                pending_submissions=0,
                graded_submissions=0,
                active_courses=0,
            )
            self.db.add(dashboard)
            await self.db.commit()
            await self.db.refresh(dashboard)
            create_time = (time.time() - create_start) * 1000
            logger.debug(f"[DASHBOARD] Create time: {create_time:.2f}ms")
        
        return dashboard
    
    async def get_lecturer_dashboard(self, lecturer_id: uuid.UUID) -> Optional[LecturerDashboardResponse]:
        """Get lecturer dashboard by lecturer ID."""
        dashboard = await self.get_or_create_lecturer_dashboard(lecturer_id)
        return LecturerDashboardResponse.model_validate(dashboard.to_dict()) if dashboard else None
    
    
    # -------------------------------------------------------------------------
    # Admin Dashboard
    # -------------------------------------------------------------------------
    
    async def get_or_create_admin_dashboard(self, admin_id: uuid.UUID) -> AdminDashboard:
        """Get existing or create new admin dashboard."""
        stmt = select(AdminDashboard).where(AdminDashboard.admin_id == admin_id)
        result = await self.db.execute(stmt)
        dashboard = result.scalar_one_or_none()
        
        if not dashboard:
            dashboard = AdminDashboard(
                admin_id=admin_id,
                total_users=0,
                total_lecturers=0,
                total_students=0,
                total_courses=0,
                total_exams=0,
                total_submissions=0,
                total_graded_submissions=0,
                total_pending_submissions=0,
            )
            self.db.add(dashboard)
            await self.db.commit()
            await self.db.refresh(dashboard)
        
        return dashboard
    
    async def get_admin_dashboard(self, admin_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None) -> Optional[AdminDashboardResponse]:
        """Get admin dashboard by admin ID. Returns cached data (auto-updated by triggers)."""
        dashboard = await self.get_or_create_admin_dashboard(admin_id)
        return AdminDashboardResponse.model_validate(dashboard.to_dict()) if dashboard else None
    
    
    # -------------------------------------------------------------------------
    # Student Dashboard
    # -------------------------------------------------------------------------
    
    async def get_or_create_student_dashboard(self, student_id: uuid.UUID) -> StudentDashboard:
        """Get existing or create new student dashboard."""
        stmt = select(StudentDashboard).where(StudentDashboard.student_id == student_id)
        result = await self.db.execute(stmt)
        dashboard = result.scalar_one_or_none()
        
        if not dashboard:
            dashboard = StudentDashboard(
                student_id=student_id,
                total_courses=0,
                total_exams=0,
                total_submissions=0,
                total_graded_submissions=0,
                total_pending_submissions=0,
                missed_exams=0,
                upcoming_exams=0,
            )
            self.db.add(dashboard)
            await self.db.commit()
            await self.db.refresh(dashboard)

        return dashboard
    
    async def get_student_dashboard(self, student_id: uuid.UUID) -> Optional[StudentDashboardResponse]:
        """Get student dashboard by student ID. Returns cached data (auto-updated by triggers)."""
        dashboard = await self.get_or_create_student_dashboard(student_id)
        return StudentDashboardResponse.model_validate(dashboard.to_dict()) if dashboard else None
    
    
    # -------------------------------------------------------------------------
    # User Dashboard (Unified)
    # -------------------------------------------------------------------------
    
    async def get_user_dashboard(self, user: User) -> Union[LecturerDashboardResponse, AdminDashboardResponse, StudentDashboardResponse]:
        """Get appropriate dashboard for user based on role."""
        if user.role == UserRole.LECTURER:
            return await self.get_lecturer_dashboard(user.id)
        elif user.role == UserRole.ADMIN or user.role == UserRole.SUPERADMIN:
            return await self.get_admin_dashboard(user.id, user.tenant_id)
        elif user.role == UserRole.STUDENT:
            return await self.get_student_dashboard(user.id)
        else:
            raise ValueError(f"Unknown user role: {user.role}")
