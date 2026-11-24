from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.security import hash_token
from app.config import get_settings
from app.db.session import get_db
from app.models import Session, User

settings = get_settings()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=settings.cookie_name),
) -> User:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token_hash = hash_token(session_token)
    result = await db.execute(
        select(Session)
        .where(Session.token_hash == token_hash)
        .options(selectinload(Session.user).selectinload(User.preferences))
    )
    session = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if (
        session is None
        or session.revoked_at is not None
        or session.expires_at < now
        or not session.user.is_active
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    request.state.session = session
    request.state.csrf_token = session.csrf_token
    return session.user


async def require_csrf(
    request: Request,
    x_csrf_token: str | None = Header(default=None, alias=settings.csrf_header),
    user: User = Depends(get_current_user),
) -> User:
    session: Session | None = getattr(request.state, "session", None)
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return user
    if session is None or not x_csrf_token or x_csrf_token != session.csrf_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")
    return user


async def get_optional_user(
    db: AsyncSession = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=settings.cookie_name),
) -> User | None:
    if not session_token:
        return None
    token_hash = hash_token(session_token)
    result = await db.execute(
        select(Session)
        .where(Session.token_hash == token_hash)
        .options(selectinload(Session.user).selectinload(User.preferences))
    )
    session = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if session is None or session.revoked_at or session.expires_at < now:
        return None
    return session.user
