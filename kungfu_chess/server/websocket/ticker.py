import asyncio
import time
from typing import TYPE_CHECKING, Dict

from shared.messages.server_messages import DisconnectCountdown, NoMatch

from server.websocket.config import TICK_SECONDS

if TYPE_CHECKING:
    from server.websocket.game_server import GameServer


class RoomTicker:
    """Advance active rooms and enforce matchmaking/disconnect timers."""

    def __init__(self, server: 'GameServer'):
        self.server = server
        self._previous_by_room: Dict[str, float] = {}

    async def run(self) -> None:
        while True:
            await asyncio.sleep(TICK_SECONDS)
            now = time.monotonic()
            await self.expire_matchmaking(now)
            await self.tick_disconnect_countdowns(now)
            await self.advance_rooms(now)

    async def advance_rooms(self, now: float) -> None:
        for room in list(self.server.rooms.rooms()):
            if not room.game_started or room.session.is_game_over:
                self._previous_by_room.pop(room.room_id, None)
                continue

            previous = self._previous_by_room.get(room.room_id, now)
            elapsed_ms = max(1, int((now - previous) * 1000))
            self._previous_by_room[room.room_id] = now
            if room.session.advance(elapsed_ms):
                await self.server.broadcast_game_state(room)
                await self.server.maybe_apply_ratings(room)

    async def expire_matchmaking(self, now: float) -> None:
        expired = self.server.matchmaker.pop_expired(now)
        for entry in expired:
            await self.server.send(
                entry.connection,
                NoMatch('no player found'),
            )
            self.server.log(
                'SYS',
                'Matchmaking timeout for {}'.format(entry.username),
            )

    async def tick_disconnect_countdowns(self, now: float) -> None:
        for room in list(self.server.rooms.rooms()):
            if (
                room.disconnect_deadline is None
                or room.disconnect_player is None
                or room.session.is_game_over
            ):
                continue

            remaining = int(max(0, room.disconnect_deadline - now))
            if (
                room.last_countdown_second is None
                or remaining != room.last_countdown_second
            ):
                room.last_countdown_second = remaining
                await self.server.broadcast_room(
                    room,
                    DisconnectCountdown(
                        username=room.disconnect_player.username,
                        seconds_remaining=remaining,
                        total_seconds=self.server.auto_resign_seconds,
                    ),
                )

            if remaining > 0:
                continue

            loser = room.disconnect_player
            room.session.resign(loser.role)
            await self.server.broadcast_game_state(room)
            await self.server.maybe_apply_ratings(
                room,
                reason='auto_resign',
            )
            room.clear_disconnect_timer()
            self.server.log(
                'SYS',
                'Auto-resign: {}'.format(loser.username),
            )
