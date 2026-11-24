from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(ROOT / ".env"), str(ROOT / "backend" / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "test", "production"] = "local"
    ai_mode: Literal["demo", "openai"] = "demo"
    openai_api_key: str = ""
    openai_model: str = ""
    database_url: str = Field(
        default=f"sqlite+aiosqlite:///{(DATA_DIR / 'travelgraph.sqlite').as_posix()}"
    )
    checkpoint_db_path: str = Field(
        default=str(DATA_DIR / "checkpoints.sqlite")
    )
    frontend_origin: str = "http://localhost:5173"
    session_secret: str = "replace-in-local-env-with-a-random-long-value"
    seed_demo_data: bool = True
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    session_ttl_hours: int = 168
    cookie_name: str = "tg_session"
    csrf_header: str = "X-CSRF-Token"
    demo_reset_inbox_path: str = str(DATA_DIR / "dev_reset_inbox.jsonl")
    # Simulated per-node latency for live demo runs (0 = instant, used by tests)
    demo_latency_scale: float = 1.0

    @property
    def is_demo(self) -> bool:
        return self.ai_mode == "demo"

    @property
    def openai_ready(self) -> bool:
        return bool(self.openai_api_key.strip()) and bool(self.openai_model.strip())


@lru_cache
def get_settings() -> Settings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()
