"""Class-based token utilities: JWT (HS256), opaque tokens, and timed signed tokens.

This module exposes `TokenService` only.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Dict, Optional, Tuple


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    s2 = s.encode("ascii")
    pad = b"=" * (-len(s2) % 4)
    return base64.urlsafe_b64decode(s2 + pad)


def _json_b64(obj: Any) -> str:
    return _b64url_encode(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def _b64_json(s: str) -> Any:
    raw = _b64url_decode(s)
    return json.loads(raw.decode("utf-8"))


class TokenService:
    """Service for creating and verifying tokens.

    Provide `default_secret` to avoid passing `secret` to each call.
    """

    def __init__(self, default_secret: Optional[str] = None):
        self.default_secret = default_secret

    # JWT (HS256)
    def create_jwt(self, payload: Dict[str, Any], secret: Optional[str] = None, algorithm: str = "HS256", expires_in: Optional[int] = None) -> str:
        if algorithm != "HS256":
            raise ValueError("Only HS256 is supported by this implementation")
        secret = secret or self.default_secret
        if secret is None:
            raise ValueError("secret is required to sign JWT")

        header = {"alg": "HS256", "typ": "JWT"}
        payload = dict(payload)
        if expires_in is not None:
            payload.setdefault("exp", int(time.time()) + int(expires_in))

        segments = [_json_b64(header), _json_b64(payload)]
        signing_input = ".".join(segments).encode("ascii")
        sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        segments.append(_b64url_encode(sig))
        return ".".join(segments)

    def verify_jwt(self, token: str, secret: Optional[str] = None, leeway: int = 0) -> Dict[str, Any]:
        secret = secret or self.default_secret
        if secret is None:
            raise ValueError("secret is required to verify JWT")

        try:
            header_s, payload_s, sig_s = token.split(".")
        except ValueError:
            raise ValueError("Invalid JWT structure")

        try:
            header = _b64_json(header_s)
            if header.get("alg") != "HS256":
                raise ValueError("Unsupported JWT alg")
        except Exception:
            raise ValueError("Invalid JWT header")

        signing_input = f"{header_s}.{payload_s}".encode("ascii")
        expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        try:
            sig = _b64url_decode(sig_s)
        except Exception:
            raise ValueError("Invalid JWT signature encoding")

        if not hmac.compare_digest(expected, sig):
            raise ValueError("Invalid JWT signature")

        payload = _b64_json(payload_s)
        exp = payload.get("exp")
        if exp is not None:
            now = int(time.time())
            if now > int(exp) + int(leeway):
                raise ValueError("JWT has expired")

        return payload

    # Opaque tokens (token + stored hash)
    def create_opaque_token(self, length: int = 32) -> Tuple[str, str]:
        token = secrets.token_urlsafe(length)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return token, token_hash

    def verify_opaque_token(self, token: str, token_hash: str) -> bool:
        if not token or not token_hash:
            return False
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return hmac.compare_digest(digest, token_hash)

    # Timed tokens
    def create_timed_token(self, obj: Any, secret: Optional[str] = None, expires_in: int = 3600) -> str:
        secret = secret or self.default_secret
        if secret is None:
            raise ValueError("secret is required to create timed token")
        payload_b64 = _json_b64(obj)
        ts = str(int(time.time()) + int(expires_in))
        signing_input = f"{payload_b64}.{ts}".encode("ascii")
        sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        return f"{payload_b64}.{ts}.{_b64url_encode(sig)}"

    def verify_timed_token(self, token: str, secret: Optional[str] = None) -> Any:
        secret = secret or self.default_secret
        if secret is None:
            raise ValueError("secret is required to verify timed token")
        try:
            payload_b64, ts_s, sig_s = token.split(".")
        except ValueError:
            raise ValueError("Invalid timed token structure")

        try:
            ts = int(ts_s)
        except Exception:
            raise ValueError("Invalid timestamp in token")

        signing_input = f"{payload_b64}.{ts_s}".encode("ascii")
        expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        try:
            sig = _b64url_decode(sig_s)
        except Exception:
            raise ValueError("Invalid signature encoding")

        if not hmac.compare_digest(expected, sig):
            raise ValueError("Invalid token signature")

        if int(time.time()) > ts:
            raise ValueError("Timed token has expired")

        return _b64_json(payload_b64)

    # Heuristic detection
    def detect_token_type(self, token: str) -> str:
        if not token:
            return "unknown"
        parts = token.split(".")
        if len(parts) == 3:
            try:
                h = _b64_json(parts[0])
                if isinstance(h, dict) and h.get("alg"):
                    return "jwt"
            except Exception:
                return "timed"

        if "." not in token and (all(c.isalnum() or c in "-_" for c in token) and len(token) >= 16):
            return "opaque"

        return "unknown"


__all__ = ["TokenService"]
