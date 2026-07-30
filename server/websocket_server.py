"""Compatibility facade for the layered WebSocket server package."""

from server.websocket import (
    AUTO_RESIGN_SECONDS,
    DB_PATH,
    HOST,
    PORT,
    TICK_SECONDS,
    GameServer,
    main,
)

__all__ = [
    'AUTO_RESIGN_SECONDS',
    'DB_PATH',
    'GameServer',
    'HOST',
    'PORT',
    'TICK_SECONDS',
    'main',
]
