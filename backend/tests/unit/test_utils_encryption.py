"""Unit tests for core.utils.encryption module.

Tests the EncryptionService class: password hashing, verification, HMAC, and AES-GCM.
"""
import pytest
from core.utils.encryption import EncryptionService


class TestEncryptionService:
    """Test suite for EncryptionService."""

    def test_hash_password_returns_pbkdf2_format(self):
        """Test that hash_password returns a string in pbkdf2_sha256 format."""
        svc = EncryptionService()
        hashed = svc.hash_password("test_password")
        
        assert isinstance(hashed, str)
        assert hashed.startswith("pbkdf2_sha256$")
        parts = hashed.split("$")
        assert len(parts) == 4
        assert parts[0] == "pbkdf2_sha256"
        assert int(parts[1]) == svc.pbkdf2_iters

    def test_verify_password_correct(self):
        """Test that verify_password returns True for correct password."""
        svc = EncryptionService()
        password = "correct_password"
        hashed = svc.hash_password(password)
        
        assert svc.verify_password(hashed, password) is True

    def test_verify_password_incorrect(self):
        """Test that verify_password returns False for incorrect password."""
        svc = EncryptionService()
        hashed = svc.hash_password("correct_password")
        
        assert svc.verify_password(hashed, "wrong_password") is False

    def test_verify_password_invalid_format(self):
        """Test that verify_password returns False for invalid hash format."""
        svc = EncryptionService()
        
        assert svc.verify_password("invalid_hash", "password") is False
        assert svc.verify_password(None, "password") is False
        assert svc.verify_password("", "password") is False

    def test_hmac_sha256_produces_32_bytes(self):
        """Test that hmac_sha256 produces a 32-byte digest."""
        svc = EncryptionService()
        key = b"secret_key"
        data = b"message"
        
        digest = svc.hmac_sha256(key, data)
        
        assert isinstance(digest, bytes)
        assert len(digest) == 32

    def test_hmac_sha256_deterministic(self):
        """Test that hmac_sha256 produces the same output for the same input."""
        svc = EncryptionService()
        key = b"secret_key"
        data = b"message"
        
        digest1 = svc.hmac_sha256(key, data)
        digest2 = svc.hmac_sha256(key, data)
        
        assert digest1 == digest2

    def test_generate_aes_key_length(self):
        """Test that generate_aes_key produces a key of the specified length."""
        svc = EncryptionService()
        
        key16 = svc.generate_aes_key(16)
        key32 = svc.generate_aes_key(32)
        
        assert len(key16) == 16
        assert len(key32) == 32

    def test_encrypt_decrypt_aes_roundtrip(self):
        """Test that AES encryption and decryption produce the original plaintext."""
        svc = EncryptionService()
        key = svc.generate_aes_key(32)
        plaintext = b"secret message"
        
        ciphertext = svc.encrypt_aes(plaintext, key=key)
        decrypted = svc.decrypt_aes(ciphertext, key=key)
        
        assert decrypted == plaintext

    def test_encrypt_aes_with_associated_data(self):
        """Test AES encryption with associated data (AEAD)."""
        svc = EncryptionService()
        key = svc.generate_aes_key(32)
        plaintext = b"secret message"
        associated_data = b"metadata"
        
        ciphertext = svc.encrypt_aes(plaintext, associated_data=associated_data, key=key)
        decrypted = svc.decrypt_aes(ciphertext, associated_data=associated_data, key=key)
        
        assert decrypted == plaintext

    def test_decrypt_aes_wrong_associated_data_fails(self):
        """Test that decryption fails if associated data doesn't match."""
        svc = EncryptionService()
        key = svc.generate_aes_key(32)
        plaintext = b"secret message"
        
        ciphertext = svc.encrypt_aes(plaintext, associated_data=b"correct", key=key)
        
        with pytest.raises(Exception):  # cryptography raises InvalidTag
            svc.decrypt_aes(ciphertext, associated_data=b"wrong", key=key)

    def test_encrypt_aes_no_key_raises(self):
        """Test that encrypt_aes raises ValueError if no key is provided."""
        svc = EncryptionService()  # No default key
        
        with pytest.raises(ValueError, match="AES key not provided"):
            svc.encrypt_aes(b"plaintext")

    def test_decrypt_aes_no_key_raises(self):
        """Test that decrypt_aes raises ValueError if no key is provided."""
        svc = EncryptionService()  # No default key
        
        with pytest.raises(ValueError, match="AES key not provided"):
            svc.decrypt_aes("fake_token")
