from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import SessionLocal
from app.models import AgentRun, Trip, User
from app.schemas.auth import PreferencesOut, UserOut
from app.services.run_executor import execute_run

logger = logging.getLogger("travelgraph.api")


# --------------------------------------------------------------------------- cookies
def set_session_cookie(response: Response, token: str, *, max_age: int | None) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
    )


# --------------------------------------------------------------------------- serializers
def user_to_out(user: User, csrf_token: str | None = None) -> UserOut:
    prefs = PreferencesOut.model_validate(user.preferences) if user.preferences else None
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        timezone=user.timezone,
        avatar_initials=user.avatar_initials,
        onboarding_completed=user.onboarding_completed,
        is_demo=user.is_demo,
        created_at=user.created_at,
        preferences=prefs,
        csrf_token=csrf_token,
    )


# --------------------------------------------------------------------------- ownership
def not_found(what: str) -> HTTPException:
    # 404 (not 403) so other users' resource ids are indistinguishable from missing ones
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} not found")


async def get_owned_trip(db: AsyncSession, user: User, trip_id: str) -> Trip:
    trip = (
        await db.execute(select(Trip).where(Trip.id == trip_id, Trip.user_id == user.id))
    ).scalar_one_or_none()
    if trip is None:
        raise not_found("Trip")
    return trip


async def get_owned_run(db: AsyncSession, user: User, run_ref: str) -> AgentRun:
    """Resolve a run by internal id or public id (e.g. TG-1047), scoped to the owner."""
    run = (
        await db.execute(
            select(AgentRun).where(
                AgentRun.user_id == user.id,
                or_(AgentRun.id == run_ref, AgentRun.public_id == run_ref),
            )
        )
    ).scalar_one_or_none()
    if run is None:
        raise not_found("Run")
    return run


# --------------------------------------------------------------------------- background runs
_BACKGROUND_TASKS: set[asyncio.Task[Any]] = set()


async def _run_in_background(run_id: str) -> None:
    try:
        async with SessionLocal() as db:
            await execute_run(db, run_id)
    except Exception:  # noqa: BLE001 - execute_run records failures itself; never crash the loop
        logger.exception("Background run %s crashed", run_id)


def spawn_run(run_id: str) -> asyncio.Task[Any]:
    """Fire-and-forget execution of a run on the running event loop (own DB session)."""
    task = asyncio.create_task(_run_in_background(run_id), name=f"run-{run_id}")
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)
    return task


async def wait_for_background_runs(timeout: float = 60.0) -> None:
    """Await in-flight runs (used by tests and graceful shutdown)."""
    pending = list(_BACKGROUND_TASKS)
    if pending:
        await asyncio.wait(pending, timeout=timeout)
