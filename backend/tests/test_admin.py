"""Tests for api/v1/admin.py — admin statistics endpoint."""

import os

os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.admin import _require_admin


class TestRequireAdmin:
    def test_allows_admin_user(self):
        user = MagicMock()
        user.tier = "admin"
        _require_admin(user)  # should not raise

    def test_rejects_free_user(self):
        user = MagicMock()
        user.tier = "free"
        with pytest.raises(HTTPException) as exc:
            _require_admin(user)
        assert exc.value.status_code == 403

    def test_rejects_premium_user(self):
        user = MagicMock()
        user.tier = "premium"
        with pytest.raises(HTTPException) as exc:
            _require_admin(user)
        assert exc.value.status_code == 403
