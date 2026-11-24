from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, status


class FailureThrottle:
    """Tiny in-process sliding-window limiter for failed auth attempts (local-first, no Redis)."""

    def __init__(self, limit: int = 8, window_s: int = 300) -> None:
        self.limit = limit
        self.window_s = window_s
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._failures[key]
        while q and now - q[0] > self.window_s:
            q.popleft()
        return q

    def check(self, key: str) -> None:
        now = time.monotonic()
        q = self._prune(key, now)
        if len(q) >= self.limit:
            retry_after = max(1, int(self.window_s - (now - q[0])))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed attempts. Please wait a few minutes and try again.",
                headers={"Retry-After": str(retry_after)},
            )

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        self._prune(key, now).append(now)

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self._failures.clear()
        else:
            self._failures.pop(key, None)


login_throttle = FailureThrottle(limit=8, window_s=300)
reset_throttle = FailureThrottle(limit=10, window_s=300)
