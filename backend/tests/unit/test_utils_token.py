"""Unit tests for core.utils.token module.

Tests the TokenService class: JWT creation/verification, opaque tokens, and timed tokens.
"""
import time
import pytest
from core.utils.token import TokenService


SECRET = "test_secret_key_for_unit_tests"


class TestTokenServiceJWT:
    """Tests for JWT creation and verification."""

    def test_create_jwt_returns_three_part_string(self):
        """Test that create_jwt returns a dot-separated three-part string."""
        svc = TokenService(default_secret=SECRET)
        token = svc.create_jwt({"sub": "user-1"})
        
        parts = token.split(".")
        assert len(parts) == 3

    def test_verify_jwt_returns_payload(self):
        """Test that verify_jwt returns the original payload."""
        svc = TokenService(default_secret=SECRET)
        payload = {"sub": "user-1", "role": "student"}
        token = svc.create_jwt(payload)
        
        decoded = svc.verify_jwt(token)
        
        assert decoded["sub"] == "user-1"
        assert decoded["role"] == "student"

    def test_verify_jwt_wrong_secret_fails(self):
        """Test that verify_jwt raises ValueError for wrong secret."""
        svc = TokenService(default_secret=SECRET)
        token = svc.create_jwt({"sub": "user-1"})
        
        with pytest.raises(ValueError, match="Invalid JWT signature"):
            svc.verify_jwt(token, secret="wrong_secret")

    def test_verify_jwt_expired_raises(self):
        """Test that verify_jwt raises ValueError for expired token."""
        svc = TokenService(default_secret=SECRET)
        token = svc.create_jwt({"sub": "user-1"}, expires_in=-1)  # Already expired
        
        with pytest.raises(ValueError, match="JWT has expired"):
            svc.verify_jwt(token)

    def test_verify_jwt_expired_with_leeway_passes(self):
        """Test that verify_jwt passes for expired token within leeway."""
        svc = TokenService(default_secret=SECRET)
        token = svc.create_jwt({"sub": "user-1"}, expires_in=-1)  # Expired 1 second ago
        
        # With 10-second leeway, should pass
        decoded = svc.verify_jwt(token, leeway=10)
        assert decoded["sub"] == "user-1"

    def test_verify_jwt_invalid_structure_raises(self):
        """Test that verify_jwt raises ValueError for malformed token."""
        svc = TokenService(default_secret=SECRET)
        
        with pytest.raises(ValueError, match="Invalid JWT structure"):
            svc.verify_jwt("not.a.valid.jwt.token")

    def test_create_jwt_no_secret_raises(self):
        """Test that create_jwt raises ValueError if no secret is provided."""
        svc = TokenService()  # No default secret
        
        with pytest.raises(ValueError, match="secret is required"):
            svc.create_jwt({"sub": "user-1"})

    def test_create_jwt_unsupported_algorithm_raises(self):
        """Test that create_jwt raises ValueError for unsupported algorithm."""
        svc = TokenService(default_secret=SECRET)
        
        with pytest.raises(ValueError, match="Only HS256 is supported"):
            svc.create_jwt({"sub": "user-1"}, algorithm="RS256")


class TestTokenServiceOpaque:
    """Tests for opaque token creation and verification."""

    def test_create_opaque_token_returns_token_and_hash(self):
        """Test that create_opaque_token returns a (token, hash) tuple."""
        svc = TokenService()
        token, token_hash = svc.create_opaque_token()
        
        assert isinstance(token, str)
        assert isinstance(token_hash, str)
        assert len(token) > 0
        assert len(token_hash) == 64  # SHA-256 hex digest

    def test_verify_opaque_token_correct(self):
        """Test that verify_opaque_token returns True for correct token."""
        svc = TokenService()
        token, token_hash = svc.create_opaque_token()
        
        assert svc.verify_opaque_token(token, token_hash) is True

    def test_verify_opaque_token_wrong_token(self):
        """Test that verify_opaque_token returns False for wrong token."""
        svc = TokenService()
        _, token_hash = svc.create_opaque_token()
        
        assert svc.verify_opaque_token("wrong_token", token_hash) is False

    def test_verify_opaque_token_empty_inputs(self):
        """Test that verify_opaque_token returns False for empty inputs."""
        svc = TokenService()
        
        assert svc.verify_opaque_token("", "hash") is False
        assert svc.verify_opaque_token("token", "") is False


class TestTokenServiceTimed:
    """Tests for timed token creation and verification."""

    def test_create_and_verify_timed_token(self):
        """Test that timed token can be created and verified."""
        svc = TokenService(default_secret=SECRET)
        obj = {"user_id": "user-1", "action": "verify_email"}
        
        token = svc.create_timed_token(obj, expires_in=3600)
        decoded = svc.verify_timed_token(token)
        
        assert decoded["user_id"] == "user-1"
        assert decoded["action"] == "verify_email"

    def test_verify_timed_token_expired_raises(self):
        """Test that verify_timed_token raises ValueError for expired token."""
        svc = TokenService(default_secret=SECRET)
        token = svc.create_timed_token({"data": "test"}, expires_in=-1)
        
        with pytest.raises(ValueError, match="Timed token has expired"):
            svc.verify_timed_token(token)

    def test_verify_timed_token_wrong_secret_raises(self):
        """Test that verify_timed_token raises ValueError for wrong secret."""
        svc = TokenService(default_secret=SECRET)
        token = svc.create_timed_token({"data": "test"})
        
        with pytest.raises(ValueError, match="Invalid token signature"):
            svc.verify_timed_token(token, secret="wrong_secret")


class TestTokenServiceDetect:
    """Tests for token type detection."""

    def test_detect_jwt(self):
        """Test that detect_token_type correctly identifies JWT tokens."""
        svc = TokenService(default_secret=SECRET)
        token = svc.create_jwt({"sub": "user-1"})
        
        assert svc.detect_token_type(token) == "jwt"

    def test_detect_opaque(self):
        """Test that detect_token_type correctly identifies opaque tokens."""
        svc = TokenService()
        token, _ = svc.create_opaque_token()
        
        assert svc.detect_token_type(token) == "opaque"

    def test_detect_empty_returns_unknown(self):
        """Test that detect_token_type returns 'unknown' for empty string."""
        svc = TokenService()
        
        assert svc.detect_token_type("") == "unknown"
