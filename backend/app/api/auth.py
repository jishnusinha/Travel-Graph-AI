from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.common import clear_session_cookie, set_session_cookie, user_to_out
from app.auth.deps import get_current_user
from app.auth.security import (
    generate_token,
    hash_password,
    hash_token,
    initials_from_name,
    session_expiry,
    verify_password,
)
from app.auth.throttle import login_throttle, reset_throttle
from app.config import get_settings
from app.db.base import utcnow
from app.db.session import get_db
from app.models import PasswordResetToken, Session, User, UserPreferences
from app.schemas.auth import ForgotPasswordIn, LoginIn, ResetPasswordIn, SignupIn, UserOut
from app.schemas.common import MessageOut

logger = logging.getLogger("travelgraph.auth")
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])

RESET_TOKEN_TTL_MINUTES = 30
SHORT_SESSION_HOURS = 12
_DUMMY_HASH: str | None = None


class ResetTokenCheckIn(BaseModel):
    token: str


class ResetTokenCheckOut(BaseModel):
    valid: bool


def _dummy_hash() -> str:
    """Constant-work verification target so unknown emails cost the same as wrong passwords."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("travelgraph-not-a-real-password")
    return _DUMMY_HASH


def _client_key(request: Request, email: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{email}|{host}"


async def _open_session(
    db: AsyncSession, request: Request, response: Response, user: User, *, remember: bool
) -> Session:
    token = generate_token(32)
    hours = settings.session_ttl_hours if remember else SHORT_SESSION_HOURS
    session = Session(
        user_id=user.id,
        token_hash=hash_token(token),
        csrf_token=generate_token(24),
        expires_at=session_expiry(hours),
        user_agent=(request.headers.get("user-agent") or "")[:512],
    )
    db.add(session)
    await db.flush()
    # Persistent cookie only for "remember me"; otherwise a browser-session cookie
    set_session_cookie(response, token, max_age=hours * 3600 if remember else None)
    return session


async def _revoke_all_sessions(db: AsyncSession, user_id: str, *, except_id: str | None = None) -> None:
    stmt = update(Session).where(Session.user_id == user_id, Session.revoked_at.is_(None))
    if except_id:
        stmt = stmt.where(Session.id != except_id)
    await db.execute(stmt.values(revoked_at=utcnow()))


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupIn, request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> UserOut:
    email = payload.email.lower().strip()
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
    full_name = payload.full_name.strip()
    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(payload.password),
        avatar_initials=initials_from_name(full_name),
        is_demo=False,
        onboarding_completed=False,
        preferences=UserPreferences(interests=[], extra={}),
    )
    db.add(user)
    await db.flush()
    session = await _open_session(db, request, response, user, remember=True)
    await db.commit()
    return user_to_out(user, csrf_token=session.csrf_token)


@router.post("/login", response_model=UserOut)
async def login(
    payload: LoginIn, request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> UserOut:
    email = payload.email.lower().strip()
    key = _client_key(request, email)
    login_throttle.check(key)
    user = (
        await db.execute(
            select(User).where(User.email == email).options(selectinload(User.preferences))
        )
    ).scalar_one_or_none()
    ok = verify_password(payload.password, user.password_hash if user else _dummy_hash())
    if user is None or not ok or not user.is_active:
        login_throttle.record_failure(key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    login_throttle.reset(key)
    session = await _open_session(db, request, response, user, remember=payload.remember_me)
    await db.commit()
    return user_to_out(user, csrf_token=session.csrf_token)


@router.post("/logout", response_model=MessageOut)
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=settings.cookie_name),
    x_csrf_token: str | None = Header(default=None, alias=settings.csrf_header),
) -> MessageOut:
    """Idempotent: always clears the cookie; revoking an active session needs the CSRF header."""
    if session_token:
        session = (
            await db.execute(select(Session).where(Session.token_hash == hash_token(session_token)))
        ).scalar_one_or_none()
        if session is not None and session.revoked_at is None:
            if not x_csrf_token or x_csrf_token != session.csrf_token:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")
            session.revoked_at = utcnow()
            await db.commit()
    clear_session_cookie(response)
    return MessageOut(message="Signed out")


@router.get("/me", response_model=UserOut)
async def me(request: Request, user: User = Depends(get_current_user)) -> UserOut:
    return user_to_out(user, csrf_token=getattr(request.state, "csrf_token", None))


# ----------------------------------------------------------------------- password reset
def _write_dev_reset_inbox(email: str, link: str, expires_at: datetime) -> None:
    """Local-only 'mailbox': terminal + JSONL file. Never reachable over HTTP."""
    banner = (
        "\n" + "=" * 72 + "\n"
        f" TravelGraph AI · PASSWORD RESET (local dev only)\n"
        f" For: {email}\n"
        f" Link: {link}\n"
        f" Expires: {expires_at.isoformat()}  (single use)\n" + "=" * 72
    )
    print(banner, flush=True)
    path = Path(settings.demo_reset_inbox_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": utcnow().isoformat(),
        "email": email,
        "link": link,
        "expires_at": expires_at.isoformat(),
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


@router.post("/forgot-password", response_model=MessageOut)
async def forgot_password(
    payload: ForgotPasswordIn, request: Request, db: AsyncSession = Depends(get_db)
) -> MessageOut:
    email = payload.email.lower().strip()
    reset_throttle.check(f"forgot|{request.client.host if request.client else 'unknown'}")
    reset_throttle.record_failure(f"forgot|{request.client.host if request.client else 'unknown'}")
    generic = MessageOut(
        message="If an account exists for that email, a password reset link has been sent."
    )
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None or not user.is_active:
        return generic  # identical response: do not leak whether the account exists

    await db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=utcnow())
    )
    token = generate_token(32)
    expires_at = utcnow() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
    db.add(PasswordResetToken(user_id=user.id, token_hash=hash_token(token), expires_at=expires_at))
    await db.commit()

    link = f"{settings.frontend_origin.rstrip('/')}/reset-password/{token}"
    if settings.app_env == "production":
        logger.warning("Password reset requested but no mail transport is configured (production).")
    else:
        _write_dev_reset_inbox(user.email, link, expires_at)
    return generic


async def _valid_reset_token(db: AsyncSession, token: str) -> PasswordResetToken | None:
    row = (
        await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(token))
        )
    ).scalar_one_or_none()
    if row is None or row.used_at is not None or row.expires_at < datetime.now(timezone.utc):
        return None
    return row


@router.post("/reset-password/validate", response_model=ResetTokenCheckOut)
async def validate_reset_token(
    payload: ResetTokenCheckIn, db: AsyncSession = Depends(get_db)
) -> ResetTokenCheckOut:
    return ResetTokenCheckOut(valid=await _valid_reset_token(db, payload.token) is not None)


@router.post("/reset-password", response_model=MessageOut)
async def reset_password(payload: ResetPasswordIn, db: AsyncSession = Depends(get_db)) -> MessageOut:
    row = await _valid_reset_token(db, payload.token)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or has expired"
        )
    user = await db.get(User, row.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This reset link is invalid or has expired"
        )
    user.password_hash = hash_password(payload.password)
    row.used_at = utcnow()
    await _revoke_all_sessions(db, user.id)
    await db.commit()
    return MessageOut(message="Password updated. You can now sign in.")
