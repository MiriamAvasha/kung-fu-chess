"""Choose in-memory or Redis matchmaking from environment."""

from __future__ import annotations

import os
from typing import Union

from server.infra.settings import REDIS_URL
from server.matchmaking.matchmaker import (
    ELO_RANGE,
    SEARCH_TIMEOUT_SECONDS,
    Matchmaker,
)
from server.matchmaking.redis_matchmaker import RedisMatchmaker

MatchmakerLike = Union[Matchmaker, RedisMatchmaker]


def matchmaking_backend() -> str:
    explicit = os.environ.get('KUNGFU_MATCHMAKING', '').strip().lower()
    if explicit in ('memory', 'redis'):
        return explicit
    # Auto-enable Redis only when Compose/host sets REDIS_URL explicitly.
    if os.environ.get('REDIS_URL', '').strip():
        return 'redis'
    return 'memory'


def open_matchmaker(
    elo_range: int = ELO_RANGE,
    timeout_seconds: int = SEARCH_TIMEOUT_SECONDS,
) -> MatchmakerLike:
    if matchmaking_backend() == 'redis':
        if not REDIS_URL:
            raise RuntimeError('REDIS_URL is required for Redis matchmaking')
        return RedisMatchmaker(
            REDIS_URL,
            elo_range=elo_range,
            timeout_seconds=timeout_seconds,
        )
    return Matchmaker(elo_range=elo_range, timeout_seconds=timeout_seconds)
