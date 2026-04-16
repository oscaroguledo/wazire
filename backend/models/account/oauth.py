from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Index, UniqueConstraint, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.types.guid import GUID
from core.database import Base
from core.utils.uuid7 import uuid7


class OAuth(Base):
    """OAuth linkage for external providers.

    Fields:
    - id: UUID primary key (uuid7 time-ordered)
    - user_id: FK to `account.users.id` (local user)
    - provider: OAuth provider name (e.g. 'google', 'facebook')
    - provider_user_id: provider's user identifier
    - created_at / updated_at timestamps

    Notes:
    - Unique constraint on `(provider, provider_user_id)` ensures one mapping per external account.
    - Deleting a user cascades oauth rows (`ondelete="CASCADE"`).
    """

    __tablename__ = "oauth"
    __table_args__ = (
        # Composite index for common lookups by user and provider
        Index("ix_oauth_user_id_provider", "user_id", "provider"),
        # Uniqueness enforced by UniqueConstraint — no separate index needed
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
        {"schema": "account"},
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7, comment="Primary key: UUIDv7")
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("account.users.id", ondelete="CASCADE"), nullable=False, comment="FK to users")
    provider: Mapped[str] = mapped_column(String(50), nullable=False, comment="OAuth provider name, e.g. 'google', 'facebook'")
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False, comment="User ID from the OAuth provider")

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<OAuth(id={self.id}, user_id={self.user_id}, provider={self.provider})>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id) if self.id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "provider": self.provider,
            "provider_user_id": self.provider_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }