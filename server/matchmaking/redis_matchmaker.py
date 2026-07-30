"""Redis-backed play queue with local WebSocket connection map."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import redis

from server.matchmaking.matchmaker import (
    ELO_RANGE,
    SEARCH_TIMEOUT_SECONDS,
    QueueEntry,
)

QUEUE_KEY = 'mm:queue'
META_PREFIX = 'mm:meta:'
CONN_PREFIX = 'mm:conn:'


class RedisMatchmaker:
    """
    Matchmaking queue stored in Redis.

    WebSocket objects stay in-process; Redis holds username/rating/timestamps
    so the queue survives gateway restarts and can be shared later.
    """

    def __init__(
        self,
        redis_url: str,
        elo_range: int = ELO_RANGE,
        timeout_seconds: int = SEARCH_TIMEOUT_SECONDS,
    ):
        self.elo_range = elo_range
        self.timeout_seconds = timeout_seconds
        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self._connections: Dict[str, Any] = {}
        self._connection_ids: Dict[int, str] = {}

    def get_entry(self, connection: Any) -> Optional[QueueEntry]:
        username = self._connection_ids.get(id(connection))
        if username is None:
            return None
        return self._load_entry(username, connection)

    def is_queued(self, connection: Any) -> bool:
        return self.get_entry(connection) is not None

    def enqueue(
        self,
        entry: QueueEntry,
    ) -> Optional[Tuple[QueueEntry, QueueEntry]]:
        key = entry.username.lower()
        if self.get_entry(entry.connection) is not None:
            raise ValueError('already_searching')
        if self._redis.exists(META_PREFIX + key):
            raise ValueError('already_searching')

        partner_name = self._find_partner_username(entry.rating)
        if partner_name is None:
            self._store_entry(entry)
            return None

        partner = self._take_entry(partner_name)
        if partner is None:
            self._store_entry(entry)
            return None

        # First enqueued player is White.
        return partner, entry

    def remove(self, connection: Any) -> Optional[QueueEntry]:
        username = self._connection_ids.get(id(connection))
        if username is None:
            return None
        return self._take_entry(username)

    def pop_expired(self, now: Optional[float] = None) -> List[QueueEntry]:
        current = time.time() if now is None else now
        expired: List[QueueEntry] = []
        for username in list(self._redis.zrange(QUEUE_KEY, 0, -1)):
            meta = self._redis.hgetall(META_PREFIX + username)
            if not meta:
                self._redis.zrem(QUEUE_KEY, username)
                continue
            enqueued_at = float(meta.get('enqueued_at', current))
            if current - enqueued_at >= self.timeout_seconds:
                entry = self._take_entry(username)
                if entry is not None:
                    expired.append(entry)
        return expired

    def seconds_remaining(
        self,
        entry: QueueEntry,
        now: Optional[float] = None,
    ) -> int:
        current = time.time() if now is None else now
        elapsed = current - entry.enqueued_at
        return max(0, int(self.timeout_seconds - elapsed))

    def _find_partner_username(self, rating: int) -> Optional[str]:
        low = rating - self.elo_range
        high = rating + self.elo_range
        candidates = self._redis.zrangebyscore(QUEUE_KEY, low, high)
        if not candidates:
            return None
        return candidates[0]

    def _store_entry(self, entry: QueueEntry) -> None:
        key = entry.username.lower()
        enqueued_at = (
            entry.enqueued_at
            if entry.enqueued_at is not None
            else time.time()
        )
        # Normalize to wall-clock for Redis durability.
        if enqueued_at < 1_000_000_000:
            enqueued_at = time.time()
        entry.enqueued_at = enqueued_at
        pipe = self._redis.pipeline()
        pipe.zadd(QUEUE_KEY, {key: entry.rating})
        pipe.hset(
            META_PREFIX + key,
            mapping={
                'username': entry.username,
                'rating': str(entry.rating),
                'enqueued_at': str(enqueued_at),
                'connection_id': str(id(entry.connection)),
            },
        )
        pipe.set(CONN_PREFIX + str(id(entry.connection)), key)
        pipe.execute()
        self._connections[key] = entry.connection
        self._connection_ids[id(entry.connection)] = key

    def _take_entry(self, username_key: str) -> Optional[QueueEntry]:
        key = username_key.lower()
        meta = self._redis.hgetall(META_PREFIX + key)
        connection = self._connections.pop(key, None)
        pipe = self._redis.pipeline()
        pipe.zrem(QUEUE_KEY, key)
        pipe.delete(META_PREFIX + key)
        if meta.get('connection_id'):
            pipe.delete(CONN_PREFIX + meta['connection_id'])
            try:
                self._connection_ids.pop(int(meta['connection_id']), None)
            except ValueError:
                pass
        pipe.execute()
        if connection is not None:
            self._connection_ids.pop(id(connection), None)
        if not meta:
            return None
        if connection is None:
            # Remote/stale entry without a live socket on this process.
            return None
        return QueueEntry(
            meta.get('username', key),
            int(meta.get('rating', 0)),
            connection,
            enqueued_at=float(meta.get('enqueued_at', time.time())),
        )

    def _load_entry(
        self,
        username_key: str,
        connection: Any,
    ) -> Optional[QueueEntry]:
        meta = self._redis.hgetall(META_PREFIX + username_key.lower())
        if not meta:
            return None
        return QueueEntry(
            meta.get('username', username_key),
            int(meta.get('rating', 0)),
            connection,
            enqueued_at=float(meta.get('enqueued_at', time.time())),
        )

    def clear_for_tests(self) -> None:
        """Drop queue keys (test helper)."""
        for username in self._redis.zrange(QUEUE_KEY, 0, -1):
            self._redis.delete(META_PREFIX + username)
        self._redis.delete(QUEUE_KEY)
        self._connections.clear()
        self._connection_ids.clear()
