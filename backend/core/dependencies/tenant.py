from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.account.tenants import TenantService


async def get_current_tenant(request: Request, db: AsyncSession = Depends(get_db)) -> Optional[object]:
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        return None

    try:
        tid = UUID(tenant_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant id")

    svc = TenantService(db)
    tenant = await svc.get(tid)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant
