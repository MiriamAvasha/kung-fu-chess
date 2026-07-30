"""Environment settings shared by Docker Compose services."""

import os


def _env_str(name: str, default: str = '') -> str:
    value = os.environ.get(name)
    if value is None or value.strip() == '':
        return default
    return value.strip()


REDIS_URL = _env_str('REDIS_URL', 'redis://localhost:6379/0')
DATABASE_URL = _env_str(
    'DATABASE_URL',
    'postgresql://kungfu:kungfu@localhost:5432/kungfu',
)
NATS_URL = _env_str('NATS_URL', 'nats://localhost:4222')
SERVICE_NAME = _env_str('SERVICE_NAME', 'unknown')
