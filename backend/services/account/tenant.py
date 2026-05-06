from __future__ import annotations

from typing import Optional, List, Tuple, Any, Dict
from uuid import UUID
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select, or_, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from models.account.tenant import Tenant
from schemas.account.tenant import TenantCreate, TenantUpdate,TenantDelete


class TenantService:
    def __init__(self, db: AsyncSession, token_service=None):
        self.db = db
        self.token_service = token_service

    async def get(
        self,
        tenant_id: UUID,
        is_active: Optional[bool] = True,  
        is_deleted: Optional[bool] = False, 
    ) -> Optional[Tenant]:
        """Fetch a single tenant by primary key."""

        # ID first — hits primary key index immediately
        stmt = select(Tenant).where(Tenant.id == tenant_id)

        # Filter deleted — default excludes soft deleted records
        if is_deleted is not None:
            stmt = stmt.where(Tenant.is_deleted.is_(is_deleted))

        # Filter active — only apply if explicitly passed
        if is_active is not None:
            stmt = stmt.where(Tenant.is_active.is_(is_active))

        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        is_active: Optional[bool] = True,
        is_deleted: Optional[bool] = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[List[Tenant], int]:
        """List all tenants (superadmin use-case) with pagination.
        
        Returns (items, total_count) ordered by created_at desc, id desc.
        """

        # Build filters once, reuse for count and data query
        filters = []

        if is_deleted is not None:
            filters.append(Tenant.is_deleted.is_(is_deleted))   # ← fixed: was `if not is_deleted`
        if is_active is not None:
            filters.append(Tenant.is_active.is_(is_active))     # ← fixed: was == not .is_()
        if start_date is not None:
            filters.append(Tenant.created_at >= start_date)
        if end_date is not None:
            filters.append(Tenant.created_at <= end_date)

        # Efficient count — no subquery
        count_stmt = select(sqlfunc.count(Tenant.id)).where(*filters)
        total = int((await self.db.execute(count_stmt)).scalar_one())

        # Data query reuses same filters
        stmt = (
            select(Tenant)
            .where(*filters)
            .order_by(Tenant.created_at.desc(), Tenant.id.desc())
            .offset(offset)
            .limit(limit)
        )

        items_res = await self.db.execute(stmt)
        return list(items_res.scalars().all()), total

    async def create(self, tenant_in: TenantCreate) -> Tenant:
        """Create a new tenant and optionally link admin users.

        Raises HTTP 400 if name or domain already exists.
        Admin users are linked by updating their tenant_id FK to point at
        the new tenant (there is no separate many-to-many table).
        """
        # Uniqueness checks
        name   = tenant_in.name.strip().lower()
        domain = tenant_in.domain.strip().lower() if tenant_in.domain else None

        existing = (await self.db.execute(
            select(Tenant.name, Tenant.domain)
            .where(Tenant.is_deleted.is_(False))
            .where(
                or_(
                    Tenant.name == name,
                    Tenant.domain == domain if domain else False,
                )
            )
        )).all()

        for row in existing:
            if row.name == name:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant name already exists")
            if domain and row.domain == domain:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Domain already exists")
        
        # Create tenant
        tenant = Tenant(
            name=name,
            domain=domain,
            logo_url=tenant_in.logo_url,
            is_active=True,
            created_by=tenant_in.created_by,
            updated_by=tenant_in.created_by,
        )

        self.db.add(tenant)
        await self.db.flush()           # catch DB errors before commit
        await self.db.refresh(tenant)
        await self.db.commit()
        return tenant

    async def update(
        self,
        tenant_update: TenantUpdate,
    ) -> Tenant:
        # 1. Fetch the existing record from the DB
        tenant = await self.db.get(Tenant, tenant_update.id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Tenant not found"
            )
        
        # 2. Extract update data 
        # exclude_unset=True is the MVP here; it ignores fields not in the request payload.
        # We also exclude 'id' so we don't accidentally try to overwrite the PK.
        update_data = tenant_update.model_dump(exclude_unset=True, exclude={"id"})

        # 3. Domain uniqueness check (Logical Guard)
        new_domain = update_data.get("domain")
        if new_domain and new_domain != tenant.domain:
            # Check if another record (that isn't this one) already uses the domain
            query = select(Tenant.id).where(
                Tenant.domain == new_domain,
                Tenant.id != tenant.id,
                Tenant.is_deleted.is_(False),
            )
            domain_exists = (await self.db.execute(query)).scalar_one_or_none()
            
            if domain_exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Domain already exists"
                )

        # 4. Apply changes to the SQLAlchemy instance
        for field, value in update_data.items():
            setattr(tenant, field, value)

        # 5. Commit the transaction
        # SQLAlchemy tracks 'tenant' because we fetched it via the same session,
        # so we just need to commit and refresh.
        try:
            await self.db.commit()
            await self.db.refresh(tenant)
        except Exception as e:
            await self.db.rollback()
            # Log the error here if needed
            raise e

        return tenant

    async def delete(self, tenant_delete: TenantDelete) -> None:
        """Soft-delete the tenant (sets is_deleted, deleted_at, is_active=False)."""
        tenant = await self.db.get(Tenant, tenant_delete.id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        tenant.delete()  # model helper
        if tenant_delete.updated_by:
            tenant.updated_by = tenant_delete.updated_by
        self.db.add(tenant)
        await self.db.commit()

    async def restore(self, tenant_delete: TenantDelete) -> Tenant:
        """Restore a soft-deleted tenant."""
        tenant = await self.db.get(Tenant, tenant_delete.id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        tenant.restore()  # model helper
        if tenant_delete.updated_by:
            tenant.updated_by = tenant_delete.updated_by
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant
    async def hard_delete(self, tenant_id: UUID) -> None:
        """Permanently delete a tenant from the database."""
        tenant = await self.db.get(Tenant, tenant_id, with_for_update=True)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        await self.db.delete(tenant)
        await self.db.commit()
