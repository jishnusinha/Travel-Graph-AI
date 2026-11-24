"""Test harness: isolated SQLite file, demo AI mode, no simulated latency, no network.

Environment is configured BEFORE any `app.*` import because settings and the DB engine are
created at import time.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="travelgraph-tests-"))
os.environ.update(
    {
        "APP_ENV": "test",
        "AI_MODE": "demo",
        "KNOWLEDGE_MODE": "catalog",
        "ALLOW_NETWORK_TOOLS": "false",
        "ALLOW_MODEL_DOWNLOAD": "false",
        "OPENAI_API_KEY": "",
        "OPENAI_MODEL": "",
        "DATABASE_URL": f"sqlite+aiosqlite:///{(_TMP / 'test.sqlite').as_posix()}",
        "CHECKPOINT_DB_PATH": str(_TMP / "checkpoints.sqlite"),
        "SEED_DEMO_DATA": "false",
        "DEMO_LATENCY_SCALE": "0",
        "DEMO_RESET_INBOX_PATH": str(_TMP / "dev_reset_inbox.jsonl"),
        "SESSION_SECRET": "pytest-session-secret-not-for-production-0123456789",
    }
)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.auth.throttle import login_throttle, reset_throttle  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db.migrate import create_all  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed.demo_seed import DEMO_EMAIL, DEMO_PASSWORD, REVIEWER_EMAIL, seed_demo  # noqa: E402

BASE_URL = "http://testserver"
INBOX_PATH = Path(os.environ["DEMO_RESET_INBOX_PATH"])


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _database():
    assert get_settings().ai_mode == "demo"
    await create_all()
    async with SessionLocal() as db:
        await seed_demo(db)
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
def _reset_throttles():
    login_throttle.reset()
    reset_throttle.reset()
    yield


def new_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL)


async def login(client: httpx.AsyncClient, email: str, password: str = DEMO_PASSWORD) -> str:
    """Sign in and return the CSRF token (cookie is stored in the client's jar)."""
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    token = res.json()["csrf_token"]
    assert token
    return token


@pytest_asyncio.fixture
async def anon():
    async with new_client() as c:
        yield c


@pytest_asyncio.fixture
async def demo():
    """Logged-in demo user: (client, headers-with-csrf)."""
    async with new_client() as c:
        csrf = await login(c, DEMO_EMAIL)
        c.headers["X-CSRF-Token"] = csrf
        yield c


@pytest_asyncio.fixture
async def reviewer():
    async with new_client() as c:
        csrf = await login(c, REVIEWER_EMAIL)
        c.headers["X-CSRF-Token"] = csrf
        yield c


@pytest.fixture
def inbox_path() -> Path:
    return INBOX_PATH
