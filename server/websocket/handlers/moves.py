from typing import TYPE_CHECKING, Any

from shared.messages.client_messages import MoveRequest
from shared.messages.server_messages import ErrorMessage
from shared.messages.types import ServerMessageType

if TYPE_CHECKING:
    from server.websocket.game_server import GameServer


class MoveHandlers:
    def __init__(self, server: 'GameServer'):
        self.server = server

    async def handle_move(
        self,
        websocket: Any,
        message: MoveRequest,
    ) -> None:
        room = self.server.rooms.get_by_connection(websocket)
        if room is None:
            await self.server.send(
                websocket,
                ErrorMessage(
                    'not_joined',
                    'join a room before sending moves',
                ),
            )
            return

        member = room.get_member(websocket)
        if member is None or not member.is_player:
            await self.server.send(
                websocket,
                ErrorMessage(
                    'viewer_cannot_move',
                    'viewers cannot send moves',
                ),
            )
            return

        if not room.is_ready() or not room.game_started:
            await self.server.send(
                websocket,
                ErrorMessage(
                    'game_not_ready',
                    'waiting for match to start',
                ),
            )
            return

        if room.session.is_game_over:
            await self.server.send(
                websocket,
                ErrorMessage('game_over', 'game already finished'),
            )
            return

        result = room.session.handle_command(
            message.command,
            member.role,
        )
        await self.server.send(websocket, result)
        if (
            result.get('type') == ServerMessageType.MOVE_RESULT
            and result.get('accepted')
        ):
            await self.server.broadcast_game_state(room)
            await self.server.maybe_apply_ratings(room)
