"""Container health checks used by docker-compose."""

from __future__ import annotations

import asyncio
import os
import sys


def check_redis() -> None:
    import redis

    client = redis.Redis.from_url(
        os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
        socket_connect_timeout=2,
    )
    client.ping()
    client.close()


async def _check_nats_async() -> None:
    import nats

    nc = await nats.connect(os.environ.get('NATS_URL', 'nats://localhost:4222'))
    await nc.close()


def check_nats() -> None:
    asyncio.run(_check_nats_async())


def check_postgres() -> None:
    import psycopg

    with psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=2) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT 1')


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else ''
    if target == 'redis':
        check_redis()
    elif target == 'nats':
        check_nats()
    elif target == 'postgres':
        check_postgres()
    else:
        raise SystemExit('usage: healthcheck.py [redis|nats|postgres]')
