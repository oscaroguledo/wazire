"""Service layer for Invoice CRUD and payment lifecycle operations."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.billings.invoice import Invoice, InvoiceStatus


class InvoiceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, invoice_id: UUID, tenant_id: Optional[UUID] = None) -> Optional[Invoice]:
        stmt = select(Invoice).where(Invoice.id == invoice_id)
        if tenant_id:
            stmt = stmt.where(Invoice.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_reference(self, payment_reference: str) -> Optional[Invoice]:
        """Look up an invoice by its payment gateway reference."""
        stmt = select(Invoice).where(Invoice.payment_reference == payment_reference)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        tenant_id: Optional[UUID] = None,
        status: Optional[InvoiceStatus] = None,
    ) -> Tuple[List[Invoice], int]:
        """List invoices with pagination. Returns (items, total_count)."""
        stmt = select(Invoice)
        count_stmt = select(func.count()).select_from(Invoice)

        if tenant_id:
            stmt = stmt.where(Invoice.tenant_id == tenant_id)
            count_stmt = count_stmt.where(Invoice.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(Invoice.status == status)
            count_stmt = count_stmt.where(Invoice.status == status)

        total = int((await self.db.execute(count_stmt)).scalar_one())
        stmt = stmt.order_by(Invoice.created_at.desc()).offset(offset).limit(limit)
        items = (await self.db.execute(stmt)).scalars().all()
        return list(items), total

    async def create(self, data: dict, tenant_id: UUID, created_by: Optional[UUID] = None) -> Invoice:
        invoice = Invoice(
            tenant_id=tenant_id,
            created_by=created_by,
            updated_by=created_by,
            **{k: v for k, v in data.items() if k not in ("tenant_id", "created_by", "updated_by")},
        )
        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    async def update(self, invoice: Invoice, data: dict, updated_by: Optional[UUID] = None) -> Invoice:
        for field, value in data.items():
            if hasattr(invoice, field):
                setattr(invoice, field, value)
        if updated_by:
            invoice.updated_by = updated_by
        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    async def mark_paid(
        self,
        invoice_id: UUID,
        paid_at: Optional[datetime] = None,
        updated_by: Optional[UUID] = None,
    ) -> Optional[Invoice]:
        """Mark an invoice as PAID.

        Sets status, paid_at, and updated_by atomically.
        """
        inv = await self.get(invoice_id)
        if not inv:
            return None
        inv.status = InvoiceStatus.PAID
        inv.paid_at = paid_at or datetime.now(timezone.utc)
        if updated_by:
            inv.updated_by = updated_by
        self.db.add(inv)
        await self.db.commit()
        await self.db.refresh(inv)
        return inv

    async def update_payment_details(
        self,
        invoice_id: UUID,
        payment_url: Optional[str] = None,
        payment_reference: Optional[str] = None,
        payment_gateway: Optional[str] = None,
    ) -> Optional[Invoice]:
        """Store payment gateway details on an invoice after initiation."""
        inv = await self.get(invoice_id)
        if not inv:
            return None
        if payment_url is not None:
            inv.payment_url = payment_url
        if payment_reference is not None:
            inv.payment_reference = payment_reference
        if payment_gateway is not None:
            inv.payment_gateway = payment_gateway
        self.db.add(inv)
        await self.db.commit()
        await self.db.refresh(inv)
        return inv
