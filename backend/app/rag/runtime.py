"""Run blocking retrieval and model inference off the API event loop."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Callable, TypeVar

_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="terra-infer")
T = TypeVar("T")


async def offload(func: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
    """Run a synchronous function on the bounded inference pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_POOL, partial(func, *args, **kwargs))
