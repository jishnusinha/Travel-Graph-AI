from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UTCDateTime as DateTime, utcnow


def _uuid() -> str:
    return str(uuid4())


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_initials: Mapped[str] = mapped_column(String(4), default="TG")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    sessions: Mapped[list[Session]] = relationship(back_populates="user", cascade="all, delete-orphan")
    preferences: Mapped[Optional[UserPreferences]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    trips: Mapped[list[Trip]] = relationship(back_populates="user", cascade="all, delete-orphan")
    runs: Mapped[list[AgentRun]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Session(Base, TimestampMixin):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")


class PasswordResetToken(Base, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class UserPreferences(Base, TimestampMixin):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    interests: Mapped[list[Any]] = mapped_column(JSON, default=list)
    home_city: Mapped[str] = mapped_column(String(120), default="Kolkata, India")
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    budget_min: Mapped[int] = mapped_column(Integer, default=20000)
    budget_max: Mapped[int] = mapped_column(Integer, default=50000)
    accommodation_style: Mapped[str] = mapped_column(String(64), default="mid-range")
    transport_preference: Mapped[str] = mapped_column(String(64), default="flights")
    ai_mode_preference: Mapped[str] = mapped_column(String(32), default="demo")
    theme: Mapped[str] = mapped_column(String(32), default="system")
    reduced_motion: Mapped[bool] = mapped_column(Boolean, default=False)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    user: Mapped[User] = relationship(back_populates="preferences")


class Trip(Base, TimestampMixin):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False)
    plan_title: Mapped[str] = mapped_column(String(200), default="")
    destination: Mapped[str] = mapped_column(String(120), nullable=False)
    origin: Mapped[str] = mapped_column(String(120), default="Kolkata, India")
    start_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    travelers: Mapped[int] = mapped_column(Integer, default=2)
    budget_inr: Mapped[int] = mapped_column(Integer, default=35000)
    estimated_cost_inr: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    prompt: Mapped[str] = mapped_column(Text, default="")
    interests: Mapped[list[Any]] = mapped_column(JSON, default=list)
    cover_image: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    budget_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    transport: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    accommodation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    public_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    user: Mapped[User] = relationship(back_populates="trips")
    days: Mapped[list[TripDay]] = relationship(back_populates="trip", cascade="all, delete-orphan")
    versions: Mapped[list[TripVersion]] = relationship(back_populates="trip", cascade="all, delete-orphan")
    recommendations: Mapped[list[TripRecommendation]] = relationship(
        back_populates="trip", cascade="all, delete-orphan"
    )
    runs: Mapped[list[AgentRun]] = relationship(back_populates="trip")


class TripVersion(Base, TimestampMixin):
    __tablename__ = "trip_versions"
    __table_args__ = (UniqueConstraint("trip_id", "version", name="uq_trip_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    change_summary: Mapped[str] = mapped_column(String(255), default="")

    trip: Mapped[Trip] = relationship(back_populates="versions")


class TripDay(Base, TimestampMixin):
    __tablename__ = "trip_days"
    __table_args__ = (UniqueConstraint("trip_id", "day_number", name="uq_trip_day"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    area: Mapped[str] = mapped_column(String(120), default="")
    image: Mapped[str] = mapped_column(String(255), default="")
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    trip: Mapped[Trip] = relationship(back_populates="days")
    activities: Mapped[list[TripActivity]] = relationship(
        back_populates="day", cascade="all, delete-orphan"
    )


class TripActivity(Base, TimestampMixin):
    __tablename__ = "trip_activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    day_id: Mapped[str] = mapped_column(ForeignKey("trip_days.id", ondelete="CASCADE"), index=True)
    time_label: Mapped[str] = mapped_column(String(32), default="")
    category: Mapped[str] = mapped_column(String(64), default="activity")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    image: Mapped[str] = mapped_column(String(255), default="")
    estimated_cost_inr: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    day: Mapped[TripDay] = relationship(back_populates="activities")


class TripRecommendation(Base, TimestampMixin):
    __tablename__ = "trip_recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(64), default="tip")
    title: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")

    trip: Mapped[Trip] = relationship(back_populates="recommendations")


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    trip_id: Mapped[Optional[str]] = mapped_column(ForeignKey("trips.id", ondelete="SET NULL"), nullable=True)
    thread_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    prompt: Mapped[str] = mapped_column(Text, default="")
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    final_plan: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ai_mode: Mapped[str] = mapped_column(String(16), default="demo")
    model_name: Mapped[str] = mapped_column(String(64), default="demo-local")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    wall_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    model_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    tool_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    cost_provenance: Mapped[str] = mapped_column(String(64), default="demo")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    revision_number: Mapped[int] = mapped_column(Integer, default=1)

    user: Mapped[User] = relationship(back_populates="runs")
    trip: Mapped[Optional[Trip]] = relationship(back_populates="runs")
    events: Mapped[list[AgentEvent]] = relationship(back_populates="run", cascade="all, delete-orphan")
    tool_invocations: Mapped[list[ToolInvocation]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    model_invocations: Mapped[list[ModelInvocation]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    cost_items: Mapped[list[CostLineItem]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list[EvaluationRun]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class AgentEvent(Base, TimestampMixin):
    __tablename__ = "agent_events"
    __table_args__ = (UniqueConstraint("run_id", "seq", name="uq_run_event_seq"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    type: Mapped[str] = mapped_column(String(64), index=True)
    node_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    run: Mapped[AgentRun] = relationship(back_populates="events")


class ToolInvocation(Base, TimestampMixin):
    __tablename__ = "tool_invocations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    node_id: Mapped[str] = mapped_column(String(64), default="")
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="succeeded")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    fee_usd: Mapped[float] = mapped_column(Float, default=0.0)
    provenance: Mapped[str] = mapped_column(String(64), default="local-catalog")
    input_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    run: Mapped[AgentRun] = relationship(back_populates="tool_invocations")


class ModelInvocation(Base, TimestampMixin):
    __tablename__ = "model_invocations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    node_id: Mapped[str] = mapped_column(String(64), default="")
    provider: Mapped[str] = mapped_column(String(64), default="demo")
    model: Mapped[str] = mapped_column(String(64), default="demo-local")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    pricing_snapshot_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    cost_status: Mapped[str] = mapped_column(String(32), default="demo")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    run: Mapped[AgentRun] = relationship(back_populates="model_invocations")


class EvaluationRun(Base, TimestampMixin):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32), default="deterministic")
    label: Mapped[str] = mapped_column(String(120), default="")
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    rubric_version: Mapped[str] = mapped_column(String(64), default="travelplan-v1")
    is_demo_fixture: Mapped[bool] = mapped_column(Boolean, default=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    judge_model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    judge_prompt_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    run: Mapped[AgentRun] = relationship(back_populates="evaluations")
    metrics: Mapped[list[EvaluationMetric]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )
    evidence: Mapped[list[EvaluationEvidence]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )


class EvaluationMetric(Base, TimestampMixin):
    __tablename__ = "evaluation_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    evaluation_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(32), default="")
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    provenance: Mapped[str] = mapped_column(String(64), default="deterministic")
    status: Mapped[str] = mapped_column(String(32), default="ok")
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    evaluation: Mapped[EvaluationRun] = relationship(back_populates="metrics")


class EvaluationEvidence(Base, TimestampMixin):
    __tablename__ = "evaluation_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    evaluation_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"), index=True
    )
    metric_name: Mapped[str] = mapped_column(String(64), default="")
    snippet: Mapped[str] = mapped_column(Text, default="")
    source_ref: Mapped[str] = mapped_column(String(120), default="")

    evaluation: Mapped[EvaluationRun] = relationship(back_populates="evidence")


class BenchmarkCase(Base, TimestampMixin):
    __tablename__ = "benchmark_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    expected: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    tags: Mapped[list[Any]] = mapped_column(JSON, default=list)


class ModelPricingSnapshot(Base, TimestampMixin):
    __tablename__ = "model_pricing_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(64), default="openai")
    input_per_1m_usd: Mapped[float] = mapped_column(Float, default=0.0)
    output_per_1m_usd: Mapped[float] = mapped_column(Float, default=0.0)
    cached_per_1m_usd: Mapped[float] = mapped_column(Float, default=0.0)
    source_date: Mapped[str] = mapped_column(String(32), default="")
    notes: Mapped[str] = mapped_column(Text, default="Demo pricing catalog — illustrative only")


class CostLineItem(Base, TimestampMixin):
    __tablename__ = "cost_line_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(32), default="model")  # model | tool
    agent_role: Mapped[str] = mapped_column(String(64), default="")
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    amount_usd: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    provenance: Mapped[str] = mapped_column(String(64), default="demo")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[AgentRun] = relationship(back_populates="cost_items")
