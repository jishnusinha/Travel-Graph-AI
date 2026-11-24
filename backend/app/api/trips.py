from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common import get_owned_trip, not_found, spawn_run
from app.auth.deps import get_current_user, require_csrf
from app.db.session import get_db
from app.models import AgentRun, Trip, TripDay, TripVersion, User
from app.schemas.common import MessageOut, Paginated
from app.schemas.trips import (
    ActivityReorderIn,
    FavoriteIn,
    ReplanDayIn,
    ReplanIn,
    RunLaunchOut,
    TripCreateIn,
    TripCreateOut,
    TripListItem,
    TripOut,
    TripUpdateIn,
    TripVersionDetailOut,
    TripVersionOut,
)
from app.services.run_executor import create_run
from app.services.trip_service import (
    TRIP_STATUSES,
    apply_plan_to_trip,
    day_count_subquery,
    duplicate_trip,
    load_trip_full,
    plan_dict_from_trip,
    run_payload_from_trip,
    serialize_trip,
    slugify,
)

router = APIRouter(prefix="/trips", tags=["trips"], dependencies=[Depends(require_csrf)])

StatusFilter = Literal["all", "completed", "in_progress", "draft", "favorite"]
SortKey = Literal["recent", "oldest", "title", "budget", "start_date", "updated"]


async def _full_out(db: AsyncSession, trip_id: str) -> TripOut:
    trip = await load_trip_full(db, trip_id)
    if trip is None:
        raise not_found("Trip")
    return serialize_trip(trip)


@router.get("", response_model=Paginated[TripListItem])
async def list_trips(
    q: Optional[str] = Query(default=None, max_length=120),
    status_filter: StatusFilter = Query(default="all", alias="status"),
    sort: SortKey = "recent",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Paginated[TripListItem]:
    conditions = [Trip.user_id == user.id]
    if status_filter == "favorite":
        conditions.append(Trip.is_favorite.is_(True))
    elif status_filter != "all":
        conditions.append(Trip.status == status_filter)
    if q and q.strip():
        like = f"%{q.strip().lower()}%"
        conditions.append(
            or_(
                func.lower(Trip.title).like(like),
                func.lower(Trip.destination).like(like),
                func.lower(Trip.plan_title).like(like),
            )
        )
    total = (await db.execute(select(func.count(Trip.id)).where(*conditions))).scalar_one()

    orders = {
        "recent": [Trip.created_at.desc()],
        "oldest": [Trip.created_at.asc()],
        "updated": [Trip.updated_at.desc()],
        "title": [func.lower(Trip.title).asc()],
        "budget": [Trip.budget_inr.desc()],
        "start_date": [Trip.start_date.is_(None), Trip.start_date.asc()],  # undated trips last
    }
    stmt = (
        select(Trip, day_count_subquery().label("day_count"))
        .where(*conditions)
        .order_by(*orders[sort], Trip.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).all()
    items = []
    for trip, n in rows:
        item = TripListItem.model_validate(trip)
        item.day_count = int(n or 0)
        items.append(item)
    return Paginated[TripListItem](items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=TripCreateOut, status_code=status.HTTP_201_CREATED)
async def create_trip(
    payload: TripCreateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TripCreateOut:
    if payload.start_date and payload.end_date and payload.end_date < payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="end_date cannot be before start_date"
        )
    title = (payload.title or "").strip() or "New Trip"
    trip = Trip(
        user_id=user.id,
        title=title[:200],
        slug=slugify(title),
        destination=(payload.destination or "").strip(),
        origin=payload.origin,
        start_date=payload.start_date,
        end_date=payload.end_date,
        travelers=payload.travelers,
        budget_inr=payload.budget_inr,
        status="in_progress" if payload.launch_run else "draft",
        prompt=payload.prompt,
        interests=list(payload.interests),
        cover_image="/assets/destinations/generic.jpg",
        destination_id=payload.destination_id,
    )
    db.add(trip)
    await db.flush()

    run: AgentRun | None = None
    if payload.launch_run:
        request_payload = {
            "prompt": payload.prompt,
            "destination": payload.destination,
            "origin": payload.origin,
            "start_date": payload.start_date.isoformat() if payload.start_date else None,
            "end_date": payload.end_date.isoformat() if payload.end_date else None,
            "travelers": payload.travelers,
            "budget_inr": payload.budget_inr,
            "interests": list(payload.interests),
            "mode": payload.mode,
            "destination_id": payload.destination_id,
        }
        run = await create_run(db, user_id=user.id, payload=request_payload, trip_id=trip.id)
    await db.commit()
    if run is not None:
        spawn_run(run.id)
    return TripCreateOut(
        trip=await _full_out(db, trip.id),
        run_id=run.id if run else None,
        run_public_id=run.public_id if run else None,
    )


@router.get("/{trip_id}", response_model=TripOut)
async def get_trip(
    trip_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> TripOut:
    await get_owned_trip(db, user, trip_id)
    return await _full_out(db, trip_id)


@router.patch("/{trip_id}", response_model=TripOut)
async def update_trip(
    trip_id: str,
    payload: TripUpdateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TripOut:
    trip = await get_owned_trip(db, user, trip_id)
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in TRIP_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"status must be one of {sorted(TRIP_STATUSES)}",
        )
    if "title" in data:
        title = (data["title"] or "").strip()
        if not title:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Title cannot be empty")
        data["title"] = title[:200]
        trip.slug = slugify(title)
    if "travelers" in data and (data["travelers"] is None or not 1 <= data["travelers"] <= 20):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="travelers must be 1-20")
    if "budget_inr" in data and (data["budget_inr"] is None or data["budget_inr"] < 1000):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="budget_inr must be >= 1000")
    for key, value in data.items():
        if value is None and key not in {"start_date", "end_date"}:
            continue  # only dates may be explicitly cleared
        setattr(trip, key, value)
    if trip.start_date and trip.end_date and trip.end_date < trip.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="end_date cannot be before start_date"
        )
    await db.commit()
    return await _full_out(db, trip_id)


@router.delete("/{trip_id}", response_model=MessageOut)
async def delete_trip(
    trip_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> MessageOut:
    trip = await get_owned_trip(db, user, trip_id)
    # Runs and their costs are kept for analytics; they simply detach from the trip.
    await db.delete(trip)
    await db.commit()
    return MessageOut(message="Trip deleted")


@router.post("/{trip_id}/favorite", response_model=TripListItem)
async def set_favorite(
    trip_id: str,
    payload: Optional[FavoriteIn] = Body(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TripListItem:
    trip = await get_owned_trip(db, user, trip_id)
    if payload is not None and payload.is_favorite is not None:
        trip.is_favorite = payload.is_favorite
    else:
        trip.is_favorite = not trip.is_favorite
    await db.commit()
    count = (await db.execute(select(func.count(TripDay.id)).where(TripDay.trip_id == trip.id))).scalar_one()
    item = TripListItem.model_validate(trip)
    item.day_count = int(count or 0)
    return item


@router.post("/{trip_id}/duplicate", response_model=TripOut, status_code=status.HTTP_201_CREATED)
async def duplicate(
    trip_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> TripOut:
    await get_owned_trip(db, user, trip_id)
    source = await load_trip_full(db, trip_id)
    assert source is not None
    clone = await duplicate_trip(db, source)
    await db.commit()
    return await _full_out(db, clone.id)


@router.get("/{trip_id}/versions", response_model=list[TripVersionOut])
async def list_versions(
    trip_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[TripVersionOut]:
    await get_owned_trip(db, user, trip_id)
    rows = (
        await db.execute(
            select(TripVersion).where(TripVersion.trip_id == trip_id).order_by(TripVersion.version.desc())
        )
    ).scalars().all()
    return [TripVersionOut.model_validate(r) for r in rows]


async def _get_version(db: AsyncSession, trip_id: str, version: int) -> TripVersion:
    row = (
        await db.execute(
            select(TripVersion).where(TripVersion.trip_id == trip_id, TripVersion.version == version)
        )
    ).scalar_one_or_none()
    if row is None:
        raise not_found("Version")
    return row


@router.get("/{trip_id}/versions/{version}", response_model=TripVersionDetailOut)
async def get_version(
    trip_id: str,
    version: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TripVersionDetailOut:
    await get_owned_trip(db, user, trip_id)
    return TripVersionDetailOut.model_validate(await _get_version(db, trip_id, version))


@router.post("/{trip_id}/versions/{version}/restore", response_model=TripOut)
async def restore_version(
    trip_id: str,
    version: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TripOut:
    """Recover an earlier plan: re-applies its snapshot as a NEW version (history is kept)."""
    trip = await get_owned_trip(db, user, trip_id)
    row = await _get_version(db, trip_id, version)
    snapshot = dict(row.snapshot or {})
    if not snapshot.get("days"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This version has no restorable itinerary")
    await apply_plan_to_trip(
        db,
        trip,
        snapshot,
        change_summary=f"Restored version {version}",
        status="completed",
    )
    await db.commit()
    return await _full_out(db, trip_id)


@router.post("/{trip_id}/replan", response_model=RunLaunchOut, status_code=status.HTTP_202_ACCEPTED)
async def replan(
    trip_id: str,
    payload: Optional[ReplanIn] = Body(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RunLaunchOut:
    """Start a new agent run for an existing trip; the result is saved as a new trip version."""
    trip = await get_owned_trip(db, user, trip_id)
    payload = payload or ReplanIn()
    prefs = dict(payload.preferences or {})
    allowed = {"destination", "origin", "start_date", "end_date", "travelers", "budget_inr", "interests"}
    overrides = {k: v for k, v in prefs.items() if k in allowed}
    for key in ("start_date", "end_date"):
        if key in overrides and overrides[key] is not None:
            overrides[key] = str(overrides[key])
    base_prompt = payload.prompt.strip() if payload.prompt and payload.prompt.strip() else None
    request_payload = run_payload_from_trip(trip, overrides)
    if base_prompt:
        request_payload["prompt"] = base_prompt
    request_payload["replan"] = True
    revision = (
        await db.execute(select(func.count(AgentRun.id)).where(AgentRun.trip_id == trip.id))
    ).scalar_one() + 1
    run = await create_run(
        db, user_id=user.id, payload=request_payload, trip_id=trip.id, revision_number=int(revision)
    )
    if trip.status != "completed":
        trip.status = "in_progress"
    await db.commit()
    spawn_run(run.id)
    return RunLaunchOut(
        trip_id=trip.id, run_id=run.id, run_public_id=run.public_id, revision_number=run.revision_number
    )


@router.post("/{trip_id}/replan-day", response_model=RunLaunchOut, status_code=status.HTTP_202_ACCEPTED)
async def replan_day(
    trip_id: str,
    payload: ReplanDayIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RunLaunchOut:
    """Regenerate one day. Other days stay as stored. A stale version is rejected."""
    trip = await load_trip_full(db, trip_id)
    if trip is None or trip.user_id != user.id:
        raise not_found("Trip")
    if trip.current_version != payload.expected_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This trip changed. Reload it before replanning a day.")
    if not any(day.day_number == payload.day_number for day in trip.days):
        raise not_found("Day")
    request_payload = run_payload_from_trip(trip)
    if payload.prompt and payload.prompt.strip():
        request_payload["prompt"] = payload.prompt.strip()
    request_payload["replan"] = True
    request_payload["replan_day"] = payload.day_number
    request_payload["expected_version"] = payload.expected_version
    request_payload["prior_days"] = plan_dict_from_trip(trip)["days"]
    revision = (
        await db.execute(select(func.count(AgentRun.id)).where(AgentRun.trip_id == trip.id))
    ).scalar_one() + 1
    run = await create_run(
        db, user_id=user.id, payload=request_payload, trip_id=trip.id, revision_number=int(revision)
    )
    await db.commit()
    spawn_run(run.id)
    return RunLaunchOut(
        trip_id=trip.id, run_id=run.id, run_public_id=run.public_id, revision_number=run.revision_number
    )


@router.post("/{trip_id}/activities/reorder", response_model=TripOut)
async def reorder_activity(
    trip_id: str,
    payload: ActivityReorderIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TripOut:
    """Swap one activity with its neighbor and store a new version."""
    trip = await load_trip_full(db, trip_id)
    if trip is None or trip.user_id != user.id:
        raise not_found("Trip")
    if trip.current_version != payload.expected_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This trip changed. Reload it before reordering.")
    located: tuple[int, int, int] | None = None
    for day in trip.days:
        ordered = sorted(day.activities, key=lambda item: item.sort_order)
        for index, act in enumerate(ordered):
            if act.id == payload.activity_id:
                located = (day.day_number, index, len(ordered))
    if located is None:
        raise not_found("Activity")
    day_number, index, count = located
    swap = index - 1 if payload.direction == "up" else index + 1
    if swap < 0 or swap >= count:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That activity is already at the edge of the day.")
    plan = plan_dict_from_trip(trip)
    activities = next(day["activities"] for day in plan["days"] if day["day_number"] == day_number)
    activities[index], activities[swap] = activities[swap], activities[index]
    await apply_plan_to_trip(db, trip, plan, change_summary=f"Reordered an activity {payload.direction}")
    await db.commit()
    return await _full_out(db, trip_id)
