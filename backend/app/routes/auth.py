import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.services.auth_service import create_access_token
from app.services.google_oauth import (
    build_authorization_url,
    exchange_code_for_token,
    get_google_userinfo,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_STATE_EXPIRE_MINUTES = 10


# ── State JWT (CSRF 対策) ────────────────────────────────────────────

def create_oauth_state() -> str:
    payload = {
        "nonce": secrets.token_hex(16),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_STATE_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def verify_oauth_state(state: str) -> bool:
    try:
        jwt.decode(state, settings.secret_key, algorithms=["HS256"])
        return True
    except JWTError:
        return False


# ── Schemas ──────────────────────────────────────────────────────────

class DevLoginRequest(BaseModel):
    user_id: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


# ── Dev login ────────────────────────────────────────────────────────

@router.post("/dev-login", response_model=TokenResponse)
async def dev_login(
    body: DevLoginRequest,
    session: AsyncSession = Depends(get_session),
):
    if not settings.dev_login_enabled:
        raise HTTPException(status_code=403, detail="dev login is disabled")
    result = await session.execute(select(User).where(User.id == body.user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ── Google OAuth ─────────────────────────────────────────────────────

@router.get("/google")
async def google_login():
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")
    state = create_oauth_state()
    url = build_authorization_url(
        settings.google_client_id, settings.google_redirect_uri, state
    )
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    if not verify_oauth_state(state):
        raise HTTPException(status_code=400, detail="invalid or expired state")

    try:
        token_data = await exchange_code_for_token(
            code,
            settings.google_client_id,
            settings.google_client_secret,
            settings.google_redirect_uri,
        )
        userinfo = await get_google_userinfo(token_data["access_token"])
    except Exception:
        raise HTTPException(status_code=400, detail="failed to authenticate with Google")

    google_id = str(userinfo["sub"])
    email = userinfo["email"]
    display_name = userinfo.get("name") or email.split("@")[0]
    avatar_url = userinfo.get("picture")

    # google_id で検索 → なければ email で検索（既存アカウントの紐付け）
    result = await session.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is None:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user is None:
        user = User(
            google_id=google_id,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
        )
        session.add(user)
    else:
        user.google_id = google_id
        user.display_name = display_name
        if avatar_url:
            user.avatar_url = avatar_url

    await session.commit()
    await session.refresh(user)

    jwt_token = create_access_token(user.id)
    response = RedirectResponse(settings.frontend_url)
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.access_token_expire_minutes * 60,
    )
    return response


@router.post("/logout")
async def logout():
    response = JSONResponse(content={"message": "logged out"})
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return response
