"""Results writer — ensures JetStream is ready for game_over events."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import nats
from nats.js.api import RetentionPolicy, StreamConfig

from server.infra.settings import NATS_URL, SERVICE_NAME
from services._runtime import run_until_stopped

GAME_RESULTS_STREAM = 'GAME_RESULTS'
GAME_OVER_SUBJECT = 'games.over'


async def _ensure_stream() -> None:
    nc = await nats.connect(NATS_URL)
    try:
        js = nc.jetstream()
        try:
            await js.stream_info(GAME_RESULTS_STREAM)
        except Exception:
            await js.add_stream(
                StreamConfig(
                    name=GAME_RESULTS_STREAM,
                    subjects=[GAME_OVER_SUBJECT],
                    retention=RetentionPolicy.WORK_QUEUE,
                )
            )
            print(
                '[{}] created JetStream stream {}'.format(
                    SERVICE_NAME,
                    GAME_RESULTS_STREAM,
                ),
                flush=True,
            )
        else:
            print(
                '[{}] JetStream stream {} ready'.format(
                    SERVICE_NAME,
                    GAME_RESULTS_STREAM,
                ),
                flush=True,
            )
    finally:
        await nc.close()


async def _on_start() -> None:
    await _ensure_stream()
    print(
        '[{}] connected to NATS at {}'.format(SERVICE_NAME, NATS_URL),
        flush=True,
    )


async def _on_heartbeat() -> None:
    await _ensure_stream()
    print('[{}] jetstream ok'.format(SERVICE_NAME), flush=True)


async def main() -> None:
    await run_until_stopped(_on_start, on_heartbeat=_on_heartbeat)


if __name__ == '__main__':
    asyncio.run(main())
