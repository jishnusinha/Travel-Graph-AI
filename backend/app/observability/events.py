from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models import AgentEvent


class EventBus:
    """In-process SSE fan-out keyed by run_id."""

    def __init__(self) -> None:
        self._subs: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def subscribe(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        async with self._lock:
            self._subs[run_id].append(q)
        return q

    async def unsubscribe(self, run_id: str, q: asyncio.Queue) -> None:
        async with self._lock:
            if run_id in self._subs and q in self._subs[run_id]:
                self._subs[run_id].remove(q)

    async def publish(self, run_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            queues = list(self._subs.get(run_id, []))
        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


event_bus = EventBus()


async def persist_event(
    db: AsyncSession,
    *,
    run_id: str,
    seq: int,
    type: str,
    node_id: str | None = None,
    status: str | None = None,
    payload: dict[str, Any] | None = None,
    ts: datetime | None = None,
) -> AgentEvent:
    event = AgentEvent(
        run_id=run_id,
        seq=seq,
        ts=ts or utcnow(),
        type=type,
        node_id=node_id,
        status=status,
        payload=payload or {},
    )
    db.add(event)
    await db.flush()
    await event_bus.publish(
        run_id,
        {
            "id": event.id,
            "run_id": run_id,
            "seq": seq,
            "ts": event.ts.isoformat(),
            "type": type,
            "node_id": node_id,
            "status": status,
            "payload": payload or {},
        },
    )
    return event
