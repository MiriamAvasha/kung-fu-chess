"""Matchmaker worker — verifies Redis connectivity (queue wiring comes next)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
ENGINE_DIR = PROJECT_DIR / 'engine'
for path in (ENGINE_DIR, PROJECT_DIR):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

import redis

from server.infra.settings import REDIS_URL, SERVICE_NAME
from services._runtime import run_until_stopped


def _ping_redis() -> None:
    client = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=3)
    client.ping()
    client.close()


async def _on_start() -> None:
    await asyncio.to_thread(_ping_redis)
    print(
        '[{}] connected to Redis at {}'.format(SERVICE_NAME, REDIS_URL),
        flush=True,
    )


async def _on_heartbeat() -> None:
    await asyncio.to_thread(_ping_redis)
    print('[{}] redis ok'.format(SERVICE_NAME), flush=True)


async def main() -> None:
    await run_until_stopped(_on_start, on_heartbeat=_on_heartbeat)


if __name__ == '__main__':
    asyncio.run(main())
