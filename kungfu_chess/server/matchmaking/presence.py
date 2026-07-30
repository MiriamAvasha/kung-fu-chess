"""Lightweight Redis presence / session keys for logged-in players."""

from __future__ import annotations

from typing import Optional

import redis

from server.infra.settings import REDIS_URL


class PresenceStore:
    def __init__(self, redis_url: str = REDIS_URL):
        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)

    def set_online(self, username: str, ttl_seconds: int = 300) -> None:
        key = 'presence:{}'.format(username.lower())
        self._redis.set(key, 'online', ex=ttl_seconds)

    def set_session(self, username: str, room_id: str) -> None:
        self._redis.set('session:{}'.format(username.lower()), room_id)

    def clear_session(self, username: str) -> None:
        self._redis.delete('session:{}'.format(username.lower()))

    def get_session(self, username: str) -> Optional[str]:
        return self._redis.get('session:{}'.format(username.lower()))

    def set_offline(self, username: str) -> None:
        pipe = self._redis.pipeline()
        pipe.delete('presence:{}'.format(username.lower()))
        pipe.delete('session:{}'.format(username.lower()))
        pipe.execute()
