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


_COLUMN_ADDS: dict[str, list[tuple[str, str]]] = {
    "trips": [("destination_id", "VARCHAR(36)")],
    "trip_versions": [
        ("snapshot_id", "VARCHAR(64)"),
        ("plan_schema_version", "VARCHAR(32) DEFAULT 'v1'"),
        ("evidence", "JSON"),
    ],
    "trip_activities": [
        ("attraction_id", "VARCHAR(36)"),
        ("lat", "FLOAT"),
        ("lon", "FLOAT"),
        ("duration_minutes", "INTEGER"),
        ("citation_ids", "JSON"),
        ("verification_status", "VARCHAR(32) DEFAULT 'catalog'"),
        ("cost_low_inr", "INTEGER"),
        ("cost_high_inr", "INTEGER"),
        ("cost_basis", "VARCHAR(32)"),
    ],
    "agent_runs": [
        ("knowledge_mode", "VARCHAR(16) DEFAULT 'catalog'"),
        ("snapshot_id", "VARCHAR(64)"),
        ("generation_provenance", "VARCHAR(64) DEFAULT 'catalog_fixture'"),
        ("parent_run_id", "VARCHAR(36)"),
        ("selected_evidence", "JSON"),
    ],
    "evaluation_runs": [
        ("dataset_version", "VARCHAR(64)"),
        ("strategy", "VARCHAR(64)"),
        ("snapshot_id", "VARCHAR(64)"),
        ("score_provenance", "VARCHAR(64) DEFAULT 'deterministic'"),
        ("sample_count", "INTEGER"),
    ],
}


def upgrade_schema_sync(bind) -> None:  # noqa: ANN001
    """Additive upgrade for databases created before the Terra tables existed."""
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=bind, checkfirst=True)
    existing = {
        row[0]
        for row in bind.exec_driver_sql("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    for table, columns in _COLUMN_ADDS.items():
        if table not in existing:
            continue
        have = {row[1] for row in bind.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}
        for name, ddl in columns:
            if name not in have:
                bind.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
    bind.exec_driver_sql(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunks_fts USING fts5(
            chunk_id UNINDEXED,
            snapshot_id UNINDEXED,
            title,
            section,
            text,
            tokenize='unicode61'
        )
        """
    )


async def create_all() -> None:
    import app.models  # noqa: F401  (register all tables on Base.metadata)

    async with engine.begin() as conn:
        await conn.run_sync(upgrade_schema_sync)


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
