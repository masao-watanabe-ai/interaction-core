from typing import Optional
from fastapi import Cookie, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models.user import User
from app.services.auth_service import decode_access_token

# auto_error=False にして 403 ではなく 401 を返す
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    access_token: Optional[str] = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    # Bearer token を優先し、なければ Cookie を使用
    token: Optional[str] = None
    if credentials is not None:
        token = credentials.credentials
    elif access_token is not None:
        token = access_token

    if token is None:
        raise HTTPException(
            status_code=401,
            detail="not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="user not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
