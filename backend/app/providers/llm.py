from __future__ import annotations

import asyncio
import hashlib
import json
from abc import ABC, abstractmethod
from contextvars import ContextVar
from typing import Any

from app.config import get_settings


class LLMProvider(ABC):
    @abstractmethod
    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema_hint: str,
        node_id: str,
    ) -> dict[str, Any]:
        raise NotImplementedError


# Simulated seconds of "thinking" per node so live demo runs show real overlap
# between parallel agents. Scaled by DEMO_LATENCY_SCALE (0 disables, e.g. in tests).
DEMO_NODE_LATENCY_S: dict[str, float] = {
    "supervisor": 0.7,
    "destination": 1.3,
    "transport": 1.0,
    "accommodation": 1.15,
    "itinerary": 1.4,
    "aggregator": 0.8,
}


# Lets callers (benchmarks, tests) run demo nodes instantly without touching global settings
demo_latency_override: ContextVar[float | None] = ContextVar("demo_latency_override", default=None)


class DemoLLMProvider(LLMProvider):
    """Deterministic local 'LLM' — no network calls."""

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema_hint: str,
        node_id: str,
    ) -> dict[str, Any]:
        override = demo_latency_override.get()
        scale = get_settings().demo_latency_scale if override is None else override
        delay = DEMO_NODE_LATENCY_S.get(node_id, 0.0) * max(scale, 0.0)
        if delay > 0:
            await asyncio.sleep(delay)
        digest = hashlib.sha256(f"{node_id}:{user}:{schema_hint}".encode()).hexdigest()[:12]
        return {
            "provider": "demo",
            "model": "demo-local",
            "node_id": node_id,
            "digest": digest,
            "narrative": f"Demo reasoning for {node_id}: constraints understood from local catalog.",
            "system_echo_len": len(system),
            "user_echo_len": len(user),
        }


class OpenAILLMProvider(LLMProvider):
    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema_hint: str,
        node_id: str,
    ) -> dict[str, Any]:
        settings = get_settings()
        if not settings.openai_ready:
            raise RuntimeError(
                "AI_MODE=openai requires OPENAI_API_KEY and OPENAI_MODEL in backend .env"
            )
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"{user}\n\nReturn JSON matching: {schema_hint}",
                },
            ],
            text={"format": {"type": "json_object"}},
        )
        text = getattr(response, "output_text", None) or "{}"
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"OpenAI returned non-JSON for {node_id}") from exc
        data["_meta"] = {
            "provider": "openai",
            "model": settings.openai_model,
            "node_id": node_id,
        }
        return data


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.ai_mode == "openai":
        if not settings.openai_ready:
            raise RuntimeError(
                "AI_MODE=openai but OPENAI_API_KEY or OPENAI_MODEL is missing. "
                "Set both in .env or switch AI_MODE=demo."
            )
        return OpenAILLMProvider()
    return DemoLLMProvider()
