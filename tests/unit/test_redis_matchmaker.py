import os
import time

import pytest

from server.matchmaking.factory import matchmaking_backend, open_matchmaker
from server.matchmaking import Matchmaker, QueueEntry, RedisMatchmaker


def test_matchmaking_backend_defaults_memory(monkeypatch):
    monkeypatch.delenv('KUNGFU_MATCHMAKING', raising=False)
    monkeypatch.delenv('REDIS_URL', raising=False)
    assert matchmaking_backend() == 'memory'
    assert isinstance(open_matchmaker(), Matchmaker)


def test_matchmaking_backend_explicit_redis(monkeypatch):
    monkeypatch.setenv('KUNGFU_MATCHMAKING', 'redis')
    monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379/15')
    import server.matchmaking.factory as factory

    monkeypatch.setattr(factory, 'REDIS_URL', 'redis://localhost:6379/15')
    assert matchmaking_backend() == 'redis'


@pytest.mark.skipif(
    os.environ.get('KUNGFU_TEST_REDIS', '').strip() != '1',
    reason='Set KUNGFU_TEST_REDIS=1 with Redis available',
)
def test_redis_matchmaker_pairs_within_elo():
    mm = RedisMatchmaker(
        os.environ.get('REDIS_URL', 'redis://localhost:6379/15'),
        elo_range=100,
        timeout_seconds=60,
    )
    mm.clear_for_tests()
    first = QueueEntry('Alice', 1200, 'c1')
    second = QueueEntry('Bob', 1280, 'c2')
    assert mm.enqueue(first) is None
    matched = mm.enqueue(second)
    assert matched is not None
    white, black = matched
    assert white.username == 'Alice'
    assert black.username == 'Bob'
    mm.clear_for_tests()


@pytest.mark.skipif(
    os.environ.get('KUNGFU_TEST_REDIS', '').strip() != '1',
    reason='Set KUNGFU_TEST_REDIS=1 with Redis available',
)
def test_redis_matchmaker_expires():
    mm = RedisMatchmaker(
        os.environ.get('REDIS_URL', 'redis://localhost:6379/15'),
        elo_range=100,
        timeout_seconds=60,
    )
    mm.clear_for_tests()
    entry = QueueEntry('Alice', 1200, 'c1', enqueued_at=time.time() - 61)
    mm.enqueue(entry)
    # Re-write enqueued_at after store normalized it
    mm._redis.hset('mm:meta:alice', 'enqueued_at', str(time.time() - 61))
    expired = mm.pop_expired(now=time.time())
    assert len(expired) == 1
    assert expired[0].username == 'Alice'
    mm.clear_for_tests()
