"""Shared infrastructure clients and settings (Redis, Postgres, NATS)."""

from server.infra.nats_bus import (
    GAME_OVER_SUBJECT,
    GAME_RESULTS_STREAM,
    GameEventsPublisher,
    try_create_publisher,
)
from server.infra.settings import (
    DATABASE_URL,
    NATS_URL,
    REDIS_URL,
    SERVICE_NAME,
)

__all__ = [
    'DATABASE_URL',
    'GAME_OVER_SUBJECT',
    'GAME_RESULTS_STREAM',
    'GameEventsPublisher',
    'NATS_URL',
    'REDIS_URL',
    'SERVICE_NAME',
    'try_create_publisher',
]
