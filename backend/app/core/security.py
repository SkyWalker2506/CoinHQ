"""
Security utilities:
- AES-256 Fernet encryption for exchange API keys
- JWT token creation and validation
- HTTPBearer dependency for protected endpoints
"""

from datetime import UTC, datetime, timedelta

from cryptography.fernet import Fernet, MultiFernet
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

# ── Fernet encryption ──────────────────────────────────────────────────────────

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    return _fernet


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns a base64 Fernet token."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a Fernet token. Returns plaintext string."""
    f = _get_fernet()
    return f.decrypt(token.encode()).decode()


def get_multi_fernet(keys: list[str]) -> MultiFernet:
    """Support multiple encryption keys for rotation.
    First key is used for encryption, all keys tried for decryption.
    """
    fernets = [Fernet(k.encode()) for k in keys]
    return MultiFernet(fernets)


# ── JWT ───────────────────────────────────────────────────────────────────────

ALGORITHM = "HS256"

_bearer = HTTPBearer()


def create_access_token(user_id: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
):
    """FastAPI dependency — validates Bearer JWT and returns the User object."""
    from app.models.user import User  # local import to avoid circular

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=[ALGORITHM],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.get(User, int(user_id))
    if user is None:
        raise credentials_exception
    return user
