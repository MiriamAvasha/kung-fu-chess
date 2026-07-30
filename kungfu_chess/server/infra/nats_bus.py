"""NATS JetStream helpers for game lifecycle events."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import nats
from nats.js.api import RetentionPolicy, StreamConfig

GAME_RESULTS_STREAM = 'GAME_RESULTS'
GAME_OVER_SUBJECT = 'games.over'
RESULTS_CONSUMER = 'results-writer'


async def ensure_game_results_stream(js) -> None:
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


class GameEventsPublisher:
    """Publishes authoritative game_over events to JetStream."""

    def __init__(self, nats_url: str):
        self._nats_url = nats_url
        self._nc = None
        self._js = None

    async def connect(self) -> None:
        if self._nc is not None:
            return
        self._nc = await nats.connect(self._nats_url)
        self._js = self._nc.jetstream()
        await ensure_game_results_stream(self._js)

    async def close(self) -> None:
        if self._nc is not None:
            await self._nc.close()
            self._nc = None
            self._js = None

    async def publish_game_over(self, payload: Dict[str, Any]) -> None:
        await self.connect()
        assert self._js is not None
        await self._js.publish(
            GAME_OVER_SUBJECT,
            json.dumps(payload).encode('utf-8'),
        )


def try_create_publisher() -> Optional[GameEventsPublisher]:
    import os

    from server.infra.settings import NATS_URL

    if not os.environ.get('NATS_URL', '').strip():
        return None
    return GameEventsPublisher(NATS_URL)
