"""Schema bootstrap.

`create_all` is the source of truth for local-first development (SQLite). Alembic is wired up
(see backend/alembic.ini) with a baseline revision that calls the same metadata, so
`alembic upgrade head` and `python -m app.db.migrate` produce the same schema.

    cd backend
    ..\\.venv\\Scripts\\python.exe -m app.db.migrate           # create tables (idempotent)
    ..\\.venv\\Scripts\\alembic.exe upgrade head                # same, tracked by Alembic
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.base import Base, utcnow
from app.db.session import SessionLocal, engine


async def create_all() -> None:
    import app.models  # noqa: F401  (register all tables on Base.metadata)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def fail_interrupted_runs() -> int:
    """Runs left pending/running by a previous process can never finish; mark them failed."""
    from app.models import AgentEvent, AgentRun, Trip

    async with SessionLocal() as db:
        stale = (
            await db.execute(select(AgentRun).where(AgentRun.status.in_(["pending", "running"])))
        ).scalars().all()
        for run in stale:
            last = (
                await db.execute(
                    select(AgentEvent.seq).where(AgentEvent.run_id == run.id).order_by(AgentEvent.seq.desc()).limit(1)
                )
            ).scalar_one_or_none()
            run.status = "failed"
            run.error_message = "Interrupted: the server restarted while this run was in progress."
            run.completed_at = utcnow()
            if run.trip_id:
                trip = await db.get(Trip, run.trip_id)
                if trip is not None and trip.status == "in_progress" and not trip.estimated_cost_inr:
                    trip.status = "draft"
            db.add(
                AgentEvent(
                    run_id=run.id,
                    seq=(last or 0) + 1,
                    ts=utcnow(),
                    type="run.failed",
                    status="failed",
                    payload={"error": run.error_message},
                )
            )
        await db.commit()
        return len(stale)


def main() -> None:
    asyncio.run(create_all())
    print("TravelGraph schema is up to date.")


if __name__ == "__main__":
    main()
