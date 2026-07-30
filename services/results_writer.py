"""Results writer — consumes game_over from JetStream into PostgreSQL."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
ENGINE_DIR = PROJECT_DIR / 'engine'
for path in (ENGINE_DIR, PROJECT_DIR):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

import nats

from server.infra.game_results import GameResultsRepository
from server.infra.nats_bus import (
    GAME_OVER_SUBJECT,
    GAME_RESULTS_STREAM,
    RESULTS_CONSUMER,
    ensure_game_results_stream,
)
from server.infra.settings import DATABASE_URL, NATS_URL, SERVICE_NAME


async def _handle_message(repo: GameResultsRepository, msg) -> None:
    payload = json.loads(msg.data.decode('utf-8'))
    inserted = repo.save_game_over(payload)
    await msg.ack()
    print(
        '[{}] {} room={} {} vs {} reason={}'.format(
            SERVICE_NAME,
            'saved' if inserted else 'duplicate',
            payload.get('room_id'),
            payload.get('winner'),
            payload.get('loser'),
            payload.get('reason'),
        ),
        flush=True,
    )


async def main() -> None:
    repo = GameResultsRepository(DATABASE_URL)
    nc = await nats.connect(NATS_URL)
    js = nc.jetstream()
    await ensure_game_results_stream(js)
    print(
        '[{}] consuming {} on {}'.format(
            SERVICE_NAME,
            GAME_OVER_SUBJECT,
            NATS_URL,
        ),
        flush=True,
    )

    async def callback(msg):
        await _handle_message(repo, msg)

    await js.subscribe(
        GAME_OVER_SUBJECT,
        cb=callback,
        durable=RESULTS_CONSUMER,
        stream=GAME_RESULTS_STREAM,
        manual_ack=True,
    )

    stop = asyncio.Event()
    await stop.wait()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
