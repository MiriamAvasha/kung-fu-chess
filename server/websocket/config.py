"""Runtime configuration for the WebSocket game server."""

import os
from pathlib import Path

from server.db import DEFAULT_DB_PATH


def _env_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or value.strip() == '':
        return default
    return value.strip()


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value.strip() == '':
        return default
    return int(value)


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or value.strip() == '':
        return default
    return float(value)


# Local default stays localhost; containers set KUNGFU_HOST=0.0.0.0.
HOST = _env_str('KUNGFU_HOST', 'localhost')
PORT = _env_int('KUNGFU_PORT', 8765)
TICK_SECONDS = _env_float('KUNGFU_TICK_SECONDS', 0.05)
AUTO_RESIGN_SECONDS = _env_int('KUNGFU_AUTO_RESIGN_SECONDS', 20)

_db_path_raw = os.environ.get('KUNGFU_DB_PATH')
if _db_path_raw is None or _db_path_raw.strip() == '':
    DB_PATH = DEFAULT_DB_PATH
else:
    DB_PATH = Path(_db_path_raw.strip())
