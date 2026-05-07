from __future__ import annotations

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.billings.invoice import Invoice
from models.account.users import User

class InvoiceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, invoice_id) -> Optional[Invoice]:
        stmt = select(Invoice).where(Invoice.id == invoice_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def mark_paid(self, invoice_id, updated_by=None) -> Optional[Invoice]:
        inv = await self.get(invoice_id)
        if not inv:
            return None

        # Best-effort: set status to 'PAID'
        try:
            inv.status = "PAID"
        except Exception:
            # If the model doesn't expose a mapped `status`, fall back to raw SQL
            await self.db.execute(
                """
                UPDATE billings.invoices SET status = 'PAID', updated_by = :updated_by, updated_at = now() WHERE id = :id
                """,
                {"updated_by": str(updated_by) if updated_by else None, "id": str(invoice_id)},
            )
            await self.db.commit()
            return await self.get(invoice_id)

        inv.updated_by = updated_by
        self.db.add(inv)
        await self.db.commit()
        await self.db.refresh(inv)
        return inv
