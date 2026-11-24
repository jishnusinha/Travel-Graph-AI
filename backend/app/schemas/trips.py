from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import Field

from app.schemas.common import APIModel


class TripCreateIn(APIModel):
    prompt: str = Field(min_length=8, max_length=2000)
    title: Optional[str] = None
    destination: Optional[str] = None
    origin: str = "Kolkata, India"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    travelers: int = Field(default=2, ge=1, le=20)
    budget_inr: int = Field(default=35000, ge=1000)
    interests: list[str] = Field(default_factory=list)
    mode: str = "simple"
    launch_run: bool = True
    destination_id: Optional[str] = None


class TripUpdateIn(APIModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    is_favorite: Optional[bool] = None
    status: Optional[str] = None
    prompt: Optional[str] = None
    destination: Optional[str] = None
    origin: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    travelers: Optional[int] = None
    budget_inr: Optional[int] = None
    interests: Optional[list[str]] = None


class TripActivityOut(APIModel):
    id: str
    time_label: str
    category: str
    title: str
    description: str
    image: str
    estimated_cost_inr: int
    sort_order: int
    attraction_id: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    duration_minutes: Optional[int] = None
    citation_ids: list[Any] = Field(default_factory=list)
    verification_status: str = "catalog"
    cost_low_inr: Optional[int] = None
    cost_high_inr: Optional[int] = None
    cost_basis: Optional[str] = None


class TripDayOut(APIModel):
    id: str
    day_number: int
    title: str
    summary: str
    area: str
    image: str
    meta: dict[str, Any] = Field(default_factory=dict)
    activities: list[TripActivityOut] = Field(default_factory=list)


class TripRecommendationOut(APIModel):
    id: str
    kind: str
    title: str
    body: str


class TripVersionOut(APIModel):
    id: str
    version: int
    change_summary: str
    created_at: datetime


class TripOut(APIModel):
    id: str
    title: str
    slug: str
    plan_title: str = ""
    destination: str
    origin: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    travelers: int
    budget_inr: int
    estimated_cost_inr: int
    status: str
    is_favorite: bool
    prompt: str
    interests: list[Any] = Field(default_factory=list)
    cover_image: str
    notes: str
    budget_breakdown: dict[str, Any] = Field(default_factory=dict)
    transport: dict[str, Any] = Field(default_factory=dict)
    accommodation: dict[str, Any] = Field(default_factory=dict)
    current_version: int
    public_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    days: list[TripDayOut] = Field(default_factory=list)
    recommendations: list[TripRecommendationOut] = Field(default_factory=list)


class TripListItem(APIModel):
    id: str
    title: str
    plan_title: str = ""
    destination: str
    travelers: int
    budget_inr: int
    estimated_cost_inr: int
    status: str
    is_favorite: bool
    cover_image: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: datetime
    day_count: int = 0


class ReplanIn(APIModel):
    prompt: Optional[str] = None
    preferences: dict[str, Any] = Field(default_factory=dict)


class ReplanDayIn(APIModel):
    day_number: int = Field(ge=1, le=30)
    expected_version: int = Field(ge=1)
    prompt: Optional[str] = None


class ActivityReorderIn(APIModel):
    activity_id: str
    expected_version: int = Field(ge=1)
    direction: Literal["up", "down"]


class FavoriteIn(APIModel):
    """Explicit favorite value; omit the body to toggle."""

    is_favorite: Optional[bool] = None


class TripCreateOut(APIModel):
    trip: TripOut
    run_id: Optional[str] = None
    run_public_id: Optional[str] = None


class RunLaunchOut(APIModel):
    trip_id: str
    run_id: str
    run_public_id: str
    revision_number: int


class TripVersionDetailOut(TripVersionOut):
    snapshot: dict[str, Any] = Field(default_factory=dict)
