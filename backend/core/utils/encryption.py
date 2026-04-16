from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Optional, Tuple

try:
	from cryptography.hazmat.primitives.ciphers.aead import AESGCM
	_HAS_CRYPTO = True
except Exception:
	AESGCM = None  # type: ignore
	_HAS_CRYPTO = False


class EncryptionService:
	"""Configurable encryption and hashing utilities.

	Use an instance for DI-friendly configuration.
	"""

	def __init__(self, *, pbkdf2_iters: int = 200_000, salt_len: int = 16, aes_key: Optional[bytes] = None):
		self.pbkdf2_iters = pbkdf2_iters
		self.salt_len = salt_len
		self._aes_key = aes_key

	# Password hashing using PBKDF2-HMAC-SHA256 (stdlib)
	def hash_password(self, password: str, *, salt: Optional[bytes] = None) -> str:
		"""Hash a password and return storage-friendly string.

		Format: pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>
		"""
		if salt is None:
			salt = os.urandom(self.salt_len)
		password_bytes = password.encode("utf-8")
		dk = hashlib.pbkdf2_hmac("sha256", password_bytes, salt, self.pbkdf2_iters, dklen=32)
		return "pbkdf2_sha256${}${}${}".format(
			self.pbkdf2_iters,
			base64.urlsafe_b64encode(salt).decode("ascii"),
			base64.urlsafe_b64encode(dk).decode("ascii"),
		)

	def verify_password(self, stored: str, password: str) -> bool:
		# Supported stored password formats:
		# - PBKDF2: pbkdf2_sha256$<iterations>$<salt_b64>$<dk_b64>
		# - Plaintext (development only): plain$<password>
		try:
			if stored is None:
				return False
			# Development shortcut: plain$PASSWORD
			if stored.startswith("plain$"):
				return stored.split("plain$", 1)[1] == password

			parts = stored.split("$")
			if len(parts) != 4 or not parts[0].startswith("pbkdf2_sha256"):
				return False
			_algo, iterations_s, salt_b64, dk_b64 = parts
			iterations = int(iterations_s)
			salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
			expected = base64.urlsafe_b64decode(dk_b64.encode("ascii"))
			dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=len(expected))
			return hmac.compare_digest(dk, expected)
		except Exception:
			return False

	# HMAC helper
	def hmac_sha256(self, key: bytes, data: bytes) -> bytes:
		return hmac.new(key, data, hashlib.sha256).digest()

	# AES-GCM helpers (require cryptography)
	def generate_aes_key(self, length: int = 32) -> bytes:
		return os.urandom(length)

	def encrypt_aes(self, plaintext: bytes, associated_data: Optional[bytes] = None, *, key: Optional[bytes] = None) -> str:
		"""Encrypt plaintext and return a urlsafe-b64 token (nonce|tag|ciphertext).

		Raises ImportError if `cryptography` is not available.
		"""
		if not _HAS_CRYPTO or AESGCM is None:
			raise ImportError("cryptography is required for AES-GCM; install the 'cryptography' package")
		k = key or self._aes_key
		if k is None:
			raise ValueError("AES key not provided; set in service or pass as `key`")
		aesgcm = AESGCM(k)
		nonce = os.urandom(12)
		ct_and_tag = aesgcm.encrypt(nonce, plaintext, associated_data)
		tag = ct_and_tag[-16:]
		ciphertext = ct_and_tag[:-16]
		return base64.urlsafe_b64encode(nonce + tag + ciphertext).decode("ascii")

	def decrypt_aes(self, token_b64: str, associated_data: Optional[bytes] = None, *, key: Optional[bytes] = None) -> bytes:
		if not _HAS_CRYPTO or AESGCM is None:
			raise ImportError("cryptography is required for AES-GCM; install the 'cryptography' package")
		raw = base64.urlsafe_b64decode(token_b64.encode("ascii"))
		nonce = raw[:12]
		tag = raw[12:28]
		ciphertext = raw[28:]
		k = key or self._aes_key
		if k is None:
			raise ValueError("AES key not provided; set in service or pass as `key`")
		aesgcm = AESGCM(k)
		return aesgcm.decrypt(nonce, ciphertext + tag, associated_data)


__all__ = ["EncryptionService"]

