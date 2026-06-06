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
#
# Encryption is always performed via MultiFernet so rotation works without code
# changes. When only ENCRYPTION_KEY is set we wrap a single Fernet in MultiFernet
# (no behavioral difference vs. plain Fernet). When ENCRYPTION_KEYS is set as a
# comma-separated list of additional past keys, those are appended after the
# primary key — the primary is always used to encrypt; all keys are tried for
# decryption (Fernet's MultiFernet semantics).

_fernet: MultiFernet | None = None


def _build_key_list() -> list[str]:
    """Merge ENCRYPTION_KEY (primary) with ENCRYPTION_KEYS (CSV of past keys).

    The primary key always comes first, so MultiFernet uses it to encrypt new
    ciphertexts. Past keys are tried for decryption only. Empty/whitespace
    entries in ENCRYPTION_KEYS are ignored. Duplicates of the primary key are
    de-duplicated to avoid wasted decrypt attempts.
    """
    keys: list[str] = [settings.ENCRYPTION_KEY]
    extra = [k.strip() for k in settings.ENCRYPTION_KEYS.split(",") if k.strip()]
    for k in extra:
        if k not in keys:
            keys.append(k)
    return keys


def _get_fernet() -> MultiFernet:
    global _fernet
    if _fernet is None:
        _fernet = get_multi_fernet(_build_key_list())
    return _fernet


def reset_fernet_cache() -> None:
    """Clear the cached MultiFernet — used by tests after mutating settings.

    Production code never needs this; the cache is built lazily on first use.
    """
    global _fernet
    _fernet = None


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string with the primary key. Returns a base64 Fernet token."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a Fernet token using any configured key. Returns plaintext string."""
    f = _get_fernet()
    return f.decrypt(token.encode()).decode()


def get_multi_fernet(keys: list[str]) -> MultiFernet:
    """Build a MultiFernet from one or more keys.

    The first key is used for encryption; all keys are tried for decryption.
    Used internally by `_get_fernet()` and exposed for ad-hoc rotation tooling.
    """
    if not keys:
        raise ValueError("get_multi_fernet requires at least one key")
    fernets = [Fernet(k.encode()) for k in keys]
    return MultiFernet(fernets)


# ── JWT ───────────────────────────────────────────────────────────────────────

ALGORITHM = "HS256"

_bearer = HTTPBearer()


def create_access_token(user_id: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_REFRESH_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_refresh_token(token: str) -> int:
    """Validate a refresh token and return user_id. Raises HTTPException on failure."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return int(user_id)
    except JWTError:
        raise credentials_exception


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
