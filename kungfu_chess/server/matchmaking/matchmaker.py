import time
from typing import Any, List, Optional, Tuple


ELO_RANGE = 100
SEARCH_TIMEOUT_SECONDS = 60


class QueueEntry:
    def __init__(
        self,
        username: str,
        rating: int,
        connection: Any,
        enqueued_at: Optional[float] = None,
    ):
        self.username = username
        self.rating = rating
        self.connection = connection
        self.enqueued_at = (
            time.monotonic() if enqueued_at is None else enqueued_at
        )


class Matchmaker:
    """In-memory play queue with ELO window matching."""

    def __init__(
        self,
        elo_range: int = ELO_RANGE,
        timeout_seconds: int = SEARCH_TIMEOUT_SECONDS,
    ):
        self.elo_range = elo_range
        self.timeout_seconds = timeout_seconds
        self._queue: List[QueueEntry] = []

    def get_entry(self, connection: Any) -> Optional[QueueEntry]:
        for entry in self._queue:
            if entry.connection is connection:
                return entry
        return None

    def is_queued(self, connection: Any) -> bool:
        return self.get_entry(connection) is not None

    def enqueue(self, entry: QueueEntry) -> Optional[Tuple[QueueEntry, QueueEntry]]:
        if self.get_entry(entry.connection) is not None:
            raise ValueError('already_searching')

        for existing in self._queue:
            if existing.username.lower() == entry.username.lower():
                raise ValueError('already_searching')

        partner = self._find_partner(entry)
        if partner is None:
            self._queue.append(entry)
            return None

        self._queue.remove(partner)
        # First enqueued player is White.
        return partner, entry

    def remove(self, connection: Any) -> Optional[QueueEntry]:
        for index, entry in enumerate(self._queue):
            if entry.connection is connection:
                return self._queue.pop(index)
        return None

    def pop_expired(self, now: Optional[float] = None) -> List[QueueEntry]:
        current = time.monotonic() if now is None else now
        expired = []
        remaining = []
        for entry in self._queue:
            if current - entry.enqueued_at >= self.timeout_seconds:
                expired.append(entry)
            else:
                remaining.append(entry)
        self._queue = remaining
        return expired

    def seconds_remaining(
        self,
        entry: QueueEntry,
        now: Optional[float] = None,
    ) -> int:
        current = time.monotonic() if now is None else now
        elapsed = current - entry.enqueued_at
        return max(0, int(self.timeout_seconds - elapsed))

    def _find_partner(self, entry: QueueEntry) -> Optional[QueueEntry]:
        for candidate in self._queue:
            if abs(candidate.rating - entry.rating) <= self.elo_range:
                return candidate
        return None
