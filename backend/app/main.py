from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.common import wait_for_background_runs
from app.api.router import api_router
from app.config import get_settings
from app.db.migrate import create_all, fail_interrupted_runs
from app.db.session import SessionLocal, engine

logger = logging.getLogger("travelgraph")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await create_all()
    interrupted = await fail_interrupted_runs()
    if interrupted:
        logger.warning("Marked %s interrupted run(s) as failed after restart", interrupted)

    # Demo accounts are local/demo only: never seeded in production
    if settings.seed_demo_data and settings.app_env != "production":
        from app.seed.demo_seed import seed_demo

        async with SessionLocal() as db:
            summary = await seed_demo(db)
        logger.info("Demo seed: %s", summary)
    if settings.ai_mode == "openai" and not settings.openai_ready:
        logger.error("AI_MODE=openai but OPENAI_API_KEY / OPENAI_MODEL are not both set; runs will fail clearly.")
    yield
    await wait_for_background_runs(timeout=5.0)
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="TravelGraph AI",
        version=__version__,
        description="Local-first multi-agent travel planning API (LangGraph). AI_MODE=demo needs no keys.",
        lifespan=lifespan,
    )

    origins = {settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"}
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", settings.csrf_header, "Last-Event-ID", "Accept"],
        expose_headers=["Content-Disposition"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": [str(p) for p in e.get("loc", [])], "msg": str(e.get("msg", "")), "type": e.get("type", "")}
            for e in exc.errors()
        ]
        first = errors[0]["msg"] if errors else "Invalid request"
        return JSONResponse(
            status_code=422,
            content={"detail": first, "code": "validation_error", "errors": errors},
        )

    app.include_router(api_router)
    return app


app = create_app()
