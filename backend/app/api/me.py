from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.common import clear_session_cookie, user_to_out
from app.auth.deps import get_current_user, require_csrf
from app.auth.security import hash_password, initials_from_name, verify_password
from app.db.base import utcnow
from app.db.session import get_db
from app.models import AgentRun, Session, Trip, TripDay, User, UserPreferences
from app.schemas.auth import (
    ChangePasswordIn,
    PreferencesIn,
    PreferencesOut,
    ProfileUpdateIn,
    UserOut,
)
from app.schemas.common import MessageOut
from app.schemas.runs import RunListItem
from app.schemas.trips import TripOut
from app.services.trip_service import serialize_trip

router = APIRouter(prefix="/me", tags=["me"], dependencies=[Depends(require_csrf)])


class OnboardingIn(BaseModel):
    skipped: bool = False
    preferences: Optional[PreferencesIn] = None


class DeleteAccountIn(BaseModel):
    password: str


async def _prefs_for(db: AsyncSession, user: User) -> UserPreferences:
    prefs = (
        await db.execute(select(UserPreferences).where(UserPreferences.user_id == user.id))
    ).scalar_one_or_none()
    if prefs is None:
        prefs = UserPreferences(user_id=user.id, interests=[], extra={})
        db.add(prefs)
        await db.flush()
    return prefs


def _apply_prefs(prefs: UserPreferences, data: dict) -> None:
    for key, value in data.items():
        if hasattr(prefs, key) and key not in {"id", "user_id"}:
            setattr(prefs, key, value)


def _validate_budget(prefs: UserPreferences) -> None:
    if prefs.budget_min > prefs.budget_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="budget_min cannot be greater than budget_max",
        )


@router.get("/preferences", response_model=PreferencesOut)
async def get_preferences(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> PreferencesOut:
    prefs = await _prefs_for(db, user)
    await db.commit()
    return PreferencesOut.model_validate(prefs)


@router.patch("/preferences", response_model=PreferencesOut)
async def update_preferences(
    payload: PreferencesIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PreferencesOut:
    prefs = await _prefs_for(db, user)
    _apply_prefs(prefs, payload.model_dump(exclude_unset=True))
    _validate_budget(prefs)
    await db.commit()
    return PreferencesOut.model_validate(prefs)


@router.post("/onboarding/complete", response_model=UserOut)
async def complete_onboarding(
    payload: OnboardingIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    prefs = await _prefs_for(db, user)
    if payload.preferences is not None and not payload.skipped:
        _apply_prefs(prefs, payload.preferences.model_dump(exclude_unset=True))
        _validate_budget(prefs)
    user.onboarding_completed = True
    await db.commit()
    user.preferences = prefs
    return user_to_out(user, csrf_token=getattr(request.state, "csrf_token", None))


@router.patch("/profile", response_model=UserOut)
async def update_profile(
    payload: ProfileUpdateIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    data = payload.model_dump(exclude_unset=True)
    if "full_name" in data:
        name = (data["full_name"] or "").strip()
        if len(name) < 2:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Name must be at least 2 characters"
            )
        user.full_name = name
        user.avatar_initials = initials_from_name(name)
    if "phone" in data:
        user.phone = (data["phone"] or "").strip() or None
    if "timezone" in data and data["timezone"]:
        user.timezone = data["timezone"]
    await db.commit()
    return user_to_out(user, csrf_token=getattr(request.state, "csrf_token", None))


@router.post("/change-password", response_model=MessageOut)
async def change_password(
    payload: ChangePasswordIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageOut:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    current: Session | None = getattr(request.state, "session", None)
    others = (
        await db.execute(
            select(Session).where(
                Session.user_id == user.id,
                Session.revoked_at.is_(None),
                Session.id != (current.id if current else ""),
            )
        )
    ).scalars().all()
    for s in others:
        s.revoked_at = utcnow()  # sign out every other device
    await db.commit()
    return MessageOut(message="Password changed")


@router.get("/export")
async def export_data(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    """Machine-readable copy of the signed-in user's own data."""
    prefs = await _prefs_for(db, user)
    trips = (
        await db.execute(
            select(Trip)
            .where(Trip.user_id == user.id)
            .options(selectinload(Trip.days).selectinload(TripDay.activities), selectinload(Trip.recommendations))
            .order_by(Trip.created_at)
        )
    ).scalars().all()
    runs = (
        await db.execute(select(AgentRun).where(AgentRun.user_id == user.id).order_by(AgentRun.created_at))
    ).scalars().all()
    return {
        "exported_at": utcnow().isoformat(),
        "user": user_to_out(user).model_dump(mode="json", exclude={"csrf_token", "preferences"}),
        "preferences": PreferencesOut.model_validate(prefs).model_dump(mode="json"),
        "trips": [serialize_trip(t).model_dump(mode="json") for t in trips],
        "runs": [RunListItem.model_validate(r).model_dump(mode="json") for r in runs],
    }


@router.delete("", response_model=MessageOut)
async def delete_account(
    payload: DeleteAccountIn,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageOut:
    if user.is_demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo accounts cannot be deleted. Use the local demo reset script instead.",
        )
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is incorrect")
    await db.delete(user)
    await db.commit()
    clear_session_cookie(response)
    return MessageOut(message="Account deleted")
