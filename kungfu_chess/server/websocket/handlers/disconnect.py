import time
from typing import TYPE_CHECKING, Any

from shared.messages.server_messages import DisconnectCountdown

if TYPE_CHECKING:
    from server.websocket.game_server import GameServer


class DisconnectHandler:
    def __init__(self, server: 'GameServer'):
        self.server = server

    async def handle(self, websocket: Any) -> None:
        self.server.matchmaker.remove(websocket)
        account = self.server.accounts.pop(websocket, None)
        room = self.server.rooms.get_by_connection(websocket)
        if room is None:
            if account is not None:
                self.server.log(
                    'SYS',
                    'Player left: {}'.format(account.username),
                )
            return

        member = room.get_member(websocket)
        if (
            member is not None
            and member.is_player
            and room.game_started
            and not room.session.is_game_over
            and room.is_ready()
        ):
            room.disconnect_deadline = (
                time.monotonic() + self.server.auto_resign_seconds
            )
            room.disconnect_player = member
            room.last_countdown_second = None
            await self.server.broadcast_room(
                room,
                DisconnectCountdown(
                    username=member.username,
                    seconds_remaining=self.server.auto_resign_seconds,
                    total_seconds=self.server.auto_resign_seconds,
                ),
            )
            self.server.log(
                'SYS',
                'Player disconnected during game: {} — '
                'auto-resign in {}s'.format(
                    member.username,
                    self.server.auto_resign_seconds,
                ),
            )
            return

        self.server.rooms.leave(websocket)
        if account is not None:
            self.server.log(
                'SYS',
                'Player left: {}'.format(account.username),
            )
