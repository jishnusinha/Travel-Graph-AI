from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app import __version__
from app.config import get_settings
from app.db.base import utcnow
from app.db.session import engine
from app.schemas.common import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    """Non-sensitive readiness probe (no secrets, no user data)."""
    settings = get_settings()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:  # noqa: BLE001
        db_status = "unavailable"
    return HealthOut(
        status="ok" if db_status == "ok" else "degraded",
        ai_mode=settings.ai_mode,
        openai_configured=settings.openai_ready,
        database=db_status,
        version=__version__,
        timestamp=utcnow(),
    )
