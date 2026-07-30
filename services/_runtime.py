"""Helpers for long-running sidecar / worker processes."""

from __future__ import annotations

import asyncio
import signal
from typing import Awaitable, Callable, Optional


async def run_until_stopped(
    on_start: Callable[[], Awaitable[None]],
    *,
    heartbeat_seconds: float = 30.0,
    on_heartbeat: Optional[Callable[[], Awaitable[None]]] = None,
) -> None:
    """Run a service until SIGTERM/SIGINT, with optional heartbeats."""
    stop = asyncio.Event()

    def _request_stop() -> None:
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except (NotImplementedError, RuntimeError):
            # Windows / limited environments: rely on KeyboardInterrupt.
            pass

    await on_start()
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=heartbeat_seconds)
        except asyncio.TimeoutError:
            if on_heartbeat is not None:
                await on_heartbeat()
