"""Deterministic local demo data (demo/local mode only).

    cd backend
    ..\\.venv\\Scripts\\python.exe -m app.seed            # idempotent seed
    ..\\.venv\\Scripts\\python.exe -m app.seed --reset    # wipe seeded users' data, then reseed
"""

from app.seed.demo_seed import (  # noqa: F401
    DEMO_EMAIL,
    DEMO_PASSWORD,
    REVIEWER_EMAIL,
    run_seed,
    seed_demo,
)
