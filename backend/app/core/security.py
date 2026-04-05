"""
AES-256 encryption for exchange API keys using Fernet (symmetric encryption).
Master key is loaded from the ENCRYPTION_KEY environment variable.
Plaintext secrets are NEVER logged or persisted.
"""

from cryptography.fernet import Fernet
from app.core.config import settings


def _get_fernet() -> Fernet:
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns a base64 Fernet token."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a Fernet token. Returns plaintext string."""
    f = _get_fernet()
    return f.decrypt(token.encode()).decode()
