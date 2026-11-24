from __future__ import annotations

from fastapi import APIRouter

from app.api import analytics, auth, evaluations, health, me, runs, trips

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(trips.router)
api_router.include_router(runs.router)
api_router.include_router(evaluations.router)
api_router.include_router(analytics.router)
