"""Tests for core/security.py — encryption, JWT, and auth dependency."""

import os
import time

from cryptography.fernet import Fernet

# Generate a proper Fernet key for tests
_TEST_FERNET_KEY = Fernet.generate_key().decode()
os.environ["ENCRYPTION_KEY"] = _TEST_FERNET_KEY
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

# Patch settings AND reset the cached fernet instance so tests use the proper key
from app.core.config import settings

settings.ENCRYPTION_KEY = _TEST_FERNET_KEY

import app.core.security as _sec_module

_sec_module._fernet = None

from app.core.security import (
    ALGORITHM,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    decrypt,
    encrypt,
    get_current_user,
    get_multi_fernet,
)

# ── Encryption ────────────────────────────────────────────────────────────────

class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        plaintext = "my-super-secret-api-key-12345"
        ciphertext = encrypt(plaintext)
        assert ciphertext != plaintext
        assert decrypt(ciphertext) == plaintext

    def test_decrypt_rejects_tampered_ciphertext(self):
        ciphertext = encrypt("secret")
        tampered = ciphertext[:-5] + "XXXXX"
        with pytest.raises(Exception):
            decrypt(tampered)

    def test_encrypt_produces_different_ciphertexts(self):
        """Fernet uses a random IV, so each encryption should produce a different result."""
        ct1 = encrypt("same-plaintext")
        ct2 = encrypt("same-plaintext")
        assert ct1 != ct2
        assert decrypt(ct1) == decrypt(ct2) == "same-plaintext"

    def test_multi_fernet_rotation(self):
        from cryptography.fernet import Fernet

        old_key = Fernet.generate_key().decode()
        new_key = Fernet.generate_key().decode()

        old_fernet = Fernet(old_key.encode())
        old_ciphertext = old_fernet.encrypt(b"rotated-secret").decode()

        multi = get_multi_fernet([new_key, old_key])
        assert multi.decrypt(old_ciphertext.encode()) == b"rotated-secret"

        new_ciphertext = multi.encrypt(b"new-secret").decode()
        assert multi.decrypt(new_ciphertext.encode()) == b"new-secret"


# ── JWT ───────────────────────────────────────────────────────────────────────

class TestJWT:
    def test_access_token_has_correct_claims(self):
        token = create_access_token(user_id=42)
        payload = jwt.decode(token, "test-jwt-secret-for-unit-tests-only", algorithms=[ALGORITHM])
        assert payload["sub"] == "42"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_refresh_token_has_correct_claims(self):
        token = create_refresh_token(user_id=7)
        payload = jwt.decode(token, "test-jwt-secret-for-unit-tests-only", algorithms=[ALGORITHM])
        assert payload["sub"] == "7"
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_decode_refresh_token_returns_user_id(self):
        token = create_refresh_token(user_id=99)
        assert decode_refresh_token(token) == 99

    def test_decode_refresh_token_rejects_access_token(self):
        access_token = create_access_token(user_id=1)
        with pytest.raises(HTTPException) as exc:
            decode_refresh_token(access_token)
        assert exc.value.status_code == 401

    def test_decode_refresh_token_rejects_wrong_secret(self):
        payload = {"sub": "1", "exp": time.time() + 3600, "type": "refresh"}
        token = jwt.encode(payload, "wrong-secret", algorithm=ALGORITHM)
        with pytest.raises(HTTPException) as exc:
            decode_refresh_token(token)
        assert exc.value.status_code == 401

    def test_decode_refresh_token_rejects_missing_sub(self):
        payload = {"exp": time.time() + 3600, "type": "refresh"}
        token = jwt.encode(payload, "test-jwt-secret-for-unit-tests-only", algorithm=ALGORITHM)
        with pytest.raises(HTTPException) as exc:
            decode_refresh_token(token)
        assert exc.value.status_code == 401


# ── get_current_user dependency ───────────────────────────────────────────────

class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        token = create_access_token(user_id=5)
        credentials = MagicMock()
        credentials.credentials = token

        mock_user = MagicMock()
        mock_user.id = 5

        db = AsyncMock()
        db.get = AsyncMock(return_value=mock_user)

        user = await get_current_user(credentials=credentials, db=db)
        assert user.id == 5

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        credentials = MagicMock()
        credentials.credentials = "invalid.jwt.token"
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials, db=db)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_but_user_not_found_raises_401(self):
        token = create_access_token(user_id=999)
        credentials = MagicMock()
        credentials.credentials = token

        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials, db=db)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self):
        payload = {"sub": "1", "exp": time.time() - 10, "type": "access"}
        token = jwt.encode(payload, "test-jwt-secret-for-unit-tests-only", algorithm=ALGORITHM)
        credentials = MagicMock()
        credentials.credentials = token
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials, db=db)
        assert exc.value.status_code == 401
