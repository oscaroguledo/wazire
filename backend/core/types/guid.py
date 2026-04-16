from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.types import TypeDecorator, BINARY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    - Uses Postgres native UUID when available (as_uuid=True).
    - Uses BINARY(16) (bytes) on other backends for compact storage.

    Python-level values are returned/accepted as ``uuid.UUID`` objects.
    """

    impl = BINARY(16)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(BINARY(16))

    def process_bind_param(self, value: Optional[Any], dialect) -> Optional[Any]:
        if value is None:
            return None

        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))

        if dialect.name == "postgresql":
            # let driver handle uuid object (psycopg/asyncpg accept uuid.UUID)
            return value

        # for other DBs store compact 16-byte representation
        return value.bytes

    def process_result_value(self, value: Optional[Any], dialect) -> Optional[uuid.UUID]:
        if value is None:
            return None

        if dialect.name == "postgresql":
            # expecting a uuid.UUID or string
            if isinstance(value, uuid.UUID):
                return value
            return uuid.UUID(str(value))

        # other backends return bytes - handle NULL/empty values
        if value == b'' or value is None:
            return None
        
        # Ensure we have exactly 16 bytes
        if len(value) != 16:
            return None
            
        return uuid.UUID(bytes=value)


__all__ = ["GUID"]
