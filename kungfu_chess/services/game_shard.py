"""Game shard worker — verifies NATS connectivity (engine hosting comes next)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import nats

from server.infra.settings import NATS_URL, SERVICE_NAME
from services._runtime import run_until_stopped


async def _on_start() -> None:
    nc = await nats.connect(NATS_URL)
    await nc.close()
    print(
        '[{}] connected to NATS at {}'.format(SERVICE_NAME, NATS_URL),
        flush=True,
    )


async def _on_heartbeat() -> None:
    nc = await nats.connect(NATS_URL)
    await nc.close()
    print('[{}] nats ok'.format(SERVICE_NAME), flush=True)


async def main() -> None:
    await run_until_stopped(_on_start, on_heartbeat=_on_heartbeat)


if __name__ == '__main__':
    asyncio.run(main())
