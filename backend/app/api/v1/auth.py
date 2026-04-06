"""
Google OAuth 2.0 flow:
  GET /api/v1/auth/google          → redirect to Google consent
  GET /api/v1/auth/google/callback → exchange code → upsert user → JWT → frontend redirect
"""

import httpx
import pydantic
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, decode_refresh_token
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
SCOPES = "openid email profile"


def _redirect_uri(request: Request) -> str:
    """Build the OAuth callback URI. Use BACKEND_URL env var if set (required in production)."""
    if settings.BACKEND_URL:
        base = settings.BACKEND_URL.rstrip("/")
    else:
        base = str(request.base_url).rstrip("/")
    return f"{base}/api/v1/auth/google/callback"


@router.get("/google")
async def google_login(request: Request):
    """Redirect user to Google OAuth consent screen."""
    redirect_uri = _redirect_uri(request)
    params = (
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={SCOPES.replace(' ', '%20')}"
        f"&access_type=offline"
        f"&prompt=select_account"
    )
    return RedirectResponse(url=GOOGLE_AUTH_URL + params)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Exchange authorization code for tokens, upsert user, issue JWT."""
    if error or not code:
        raise HTTPException(status_code=401, detail=f"OAuth error: {error or 'missing code'}")

    redirect_uri = _redirect_uri(request)

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    if token_resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Failed to exchange OAuth code")

    tokens = token_resp.json()
    access_token = tokens.get("access_token")

    # Fetch user info
    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if userinfo_resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Failed to fetch user info from Google")

    userinfo = userinfo_resp.json()
    google_id = userinfo.get("sub")
    email = userinfo.get("email")
    name = userinfo.get("name")

    if not google_id or not email:
        raise HTTPException(status_code=400, detail="Incomplete user info from Google")

    # Upsert user
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(google_id=google_id, email=email, name=name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Update name/email in case they changed
        user.email = email
        user.name = name
        await db.commit()

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    frontend_redirect = (
        f"{settings.FRONTEND_URL}/auth/callback"
        f"?token={access_token}&refresh_token={refresh_token}"
    )
    return RedirectResponse(url=frontend_redirect)


class RefreshRequest(pydantic.BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh_access_token(body: RefreshRequest):
    """Exchange a valid refresh token for a new access token."""
    user_id = decode_refresh_token(body.refresh_token)
    return {"access_token": create_access_token(user_id), "token_type": "bearer"}
