"""UUIDv7 generator utility.

This module provides a small, dependency-free implementation of UUID version 7
as described in the UUID revision drafts: a time-ordered UUID made from a
48-bit unix timestamp in milliseconds plus random bits. The implementation
creates a 128-bit value where the top 48 bits are the timestamp (big-endian),
then 80 bits of randomness. It also sets the RFC-4122 variant and the version
(7) bits so the returned object is a valid UUID instance.

The format is intentionally simple and suitable for database primary keys
or model IDs where time-ordering is desired.
"""

from __future__ import annotations

import time
import uuid
import secrets
from typing import Union


def uuid7() -> uuid.UUID:
	"""Generate a UUIDv7-like UUID instance.

	Returns:
		uuid.UUID: A UUID object (version field set to 7 and variant set per RFC).
	"""
	# 48-bit unix timestamp in milliseconds
	ts_ms = int(time.time() * 1000) & ((1 << 48) - 1)

	# 80 bits of randomness to fill the remaining 10 bytes
	rand80 = secrets.randbits(80)

	# Build 16-byte array: 6 bytes timestamp (big-endian) + 10 bytes randomness
	b = bytearray(ts_ms.to_bytes(6, "big") + rand80.to_bytes(10, "big"))

	# Set version (7) in the most-significant 4 bits of byte index 6
	b[6] = (b[6] & 0x0F) | (0x7 << 4)

	# Set RFC 4122 variant (10xx) in byte index 8
	b[8] = (b[8] & 0x3F) | 0x80

	return uuid.UUID(bytes=bytes(b))


def uuid7_str() -> str:
	"""Return canonical string form of a generated UUIDv7."""
	return str(uuid7())


def parse_uuid7(u: Union[str, uuid.UUID]) -> uuid.UUID:
	"""Return a UUID instance from a string or UUID input (no-op if already UUID)."""
	if isinstance(u, uuid.UUID):
		return u
	return uuid.UUID(str(u))


__all__ = ["uuid7", "uuid7_str", "parse_uuid7"]

